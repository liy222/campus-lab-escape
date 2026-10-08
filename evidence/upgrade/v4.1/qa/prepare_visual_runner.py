"""Prepare new R2 browser adapter from sealed R1 route; no formal execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[4]
qa = Path(__file__).resolve().parent
source = root / 'tests/e2e/run_visual_v40.mjs'
target = root / 'tests/e2e/run_visual_v41.mjs'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
old_e2e = {p.relative_to(root).as_posix(): sha(p) for p in sorted((root / 'tests/e2e').glob('*.mjs')) if p != target}
assert len(old_e2e) == 13
old_api = {p.relative_to(root).as_posix(): sha(p) for p in sorted((root / 'tests/api').glob('*.py'))}
assert len(old_api) == 12
text = source.read_text(encoding='utf-8')

def replace(a, b):
    global text
    assert text.count(a) == 1, a[:160]
    text = text.replace(a, b)

replace('// Independent v4.0 R1 visual adapter;', '// Independent v4.1 R1/R2 visual adapter;')
replace("'evidence/upgrade/v4.0/qa',", "'evidence/upgrade/v4.1/qa',")
text = text.replace('campus-visual-v40-browser-', 'campus-visual-v41-browser-')
replace("state?.room.room_id === 'R1';", "['R1','R2'].includes(state?.room.room_id);")
replace("if(['r1_symbols','r1_fuse','r1_photo'].includes(id)) {\n      await http(page,'canvas-inspect:r1_cabinet',()=>canvasInput(page,'r1_cabinet'));\n      await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view','r1_cabinet');\n    }", """if(['r1_symbols','r1_fuse','r1_photo'].includes(id)) {
      await http(page,'canvas-inspect:r1_cabinet',()=>canvasInput(page,'r1_cabinet'));
      await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view','r1_cabinet');
    }
    if(state.room.room_id==='R2' && !await page.locator(`.game-canvas-host .scene-keyboard-hotspot[data-object-id="${id}"][data-scene-action="object"]`).count()) {
      const parent=['research_strip','access_card'].includes(id)?'r2_monitor':id==='r2_service_label'?'r2_powerbox':null;
      assert(parent,'Expected visible R2 canvas hotspot: '+id);
      await http(page,'canvas-inspect:'+parent,()=>canvasInput(page,parent));
      await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view',parent);
    }""")
replace("()=>page.locator(`.closeup-actions [data-scene-action=\"${action.tool}\"][data-target-id=\"${id}\"]`).click()", "()=>state.room.room_id==='R2'?canvasInput(page,id,action.tool):page.locator(`.closeup-actions [data-scene-action=\"${action.tool}\"][data-target-id=\"${id}\"]`).click()")
replace("async function login(page, username, password, expected = 200) {\n  await select(page, 'r2_monitor'); await page.getByRole('button', { name: /^互动$/ }).click();", "async function login(page, username, password, expected = 200) {\n  await select(page, 'r2_monitor'); if(!visual()) await page.getByRole('button', { name: /^互动$/ }).click();")
replace("if(visual()) {await select(page,'r1_door');return http(page,'move:'+destination,()=>page.locator('.closeup-actions [data-scene-action=\"move\"]').click(),expected);}", """if(visual()) {
    if(state.room.room_id==='R1') {await select(page,'r1_door');return http(page,'move:'+destination,()=>page.locator('.closeup-actions [data-scene-action="move"]').click(),expected);}
    if(destination==='R1') {await roomView(page);return http(page,'move:'+destination,()=>canvasInput(page,'return_R1','move'),expected);}
    await select(page,'r2_door');return http(page,'move:'+destination,()=>canvasInput(page,'r2_door','move'),expected);
  }""")
replace("async function openCircuit(page) { await select(page,'r2_powerbox'); await page.getByRole('button',{name:/^互动$/}).click(); await expect(page.locator('.circuit-submit')).toBeVisible(); }", """async function openCircuit(page) {
  await select(page,'r2_powerbox');if(!visual()) await page.getByRole('button',{name:/^互动$/}).click();
  await expect(page.locator('.circuit-submit')).toBeVisible();
  if(visual()) {await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-circuit-status',state.minigames.circuit.status);await expect(page.locator('.scene-keyboard-hotspot[data-module-id]')).toHaveCount(9);}
}""")
replace("async function rotate(page, id) { return http(page,'rotate:'+id,() => page.locator(`.circuit-cell[data-module-id=\"${id}\"]`).click()); }", """async function rotate(page, id) {
  const before=structuredClone(state),module=before.minigames.circuit.modules.find(module=>module.module_id===id);assert(module);
  const body=await http(page,'rotate:'+id,()=>visual()?moduleInput(page,id):page.locator(`.circuit-cell[data-module-id="${id}"]`).click());
  assert.equal(state.minigames.circuit.modules.find(module=>module.module_id===id).rotation,(module.rotation+1)%4);
  assert.equal(state.device_states.powerbox,'FUSE_INSTALLED');assert.equal(state.progress.power_on,false);
  if(visual()) {assert.equal(body.data.receipt.tool,'rotate_circuit');await expect(page.locator(`.scene-keyboard-hotspot[data-module-id="${id}"]`)).toHaveAttribute('data-rotation',String((module.rotation+1)%4));}
  return body;
}""")
replace("await observe(page, 'r2_door'); await interact(page, 'r2_door');", "await r2Checkpoint(page,'R2-initial-dark-no-tray-no-service');await observe(page, 'r2_door'); await interact(page, 'r2_door');")
replace("await observe(page, 'r2_maintenance'); await observe(page, 'r2_powerbox');\n  await interact(page, 'r2_powerbox'); await interact(page, 'r2_powerbox'); await use(page, 'fuse', 'r2_powerbox');", """await observe(page,'r2_maintenance');await r2Checkpoint(page,'R2-maintenance-original-text');
  await observe(page,'r2_powerbox');await r2Checkpoint(page,'R2-powerbox-CLOSED');
  await interact(page,'r2_powerbox');assert.equal(state.device_states.powerbox,'OPEN');await r2Checkpoint(page,'R2-powerbox-OPEN');
  await interact(page,'r2_powerbox');assert.equal(state.device_states.powerbox,'MISSING_FUSE');await r2Checkpoint(page,'R2-powerbox-MISSING_FUSE');
  await observe(page,'r2_monitor');const beforeWrongFuse=structuredClone(state);await use(page,'fuse','r2_monitor',409);countedMistake(beforeWrongFuse);await r2Checkpoint(page,'R2-wrong-held-fuse-keeps-dark-and-off');
  await use(page,'fuse','r2_powerbox');await r2Checkpoint(page,'R2-powerbox-FUSE_INSTALLED');""")
replace("assert.equal(await page.locator('.circuit-cell').count(),9);", "assert.equal(await page.locator('.scene-keyboard-hotspot[data-module-id]').count(),9);")
replace("const initialModule = state.minigames.circuit.modules[0]; await rotate(page,initialModule.module_id);", """const initialModule=state.minigames.circuit.modules[0];
  const beforeKeyboard=structuredClone(state);await http(page,'R2-independent-keyboard-module',()=>moduleInput(page,initialModule.module_id,true));
  assert.equal(state.minigames.circuit.modules[0].rotation,(beforeKeyboard.minigames.circuit.modules[0].rotation+1)%4);
  assert.equal(state.device_states.powerbox,'FUSE_INSTALLED');assert.equal(state.progress.power_on,false);
  checks.push({check:'R2-independent-keyboard-public-circuit-rotation',passed:true,module_id:initialModule.module_id});""")
replace("await http(page,'state',() => page.getByRole('button',{name:'同步进度',exact:true}).click(),200,'/state'); assert.deepEqual(state,beforeBoardRestart);", "await menu(page);await http(page,'state',() => page.getByRole('button',{name:'同步进度',exact:true}).click(),200,'/state'); assert.deepEqual(state,beforeBoardRestart);")
replace("await expect(page.locator('.circuit-cell').first()).toBeDisabled();", "await expect(page.locator('.scene-keyboard-hotspot[data-module-id]').first()).toBeDisabled();await r2Checkpoint(page,'R2-CIRCUIT_READY-still-dark-switch-required');await roomView(page);await r2Checkpoint(page,'R2-dark-overview-before-switch');const r2DarkOverview=sha(await page.locator('.game-canvas-host canvas').screenshot());")
replace("await interact(page,'r2_powerbox'); await observe(page,'r2_service_label'); assert.equal(state.statistics.hidden_found,2);", """await interact(page,'r2_powerbox');assert.equal(state.device_states.powerbox,'POWER_ON');assert.equal(state.progress.power_on,true);
  await r2Checkpoint(page,'R2-POWER_ON-bright-service-present');
  await roomView(page);await r2Checkpoint(page,'R2-bright-overview-after-switch');assert.notEqual(sha(await page.locator('.game-canvas-host canvas').screenshot()),r2DarkOverview);checks.push({check:'R2-real-overview-pixels-differ-after-manual-server-switch',passed:true});
  const powerArchive=await appendMoment(page,'已通电时刻');await retrieveMoment(page,partialArchive);await assertSnapshotIdle(page);await retrieveMoment(page,powerArchive);await assertSnapshotIdle(page);
  await roomView(page);await r2Checkpoint(page,'R2-restored-powered-snapshot');
  await observe(page,'r2_service_label');await r2Checkpoint(page,'R2-service-label-original-story');assert.equal(state.statistics.hidden_found,2);""")
replace("await observe(page, 'r2_monitor'); await interact(page, 'r2_monitor'); await interact(page, 'r2_monitor');", """await observe(page,'r2_monitor');await r2Checkpoint(page,'R2-monitor-OFF');
  await interact(page,'r2_monitor');assert.equal(state.device_states.computer,'BOOTING');await r2Checkpoint(page,'R2-monitor-BOOTING');
  await interact(page,'r2_monitor');await r2Checkpoint(page,'R2-monitor-LOGIN_LOCKED');""")
replace("await login(page, 'LAB-42', '2117'); assert.equal(state.device_states.computer, 'UNLOCKED');", "await login(page, 'LAB-42', '2117'); assert.equal(state.device_states.computer, 'UNLOCKED');await r2Checkpoint(page,'R2-monitor-UNLOCKED-no-items-yet');")
replace("await http(page, 'state', () => page.getByRole('button', { name: '同步进度', exact: true }).click(), 200, '/state');\n  assert.deepEqual(state, beforeRestart);", "await menu(page);await http(page, 'state', () => page.getByRole('button', { name: '同步进度', exact: true }).click(), 200, '/state');\n  assert.deepEqual(state, beforeRestart);")
replace("await select(page, 'r2_monitor'); await page.getByRole('button', { name: /^互动$/ }).click();\n  await expect(page.getByLabel('用户名', { exact: true })).toHaveValue('');", "await select(page,'r2_monitor');\n  await expect(page.getByLabel('用户名', { exact: true })).toHaveValue('');")
replace("const before=structuredClone(state),row=page.locator(`.save-slot[data-save-id=\"${moment.slot.save_id}\"]`);", "const before=structuredClone(state),restoreAnimationCount=(await markers(page)).length,row=page.locator(`.save-slot[data-save-id=\"${moment.slot.save_id}\"]`);")
replace("await menu(page);await expect(row).toBeVisible();", "await menu(page);await expect(row).toBeVisible();if(visual()){assert.equal((await markers(page)).length,restoreAnimationCount,'Archive restore must not produce progression animation');await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-animation','idle');}")
text = text.replace("'R2-login-graybox'", "'R2-login-visual'").replace("'R2-graybox.png'", "'R2-visual.png'")
replace("await login(page, 'LAB-42', '2117'); await interact(page, 'r2_monitor');\n  await observe(page, 'research_strip'); await interact(page, 'research_strip'); await observe(page, 'access_card'); await interact(page, 'access_card');", """await login(page,'LAB-42','2117');await interact(page,'r2_monitor');assert.equal(state.device_states.computer,'DATA_READ');
  assert(state.objects.some(object=>object.object_id==='research_strip'));assert(state.objects.some(object=>object.object_id==='access_card'));
  assert(!state.inventory.some(item=>['research_strip','access_card'].includes(item.item_id)));await r2Checkpoint(page,'R2-DATA_READ-tray-items-not-auto-taken');
  await observe(page,'research_strip');await interact(page,'research_strip');assert(state.inventory.some(item=>item.item_id==='research_strip'));assert(!state.objects.some(object=>object.object_id==='research_strip'));assert(state.objects.some(object=>object.object_id==='access_card'));
  await observe(page,'access_card');await interact(page,'access_card');await r2Checkpoint(page,'R2-tray-both-items-taken');""")
text = text.replace("await expect(page.locator('.save-slot')).toHaveCount(5);", "await expect(page.locator('.save-slot')).toHaveCount(6);")
replace("await retrieveMoment(page,earlyArchive);await retrieveMoment(page,partialArchive);await retrieveMoment(page,wonArchive);", "await retrieveMoment(page,earlyArchive);await retrieveMoment(page,partialArchive);await assertSnapshotIdle(page);await retrieveMoment(page,powerArchive);await assertSnapshotIdle(page);await retrieveMoment(page,wonArchive);")
replace("archive_count:4,legacy_count:1", "archive_count:5,legacy_count:1")
replace("check:'four-immutable-archives-plus-old-slot-persist-reset-refresh-OSrestart'", "check:'five-immutable-archives-plus-old-slot-persist-reset-refresh-OSrestart'")
replace("await touchSmoke(service);", "await touchSmoke(service);await touchR2Smoke(service);")
replace("try {\n  assert(fs.existsSync(chromePath));", r'''async function moduleInput(page,id,keyboard=false,touch=false) {
  const host=page.locator('.game-canvas-host[data-room="R2"]');await expect(host).toHaveAttribute('data-assets-ready','true');
  const zone=host.locator(`.scene-keyboard-hotspot[data-module-id="${id}"]`);await expect(zone).toHaveCount(1);await expect(zone).toBeEnabled();
  if(keyboard) {await zone.focus();await zone.press('Enter');return;}
  const values=(await zone.getAttribute('data-bounds')).split(',').map(Number),box=await host.locator('canvas').boundingBox();assert(box);
  const x=box.x+(values[0]+values[2]/2)*box.width/1600,y=box.y+(values[1]+values[3]/2)*box.height/900;
  assert.equal(await page.evaluate(({x,y})=>document.elementFromPoint(x,y)?.tagName,{x,y}),'CANVAS');
  if(touch) await page.touchscreen.tap(x,y);else await page.mouse.click(x,y);
}
async function assertSnapshotIdle(page) {
  await closeDrawer(page);await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-animation','idle');
  await expect(page.locator('.game-canvas-host canvas')).toHaveCount(1);
  checks.push({check:'R2-restored-snapshot-one-canvas-no-progression-animation',powerbox:state.device_states.powerbox,passed:true});
}
async function r2Checkpoint(page,label) {
  assert.equal(state.room.room_id,'R2');await closeDrawer(page);
  const host=page.locator('.game-canvas-host');await expect(host).toHaveAttribute('data-room','R2');await expect(host).toHaveAttribute('data-assets-ready','true');
  await expect(host).toHaveAttribute('data-powerbox-state',state.device_states.powerbox);await expect(host).toHaveAttribute('data-computer-state',state.device_states.computer);
  await expect(host.locator('canvas')).toHaveCount(1);assert.equal(await page.locator('.object-grid').count(),0);
  if(state.device_states.powerbox!=='POWER_ON') {assert(!state.objects.some(object=>object.object_id==='r2_service_label'));assert.equal(await page.locator('.scene-keyboard-hotspot[data-object-id="r2_service_label"]').count(),0);}
  if(state.device_states.computer!=='DATA_READ') {assert(!state.objects.some(object=>['research_strip','access_card'].includes(object.object_id)));assert.equal(await page.locator('.scene-keyboard-hotspot[data-object-id="research_strip"],.scene-keyboard-hotspot[data-object-id="access_card"]').count(),0);}
  const measured=await page.evaluate(()=>{
    const nodes=selector=>[...document.querySelectorAll(selector)].filter(node=>node.getClientRects().length);
    const rect=node=>node.getBoundingClientRect(),overlap=(a,b)=>Math.min(a.right,b.right)>Math.max(a.left,b.left)&&Math.min(a.bottom,b.bottom)>Math.max(a.top,b.top);
    const feedback=nodes('.feedback p').map(rect),content=nodes('.game-hud button,.closeup-reading,.closeup-description,.closeup-controls button,.closeup-controls input,.closeup-controls label').map(rect);
    return {feedback_overlaps:feedback.flatMap(a=>content.filter(b=>overlap(a,b))).length,horizontal_overflow:content.filter(b=>b.left<0||b.right>innerWidth).length};
  });assert.equal(measured.feedback_overlaps,0);assert.equal(measured.horizontal_overflow,0);
  await page.screenshot({path:path.join(folder,label+'.png'),fullPage:true});await canvasPixels(page,label);
  checks.push({check:'R2-public-state-membership-rendering-and-readable-controls',label,powerbox:state.device_states.powerbox,computer:state.device_states.computer,power_on:state.progress.power_on,...measured,passed:true});
}
async function touchR2Smoke(service) {
  // A synthetic context creates its own session; it cannot read another session's archive.
  const context=await browser.newContext({viewport:{width:375,height:812},hasTouch:true,isMobile:true,deviceScaleFactor:1}),page=await context.newPage();
  const errors=[];page.on('pageerror',()=>errors.push('uncaught R2 touch exception'));state=undefined;
  await page.goto(service.frontendURL,{waitUntil:'networkidle'});await http(page,'R2-touch-create',()=>page.getByRole('button',{name:'开始新游戏 →',exact:true}).click(),201,'/api/sessions');
  await observe(page,'r1_clock');await observe(page,'r1_record');await observe(page,'r1_plaque');await observe(page,'sample_slide');await interact(page,'sample_slide');await use(page,'sample_slide','r1_microscope');await observe(page,'r1_microscope');
  await code(page,'r1_cabinet','4217');await interact(page,'r1_cabinet');await observe(page,'r1_fuse');await interact(page,'r1_fuse');
  await observe(page,'r1_door');await interact(page,'r1_door');await move(page,'R2');
  await http(page,'R2-real-touch-maintenance',()=>canvasInput(page,'r2_maintenance','object',false,true));assert(state.clues.some(clue=>clue.object_id==='r2_maintenance'));
  await select(page,'r2_powerbox',true);await http(page,'R2-real-touch-open-box',()=>canvasInput(page,'r2_powerbox','interact',false,true));assert.equal(state.device_states.powerbox,'OPEN');
  await http(page,'R2-keyboard-remove-guard',()=>canvasInput(page,'r2_powerbox','interact',true));assert.equal(state.device_states.powerbox,'MISSING_FUSE');
  await use(page,'fuse','r2_powerbox');await openCircuit(page);const beforeTouchRotate=structuredClone(state),first=state.minigames.circuit.modules[0];
  await http(page,'R2-real-touch-public-circuit-module',()=>moduleInput(page,first.module_id,false,true));assert.equal(state.minigames.circuit.modules[0].rotation,(beforeTouchRotate.minigames.circuit.modules[0].rotation+1)%4);assert.equal(state.device_states.powerbox,'FUSE_INSTALLED');assert.equal(state.progress.power_on,false);
  await r2Checkpoint(page,'R2-real-touch-keyboard-375');assert.equal(errors.length,0);
  checks.push({check:'R2-hasTouch-real-canvas-and-independent-keyboard',passed:true,width:375});await context.close();
}
try {
  assert(fs.existsSync(chromePath));''')
target.write_text(text, encoding='utf-8')
assert all(sha(root / p) == h for p, h in old_e2e.items())
assert all(sha(root / p) == h for p, h in old_api.items())
command = ['C:/Program Files/nodejs/node.exe', '--check', str(target.relative_to(root)).replace('\\', '/')]
run = subprocess.run(command, cwd=root, text=True, capture_output=True)
record = {'status': 'New R2 browser preparation only; no formal visual execution', 'recorded_at': datetime.now(timezone.utc).isoformat(), 'command': command, 'exit_code': run.returncode, 'stdout': run.stdout, 'stderr': run.stderr, 'new_runner': {'path': target.relative_to(root).as_posix(), 'sha256': sha(target)}, 'old_e2e13_sha256': old_e2e, 'old_API12_sha256': old_api, 'old_test_byte_changes': 0, 'formal_visual_runs': 0, 'paid_calls': 0, 'generation_history': [{'exit_code': 1, 'scope': 'First preparation failed on ambiguous new replacement anchor before writing runner; corrected to function-specific anchor; no tests/services executed'}, {'exit_code': 0, 'scope': 'Successful first preparation/Node syntax'}, {'exit_code': run.returncode, 'scope': 'Additional meaningful R2 held-fuse/lighting/touch-circuit cases; Node syntax only'}], 'protocol_status': 'Prepared against Frontend R2 selector blueprint; final SOURCE STOP selector review still required', 'cases': ['Complete original three-room route/R1 regression retained', 'R2 public canvas inspect/interact/use-item/move and independent keyboard/touch', 'Nine circuit rotations via Canvas public module_id/rotation; server submit then separate switch', 'Six power states/five monitor states/screens/hidden label/tray membership', 'Early/slide/partial-circuit/powered/win archives plus legacy slot, cancel/reset/reload/process restart/snapshot-only', 'Original wrong-item/login/circuit/sequence stats and UTC settlement assertions retained', 'Actual rendered Canvas pixels/readable feedback/screens/no pageerror'], 'limitations': ['Static Node syntax only; no new R2 run or screenshot.', 'No root CMD interactive startup/controlled missing-asset/audio quality/human or paid-provider claim.', 'New adapter will be finalized against actual stable public DOM before formal Main candidate GO.']}
(qa / 'preparation-runner.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'exit_code': run.returncode, 'old_e2e13_match': True, 'old_API12_match': True, 'formal_runs': 0, 'new_runner_sha256': sha(target)}))
raise SystemExit(run.returncode)
