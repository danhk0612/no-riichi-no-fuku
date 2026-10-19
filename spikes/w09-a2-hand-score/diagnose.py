"""Pinned-engine clone diagnostic. No production code or real user data modified."""
from __future__ import annotations
import hashlib,json,os,signal,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from riichienv import RiichiEnv,GameRule,ActionType,calculate_score
from app.mahjong.tier0 import Tier0Agent
from app.mahjong.tier2 import Tier2Agent
HERE=Path(__file__).resolve().parent
FIELDS=('is_win','han','fu','yakuman','yaku','ron_agari','tsumo_agari_oya','tsumo_agari_ko','pao_payer')
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def results(env):return {str(s):{k:getattr(w,k) for k in FIELDS} for s,w in env.win_results.items()}
def fingerprint(env):
 return digest(dict(hands=env.hands,wall=env.wall,log=env.mjai_log,scores=env.scores(),honba=env.honba,sticks=env.riichi_sticks,oya=env.oya,wind=env.round_wind,kyoku=env.kyoku_idx))
def band(w):
 if w['yakuman']:return 3
 points=calculate_score(w['han'],w['fu'],False,False,0).pay_ron
 return 3 if points>=16000 else 2 if points>=8000 else 1

def capture(env,actions):
 before=fingerprint(env);offset=len(env.mjai_log);started=time.perf_counter()
 clone=env.clone();clone.set_scores([-1000000]*4);clone.step(actions)
 assert fingerprint(env)==before,'clone mutated original'
 horas=[e for e in clone.mjai_log[offset:] if e['type']=='hora']
 win=results(clone)
 assert {str(e['actor']) for e in horas}==set(win),'clone winner/result mismatch'
 if horas:assert clone.done(),'clone did not stop before result clear'
 return dict(horas=horas,win_results=win,bands={s:band(w) for s,w in win.items()},elapsed_s=time.perf_counter()-started)

def worker(seed,tier,collect):
 signal.signal(signal.SIGALRM,lambda *a:(_ for _ in ()).throw(TimeoutError('30 second match budget')));signal.alarm(30)
 started=time.monotonic();env=RiichiEnv(game_mode='4p-red-east',rule=GameRule.default_tenhou(),seed=seed)
 obs=env.reset();agents={s:(Tier0Agent if tier==0 else Tier2Agent)(seed=seed*10+s) for s in range(4)}
 trace=[];captured=[];hora_count=0
 for steps in range(5000):
  if env.done():break
  actions={s:agents[s].choose_action(o) for s,o in obs.items()};trace.append({str(s):a.to_dict() for s,a in actions.items()})
  offset=len(env.mjai_log)
  winning=any(a.action_type in (ActionType.RON,ActionType.TSUMO) for a in actions.values())
  shadow=capture(env,actions) if collect and winning else None
  obs=env.step(actions)
  horas=[e for e in env.mjai_log[offset:] if e['type']=='hora'];hora_count+=len(horas)
  if collect and horas:
   assert shadow is not None,'hora without submitted winning action'
   assert shadow['horas']==horas,'shadow changed hora/payment/event order'
   live=results(env)
   if live:assert live==shadow['win_results'],'final live result mismatch'
   captured.append(dict(step=steps+1,source_offset=offset,hora_count=len(horas),final_live=bool(live),**shadow))
 else:raise RuntimeError('5000 step budget')
 assert env.done(),'match unfinished'
 result=dict(seed=seed,tier=tier,collect=collect,steps=len(trace),trace=digest(trace),scores=env.scores(),ranks=env.ranks(),log_digest=digest(env.mjai_log),hora_count=hora_count,captured=captured,elapsed_s=time.monotonic()-started)
 if collect:assert sum(r['hora_count'] for r in captured)==hora_count
 signal.alarm(0);return result

def main():
 folder=HERE/'evidence'
 if folder.exists():raise RuntimeError('preserve evidence; no retries')
 folder.mkdir();start=time.monotonic();deadline=start+600
 meta=dict(source='2291583f1614fde08c397550d34746d0db5d466b',status='running',budget_s=600,max_steps=5000,per_match_s=30,completed_matches=0)
 (folder/'execution.json').write_text(json.dumps(meta,indent=2)+'\n');rows=[]
 try:
  for seed in range(701,705):
   for tier in (0,2):
    for collect in (False,True):
     if time.monotonic()>=deadline:raise TimeoutError('overall budget')
     r=subprocess.run([sys.executable,__file__,'worker',str(seed),str(tier),str(int(collect))],capture_output=True,text=True,timeout=min(30,deadline-time.monotonic()))
     name=f'{seed}-tier{tier}-{int(collect)}';(folder/f'{name}.json').write_text(r.stdout)
     if r.stderr:(folder/f'{name}.stderr.txt').write_text(r.stderr)
     if r.returncode:raise RuntimeError(f'worker failed {name}')
     data=json.loads(r.stdout);rows.append(data);meta['completed_matches']+=1
     if collect:assert all(data[k]==rows[-2][k] for k in ('steps','trace','scores','ranks','log_digest','hora_count')),'instrumentation changed original match'
     print(name,data['hora_count'],flush=True)
  meta['status']='passed-natural-gate'
 except BaseException:meta.update(status='stopped',failure=traceback.format_exc())
 meta['elapsed_s']=time.monotonic()-start;(folder/'execution.json').write_text(json.dumps(meta,indent=2)+'\n')
 return 0 if meta['status']=='passed-natural-gate' else 1
if __name__=='__main__':
 if len(sys.argv)>1:
  try:print(json.dumps(worker(int(sys.argv[2]),int(sys.argv[3]),bool(int(sys.argv[4])))))
  except BaseException:traceback.print_exc();sys.exit(1)
 else:sys.exit(main())
