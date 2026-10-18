"""Frozen suit-corrected candidate measurement; no fitting or parameter search."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))
sys.path.insert(0, str(ROOT/'spikes/w-diff-a/calibration'))
import run as previous
from app.mahjong.difficulty import PROFILES, ProfileAgent
previous.PROFILES, previous.ProfileAgent = PROFILES, ProfileAgent
import hashlib
import json
import statistics
import subprocess
import time

OUT = Path(__file__).parent/'evidence'

def main():
    started=time.perf_counter()
    source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    checks=[]
    for n in (1,2):
        path=OUT/f'check-{n}.json'
        subprocess.run([sys.executable,str(Path(__file__).parent/'check.py'),str(path)],
                       check=True,timeout=max(1,1200-(time.perf_counter()-started)))
        data=json.loads(path.read_text())
        checks.append(hashlib.sha256(json.dumps({k:v for k,v in data.items() if k!='timings'},sort_keys=True).encode()).hexdigest())
        print('check',n,checks[-1],flush=True)
    assert checks[0]==checks[1]
    start=5000
    jobs=[(c,l,s,seat,start) for c in previous.CONTEXTS for l in (*range(1,11),'tier2')
          for s in range(start,start+32) for seat in range(4)]
    def progress(rows):
        if len(rows)%128==0:
            (OUT/'partial.json').write_text(json.dumps(rows,separators=(',',':'))+'\n')
            print(len(rows),rows[-1]['context'],rows[-1]['label'],flush=True)
    rows=previous.run_jobs(jobs,workers=8,wall_budget=1200-(time.perf_counter()-started),on_result=progress)
    (OUT/'matches.json').write_text(json.dumps(rows,separators=(',',':'))+'\n')
    samples=[]
    for c in previous.CONTEXTS:
        for label in (1,5,10,'tier2'):
            job=(c,label,5000,1,start)
            fresh=previous.match(job)
            saved=next(r for r in rows if (r['context'],r['label'],r['seed'],r['seat'])==job[:4])
            for key in ('scores','ranks','steps','trace'):
                assert json.loads(json.dumps(fresh[key]))==saved[key],(job,key)
            samples.append(fresh)
    summaries={c:previous.summarize([r for r in rows if r['context']==c]) for c in previous.CONTEXTS}
    bands={}; passed=True
    for c,summary in summaries.items():
        band=[]
        for name,levels in [('low',range(1,4)),('mid',range(4,8)),('high',range(8,11))]:
            sub=[r for r in rows if r['context']==c and r['label'] in levels]
            band.append(dict(name=name,mean_score=statistics.mean(r['scores'][r['seat']] for r in sub),
                             mean_rank=statistics.mean(r['ranks'][r['seat']] for r in sub)))
        passed &= all(a['mean_score']<b['mean_score'] and a['mean_rank']>b['mean_rank'] for a,b in zip(band,band[1:]))
        bands[c]=band
    identical=0
    lookup={(r['context'],r['label'],r['seed'],r['seat']):r for r in rows}
    for r in rows:
        if r['label']!=10:continue
        base=lookup[r['context'],'tier2',r['seed'],r['seat']]
        assert all(r[k]==base[k] for k in ('scores','ranks','steps','trace'))
        identical+=1
    payload=dict(source=source,profiles=[previous.asdict(p) for p in PROFILES],checks=checks,
                 sample_reproductions=samples,summary=summaries,bands=bands,
                 l10_tier2_identical=identical,elapsed_s=time.perf_counter()-started,passed=bool(passed))
    (OUT/'result.json').write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps(dict(bands=bands,passed=bool(passed),elapsed_s=payload['elapsed_s'])),flush=True)
    assert passed,'broad strength trend failed; do not adopt'
    assert payload['elapsed_s']<1200

if __name__=='__main__':main()
