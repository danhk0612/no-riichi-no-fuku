"""Fixed-budget rotated comparisons. Run tune before holdout; no candidate search."""
import argparse
from multiprocessing import Pool, TimeoutError as PoolTimeoutError
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compare import summarize
from profiles import PROFILES as V1, ProfileAgent as AgentV1
from verify import FIELDS, ROOT
from profiles_v2 import PROFILES, ProfileAgent
from app.mahjong.riichienv_adapter import RiichiEnvAdapter
from app.mahjong.tier0 import Tier0Agent
from app.mahjong.tier1 import Tier1Agent
from app.mahjong.tier2 import Tier2Agent

PERSONALITIES = [{k: p[k] for k in FIELDS} for p in json.loads(
    (ROOT / 'backend/app/seeds/cpu_characters.json').read_text())]
CONTEXTS = ('neutral', 'mixed', 'characters')
LABELS = (*range(1, 11), 'v1-L1', 'tier2')

def run_jobs(jobs, *, worker=None, workers=8, wall_budget=2700, on_result=None):
    """Keep submission order, but bound waits and terminate workers on failure."""
    before = time.perf_counter()
    rows = []
    # Pool's context exit terminates queued AND running work, unlike executor
    # shutdown(wait=True). A timed iterator wait also covers a stalled first job.
    with Pool(processes=workers) as pool:
        pending = pool.imap(match if worker is None else worker, jobs)
        for _ in range(len(jobs)):
            remaining = wall_budget - (time.perf_counter() - before)
            if remaining <= 0:
                raise TimeoutError('fixed wall budget exceeded')
            try:
                row = pending.next(timeout=remaining)
            except PoolTimeoutError as exc:
                raise TimeoutError('fixed wall budget exceeded') from exc
            rows.append(row)
            if on_result is not None:
                on_result(rows)
        if time.perf_counter() - before >= wall_budget:
            raise TimeoutError('fixed wall budget exceeded')
    return rows

def match(job):
    context, label, seed, seat, start = job
    index = (seed - start) % 6
    target_personality = PERSONALITIES[0 if context == 'neutral' else index]
    agents = {}
    for offset in range(4):
        s = (seat + offset) % 4
        personality = PERSONALITIES[0 if context != 'characters' else (index + offset) % 6]
        cls = (Tier0Agent, Tier1Agent, Tier2Agent)[offset - 1] if context == 'mixed' and offset else Tier2Agent
        agents[s] = cls(seed=seed * 10 + s, **personality)
    if isinstance(label, int):
        agents[seat] = ProfileAgent(PROFILES[label - 1], seed=seed*10+seat, **target_personality)
    elif label == 'v1-L1':
        agents[seat] = AgentV1(V1[0], seed=seed*10+seat, **target_personality)
    else:
        agents[seat] = Tier2Agent(seed=seed*10+seat, **target_personality)
    adapter = RiichiEnvAdapter(seed=seed)
    adapter.start()
    trace = hashlib.sha256()
    durations = []
    steps = 0
    started = time.perf_counter()
    while not adapter.done:
        actions = {}
        for s in sorted(adapter.pending_observations):
            before = time.perf_counter_ns()
            actions[s] = agents[s].choose_action(adapter.pending_observations[s])
            if s == seat:
                durations.append((time.perf_counter_ns()-before)/1e6)
        trace.update(json.dumps({s:a.to_dict() for s,a in actions.items()}, sort_keys=True).encode())
        adapter.step(actions)
        steps += 1
        assert steps <= 5000, job
    target, result = agents[seat], adapter.result()
    return dict(context=context, label=label, seed=seed, seat=seat,
        personality_index=0 if context=='neutral' else index,
        scores=result.scores, ranks=result.ranks, steps=steps, trace=trace.hexdigest(),
        elapsed_s=time.perf_counter()-started, decisions=len(durations),
        decision_ms_sum=sum(durations), decision_ms_p95=sorted(durations)[int((len(durations)-1)*.95)],
        decision_ms_max=max(durations), lapses=getattr(target,'lapses',0),
        changed=getattr(target,'changed',0), protected_folds=getattr(target,'protected_folds',0))

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('split', choices=('tune','holdout'))
    p.add_argument('output', type=Path)
    args = p.parse_args()
    start, count = (300,4) if args.split=='tune' else (1000,32)
    jobs = [(c,l,s,seat,start) for c in CONTEXTS for l in LABELS
            for s in range(start,start+count) for seat in range(4)]
    before = time.perf_counter()
    def progress(rows):
        if len(rows) % (count*4) == 0:
            print(json.dumps(dict(context=rows[-1]['context'], summary=summarize(rows[-count*4:])[0])),flush=True)
    rows = run_jobs(jobs, on_result=progress)
    payload = dict(base='a50f13b57c41becb56cac9561bad456e9246199f', split=args.split,
        python=platform.python_version(), platform=platform.platform(),riichienv='0.4.8',
        seed_start=start,seed_count=count,workers=8,elapsed_s=time.perf_counter()-before,
        profiles=[asdict(p) for p in PROFILES],
        summary={c:summarize([r for r in rows if r['context']==c]) for c in CONTEXTS},matches=rows)
    args.output.write_text(json.dumps(payload,indent=2)+'\n')
