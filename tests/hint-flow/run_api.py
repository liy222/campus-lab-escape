"""Frozen-candidate execution wrapper; retains every distinct run directory."""
from pathlib import Path
import hashlib
import io
import json
import subprocess
import sys
import unittest
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    candidate_path = sys.argv[1]
    candidate = json.loads((ROOT / candidate_path).read_text(encoding='utf-8-sig'))
    source = candidate['source_sha256']
    before = {p: digest(p) for p in source}
    assert before == source, 'Frozen candidate mismatch before API execution'
    prep = json.loads((ROOT / 'evidence/integration/hint-flow/qa/preparation.json').read_text(encoding='utf-8'))
    assert prep['protocol_ready'], 'QA protocol not ready'
    assert all(digest(p) == h for p, h in prep['old_test_sha256'].items())
    folder = ROOT / 'evidence/integration/hint-flow/qa' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-api')
    folder.mkdir(parents=True)
    from tests.api import test_hint_flow as new
    from tests.api import test_upgrade_v34 as old
    from tests.api import test_r1 as capture
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(new)])
    for name in prep['selected_old_methods']:
        suite.addTest(old.UpgradeV34Acceptance(name))
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    after = {p: digest(p) for p in source}
    old_match = all(digest(p) == h for p, h in prep['old_test_sha256'].items())
    code = 0 if result.wasSuccessful() and before == after and old_match else 1
    (folder / 'unittest.txt').write_text(output.getvalue(), encoding='utf-8')
    (folder / 'checks.json').write_text(json.dumps(new.RECORDS, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (folder / 'http.json').write_text(json.dumps([x for x in capture.EXCHANGES if x['path'].endswith('/ai/turns')], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    payload = {'candidate': candidate_path, 'command': [sys.executable, '-B', '-X', 'utf8', *sys.argv], 'exit_code': code, 'methods': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'source_sha256_before': before, 'source_sha256_after': after, 'old_tests_unchanged': old_match, 'selected_old_methods': prep['selected_old_methods'], 'excluded_old_assertions': prep['excluded_old_assertions'], 'qa_script_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__).resolve(), ROOT / 'tests/api/test_hint_flow.py')}, 'paid_calls': 0, 'limitations': ['Isolated fresh temporary SQLite fixtures; historical user saves/databases are not accessed.', 'Synthetic provider branches test authority/failures, not real-provider quality.', 'No full old backend suite; changed initial NO_HINT contract is deliberately not run.']}
    (folder / 'run.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(output.getvalue())
    print(json.dumps({'evidence': str(folder), 'exit_code': code, 'methods': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors)}))
    return code


if __name__ == '__main__':
    sys.exit(main())
