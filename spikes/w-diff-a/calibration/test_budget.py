"""Fault checks for the research runner's finite process lifetime."""
import multiprocessing
import time
import unittest
from run import run_jobs

def delayed(job):
    delay, result = job
    time.sleep(delay)
    return result

def failing(job):
    if job == 0:
        raise ValueError('worker failed')
    time.sleep(30)

class BudgetTests(unittest.TestCase):
    def test_submission_order(self):
        self.assertEqual(run_jobs([(.05, 1), (0, 2)], worker=delayed,
                                  workers=2, wall_budget=5), [1, 2])

    def test_stalled_first_job_terminates_running_and_queued_work(self):
        before = time.monotonic()
        children = {p.pid for p in multiprocessing.active_children()}
        with self.assertRaisesRegex(TimeoutError, 'wall budget'):
            run_jobs([(30, i) for i in range(20)], worker=delayed,
                     workers=2, wall_budget=.15)
        self.assertLess(time.monotonic() - before, 3)
        self.assertEqual({p.pid for p in multiprocessing.active_children()}, children)

    def test_worker_failure_terminates_other_work(self):
        before = time.monotonic()
        children = {p.pid for p in multiprocessing.active_children()}
        with self.assertRaisesRegex(ValueError, 'worker failed'):
            run_jobs(list(range(20)), worker=failing, workers=2, wall_budget=5)
        self.assertLess(time.monotonic() - before, 3)
        self.assertEqual({p.pid for p in multiprocessing.active_children()}, children)

if __name__ == '__main__':
    unittest.main()
