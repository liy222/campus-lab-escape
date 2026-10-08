"""Validate existing sealed execution records; finalize joint QA without rerunning tests."""
from datetime import datetime, timezone
import hashlib
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[4]
qa = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
rel = lambda p: p.relative_to(root).as_posix()
initial_path = qa.parent / 'candidate.json'
fixed_path = qa.parent / 'candidate-fixed.json'
initial, fixed = read(initial_path), read(fixed_path)
assert sha(initial_path) == '664b3474a5429d65ee455845d794df20d5aec741d9f7c4a67e09dee5e7088fb8'
assert sha(fixed_path) == '524ab24a54f39405430f2a53446dc221702aa671e090e2858cda3ee02e63a9e3'
assert len(initial['source_sha256']) == len(fixed['source_sha256']) == 85
assert all(sha(root / p) == h for p, h in fixed['source_sha256'].items())
changed = [p for p, h in initial['source_sha256'].items() if fixed['source_sha256'][p] != h]
assert changed == ['frontend/src/assets/closeup_cabinet_locked.svg', 'frontend/src/assets/closeup_clock.svg', 'frontend/src/assets/r1_clock.svg', 'frontend/src/style.css']
baseline_path = qa / 'baseline-result.json'
first_path = qa / 'first-result.json'
baseline, first = read(baseline_path), read(first_path)
base_api_path = qa / 'baseline-api/run.json'
base_api = read(base_api_path)
targeted_path = qa / 'formal-api/run.json'
build_path = qa / 'formal-build/run.json'
browser_path = qa / '20261007T135541642Z-browser/run.json'
fixed_build_path = qa / 'fixed-build/run.json'
fixed_browser_path = qa / '20261007T140546920Z-browser-fix/run.json'
targeted, build, browser = map(read, [targeted_path, build_path, browser_path])
fixed_build, fixed_browser = map(read, [fixed_build_path, fixed_browser_path])
assert base_api['exit_code'] == 0
assert baseline['API']['passed_methods'] == 127 and baseline['API']['passed_subtests'] == 337
backend_paths = [p for p in initial['source_sha256'] if p.startswith(('backend/', 'contracts/'))]
assert len(backend_paths) == 40
baseline_backend_paths = [p for p in backend_paths if p in base_api['source_sha256_before']]
assert len(baseline_backend_paths) == 31
assert all(base_api['source_sha256_before'][p] == base_api['source_sha256_after'][p] == initial['source_sha256'][p] == fixed['source_sha256'][p] for p in baseline_backend_paths)
git_line_ending_only = []
for p in backend_paths:
    blob = subprocess.run(['git', 'show', '9762fae018d39beea07c58207d2715227b537d00:' + p], cwd=root, capture_output=True, check=True)
    current = (root / p).read_bytes()
    assert blob.stdout.replace(b'\r\n', b'\n') == current.replace(b'\r\n', b'\n')
    if hashlib.sha256(blob.stdout).hexdigest() != fixed['source_sha256'][p]:
        git_line_ending_only.append(p)
for run in [targeted, build, browser]:
    assert run['exit_code'] == 0
    assert run['source_sha256_before'] == run['source_sha256_after'] == initial['source_sha256']
for run in [fixed_build, fixed_browser]:
    assert run['exit_code'] == 0
    assert run['source_sha256_before'] == run['source_sha256_after'] == fixed['source_sha256']
