"""Recompute descriptive diagnosis from raw evidence; never selects a profile."""
import json
from pathlib import Path
import statistics
import sys

def interval(values, z):
    m = statistics.mean(values)
    se = statistics.stdev(values)/len(values)**.5
    return dict(n=len(values), mean=m, se=se, interval=[m-z*se,m+z*se], seed_blocks=values)

def analyze(folder):
    execution = json.loads((folder/'execution.json').read_text())
    result = dict(status=execution['status'], completed_matches=execution['completed_matches'])
    gate_file = folder/'gate1.json'
    if gate_file.exists():
        gate = json.loads(gate_file.read_text())
        sequences = {(r['personality'],r['label']):r['sequence'] for r in gate['rows']}
        differences = []
        if gate['gate_passed']:
            for label in ('baseline','candidate'):
                row = dict(label=label, vs_neutral=[])
                for i in range(1,8):
                    pairs = list(zip(sequences[0,label], sequences[i,label]))
                    both = [(a,b) for a,b in pairs if a['type']==0 and b['type']==0]
                    row['vs_neutral'].append(dict(personality=i, all_actions=sum(a!=b for a,b in pairs),
                        both_discard=len(both), tile_kinds=sum(a['tile']//4!=b['tile']//4 for a,b in both)))
                differences.append(row)
            result['candidate_action_changes'] = [sum(a!=b for a,b in zip(sequences[i,'baseline'],
                                                                         sequences[i,'candidate'])) for i in range(8)]
        result.update(gate_passed=gate['gate_passed'], personality_differences=differences,
                      timings=gate['timings'], gate_failure=gate.get('failure'))
    match_file = folder/'matches.json'
    if match_file.exists():
        rows = json.loads(match_file.read_text())
        contexts = ('neutral','mixed','characters')
        labels = ('tier2','baseline','candidate')
        by = {(r['context'],r['label'],r['seed'],r['seat']):r for r in rows}
        expected = {(c,l,s,seat) for c in contexts for l in labels for s in range(4000,4008) for seat in range(4)}
        assert set(by)==expected and len(rows)==288
        for c in contexts:
            for s in range(4000,4008):
                for seat in range(4):
                    a,b = by[c,'tier2',s,seat], by[c,'baseline',s,seat]
                    assert all(a[k]==b[k] for k in ('trace','scores','ranks','steps','decisions'))
        z = statistics.NormalDist().inv_cdf(1-.05/(2*6))
        summaries, paired = [], []
        for c in contexts:
            for label in labels:
                selected = [r for r in rows if r['context']==c and r['label']==label]
                summaries.append(dict(context=c,label=label,matches=len(selected),
                    mean_score=statistics.mean(r['scores'][r['seat']] for r in selected),
                    mean_rank=statistics.mean(r['ranks'][r['seat']] for r in selected),
                    decisions=sum(r['decisions'] for r in selected),changed=sum(r['changed'] for r in selected),
                    nodes=sum(r['nodes'] for r in selected)))
            metrics = {}
            for metric in ('scores','ranks'):
                values = [statistics.mean(by[c,'candidate',s,seat][metric][seat]-
                                         by[c,'tier2',s,seat][metric][seat] for seat in range(4)) for s in range(4000,4008)]
                metrics[metric] = dict(descriptive_t95=interval(values,2.365),
                                       bonferroni_normal95=interval(values,z))
            paired.append(dict(context=c,metrics=metrics))
        result.update(matches=len(rows), steps=sum(r['steps'] for r in rows),
                      max_steps=max(r['steps'] for r in rows),baseline_reference_pairs=96,
                      summaries=summaries,paired=paired,bonferroni_normal_multiplier=z,
                      comparison_unit='8 seed blocks; four rotated seats averaged first')
    return result

if __name__=='__main__':
    folder=Path(sys.argv[1])
    result=analyze(folder)
    (folder/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],matches=result.get('matches',0),gate=result.get('gate_passed'))))
