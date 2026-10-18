"""Lossless compact evidence and exact source hashes; never runs games."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
from probe import BASE,HERE,ROOT,digest

def archive():
    directory=HERE/'evidence'
    execution=json.loads((directory/'execution.json').read_text())
    # Preserve incomplete evidence on failure; do not manufacture a successful archive.
    assert execution['status']=='passed'
    measured_sources={}
    for name in ('PLAN.md','agent.py','execute.py','probe.py','worker.py'):
        path='spikes/w-diff-a/decision-probe/'+name
        frozen=subprocess.check_output(['git','show','da07bcfafb3b755a05b758f350a602f2d99958dc:'+path],cwd=ROOT)
        assert frozen==(HERE/name).read_bytes(),('measured source changed',name)
        measured_sources[name]=hashlib.sha256(frozen).hexdigest()
    preserved={}
    entries=subprocess.check_output(['git','ls-tree','-rz',BASE],cwd=ROOT).split(b'\0')
    for entry in entries:
        if not entry:continue
        info,path=entry.decode().split('\t');mode,kind,sha=info.split()
        if path in ('ARCHITECTURE.md','CURRENT_STATE.md','TASKS.md'):continue
        local=subprocess.check_output(['git','hash-object',path],cwd=ROOT).decode().strip()
        assert local==sha,('preserved baseline changed',path)
        preserved[path]=sha
    archives={}
    for name in ('gate1','gate2','matches'):
        path=directory/f'{name}.json'
        data=json.loads(path.read_text())
        compact=json.dumps(data,separators=(',',':')).encode()
        compressed=gzip.compress(compact,mtime=0)
        target=path.with_suffix('.json.gz')
        target.write_bytes(compressed)
        assert json.loads(gzip.decompress(target.read_bytes()))==data
        archives[target.name]=dict(json_sha256=hashlib.sha256(compact).hexdigest(),
                                  gzip_sha256=hashlib.sha256(compressed).hexdigest())
        path.unlink()
    # Complete rows are retained without duplicate JSONL, whose raw hash is recorded.
    journal=directory/'matches.jsonl'
    journal_hash=hashlib.sha256(journal.read_bytes()).hexdigest()
    assert len(journal.read_text().splitlines())==1728
    journal.unlink()
    sources=dict(base=BASE,base_tree='ac4dc24e89271b9dffcee8b1f7d1a132f1ff989e',
        premeasurement_local_commit='eb4f303',published_identical_source_commit='da07bcfafb3b755a05b758f350a602f2d99958dc',
        premeasurement_tree='69efafd5417629094151868c1f628c132d531b5c',
        frozen_measured_source_sha256=measured_sources,
        scripts={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob('*.py'))},
        plan_sha256=hashlib.sha256((HERE/'PLAN.md').read_bytes()).hexdigest(),
        preserved_base_blob_hashes=preserved,lossless_archives=archives,raw_matches_jsonl_sha256=journal_hash,
        evidence_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.iterdir())
                         if p.name!='sources.json'})
    (directory/'sources.json').write_text(json.dumps(sources,indent=2)+'\n')

if __name__=='__main__':archive()