assert fixed_browser['candidate_sha256'] == sha(fixed_path)
assert len(browser['checks']) == 206 and not browser['issues']
assert len(fixed_browser['checks']) == 112 and not fixed_browser['issues']
assert not any(c.get('passed') is False for c in fixed_browser['checks'])
assert sum(c['check'] == 'fixed-feedback-does-not-cover-reading-return-input' for c in fixed_browser['checks']) == 26
preparation = read(qa / 'preparation-runner-renderer.json')
old_api, old_e2e = preparation['prior_api_tests_sha256'], preparation['old_e2e_preparation_sha256']
assert len(old_api) == 12 and len(old_e2e) == 11
assert all(sha(root / p) == h for p, h in old_api.items())
assert all(sha(root / p) == h for p, h in old_e2e.items())
viewed = ['fixed-clock-reading-1920.png', 'fixed-eyepiece-reading-1920.png', 'fixed-four-wheel-lock-1920.png', 'fixed-clock-reading-375.png', 'fixed-wrong-code-375.png', 'fixed-restored-photo-reading-375.png']
commands = [{'epoch': label, 'record': rel(path), 'command': read(path)['command'], 'exit_code': read(path)['exit_code'], 'executed_by_current_recovery_agent': False} for label, path in [('previsual-full-API', base_api_path), ('initial-targeted-API', targeted_path), ('initial-build', build_path), ('initial-complete-route-Chrome', browser_path), ('fixed-build', fixed_build_path), ('fixed-narrow-Chrome', fixed_browser_path)]]
record = {
    'status': 'Independent joint v4.0 QA accepted; SOURCE STOP',
    'recorded_at': datetime.now(timezone.utc).isoformat(),
    'finalization_operator': 'visual_qa_oct08; read-only recovery audit and six fixed PNG visual reviews, no formal reruns',
    'prior_execution_operator': 'Prior QA epoch recorded by existing run.json evidence; recovery does not claim those executions or infer resumed runtime model',
    'candidate': rel(fixed_path), 'candidate_sha256': sha(fixed_path), 'source_count': 85,
    'initial_candidate': rel(initial_path), 'initial_candidate_sha256': sha(initial_path),
    'reuse_policy': 'Joint coverage: historical full API baseline + initial frozen complete route/targeted API + fixed four-path narrow recheck. No second complete API or route run, and no repeated counts added.',
    'baseline_reuse': {'result': rel(baseline_path), 'methods_passed': 127, 'subtests_passed': 337, 'exit_code': 0, 'baseline_manifest_backend_contract_31_raw_byte_identical': True, 'all_40_backend_contract_paths_content_identical_to_baseline_git_after_CRLF_normalization': True, 'baseline_git_raw_identical_count': 40-len(git_line_ending_only), 'baseline_git_line_ending_only_paths': git_line_ending_only, 'baseline_head': '9762fae018d39beea07c58207d2715227b537d00'},
    'initial_candidate_coverage': {'result': rel(first_path), 'targeted_methods': 6, 'targeted_subtests': 3, 'targeted_exit_code': 0, 'build_exit_code': 0, 'browser_checks': 206, 'browser_exit_code': 0, 'issues': []},
    'fixed_candidate_coverage': {'browser_run': rel(fixed_browser_path), 'browser_exit_code': 0, 'checks': 112, 'issues': [], 'layout_records': 26, 'pixel_records': sum(c['check'] == 'real-rendered-canvas-nonblack-nonuniform' for c in fixed_browser['checks']), 'build_run': rel(fixed_build_path), 'build_exit_code': 0, 'scope': 'R1 CSS and three SVG assets; clock/record/plaque/eyepiece/four-wheel lock/wrong-code/photo/restore at 1920,1280,375; cabinet accepted-closed/open and R1 legacy-slot reset/restore'},
    'fixed_delta': {'changed_paths': changed, 'other_81_identical': True, 'new_removed_paths': [], 'current_fixed85_match': True},
    'old_tests': {'API_12_byte_identical': True, 'e2e_11_byte_identical': True, 'hash_reference': 'evidence/upgrade/v4.0/qa/preparation-runner-renderer.json'},
    'actual_commands_from_existing_records': commands,
    'earlier_failed_attempts': {'record': 'evidence/upgrade/v4.0/qa/browser-attempts.json', 'exit_codes': [1, 1], 'check_counts': [35, 45], 'scope': 'New QA selector adaptation failures; historical artifacts unchanged; repeated checks not added'},
    'fixed_screens_personally_viewed_by_recovery_operator': {rel(fixed_browser_path.parent / name): sha(fixed_browser_path.parent / name) for name in viewed},
    'visual_findings': [
        {'id': 'V40-READING', 'status': 'closed', 'evidence': rel(fixed_browser_path), 'fact': 'Feedback at page top no longer overlaps original clue text or controls; six reviewed PNGs and 26 measured layout records.'},
        {'id': 'V40-CLOCK', 'status': 'closed', 'evidence': rel(fixed_browser_path), 'fact': 'Hour hand visibly points left/up; recorded SVG geometry hour278.5 degrees and minute102.724/102.002 degrees; matches21:17.'},
        {'id': 'V40-LOCK', 'status': 'closed', 'evidence': rel(fixed_browser_path), 'fact': 'Locked cabinet closeup visibly has four wheels; recorded independent SVG check agrees.'}
    ],
    'evidence_sha256': {rel(p): sha(p) for p in [baseline_path, first_path, base_api_path, targeted_path, build_path, browser_path, fixed_build_path, fixed_browser_path, qa / 'browser-attempts.json', qa / 'preparation-runner-renderer.json', qa.parent / 'fix-delta.json']},
    'recovery_finalization_command': ['C:/Users/liyh/.conda/envs/1/python.exe', '-B', '-X', 'utf8', 'evidence/upgrade/v4.0/qa/seal_recovery.py'],
    'recovery_readonly_git_commands': {'command_pattern': ['git', 'show', '9762fae018d39beea07c58207d2715227b537d00:<backend-or-contract-path>'], 'count_in_final_successful_validation': 40, 'exit_code_each': 0, 'purpose': 'Compare all immutable content to baseline Git with explicit CRLF-only treatment;31 recorded working-source bytes separately match raw baseline execution evidence'},
    'recovery_finalization_attempts': [{'exit_code': 1, 'cause': 'New finalization script assumed all40 immutable files were in focused baseline41 manifest; KeyError before writing result. Corrected metadata validation to compare31 recorded files plus40 baseline Git blobs.', 'product_failure': False, 'formal_tests_executed': 0}, {'exit_code': 1, 'cause': 'Git stores LF while four working files have CRLF; overbroad raw-Git-byte assertion failed before result write. Read-only diagnosis proved only line endings differed; raw execution-manifest assertions retained.', 'product_failure': False, 'formal_tests_executed': 0}, {'exit_code': 0, 'scope': 'Finalization metadata and byte audit only'}],
    'product_edits_by_recovery_QA': 0, 'old_test_edits_by_recovery_QA': 0, 'formal_reruns_by_recovery_QA': 0, 'paid_calls': 0,
    'limitations': [
        'One existing Starlette/httpx deprecation warning remains.',
        'R1 original SVG visuals only; R2/R3 are tested playable graybox fallback, not later visual acceptance.',
        'RootCMD was not interactively launched; owned direct loopback backend process restart was covered in initial browser epoch.',
        'Controlled missing-asset failure was not exercised; normal assets-ready, rendered pixels, scene recreation and no-pageerror checks were exercised.',
        'No paid-provider quality, real credentials, sensitive historical database, audio-quality or human manual playtest/completion-time claim.',
        'Fix browser used ordinary375 viewport; real hasTouch touchscreen and independent keyboard were covered by the initial browser epoch.',
        'Corrected CSS/three SVG scope uses joint evidence; fixed candidate did not rerun complete three-room route or full API suite.'
    ]
}
(qa / 'result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'exit_code': 0, 'fixed85_match': True, 'old_API12_match': True, 'old_e2e11_match': True, 'initial_browser_checks': 206, 'fixed_narrow_checks': 112, 'new_formal_runs': 0, 'result_sha256': sha(qa / 'result.json')}, ensure_ascii=False))
