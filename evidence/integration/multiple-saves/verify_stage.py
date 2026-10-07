"""Main integration operator for frozen independent build/browser evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument('stage', choices=['build', 'browser'])
options = parser.parse_args()
candidate_path = ROOT / 'evidence/integration/multiple-saves/candidate.json'
candidate = json.loads(candidate_path.read_text(encoding='utf-8'))
def hashes():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in candidate['source_sha256']}
before = hashes()
assert before == candidate['source_sha256'], 'Frozen candidate changed'
folder = ROOT / 'evidence/integration/multiple-saves/qa' / ('formal-build' if options.stage == 'build' else 'browser-console')
folder.mkdir(parents=True, exist_ok=True)
assert not (folder / 'run.json').exists(), 'Preserve prior completed stage evidence'
command = (['C:/Program Files/nodejs/npm.cmd', 'run', 'build', '--prefix', 'frontend'] if options.stage == 'build'
           else ['C:/Program Files/nodejs/node.exe', 'tests/e2e/run_multiple_saves.mjs', 'evidence/integration/multiple-saves/candidate.json'])
started = datetime.now(timezone.utc).isoformat()
environment = dict(os.environ)
environment.update(AI_PROVIDER='mock', PYTHONUTF8='1')
result = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
(folder / 'stdout.txt').write_text(result.stdout, encoding='utf-8')
(folder / 'stderr.txt').write_text(result.stderr, encoding='utf-8')
after = hashes()
record = {'execution_owner':'Main integration operates previously QA-authored frozen tests', 'stage':options.stage,
          'candidate':'evidence/integration/multiple-saves/candidate.json', 'command':command,
          'started':started, 'ended':datetime.now(timezone.utc).isoformat(), 'exit_code':result.returncode,
          'public_environment':{'AI_PROVIDER':'mock','PYTHONUTF8':'1'}, 'source_sha256_before':before,
          'source_sha256_after':after, 'candidate_before_after_match':before == after == candidate['source_sha256'],
          'paid_calls':0, 'phaser_added':False}
(folder / 'run.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'stage':options.stage,'exit_code':result.returncode,'candidate_before_after_match':record['candidate_before_after_match'],'evidence':str(folder)}, ensure_ascii=False))
print(result.stdout[-1600:])
if result.stderr: print(result.stderr[-800:])
raise SystemExit(result.returncode if record['candidate_before_after_match'] else 2)
