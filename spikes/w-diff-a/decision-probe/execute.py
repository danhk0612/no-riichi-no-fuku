"""Single 20-minute deadline for both gates, games, trace and saved replay."""
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent

def bounded(command,remaining):
    process=subprocess.Popen(command,start_new_session=True)
    try:
        code=process.wait(timeout=max(0,remaining))
        if code:raise RuntimeError(f'stage exited {code}: {command}')
    finally:
        # Also terminate descendants if the stage exits before its workers.
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        process.wait()

def main():
    directory=HERE/'evidence'
    if any(directory.glob('gate*.json')) or (directory/'execution.json').exists():
        raise RuntimeError('evidence already exists; no experiment retry')
    started=time.monotonic();deadline=started+1200
    status=dict(base='e8a70b57db22727a861956ae6ee42c087057f6b8',
                python=platform.python_version(),platform=platform.platform(),
                workers=8,wall_budget_s=1200,planned_matches=1728,stages=[])
    try:
        for name in ('gate1','gate2','matches','reproduce','replay'):
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('overall deadline')
            before=time.monotonic()
            status['active_stage']=name
            command=([sys.executable,str(HERE/'probe.py'),'gate',str(directory/f'{name}.json')]
                     if name.startswith('gate') else
                     [sys.executable,str(HERE/'worker.py'),name,str(directory),str(remaining)])
            bounded(command,remaining)
            if name=='gate2':
                a=json.loads((directory/'gate1.json').read_text());a.pop('timings')
                b=json.loads((directory/'gate2.json').read_text());b.pop('timings')
                assert a==b,'independent gate differs'
                status['independent_gate_sha256']=hashlib.sha256(json.dumps(a,sort_keys=True).encode()).hexdigest()
            status['stages'].append(dict(name=name,elapsed_s=time.monotonic()-before))
            print(json.dumps(status['stages'][-1]),flush=True)
        assert time.monotonic()<=deadline
        status['status']='passed'
    except BaseException:
        status['status']='stopped'
        status['failure']=traceback.format_exc()
        print(status['failure'],flush=True)
    finally:
        status['elapsed_s']=time.monotonic()-started
        partial=directory/'matches.jsonl'
        status['completed_matches']=len(partial.read_text().splitlines()) if partial.exists() else 0
        status['uncompleted_matches']=1728-status['completed_matches']
        (directory/'execution.json').write_text(json.dumps(status,indent=2)+'\n')
    return 0 if status['status']=='passed' else 1

if __name__=='__main__':sys.exit(main())
