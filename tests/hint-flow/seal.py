"""Read-only post-run evidence digest and result; does not run product checks."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
qa = ROOT / 'evidence/integration/hint-flow/qa'
candidate_path = 'evidence/integration/hint-flow/candidate.json'
candidate = json.loads((ROOT / candidate_path).read_text(encoding='utf-8-sig'))
api_path = 'evidence/integration/hint-flow/qa/20261018T052105812289Z-api'
browser_path = 'evidence/integration/hint-flow/qa/20261018T052128899Z-browser'
api = json.loads((ROOT / api_path / 'run.json').read_text(encoding='utf-8'))
browser = json.loads((ROOT / browser_path / 'run.json').read_text(encoding='utf-8'))
prep = json.loads((qa / 'preparation.json').read_text(encoding='utf-8'))
digest = lambda p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
current = {p: digest(p) for p in candidate['source_sha256']}
assert current == candidate['source_sha256'] == api['source_sha256_before'] == api['source_sha256_after'] == browser['source_sha256_before'] == browser['source_sha256_after']
assert all(digest(p) == h for p, h in prep['old_test_sha256'].items())
assert api['exit_code'] == browser['exit_code'] == 0 and not browser['issues']
artifacts = sorted(p for p in qa.rglob('*') if p.is_file() and p.name != 'result.json')
result = {
    'recorded_at': datetime.now(timezone.utc).isoformat(),
    'operator': 'hint_flow_qa independent QA',
    'candidate': candidate_path,
    'candidate_sha': 'cae6d5cb1b42e1a5ad036b973f3ffaa19bd933ee15655c3bfe1e80b2ec3b3ac7',
    'accepted_scope': 'Focused domain/HTTP hint safety, flow, stats/replay/restore and desktop UI; no complete old-suite claim.',
    'actual_API': {'path': api_path, 'exit_code': 0, 'methods': api['methods'], 'seconds': 12.371, 'new_methods': 7, 'old_methods': 4, 'subtest_count': None, 'runs': 1},
    'actual_browser': {'path': browser_path, 'exit_code': 0, 'record_count': len(browser['checks']), 'issues': browser['issues'], 'viewport': browser['desktop_viewport'], 'runs': 1, 'production_builds': 1, 'typecheck_exit': 0, 'build_exit': 0, 'legacy_view': 'Isolated real legacy backend/Vite dev view, no second production build.'},
    'actual_manual_PNG_review': [browser_path + '/' + p for p in ['default-free.png', 'real-mode-retained.png', 'restored-rotation.png', 'R3-readonly-hint.png', 'legacy-input.png']],
    'actual_domain_projection_records': 116,
    'original_template_variants': 18,
    'source_files_match': len(current),
    'old_test_files_unchanged': len(prep['old_test_sha256']),
    'source_sha256': current,
    'artifact_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts},
    'artifact_count_before_result': len(artifacts),
    'QA_source_sha256': {p: digest(p) for p in ['tests/api/test_hint_flow.py', 'tests/hint-flow/prepare.py', 'tests/hint-flow/run_api.py', 'tests/hint-flow/run_browser.mjs', 'tests/hint-flow/seal.py', 'review/findings/hint-flow.md']},
    'unresolved_product_findings': [],
    'failed_formal_epochs': [],
    'paid_calls': 0,
    'mobile_checks': 0,
    'product_changes_by_QA': 0,
    'old_evidence_changes': 0,
    'limitations': ['No full old backend suite, full visual acceptance or human timing.', 'No real provider request/quality or historical user DB test.', 'Original initial NO_HINT/fixed-first-topic expectations are superseded and source-retained, not weakened.', '116 projection records include repeated states; 71 browser records include public API setup/cleanup, not unique assertions.', 'Existing Starlette/httpx deprecation and Vite chunk warning retained.'],
}
(qa / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'source_match': len(current), 'old_tests_match': len(prep['old_test_sha256']), 'artifact_count_before_result': len(artifacts), 'unresolved': 0, 'exit_code': 0}))
