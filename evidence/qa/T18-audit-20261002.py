"""Read-only post-run evidence/key scan; no Provider/HTTP/ledger writes."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from backend.app.ai.provider import DeepSeekConfig
key=DeepSeekConfig.from_environment().api_key
assert key.strip(), 'Cannot perform actual-key equality scan without current configuration'
accepted=['20261002T120504699455Z-m3-api','20261002T115503579Z-m3-browser','20261002T115601621Z-m2-browser','20261002T120735404563Z-m3-real']
checks=[]
for name in accepted:
    folder=ROOT/'evidence/qa'/name
    run=json.loads((folder/'run.json').read_text(encoding='utf-8'))
    assert run['exit_code']==0
    assert run['source_sha256_before']==run['source_sha256_after']
    hashes=run['evidence_sha256']
    assert all(hashlib.sha256((folder/file).read_bytes()).hexdigest()==expected for file,expected in hashes.items())
    checks.append({'run':name,'exit_code':run['exit_code'],'source_unchanged':True,'evidence_hashes_verified':len(hashes)})
summary_path=ROOT/'evidence/qa/check/20261002T120553.430164Z-b81339d5/summary.json'
summary=json.loads(summary_path.read_text(encoding='utf-8'))
assert summary['exit_code']==0 and summary['source_unchanged']
assert all(hashlib.sha256((ROOT/file).read_bytes()).hexdigest()==expected for file,expected in summary['source_hashes'].items())
checks.append({'current_all_checker_sources_match':True,'source_count':len(summary['source_hashes']),'steps':[{'name':s['name'],'exit_code':s['exit_code']} for s in summary['steps']]})
scanned=[]
for base in ['frontend/dist','backend/app','frontend/src','scripts','contracts','tests','evidence/qa']:
    for file in (ROOT/base).rglob('*'):
        if file.is_file() and '__pycache__' not in file.parts and file.suffix.lower() in {'.py','.json','.txt','.mjs','.ts','.tsx','.css','.html','.md'}:
            # Exact comparison in memory; no key/digest/length in output.
            assert key not in file.read_text(encoding='utf-8',errors='replace'), 'Actual configured key found in public/source/evidence scope'
            scanned.append(file.relative_to(ROOT).as_posix())
git=subprocess.run(['git','-c',f'safe.directory={ROOT.as_posix()}','ls-files','-z'],cwd=ROOT,capture_output=True)
assert git.returncode==0
tracked=[name for name in git.stdout.decode('utf-8').split('\0') if name]
for name in tracked:
    p=Path(name)
    assert p.name!='.env' and p.suffix.lower() not in {'.sqlite','.sqlite3','.db'} and not {'node_modules','.venv','venv'}&set(p.parts), 'Sensitive runtime path is tracked'
result={'command':[sys.executable,str(Path(__file__).resolve())],'actual_exit_code':0,'checks':checks,'exact_actual_configured_key_scan':{'passed':True,'files_scanned':len(scanned),'roots':['frontend/dist','backend/app','frontend/src','scripts','contracts','tests','evidence/qa']},'tracked_sensitive_runtime_paths':0,'limitations':'Exact configured key and known session-capability probes only; not a proof against arbitrary future secrets or covert channels. No credentials/providerbody/headers copied.'}
(ROOT/'evidence/qa/T18-audit-20261002.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'actual_exit_code':0,'evidence':'evidence/qa/T18-audit-20261002.json','accepted_runs_verified':len(checks)-1,'exact_key_scan_files':len(scanned)}))
