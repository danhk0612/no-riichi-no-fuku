"""Known paired outcomes check seed-block aggregation, not game strength."""
import json
from pathlib import Path
import tempfile
import unittest
from report import analyze

class ReportTests(unittest.TestCase):
    def test_constant_paired_effect_and_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            (folder/'execution.json').write_text(json.dumps(dict(status='passed',completed_matches=288)))
            rows=[]
            for c in ('neutral','mixed','characters'):
                for label in ('tier2','baseline','candidate'):
                    delta=800 if label=='candidate' else 0
                    for seed in range(4000,4008):
                        for seat in range(4):
                            rows.append(dict(context=c,label=label,seed=seed,seat=seat,
                                scores=[seed+delta]*4,ranks=[2.5-delta/8000]*4,
                                steps=1,trace=str(seed),decisions=1,changed=0,nodes=0))
            (folder/'matches.json').write_text(json.dumps(rows))
            result=analyze(folder)
            self.assertEqual(result['baseline_reference_pairs'],96)
            for r in result['paired']:
                v=r['metrics']['scores']['descriptive_t95']
                self.assertEqual(v['n'],8)
                self.assertEqual(v['interval'],[800,800])
                self.assertAlmostEqual(r['metrics']['ranks']['descriptive_t95']['mean'],-.1)

if __name__=='__main__':
    unittest.main()
