"""Append sanitized evidence and hashes for an explicitly authorized stable candidate."""
import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def sources():
    files = []
    for directory in ['backend/app', 'contracts', 'tests']:
        files += [p for p in (ROOT / directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and 'node_modules' not in p.parts and p.suffix in {'.py', '.json', '.mjs'} and not p.relative_to(ROOT).as_posix().startswith('backend/app/ai/')]
    files += [ROOT / n for n in ['AGENTS.md', 'docs/SPEC.md', 'docs/level_design.md', 'backend/requirements.lock.txt']]
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files) if p.exists()}


def git_read(*args):
    result = subprocess.run(['git', '-c', f'safe.directory={ROOT.as_posix()}', *args], cwd=ROOT, text=True, capture_output=True)
    return {'exit_code': result.returncode, 'output': result.stdout.strip() if result.returncode == 0 else 'Git metadata unavailable'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output', default='evidence/qa')
    args = parser.parse_args()
    folder = ROOT / args.output / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-r1-api')
    folder.mkdir(parents=True, exist_ok=False)
    before = sources()
    start = datetime.now(timezone.utc).isoformat()
    stream, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(stderr):
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('tests.api.test_r1'))
    from tests.api.test_r1 import EXCHANGES, sanitize
    raw = sanitize(stream.getvalue())
    (folder / 'unittest-output.txt').write_text(raw, encoding='utf-8')
    (folder / 'stderr.txt').write_text(sanitize(stderr.getvalue()), encoding='utf-8')
    (folder / 'http-exchanges.json').write_text(json.dumps(EXCHANGES, ensure_ascii=False, indent=2), encoding='utf-8')
    after = sources()
    code = 0 if result.wasSuccessful() and before == after else 1
    metadata = {'candidate': args.candidate, 'target': 'M1 working-tree backend candidate; frontend and independent backend/app/ai provider probe excluded, no AI calls in M1', 'head': git_read('rev-parse', 'HEAD'), 'working_tree': git_read('status', '--short'), 'start': start, 'end': datetime.now(timezone.utc).isoformat(), 'command': [sys.executable, '-m', 'tests.qa_runner', *sys.argv[1:]], 'python': sys.version, 'provider': 'mock explicitly; no model invocation', 'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped), 'source_sha256_before': before, 'source_sha256_after': after, 'source_changed_during_run': before != after, 'exit_code': code, 'evidence_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}, 'sanitization': 'No headers/database copied; token keys and known token values redacted.'}
    (folder / 'run.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print(raw, end='')
    print('Evidence:', folder)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
