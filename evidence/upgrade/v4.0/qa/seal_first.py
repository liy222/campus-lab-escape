"""Seal real first-candidate coverage; preserve visual failures for narrow fixes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[4]
folder = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
candidate_path = root / 'evidence/upgrade/v4.0/candidate.json'
candidate = json.loads(candidate_path.read_text())
api = json.loads((folder / 'formal-api/run.json').read_text())
build = json.loads((folder / 'formal-build/run.json').read_text())
browser_path = folder / '20261007T135541642Z-browser/run.json'
browser = json.loads(browser_path.read_text())
assert api['exit_code'] == build['exit_code'] == browser['exit_code'] == 0
assert api['source_sha256_before'] == api['source_sha256_after'] == candidate['source_sha256']
assert build['source_sha256_before'] == build['source_sha256_after'] == candidate['source_sha256']
assert browser['source_sha256_before'] == browser['source_sha256_after'] == candidate['source_sha256']
old = json.loads((folder / 'preparation-runner.json').read_text())
old_e2e = json.loads((folder / 'preparation-runner-renderer.json').read_text())['old_e2e_preparation_sha256']
assert all(sha(root / name) == value for name,value in old['prior_api_tests_sha256'].items())
assert all(sha(root / name) == value for name,value in old_e2e.items())
viewed = ['R1-visual-desktop.png','R1-visual-mobile.png','R1-clock-closeup.png','R1-touch-clock-closeup.png','r1_record-reading.png','r1_plaque-reading.png','r1_microscope-SLIDE_PLACED-eyepiece.png','R1-code-accepted-still-closed.png','R1-cabinet-open.png','sample_slide-before-take.png','sample_slide-receipt-frame-take.png','sample_slide-settled-take.png','r1_cabinet-receipt-frame-interact.png','r1_cabinet-settled-interact.png','r1_photo-reading.png','desktop-selected-restore-confirmation.png','mobile-three-archive-list.png','mobile-selected-restore-confirmation.png','mobile-victory.png']
findings = [
    {'id':'V40-READING','status':'product fix pending','fact':'Desktop feedback overlaps original clock, microscope, record and photo clue text. Mobile touch clock text was readable.','evidence':['R1-clock-closeup.png','r1_microscope-SLIDE_PLACED-eyepiece.png']},
    {'id':'V40-CLOCK','status':'product fix pending','fact':'Initial hour-hand points left/down; 21:17 requires hour clockwise 278.5 degrees from12 (left/up).','evidence':['R1-clock-closeup.png']},
    {'id':'V40-LOCK','status':'product fix pending','fact':'Locked closeup draws3 wheels while primary visual plan line574 requires four-digit mechanical/digital lock.','evidence':['R1-code-accepted-still-closed.png']},
]
record = {
    'status':'First frozen-candidate complete functional scope passed; visual acceptance pending three narrow fixes',
    'recorded_at':datetime.now(timezone.utc).isoformat(),'candidate':str(candidate_path.relative_to(root)).replace('\\','/'),'candidate_sha256':sha(candidate_path),'source_count':len(candidate['source_sha256']),
    'baseline_reuse':{'result':'evidence/upgrade/v4.0/qa/baseline-result.json','methods_passed':127,'subtests_passed':337,'scope':'Historical previsual full API baseline; no new complete127-green claim'},
    'targeted_API':{'run':'formal-api/run.json','command':api['command'],'exit_code':0,'methods_passed':6,'subtests_passed':3,'duration_seconds':12.95,'warnings':1},
    'build':{'run':'formal-build/run.json','command':build['command'],'exit_code':0},
    'browser':{'run':str(browser_path.relative_to(folder)).replace('\\','/'),'command':browser['command'],'exit_code':0,'checks':len(browser['checks']),'issues':browser['issues'],'pixel_checks':sum(check['check']=='real-rendered-canvas-nonblack-nonuniform' for check in browser['checks']),'actual_touch_and_keyboard':any(check['check']=='hasTouch-mobile-actual-touchscreen-tap-and-keyboard-Enter' for check in browser['checks'])},
    'earlier_failed_attempts':'browser-attempts.json (35/45 checks, each exit1; preserved, duplicate checks not added)',
    'source_85_before_after_bound_all_passed_stages':True,'old_API_12_byte_identical':True,'old_e2e_11_byte_identical_to_preparation':True,
    'screens_personally_viewed':{name:sha(browser_path.parent/name) for name in viewed},'visual_findings':findings,
    'paid_calls':0,'product_edits_by_QA':0,'limitations':['Stylized originalSVG R1 only; R2/R3 use existing graybox fallback and are not visual acceptance.','Synthetic-key UI memory test never submitted a real-provider request.','No audio quality/human completion-time/paid-provider quality claim.','RootCMD not launched interactively; owned direct loopback process restart only.','Controlled missing-asset failure not exercised; successful assets-ready, realCanvas pixels, scene recreation, no pageerror checked.'],
}
(folder / 'first-result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'exit_code':0,'API_methods':6,'API_subtests':3,'browser_checks':len(browser['checks']),'visual_findings_pending':3,'old_API_12_match':True,'old_e2e_11_match':True,'first_result_sha256':sha(folder/'first-result.json')}))
