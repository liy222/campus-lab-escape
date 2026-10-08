"""Seal actual focused stage UI evidence; no application test execution."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
QA = ROOT / 'evidence/integration/stage-ui/qa'
def read(p): return json.loads((ROOT / p).read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
def rel(p): return p.relative_to(ROOT).as_posix()
def save(p, data): (ROOT / p).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

candidate_paths = ['evidence/integration/stage-ui/candidate' + suffix + '.json' for suffix in ['', '-fixed', '-fixed2', '-fixed3']]
candidates = {p: read(p)['source_sha256'] for p in candidate_paths}
final_path = candidate_paths[-1]
current = {p: sha(p) for p in candidates[final_path]}
assert len(current) == 152 and current == candidates[final_path]
prep = read('evidence/integration/stage-ui/qa/preparation.json')
assert all(sha(p) == h for p, h in prep['immutable_sha256'].items())
old_qa = read('evidence/upgrade/v4.2/qa/result.json')['artifact_sha256']
assert len(old_qa) == 238 and all(sha(p) == h for p, h in old_qa.items())
builds = []
for p in sorted((QA / 'formal-build').glob('*/run.json')):
    d = read(rel(p))
    assert d['exit_code'] == 0 and d['candidate_before_after_match']
    assert d['source_sha256_before'] == d['source_sha256_after'] == candidates[d['candidate']]
    builds.append({'run': rel(p), 'candidate': d['candidate'], 'command': d['command'], 'exit_code': d['exit_code'], 'source_before_after_match': True})
assert len(builds) == 4
browser = []
for p in sorted(QA.glob('*-browser/run.json')):
    d = read(rel(p))
    assert d['source_sha256_before'] == d['source_sha256_after'] == candidates[d['candidate']]
    browser.append({'run': rel(p), 'candidate': d['candidate'], 'command': d['command'], 'exit_code': d['exit_code'], 'records': len(d['checks']), 'necessary_scope': d['necessary_scope'], 'issues': d['issues'], 'source_before_after_match': True})
assert len(browser) == 9 and [d['exit_code'] for d in browser] == [1] * 7 + [0, 0]
assert browser[-2]['records'] == 87 and browser[-1]['records'] == 63
end_path, feedback_path = browser[-2]['run'], browser[-1]['run']
feedback = read(feedback_path)
observation = next(c for c in feedback['checks'] if c['check'] == 'landscape-feedback-HUD-observation')
assert observation['overlap_count'] == 0
passed = {
    'original R1 lock / R2 circuit / CRT four viewport geometry, real lock and circuit touch': browser[1]['run'],
    'original actual CRT submit and notebook geometry': browser[2]['run'],
    'original actual named save and menu geometry': browser[4]['run'],
    'original eligible mock hint, noncredential key storage/switch boundary': browser[5]['run'],
    'fixed dialog44 at1280/375/812, reload/selected restore/post-restore key; R3 desktop1920/1280': browser[6]['run'],
    'fixed2 inventory four viewport, R3 compact375/812, actual Canvas touch/keyboard draft and server sequence, EXIT four viewport': end_path,
    'fixed3 812x375 feedback/HUD zero intersection; actual menu/notebook mouse and Canvas device touch': feedback_path,
}
viewed = [
    '20261008T130239103Z-browser/R3-sequence-375x812.png',
    '20261008T075147443Z-browser/R2-login-1280x900.png',
    '20261008T130239103Z-browser/selected-restore-confirm-375x812.png',
    '20261008T130822346Z-browser/R3-affected-inventory-375x812.png',
    '20261008T130822346Z-browser/R3-sequence-812x375.png',
    '20261008T130822346Z-browser/EXIT-victory-375x812.png',
    '20261008T131459427Z-browser/R3-landscape-feedback-HUD-812x375.png',
]
limitations = [
    'Joint coverage across four product candidates; seven browser failures and two necessary-scope passes. No single full-green browser claim and no sum of repeated record counts.',
    'Public authenticated mock API fixtures prepare prerequisites; targeted lock/circuit/CRT/sequence/draft/HUD/archive actions use real UI. Fixture-generated Win is not a new full route claim.',
    'Second browser actual422 response body was not retained; selector-response and resize readiness corrections subsequently passed CRT on unchanged original source. First dialog40 failure had no screenshot; actual visible rectangles/stack are retained, no image reconstructed.',
    'One quota approval-review failure prevented execution after fourth adapter fix; it is not a test run. Fixed3 reverse-byte proof initially demanded a unique CRLF interval; equivalent intervals restore identical bytes, corrected static proof0.',
    'Headless Chrome emulated touch; no physical-device usability, human completion-time, audio audition, root CMD or new process-restart claim. No new full API suite; existing backend tests/evidence remain immutable.',
    'Mock turns use owned temporary SQLite; deterministic mock creates no paid BudgetLedger. Noncredential key was never submitted to a paid provider; no historical DB, user credential or model-runtime identity claim.',
]
report = '''# Stage UI independent QA — SOURCE STOP

Joint focused verdict passes on final152-source candidate-fixed3.json. Desktop HUD/backpack/closeup controls fit the real16:9 Canvas; portrait and low-height landscape use approved readable panels within the fixed viewport stage. Full document screenshots and bounds show no web region below the stage. Original App visual/legacy grid branches were mutually exclusive; a duplicate legacy scene was never claimed reproduced.

Actual builds: four exit0 runs, one each for original/fixed/fixed2/fixed3 product epoch; no unchanged-candidate repeat. Actual browsers: seven exit1 runs retained, then fixed2 `--only=end`87records/exit0 and fixed3 `--only=feedback`63records/exit0, issues[]. These counts include setup/observations/cleanup and are not summed. All actual commands, source maps, errors, image hashes and scope-to-run links are in [result.json](../../evidence/integration/stage-ui/qa/result.json).

Five earlier failures were new QA fixture/readiness/close-order expectations: microscope inspect missing;422 response with no retained body then corrected readiness; notebook backdrop left open; public fixture/UI stale revision; legal unavailable hint when no topic. Three product findings were closed by separate frozen fixes: visible confirmation buttons40→44px; mobile inventory button42→44px with46px parent; landscape feedback/HUD visual overlap→zero intersection. The seventh failed run is the inventory finding; feedback was identified from the subsequent passing run's actual whole-page image, then explicitly tested after its fix. Original evidence remains untouched.

Successful joint scopes: lock/circuit/CRT at1920×1080,1280×900,375×812,812×375; real lock submit, circuit touch and CRT login; notebook/menu/named save; eligible free mock/key-memory boundary; dialog44/reload/selected restore/new generation/cleared key; R3 desktop+compact geometry, physical touch and independent keyboard draft/server sequence; inventory four sizes and EXIT four sizes. Final812 landscape tests additionally prove feedback/HUD rectangles do not intersect and real HUD/Canvas actions remain reachable.

Proofs independently reverse the conditional dialog class+CSS append, the two inventory declarations, and the one landscape feedback declaration to their exact preceding raw hashes. Final152 current sources match; backend/contracts40, SVG84, api.ts/manifest, oldAPI12/e2e15 and all238 sealed v4.2 artifacts remain unchanged. New files: run_stage_ui.mjs, QA wrappers/protocols/epochs/runs/seal under evidence/integration/stage-ui/qa, and this report. Node --check0 is in the protocol evidence. Seal command is configured Python -B -X utf8 evidence/integration/stage-ui/qa/seal_result.py; actual exit is recorded by its caller.

Limits: focused UI regression using QA-owned public API setup, not a full route or repeated127 API suite. No human timing, hardware touch, paid-provider quality, audio audition, interactive root CMD or new restart claim. The first40px dialog failure had no PNG; it is not reconstructed. Second422 body is unavailable. A quota approval-review failure prevented a command from executing; it is not counted as a run. Native mock uses temporary game/AI storage and no paid budget ledger. Seven actual QA image views are listed separately; Main's additional views are not attributed to QA. No paid calls, product edits by QA, commits or agents spawned.
'''
report_path = 'review/findings/stage-ui.md'
(ROOT / report_path).write_text(report, encoding='utf-8')
artifacts = {rel(p): sha(rel(p)) for p in sorted(QA.rglob('*')) if p.is_file() and p.name not in ['result.json', 'seal-execution.json'] and '__pycache__' not in p.parts}
result = {
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'operator': 'visual_qa_oct08',
    'status': 'SEALED independent joint focused verdict PASS; SOURCE STOP',
    'final_candidate': final_path, 'final_candidate_file_sha256': sha(final_path), 'source_count': 152, 'source_sha256_final': current,
    'candidate_file_sha256': {p: sha(p) for p in candidate_paths},
    'source_current_match': True, 'immutable_guards': {**prep['immutable_counts'], 'api_and_manifest_raw_same': True, 'old_v42_artifacts_raw_same': 238, 'all_raw_match': True},
    'build_runs': builds, 'browser_runs': browser, 'successful_joint_coverage': passed, 'record_counts_summed': False,
    'fixture_boundary': limitations[1], 'new_full_API_runs': 0, 'paid_calls': 0,
    'closed_findings': ['visible restore dialog button40px', 'native mobile inventory button42px', 'landscape feedback/HUD visual overlap'],
    'final_feedback_geometry': observation,
    'byte_delta_proofs': ['evidence/integration/stage-ui/qa/final-protocol.json','evidence/integration/stage-ui/qa/fix2-protocol.json','evidence/integration/stage-ui/qa/fix3-protocol.json'],
    'runner': {'path':'tests/e2e/run_stage_ui.mjs','sha256':sha('tests/e2e/run_stage_ui.mjs'),'epochs':'evidence/integration/stage-ui/qa/runner-epochs'},
    'report': {'path': report_path, 'sha256': sha(report_path)},
    'QA_viewed_PNG_sha256': {'evidence/integration/stage-ui/qa/'+p:sha('evidence/integration/stage-ui/qa/'+p) for p in viewed},
    'limitations': limitations, 'artifact_count': len(artifacts), 'artifact_sha256': artifacts,
    'seal_command': ['C:/Users/liyh/.conda/envs/1/python.exe','-B','-X','utf8','evidence/integration/stage-ui/qa/seal_result.py'],
}
save('evidence/integration/stage-ui/qa/result.json', result)
print(json.dumps({'result_sha256':sha('evidence/integration/stage-ui/qa/result.json'),'report_sha256':sha(report_path),'artifacts':len(artifacts),'browser_runs':len(browser),'build_runs':len(builds),'current152_match':True,'immutable_match':True},ensure_ascii=False))
