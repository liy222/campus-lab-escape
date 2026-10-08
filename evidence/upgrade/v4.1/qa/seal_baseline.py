"""Seal actual targeted API/build baseline; no test execution here."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[4]
qa = Path(__file__).resolve().parent
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
candidate_path = qa.parent / 'baseline-candidate.json'
candidate = read(candidate_path)
assert sha(candidate_path) == '3f803251ed225c147bc59e4be6e9e7d97cff7c4c85919de0a580393e4a90e587'
api_path, build_path = qa / 'baseline-api/run.json', qa / 'baseline-build/run.json'
api, build = read(api_path), read(build_path)
for run in [api, build]:
    assert run['exit_code'] == 0
    assert run['source_sha256_before'] == run['source_sha256_after'] == candidate['source_sha256']
assert api['tests_before_after_match'] and api['test_sha256_before'] == api['test_sha256_after']
assert len(api['test_sha256_before']) == 12
assert '6 passed, 1 warning, 3 subtests passed in 11.40s' in (qa / 'baseline-api/stdout.txt').read_text(encoding='utf-8')
copies = read(qa / 'baseline-copy.json')
for item in copies['copies']:
    assert sha(root / item['origin']) == item['origin_sha256']
    assert sha(root / item['copy']) == item['copy_sha256']
record = {
    'status': 'v4.1 actual compact baseline accepted; baseline SOURCE STOP; R2 implementation may start',
    'operator': 'visual_qa_oct08 actual execution',
    'recorded_at': datetime.now(timezone.utc).isoformat(),
    'candidate': 'evidence/upgrade/v4.1/baseline-candidate.json', 'candidate_sha256': sha(candidate_path),
    'source_count': len(candidate['source_sha256']), 'source_85_before_after_bound_both_stages': True,
    'parent_commit': '1047e293ade70e446c9c76be0a0d751f3e3ad81a',
    'API': {'run': 'evidence/upgrade/v4.1/qa/baseline-api/run.json', 'command': api['command'], 'pytest_arguments': api['pytest_arguments'], 'exit_code': 0, 'passed_methods': 6, 'passed_subtests': 3, 'warnings': 1, 'duration_seconds': 11.40, 'compact_check_records': api['checks_count'], 'old_API_12_before_after_identical': True},
    'build': {'run': 'evidence/upgrade/v4.1/qa/baseline-build/run.json', 'wrapper_command': ['C:/Users/liyh/.conda/envs/1/python.exe', '-B', '-X', 'utf8', 'evidence/upgrade/v4.1/qa/baseline_build.py', 'evidence/upgrade/v4.1/baseline-candidate.json'], 'command': build['command'], 'exit_code': 0},
    'copy_policy': copies,
    'full_API_baseline_reuse': {'result': 'evidence/upgrade/v4.0/qa/baseline-result.json', 'methods_passed': 127, 'subtests_passed': 337, 'scope': 'Historical same backend full baseline. Not rerun or recounted in v4.1.'},
    'evidence_sha256': {str(p.relative_to(root)).replace('\\', '/'): sha(p) for p in [api_path, build_path, qa / 'baseline-api/stdout.txt', qa / 'baseline-api/checks.json', qa / 'baseline-build/stdout.txt', qa / 'baseline-copy.json']},
    'formal_new_R2_visual_runs': 0, 'product_edits': 0, 'old_test_edits': 0, 'paid_calls': 0,
    'limitations': ['One existing Starlette/httpx deprecation warning remains.', 'Baseline API/build only; no new R2 scene or asset acceptance.', 'Mock/stub and owned temporary SQLite only; no real provider or human playtest claim.', 'New R2 browser formal run waits owner SOURCE STOP and frozen Main candidate GO.']
}
(qa / 'baseline-result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'exit_code': 0, 'API_methods': 6, 'API_subtests': 3, 'build_exit_code': 0, 'source85_bound': True, 'result_sha256': sha(qa / 'baseline-result.json')}))
