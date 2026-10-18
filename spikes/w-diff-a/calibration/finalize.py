"""Recompute both splits, compare independent checks, reproduce 12 held-out traces."""
import hashlib
import json
from pathlib import Path
import sys
from analyze_v2 import analyze
from run import CONTEXTS,match
from analyze import analyze as analyze_v1
from compare import summarize

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

def finalize(directory):
    output=HERE/'evidence'
    output.mkdir(exist_ok=True)
    for split in ('tune','holdout'):
        data=json.loads((directory/f'calibration-{split}.json').read_text())
        analysis=analyze(data)
        (output/f'{split}.json').write_text(json.dumps(data,indent=2)+'\n')
        (output/f'{split}-analysis.json').write_text(json.dumps(analysis,indent=2)+'\n')
    left=json.loads((directory/'calibration-check1.json').read_text())
    right=json.loads((directory/'calibration-check2.json').read_text())
    (output/'check.json').write_text(json.dumps(left,indent=2)+'\n')
    left_timing,right_timing=left.pop('timings'),right.pop('timings')
    assert left==right, 'independent processes changed behavior or replay'
    old=json.loads((PARENT/'evidence/matches.json').read_text())
    assert summarize(old['matches'])==old['summary']
    assert analyze_v1(old)==json.loads((PARENT/'evidence/analysis.json').read_text())
    old_sources=json.loads((PARENT/'evidence/sources.json').read_text())
    for path,sha in old_sources['script_sha256'].items():
        assert hashlib.sha256((PARENT/path).read_bytes()).hexdigest()==sha,path
    held=json.loads((output/'holdout.json').read_text())
    repeats=[]
    for context in CONTEXTS:
        for label in (1,5,10,'tier2'):
            original=next(r for r in held['matches'] if r['context']==context and r['label']==label
                          and r['seed']==1000 and r['seat']==2)
            # Normalize tuple scores/ranks to their persisted JSON list representation.
            repeated=json.loads(json.dumps(match((context,label,1000,2,1000))))
            deterministic=('context','label','seed','seat','personality_index','trace','scores','ranks',
                           'steps','decisions','lapses','changed','protected_folds')
            assert all(original[k]==repeated[k] for k in deterministic),(context,label)
            repeats.append({k:repeated[k] for k in deterministic})
    record=dict(independent_check_equal=True,deterministic_check_sha256=digest(left),
        timings_process1=left_timing,timings_process2=right_timing,
        v1_summary_analysis_and_script_hashes_unchanged=True,repeated_holdout_matches=repeats)
    (output/'reproducibility.json').write_text(json.dumps(record,indent=2)+'\n')
    sources=dict(base=held['base'],plan_sha256=hashlib.sha256((HERE/'PLAN.md').read_bytes()).hexdigest(),
        calibration_scripts={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob('*.py'))},
        reused_v1_scripts=old_sources['script_sha256'],
        evidence_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.glob('*.json'))
                         if p.name!='sources.json'})
    (output/'sources.json').write_text(json.dumps(sources,indent=2)+'\n')
    print(json.dumps(dict(check_hash=record['deterministic_check_sha256'],repeated_matches=len(repeats),
                         v1_unchanged=True)))

if __name__=='__main__':finalize(Path(sys.argv[1]))
