"""Stages launched by one deadline-owning parent; partial rows survive failure."""
import json
from pathlib import Path
import sys
import time
from probe import ALL_LABELS, CONTEXTS, HERE, match, replay
sys.path.insert(0,str(HERE.parent/'calibration'))
from run import run_jobs

DETERMINISTIC=('context','label','seed','seat','personality_index','trace','scores','ranks',
               'steps','decisions','changed','folds','nondiscard')

def main(mode,directory,budget):
    if mode=='matches':
        jobs=[(c,l,s,seat) for c in CONTEXTS for l in ALL_LABELS
              for s in range(2000,2016) for seat in range(4)]
        (directory/'jobs.json').write_text(json.dumps(jobs)+'\n')
        with (directory/'matches.jsonl').open('w') as stream:
            def progress(rows):
                stream.write(json.dumps(rows[-1])+'\n');stream.flush()
                if len(rows)%64==0:print(f'{len(rows)}/1728',flush=True)
            rows=run_jobs(jobs,worker=match,wall_budget=budget,workers=8,on_result=progress)
        assert len(rows)==1728
        by_key={(r['context'],r['label'],r['seed'],r['seat']):r for r in rows}
        for c in CONTEXTS:
            for seed in range(2000,2016):
                for seat in range(4):
                    a=by_key[c,'000',seed,seat];b=by_key[c,'tier2',seed,seat]
                    assert all(a[k]==b[k] for k in ('trace','scores','ranks','steps','decisions','nondiscard'))
        (directory/'matches.json').write_text(json.dumps(rows,indent=2)+'\n')
    elif mode=='reproduce':
        rows=json.loads((directory/'matches.json').read_text())
        repeated=[]
        for c in CONTEXTS:
            for label in ALL_LABELS:
                row=json.loads(json.dumps(match((c,label,2000,2))))
                original=next(r for r in rows if (r['context'],r['label'],r['seed'],r['seat'])==(c,label,2000,2))
                assert all(original[k]==row[k] for k in DETERMINISTIC),(c,label)
                repeated.append({k:row[k] for k in DETERMINISTIC})
        (directory/'reproduced.json').write_text(json.dumps(repeated,indent=2)+'\n')
    else:
        (directory/'replay.json').write_text(json.dumps(replay(),indent=2)+'\n')

if __name__=='__main__':main(sys.argv[1],Path(sys.argv[2]),float(sys.argv[3]))
