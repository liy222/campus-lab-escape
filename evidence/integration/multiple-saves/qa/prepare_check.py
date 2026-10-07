"""Static QA preparation only; never imports product or executes acceptance."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
record=read('evidence/integration/multiple-saves/qa/preparation.json')
old=read('evidence/upgrade/v3.4/qa/formal-api-directed-20261007/run.json')['test_sha256_after']
old.update({item['path']:item['sha256'] for item in read('evidence/upgrade/v3.4/qa/preparation.json')['old_file_checks']})
old['tests/e2e/run_upgrade_v34.mjs']='6317c927e7dfbb7ff9ddf5625b589b77149fde1e7b5b480b6bac65832939de88'
assert all(sha(path)==value for path,value in old.items()),'Old API/runner bytes changed'
prepared=['tests/api/test_multiple_saves.py','tests/e2e/run_multiple_saves.mjs',
          'evidence/integration/multiple-saves/qa/formal-api/runner.py']
methods=[]
for path in prepared:
    if not path.endswith('.py'):continue
    tree=ast.parse((ROOT/path).read_text(encoding='utf-8'))
    methods.extend(n.name for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_'))
node=['C:/Program Files/nodejs/node.exe','--check','tests/e2e/run_multiple_saves.mjs']
result=subprocess.run(node,cwd=ROOT,text=True,capture_output=True)
assert result.returncode==0,result.stderr
record.update(status='QA PREPARATION SOURCE STOP; protocol implemented in tests, formal waits frozen candidate/Main GO',
    recorded_at=datetime.now(timezone.utc).isoformat(),formal_runs=0,
    prepared_files=[{'path':p,'sha256':sha(p)} for p in prepared],new_api_methods=methods,
    old_file_checks=[{'path':p,'sha256':v,'matches_v34_sealed_raw_hash':True} for p,v in old.items()],
    static_commands=[{'command':[sys.executable,'-B','-X','utf8',str(Path(__file__).relative_to(ROOT)).replace('\\','/')],
        'script_sha256':sha(str(Path(__file__).relative_to(ROOT))),'exit_code':0,
        'scope':'AST parse new API/wrapper and exact raw-byte hashes of old API/runner only'},
        {'command':node,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr}],
    protocol_pending=['Final candidate raw hashes and overall SOURCE STOP/Main GO; frontend final stable DOM notification'],
    scope_limits=['No formal API/build/browser executed during this preparation.','Mock/stub and owned synthetic SQLite only.',
        'No product changes, old test edits, spawn, paid call, commit or Phaser/v4 work.'])
(OUT/'preparation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':record['status'],'static_exit_code':0,'new_methods':len(methods),'old_files_unchanged':len(old),'formal_runs':0},ensure_ascii=False))
