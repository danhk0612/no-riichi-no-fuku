"""Analyze saved evidence only; never rerun matches or replace timing evidence."""
import hashlib,importlib.metadata,json,statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent

def analyze():
 folder=HERE/'evidence';rows=[json.loads(p.read_text()) for p in sorted(folder.glob('*-tier*-*.json'))]
 assert len(rows)==16
 collect=[r for r in rows if r['collect']];captures=[c for r in collect for c in r['captured']]
 for r in collect:
  base=next(x for x in rows if x['seed']==r['seed'] and x['tier']==r['tier'] and not x['collect'])
  prior=json.loads((HERE.parent/'w09-a-hand-results/evidence'/f"{r['seed']}-tier{r['tier']}-0.json").read_text())
  for key in ('steps','trace','scores','ranks','log_digest','hora_count'):assert r[key]==base[key]
  for key in ('steps','trace','scores','ranks','log_digest'):assert r[key]==prior[key]
  assert sum(c['hora_count'] for c in r['captured'])==r['hora_count']
 timings=sorted(c['elapsed_s']*1000 for c in captures)
 fixtures=json.loads((folder/'fixtures.json').read_text())
 return dict(source='2291583f1614fde08c397550d34746d0db5d466b',riichienv=importlib.metadata.version('riichienv'),natural_matches=len(rows),pairs=len(collect),horas=sum(r['hora_count'] for r in collect),captured_boundaries=len(captures),intermediate_boundaries=sum(not c['final_live'] for c in captures),live_final_boundaries=sum(c['final_live'] for c in captures),all_trace_equal=True,matches_prior_a_baseline=True,candidate_mismatches=0,clone_capture_mean_ms=statistics.mean(timings),clone_capture_max_ms=max(timings),synthetic_fixtures=len(fixtures['cases']),fixture_setup_expectation_failures=2,production='unchanged',windows='not run',harness_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (HERE/'PLAN.md',HERE/'diagnose.py',HERE/'fixtures.py')})
if __name__=='__main__':
 result=analyze();target=HERE/'evidence/analysis.json'
 if target.exists():assert result==json.loads(target.read_text())
 else:target.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
