"""Independent full API revalidation; compact evidence, no real calls or state export."""
import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
CANDIDATE = Path('evidence/upgrade/v3.4/candidate.json')
os.chdir(ROOT)
candidate = json.loads(CANDIDATE.read_text(encoding='utf-8'))

def hashes(paths):
    return {str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}

def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

before = hashes(candidate['source_sha256'])
tests_before = hashes(sorted(str(p).replace('\\', '/') for p in Path('tests/api').glob('*.py')))
record = {
    'candidate': str(CANDIDATE).replace('\\', '/'),
    'started': datetime.now(timezone.utc).isoformat(),
    'command': [sys.executable, '-B', '-X', 'utf8', str(Path(__file__).relative_to(ROOT)).replace('\\', '/')],
    'pytest_arguments': ['tests/api', '-q', '--tb=short', '-p', 'no:cacheprovider'],
    'source_sha256_before': before,
    'test_sha256_before': tests_before,
    'candidate_before_match': before == candidate['source_sha256'],
    'environment': {'AI_PROVIDER': 'mock', 'GAMEPLAY_VERSION': 'legacy', 'SQLITE_PATH': '<QA-owned temporary import SQLite>'},
    'paid_calls': 0,
    'evidence_policy': 'Sanitized stdout and compact CHECKS34 only; no full-state or token exports',
}
if not record['candidate_before_match']:
    record.update(exit_code=2, status='Not run: frozen candidate mismatch')
    save('run.json', record)
    raise SystemExit(2)
stream = io.StringIO()
with tempfile.TemporaryDirectory(prefix='campus-qa-v34-formal-') as temporary:
    os.environ.update(AI_PROVIDER='mock', GAMEPLAY_VERSION='legacy', SQLITE_PATH=str(Path(temporary) / 'import.sqlite'))
    import pytest
    with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        code = int(pytest.main(record['pytest_arguments']))
    from tests.api.test_r1 import sanitize
    from tests.api.test_upgrade_v34 import CHECKS34
    stdout = sanitize(stream.getvalue())
    stdout = '\n'.join('E   AssertionError: full public-state response omitted; actual status/error and compact checks retained' if 'AssertionError:' in line and "'visible_state':" in line else line for line in stdout.splitlines()) + '\n'
    (OUT / 'stdout.txt').write_text(stdout, encoding='utf-8')
    save('checks.json', CHECKS34)
after = hashes(candidate['source_sha256'])
tests_after = hashes(tests_before)
record.update(
    ended=datetime.now(timezone.utc).isoformat(), exit_code=code,
    source_sha256_after=after, test_sha256_after=tests_after,
    candidate_after_match=after == candidate['source_sha256'],
    source_before_after_match=before == after,
    tests_before_after_match=tests_before == tests_after,
    checks_count=len(CHECKS34),
)
save('run.json', record)
print(stdout, end='')
print(json.dumps({k: record[k] for k in ('exit_code', 'candidate_before_match', 'candidate_after_match', 'source_before_after_match', 'tests_before_after_match', 'checks_count')}, ensure_ascii=False))
raise SystemExit(code)