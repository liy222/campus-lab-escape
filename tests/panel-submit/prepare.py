"""Prepare focused QA without executing product code or changing old evidence."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'evidence/integration/panel-submit/qa'
OUT.mkdir(parents=True, exist_ok=True)
plan = json.loads((ROOT / 'evidence/integration/panel-submit/plan.json').read_text(encoding='utf-8-sig'))
baseline = plan['baseline_head']
paths = ['frontend/src/components/Room3.tsx', 'frontend/src/App.tsx', 'backend/app/domain/mini_rules.py', 'backend/app/domain/puzzle_rules.py']
evidence = []
for name in paths:
    command = ['git', 'show', f'{baseline}:{name}']
    p = subprocess.run(command, cwd=ROOT, capture_output=True)
    assert p.returncode == 0, name
    text = p.stdout.decode('utf-8')
    evidence.append({'path': name, 'command': command, 'exit_code': p.returncode,
                     'git_blob_sha256': hashlib.sha256(p.stdout).hexdigest(),
                     'selected_lines': [{'line': i, 'text': line} for i, line in enumerate(text.splitlines(), 1)
                                        if any(s in line for s in ('selectedItemId', "input.kind === 'sequence-device'", "d.exit == 'FINAL_CHECK'", 'CARD_ACCEPTED', '启动终检', 'sequence-submit'))]})
static = {'kind': 'independent_static_baseline_investigation_not_formal_QA', 'baseline_head': baseline,
          'evidence': evidence, 'browser_reproduction_executed': False,
          'reason': 'Frontend ownership is concurrent; avoid certifying a potentially stale production dist or mutating source.',
          'findings': ['Selected persistent access_card routes device click to use_item instead of local draft.',
                       'CARD_ACCEPTED has no panel start control; submit affordance requires FINAL_CHECK from existing exit_door interact.',
                       'Selected card also routes overview panel object click through App.visualObject to use_item.'],
          'paid_calls': 0}
(OUT / 'reproduction.json').write_text(json.dumps(static, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
original = (ROOT / 'tests/handpainted/run_browser.mjs').read_text(encoding='utf-8-sig')
prefix = original[:original.index('async function isolation(')]
prefix = prefix.replace("const candidatePath=process.argv[2],only=(process.argv.find(x=>x.startsWith('--only='))||'--only=all').slice(7);", "const candidatePath=process.argv[2];")
prefix = prefix.replace("assert(['all','remaining','presentation'].includes(only));", '')
prefix = prefix.replace("const protocol=read('evidence/integration/handpainted/qa/preparation.json');\nassert(protocol.protocol_ready,'Final owner stage selector must be bound before formal execution');", "const plan=read('evidence/integration/panel-submit/plan.json');\nconst protocol={immutable_sha256:Object.fromEntries(Object.entries(plan.baseline_source_sha256).filter(([p])=>p!=='frontend/src/components/Room3.tsx'))};")
prefix = prefix.replace('evidence/integration/handpainted/qa', 'evidence/integration/panel-submit/qa').replace('campus-handpainted-', 'campus-panel-submit-')
prefix = prefix.replace("if(r.status()!==status){", "if(r.status()!==status){")
prefix = prefix.replace("assert(b.ok,b.error?.code);state=b.data.visible_state;return b;", "if(status>=400)assert(!b.ok);else assert(b.ok,b.error?.code);if(b.data?.visible_state)state=b.data.visible_state;else if(b.visible_state)state=b.visible_state;return b;")
prefix = prefix.replace("page.waitForResponse(r=>", "page.waitForResponse(r=>")
(ROOT / 'tests/panel-submit/run_browser.mjs').write_text(prefix + (ROOT / 'tests/panel-submit/browser-body.mjs').read_text(encoding='utf-8'), encoding='utf-8')
print(json.dumps({'preparation': str(OUT / 'reproduction.json'), 'exit_code': 0}))
