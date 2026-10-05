"""Main-owned raw-byte archive; neither executes target code nor copies secrets."""
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
GAME = '7821af4efe0613c20a80ea164c1dab1c0f288bab'
EXPERIMENT = 'd20a1f17e121dcd672e4af1196699618fa5ba818'
FORMAL = 'experiments/runs/20261005T053334004502Z-formal-real-48d972eb'
DEST = 'release/archives/baseline_v1'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def git(*args):
    return subprocess.check_output(['git', '-c', 'safe.directory=D:/深度能力', *args], cwd=ROOT)

def main():
    baseline = json.loads((ROOT/'evidence/integration/baseline_v1-manifest.json').read_text(encoding='utf-8'))
    plan = json.loads((ROOT/FORMAL/'plan.json').read_text(encoding='utf-8'))
    expected = {p: (s['candidate_runtime_raw_sha256'], GAME) for p, s in baseline['sources'].items()}
    for p, h in plan['freeze']['source_hashes'].items():
        if p in expected and expected[p][0] != h:
            raise ValueError('conflicting frozen raw identity: '+p)
        expected.setdefault(p, (h, EXPERIMENT))
    records = {}
    # Validate every source before making the first archive write.
    for p, (h, commit) in sorted(expected.items()):
        rel = PurePosixPath(p)
        if rel.is_absolute() or '..' in rel.parts or ':' in p or any(x in {'.env','node_modules','data','.git'} for x in rel.parts):
            raise ValueError('unapproved source: '+p)
        source = ROOT/p
        if source.is_symlink() or any(x.is_symlink() or getattr(x.lstat(), 'st_file_attributes', 0) & 0x400 for x in [source, *source.parents] if x.exists()):
            raise ValueError('reparse source: '+p)
        raw = source.read_bytes()
        raw.decode('utf-8', errors='strict')
        blob = git('show', commit+':'+p)
        canonical = raw.decode('utf-8').replace('\r\n', '\n').encode('utf-8')
        if sha(raw) != h or canonical != blob.decode('utf-8').replace('\r\n', '\n').encode('utf-8'):
            raise ValueError('source identity mismatch: '+p)
        target = ROOT/DEST/p
        if target.exists() and target.read_bytes() != raw:
            raise ValueError('existing archive mismatch: '+p)
        records[p] = {'archive_release_id': 'baseline_v1', 'archive_path': DEST+'/'+p,
                      'raw_sha256': h, 'git_source_commit': commit,
                      'git_blob_oid': git('rev-parse', commit+':'+p).decode().strip(),
                      'git_blob_sha256': sha(blob), 'utf8_lf_v1_sha256': sha(canonical),
                      'binding': 'raw_equal' if raw == blob else 'approved_crlf_to_lf_only'}
    for p, record in records.items():
        target = ROOT/record['archive_path']
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes((ROOT/p).read_bytes())
        if sha(target.read_bytes()) != record['raw_sha256']:
            raise ValueError('archive verification failed: '+p)
    output = ROOT/'evidence/integration/E1-source-archive-20261005.json'
    if output.exists():
        raise ValueError('append-only archive record already exists')
    record = {'created_at': datetime.now(timezone.utc).isoformat(), 'approved_by': 'Main',
              'archive_release_id': 'baseline_v1', 'product_commit': GAME,
              'experiment_commit': EXPERIMENT, 'count': len(records), 'sources': records,
              'formal_plan_raw_sha256': sha((ROOT/FORMAL/'plan.json').read_bytes()),
              'baseline_manifest_raw_sha256': sha((ROOT/'evidence/integration/baseline_v1-manifest.json').read_bytes()),
              'scope': 'Exact raw bytes checked against frozen runtime maps, copied before CH01. Archives were not executed. Git identity refers to original source commits; archived Git files may use explicitly approved CRLF-to-LF normalization.'}
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'count': len(records), 'record': str(output), 'raw_sha256': sha(output.read_bytes())}, ensure_ascii=False))

if __name__ == '__main__':
    main()
