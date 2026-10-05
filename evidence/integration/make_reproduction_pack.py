"""Main creates an exact committed Git ZIP and approves each runtime byte representation."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[2]
GIT=['git','-c','safe.directory=D:/深度能力']
def git(*args):return subprocess.check_output(GIT+list(args),cwd=ROOT)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
    commit=git('rev-parse','HEAD').decode().strip()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    runtime=ROOT/'data/reproduction'/stamp
    runtime.mkdir(parents=True,exist_ok=False)
    archive=runtime/'source.zip'
    with archive.open('xb') as stream:subprocess.run(GIT+['archive','--format=zip',commit],cwd=ROOT,stdout=stream,check=True)
    pins={};fallbacks=[]
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            if item.is_dir():continue
            name=item.filename;blob=z.read(item)
            current=ROOT/name
            raw=current.read_bytes() if current.is_file() else blob
            mode='raw_equal';approved=blob;indices=None
            if raw!=blob:
                # Only Main chooses conversion, after proving exact raw reproduction.
                if b'\r' not in blob and blob.replace(b'\n',b'\r\n')==raw:
                    mode='main_pinned_lf_to_crlf';approved=raw
                elif raw.decode('utf-8',errors='strict').replace('\r\n','\n').encode()!=blob.decode('utf-8',errors='strict').replace('\r\n','\n').encode():
                    # Active docs may be later revisions. This package remains this commit.
                    fallbacks.append(name)
                else:
                    canonical=blob.decode('utf-8',errors='strict').replace('\r\n','\n').encode('utf-8')
                    parts=raw.split(b'\n')
                    indices=[i for i,part in enumerate(parts[:-1]) if part.endswith(b'\r')]
                    clean=canonical.split(b'\n');selected=set(indices)
                    rebuilt=b'\n'.join(part+(b'\r' if i in selected and i<len(clean)-1 else b'') for i,part in enumerate(clean))
                    assert rebuilt==raw,name
                    mode='main_pinned_line_endings';approved=raw
            pins[name]={'git_blob_sha256':sha(blob),'runtime_raw_sha256':sha(approved),'materialization':mode}
            if indices is not None:pins[name]['crlf_newline_indices']=indices
    # Critical identity references must not silently use a different representation.
    manifest=json.loads((ROOT/'evidence/integration/CH01_v2-manifest.json').read_bytes())
    for name,record in manifest['sources'].items():
        assert pins[name]['runtime_raw_sha256']==record['candidate_runtime_raw_sha256'],name
    qa_path=ROOT/'evidence/qa/T27-CH01-event-20261005T115700Z/result.json'
    qa_raw=qa_path.read_bytes()
    assert sha(qa_raw)=='958c67a1c3fb3d54e1f1af48b14cd8aa57dc1d58e66f187f0ec6e8bd3d9810e0'
    qa=json.loads(qa_raw)
    assert qa['checks']==qa['passed']==79 and not qa['failures']
    assert len(qa['sources_before'])==52 and qa['sources_before']==qa['sources_after']
    for name,digest in qa['sources_before'].items():
        assert sha((ROOT/name).read_bytes())==digest,name
        assert pins[name]['runtime_raw_sha256']==digest,name
    fixture=git('show','165a961c9d6694ceb44c88ef86c1ea28de2eae71:backend/app/storage/sqlite.py')
    assert sha(fixture)=='21d992feb895ce5535c6b0b3d731887be9619171351a551935e1d10fc2bfae22'
    fixture_path=runtime/'m2-legacy-sqlite-165a961.py';fixture_path.write_bytes(fixture)
    archive_hash=sha(archive.read_bytes())
    value={'commit':commit,'archive_sha256':archive_hash,'files':pins,'approved_by':'Main',
           'hash_policy':'Git blob bytes exact; only separately listed and proven LF->CRLF or Main-fixed newline indices restore runtime pins. Preserve BOM, EOF and every other byte. No target-controlled normalization.',
           'git_used_for_newer_uncommitted_paths':fallbacks,'created_at':datetime.now(timezone.utc).isoformat(),
           'evaluator_candidate_independent_qa':str(qa_path.relative_to(ROOT)),
           'evaluator_candidate_qa_sha256':sha(qa_raw),'evaluator_source_count':52}
    path=ROOT/f'evidence/integration/reproduction-{stamp}-pins.json'
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    descriptor={'commit':commit,'archive':str(archive),'archive_sha256':archive_hash,'members':len(pins),
                'pins':str(path),'pins_sha256':sha(path.read_bytes()),'legacy_fixture':str(fixture_path),
                'workspace':str(runtime/'clean'),'output':str(ROOT/f'evidence/delivery/T32-clean-{stamp}'),
                'helper_raw_sha256':sha((ROOT/'scripts/reproduce.py').read_bytes()),'nonsecret_only':True,'actual_paid_calls':0,
                'scope':'Committed source reproduced in a new directory using existing Conda; no clean-OS/environment claim.'}
    (ROOT/f'evidence/integration/reproduction-{stamp}-handoff.json').write_text(json.dumps(descriptor,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(descriptor,ensure_ascii=False))
if __name__=='__main__':main()
