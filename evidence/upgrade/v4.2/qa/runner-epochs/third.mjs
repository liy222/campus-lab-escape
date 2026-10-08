// Independent v4.2 final visual adapter preparation; complete prior route/assertions retained, owned mock DBs.
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const requireFrontend = createRequire(path.join(root, 'frontend/package.json'));
const { chromium, expect } = requireFrontend('@playwright/test');
const protocolPath = path.join(root,'evidence/upgrade/v4.2/qa/protocol-final.json');
assert(fs.existsSync(protocolPath),'PREPARATION ONLY: final actual selectors and Main freeze not yet bound');
const protocol = JSON.parse(fs.readFileSync(protocolPath,'utf8'));
assert.equal(protocol.ready_for_Main_formal_GO,true,'Final selector binding incomplete');
const candidatePath = process.argv[2];
const only=(process.argv.find(value=>value.startsWith('--only='))||'--only=full').slice(7);
assert(['full','audio','gates','touch-r3','production','legacy','victory','remaining'].includes(only),'Unknown necessary-scope mode');
assert(path.basename(candidatePath||'')!=='baseline-candidate.json','Formal runs require the Main frozen candidate, never baseline preparation JSON');
assert(candidatePath, 'Pass a frozen Main candidate JSON explicitly');
const candidate = JSON.parse(fs.readFileSync(path.resolve(root, candidatePath), 'utf8').replace(/^\uFEFF/, ''));
const folder = path.join(root, 'evidence/upgrade/v4.2/qa', new Date().toISOString().replace(/[-:.]/g, '') + '-browser');
fs.mkdirSync(folder, { recursive: true });
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'campus-visual-v42-browser-'));
const python = 'C:\\Users\\liyh\\.conda\\envs\\1\\python.exe';
const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const children = [], checks = [], issues = [], commands = [], serviceOutput = [];
const started = new Date().toISOString();
let browser, state, latestAction;
function briefError(error) { return String(error.message || error).split(/\r?\n/)[0].slice(0,240); }
function diagnosticError(error) {
  const result={error:briefError(error),stack_frames:String(error.stack||'').split(/\r?\n/).filter(line=>/^\s+at\s/.test(line)).map(line=>line.trim())};
  const matcher=error.matcherResult;
  if(matcher&&['boolean','number'].includes(typeof matcher.actual)) result.actual=matcher.actual;
  if(matcher&&['boolean','number'].includes(typeof matcher.expected)) result.expected=matcher.expected;
  return result;
}
function sha(bytes) { return crypto.createHash('sha256').update(bytes).digest('hex'); }
function sourceHashes() {
  return Object.fromEntries(Object.keys(candidate.source_sha256).map(relative => [relative, sha(fs.readFileSync(path.join(root, relative)))]));
}
const preservedTests=JSON.parse(fs.readFileSync(path.join(root,'evidence/upgrade/v4.2/qa/preparation.json'),'utf8')).old_test_sha256;
for(const [p,h] of Object.entries(preservedTests))assert.equal(sha(fs.readFileSync(path.join(root,p))),h,'Old test byte guard: '+p);
const before = sourceHashes();
assert.deepEqual(before, candidate.source_sha256, 'Current source differs from frozen candidate');
function publicGame(value) { return Object.fromEntries(Object.entries(value).filter(([key]) => !['revision', 'generation', 'save'].includes(key))); }
function stages(value) { return { room: value.room.room_id, devices: value.device_states, slots: value.puzzle_states, progress: value.progress, statistics: value.statistics, settlement: value.settlement, minigames: value.minigames ? Object.fromEntries(Object.entries(value.minigames).map(([key, game]) => [key, game ? { status: game.status, ...(game.modules ? { rotations: game.modules.map(module => module.rotation) } : {}) } : null])) : undefined }; }
function record(label, body, status) {
  const previous = state;
  state = body.ok ? body.data.visible_state : body.visible_state || state;
  if (!body.ok || !previous || JSON.stringify(stages(previous)) !== JSON.stringify(stages(state)) || ['save', 'restore', 'reset', 'state', 'create'].includes(label)) {
    checks.push({ check: label, http_status: status, error: body.error?.code || null,
      revision: state?.revision, generation_changed: !!previous && previous.generation !== state.generation,
      ...(state ? stages(state) : {}), clues: state?.clues.length, inventory: state?.inventory.map(item => item.item_id) });
  }
}
function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer(); server.once('error', reject);
    server.listen(0, '127.0.0.1', () => { const port = server.address().port; server.close(error => error ? reject(error) : resolve(port)); });
  });
}
function start(label, executable, args, env, cwd = root) {
  const selected = { AI_PROVIDER: 'mock', PYTHONUTF8: '1', ...env };
  commands.push({ label, executable, arguments: args, public_environment: selected, cwd });
  const child = spawn(executable, args, { cwd, env: { ...process.env, ...selected }, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  children.push(child);
  child.on('error', error => issues.push({ check: 'start', label, error: briefError(error) }));
  for (const stream of ['stdout', 'stderr']) child[stream].on('data', bytes => serviceOutput.push({ label, text: bytes.toString() }));
  return child;
}
async function ready(url) {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) { try { if ((await fetch(url)).ok) return; } catch {} await new Promise(resolve => setTimeout(resolve, 100)); }
  throw new Error('Owned local service startup timed out');
}
async function stop(child) {
  if (!child.pid || child.exitCode !== null || child.signalCode !== null) return;
  const result = spawnSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], { encoding: 'utf8', windowsHide: true });
  checks.push({ check: 'stop-owned-process-tree', pid: child.pid, exit_code: result.status });
  assert.equal(result.status, 0);
  if (child.exitCode === null && child.signalCode === null) await new Promise(resolve => child.once('exit', resolve));
}
async function pair(version) {
  const backendPort = await freePort(); let frontendPort = await freePort();
  while (frontendPort === backendPort) frontendPort = await freePort();
  const backendURL = `http://127.0.0.1:${backendPort}`, frontendURL = `http://127.0.0.1:${frontendPort}`;
  const backendArgs = ['-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', String(backendPort), '--no-access-log'];
  const backendEnv = { GAMEPLAY_VERSION: version, SQLITE_PATH: path.join(temp, version + '.sqlite') };
  const backend = start(version + '-backend', python, backendArgs, backendEnv);
  start(version + '-frontend', process.execPath, [path.join(root, 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', String(frontendPort), '--strictPort'], { CAMPUS_BACKEND_URL: backendURL, VITE_GAMEPLAY_VERSION: version }, path.join(root, 'frontend'));
  await Promise.all([ready(backendURL + '/api/health'), ready(frontendURL)]);
  return { backend, backendArgs, backendEnv, backendURL, frontendURL };
}
async function http(page, label, operation, expected = 200, suffix = '/actions') {
  const waiting = page.waitForResponse(response => new URL(response.url()).pathname.endsWith(suffix) && response.request().method() === (suffix === '/state' ? 'GET' : 'POST')).catch(error=>({qaWaitError:error}));
  const soundBefore=audibleAttempts(await audioEvents(page)).length;
  const audioReady=await page.locator('.presentation-observer[data-audio-state="ready"]').count()===1;
  const muted=await page.locator('.presentation-observer[data-audio-state="muted"]').count()===1;
  await operation(); const response = await waiting;if(response.qaWaitError)throw response.qaWaitError;const body = await response.json();
  if(suffix==='/actions'&&body.ok&&body.data.receipt)latestAction={request_body:response.request().postData(),pathname:new URL(response.url()).pathname};
  record(label, body, response.status()); assert.equal(response.status(), expected, label + ' HTTP result');
  if(state?.level_version==='3.4.0'&&suffix==='/actions'&&audioReady) {
    const hasCue=body.ok?body.data.receipt?.changed&&!body.data.replayed:!['NETWORK_ERROR','SERVICE_UNAVAILABLE','FORBIDDEN_SESSION'].includes(body.error?.code);
    if(hasCue) await expect.poll(async()=>audibleAttempts(await audioEvents(page)).length).toBe(soundBefore+1);
    else {await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));assert.equal(audibleAttempts(await audioEvents(page)).length,soundBefore);}
    const actualAudio=await audioEvents(page);assert(actualAudio.filter(event=>event.kind==='context-created').every(event=>event.gesture_count>0),'Audio context created without trusted gesture');assert(audibleAttempts(actualAudio).every(event=>event.gesture_count>0&&event.state==='running'),'Cue did not start in running gesture-unlocked AudioContext');
    checks.push({check:'actual-one-shot-audio-server-action',label,http_status:response.status(),one_shots:hasCue?1:0,trusted_gesture:await page.evaluate(()=>window.qaTrustedGestures>0),passed:true});
  }else if(muted&&suffix==='/actions') {await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));assert.equal(audibleAttempts(await audioEvents(page)).length,soundBefore);checks.push({check:'muted-actual-action-no-one-shot',label,passed:true});}
  return body;
}

function visual() { return state?.level_version === '3.4.0' && ['R1','R2','R3','EXIT'].includes(state?.room.room_id); }
async function closeDrawer(page) {
  const backdrop=page.getByRole('button',{name:'关闭面板',exact:true});
  if(await backdrop.isVisible()) await backdrop.click({position:{x:5,y:5}});
}
async function menu(page) {
  if(visual() && !await page.locator('.save-panel').isVisible()) {
    await closeDrawer(page); if(state.status==='won') await page.locator('.victory-records').click();else await page.getByRole('button',{name:'游戏菜单',exact:true}).click();
  }
}
async function partner(page) {
  if(visual() && !await page.locator('#hint-level').isVisible()) {
    await closeDrawer(page); await page.getByRole('button',{name:'AI 探索伙伴',exact:true}).click();
  }
}
async function roomView(page) {
  await closeDrawer(page);
  const cancel=page.locator('.cancel-item');if(await cancel.isVisible()) await cancel.click();
  if(await page.locator('.closeup-back').isVisible()) {
    const before=structuredClone(state);await page.locator('.closeup-back').click();assert.deepEqual(state,before);
  }
  await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view','room');
}
async function canvasSizeReady(host) {
  await expect.poll(async()=>host.evaluate(node=>{const canvas=node.querySelector('canvas');if(!canvas)return false;const a=node.getBoundingClientRect(),b=canvas.getBoundingClientRect();return b.width>0&&Math.abs(a.width-b.width)<=1&&Math.abs(b.width/b.height-1600/900)<=.01;})).toBe(true);
}
async function settledRoomTransition(page) {
  const transition=page.locator('.room-transition');if(await transition.count())await expect.poll(async()=>Number(await transition.evaluate(node=>getComputedStyle(node).opacity))).toBe(0);
}
async function canvasInput(page,id,tool='object',keyboard=false,touch=false) {
  const host=page.locator('.game-canvas-host');await expect(host).toHaveAttribute('data-assets-ready','true');
  await expect(host.locator('canvas')).toHaveCount(1);await canvasSizeReady(host);
  const hotspot=host.locator(`.scene-keyboard-hotspot[data-object-id="${id}"][data-scene-action="${tool}"]`);
  await expect(hotspot).toHaveCount(1);await expect(hotspot).toBeEnabled();
  if(keyboard) { await hotspot.focus();await hotspot.press('Enter'); }
  else {
    const values=(await hotspot.getAttribute('data-bounds')).split(',').map(Number), box=await host.locator('canvas').boundingBox();
    assert(box);const x=box.x+(values[0]+values[2]/2)*box.width/1600,y=box.y+(values[1]+values[3]/2)*box.height/900;
    const hit=await page.evaluate(({x,y})=>document.elementFromPoint(x,y)?.tagName,{x,y});assert.equal(hit,'CANVAS','Mouse input must hit actual canvas');
    if(touch) await page.touchscreen.tap(x,y);else await page.mouse.click(x,y);
  }
}
async function select(page,id,keyboard=false) {
  const object=state.objects.find(object=>object.object_id===id);assert(object,'Object must be currently visible: '+id);
  if(visual()) {
    await roomView(page);
    if(['r1_symbols','r1_fuse','r1_photo'].includes(id)) {
      await http(page,'canvas-inspect:r1_cabinet',()=>canvasInput(page,'r1_cabinet'));
      await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view','r1_cabinet');
    }
    if(state.room.room_id==='R2' && !await page.locator(`.game-canvas-host .scene-keyboard-hotspot[data-object-id="${id}"][data-scene-action="object"]`).count()) {
      const parent=['research_strip','access_card'].includes(id)?'r2_monitor':id==='r2_service_label'?'r2_powerbox':null;
      assert(parent,'Expected visible R2 canvas hotspot: '+id);
      await http(page,'canvas-inspect:'+parent,()=>canvasInput(page,parent));
      await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view',parent);
    }
    let count=0;const listener=request=>{if(new URL(request.url()).pathname.endsWith('/actions')) count++;};page.on('request',listener);
    const body=await http(page,(keyboard?'keyboard':'canvas')+'-inspect:'+id,()=>canvasInput(page,id,'object',keyboard));
    await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view',id);page.off('request',listener);
    assert.equal(count,1);assert.equal(body.data.receipt.tool,'inspect');assert.equal(body.data.receipt.arguments.object_id,id);
    checks.push({check:keyboard?'keyboard-independent-hotspot':'real-canvas-one-inspect-closeup',object_id:id,passed:true});
    if(['r1_record','r1_plaque','r1_microscope','r1_photo'].includes(id)) {
      const stage=id==='r1_microscope'?(state.puzzle_states.microscope+(state.clues.some(clue=>clue.object_id===id)?'-eyepiece':'')):'reading';
      const imagePath=path.join(folder,id+'-'+stage+'.png');if(!fs.existsSync(imagePath)) {await canvasPixels(page,id+'-'+stage);await page.locator('.visual-room').screenshot({path:imagePath});}
    }return body;
  }
  const escaped=object.name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  await page.locator('.object-grid').getByRole('button',{name:new RegExp(escaped)}).click();
}
async function observe(page,id) {
  if(visual()) return select(page,id);
  await select(page,id);return http(page,'inspect:'+id,()=>page.getByRole('button',{name:/^观察$/}).click());
}
async function interact(page,id) {
  await select(page,id);
  if(visual()) {
    const object=state.objects.find(value=>value.object_id===id),action=object.actions.find(value=>value.tool==='interact')||object.actions.find(value=>value.tool==='take')||object.actions.find(value=>value.tool==='inspect');
    assert(action);
    const beforeActionMarkers=(await markers(page)).length;
    if(action.tool==='take'||id==='r1_cabinet') await page.locator('.game-canvas-host canvas').screenshot({path:path.join(folder,id+'-before-'+action.tool+'.png')});
    const body=await http(page,action.tool+':'+id,()=>['R2','R3'].includes(state.room.room_id)?canvasInput(page,id,action.tool):page.locator(`.closeup-actions [data-scene-action="${action.tool}"][data-target-id="${id}"]`).click());
    if(action.tool==='take'||id==='r1_cabinet') {
      await expect.poll(async()=> (await markers(page)).slice(beforeActionMarkers).includes(action.tool)).toBe(true);
      await page.locator('.game-canvas-host canvas').screenshot({path:path.join(folder,id+'-receipt-frame-'+action.tool+'.png')});
      await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-animation','idle');
      await page.locator('.game-canvas-host canvas').screenshot({path:path.join(folder,id+'-settled-'+action.tool+'.png')});
      if(state.room.room_id==='R2'&&action.tool==='take') {
        assert(['research_strip','access_card'].includes(id));assert(state.inventory.some(item=>item.item_id===id));assert(!state.objects.some(object=>object.object_id===id));
        await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view','room');
        assert.equal(await page.locator(`.scene-keyboard-hotspot[data-object-id="${id}"]`).count(),0);
        checks.push({check:'R2-take-removes-visible-object-and-auto-returns-overview',object_id:id,passed:true});
      }
      checks.push({check:'receipt-animation-frames-for-independent-visual-review',object_id:id,tool:action.tool,passed:true});
    }return body;
  }
  return http(page,'interact:'+id,()=>page.getByRole('button',{name:/^互动$/}).click());
}
async function code(page,id,value,expected=200) {
  await select(page,id);if(!visual()) await page.getByRole('button',{name:/^互动$/}).click();
  await page.getByLabel('输入你推理出的数字',{exact:true}).fill(value);
  return http(page,'code:'+id,()=>page.locator('.code-form').getByRole('button',{name:'提交',exact:true}).click(),expected);
}
async function login(page, username, password, expected = 200) {
  await select(page, 'r2_monitor'); if(!visual()) await page.getByRole('button', { name: /^互动$/ }).click();
  await expect(page.locator('.login-form')).toHaveCount(1);await expect(page.locator('#terminal-username')).toHaveCount(1);await expect(page.locator('#terminal-password')).toHaveCount(1);
  await page.locator('#terminal-username').fill(username);await page.locator('#terminal-password').fill(password);
  return http(page, 'submit_login', () => visual()?page.locator('.login-form [data-scene-action="submit_login"][data-target-id="r2_monitor"]').click():page.locator('.login-form').getByRole('button', { name: '提交登录', exact: true }).click(), expected);
}

