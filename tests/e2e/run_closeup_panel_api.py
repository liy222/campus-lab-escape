"""Frozen-candidate targeted execution; preparation/AST checks do not invoke this."""
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    candidate_path = sys.argv[1]
    preparation = json.loads((ROOT / 'evidence/integration/closeup-panel/qa/preparation.json').read_text(encoding='utf-8'))
    assert preparation['protocol_ready'], 'Formal execution requires stable Main candidate GO'
    candidate = json.loads((ROOT / candidate_path).read_text(encoding='utf-8-sig'))
    before = {p: sha(p) for p in candidate['source_sha256']}
    assert before == candidate['source_sha256']
    assert all(sha(p) == h for p, h in preparation['immutable_sha256'].items())
    os.environ['AI_PROVIDER'] = 'mock'
    tests = [
        'tests.api.test_closeup_panel.CloseupPanelProjection.test_early_public_devices_keep_final_check_guard_then_finish',
        'tests.api.test_closeup_panel.CloseupPanelProjection.test_early_board_control_and_archive_restore_reopen_projection',
        'tests.api.test_closeup_panel.CloseupPanelV33Compatibility.test_v33_keeps_sequence_hidden_until_final_check',
        'tests.api.test_upgrade_v33.UpgradeV33Acceptance.test_ai_read_guard_cannot_mutate_circuit_sequence_or_reveal_unknown_board',
        'tests.api.test_upgrade_v33.UpgradeV33Acceptance.test_ai_legitimate_read_preserves_partial_board_and_manual_only_tools',
        'tests.api.test_upgrade_v34.UpgradeV34Acceptance.test_initial_fixed_statistics_no_future_boards_and_no_hint_paid_request',
        'tests.api.test_upgrade_v34.UpgradeV34Acceptance.test_runtime_selection_injection_unknown_refs_free_answer_and_autoread_stop',
        'tests.api.test_multiple_saves.MultipleSavesAcceptance.test_selected_restore_expires_pending_mock_hint_without_stats_mutation',
    ]
    started = datetime.now(timezone.utc)
    folder = ROOT / 'evidence/integration/closeup-panel/qa' / (started.strftime('%Y%m%dT%H%M%S%fZ') + '-api')
    folder.mkdir()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(tests))
    from tests.api.test_r1 import sanitize
    after = {p: sha(p) for p in before}
    immutable = all(sha(p) == h for p, h in preparation['immutable_sha256'].items())
    code = 0 if result.wasSuccessful() and after == before and immutable else 1
    record = {'candidate': candidate_path, 'command': [sys.executable, '-B', '-X', 'utf8', *sys.argv],
              'started': started.isoformat(), 'ended': datetime.now(timezone.utc).isoformat(),
              'exit_code': code, 'tests_run': result.testsRun, 'selected_methods': tests,
              'errors': sanitize([(test.id(), trace) for test, trace in result.errors]),
              'failures': sanitize([(test.id(), trace) for test, trace in result.failures]),
              'source_sha256_before': before, 'source_sha256_after': after,
              'immutable_match': immutable, 'paid_calls': 0,
              'limitations': ['Targeted API methods only; no full suite or provider quality claim.']}
    (folder / 'run.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'evidence': str(folder), 'exit_code': code, 'tests_run': result.testsRun}))
    return code


if __name__ == '__main__':
    sys.exit(main())
