"""Bind final owner protocol and Main frozen GO; generate only new QA runner."""
from pathlib import Path
import hashlib
import json
import shutil
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'evidence/integration/handpainted/qa'
prep = OUT / 'preparation.json'
epoch = OUT / 'preparation-epochs/final-bind-before'
epoch.mkdir(parents=True, exist_ok=True)
shutil.copyfile(prep, epoch / 'preparation.json')
shutil.copyfile(ROOT / 'tests/handpainted/run_browser.mjs', epoch / 'run_browser.mjs')
protocol = json.loads(prep.read_text(encoding='utf-8'))
candidate = ROOT / 'evidence/integration/handpainted/candidate.json'
expected = 'e7341a6d778c0af4295c791946ec92633347287e1ae4a4d8813af3c58ab39f81'
assert hashlib.sha256(candidate.read_bytes()).hexdigest() == expected
owner = ROOT / 'evidence/integration/handpainted/frontend/report.json'
report = json.loads(owner.read_text(encoding='utf-8-sig'))
assert report['status'] == 'SOURCE STOP'
protocol.update(protocol_ready=True, status='Final sealed Owner protocol bound; explicit Main frozen candidate formal GO received',
    candidate='evidence/integration/handpainted/candidate.json', candidate_sha256=expected,
    owner_report_sha256=hashlib.sha256(owner.read_bytes()).hexdigest(),
    painted_frames_protocol=report['render_observers']['canvas.data-painted-frames'])
protocol['limitations']=['Final Owner development evidence not counted as independent QA.', 'Source freeze verified per formal run; visual result requires actual representative PNG inspection.']
prep.write_text(json.dumps(protocol, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
old=(ROOT/'tests/e2e/run_closeup_panel.mjs').read_text(encoding='utf-8-sig')
scaffold=old[:old.index('async function run(){')].replace('evidence/integration/closeup-panel/qa','evidence/integration/handpainted/qa').replace('campus-closeup-panel-','campus-handpainted-').replace("assert(['all','r1','r2','r3','remaining'].includes(only));", "assert.equal(only,'all');")
(ROOT/'tests/handpainted/run_browser.mjs').write_text(scaffold+(ROOT/'tests/handpainted/browser-body.mjs').read_text(encoding='utf-8'),encoding='utf-8')
print(json.dumps({'protocol_ready':True,'candidate_sha256':expected,'formal_executions':0}))
