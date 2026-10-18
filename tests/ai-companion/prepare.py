"""Preparation validates syntax/hashes only; does not run product code."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
qa = ROOT / 'evidence/integration/ai-companion/qa'
design = json.loads((qa/'design-review.json').read_text(encoding='utf-8'))
paths = ['tests/api/test_ai_companion.py', 'tests/ai-companion/run_api.py', 'tests/ai-companion/qa_app.py', 'tests/ai-companion/prepare.py', 'tests/ai-companion/fake_runtime.py']
for p in paths: ast.parse((ROOT/p).read_text(encoding='utf-8'))
payload = {
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'formal_execution': False, 'protocol_ready': True,
    'formal_gate': 'Main SOURCE STOP/frozen candidate GO required; exact source hashes before/after.',
    'old_test_sha256': design['old_test_sha256'],
    'old_preset_methods': ['test_mock_round_robin_at_two_original_topics_and_levels', 'test_initial_observation_valid_repeat_replay_stale_and_failed_provider'],
    'old_legacy_methods': ['test_real_selection_is_fixed_offline_redacted_and_request_is_idempotent', 'test_two_sessions_parallel_different_keys_no_shared_runtime_mutation'],
    'API_scope': ['Real HTTP deepseek override with synthetic credentials and patched provider complete, tools=[]/none and known context.', 'Current question plus bounded recent successful question/answer/action history; redaction and restore generation.', 'Safe natural prose survives Store; full-answer/hidden-fact/false-completion/ref/shape attacks including answer-only confirmations.', 'Server durable mode authority vs spoofed usage, new-mode conflict/replay and additive oldDB/oldreceipt migration.', 'Valid count/presetlevel preservation, duplicate inflight/manual race/provider failure, save/restore/reopen.'],
    'UI_scope': ['One production build and desktop1280x900 only.', 'Real provider branch through test-only local app with fakecomplete, no external network.', 'Question/key, actual natural reply, recent4 UI log, known readonly state and preset switch.', 'Necessary namedarchive/restore/reload clears history and secret; no new legacy/mobile matrix.'],
    'paid_calls': 0, 'python_AST_files': len(paths), 'formal_tests': 0,
}
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == h for p,h in design['old_test_sha256'].items())
(qa/'preparation.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'protocol_ready': True, 'AST_files': len(paths), 'old_tests_match': len(design['old_test_sha256']), 'formal_tests': 0}))
