"""Seed-block paired estimates; descriptive factorial contrasts, no selection."""
import itertools
import gzip
import json
from pathlib import Path
import statistics
import sys
from probe import LABELS, ALL_LABELS, CONTEXTS

def interval(values,z):
    mean=statistics.mean(values)
    se=statistics.stdev(values)/(len(values)**.5) if len(values)>1 else None
    return dict(n=len(values),mean=mean,se=se,
                interval=None if se is None else [mean-z*se,mean+z*se])

def analyze(rows):
    assert len(rows)==1728
    by_key={(r['context'],r['label'],r['seed'],r['seat']):r for r in rows}
    assert len(by_key)==1728
    z=statistics.NormalDist().inv_cdf(1-.05/(2*48))
    results=[];contrasts=[]
    for c in CONTEXTS:
        blocks={}
        for l in ALL_LABELS:
            blocks[l]={s:{metric:statistics.mean(by_key[c,l,s,seat][metric][seat] for seat in range(4))
                           for metric in ('scores','ranks')} for s in range(2000,2016)}
        for label in ALL_LABELS:
            selected=[r for r in rows if r['context']==c and r['label']==label]
            metrics={}
            for metric in ('scores','ranks'):
                values=[blocks[label][s][metric]-blocks['tier2'][s][metric] for s in range(2000,2016)]
                metrics[metric]=dict(absolute_mean=statistics.mean(blocks[label][s][metric] for s in range(2000,2016)),
                    paired_t95=interval(values,2.131),paired_bonferroni_normal95=interval(values,z),
                    seed_blocks=values)
            personality=[]
            for i in range(6):
                seeds=[s for s in range(2000,2016) if (0 if c=='neutral' else (s-2000)%6)==i]
                if seeds:personality.append(dict(index=i,n_blocks=len(seeds),**{
                    metric:statistics.mean(blocks[label][s][metric]-blocks['tier2'][s][metric] for s in seeds)
                    for metric in ('scores','ranks')}))
            results.append(dict(context=c,label=label,metrics=metrics,personality=personality,
                elapsed_worker_s=sum(r['elapsed_s'] for r in selected),
                decision_mean_ms=sum(r['decision_ms_sum'] for r in selected)/sum(r['decisions'] for r in selected),
                decision_max_ms=max(r['decision_ms_max'] for r in selected),
                changes=sum(r['changed'] for r in selected),folds=sum(r['folds'] for r in selected),
                nondiscard=sum(r['nondiscard'] for r in selected)))
        for count in (1,2,3):
            for axes in itertools.combinations(range(3),count):
                metrics={}
                for metric in ('scores','ranks'):
                    values=[sum((1 if sum(int(l[a]) for a in axes)%2==count%2 else -1)
                                *blocks[l][s][metric] for l in LABELS)/4 for s in range(2000,2016)]
                    metrics[metric]=interval(values,2.131)
                contrasts.append(dict(context=c,axes=''.join('UDM'[a] for a in axes),metrics=metrics))
    return dict(comparison_unit='seed mean of four rotated seats',n_blocks_per_context=16,
        t_multiplier=2.131,bonferroni_normal_multiplier=z,comparison_count=48,
        contrast_definition='sum(sign * block outcome)/4; sign=product(2*bit-1); higher order scaled like main effects',
        results=results,contrasts=contrasts)

if __name__=='__main__':
    directory=Path(sys.argv[1])
    source=directory/'matches.json'
    data=source.read_text() if source.exists() else gzip.decompress(source.with_suffix('.json.gz').read_bytes()).decode()
    (directory/'analysis.json').write_text(json.dumps(analyze(json.loads(data)),indent=2)+'\n')
