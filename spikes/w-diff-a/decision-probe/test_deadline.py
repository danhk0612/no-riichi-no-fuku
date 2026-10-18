"""Deliberate process stalls/failures, separate from the experiment budget."""
import multiprocessing
from pathlib import Path
import subprocess
import sys
import time
import unittest
from execute import bounded
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'backend'))
sys.path.insert(0,str(HERE.parent/'calibration'))
from run import run_jobs

def delayed(job):
    delay,value=job
    time.sleep(delay)
    return value

def failing(job):
    if job==0:raise ValueError('worker failed')
    time.sleep(30)

class DeadlineTests(unittest.TestCase):
    def test_pool_timeout_cleanup(self):
        children={p.pid for p in multiprocessing.active_children()}
        before=time.monotonic()
        with self.assertRaises(TimeoutError):
            run_jobs([(30,i) for i in range(20)],worker=delayed,workers=2,wall_budget=.15)
        self.assertLess(time.monotonic()-before,3)
        self.assertEqual({p.pid for p in multiprocessing.active_children()},children)

    def test_pool_error_cleanup(self):
        children={p.pid for p in multiprocessing.active_children()}
        with self.assertRaisesRegex(ValueError,'worker failed'):
            run_jobs(list(range(20)),worker=failing,workers=2,wall_budget=5)
        self.assertEqual({p.pid for p in multiprocessing.active_children()},children)

    def test_parent_deadline(self):
        before=time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            bounded([sys.executable,'-c','import time; time.sleep(30)'],.15)
        self.assertLess(time.monotonic()-before,3)

    def test_parent_reports_failure(self):
        with self.assertRaisesRegex(RuntimeError,'stage exited 7'):
            bounded([sys.executable,'-c','raise SystemExit(7)'],3)

if __name__=='__main__':unittest.main()
