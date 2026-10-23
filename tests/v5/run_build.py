"""One candidate-bound V5 production build, invoked only after formal GO."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.dev import npm_command
from scripts.run_v5 import frontend_environment
from scripts.check_v5 import source_hashes,safe_text

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    candidate=json.loads(args.candidate.read_text(encoding='utf-8-sig'))
    expected=candidate.get('source_sha256',candidate.get('source_hashes',{}))
    if not expected: raise ValueError('Nonempty candidate source map is required')
    sha=lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    before={p:sha(p) for p in expected}
    command=npm_command('--prefix','frontend','run','build')
    report={'candidate':str(args.candidate),'candidate_sha256':hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
            'command':command,'started':datetime.now(timezone.utc).isoformat(),'source_before':before,
            'build_environment':{'VITE_GAMEPLAY_VERSION':'v5','CAMPUS_BACKEND_URL':'http://127.0.0.1:8001'},
            'paid_calls':0,'process_exit_code':None,'limitations':['Build/typecheck only; not browser or real AI evidence.']}
    code=1;output=''
    try:
        if before!=expected: raise ValueError('Candidate does not match before build')
        completed=subprocess.run(command,cwd=ROOT,env=frontend_environment(os.environ.copy(),'http://127.0.0.1:8001'),capture_output=True,timeout=120)
        code=completed.returncode;report['process_exit_code']=code
        output=safe_text((completed.stdout+completed.stderr).decode('utf-8',errors='replace'))
    except subprocess.TimeoutExpired as error:
        code=124;output=safe_text((error.stdout or b'').decode('utf-8',errors='replace'))+'\n[build timeout]\n'
    except Exception as error: report['error']=str(error)
    after={p:sha(p) for p in expected};report.update(source_after=after,source_unchanged=before==after,
        ended=datetime.now(timezone.utc).isoformat(),exit_code=code if code else int(before!=after))
    (args.output/'output.txt').write_text(output,encoding='utf-8')
    (args.output/'run.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'evidence':str(args.output),'exit_code':report['exit_code']}));return report['exit_code']

if __name__=='__main__':raise SystemExit(main())
