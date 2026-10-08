"""Independent targeted API/state binding to v4.1 frozen R2 candidate; compact evidence, no real calls or state export."""
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
if len(sys.argv) != 2:
    raise SystemExit('Pass Main frozen candidate JSON explicitly')
CANDIDATE = Path(sys.argv[1])
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
    'command': [sys.executable, '-B', '-X', 'utf8', str(Path(__file__).relative_to(ROOT)).replace('\\', '/'), str(CANDIDATE).replace('\\', '/')],
    'pytest_arguments': ['tests/api/test_upgrade_v34.py::UpgradeV34Acceptance::test_three_levels_only_known_context_no_auto_inspect_no_private_full_solution', 'tests/api/test_upgrade_v34.py::UpgradeV34Acceptance::test_meaningful_numeric_login_circuit_sequence_wrong_item_count_once_only', 'tests/api/test_upgrade_v34.py::UpgradeV34Acceptance::test_optional_story_objects_visibility_discoveries_total_ten_and_win_score', 'tests/api/test_upgrade_v34.py::UpgradeV34Acceptance::test_server_UTC_offline_elapsed_reset_saved_run_restore_and_win_freeze', 'tests/api/test_multiple_saves.py::MultipleSavesAcceptance::test_append_immutable_three_moments_restore_stats_reset_and_reopen', 'tests/api/test_multiple_saves.py::MultipleSavesAcceptance::test_selected_restore_expires_pending_mock_hint_without_stats_mutation', '-q', '--tb=short', '-p', 'no:cacheprovider'],
    'source_sha256_before': before,
    'test_sha256_before': tests_before,
    'candidate_before_match': before == candidate['source_sha256'],
    'environment': {'AI_PROVIDER': 'mock', 'GAMEPLAY_VERSION': 'legacy', 'SQLITE_PATH': '<QA-owned temporary import SQLite>'},
    'paid_calls': 0,
    'evidence_policy': 'Sanitized stdout and compact CHECKS_SAVES only; no full-state or token exports',
}
if not record['candidate_before_match']:
    record.update(exit_code=2, status='Not run: frozen candidate mismatch')
    save('run.json', record)
    raise SystemExit(2)
stream = io.StringIO()
with tempfile.TemporaryDirectory(prefix='campus-qa-v41-formal-') as temporary:
    os.environ.update(AI_PROVIDER='mock', GAMEPLAY_VERSION='legacy', SQLITE_PATH=str(Path(temporary) / 'import.sqlite'))
    import pytest
    with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        code = int(pytest.main(record['pytest_arguments']))
    from tests.api.test_r1 import sanitize
    from tests.api.test_multiple_saves import CHECKS_SAVES
    stdout = sanitize(stream.getvalue())
    stdout = '\n'.join('E   AssertionError: full public-state response omitted; actual status/error and compact checks retained' if 'AssertionError:' in line and "'visible_state':" in line else line for line in stdout.splitlines()) + '\n'
    (OUT / 'stdout.txt').write_text(stdout, encoding='utf-8')
    save('checks.json', CHECKS_SAVES)
after = hashes(candidate['source_sha256'])
tests_after = hashes(tests_before)
record.update(
    ended=datetime.now(timezone.utc).isoformat(), exit_code=code,
    source_sha256_after=after, test_sha256_after=tests_after,
    candidate_after_match=after == candidate['source_sha256'],
    source_before_after_match=before == after,
    tests_before_after_match=tests_before == tests_after,
    checks_count=len(CHECKS_SAVES),
)
save('run.json', record)
print(stdout, end='')
print(json.dumps({k: record[k] for k in ('exit_code', 'candidate_before_match', 'candidate_after_match', 'source_before_after_match', 'tests_before_after_match', 'checks_count')}, ensure_ascii=False))
raise SystemExit(code)