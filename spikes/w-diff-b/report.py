"""Descriptive paired seed-block band intervals; not adjacent significance tests."""
import json
import statistics as stats
from pathlib import Path
HERE=Path(__file__).parent
rows=json.loads((HERE/'evidence/matches.json').read_text())
result={}
for context in ('neutral','mixed','characters'):
    groups=[]
    for left,right in ((range(1,4),range(4,8)),(range(4,8),range(8,11)),(range(1,4),range(8,11))):
        metrics={}
        for metric in ('scores','ranks'):
            differences=[]
            for seed in range(5000,5032):
                sub=[r for r in rows if r['context']==context and r['seed']==seed]
                get=lambda levels:stats.mean(r[metric][r['seat']] for r in sub if r['label'] in levels)
                differences.append(get(right)-get(left))
            mean=stats.mean(differences);half=2.04*stats.stdev(differences)/(len(differences)**.5)
            metrics[metric]=dict(mean=mean,descriptive_95_interval=[mean-half,mean+half],seed_blocks=32)
        groups.append(dict(left=list(left),right=list(right),**metrics))
    result[context]=groups
(HERE/'evidence/band-intervals.json').write_text(json.dumps(result,indent=2)+'\n')
