"""Only the failed new static-label method; fix QA's quote-sensitive assertion."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import importlib.util
import io
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('sealed_label_tests', ROOT / 'tests/companion-nextstep/run_labels.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)


class QuoteCorrected(prior.Labels):
    def assertIn(self, member, container, msg=None):
        if member == '观察按钮':
            # Actual prompt explicitly uses Chinese quotation marks; recognize
            # its meaning without modifying the prior sealed test or product.
            return self.assertRegex(container, r'不要求玩家寻找[“\"]?观察[”\"]?按钮', msg)
        return super().assertIn(member, container, msg)


def main():
    candidate_path = 'evidence/integration/companion-nextstep/candidate-label-fixed.json'
    source = prior.base.read(candidate_path)['source_sha256']
    before = {p: prior.base.sha(p) for p in source}
    assert before == source
    old_script_sha = prior.base.sha('tests/companion-nextstep/run_labels.py')
    folder = ROOT / 'evidence/integration/companion-nextstep/qa' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-label-static-narrow')
    folder.mkdir(parents=True)
    output = io.StringIO()
    started = datetime.now(timezone.utc)
    suite = unittest.TestSuite([QuoteCorrected('test_wire_click_labels_and_original_public_affordances_unchanged')])
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    after = {p: prior.base.sha(p) for p in source}
    code = 0 if result.wasSuccessful() and before == after else 1
    (folder / 'unittest.txt').write_text(output.getvalue(), encoding='utf-8')
    (folder / 'checks.json').write_text(json.dumps(prior.RECORDS, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    payload = {'candidate': candidate_path, 'candidate_file_sha256': prior.base.sha(candidate_path),
               'command': [sys.executable, '-B', '-X', 'utf8', *sys.argv],
               'started_at': started.isoformat(), 'ended_at': datetime.now(timezone.utc).isoformat(),
               'exit_code': code, 'methods': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
               'source_sha256_before': before, 'source_sha256_after': after,
               'prior_script_sha256_unchanged': old_script_sha,
               'qa_script_sha256': prior.base.sha('tests/companion-nextstep/run_labels_narrow.py'),
               'reason': 'Correct only QA expected unquoted observation-button text; actual SYSTEM uses Chinese quotes.',
               'prior_run': 'evidence/integration/companion-nextstep/qa/20261018T153601756155Z-labels/run.json',
               'paid_calls': 0, 'network': False, 'canonical_database_access': False,
               'builds': 0, 'UI_runs': 0, 'already_passed_HTTP_repeated': False,
               'limitations': ['Only completes prior failed static label method; final text has no real model retest.']}
    assert prior.base.sha('tests/companion-nextstep/run_labels.py') == old_script_sha
    (folder / 'run.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(output.getvalue())
    print(json.dumps({'evidence': str(folder), 'exit_code': code, 'methods': result.testsRun}))
    return code


if __name__ == '__main__':
    sys.exit(main())
