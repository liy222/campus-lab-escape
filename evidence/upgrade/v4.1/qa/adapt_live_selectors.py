"""Static QA-only adaptation to actual R2 DOM; never run product services."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[4]
qa = Path(__file__).resolve().parent
target = root / 'tests/e2e/run_visual_v41.mjs'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
prior_path = qa / 'preparation-runner.json'
prior = json.loads(prior_path.read_text(encoding='utf-8'))
for key in ['old_e2e13_sha256', 'old_API12_sha256']:
    assert all(sha(root / p) == h for p, h in prior[key].items())
assert sha(target) == prior['new_runner']['sha256']
source = target.read_text(encoding='utf-8')
before_sha = sha(target)

def replace(a, b, count=1):
    global source
    assert source.count(a) == count, a[:140]
    source = source.replace(a, b)

replace("await page.getByLabel('用户名', { exact: true }).fill(username); await page.getByLabel('密码', { exact: true }).fill(password);", "await expect(page.locator('.login-form')).toHaveCount(1);await expect(page.locator('#terminal-username')).toHaveCount(1);await expect(page.locator('#terminal-password')).toHaveCount(1);\n  await page.locator('#terminal-username').fill(username);await page.locator('#terminal-password').fill(password);")
replace("() => page.locator('.login-form').getByRole('button', { name: '提交登录', exact: true }).click()", "() => visual()?page.locator('.login-form [data-scene-action=\"submit_login\"][data-target-id=\"r2_monitor\"]').click():page.locator('.login-form').getByRole('button', { name: '提交登录', exact: true }).click()")
replace("await expect(page.getByLabel('用户名', { exact: true })).toHaveValue(''); await expect(page.getByLabel('密码', { exact: true })).toHaveValue('');", "await expect(page.locator('#terminal-username')).toHaveCount(1);await expect(page.locator('#terminal-password')).toHaveCount(1);\n  await expect(page.locator('#terminal-username')).toHaveValue('');await expect(page.locator('#terminal-password')).toHaveValue('');")
replace("if(action.tool==='take'||id==='r1_cabinet') await page.locator('.game-canvas-host canvas').screenshot", "const beforeActionMarkers=(await markers(page)).length;\n    if(action.tool==='take'||id==='r1_cabinet') await page.locator('.game-canvas-host canvas').screenshot")
replace("await expect.poll(async()=> (await markers(page)).includes(action.tool)).toBe(true);", "await expect.poll(async()=> (await markers(page)).slice(beforeActionMarkers).includes(action.tool)).toBe(true);")
replace("checks.push({check:'receipt-animation-frames-for-independent-visual-review',object_id:id,tool:action.tool,passed:true});", """if(state.room.room_id==='R2'&&action.tool==='take') {
        assert(['research_strip','access_card'].includes(id));assert(state.inventory.some(item=>item.item_id===id));assert(!state.objects.some(object=>object.object_id===id));
        await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view','room');
        assert.equal(await page.locator(`.scene-keyboard-hotspot[data-object-id="${id}"]`).count(),0);
        checks.push({check:'R2-take-removes-visible-object-and-auto-returns-overview',object_id:id,passed:true});
      }
      checks.push({check:'receipt-animation-frames-for-independent-visual-review',object_id:id,tool:action.tool,passed:true});""")
replace(".closeup-controls input,.closeup-controls label').map(rect);", ".closeup-controls input,.closeup-controls label,.crt-login input,.crt-login label,.crt-login button').map(rect);")
replace("await expect(host.locator('canvas')).toHaveCount(1);assert.equal(await page.locator('.object-grid').count(),0);", """await expect(host.locator('canvas')).toHaveCount(1);assert.equal(await page.locator('.object-grid').count(),0);
  const currentView=await host.getAttribute('data-view');
  if(currentView==='r2_monitor'&&state.device_states.computer==='LOGIN_LOCKED') {await expect(page.locator('.crt-login')).toHaveCount(1);await expect(page.locator('#terminal-username')).toHaveCount(1);await expect(page.locator('#terminal-password')).toHaveCount(1);}
  else assert.equal(await page.locator('.crt-login').count(),0);
  if(state.device_states.powerbox==='POWER_ON'&&currentView==='r2_powerbox') {await expect(host.locator('.scene-keyboard-hotspot[data-object-id="r2_service_label"]')).toHaveCount(1);} """)
replace("assert.equal(state.statistics.hidden_found,2);", "assert.equal(state.statistics.hidden_found,2);await roomView(page);await select(page,'r2_powerbox');await http(page,'R2-actual-closeup-service-label-hit',()=>canvasInput(page,'r2_service_label'));await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view','r2_service_label');assert.equal(state.statistics.hidden_found,2);")
replace("assert.equal(state.device_states.powerbox,'FUSE_INSTALLED');assert.equal(state.progress.power_on,false);\n  if(visual())", "assert.equal(state.device_states.powerbox,'FUSE_INSTALLED');assert.equal(state.progress.power_on,false);assert.equal(state.revision,before.revision+1);\n  if(visual())")
target.write_text(source, encoding='utf-8')
for key in ['old_e2e13_sha256', 'old_API12_sha256']:
    assert all(sha(root / p) == h for p, h in prior[key].items())
command = ['C:/Program Files/nodejs/node.exe', '--check', target.relative_to(root).as_posix()]
syntax = subprocess.run(command, cwd=root, text=True, capture_output=True)
read_paths = ['frontend/src/game/Room2Scene.ts', 'frontend/src/game/GameCanvas.tsx', 'frontend/src/game/bridge.ts', 'frontend/src/components/Room2.tsx', 'frontend/src/components/RoomChrome.tsx', 'frontend/src/assets/manifest.ts', 'frontend/src/App.tsx', 'frontend/src/style.css']
record = {
    'status': 'R2 current public-selector static adaptation SOURCE STOP; formal execution waits Main frozen candidate GO',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'command': command, 'exit_code': syntax.returncode, 'stdout': syntax.stdout, 'stderr': syntax.stderr,
    'prior_preparation': prior_path.relative_to(root).as_posix(), 'prior_preparation_sha256': sha(prior_path),
    'new_runner': {'path': target.relative_to(root).as_posix(), 'before_sha256': before_sha, 'sha256': sha(target)},
    'read_source_sha256_at_preparation_only_not_frozen': {p: sha(root / p) for p in read_paths},
    'protocol': {'CRT': 'Exactly one React .crt-login and #terminal-username/password, button data-scene-action=submit_login targetr2_monitor; USER/PASS labels use same field ids', 'tray': 'real object_id research_strip/access_card, taken object leavesobjects and auto viewroom', 'service_label': 'Overview and powerbox closeup use real r2_service_label; closeup image180x96 and hitbox180x250 share center that lies inside actual rendered image', 'circuit': 'Actual Canvas9 zones with module_id/rotation; public completed modules disabled, server submit_circuit remains separate from total-switch interact'},
    'preserved': ['Full original three-room route, R1 regression, all old game/state/counter assertions', 'Selected archives/cancel/reset/reload/process restart/replayedfalse and namespace checks', 'Original13 e2e and12API source bytes', 'No product edits, formal browser execution, paid requests or credentials'],
    'formal_visual_runs': 0, 'product_edits': 0, 'old_test_byte_changes': 0, 'paid_calls': 0,
    'old_e2e13_sha256': prior['old_e2e13_sha256'], 'old_API12_sha256': prior['old_API12_sha256'],
    'limitations': ['Current source reads are static preparation and may change until owner SOURCE STOP.', 'No actual browser/screenshot acceptance yet; only Node syntax.', 'Final candidate source hashes and actual before/after outputs will be bound by formal GO.']
}
(qa / 'preparation-live-selectors.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'exit_code': syntax.returncode, 'old_e2e13_match': True, 'old_API12_match': True, 'formal_visual_runs': 0, 'new_runner_sha256': sha(target)}))
raise SystemExit(syntax.returncode)
