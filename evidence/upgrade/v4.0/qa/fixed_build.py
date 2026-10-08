"""Independent final candidate build with exact before/after source hashes."""
import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent/'fixed-build'
OUT.mkdir(exist_ok=True)
import sys
if len(sys.argv)!=2:raise SystemExit('Pass frozen Main candidate JSON explicitly')
CANDIDATE=Path(sys.argv[1])
candidate=json.loads((ROOT/CANDIDATE).read_text(encoding='utf-8-sig'))
def hashes():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in candidate['source_sha256']}
before=hashes()
assert before==candidate['source_sha256'],'Candidate mismatch; not running build'
command=['C:/Program Files/nodejs/npm.cmd','run','build','--prefix','frontend']
started=datetime.now(timezone.utc).isoformat()
run=subprocess.run(command,cwd=ROOT,text=True,encoding='utf-8',errors='replace',capture_output=True)
(OUT/'stdout.txt').write_text(run.stdout+run.stderr,encoding='utf-8')
after=hashes()
record={'candidate':str(CANDIDATE).replace('\\','/'),'command':command,'exit_code':run.returncode,
        'started':started,'ended':datetime.now(timezone.utc).isoformat(),
        'source_sha256_before':before,'source_sha256_after':after,
        'candidate_before_after_match':before==after==candidate['source_sha256']}
(OUT/'run.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:record[k] for k in ('exit_code','candidate_before_after_match')},ensure_ascii=False))
raise SystemExit(run.returncode)
