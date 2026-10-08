"""Seal existing actual QA evidence; does not run application tests."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
QA = ROOT / 'evidence/upgrade/v4.2/qa'


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def save(path, value):
    (ROOT / path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


candidate = read('evidence/upgrade/v4.2/candidate.json')
baseline = read('evidence/upgrade/v4.2/baseline-candidate.json')
prep = read('evidence/upgrade/v4.2/qa/preparation.json')
current = {p: digest(p) for p in candidate['source_sha256']}
assert len(current) == 152 and current == candidate['source_sha256']
old_tests = {p: digest(p) for p in prep['old_test_sha256']}
assert old_tests == prep['old_test_sha256'] and len(old_tests) == 26
backend = {p: h for p, h in baseline['source_sha256'].items() if p.startswith(('backend/', 'contracts/'))}
svg = {p: h for p, h in baseline['source_sha256'].items() if p.endswith('.svg')}
assert len(backend) == 40 and len(svg) == 61
assert all(digest(p) == h for p, h in {**backend, **svg}.items())
api_path = 'evidence/upgrade/v4.2/qa/formal-api/20261008T060434213982Z-full/run.json'
build_path = 'evidence/upgrade/v4.2/qa/formal-build/20261008T060439597839Z-build/run.json'
api, build = read(api_path), read(build_path)
assert api['exit_code'] == build['exit_code'] == 0
assert api['candidate_before_match'] and api['candidate_after_match'] and api['tests_before_after_match']
assert build['candidate_before_after_match']
attempts = read('evidence/upgrade/v4.2/qa/browser-attempts.json')['attempts']
assert len(attempts) == 6
runs = []
for attempt in attempts:
    entry = dict(attempt)
    if entry.get('run_json'):
        run = read(entry['run_json'])
        assert run['source_sha256_before'] == current == run['source_sha256_after']
        entry['command'] = run['command']
        entry['checks'] = len(run['checks'])
        entry['exit_code'] = run['exit_code']
    runs.append(entry)
finish_path = 'evidence/upgrade/v4.2/qa/20261008T062911957Z-browser/run.json'
finish = read(finish_path)
assert finish['exit_code'] == 0 and not finish['issues'] and len(finish['checks']) == 283
assert finish['source_sha256_before'] == current == finish['source_sha256_after']
runner = 'tests/e2e/run_visual_v42.mjs'
epoch_path = 'evidence/upgrade/v4.2/qa/runner-epochs/seventh.mjs'
assert not (ROOT / epoch_path).exists()
(ROOT / epoch_path).write_bytes((ROOT / runner).read_bytes())
syntax_command = ['C:/Program Files/nodejs/node.exe', '--check', runner]
syntax = subprocess.run(syntax_command, cwd=ROOT, capture_output=True, text=True)
assert syntax.returncode == 0
viewed = [
    '20261008T060516018Z-browser/development-quiet-first-launch.png',
    '20261008T060516018Z-browser/R1-gated-early-missing-svg.png',
    '20261008T060849492Z-browser/R2-monitor-LOGIN_LOCKED.png',
    '20261008T062418881Z-browser/R3-public-sequence-mobile.png',
    '20261008T062418881Z-browser/R3-real-touch-keyboard-public-draft-375.png',
    '20261008T062418881Z-browser/R3-gated-sequence-missing-svg.png',
    '20261008T062418881Z-browser/R3-door-opening-frame.png',
    '20261008T062418881Z-browser/R3-OPEN.png',
    '20261008T062418881Z-browser/victory-server-fields.png',
]
artifacts = {p.relative_to(ROOT).as_posix(): digest(p.relative_to(ROOT)) for p in sorted(QA.rglob('*'))
             if p.is_file() and p.name != 'result.json' and '__pycache__' not in p.parts}
limitations = [
    'Joint browser coverage across retained failed adapter epochs and necessary narrow completions; not a single full-green browser run. Repeated checks are not summed.',
    'First browser exited 1 before run.json persisted; only actual stdout and four PNGs exist. Original immediate assertion/check count cannot be reconstructed.',
    'Late final/finish preparation uses QA-owned authenticated public API fixtures for already-covered prerequisites and moments; actual R3 successful route was Canvas in final, while finish fixture prepares already-covered Win for remaining archive/UI tests.',
    'Two blocked EXIT negative requests use original public API plus UI control-absence assertions. No hidden state injection or fabricated receipt.',
    'Native AudioContext trusted gesture and one-shot oscillator starts were observed separately from ambient BufferSource rebuilding. No human audition or sound-quality claim.',
    'Controlled missing SVG faults cover all three room gates/retry; module-import failure injection is not formally exercised.',
    'S/A/B/C are server API cases; browser compares six fields and rating of actual earned settlement, not fabricated four UI ratings.',
    'Old-version namespace/no-engine request smoke uses development server and owned new slots; compiled production request verification covers current first launch and started R1.',
    'Root CMD was not interactively launched; loopback owned backend process restart only. No historical sensitive DB access, paid model calls, human completion-time or real-provider quality claim.',
]
result = {
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'operator': 'visual_qa_oct08',
    'status': 'SEALED — independent joint coverage complete; SOURCE STOP',
    'candidate': 'evidence/upgrade/v4.2/candidate.json',
    'candidate_sha256': '387725b128af9e5d815ab5f9398de937503887b3b1a196b99dc679201b2d5bf7',
    'source_count': 152, 'source_sha256_final': current, 'candidate_current_match': True,
    'immutable_guards': {'backend_contracts': 40, 'old_svg': 61, 'old_API_files': 12, 'old_e2e_files': 14, 'all_raw_bytes_match': True, 'old_test_sha256_final': old_tests},
    'baseline': {'reused': 'evidence/upgrade/v4.1/qa/result.json', 'new_runs': 0},
    'API': {'run': api_path, 'command': api['command'], 'pytest_arguments': api['pytest_arguments'], 'exit_code': 0, 'methods_passed': 127, 'subtests_passed': 337, 'seconds': 295.14, 'existing_warning_count': 1, 'full_suite_runs': 1},
    'build': {'run': build_path, 'command': build['command'], 'wrapper_command': ['C:/Users/liyh/.conda/envs/1/python.exe','-B','-X','utf8','evidence/upgrade/v4.2/qa/formal_build.py','evidence/upgrade/v4.2/candidate.json'], 'exit_code': 0,
              'main_js': {p:v for p,v in build['dist_files'].items() if p.endswith('.js') and ('/index-' in p or '/phaser-' in p)}},
    'browser_failed_epochs': runs,
    'browser_final_necessary_completion': {'run': finish_path, 'command': finish['command'], 'exit_code': 0, 'checks': 283, 'issues': []},
    'joint_coverage': [
        {'run': 'evidence/upgrade/v4.2/qa/20261008T060849492Z-browser/run.json', 'scope': 'R1 complete regression/quiet entry/replay/native audio/mute/motion/early missing asset/archives/reload/restart; R2 through circuit, manual switch, dark/bright and LOGIN_LOCKED'},
        {'run': 'evidence/upgrade/v4.2/qa/20261008T061905431Z-browser/run.json', 'scope': 'Corrected R2 missing SVG/retry, wrong/correct CRT login, selected restore/restart, mobile CRT, DATA_READ and tray pickups'},
        {'run': 'evidence/upgrade/v4.2/qa/20261008T062418881Z-browser/run.json', 'scope': 'Real R3 Canvas public draft/invalid duplicate/clear/restore/reload/completed save; missing SVG/retry; actual touch/keyboard375; all five exit states and blocked opening input; Victory server fields/save/reload/restart/reset/restore'},
        {'run': finish_path, 'scope': 'Remaining archive/reset/selected early-partial-power-Win restores, mobile Victory/records/cancel, independent R1/R2 touch/keyboard, production lazy startup actual requests/transfer sizes and legacy namespace/no-engine smoke'},
    ],
    'repeated_checks_summed': False, 'product_fixes': [], 'paid_calls': 0,
    'runner_final': {'path': runner, 'sha256': digest(runner), 'epoch': epoch_path, 'syntax_command': syntax_command, 'syntax_exit_code': syntax.returncode},
    'QA_operator_viewed_png_sha256': {'evidence/upgrade/v4.2/qa/' + p: digest('evidence/upgrade/v4.2/qa/' + p) for p in viewed},
    'main_viewed_additional_evidence': 'Main separately reported viewing clear finish mobile-victory, R2 mobile tray, first launch and R3 actual touch; not claimed as QA operator image views.',
    'limitations': limitations, 'artifact_count': len(artifacts), 'artifact_sha256': artifacts,
    'seal_command': ['C:/Users/liyh/.conda/envs/1/python.exe','-B','-X','utf8','evidence/upgrade/v4.2/qa/seal_result.py'],
}
save('evidence/upgrade/v4.2/qa/result.json', result)
report = '''# v4.2 independent QA — SOURCE STOP

Frozen 152-source candidate `387725b128af9e5d815ab5f9398de937503887b3b1a196b99dc679201b2d5bf7` remains byte-identical. Backend/contracts40, old SVG61, API12 and old e2e14 are unchanged. Operator: visual_qa_oct08; no product edits, paid calls, commits or new agents.

Actual full API ran once: 127 methods / 337 subtests passed in 295.14s, exit0, one existing Starlette warning. Actual build exit0; entry JS 294655 bytes/gzip91244, deferred Phaser1388183/gzip368108. Commands and raw per-file build sizes are linked in [result.json](../../evidence/upgrade/v4.2/qa/result.json) and its actual run references.

Browser coverage is joint evidence, not a single all-green full run. Six adapter failures remain: first exit1 without persisted run.json/count (actual stdout +4PNG only), then 290/71/94/195/245-record exit1 runs. Their exact errors, commands and runner byte epochs are preserved in browser-attempts.json and each run. Fixes only addressed new QA navigation/waits/manifest filename/menu scope; no old assertion was weakened. Final `node tests/e2e/run_visual_v42.mjs evidence/upgrade/v4.2/candidate.json --only=finish` exited0 with283 checks/issues[]. Repeated checks are not added together.

Retained successful scopes cover R1 regression and R2 actual circuit/manual switch/CRT/tray, R3 true Canvas player draft/server sequence validation, all five exit states and opening input lock, wrong actions, touch375/keyboard, settlement six server fields, archives/selected restore/reload/owned process restart/reset/cancel, three controlled missing-SVG gates/retry, trusted-gesture native audio/mute/receipt replay deduplication/snapshot silence, built first-launch noDashboard/noPhaser requests then deferred engine, and legacy namespace/no-engine smoke. Precise scope-to-run mapping and all artifact hashes are in result.json.

Late final/finish setup uses explicitly recorded public API fixtures for already-covered prerequisites/moments; final's successful R3 route remains actual Canvas. Finish prepares previously-covered Win through public API only to inspect the still-unpassed archive/mobile UI. Two blocked EXIT server-negative cases use original API plus UI absence assertions. No hidden state/receipt fabrication. S/A/B/C are real full API cases; UI checks the actual earned rating. Nine actually viewed QA PNG paths/hashes are listed separately; Main's additional image views are attributed to Main.

Limitations: no root CMD interactive launch, human playtime/audio audition or paid-provider quality claim; no historical sensitive DB access. Missing SVG faults are tested, dynamic-module import fault injection is not. Legacy no-engine request smoke is development-mode; compiled production verification covers current entry/R1. Native one-shot sound checks distinguish ambient loop reconstruction. First failed run's original immediate assertion stack/count was not persisted and is not reconstructed. No further suite or product change is required by the observed evidence.

Files: new tests/e2e/run_visual_v42.mjs; new QA wrappers, protocol, actual runs, preserved epochs and seal_result.py under evidence/upgrade/v4.2/qa; this report. Seal command: configured Python -B -X utf8 evidence/upgrade/v4.2/qa/seal_result.py; expected exit is recorded by the actual caller, not invented here. Final Node --check executed by seal returns0. SOURCE STOP.
'''
(ROOT / 'review/findings/visual-v42.md').write_text(report, encoding='utf-8')
print(json.dumps({'result': 'evidence/upgrade/v4.2/qa/result.json', 'result_sha256': digest('evidence/upgrade/v4.2/qa/result.json'), 'report': 'review/findings/visual-v42.md', 'runner_sha256': digest(runner), 'artifact_count': len(artifacts), 'source_match': True, 'old_bytes_match': True, 'node_check_exit_code': syntax.returncode}, ensure_ascii=False))
