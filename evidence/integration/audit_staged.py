"""Inspect staged bytes without printing potential secret values; main integration tool."""
import json
from pathlib import PurePosixPath
import re
import subprocess
import sys

GIT = ['git', '-c', 'safe.directory=D:/深度能力']
paths = subprocess.check_output(GIT + ['diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z']).decode('utf-8').split('\0')
patterns = {
    'github_token': re.compile(rb'gh[pousr]_[A-Za-z0-9_]{30,}'),
    'api_key': re.compile(rb'sk-[A-Za-z0-9]{28,}'),
    'session_capability': re.compile(rb'"token"\s*:\s*"[A-Za-z0-9_-]{32,}"'),
    'private_key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
}
failures = []
count = 0
for path in filter(None, paths):
    count += 1
    parts = PurePosixPath(path).parts
    forbidden = any(p in {'.git', 'node_modules', '.venv', 'venv', 'envs', '.conda', 'data', 'raw-sensitive'} for p in parts)
    forbidden |= path.rsplit('/', 1)[-1].startswith('.env') and path.rsplit('/', 1)[-1] != '.env.example'
    forbidden |= path.endswith(('.db', '.sqlite', '.sqlite3', '.sqlite-wal', '.sqlite-shm', '.log', '.pem', '.key'))
    if forbidden:
        failures.append({'path': path, 'rule': 'forbidden_runtime_or_secret_path'})
        continue
    content = subprocess.check_output(GIT + ['show', ':' + path])
    if content.startswith(b'SQLite format 3'):
        failures.append({'path': path, 'rule': 'database_bytes'})
    for rule, pattern in patterns.items():
        if pattern.search(content):
            failures.append({'path': path, 'rule': rule})
print(json.dumps({'scope': 'staged bytes, selected credential patterns and runtime paths; not exhaustive security proof', 'staged_files': count, 'findings': failures, 'exit_code': 1 if failures else 0}, ensure_ascii=False, indent=2))
sys.exit(1 if failures else 0)
