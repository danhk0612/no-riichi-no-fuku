"""Fixed 288-game diagnostic grid and nine predetermined trace reproductions."""
import hashlib
import json
from pathlib import Path
import sys
import time
from validate import HERE, ROOT, PERSONALITIES, PROFILES, OneStepAgent
from probe import CONTEXTS
from app.mahjong.tier0 import Tier0Agent
from app.mahjong.tier1 import Tier1Agent
from app.mahjong.tier2 import Tier2Agent
from app.mahjong.riichienv_adapter import RiichiEnvAdapter
sys.path.insert(0, str(HERE.parent/'calibration'))
from run import run_jobs

LABELS = ('tier2', 'baseline', 'candidate')
KEYS = ('context','label','seed','seat','scores','ranks','steps','trace','decisions','changed','nodes')

def match(job):
    context, label, seed, seat = job
    index = (seed-4000)%6
    agents = {}
    for offset in range(4):
        s = (seat+offset)%4
        p = PERSONALITIES[0 if context!='characters' else (index+offset)%6]
        cls = (Tier0Agent,Tier1Agent,Tier2Agent)[offset-1] if context=='mixed' and offset else Tier2Agent
        agents[s] = cls(seed=seed*10+s, **p)
    personality = PERSONALITIES[0 if context=='neutral' else index]
    agents[seat] = (Tier2Agent(seed=seed*10+seat, **personality) if label=='tier2' else
                    OneStepAgent(PROFILES[0 if label=='baseline' else 1], seed=seed*10+seat, **personality))
    adapter = RiichiEnvAdapter(seed=seed)
    adapter.start()
    trace = hashlib.sha256()
    steps = changed = nodes = decisions = 0
    before = time.perf_counter()
    while not adapter.done:
        assert steps < 5000
        actions = {}
        for s in sorted(adapter.pending_observations):
            obs = adapter.pending_observations[s]
            action = agents[s].choose_action(obs)
            assert action.to_dict() in [a.to_dict() for a in obs.legal_actions()]
            actions[s] = action
            if s==seat:
                decisions += 1
                if label!='tier2':
                    changed += action.to_dict()!=agents[s].last['baseline']
                    nodes += agents[s].last['nodes']
        trace.update(json.dumps({s:a.to_dict() for s,a in actions.items()}, sort_keys=True).encode())
        adapter.step(actions)
        steps += 1
    result = adapter.result()
    return dict(context=context, label=label, seed=seed, seat=seat, scores=result.scores,
                ranks=result.ranks, steps=steps, trace=trace.hexdigest(), decisions=decisions,
                changed=changed, nodes=nodes, elapsed_s=time.perf_counter()-before)

if __name__ == '__main__':
    mode, folder, budget = sys.argv[1:]
    directory = Path(folder)
    if mode=='matches':
        jobs = [(c,l,s,seat) for c in CONTEXTS for l in LABELS for s in range(4000,4008) for seat in range(4)]
        (directory/'jobs.json').write_text(json.dumps(jobs)+'\n')
        with (directory/'matches.jsonl').open('w') as stream:
            def progress(rows):
                stream.write(json.dumps(rows[-1])+'\n')
                stream.flush()
                if len(rows)%32==0:
                    print(f'{len(rows)}/288', flush=True)
            rows = run_jobs(jobs, worker=match, workers=8, wall_budget=float(budget), on_result=progress)
        by = {(r['context'],r['label'],r['seed'],r['seat']):r for r in rows}
        for c in CONTEXTS:
            for s in range(4000,4008):
                for seat in range(4):
                    a,b = by[c,'tier2',s,seat], by[c,'baseline',s,seat]
                    assert all(a[k]==b[k] for k in ('scores','ranks','steps','trace','decisions'))
        (directory/'matches.json').write_text(json.dumps(rows, indent=2)+'\n')
    else:
        rows = json.loads((directory/'matches.json').read_text())
        repeats = []
        for c in CONTEXTS:
            for label in LABELS:
                r = json.loads(json.dumps(match((c,label,4000,2))))
                original = next(x for x in rows if all(x[k]==r[k] for k in ('context','label','seed','seat')))
                assert all(original[k]==r[k] for k in KEYS)
                repeats.append({k:r[k] for k in KEYS})
        (directory/'reproduced.json').write_text(json.dumps(repeats, indent=2)+'\n')
