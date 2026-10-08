"""Independent focused closeup panel frozen build with exact before/after source hashes."""
import hashlib
import gzip
import json
from pathlib import Path
from datetime import datetime, timezone
import subprocess

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent/'formal-build'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-build')
OUT.mkdir(parents=True,exist_ok=False)
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
record['dist_files']={p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'gzip_bytes':len(gzip.compress(p.read_bytes(),mtime=0)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted((ROOT/'frontend/dist').rglob('*')) if p.is_file()}
(OUT/'run.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:record[k] for k in ('exit_code','candidate_before_after_match')},ensure_ascii=False))
raise SystemExit(run.returncode)
