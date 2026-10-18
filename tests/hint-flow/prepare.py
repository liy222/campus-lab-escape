"""Read-only protocol preparation; executes no product/test/browser code."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
out = ROOT / 'evidence/integration/hint-flow/qa'
out.mkdir(parents=True, exist_ok=True)
test_paths = subprocess.check_output(['rg', '--files', 'tests'], cwd=ROOT, text=True, encoding='utf-8').splitlines()
old_tests = [p.replace('\\', '/') for p in test_paths if not p.replace('\\', '/').startswith('tests/hint-flow/') and p.replace('\\', '/') != 'tests/api/test_hint_flow.py']
for p in ['tests/api/test_hint_flow.py', 'tests/hint-flow/run_api.py', 'tests/hint-flow/prepare.py']:
    ast.parse((ROOT / p).read_text(encoding='utf-8'))
protocol = {
    'recorded_at': datetime.now(timezone.utc).isoformat(),
    'protocol_ready': True,
    'formal_execution': False,
    'formal_gate': 'Await explicit Main SOURCE STOP candidate GO; frozen raw hashes must match before and after each formal run.',
    'baseline_head': 'c3d9a41e1f2ce7bb6dff17e8d490b47c4d7f1530',
    'old_test_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sorted(old_tests)},
    'selected_old_methods': [
        'test_hint_replay_stale_invalid_level_settings_failures_do_not_increment',
        'test_runtime_selection_injection_unknown_refs_free_answer_and_autoread_stop',
        'test_store_finalizer_rechecks_fake_runtime_answer_refs_proposal_and_stale',
        'test_hint_concurrent_duplicate_inflight_stale_generation_and_timeout_never_double_count',
    ],
    'excluded_old_assertions': [
        {'method': 'test_initial_fixed_statistics_no_future_boards_and_no_hint_paid_request', 'reason': 'Initial observation hints now intentionally valid; old no-topic/no-count expectation is superseded. Original source retained.'},
        {'method': 'test_three_levels_only_known_context_no_auto_inspect_no_private_full_solution', 'reason': 'New procedural candidates can change selected refs; exact original-first-topic context assertion is outside new requirements. New tests cover all original18, levels, known refs, safe context and readonly authority.'},
    ],
    'API_scope': ['Legal accepted walkthrough states, early room traversal and guessed solutions without deduction clues.', 'Original18 text identity, three-level rendered safety and topic-reference uniqueness.', 'Temporary DB HTTP mock count/replay/new requests/stale/providerfail/noautoinspect/Store rerender authority.', 'Named archive restore/reopen preserves counter/level and deterministic next eligible selection.', 'Relevant four old security/race/count tests only; no full backend suite.'],
    'UI_scope': ['One formal production typecheck/build; desktop1280x900 only.', 'Default presets have no label/question/count/key, valid fixed request works and level/rotation remain readonly.', 'Real mode keeps input/key/format guard without request; no external provider call.', 'Actual named archive/save/restore/reload and minimumR3 hint check.', 'Legacy isolated actual dev view input and free mock submit; no second production build.'],
    'paid_calls': 0,
    'preparation_validation': {'python_ast_parse': 3, 'product_imports_or_tests_run': 0},
}
(out / 'preparation.json').write_text(json.dumps(protocol, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'formal_execution': False, 'protocol_ready': True, 'old_test_files': len(old_tests), 'python_ast_parse': 3}))
