"""Own one overall deadline; preserve failed gates and partial comparisons."""
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
from validate import HERE, digest
from execute import bounded

def main():
    folder = HERE/'evidence'
    if folder.exists():
        raise RuntimeError('evidence exists; no experiment retry')
    folder.mkdir()
    started = time.monotonic()
    deadline = started+1200
    report = dict(base='4c883a085e24aff1d9e0da7457315588be7f21f9', planned_matches=288,
                  wall_budget_s=1200, stages=[], status='running')
    try:
        for stage in ('gate1','gate2','matches','reproduce','replay'):
            remaining = deadline-time.monotonic()
            if remaining<=0:
                raise TimeoutError('overall research deadline')
            report['active_stage'] = stage
            before = time.monotonic()
            if stage.startswith('gate') or stage=='replay':
                command = [sys.executable, str(HERE/'validate.py'), 'gate' if stage.startswith('gate') else 'replay',
                           str(folder/f'{stage}.json')]
            else:
                command = [sys.executable, str(HERE/'compare.py'), stage, str(folder), str(remaining)]
            bounded(command, remaining)
            report['stages'].append(dict(name=stage, elapsed_s=time.monotonic()-before))
            print(json.dumps(report['stages'][-1]), flush=True)
            if stage=='gate2':
                a=json.loads((folder/'gate1.json').read_text());a.pop('timings')
                b=json.loads((folder/'gate2.json').read_text());b.pop('timings')
                assert a==b, 'independent gate results differ'
                report['gate_sha256'] = digest(a)
        assert time.monotonic()<=deadline
        report['status'] = 'passed'
    except BaseException:
        report['status'] = 'stopped'
        report['failure'] = traceback.format_exc()
    finally:
        report['elapsed_s'] = time.monotonic()-started
        journal = folder/'matches.jsonl'
        report['completed_matches'] = len(journal.read_text().splitlines()) if journal.exists() else 0
        report['uncompleted_matches'] = 288-report['completed_matches']
        (folder/'execution.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2), flush=True)
    return 0 if report['status']=='passed' else 1

if __name__ == '__main__':
    sys.exit(main())