async function use(page,itemId,targetId,expected=200) {
  const item=state.inventory.find(item=>item.item_id===itemId);assert(item,'Owned item: '+itemId);
  await select(page,targetId);
  let canvasTool=null;
  if(visual()) {
    const zone=page.locator(`.game-canvas-host .scene-keyboard-hotspot[data-object-id="${targetId}"]`);
    if(await zone.count()===1) canvasTool=await zone.getAttribute('data-scene-action');
    else {await roomView(page);canvasTool='object';}
  }
  const button=page.locator('.inventory-item').filter({hasText:item.name}).locator('.item-select-button');
  if(await button.getAttribute('aria-pressed')!=='true') await button.click();
  const body=await http(page,'use:'+itemId+':'+targetId,()=>canvasTool?canvasInput(page,targetId,canvasTool):page.getByRole('button',{name:/^使用物品/}).click(),expected);
  if(canvasTool) {if(expected===200) assert.equal(body.data.receipt.tool,'use_item');checks.push({check:'actual-canvas-held-item-server-authority',item_id:itemId,target_id:targetId,http_status:expected,passed:true});}
  if(expected!==200) await expect(button).toHaveAttribute('aria-pressed','true');return body;
}
async function move(page,destination,expected=200) {
  const exit=state.exits.find(exit=>exit.destination_id===destination);assert(exit,'Visible passage: '+destination);
  if(visual()) {
    if(state.room.room_id==='R1') {await select(page,'r1_door');return http(page,'move:'+destination,()=>page.locator('.closeup-actions [data-scene-action="move"]').click(),expected);}
    if(state.room.room_id==='R3') {
      if(destination==='EXIT'&&expected!==200) {
        assert.equal(await page.locator('.scene-keyboard-hotspot[data-scene-action="move"][data-target-id="EXIT"],.room3-controls [data-scene-action="move"]').count(),0,'Locked EXIT must have no UI move control');
        return rejectedPublicAction(page,'move',{destination_id:destination},expected);
      }
      if(destination==='R2') {await roomView(page);return http(page,'move:'+destination,()=>canvasInput(page,'return_R2','move'),expected);}
      await select(page,'exit_door');return http(page,'move:'+destination,()=>canvasInput(page,'exit_door','move'),expected);
    }
    if(destination==='R1') {await roomView(page);return http(page,'move:'+destination,()=>canvasInput(page,'return_R1','move'),expected);}
    await select(page,'r2_door');return http(page,'move:'+destination,()=>canvasInput(page,'r2_door','move'),expected);
  }
  return http(page,'move:'+destination,()=>page.locator('.exit-button').filter({hasText:exit.name}).click(),expected);
}
async function control(page, operation) {
  await menu(page);
  let answer;await assertSilentOperation(page,'control:'+operation,async()=>{answer=await http(page, operation, async () => {
    await page.getByRole('button', { name: operation === 'save' ? '保存进度' : operation === 'restore' ? '恢复存档' : '重新开始', exact: true }).click();
    if (operation !== 'save') await page.getByRole('dialog').getByRole('button', { name: operation === 'restore' ? '确认恢复' : '确认开始', exact: true }).click();
  }, 200, '/' + operation);});return answer;
}
async function appendMoment(page,name) {
  await menu(page);
  const before=structuredClone(state);
  await page.locator('#save-slot-name').fill(name);
  const body=await http(page,'archive-create',() => page.locator('.save-slot-create-button').click(),201,'/saves');
  assert.deepEqual(state,before);assert.equal(body.data.slot.name,name);
  assert.equal(body.data.replayed,false);assert.equal(body.data.slot.kind,'archive');
  await expect(page.locator(`.save-slot[data-save-id="${body.data.slot.save_id}"]`)).toBeVisible();
  await expect(page.locator('#save-slot-name')).toHaveValue('');
  checks.push({check:'append-moment-keeps-live-game-and-old-slot',name,room:state.room.room_id,statistics:state.statistics,passed:true});
  return {slot:body.data.slot,state:structuredClone(state)};
}
async function retrieveMoment(page,moment,checkCancel=false) {
  await menu(page);
  const before=structuredClone(state),restoreAnimationCount=(await markers(page)).length,row=page.locator(`.save-slot[data-save-id="${moment.slot.save_id}"]`);
  await expect(row).toBeVisible();await row.locator('.save-slot-restore').click();
  const dialog=page.getByRole('dialog');await expect(dialog.getByRole('heading',{name:'读取指定存档？',exact:true})).toBeVisible();
  if(checkCancel) {
    await dialog.screenshot({path:path.join(folder,'desktop-selected-restore-confirmation.png')});
    await dialog.getByRole('button',{name:'取消',exact:true}).click();assert.deepEqual(state,before);
    await row.locator('.save-slot-restore').click();
  }
  let body;await assertSilentOperation(page,'archive-selected-restore',async()=>{body=await http(page,'archive-selected-restore',() => dialog.getByRole('button',{name:'读取此存档',exact:true}).click(),200,`/saves/${moment.slot.save_id}/restore`);});
  assert.equal(body.data.slot.save_id,moment.slot.save_id);assert.equal(body.data.replayed,false);
  assert.deepEqual(publicGame(state),publicGame(moment.state));assert.equal(state.revision,before.revision+1);assert.notEqual(state.generation,before.generation);
  await menu(page);await expect(row).toBeVisible();if(visual()){assert.equal((await markers(page)).length,restoreAnimationCount,'Archive restore must not produce progression animation');if(state.status!=='won')await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-animation','idle');}
  checks.push({check:'user-selected-moment-restores-game-statistics-new-generation',name:moment.slot.name,cancel_checked:checkCancel,passed:true});
}
async function refresh(page) {
  await page.reload({ waitUntil: 'networkidle' });
  assert.equal(audibleAttempts(await audioEvents(page)).length,0,'Reload must not replay old receipt');
  await http(page, 'state', () => page.locator('.welcome-buttons').getByRole('button', { name: '继续当前游戏', exact: true }).click(), 200, '/state');
  if(visual()) {await trackMarkers(page);await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));assert.equal(audibleAttempts(await audioEvents(page)).length,0,'Continue snapshot must not play progression sound');}
}
async function layout(page, width, label) {
  if(visual()&&state.status!=='won') {await closeDrawer(page);await expect(page.locator('.game-canvas-host canvas')).toHaveCount(1);await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-assets-ready','true');await canvasPixels(page,label);}
  else if(state?.status==='won'&&visual()) {await closeDrawer(page);await expect(page.locator('.victory-screen')).toBeVisible();await expect(page.locator('.game-canvas-host canvas')).toHaveCount(0);assert.equal(await page.locator('.object-grid').count(),0);}
  else {await expect(page.locator('.game-canvas-host canvas')).toHaveCount(0);await expect(page.locator('.object-grid button')).toHaveCount(state.objects.length);}
  const dimensions = await page.evaluate(() => {
    const controls = [...document.querySelectorAll('button,input,textarea')].filter(element => element.getClientRects().length);
    const outside = controls.filter(element => { const r = element.getBoundingClientRect(); return r.left < -1 || r.right > innerWidth + 1 || r.width <= 0; });
    return { viewport_width: innerWidth, document_width: document.documentElement.scrollWidth, controls: controls.length, outside_viewport: outside.length };
  });
  assert.equal(dimensions.viewport_width, width); assert(dimensions.document_width <= width + 1); assert.equal(dimensions.outside_viewport, 0);
  checks.push({ check: label, ...dimensions, visible_object_ids: state.objects.map(object => object.object_id) });
}

// Public instruction only: I0=N/S, L0=N/E, +1 clockwise, reciprocal neighbors.
const sides = ['N', 'E', 'S', 'W'], deltas = [[-1,0],[0,1],[1,0],[0,-1]];
function ports(module, rotation = module.rotation) { return (module.shape === 'I' ? [0,2] : [0,1]).map(side => (side + rotation) % 4); }
function connected(board, rotations) {
  const modules = new Map(board.modules.map(module => [module.module_id, module]));
  const positions = new Map(board.modules.map(module => [[module.row,module.column].join(','), module.module_id]));
  const allPorts = new Map(board.modules.map(module => [module.module_id, ports(module, rotations?.[module.module_id] ?? module.rotation)]));
  if (!allPorts.get(board.source.module_id).includes(sides.indexOf(board.source.side)) || !allPorts.get(board.sink.module_id).includes(sides.indexOf(board.sink.side))) return false;
  const todo = [board.source.module_id], seen = new Set();
  while (todo.length) {
    const id = todo.pop(); if (seen.has(id)) continue; seen.add(id); if (id === board.sink.module_id) return true;
    const module = modules.get(id);
    for (const side of allPorts.get(id)) {
      const [dr,dc] = deltas[side], other = positions.get([module.row+dr,module.column+dc].join(','));
      if (other && allPorts.get(other).includes((side+2)%4) && !seen.has(other)) todo.push(other);
    }
  }
  return false;
}
function deriveCircuit(board) {
  let result;
  function search(index, chosen) {
    if (result) return;
    if (index === board.modules.length) { if (connected(board, chosen)) result = { ...chosen }; return; }
    const module = board.modules[index];
    for (let rotation=0; rotation<(module.shape === 'I' ? 2 : 4); rotation++) search(index+1,{ ...chosen,[module.module_id]:rotation });
  }
  search(0,{}); assert(result, 'Public reciprocal ports must admit source-to-sink connection'); return result;
}
function deriveSequence(value) {
  const fact = id => value.clues.filter(clue => clue.object_id === id).map(clue => clue.text).join('\n');
  const symbols = fact('r1_symbols').match(/[▲●■★]/g), positions = (fact('research_strip').match(/\d+/g) || []).map(Number);
  const sequence = value.minigames.sequence, legend = fact('r3_legend');
  assert.equal(symbols.length,4); assert.deepEqual([...positions].sort(),[1,2,3,4]); assert.equal(sequence.devices.length,4);
  for (const device of sequence.devices) { assert(legend.includes(device.symbol)); assert(legend.includes(device.label)); }
  const map = Object.fromEntries(sequence.devices.map(device => [device.symbol,device.device_id]));
  const result = positions.map(position => map[symbols[position-1]]); assert.equal(new Set(result).size,4); return result;
}
async function openCircuit(page) {
  await select(page,'r2_powerbox');if(!visual()) await page.getByRole('button',{name:/^互动$/}).click();
  await expect(page.locator('.circuit-submit')).toBeVisible();
  if(visual()) {await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-circuit-status',state.minigames.circuit.status);await expect(page.locator('.scene-keyboard-hotspot[data-module-id]')).toHaveCount(9);}
}
async function rotate(page, id) {
  const before=structuredClone(state),module=before.minigames.circuit.modules.find(module=>module.module_id===id);assert(module);
  const body=await http(page,'rotate:'+id,()=>visual()?moduleInput(page,id):page.locator(`.circuit-cell[data-module-id="${id}"]`).click());
  assert.equal(state.minigames.circuit.modules.find(module=>module.module_id===id).rotation,(module.rotation+1)%4);
  assert.equal(state.device_states.powerbox,'FUSE_INSTALLED');assert.equal(state.progress.power_on,false);assert.equal(state.revision,before.revision+1);
  if(visual()) {assert.equal(body.data.receipt.tool,'rotate_circuit');await expect(page.locator(`.scene-keyboard-hotspot[data-module-id="${id}"]`)).toHaveAttribute('data-rotation',String((module.rotation+1)%4));}
  return body;
}
async function submitCircuit(page, expected=200) { return http(page,'submit_circuit',() => page.locator('.circuit-submit').click(),expected); }
async function rejectedPublicAction(page,tool,args,expected) {
  // Only the old locked EXIT rejection assertion uses direct public API; UI correctly has no forbidden move button.
  const result=await page.evaluate(async({tool,args,revision,generation})=>{
    const session=JSON.parse(sessionStorage.getItem('campus-lab-session-upgrade-v3.4'));
    const response=await fetch(`/api/sessions/${encodeURIComponent(session.session_id)}/actions`,{method:'POST',headers:{'Content-Type':'application/json','X-Session-Token':session.token},body:JSON.stringify({request_id:crypto.randomUUID(),revision,generation,tool,arguments:args})});
    return {status:response.status,body:await response.json()};
  },{tool,args,revision:state.revision,generation:state.generation});
  record('locked-EXIT-public-rejection',result.body,result.status);assert.equal(result.status,expected);
  checks.push({check:'UI-omits-locked-EXIT-and-public-server-rejection-preserved',passed:true});return result.body;
}
async function replayReceiptThroughUI(page,id) {
  const captured=latestAction;assert(captured);const before=structuredClone(state),markerCount=(await markers(page)).length;await roomView(page);
  const handler=async route=>{const actual=await route.fetch({postData:captured.request_body});await route.fulfill({response:actual});};
  const pattern='**'+captured.pathname;await page.route(pattern,handler,{times:1});
  const body=await http(page,'actual-server-replayed-receipt-through-UI',()=>canvasInput(page,id,'object'));
  await page.unroute(pattern,handler);assert.equal(body.data.replayed,true);assert.deepEqual(state,before);assert.equal((await markers(page)).length,markerCount);
  checks.push({check:'actual-server-replay-no-repeat-animation-or-one-shot',passed:true});
}
async function assetGateSnapshot(page,pattern,label,afterReady) {
  const snapshot=structuredClone(state),failure=await controlledAssetFailure(page,pattern);
  await refresh(page);await expect(page.locator('.canvas-error')).toBeVisible();assert(failure.failedRequests>0,'Actual SVG abort must occur');
  const host=page.locator('.game-canvas-host');await expect(host).toHaveAttribute('data-assets-ready','false');
  const disabled=await host.locator('.scene-keyboard-hotspot').evaluateAll(nodes=>nodes.length>0&&nodes.every(node=>node.disabled));assert(disabled);
  for(const form of ['.code-form','.crt-login','.sequence-controls']) {const controls=page.locator(form+' input,'+form+' button');for(let index=0;index<await controls.count();index++)await expect(controls.nth(index)).toBeDisabled();}
  await gateAttempt(page,label+'-Canvas',async()=>{const box=await host.locator('canvas').boundingBox();assert(box);await page.mouse.click(box.x+box.width*.1,box.y+box.height*.1);});
  await gateAttempt(page,label+'-keyboard',async()=>{await host.locator('.scene-keyboard-hotspot').first().evaluate(node=>node.focus());await page.keyboard.press('Enter');});
  await expect(page.locator('.closeup-controls')).toHaveCount(0); // Reload snapshot has no selected view: forms/actions cannot be opened while blocked.
  await page.screenshot({path:path.join(folder,label+'-missing-svg.png'),fullPage:true});
  await failure.release();const requests=requestMeasurement(page),beforeMarkers=(await markers(page)).length;
  await assertSilentOperation(page,label+'-retry-snapshot',()=>page.locator('.canvas-retry').click());
  await expect(host).toHaveAttribute('data-assets-ready','true');requests.stop();
  assert.equal(requests.requests.filter(request=>request.method==='POST').length,0);assert.deepEqual(state,snapshot);assert.equal((await markers(page)).length,beforeMarkers);
  await expect(host).toHaveAttribute('data-animation','idle');await canvasPixels(page,label+'-retry');if(afterReady)await afterReady();
  checks.push({check:'controlled-external-SVG-abort-input-gate-and-retry-same-server-snapshot',label,failed_requests:failure.failedRequests,revision:state.revision,passed:true});
}
async function r3Checkpoint(page,label) {
  assert.equal(state.room.room_id,'R3');await closeDrawer(page);const host=page.locator('.game-canvas-host[data-room="R3"]');await expect(host).toHaveAttribute('data-assets-ready','true');
  await expect(host).toHaveAttribute('data-panel-state',state.puzzle_states.panel);await expect(host).toHaveAttribute('data-exit-state',state.device_states.exit);assert.equal(await page.locator('.object-grid').count(),0);
  if(state.minigames.sequence)await expect(host).toHaveAttribute('data-sequence-status',state.minigames.sequence.status);
  await expect.poll(async()=>host.locator('.scene-keyboard-hotspot').evaluateAll(nodes=>nodes.every(node=>{const r=node.getBoundingClientRect();return r.width>=43.9&&r.height>=43.9;}))).toBe(true);
  const buttons=await host.locator('.scene-keyboard-hotspot').evaluateAll(nodes=>nodes.map(node=>{const r=node.getBoundingClientRect();return {id:node.dataset.objectId,device:node.dataset.deviceId,width:r.width,height:r.height,left:r.left,right:r.right,top:r.top,bottom:r.bottom};}));
  for(const button of buttons)assert(button.width>=43.9&&button.height>=43.9,'Real responsive hotspot smaller than 44px');
  const devices=buttons.filter(button=>button.device);for(let a=0;a<devices.length;a++)for(let b=a+1;b<devices.length;b++)assert(!(Math.min(devices[a].right,devices[b].right)>Math.max(devices[a].left,devices[b].left)+1&&Math.min(devices[a].bottom,devices[b].bottom)>Math.max(devices[a].top,devices[b].top)+1),'Real sequence hotspot overlap');
  await canvasPixels(page,label);await page.screenshot({path:path.join(folder,label+'.png'),fullPage:true});checks.push({check:'R3-authoritative-rendering-44px-independent-hotspots',label,panel:state.puzzle_states.panel,exit:state.device_states.exit,hotspots:buttons,passed:true});
}
async function presentationSettings(page,muted,reduced=false) {
  const before=structuredClone(state),requests=requestMeasurement(page);await menu(page);
  const sound=page.locator('.sound-toggle');if(await sound.getAttribute('aria-pressed')!==String(muted))await sound.click();await expect(sound).toHaveAttribute('aria-pressed',String(muted));
  await page.locator('.motion-toggle').setChecked(reduced);await expect(page.locator('.presentation-observer')).toHaveAttribute('data-reduced-motion',String(reduced));await closeDrawer(page);
  requests.stop();assert.equal(requests.requests.filter(request=>request.method==='POST').length,0);assert.deepEqual(state,before);checks.push({check:'sound-reduced-motion-settings-local-only',muted,reduced,passed:true});
}
async function touchR3SameOwnedSession(service,mainPage) {
  // Same QA-owned authenticated session is passed only in memory, never recorded or persisted outside browser tab storage.
  const owned=await mainPage.evaluate(()=>sessionStorage.getItem('campus-lab-session-upgrade-v3.4'));assert(owned);
  const context=await browser.newContext({viewport:{width:375,height:812},hasTouch:true,isMobile:true,deviceScaleFactor:1,reducedMotion:'reduce'});
  await context.addInitScript(value=>sessionStorage.setItem('campus-lab-session-upgrade-v3.4',value),owned);await installAudioProbe(context);
  const page=await context.newPage(),errors=[];page.on('pageerror',()=>errors.push('uncaught R3 touch exception'));await page.goto(service.frontendURL,{waitUntil:'networkidle'});
  await http(page,'R3-touch-own-session-state',()=>page.getByRole('button',{name:'继续当前游戏',exact:true}).click(),200,'/state');assert.equal(state.room.room_id,'R3');await trackMarkers(page);
  await roomView(page);await http(page,'R3-actual-touch-legend',()=>canvasInput(page,'r3_legend','object',false,true));await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view','r3_legend');
  await select(page,'r3_panel',true);const publicIds=state.minigames.sequence.devices.map(device=>device.device_id);const before=structuredClone(state);
  await sequenceInput(page,publicIds[0],false,true);await sequenceInput(page,publicIds[1],true,false);
  const ids=await page.locator('.sequence-draft li[data-device-id]').evaluateAll(nodes=>nodes.map(node=>node.dataset.deviceId));assert.deepEqual(ids,publicIds.slice(0,2));assert.deepEqual(state,before);await expect(page.locator('.sequence-submit')).toBeDisabled();
  await r3Checkpoint(page,'R3-real-touch-keyboard-public-draft-375');await expect(page.locator('.presentation-observer')).toHaveAttribute('data-reduced-motion','true');assert.equal(errors.length,0);await context.close();
  await menu(mainPage);await http(mainPage,'state-after-R3-touch-own-session',()=>mainPage.getByRole('button',{name:'同步进度',exact:true}).click(),200,'/state');await openSequence(mainPage);
  checks.push({check:'R3-real-touch-and-keyboard-with-public-IDs-local-draft-system-reduced-motion',scope:'same QA-owned authenticated session held only in memory',passed:true});
}
function isEngineRequest(request) {return /phaser|Room[123]Scene|GameCanvas|\/Room[123]\.tsx/.test(request.pathname);}
async function firstLaunch(page,requests,label) {
  await expect(page.locator('.welcome.quiet-entry')).toBeVisible();assert.equal(await page.locator('.game-canvas-host').count(),0);assert.equal(await page.locator('.object-grid,.support-grid,.run-statistics').count(),0);
  assert.equal(requests.requests.filter(isEngineRequest).length,0,'First launch loaded the game engine');assert.equal((await audioEvents(page)).length,0,'AudioContext existed before trusted gesture');
  assert(await page.locator('.entry-room img').evaluateAll(nodes=>nodes.length>0&&nodes.every(node=>node.complete&&node.naturalWidth>0)));
  await page.screenshot({path:path.join(folder,label+'-quiet-first-launch.png'),fullPage:true});checks.push({check:'actual-first-launch-static-night-scene-no-dashboard-no-engine-no-audio',label,requests:requests.requests,passed:true});
}
async function productionStartupMeasurement(service) {
  const port=await freePort(),url=`http://127.0.0.1:${port}`;
  start('v42-built-production-preview',process.execPath,[path.join(root,'frontend/node_modules/vite/bin/vite.js'),'preview','--host','127.0.0.1','--port',String(port),'--strictPort'],{CAMPUS_BACKEND_URL:service.backendURL},path.join(root,'frontend'));await ready(url);
  const context=await browser.newContext({viewport:{width:1920,height:1080}});await installAudioProbe(context);const page=await context.newPage(),requests=requestMeasurement(page);state=undefined;
  await page.goto(url,{waitUntil:'networkidle'});await firstLaunch(page,requests,'built-production');
  const startup=await page.evaluate(()=>performance.getEntriesByType('resource').filter(entry=>new URL(entry.name).pathname.endsWith('.js')).map(entry=>({pathname:new URL(entry.name).pathname,transfer_bytes:entry.transferSize,encoded_bytes:entry.encodedBodySize,decoded_bytes:entry.decodedBodySize})));
  await http(page,'production-preview-create',()=>page.getByRole('button',{name:'开始新游戏 →',exact:true}).click(),201,'/api/sessions');await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-assets-ready','true');await page.waitForLoadState('networkidle');
  const engine=requests.requests.filter(request=>/\/phaser-[^/]+\.js$/.test(request.pathname));assert.equal(engine.length,1,'Production Phaser must be a separate deferred chunk fetched on play');
  const resources=await page.evaluate(()=>performance.getEntriesByType('resource').filter(entry=>new URL(entry.name).pathname.endsWith('.js')).map(entry=>({pathname:new URL(entry.name).pathname,transfer_bytes:entry.transferSize,encoded_bytes:entry.encodedBodySize,decoded_bytes:entry.decodedBodySize})));
  const chunk=resources.find(entry=>/\/phaser-[^/]+\.js$/.test(entry.pathname));assert(chunk);assert(startup.every(entry=>!entry.pathname.includes('phaser-')));assert(startup.reduce((total,entry)=>total+entry.decoded_bytes,0)<chunk.decoded_bytes,'Startup JS should be smaller than deferred engine');
  await canvasPixels(page,'built-production-R1-render');requests.stop();checks.push({check:'production-build-actual-startup-and-on-play-lazy-network-bytes',startup,after_start_resources:resources,passed:true});await context.close();
}
async function authoritativeVictory(page) {
  const result=state.settlement;assert(result);assert.equal(result.rating,publicRating(result));await expect(page.locator('.victory-screen')).toBeVisible();await settledRoomTransition(page);
  const time=[Math.floor(result.elapsed_seconds/3600),Math.floor(result.elapsed_seconds/60)%60,Math.floor(result.elapsed_seconds)%60].map(value=>String(value).padStart(2,'0')).join(':');
  const values={elapsed_seconds:time,clues_found:`${result.clues_found}/${result.clues_total}`,hidden_found:`${result.hidden_found}/${result.hidden_total}`,hint_count:String(result.hint_count),mistake_count:String(result.mistake_count),rating:result.rating};
  for(const [key,value]of Object.entries(values))await expect(page.locator(`.victory-screen [data-stat="${key}"]`)).toHaveText(value);
  assert.equal(await page.locator('.game-canvas-host').count(),0);await page.locator('.victory-screen').screenshot({path:path.join(folder,'victory-server-fields.png')});checks.push({check:'Victory-six-fields-exact-authoritative-settlement',values,passed:true});
}
async function sequenceInput(page,id,keyboard=false,touch=false) {
  const host=page.locator('.game-canvas-host[data-room="R3"]');await expect(host).toHaveAttribute('data-assets-ready','true');
  const zone=host.locator(`.scene-keyboard-hotspot[data-device-id="${id}"][data-scene-action="sequence_device"]`);await expect(zone).toHaveCount(1);await expect(zone).toBeEnabled();
  const before=structuredClone(state),requests=requestMeasurement(page);
  if(keyboard) {await zone.focus();await zone.press('Enter');}
  else {await canvasSizeReady(host);const values=(await zone.getAttribute('data-bounds')).split(',').map(Number),box=await host.locator('canvas').boundingBox();assert(box);
    const x=box.x+(values[0]+values[2]/2)*box.width/1600,y=box.y+(values[1]+values[3]/2)*box.height/900;
    assert.equal(await page.evaluate(({x,y})=>document.elementFromPoint(x,y)?.tagName,{x,y}),'CANVAS');
    if(touch)await page.touchscreen.tap(x,y);else await page.mouse.click(x,y);
  }
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(resolve)));requests.stop();
  assert.equal(requests.requests.filter(request=>request.pathname.endsWith('/actions')).length,0,'Sequence draft must remain local');assert.deepEqual(state,before);
  checks.push({check:'public-sequence-local-draft-real-'+(touch?'touch':keyboard?'keyboard':'Canvas'),device_id:id,passed:true});
}
async function openSequence(page) { await select(page,'r3_panel'); if(!visual()) await page.getByRole('button',{name:/^互动$/}).click(); await expect(page.locator('.sequence-submit')).toBeVisible();if(visual()) {await expect(page.locator('.scene-keyboard-hotspot[data-device-id]')).toHaveCount(state.minigames.sequence.devices.length);await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-sequence-status',state.minigames.sequence.status);} }
async function draftSequence(page, ids) { if (await page.locator('.sequence-clear').isEnabled()) await page.locator('.sequence-clear').click(); for (const id of ids) {if(visual()) await sequenceInput(page,id);else await page.locator(`.sequence-device[data-device-id="${id}"]`).click();} }
async function submitSequence(page, expected=200) { return http(page,'submit_sequence',() => page.locator('.sequence-submit').click(),expected); }


function unchangedCore(value) { return Object.fromEntries(Object.entries(value).filter(([key]) => !['revision','statistics','settlement'].includes(key))); }
function countedMistake(before) {
  assert.deepEqual(unchangedCore(state),unchangedCore(before)); assert.equal(state.revision,before.revision+1);
  assert.equal(state.statistics.mistake_count,before.statistics.mistake_count+1); assert.equal(state.statistics.hint_count,before.statistics.hint_count);
}
async function hint(page,level,expectAccepted=true) {
  await partner(page);
  let requests=0; const listener=request => { if(new URL(request.url()).pathname.endsWith('/ai/turns')) requests++; };
  page.on('request',listener); const before=structuredClone(state);
  await page.locator('#hint-level').selectOption(String(level)); assert.equal(requests,0); assert.deepEqual(state,before);
  await page.locator('#ai-question').fill('只依据已发现线索给提示，玩家自己曾输入4217。');
  const body=await http(page,'hint-level:'+level,() => page.locator('.hint-ask').click(),200,'/ai/turns');
  page.off('request',listener); assert.equal(requests,1); assert.equal(body.data.status,'no_suggestion'); assert.equal(body.data.proposal,null); assert.equal(body.data.usage.read_tool_calls,0);
  assert.deepEqual(unchangedCore(state),unchangedCore(before)); assert.equal(state.statistics.mistake_count,before.statistics.mistake_count);
  assert.equal(state.statistics.hint_count,before.statistics.hint_count+(expectAccepted?1:0));
  if(expectAccepted) { assert.equal(state.statistics.current_hint_level,level); assert.equal(body.data.usage.model_calls,0); await expect(page.locator('.hint-count')).toHaveText(String(state.statistics.hint_count)); }
  else assert.equal(body.data.usage.model_calls,0);
  assert(!body.data.answer.includes('4217')); assert(!body.data.answer.includes('4792'));
  checks.push({check:'hint-selection-local-and-bounded-response',level,accepted:expectAccepted,model_calls:body.data.usage.model_calls,known_refs:body.data.clue_refs,count:state.statistics.hint_count});
  return body.data.answer;
}
function publicRating(score) { return score.clues_found>=9&&score.hint_count<=1&&score.mistake_count<=2?'S':score.clues_found>=7&&score.hint_count<=3&&score.mistake_count<=5?'A':score.hint_count<=8?'B':'C'; }


async function touchSmoke(service) {
  const context=await browser.newContext({viewport:{width:375,height:812},hasTouch:true,isMobile:true,deviceScaleFactor:1}),page=await context.newPage();
  const errors=[];page.on('pageerror',()=>errors.push('uncaught touch browser exception'));state=undefined;
  await installAudioProbe(context);await page.goto(service.frontendURL,{waitUntil:'networkidle'});
  await http(page,'touch-create',()=>page.getByRole('button',{name:'开始新游戏 →',exact:true}).click(),201,'/api/sessions');
  await http(page,'real-touchscreen-canvas-clock-inspect',()=>canvasInput(page,'r1_clock','object',false,true));
  await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view','r1_clock');assert(state.clues.some(clue=>clue.object_id==='r1_clock'));
  await canvasPixels(page,'R1-touch-clock-closeup');await page.screenshot({path:path.join(folder,'R1-touch-clock-closeup.png'),fullPage:true});
  await select(page,'r1_record',true);assert(state.clues.some(clue=>clue.object_id==='r1_record'));
  await layout(page,375,'R1-actual-touch-keyboard');assert.equal(errors.length,0);
  checks.push({check:'hasTouch-mobile-actual-touchscreen-tap-and-keyboard-Enter',passed:true,width:375});await context.close();
}
async function canvasPixels(page,label) {
  const host=page.locator('.game-canvas-host');
  await expect(host).toHaveAttribute('data-assets-ready','true');
  const renderer=await host.getAttribute('data-renderer');assert(['canvas','webgl'].includes(renderer),'Renderer must be explicitly ready');
  const imagePath=path.join(folder,label+'-canvas-pixels.png');await host.locator('canvas').screenshot({path:imagePath});
  const args=['-B','-X','utf8',path.join(root,'evidence/upgrade/v4.0/qa/pixel_check.py'),imagePath];
  const result=spawnSync(python,args,{cwd:root,encoding:'utf8',windowsHide:true});
  commands.push({label:'canvas-pixel-check:'+label,executable:python,arguments:args,cwd:root,exit_code:result.status,stdout:result.stdout.trim(),stderr:result.stderr.trim()});
  assert.equal(result.status,0,'Canvas screenshot is black/uniform or pixel reader failed');
  checks.push({check:'real-rendered-canvas-nonblack-nonuniform',label,renderer,...JSON.parse(result.stdout)});
}

// Independent browser-only probes. No product flags, test hooks, or credential exports.
async function installAudioProbe(context) {
  await context.addInitScript(()=>{
    window.qaAudioEvents=[];window.qaTrustedGestures=0;
    for(const type of ['pointerdown','keydown']) window.addEventListener(type,event=>{if(event.isTrusted)window.qaTrustedGestures++;},{capture:true});
    const note=(kind,detail={})=>window.qaAudioEvents.push({kind,gesture_count:window.qaTrustedGestures,...detail});
    const nativePlay=HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play=function(...args){note('media-play',{muted:this.muted,volume:this.volume});return nativePlay.apply(this,args);};
    for(const key of ['AudioContext','webkitAudioContext']) {
      const Native=window[key];if(!Native)continue;
      window[key]=class extends Native {
        constructor(...args){super(...args);note('context-created',{state:this.state});}
        resume(...args){note('context-resume',{state:this.state});return super.resume(...args);}
        createOscillator(...args){const node=super.createOscillator(...args),start=node.start.bind(node),context=this;node.start=(...values)=>{note('oscillator-start',{state:context.state});return start(...values);};return node;}
        createBufferSource(...args){const node=super.createBufferSource(...args),start=node.start.bind(node),context=this;node.start=(...values)=>{note('buffer-start',{state:context.state});return start(...values);};return node;}
      };
    }
  });
}
async function audioEvents(page) {return page.evaluate(()=>window.qaAudioEvents||[]);}
function audibleAttempts(events) {return events.filter(event=>['media-play','oscillator-start'].includes(event.kind));} // Ambient buffer start is measured separately; snapshot rule concerns progression cues.
async function assertSilentOperation(page,label,operation) {
  const before=audibleAttempts(await audioEvents(page)).length;
  await operation();
  // Two actual browser frames allow effects and queued receipt observers to settle.
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  assert.equal(audibleAttempts(await audioEvents(page)).length,before,label+' must not play progression sound');
  checks.push({check:'silent-snapshot-or-muted-operation',label,passed:true});
}
function requestMeasurement(page) {
  const requests=[];
  const listener=request=>{const url=new URL(request.url());requests.push({pathname:url.pathname,method:request.method(),resource_type:request.resourceType()});};
  page.on('request',listener);
  return {requests,stop:()=>page.off('request',listener)};
}
async function gateAttempt(page,label,attempt) {
  const before=structuredClone(state),mutations=[];
  const listener=request=>{const pathname=new URL(request.url()).pathname;if(request.method()==='POST'&&(/\/(actions|restore|reset|save)$/.test(pathname)||pathname.endsWith('/ai/turns')))mutations.push(pathname);};
  page.on('request',listener);
  await attempt();await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  page.off('request',listener);assert.deepEqual(mutations,[],label+' issued a progress request while asset gate was closed');assert.deepEqual(state,before);
  checks.push({check:'asset-error-blocked-input-no-progress-request',label,passed:true});
}
async function controlledAssetFailure(page,assetPattern) {
  assert.equal(typeof assetPattern,'string');assert(assetPattern.includes('.svg'),'Controlled failure targets an actual external SVG only');
  let failedRequests=0;const abort=async route=>{failedRequests++;await route.abort('failed');};
  await page.route(assetPattern,abort);
  return {get failedRequests(){return failedRequests;},release:()=>page.unroute(assetPattern,abort)};
}

async function markers(page) {return page.evaluate(()=>window.qaVisualMarkers||[]);}
async function trackMarkers(page) {
  await page.evaluate(()=>{
    window.qaVisualMarkers=[];window.qaVisualObserver?.disconnect();
    window.qaVisualObserver=new MutationObserver(records=>{for(const record of records) if(record.attributeName==='data-animation') {
      for(const value of [record.oldValue,record.target.getAttribute('data-animation')]) if(value&&value!=='idle') window.qaVisualMarkers.push(value);
    }});window.qaVisualObserver.observe(document.body,{subtree:true,attributes:true,attributeOldValue:true,attributeFilter:['data-animation']});
  });
}
async function visualOpening(page) {
  await roomView(page);await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-assets-ready','true');
  assert.equal(await page.locator('.game-canvas-host canvas').count(),1);assert.equal(await page.locator('.object-grid').count(),0);
  assert.equal(state.clues.length,0);assert(!state.objects.some(object=>['r1_photo','r1_symbols','r1_fuse'].includes(object.object_id)));
  assert.equal(await page.locator('.scene-keyboard-hotspot[data-object-id="r1_photo"]').count(),0);
  assert(!await page.locator('body').innerText().then(value=>value.includes('4217')));
  await trackMarkers(page);await assetGateSnapshot(page,'**/r1_background.svg*','R1-gated-early',async()=>{await select(page,'r1_cabinet');await expect(page.locator('#code-r1_cabinet')).toBeEnabled();});await select(page,'r1_clock',true);await expect.poll(async()=>await page.locator('.presentation-observer').getAttribute('data-audio-state')).toBe('ready');await replayReceiptThroughUI(page,'r1_clock');await canvasPixels(page,'R1-clock-closeup');await page.locator('.visual-room').screenshot({path:path.join(folder,'R1-clock-closeup.png')});
  await roomView(page);await page.getByRole('button',{name:'线索笔记',exact:true}).click();
  const notebook=page.locator('.notebook-modal');await expect(notebook).toBeVisible();
  assert.equal(await notebook.locator('.clue-list li').count(),1);await expect(notebook).toContainText(state.clues[0].text);
  await notebook.getByRole('button',{name:'合上笔记',exact:true}).click();
  // Synthetic UI input only: never press ask with the real-provider option selected.
  await partner(page);let calls=0;const listener=request=>{if(new URL(request.url()).pathname.endsWith('/ai/turns')) calls++;};page.on('request',listener);
  await page.locator('input[name="ai-provider"][value="deepseek"]').check();await page.locator('#ai-api-key').fill('QA-NOT-A-CREDENTIAL');
  await page.getByRole('button',{name:'关闭伙伴',exact:true}).click();await partner(page);await expect(page.locator('#ai-api-key')).toHaveValue('QA-NOT-A-CREDENTIAL');
  await page.locator('input[name="ai-provider"][value="mock"]').check();await page.locator('input[name="ai-provider"][value="deepseek"]').check();await expect(page.locator('#ai-api-key')).toHaveValue('');
  await page.locator('input[name="ai-provider"][value="mock"]').check();assert.equal(calls,0);page.off('request',listener);await closeDrawer(page);
  checks.push({check:'assistant-local-close-open-preserves-ephemeral-input-mock-clears-no-call',passed:true});
  checks.push({check:'scene-ready-one-canvas-hidden-membership-notebook-original-fact',passed:true});
}
async function visualSampleSnapshots(page,service,earlyArchive) {
  // Correct action follows wrong visible observed target; only statistics change on the failure.
  await observe(page,'r1_clock');const before=structuredClone(state);
  await use(page,'sample_slide','r1_clock',409);countedMistake(before);
  const sample=await appendMoment(page,'样本拿取时刻');await retrieveMoment(page,earlyArchive);
  await closeDrawer(page);await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view','room');
  await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-cabinet-state','LOCKED');assert.equal(state.inventory.length,0);
  const beforeMarkers=(await markers(page)).length;await retrieveMoment(page,sample);
  await closeDrawer(page);await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-animation','idle');assert.equal((await markers(page)).length,beforeMarkers);
  await refresh(page);assert.deepEqual(publicGame(state),publicGame(sample.state));
  const restart=structuredClone(state);await stop(service.backend);start('visual-R1-sample-backend-restarted',python,service.backendArgs,service.backendEnv);await ready(service.backendURL+'/api/health');
  await menu(page);await http(page,'state',()=>page.getByRole('button',{name:'同步进度',exact:true}).click(),200,'/state');assert.deepEqual(state,restart);
  await closeDrawer(page);await expect(page.locator('.game-canvas-host canvas')).toHaveCount(1);
  await trackMarkers(page);
  checks.push({check:'R1-wrong-held-item-preserved-and-selected-archives-reload-process-restart-snapshot-only',passed:true});
}
async function visualCabinet(page) {
  await select(page,'r1_cabinet');await expect(page.locator('#code-r1_cabinet')).toHaveValue('');
  assert.equal(await page.locator('.scene-keyboard-hotspot[data-object-id="r1_photo"]').count(),0);
  await presentationSettings(page,true,true);const previous=structuredClone(state), markerCount=(await markers(page)).length;
  await page.locator('#code-r1_cabinet').fill('0000');await http(page,'R1-wrong-lock-code',()=>page.locator('.code-form').getByRole('button',{name:'提交',exact:true}).click(),409);
  countedMistake(previous);assert.equal(state.device_states.cabinet,'LOCKED');assert.equal((await markers(page)).length,markerCount);await presentationSettings(page,false,false);
  await page.locator('.visual-room').screenshot({path:path.join(folder,'R1-wrong-code-locked.png')});
  await roomView(page);await page.getByRole('button',{name:'线索笔记',exact:true}).click();
  const notebook=page.locator('.notebook-modal'),texts=[];
  do {
    const rows=await notebook.locator('.clue-list li p').allTextContents();assert(rows.length<=2);texts.push(...rows);
    if(!await notebook.getByRole('button',{name:'下一页',exact:true}).isEnabled()) break;
    await notebook.getByRole('button',{name:'下一页',exact:true}).click();
  }while(true);
  assert.deepEqual(texts,state.clues.map(clue=>clue.text));await notebook.getByRole('button',{name:'合上笔记',exact:true}).click();
  checks.push({check:'locked-no-autofill-wrong-receipt-no-animation-notebook-pages-original-facts',passed:true});
}

async function lightOldVersion(version, level, key) {
  const service = await pair(version), context = await browser.newContext({ viewport: { width: 1280, height: 900 } }), page = await context.newPage();
  state = undefined; await installAudioProbe(context);const lazy=requestMeasurement(page);await page.goto(service.frontendURL, { waitUntil: 'networkidle' });
  await page.evaluate(() => sessionStorage.setItem('campus-lab-session-upgrade-v3.4', 'qa-preserve-v34'));
  await http(page, 'create', () => page.getByRole('button', { name: '开始新游戏 →', exact: true }).click(), 201, '/api/sessions');
  assert.equal(state.level_version, level); if (version === 'v3.2' || version === 'v3.3') assert(state.puzzle_states); else assert.equal(state.puzzle_states, undefined); if (version === 'v3.3') assert(state.minigames); else assert.equal(state.minigames, undefined); assert.equal(state.statistics,undefined); assert.equal(state.settlement,undefined);
  assert(await page.evaluate(key => !!sessionStorage.getItem(key), key));
  assert.equal(await page.evaluate(() => sessionStorage.getItem('campus-lab-session-upgrade-v3.4')), 'qa-preserve-v34');
  await observe(page, 'r1_cabinet'); const saved = (await control(page, 'save')).data.visible_state;
  await control(page, 'reset'); await control(page, 'restore'); assert.deepEqual(publicGame(state), publicGame(saved));
  lazy.stop();assert.equal(lazy.requests.filter(isEngineRequest).length,0,'Legacy UI must not request Phaser or visual scenes');checks.push({check:'legacy-no-engine-actual-browser-requests',mode:version,requests:lazy.requests,passed:true});checks.push({ check: 'light-old-mode-selection-save-slot-and-namespace', mode: version, level, passed: true }); await context.close();
}
async function moduleInput(page,id,keyboard=false,touch=false) {
  const host=page.locator('.game-canvas-host[data-room="R2"]');await expect(host).toHaveAttribute('data-assets-ready','true');
  const zone=host.locator(`.scene-keyboard-hotspot[data-module-id="${id}"]`);await expect(zone).toHaveCount(1);await expect(zone).toBeEnabled();
  if(keyboard) {await zone.focus();await zone.press('Enter');return;}
  await canvasSizeReady(host);const values=(await zone.getAttribute('data-bounds')).split(',').map(Number),box=await host.locator('canvas').boundingBox();assert(box);
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
  const currentView=await host.getAttribute('data-view');
  if(currentView==='r2_monitor'&&state.device_states.computer==='LOGIN_LOCKED') {await expect(page.locator('.crt-login')).toHaveCount(1);await expect(page.locator('#terminal-username')).toHaveCount(1);await expect(page.locator('#terminal-password')).toHaveCount(1);}
  else assert.equal(await page.locator('.crt-login').count(),0);
  if(state.device_states.powerbox==='POWER_ON'&&currentView==='r2_powerbox') {await expect(host.locator('.scene-keyboard-hotspot[data-object-id="r2_service_label"]')).toHaveCount(1);}
  if(state.device_states.powerbox!=='POWER_ON') {assert(!state.objects.some(object=>object.object_id==='r2_service_label'));assert.equal(await page.locator('.scene-keyboard-hotspot[data-object-id="r2_service_label"]').count(),0);}
  if(state.device_states.computer!=='DATA_READ') {assert(!state.objects.some(object=>['research_strip','access_card'].includes(object.object_id)));assert.equal(await page.locator('.scene-keyboard-hotspot[data-object-id="research_strip"],.scene-keyboard-hotspot[data-object-id="access_card"]').count(),0);}
  const measured=await page.evaluate(()=>{
    const nodes=selector=>[...document.querySelectorAll(selector)].filter(node=>node.getClientRects().length);
    const rect=node=>node.getBoundingClientRect(),overlap=(a,b)=>Math.min(a.right,b.right)>Math.max(a.left,b.left)&&Math.min(a.bottom,b.bottom)>Math.max(a.top,b.top);
    const feedback=nodes('.feedback p').map(rect),content=nodes('.game-hud button,.closeup-reading,.closeup-description,.closeup-controls button,.closeup-controls input,.closeup-controls label,.crt-login input,.crt-login label,.crt-login button').map(rect);
    return {feedback_overlaps:feedback.flatMap(a=>content.filter(b=>overlap(a,b))).length,horizontal_overflow:content.filter(b=>b.left<0||b.right>innerWidth).length};
  });assert.equal(measured.feedback_overlaps,0);assert.equal(measured.horizontal_overflow,0);
  await page.screenshot({path:path.join(folder,label+'.png'),fullPage:true});await canvasPixels(page,label);
  checks.push({check:'R2-public-state-membership-rendering-and-readable-controls',label,powerbox:state.device_states.powerbox,computer:state.device_states.computer,power_on:state.progress.power_on,...measured,passed:true});
}
async function touchR2Smoke(service) {
  // A synthetic context creates its own session; it cannot read another session's archive.
  const context=await browser.newContext({viewport:{width:375,height:812},hasTouch:true,isMobile:true,deviceScaleFactor:1}),page=await context.newPage();
  const errors=[];page.on('pageerror',()=>errors.push('uncaught R2 touch exception'));state=undefined;
  await installAudioProbe(context);await page.goto(service.frontendURL,{waitUntil:'networkidle'});await http(page,'R2-touch-create',()=>page.getByRole('button',{name:'开始新游戏 →',exact:true}).click(),201,'/api/sessions');await trackMarkers(page);
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
async function normalProgressToR3(page,withGates=false) {
  if(withGates)await assetGateSnapshot(page,'**/r1_background.svg*','narrow-R1');
  for(const id of ['r1_clock','r1_record','r1_plaque','sample_slide'])await observe(page,id);
  await interact(page,'sample_slide');await use(page,'sample_slide','r1_microscope');await observe(page,'r1_microscope');await code(page,'r1_cabinet','4217');await interact(page,'r1_cabinet');
  await observe(page,'r1_symbols');await observe(page,'r1_fuse');await interact(page,'r1_fuse');await observe(page,'r1_door');await interact(page,'r1_door');await move(page,'R2');await observe(page,'r2_maintenance');
  await interact(page,'r2_powerbox');await interact(page,'r2_powerbox');await use(page,'fuse','r2_powerbox');await openCircuit(page);const solution=deriveCircuit(state.minigames.circuit);
  for(const module of [...state.minigames.circuit.modules])for(let turn=0;turn<(solution[module.module_id]-module.rotation+4)%4;turn++)await rotate(page,module.module_id);
  await submitCircuit(page);await interact(page,'r2_powerbox');await interact(page,'r2_monitor');await interact(page,'r2_monitor');
  if(withGates)await assetGateSnapshot(page,'**/r2_background_dark.svg*','narrow-R2',async()=>{await select(page,'r2_monitor');await expect(page.locator('#terminal-password')).toBeEnabled();});
  await login(page,'LAB-42','2117');await interact(page,'r2_monitor');await interact(page,'research_strip');await interact(page,'access_card');await observe(page,'r2_door');await interact(page,'r2_door');await move(page,'R3');
  await observe(page,'r3_legend');await observe(page,'r3_panel');await use(page,'research_strip','r3_panel');await observe(page,'exit_door');await use(page,'access_card','exit_door');await interact(page,'exit_door');
  if(withGates)await assetGateSnapshot(page,'**/r3_background.svg*','narrow-R3',()=>openSequence(page));await openSequence(page);
}
async function remainingRun(service) {
  const context=await browser.newContext({viewport:{width:1280,height:900}});await installAudioProbe(context);const page=await context.newPage();state=undefined;
  const pageErrors=[];page.on('pageerror',()=>pageErrors.push('uncaught remaining browser exception'));
  await page.goto(service.frontendURL,{waitUntil:'networkidle'});await http(page,'remaining-owned-create',()=>page.getByRole('button',{name:'开始新游戏 →',exact:true}).click(),201,'/api/sessions');await trackMarkers(page);
  const earlyArchive=await appendMoment(page,'早期时刻（remaining准备）');
  for(const id of ['r1_clock','r1_record','r1_plaque','r1_microscope'])await observe(page,id);
  for(const level of [1,2,3])await hint(page,level);await closeDrawer(page);
  await interact(page,'sample_slide');await appendMoment(page,'样本拿取时刻（remaining准备）');await use(page,'sample_slide','r1_microscope');await observe(page,'r1_microscope');
  await code(page,'r1_cabinet','4217');await interact(page,'r1_cabinet');await observe(page,'r1_symbols');await interact(page,'r1_fuse');await observe(page,'r1_photo');
  await observe(page,'r1_door');await interact(page,'r1_door');await move(page,'R2');await observe(page,'r2_maintenance');await interact(page,'r2_powerbox');await interact(page,'r2_powerbox');await use(page,'fuse','r2_powerbox');await openCircuit(page);
  await rotate(page,state.minigames.circuit.modules[0].module_id);await control(page,'save');const partialArchive=await appendMoment(page,'线路板中期（remaining准备）');
  const solution=deriveCircuit(state.minigames.circuit);for(const module of [...state.minigames.circuit.modules])for(let turn=0;turn<(solution[module.module_id]-module.rotation+4)%4;turn++)await rotate(page,module.module_id);
  await submitCircuit(page);await interact(page,'r2_powerbox');const powerArchive=await appendMoment(page,'已通电时刻（remaining准备）');await observe(page,'r2_service_label');await interact(page,'r2_monitor');await interact(page,'r2_monitor');
  await assetGateSnapshot(page,'**/r2_background_dark.svg*','R2-gated-login',async()=>{await select(page,'r2_monitor');await expect(page.locator('#terminal-username')).toBeEnabled();});
  checks.push({check:'necessary-normal-public-prerequisites-and-real-moments-rebuilt-for-unpassed-tail',passed:true,scope:'Does not repeat passed early exploration/XSS/wrong-lock/wrong-item/alternate-circuit/full R1 snapshot regression'});
  assert.equal(state.device_states.computer, 'LOGIN_LOCKED'); const saved = (await control(page, 'save')).data.visible_state;
  const beforeWrong = structuredClone(state); await login(page, 'LAB-41', '2117', 409); countedMistake(beforeWrong);
  await login(page, 'LAB-42', '2117'); assert.equal(state.device_states.computer, 'UNLOCKED');await r2Checkpoint(page,'R2-monitor-UNLOCKED-no-items-yet');
  await control(page, 'restore'); assert.deepEqual(publicGame(state), publicGame(saved));
  await refresh(page); assert.equal(state.device_states.computer, 'LOGIN_LOCKED');
  const beforeRestart = structuredClone(state); await stop(service.backend);
  start('v3.4-backend-restarted', python, service.backendArgs, service.backendEnv); await ready(service.backendURL + '/api/health');
  await menu(page);await http(page, 'state', () => page.getByRole('button', { name: '同步进度', exact: true }).click(), 200, '/state');
  assert.deepEqual(state, beforeRestart);
  await select(page,'r2_monitor');
  await expect(page.locator('#terminal-username')).toHaveCount(1);await expect(page.locator('#terminal-password')).toHaveCount(1);
  await expect(page.locator('#terminal-username')).toHaveValue('');await expect(page.locator('#terminal-password')).toHaveValue('');
  await layout(page, 1280, 'R2-login-visual'); await page.screenshot({ path: path.join(folder, 'R2-visual.png'), fullPage: true });
  await page.setViewportSize({ width: 375, height: 812 }); await layout(page,375,'R2-mobile-login');await page.screenshot({path:path.join(folder,'R2-mobile-login.png'),fullPage:true});await page.setViewportSize({width:1280,height:900});
  await login(page,'LAB-42','2117');await interact(page,'r2_monitor');assert.equal(state.device_states.computer,'DATA_READ');
  assert(state.objects.some(object=>object.object_id==='research_strip'));assert(state.objects.some(object=>object.object_id==='access_card'));
  assert(!state.inventory.some(item=>['research_strip','access_card'].includes(item.item_id)));await r2Checkpoint(page,'R2-DATA_READ-tray-items-not-auto-taken');await page.setViewportSize({width:375,height:812});await r2Checkpoint(page,'R2-DATA_READ-tray-mobile');await page.setViewportSize({width:1280,height:900});
  await observe(page,'research_strip');await interact(page,'research_strip');assert(state.inventory.some(item=>item.item_id==='research_strip'));assert(!state.objects.some(object=>object.object_id==='research_strip'));assert(state.objects.some(object=>object.object_id==='access_card'));
  await observe(page,'access_card');await interact(page,'access_card');await r2Checkpoint(page,'R2-tray-both-items-taken');
  await move(page, 'R3'); await observe(page,'r3_legend');await observe(page, 'r3_panel'); await observe(page, 'exit_door');
  await use(page, 'research_strip', 'r3_panel'); assert.equal(state.puzzle_states.panel, 'STRIP_INSERTED');await r3Checkpoint(page,'R3-strip-inserted');
  await use(page, 'access_card', 'exit_door'); assert.equal(state.device_states.exit, 'CARD_ACCEPTED');await r3Checkpoint(page,'R3-CARD_ACCEPTED');
  const cardState = structuredClone(state); await move(page, 'EXIT', 409); assert.deepEqual(state, cardState);
  await interact(page,'exit_door');assert.equal(state.device_states.exit,'FINAL_CHECK');await r3Checkpoint(page,'R3-FINAL_CHECK');await assetGateSnapshot(page,'**/r3_background.svg*','R3-gated-sequence',()=>openSequence(page));await openSequence(page); const beforeSequence=structuredClone(state), derivedSequence=deriveSequence(state);
  const draftBeforeState=structuredClone(state); const wrongSequence=derivedSequence.slice(1).concat(derivedSequence[0]);
  await draftSequence(page,wrongSequence.slice(0,3)); await expect(page.locator('.sequence-submit')).toBeDisabled(); assert.deepEqual(state,draftBeforeState);
  await sequenceInput(page,wrongSequence[3]); await submitSequence(page,409); countedMistake(beforeSequence);
  const wrongDraft=await page.locator('.sequence-draft li').allTextContents(); assert.equal(wrongDraft.length,4); for(let index=0;index<4;index++) assert(wrongDraft[index].includes(state.minigames.sequence.devices.find(device => device.device_id===wrongSequence[index]).label));
  await draftSequence(page,[derivedSequence[0],derivedSequence[0],derivedSequence[2],derivedSequence[3]]); const beforeDuplicate=structuredClone(state); await submitSequence(page,422); assert.deepEqual(state,beforeDuplicate);
  await draftSequence(page,derivedSequence.slice(0,2)); const draftSaved=(await control(page,'save')).data.visible_state;
  await control(page,'restore'); assert.deepEqual(publicGame(state),publicGame(draftSaved)); await openSequence(page); await expect(page.locator('.sequence-submit')).toBeDisabled();
  await draftSequence(page,derivedSequence.slice(0,2)); await refresh(page); await openSequence(page); await expect(page.locator('.sequence-submit')).toBeDisabled();
  await draftSequence(page,derivedSequence.slice(0,2)); await move(page,'R2'); await move(page,'R3'); await openSequence(page); await expect(page.locator('.sequence-submit')).toBeDisabled();
  await r3Checkpoint(page,'R3-public-sequence-desktop');await layout(page,1280,'R3-sequence-panel'); await page.screenshot({path:path.join(folder,'R3-sequence-panel.png'),fullPage:true});
  await page.setViewportSize({width:375,height:812}); await r3Checkpoint(page,'R3-public-sequence-mobile');await layout(page,375,'R3-mobile-sequence'); await page.setViewportSize({width:1280,height:900});
  await touchR3SameOwnedSession(service,page);await draftSequence(page,derivedSequence); await submitSequence(page); assert.equal(state.progress.check_done,true); assert.equal(state.device_states.exit,'FINAL_CHECK');
  const miniCompleted=(await control(page,'save')).data.visible_state; await control(page,'reset'); await control(page,'restore'); await refresh(page); assert.deepEqual(publicGame(state),publicGame(miniCompleted));
  checks.push({check:'cross-room-public-sequence-wrong-duplicates-draft-clears-restore-reload-room-and-completed-save',passed:true,derived_sequence:derivedSequence});
  const checkedState = structuredClone(state); await move(page, 'EXIT', 409); assert.deepEqual(state, checkedState);
  await interact(page, 'exit_door'); assert.equal(state.device_states.exit, 'UNLOCKED');await r3Checkpoint(page,'R3-UNLOCKED');
  await select(page,'exit_door');const openMarkers=(await markers(page)).length;
  await http(page,'interact:exit_door',()=>canvasInput(page,'exit_door','interact'));assert.equal(state.device_states.exit,'OPEN');assert.equal(state.status,'playing');
  await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-animation','door_open');await expect(page.locator('.room3-controls [data-scene-action="move"]')).toBeDisabled();for(const zone of await page.locator('.scene-keyboard-hotspot').all())await expect(zone).toBeDisabled();
  const openState=structuredClone(state);await gateAttempt(page,'one-second-door-opening-Canvas',async()=>{const box=await page.locator('.game-canvas-host canvas').boundingBox();await page.mouse.click(box.x+box.width*.5,box.y+box.height*.5);});assert.deepEqual(state,openState);
  await page.locator('.game-canvas-host canvas').screenshot({path:path.join(folder,'R3-door-opening-frame.png')});await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-animation','idle');assert((await markers(page)).slice(openMarkers).includes('door_open'));
  await r3Checkpoint(page,'R3-OPEN');await move(page, 'EXIT'); assert.equal(state.status, 'won');await authoritativeVictory(page);
  await expect(page.getByRole('heading', { name: '逃离成功', exact: true })).toBeVisible();
  const score=structuredClone(state.settlement); assert(score); assert.equal(score.clues_found,10); assert.equal(score.hidden_found,2); assert.equal(score.hint_count,3); assert.equal(score.rating,publicRating(score));
  assert.equal(score.elapsed_seconds,Math.max(0,Math.floor((Date.parse(state.statistics.finished_at)-Date.parse(state.statistics.started_at))/1000)));
  await expect(page.locator('.victory-screen [data-stat="rating"]')).toHaveText(score.rating);
  await expect(page.locator('.victory-screen [data-stat="clues_found"]')).toHaveText('10/10'); await expect(page.locator('.victory-screen [data-stat="hidden_found"]')).toHaveText('2/2');
  const wonSaved=(await control(page,'save')).data.visible_state; await refresh(page); assert.deepEqual(publicGame(state),publicGame(wonSaved));
  const frozenWin=structuredClone(state); await stop(service.backend); start('v3.4-backend-win-restarted',python,service.backendArgs,service.backendEnv); await ready(service.backendURL+'/api/health');
  await menu(page);await http(page,'state',() => page.getByRole('button',{name:'同步进度',exact:true}).click(),200,'/state'); assert.deepEqual(state,frozenWin); assert.deepEqual(state.settlement,score);
  await closeDrawer(page);await http(page,'victory-reset',async()=>{await page.locator('.victory-reset').click();await page.getByRole('dialog').getByRole('button',{name:'确认开始',exact:true}).click();},200,'/reset'); assert.equal(state.statistics.hint_count,0); assert.equal(state.statistics.mistake_count,0); assert.equal(state.statistics.finished_at,null); assert.equal(state.settlement,null); assert(state.save);
  await control(page,'restore'); assert.deepEqual(publicGame(state),publicGame(wonSaved)); assert.deepEqual(state.settlement,score);
  const wonArchive=await appendMoment(page,'通关时刻');
  await expect(page.locator('.save-slot')).toHaveCount(6);
  await page.locator('.save-panel').screenshot({path:path.join(folder,'desktop-three-archive-list.png')});
  await refresh(page);await expect(page.locator('.save-slot')).toHaveCount(6);
  const beforeArchiveRestart=structuredClone(state);await stop(service.backend);
  start('multiple-saves-backend-list-restarted',python,service.backendArgs,service.backendEnv);await ready(service.backendURL+'/api/health');
  await menu(page);await http(page,'state',() => page.getByRole('button',{name:'同步进度',exact:true}).click(),200,'/state');
  assert.deepEqual(state,beforeArchiveRestart);await expect(page.locator('.save-slot')).toHaveCount(6);
  await control(page,'reset');await expect(page.locator('.save-slot')).toHaveCount(6);
  await retrieveMoment(page,earlyArchive);await retrieveMoment(page,partialArchive);await assertSnapshotIdle(page);await retrieveMoment(page,powerArchive);await assertSnapshotIdle(page);await retrieveMoment(page,wonArchive);
  assert.deepEqual(state.settlement,score);await expect(page.locator('.save-slot')).toHaveCount(6);
  checks.push({check:'five-immutable-archives-plus-old-slot-persist-reset-refresh-OSrestart',passed:true,archive_count:5,legacy_count:1});
  checks.push({check:'settlement-authoritative-UTC-score-winfreeze-reset-slot-restore-refresh-OSrestart',passed:true,settlement:score});
  await page.setViewportSize({ width: 375, height: 812 }); await layout(page, 375, 'mobile-victory');await menu(page);
  await page.locator('.save-panel').screenshot({path:path.join(folder,'mobile-three-archive-list.png')});
  await page.locator(`.save-slot[data-save-id="${partialArchive.slot.save_id}"] .save-slot-restore`).click();
  await page.getByRole('dialog').screenshot({path:path.join(folder,'mobile-selected-restore-confirmation.png')});
  await page.getByRole('dialog').getByRole('button',{name:'取消',exact:true}).click();assert.deepEqual(state.settlement,score);
  await closeDrawer(page);await settledRoomTransition(page);await page.screenshot({ path: path.join(folder, 'mobile-victory.png'), fullPage: true }); assert.equal(pageErrors.length, 0);
  checks.push({ check: 'three-room-route-slots-items-save-restore-reload-actual-server-restart-win', passed: true, final_room: state.room.room_id });
  await context.close();
  await touchSmoke(service);await touchR2Smoke(service);await productionStartupMeasurement(service);
  await lightOldVersion('legacy', '2.0.0', 'campus-lab-session-v1');
  await lightOldVersion('v3.1', '3.1.0', 'campus-lab-session-upgrade-v3.1');
  await lightOldVersion('v3.2', '3.2.0', 'campus-lab-session-upgrade-v3.2');
  await lightOldVersion('v3.3', '3.3.0', 'campus-lab-session-upgrade-v3.3');
}
async function runNecessaryScope(service,mode) {
  if(mode==='remaining') {await remainingRun(service);return;}
  if(mode==='production') {await productionStartupMeasurement(service);return;}
  if(mode==='legacy') {for(const [version,level,key]of [['legacy','2.0.0','campus-lab-session-v1'],['v3.1','3.1.0','campus-lab-session-upgrade-v3.1'],['v3.2','3.2.0','campus-lab-session-upgrade-v3.2'],['v3.3','3.3.0','campus-lab-session-upgrade-v3.3']])await lightOldVersion(version,level,key);return;}
  const context=await browser.newContext({viewport:{width:1280,height:900}});await installAudioProbe(context);const page=await context.newPage(),errors=[];page.on('pageerror',()=>errors.push('uncaught narrow browser exception'));state=undefined;
  await page.goto(service.frontendURL,{waitUntil:'networkidle'});await http(page,'necessary-scope-create',()=>page.getByRole('button',{name:'开始新游戏 →',exact:true}).click(),201,'/api/sessions');await trackMarkers(page);
  if(mode==='audio') {
    await observe(page,'r1_clock');await expect(page.locator('.presentation-observer')).toHaveAttribute('data-audio-state','ready');await replayReceiptThroughUI(page,'r1_clock');
    await presentationSettings(page,true,true);await observe(page,'r1_record');await presentationSettings(page,false,false);await observe(page,'r1_plaque');
    await control(page,'save');await control(page,'reset');await control(page,'restore');await refresh(page);
    const events=await audioEvents(page);assert.equal(audibleAttempts(events).length,0,'Reload/continue must not emit receipt cues');
  }else {
    await normalProgressToR3(page,mode==='gates');
    if(mode==='touch-r3')await touchR3SameOwnedSession(service,page);
    if(mode==='victory') {await draftSequence(page,deriveSequence(state));await submitSequence(page);await interact(page,'exit_door');await interact(page,'exit_door');await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-animation','idle');await move(page,'EXIT');await authoritativeVictory(page);await menu(page);await closeDrawer(page);await http(page,'narrow-Victory-reset',async()=>{await page.locator('.victory-reset').click();await page.getByRole('dialog').getByRole('button',{name:'确认开始',exact:true}).click();},200,'/reset');assert.equal(state.room.room_id,'R1');assert.equal(state.settlement,null);}
  }
  assert.equal(errors.length,0);await context.close();checks.push({check:'necessary-scope-only-adapter-followup',mode,passed:true,scope:'normal authorized public preparation plus named affected checks; no whole archives/regression suite'});
}
try {
  assert(fs.existsSync(chromePath));
  const service = await pair('v3.4');
  browser = await chromium.launch({ headless: true, executablePath: chromePath });
  if(only!=='full')await runNecessaryScope(service,only);else {
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } }), page = await context.newPage();
  const pageErrors = []; page.on('pageerror', () => pageErrors.push('uncaught browser exception'));
  await installAudioProbe(context);const startupRequests=requestMeasurement(page);await page.goto(service.frontendURL, { waitUntil: 'networkidle' });await firstLaunch(page,startupRequests,'development');startupRequests.stop();
  await page.evaluate(() => { sessionStorage.setItem('campus-lab-session-v1', 'qa-preserve-legacy'); sessionStorage.setItem('campus-lab-session-upgrade-v3.1', 'qa-preserve-v31'); sessionStorage.setItem('campus-lab-session-upgrade-v3.2', 'qa-preserve-v32'); sessionStorage.setItem('campus-lab-session-upgrade-v3.3', 'qa-preserve-v33'); });
  await http(page, 'create', () => page.getByRole('button', { name: '开始新游戏 →', exact: true }).click(), 201, '/api/sessions');
  assert.equal(state.level_version, '3.4.0'); assert.equal(state.schema_version, '1.4.0');
  assert(await page.evaluate(() => !!sessionStorage.getItem('campus-lab-session-upgrade-v3.4')));
  assert.equal(await page.evaluate(() => sessionStorage.getItem('campus-lab-session-v1')), 'qa-preserve-legacy');
  assert.equal(await page.evaluate(() => sessionStorage.getItem('campus-lab-session-upgrade-v3.1')), 'qa-preserve-v31');
  assert.equal(await page.evaluate(() => sessionStorage.getItem('campus-lab-session-upgrade-v3.2')), 'qa-preserve-v32');
  assert.equal(await page.evaluate(() => sessionStorage.getItem('campus-lab-session-upgrade-v3.3')), 'qa-preserve-v33');
  const earlyArchive=await appendMoment(page,'早期 <img src=x onerror=QA_INJECTION>');
  assert.equal(await page.locator('.save-slot-list img').count(),0);
  assert.equal(await page.evaluate(() => window.QA_INJECTION),undefined);
  await expect(page.locator('.save-slot-list')).toContainText(earlyArchive.slot.name);
  await page.locator('.save-panel').screenshot({path:path.join(folder,'early-archive-list.png')});
  assert.deepEqual(state.minigames, { circuit: null, sequence: null });
  assert.equal(state.statistics.clues_total,10); assert.equal(state.statistics.hidden_total,2); assert.equal(state.statistics.hint_count,0); assert.equal(state.settlement,null); await hint(page,3,false);
  await visualOpening(page); await closeDrawer(page); await layout(page,1920,'R1-visual-desktop'); await page.screenshot({path:path.join(folder,'R1-visual-desktop.png'),fullPage:true});
  await page.setViewportSize({ width: 375, height: 812 }); await layout(page,375,'R1-mobile');await page.screenshot({path:path.join(folder,'R1-visual-mobile.png'),fullPage:true});await page.setViewportSize({width:1280,height:900});
  // Prove early exploration, before obtaining any item or powering/login.
  await observe(page, 'r1_door'); await interact(page, 'r1_door'); await move(page, 'R2');
  await r2Checkpoint(page,'R2-initial-dark-no-tray-no-service');await observe(page, 'r2_door'); await interact(page, 'r2_door'); await move(page, 'R3'); await observe(page, 'r3_legend');
  assert.equal(state.inventory.length, 0); assert.equal(state.device_states.computer, 'OFF');
  await r3Checkpoint(page,'R3-EMPTY-LOCKED');await layout(page, 1280, 'R3-early-visual'); await page.screenshot({ path: path.join(folder, 'R3-visual.png'), fullPage: true });
  await page.setViewportSize({ width: 375, height: 812 }); await layout(page, 375, 'R3-mobile'); await page.setViewportSize({ width: 1280, height: 900 });
  await move(page, 'R2'); await move(page, 'R1');
  await observe(page, 'r1_clock'); await observe(page, 'r1_record'); await observe(page, 'r1_plaque');
  const levelAnswers=[]; for(const level of [1,2,3]) levelAnswers.push(await hint(page,level)); assert.equal(new Set(levelAnswers).size,3); await closeDrawer(page);await menu(page);await expect(page.locator('.menu-statistics [data-stat="hint_count"]')).toHaveText('3');await closeDrawer(page);
  await observe(page, 'r1_microscope'); await observe(page, 'sample_slide'); await interact(page, 'sample_slide');
  await visualSampleSnapshots(page,service,earlyArchive);
  await use(page, 'sample_slide', 'r1_microscope'); assert.equal(state.puzzle_states.microscope, 'SLIDE_PLACED');
  await observe(page, 'r1_microscope'); assert(state.clues.some(clue => clue.object_id === 'r1_microscope' && clue.text.includes('42')));
  await visualCabinet(page);
  await observe(page, 'r1_cabinet'); await code(page, 'r1_cabinet', '4217');assert.equal(state.device_states.cabinet,'CODE_ACCEPTED');await expect.poll(async()=> (await markers(page)).includes('submit_code')).toBe(true);await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-cabinet-state','CODE_ACCEPTED');await page.locator('.visual-room').screenshot({path:path.join(folder,'R1-code-accepted-still-closed.png')});await interact(page,'r1_cabinet');assert.equal(state.device_states.cabinet,'OPEN');await page.locator('.visual-room').screenshot({path:path.join(folder,'R1-cabinet-open.png')});
  await observe(page, 'r1_symbols'); await observe(page, 'r1_fuse'); await interact(page, 'r1_fuse'); await observe(page,'r1_photo'); assert.equal(state.statistics.hidden_found,1); await move(page, 'R2');
  await observe(page,'r2_maintenance');await r2Checkpoint(page,'R2-maintenance-original-text');
  await observe(page,'r2_powerbox');await r2Checkpoint(page,'R2-powerbox-CLOSED');
  await interact(page,'r2_powerbox');assert.equal(state.device_states.powerbox,'OPEN');await r2Checkpoint(page,'R2-powerbox-OPEN');
  await interact(page,'r2_powerbox');assert.equal(state.device_states.powerbox,'MISSING_FUSE');await r2Checkpoint(page,'R2-powerbox-MISSING_FUSE');
  await observe(page,'r2_monitor');const beforeWrongFuse=structuredClone(state);await use(page,'fuse','r2_monitor',409);countedMistake(beforeWrongFuse);await r2Checkpoint(page,'R2-wrong-held-fuse-keeps-dark-and-off');
  await use(page,'fuse','r2_powerbox');await r2Checkpoint(page,'R2-powerbox-FUSE_INSTALLED');
  assert.equal(state.progress.power_on, false); assert.equal(state.minigames.circuit.status,'editing');
  await openCircuit(page); assert.equal(await page.locator('.scene-keyboard-hotspot[data-module-id]').count(),9);
  const disconnected = structuredClone(state); assert.equal(connected(state.minigames.circuit),false);
  await submitCircuit(page,409); countedMistake(disconnected);
  const initialModule=state.minigames.circuit.modules[0];
  const beforeKeyboard=structuredClone(state);await http(page,'R2-independent-keyboard-module',()=>moduleInput(page,initialModule.module_id,true));
  assert.equal(state.minigames.circuit.modules[0].rotation,(beforeKeyboard.minigames.circuit.modules[0].rotation+1)%4);
  assert.equal(state.device_states.powerbox,'FUSE_INSTALLED');assert.equal(state.progress.power_on,false);
  checks.push({check:'R2-independent-keyboard-public-circuit-rotation',passed:true,module_id:initialModule.module_id});
  const partial = structuredClone(state); assert.equal(state.device_states.powerbox,'FUSE_INSTALLED'); assert.equal(state.progress.power_on,false);
  const partialSaved = (await control(page,'save')).data.visible_state; await control(page,'reset'); await control(page,'restore'); assert.deepEqual(publicGame(state),publicGame(partialSaved));
  const partialArchive=await appendMoment(page,'线路板中期');
  await expect(page.locator('.save-slot[data-save-id="legacy"]')).toBeVisible();
  await retrieveMoment(page,earlyArchive,true);await retrieveMoment(page,partialArchive);
  await expect(page.locator('.save-slot')).toHaveCount(4);
  await refresh(page); assert.deepEqual(publicGame(state),publicGame(partial));
  const beforeBoardRestart = structuredClone(state); await stop(service.backend);
  start('v3.4-backend-partial-board-restarted',python,service.backendArgs,service.backendEnv); await ready(service.backendURL+'/api/health');
  await menu(page);await http(page,'state',() => page.getByRole('button',{name:'同步进度',exact:true}).click(),200,'/state'); assert.deepEqual(state,beforeBoardRestart);
  await openCircuit(page); await layout(page,1280,'R2-partial-circuit'); await page.screenshot({path:path.join(folder,'R2-partial-circuit.png'),fullPage:true});
  await page.setViewportSize({width:375,height:812}); await layout(page,375,'R2-mobile-circuit');await page.screenshot({path:path.join(folder,'R2-mobile-circuit.png'),fullPage:true});await page.setViewportSize({width:1280,height:900});
  const solution = deriveCircuit(state.minigames.circuit), alternate = {...solution};
  const straight = state.minigames.circuit.modules.find(module => module.shape==='I'); alternate[straight.module_id]=(alternate[straight.module_id]+2)%4;
  assert(connected(state.minigames.circuit,solution)); assert(connected(state.minigames.circuit,alternate)); assert.notDeepEqual(solution,alternate);
  for (const module of [...state.minigames.circuit.modules]) for(let turn=0;turn<(alternate[module.module_id]-module.rotation+4)%4;turn++) await rotate(page,module.module_id);
  await submitCircuit(page); assert.equal(state.device_states.powerbox,'CIRCUIT_READY'); assert.equal(state.progress.power_on,false); assert.equal(state.minigames.circuit.status,'completed');
  await expect(page.locator('.scene-keyboard-hotspot[data-module-id]').first()).toBeDisabled();await r2Checkpoint(page,'R2-CIRCUIT_READY-still-dark-switch-required');await roomView(page);await r2Checkpoint(page,'R2-dark-overview-before-switch');const r2DarkOverview=sha(await page.locator('.game-canvas-host canvas').screenshot());
  checks.push({check:'partial-circuit-save-restore-refresh-OSrestart-and-alternate-public-connection',passed:true,public_derived_solution:solution,alternate});
  await interact(page,'r2_powerbox');assert.equal(state.device_states.powerbox,'POWER_ON');assert.equal(state.progress.power_on,true);
  await r2Checkpoint(page,'R2-POWER_ON-bright-service-present');
  await roomView(page);await r2Checkpoint(page,'R2-bright-overview-after-switch');assert.notEqual(sha(await page.locator('.game-canvas-host canvas').screenshot()),r2DarkOverview);checks.push({check:'R2-real-overview-pixels-differ-after-manual-server-switch',passed:true});
  const powerArchive=await appendMoment(page,'已通电时刻');await retrieveMoment(page,partialArchive);await assertSnapshotIdle(page);await retrieveMoment(page,powerArchive);await assertSnapshotIdle(page);
  await roomView(page);await r2Checkpoint(page,'R2-restored-powered-snapshot');
  await observe(page,'r2_service_label');await r2Checkpoint(page,'R2-service-label-original-story');assert.equal(state.statistics.hidden_found,2);await roomView(page);await select(page,'r2_powerbox');await http(page,'R2-actual-closeup-service-label-hit',()=>canvasInput(page,'r2_service_label'));await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view','r2_service_label');assert.equal(state.statistics.hidden_found,2);
  await observe(page,'r2_monitor');await r2Checkpoint(page,'R2-monitor-OFF');
  await interact(page,'r2_monitor');assert.equal(state.device_states.computer,'BOOTING');await r2Checkpoint(page,'R2-monitor-BOOTING');
  await interact(page,'r2_monitor');await r2Checkpoint(page,'R2-monitor-LOGIN_LOCKED');await assetGateSnapshot(page,'**/r2_background_dark.svg*','R2-gated-login',async()=>{await select(page,'r2_monitor');await expect(page.locator('#terminal-username')).toBeEnabled();});
  assert.equal(state.device_states.computer, 'LOGIN_LOCKED'); const saved = (await control(page, 'save')).data.visible_state;
  const beforeWrong = structuredClone(state); await login(page, 'LAB-41', '2117', 409); countedMistake(beforeWrong);
  await login(page, 'LAB-42', '2117'); assert.equal(state.device_states.computer, 'UNLOCKED');await r2Checkpoint(page,'R2-monitor-UNLOCKED-no-items-yet');
  await control(page, 'restore'); assert.deepEqual(publicGame(state), publicGame(saved));
  await refresh(page); assert.equal(state.device_states.computer, 'LOGIN_LOCKED');
  const beforeRestart = structuredClone(state); await stop(service.backend);
  start('v3.4-backend-restarted', python, service.backendArgs, service.backendEnv); await ready(service.backendURL + '/api/health');
  await menu(page);await http(page, 'state', () => page.getByRole('button', { name: '同步进度', exact: true }).click(), 200, '/state');
  assert.deepEqual(state, beforeRestart);
  await select(page,'r2_monitor');
  await expect(page.locator('#terminal-username')).toHaveCount(1);await expect(page.locator('#terminal-password')).toHaveCount(1);
  await expect(page.locator('#terminal-username')).toHaveValue('');await expect(page.locator('#terminal-password')).toHaveValue('');
  await layout(page, 1280, 'R2-login-visual'); await page.screenshot({ path: path.join(folder, 'R2-visual.png'), fullPage: true });
  await page.setViewportSize({ width: 375, height: 812 }); await layout(page,375,'R2-mobile-login');await page.screenshot({path:path.join(folder,'R2-mobile-login.png'),fullPage:true});await page.setViewportSize({width:1280,height:900});
  await login(page,'LAB-42','2117');await interact(page,'r2_monitor');assert.equal(state.device_states.computer,'DATA_READ');
  assert(state.objects.some(object=>object.object_id==='research_strip'));assert(state.objects.some(object=>object.object_id==='access_card'));
  assert(!state.inventory.some(item=>['research_strip','access_card'].includes(item.item_id)));await r2Checkpoint(page,'R2-DATA_READ-tray-items-not-auto-taken');await page.setViewportSize({width:375,height:812});await r2Checkpoint(page,'R2-DATA_READ-tray-mobile');await page.setViewportSize({width:1280,height:900});
  await observe(page,'research_strip');await interact(page,'research_strip');assert(state.inventory.some(item=>item.item_id==='research_strip'));assert(!state.objects.some(object=>object.object_id==='research_strip'));assert(state.objects.some(object=>object.object_id==='access_card'));
  await observe(page,'access_card');await interact(page,'access_card');await r2Checkpoint(page,'R2-tray-both-items-taken');
  await move(page, 'R3'); await observe(page, 'r3_panel'); await observe(page, 'exit_door');
  await use(page, 'research_strip', 'r3_panel'); assert.equal(state.puzzle_states.panel, 'STRIP_INSERTED');await r3Checkpoint(page,'R3-strip-inserted');
  await use(page, 'access_card', 'exit_door'); assert.equal(state.device_states.exit, 'CARD_ACCEPTED');await r3Checkpoint(page,'R3-CARD_ACCEPTED');
  const cardState = structuredClone(state); await move(page, 'EXIT', 409); assert.deepEqual(state, cardState);
  await interact(page,'exit_door');assert.equal(state.device_states.exit,'FINAL_CHECK');await r3Checkpoint(page,'R3-FINAL_CHECK');await assetGateSnapshot(page,'**/r3_background.svg*','R3-gated-sequence',()=>openSequence(page));await openSequence(page); const beforeSequence=structuredClone(state), derivedSequence=deriveSequence(state);
  const draftBeforeState=structuredClone(state); const wrongSequence=derivedSequence.slice(1).concat(derivedSequence[0]);
  await draftSequence(page,wrongSequence.slice(0,3)); await expect(page.locator('.sequence-submit')).toBeDisabled(); assert.deepEqual(state,draftBeforeState);
  await sequenceInput(page,wrongSequence[3]); await submitSequence(page,409); countedMistake(beforeSequence);
  const wrongDraft=await page.locator('.sequence-draft li').allTextContents(); assert.equal(wrongDraft.length,4); for(let index=0;index<4;index++) assert(wrongDraft[index].includes(state.minigames.sequence.devices.find(device => device.device_id===wrongSequence[index]).label));
  await draftSequence(page,[derivedSequence[0],derivedSequence[0],derivedSequence[2],derivedSequence[3]]); const beforeDuplicate=structuredClone(state); await submitSequence(page,422); assert.deepEqual(state,beforeDuplicate);
  await draftSequence(page,derivedSequence.slice(0,2)); const draftSaved=(await control(page,'save')).data.visible_state;
  await control(page,'restore'); assert.deepEqual(publicGame(state),publicGame(draftSaved)); await openSequence(page); await expect(page.locator('.sequence-submit')).toBeDisabled();
  await draftSequence(page,derivedSequence.slice(0,2)); await refresh(page); await openSequence(page); await expect(page.locator('.sequence-submit')).toBeDisabled();
  await draftSequence(page,derivedSequence.slice(0,2)); await move(page,'R2'); await move(page,'R3'); await openSequence(page); await expect(page.locator('.sequence-submit')).toBeDisabled();
  await r3Checkpoint(page,'R3-public-sequence-desktop');await layout(page,1280,'R3-sequence-panel'); await page.screenshot({path:path.join(folder,'R3-sequence-panel.png'),fullPage:true});
  await page.setViewportSize({width:375,height:812}); await r3Checkpoint(page,'R3-public-sequence-mobile');await layout(page,375,'R3-mobile-sequence'); await page.setViewportSize({width:1280,height:900});
  await touchR3SameOwnedSession(service,page);await draftSequence(page,derivedSequence); await submitSequence(page); assert.equal(state.progress.check_done,true); assert.equal(state.device_states.exit,'FINAL_CHECK');
  const miniCompleted=(await control(page,'save')).data.visible_state; await control(page,'reset'); await control(page,'restore'); await refresh(page); assert.deepEqual(publicGame(state),publicGame(miniCompleted));
  checks.push({check:'cross-room-public-sequence-wrong-duplicates-draft-clears-restore-reload-room-and-completed-save',passed:true,derived_sequence:derivedSequence});
  const checkedState = structuredClone(state); await move(page, 'EXIT', 409); assert.deepEqual(state, checkedState);
  await interact(page, 'exit_door'); assert.equal(state.device_states.exit, 'UNLOCKED');await r3Checkpoint(page,'R3-UNLOCKED');
  await select(page,'exit_door');const openMarkers=(await markers(page)).length;
  await http(page,'interact:exit_door',()=>canvasInput(page,'exit_door','interact'));assert.equal(state.device_states.exit,'OPEN');assert.equal(state.status,'playing');
  await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-animation','door_open');await expect(page.locator('.room3-controls [data-scene-action="move"]')).toBeDisabled();for(const zone of await page.locator('.scene-keyboard-hotspot').all())await expect(zone).toBeDisabled();
  const openState=structuredClone(state);await gateAttempt(page,'one-second-door-opening-Canvas',async()=>{const box=await page.locator('.game-canvas-host canvas').boundingBox();await page.mouse.click(box.x+box.width*.5,box.y+box.height*.5);});assert.deepEqual(state,openState);
  await page.locator('.game-canvas-host canvas').screenshot({path:path.join(folder,'R3-door-opening-frame.png')});await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-animation','idle');assert((await markers(page)).slice(openMarkers).includes('door_open'));
  await r3Checkpoint(page,'R3-OPEN');await move(page, 'EXIT'); assert.equal(state.status, 'won');await authoritativeVictory(page);
  await expect(page.getByRole('heading', { name: '逃离成功', exact: true })).toBeVisible();
  const score=structuredClone(state.settlement); assert(score); assert.equal(score.clues_found,10); assert.equal(score.hidden_found,2); assert.equal(score.hint_count,3); assert.equal(score.rating,publicRating(score));
  assert.equal(score.elapsed_seconds,Math.max(0,Math.floor((Date.parse(state.statistics.finished_at)-Date.parse(state.statistics.started_at))/1000)));
  await expect(page.locator('.victory-screen [data-stat="rating"]')).toHaveText(score.rating);
  await expect(page.locator('.victory-screen [data-stat="clues_found"]')).toHaveText('10/10'); await expect(page.locator('.victory-screen [data-stat="hidden_found"]')).toHaveText('2/2');
  const wonSaved=(await control(page,'save')).data.visible_state; await refresh(page); assert.deepEqual(publicGame(state),publicGame(wonSaved));
  const frozenWin=structuredClone(state); await stop(service.backend); start('v3.4-backend-win-restarted',python,service.backendArgs,service.backendEnv); await ready(service.backendURL+'/api/health');
  await menu(page);await http(page,'state',() => page.getByRole('button',{name:'同步进度',exact:true}).click(),200,'/state'); assert.deepEqual(state,frozenWin); assert.deepEqual(state.settlement,score);
  await closeDrawer(page);await http(page,'victory-reset',async()=>{await page.locator('.victory-reset').click();await page.getByRole('dialog').getByRole('button',{name:'确认开始',exact:true}).click();},200,'/reset'); assert.equal(state.statistics.hint_count,0); assert.equal(state.statistics.mistake_count,0); assert.equal(state.statistics.finished_at,null); assert.equal(state.settlement,null); assert(state.save);
  await control(page,'restore'); assert.deepEqual(publicGame(state),publicGame(wonSaved)); assert.deepEqual(state.settlement,score);
  const wonArchive=await appendMoment(page,'通关时刻');
  await expect(page.locator('.save-slot')).toHaveCount(6);
  await page.locator('.save-panel').screenshot({path:path.join(folder,'desktop-three-archive-list.png')});
  await refresh(page);await expect(page.locator('.save-slot')).toHaveCount(6);
  const beforeArchiveRestart=structuredClone(state);await stop(service.backend);
  start('multiple-saves-backend-list-restarted',python,service.backendArgs,service.backendEnv);await ready(service.backendURL+'/api/health');
  await menu(page);await http(page,'state',() => page.getByRole('button',{name:'同步进度',exact:true}).click(),200,'/state');
  assert.deepEqual(state,beforeArchiveRestart);await expect(page.locator('.save-slot')).toHaveCount(6);
  await control(page,'reset');await expect(page.locator('.save-slot')).toHaveCount(6);
  await retrieveMoment(page,earlyArchive);await retrieveMoment(page,partialArchive);await assertSnapshotIdle(page);await retrieveMoment(page,powerArchive);await assertSnapshotIdle(page);await retrieveMoment(page,wonArchive);
  assert.deepEqual(state.settlement,score);await expect(page.locator('.save-slot')).toHaveCount(6);
  checks.push({check:'five-immutable-archives-plus-old-slot-persist-reset-refresh-OSrestart',passed:true,archive_count:5,legacy_count:1});
  checks.push({check:'settlement-authoritative-UTC-score-winfreeze-reset-slot-restore-refresh-OSrestart',passed:true,settlement:score});
  await page.setViewportSize({ width: 375, height: 812 }); await layout(page, 375, 'mobile-victory');await menu(page);
  await page.locator('.save-panel').screenshot({path:path.join(folder,'mobile-three-archive-list.png')});
  await page.locator(`.save-slot[data-save-id="${partialArchive.slot.save_id}"] .save-slot-restore`).click();
  await page.getByRole('dialog').screenshot({path:path.join(folder,'mobile-selected-restore-confirmation.png')});
  await page.getByRole('dialog').getByRole('button',{name:'取消',exact:true}).click();assert.deepEqual(state.settlement,score);
  await closeDrawer(page);await settledRoomTransition(page);await page.screenshot({ path: path.join(folder, 'mobile-victory.png'), fullPage: true }); assert.equal(pageErrors.length, 0);
  checks.push({ check: 'three-room-route-slots-items-save-restore-reload-actual-server-restart-win', passed: true, final_room: state.room.room_id });
  await context.close();
  await touchSmoke(service);await touchR2Smoke(service);await productionStartupMeasurement(service);
  await lightOldVersion('legacy', '2.0.0', 'campus-lab-session-v1');
  await lightOldVersion('v3.1', '3.1.0', 'campus-lab-session-upgrade-v3.1');
  await lightOldVersion('v3.2', '3.2.0', 'campus-lab-session-upgrade-v3.2');
  await lightOldVersion('v3.3', '3.3.0', 'campus-lab-session-upgrade-v3.3');
  }
} catch (error) { issues.push({ check: 'runner', ...diagnosticError(error) }); }
finally {
  await browser?.close();
  for (const child of children) { try { await stop(child); } catch (error) { issues.push({ check: 'owned-process-cleanup', error: briefError(error) }); } }
  try {
    const resolved = fs.realpathSync(temp), temporaryRoot = fs.realpathSync(os.tmpdir());
    assert.equal(path.dirname(resolved).toLowerCase(), temporaryRoot.toLowerCase()); assert(path.basename(resolved).startsWith('campus-visual-v42-browser-')); assert.equal(path.resolve(temp).toLowerCase(), resolved.toLowerCase());
    fs.rmSync(resolved, { recursive: true });
  } catch (error) { issues.push({ check: 'owned-temp-cleanup', error: briefError(error) }); }
  for(const [p,h] of Object.entries(preservedTests))if(sha(fs.readFileSync(path.join(root,p)))!==h)issues.push({check:'old-test-byte-guard',path:p});
  const after = sourceHashes(); if (JSON.stringify(before) !== JSON.stringify(after)) issues.push({ check: 'source-freeze', error: 'Candidate source changed during run' });
  const exitCode = issues.length ? 1 : 0;
  const result = { candidate: candidatePath, candidate_sha256: sha(fs.readFileSync(path.resolve(root, candidatePath))), started, ended: new Date().toISOString(),
    command: [process.execPath, ...process.argv.slice(1)], necessary_scope:only, commands, exit_code: exitCode, provider: 'mock only; no paid model calls', browser: 'Google Chrome headless, isolated contexts',
    source_sha256_before: before, source_sha256_after: after, checks, issues,
    limitations: ['No actual root CMD startup; direct loopback module launches only; partial circuit and archive-list process restart exercised', 'No real model quality or human completion-time claim', 'Old-version light smoke uses owned public-created slots, no historical sensitive DB access'] };
  fs.writeFileSync(path.join(folder, 'run.json'), JSON.stringify(result, null, 2));
  if (issues.length) fs.writeFileSync(path.join(folder, 'failure-summary.json'), JSON.stringify({ issues, service_message_count: serviceOutput.length }, null, 2));
  console.log(JSON.stringify({ evidence: folder, exit_code: exitCode, checks: checks.length, issues }, null, 2)); process.exitCode = exitCode;
}
