"""Known factorial outcomes validate block and interaction aggregation."""
import unittest
from analyze import analyze
from probe import ALL_LABELS,CONTEXTS

class AnalysisTests(unittest.TestCase):
    def test_known_additive_axes_and_paired_blocks(self):
        rows=[]
        for c in CONTEXTS:
            for label in ALL_LABELS:
                u,d,m=(0,0,0) if label=='tier2' else map(int,label)
                score=100*u+20*d+3*m
                for seed in range(2000,2016):
                    for seat in range(4):
                        rows.append(dict(context=c,label=label,seed=seed,seat=seat,
                            scores=[score+seed]*4,ranks=[2.5-score/1000]*4,
                            elapsed_s=1,decision_ms_sum=2,decisions=2,decision_ms_max=1,
                            changed=0,folds=0,nondiscard=0))
        report=analyze(rows)
        for row in report['contrasts']:
            expected={'U':100,'D':20,'M':3}.get(row['axes'],0)
            self.assertAlmostEqual(row['metrics']['scores']['mean'],expected)
            self.assertEqual(row['metrics']['scores']['n'],16)
        full=next(r for r in report['results'] if r['context']=='mixed' and r['label']=='111')
        self.assertEqual(full['metrics']['scores']['paired_t95']['mean'],123)
        self.assertEqual([r['n_blocks'] for r in full['personality']],[3,3,3,3,2,2])
        self.assertEqual(full['metrics']['scores']['paired_t95']['interval'],[123,123])

if __name__=='__main__':unittest.main()
