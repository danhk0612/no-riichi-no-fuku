"""Recompute complete fixed-grid seed-block comparisons without sorting levels."""
import json
from pathlib import Path
from statistics import NormalDist,mean,stdev
import sys
from run import CONTEXTS,LABELS,summarize

def analyze(data):
    rows=data['matches'];start=data['seed_start'];count=data['seed_count']
    by_key={(r['context'],r['label'],r['seed'],r['seat']):r for r in rows}
    expected={(c,l,s,seat) for c in CONTEXTS for l in LABELS
              for s in range(start,start+count) for seat in range(4)}
    assert set(by_key)==expected and len(rows)==len(expected)
    for c in CONTEXTS:
        for s in range(start,start+count):
            for seat in range(4):
                a,b=(by_key[c,l,s,seat] for l in (10,'tier2'))
                assert all(a[k]==b[k] for k in ('trace','scores','ranks','steps'))
    assert data['summary']=={c:summarize([r for r in rows if r['context']==c]) for c in CONTEXTS}
    z=NormalDist().inv_cdf(1-.05/(2*54))
    pairs=[]
    for c in CONTEXTS:
        for low,high in [*((i,i+1) for i in range(1,10)),(1,10),('v1-L1',1)]:
            entry=dict(context=c,low=low,high=high)
            for metric in ('scores','ranks'):
                blocks=[mean(by_key[c,high,s,seat][metric][seat]-by_key[c,low,s,seat][metric][seat]
                             for seat in range(4)) for s in range(start,start+count)]
                m,se=mean(blocks),stdev(blocks)/count**.5
                entry[metric]=dict(mean=m,se=se,seed_blocks=blocks,
                    descriptive_95=[m-2.04*se,m+2.04*se] if count==32 else None,
                    bonferroni_normal_54=[m-z*se,m+z*se] if count==32 else None)
            if count==32:
                entry['practical_recommendation_met']=(entry['scores']['mean']>=500 and entry['ranks']['mean']<=-.05
                    and entry['scores']['bonferroni_normal_54'][0]>0 and entry['ranks']['bonferroni_normal_54'][1]<0)
            pairs.append(entry)
    # Small per-character strata are descriptive only; never treat seats as independent.
    strata=[]
    for c in CONTEXTS[1:]:
        for index in range(6):
            for label in LABELS:
                group=[r for r in rows if r['context']==c and r['personality_index']==index and r['label']==label]
                if group:strata.append(dict(context=c,personality=index,label=label,matches=len(group),
                    seed_blocks=len({r['seed'] for r in group}),mean_score=mean(r['scores'][r['seat']] for r in group),
                    mean_rank=mean(r['ranks'][r['seat']] for r in group)))
    return dict(split=data['split'],matches=len(rows),steps=sum(r['steps'] for r in rows),
        target_decisions=sum(r['decisions'] for r in rows),max_steps=max(r['steps'] for r in rows),
        seed_blocks_per_context=count,rotations_per_block=4,
        interval='df31 t approximation 2.04 (32 only); Bonferroni normal approximation over 54 tests, not exact simultaneous t inference',
        adjusted_normal_multiplier=z,level10_equals_tier2_all_traces=True,pairs=pairs,personality_strata=strata,
        adjacent_practical_pass_count=sum(p.get('practical_recommendation_met',False) for p in pairs if isinstance(p['low'],int) and p['high']==p['low']+1))

if __name__=='__main__':
    Path(sys.argv[2]).write_text(json.dumps(analyze(json.loads(Path(sys.argv[1]).read_text())),indent=2)+'\n')
