"""One frozen-source frontend build with exact output and before/after hashes."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
candidate_path=ROOT/'evidence/integration/handpainted/candidate.json'
candidate=json.loads(candidate_path.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
protocol=json.loads((ROOT/'evidence/integration/handpainted/qa/preparation.json').read_text(encoding='utf-8'))
assert protocol['protocol_ready']
before={p:sha(p) for p in candidate['source_sha256']}
assert before==candidate['source_sha256']
folder=ROOT/'evidence/integration/handpainted/qa'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'-build')
folder.mkdir(parents=True)
command=['npm.cmd','run','build']
completed=subprocess.run(command,cwd=ROOT/'frontend',capture_output=True,text=True,encoding='utf-8',errors='replace')
(folder/'output.txt').write_text(completed.stdout+completed.stderr,encoding='utf-8')
after={p:sha(p) for p in candidate['source_sha256']}
code=completed.returncode if completed.returncode else int(before!=after)
result={'command':command,'cwd':str(ROOT/'frontend'),'exit_code':code,'process_exit_code':completed.returncode,'candidate':'evidence/integration/handpainted/candidate.json','candidate_sha256':hashlib.sha256(candidate_path.read_bytes()).hexdigest(),'source_sha256_before':before,'source_sha256_after':after,'output':'output.txt'}
(folder/'run.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'evidence':str(folder),'exit_code':code}))
sys.exit(code)
