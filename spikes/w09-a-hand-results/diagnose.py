"""Bounded read-only engine diagnostics. No production imports are patched."""
from __future__ import annotations
import copy, hashlib, json, os, signal, subprocess, sys, tempfile, time, traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from importlib.metadata import version
from riichienv import RiichiEnv, GameRule, MjaiReplay, calculate_score
from app.mahjong.tier0 import Tier0Agent
from app.mahjong.tier2 import Tier2Agent
SOURCE='d90cc4dcb78c2f5ffa24e2a9a5b2fd32e36603b4'

def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def wr(x):
    return {k:getattr(x,k) for k in ('is_win','han','fu','yakuman','ron_agari','tsumo_agari_oya','tsumo_agari_ko','pao_payer','yaku')}

def replay(log):
    with tempfile.TemporaryDirectory(prefix='w09a-log-') as temp:
        p=Path(temp)/'match.jsonl';p.write_text('\n'.join(json.dumps(x) for x in log)+'\n')
        r=MjaiReplay.from_jsonl(str(p),rule='tenhou')
        return [[dict(seat=c.seat,actual=wr(c.actual),expected_han=c.expected_han,expected_fu=c.expected_fu,
                      conditions={k:getattr(c.conditions,k) for k in ('honba','riichi_sticks','tsumo','player_wind','round_wind')},
                      recalculated=wr(c.calculate(c.create_calculator())))
                 for c in k.take_win_result_contexts()] for k in r.take_kyokus()]

def worker(seed,tier,collect):
    signal.signal(signal.SIGALRM,lambda *a:(_ for _ in ()).throw(TimeoutError('30 second match budget')))
    signal.alarm(30);began=time.monotonic()
    e=RiichiEnv(game_mode='4p-red-east',rule=GameRule.default_tenhou(),seed=seed)
    obs=e.reset();agents={s:(Tier0Agent if tier==0 else Tier2Agent)(seed=seed*10+s) for s in range(4)}
    trace=[];boundaries=[];obs_hora=[];cursor=0;step=0;log_snapshot=None
    while not e.done():
        if step>=5000:raise RuntimeError('5000 step budget')
        actions={s:agents[s].choose_action(o) for s,o in obs.items()}
        trace.append({s:a.to_dict() for s,a in actions.items()})
        obs=e.step(actions);step+=1
        log=e.mjai_log
        delta=log[cursor:];cursor=len(log)
        if any(x['type'] in ('hora','ryukyoku','end_kyoku') for x in delta):
            boundaries.append(dict(step=step,log_end=cursor,done=e.done(),events=delta,
                                   win_results={s:wr(v) for s,v in e.win_results.items()}))
        for s,o in obs.items():
            for ev in o.to_dict().get('events',[]):
                if isinstance(ev,str):ev=json.loads(ev)
                if ev.get('type')=='hora':obs_hora.append(dict(step=step,seat=s,event=ev))
        if collect and log_snapshot is None and any(x['type']=='end_kyoku' for x in delta):
            log_snapshot=copy.deepcopy(log)
    log=copy.deepcopy(e.mjai_log);before=digest(log)
    result=dict(seed=seed,tier=tier,collect=collect,steps=step,scores=e.scores(),ranks=e.ranks(),trace=digest(trace),
                log_digest=before,boundaries=boundaries,observation_hora=obs_hora,
                event_counts={t:sum(ev['type']==t for ev in log) for t in sorted({x['type'] for x in log})})
    if collect:
        native_start=time.monotonic()
        try:result['native']=replay(copy.deepcopy(log))
        except Exception:result['native_error']=traceback.format_exc()
        result['native_s']=time.monotonic()-native_start
        viewer_start=time.monotonic()
        try:
            from riichienv.visualizer import GameViewer
            v=GameViewer(copy.deepcopy(log));n=sum(x['type']=='end_kyoku' for x in log)
            result['viewer']=[[wr(x) for x in v.get_results(i)] for i in range(n)]
        except Exception:result['viewer_error']=traceback.format_exc()
        result['viewer_s']=time.monotonic()-viewer_start
        if log_snapshot is not None:
            try:result['first_boundary_native']=replay(log_snapshot)
            except Exception:result['first_boundary_native_error']=traceback.format_exc()
        assert digest(e.mjai_log)==before,'collector modified original engine log'
    result['elapsed_s']=time.monotonic()-began
    signal.alarm(0)
    return result

def main():
    folder=HERE/'evidence'
    if folder.exists():raise RuntimeError('preserve evidence: no natural-sample retry')
    folder.mkdir()
    start=time.monotonic();deadline=start+600
    jobs=[(seed,tier,collect) for seed in range(701,705) for tier in (0,2) for collect in (False,True)]
    meta=dict(source=SOURCE,python=sys.version,riichienv=version('riichienv'),jobs=jobs,budget_s=600,
              per_match_s=30,max_steps=5000,agent_seed='seed*10+seat',tier2_policy=2,status='running')
    (folder/'plan.json').write_text(json.dumps(meta,indent=2)+'\n')
    rows=[]
    try:
        for seed,tier,collect in jobs:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('overall 600 second deadline')
            run=subprocess.run([sys.executable,__file__,'worker',str(seed),str(tier),str(int(collect))],
                               text=True,capture_output=True,timeout=min(30,remaining))
            name=f'{seed}-tier{tier}-{int(collect)}'
            (folder/f'{name}.json').write_text(run.stdout)
            if run.stderr:(folder/f'{name}.stderr.txt').write_text(run.stderr)
            if run.returncode:raise RuntimeError(f'worker stopped {name}: {run.returncode}')
            row=json.loads(run.stdout);rows.append(row)
            if collect:
                prior=rows[-2]
                assert all(prior[k]==row[k] for k in ('trace','scores','ranks','steps','log_digest')),'trace/final mismatch'
            print(f'{name}: {row["steps"]} steps / {row["elapsed_s"]:.3f}s',flush=True)
        meta['status']='passed-trace-gate'
    except BaseException:meta.update(status='stopped',failure=traceback.format_exc())
    meta.update(elapsed_s=time.monotonic()-start,completed_matches=len(rows))
    (folder/'execution.json').write_text(json.dumps(meta,indent=2)+'\n')
    return 0 if meta['status']=='passed-trace-gate' else 1

if __name__=='__main__':
    if len(sys.argv)>1:
        try:print(json.dumps(worker(int(sys.argv[2]),int(sys.argv[3]),bool(int(sys.argv[4]))),default=int))
        except BaseException:traceback.print_exc();sys.exit(1)
    else:sys.exit(main())
