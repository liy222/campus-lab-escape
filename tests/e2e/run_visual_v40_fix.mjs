// Narrow v4.0 fixed-candidate R1 visual recheck; original complete runner remains sealed.
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
const candidatePath = process.argv[2];
assert(candidatePath, 'Pass a frozen Main candidate JSON explicitly');
const candidate = JSON.parse(fs.readFileSync(path.resolve(root, candidatePath), 'utf8').replace(/^\uFEFF/, ''));
const folder = path.join(root, 'evidence/upgrade/v4.0/qa', new Date().toISOString().replace(/[-:.]/g, '') + '-browser-fix');
fs.mkdirSync(folder, { recursive: true });
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'campus-visual-v40-browser-'));
const python = 'C:\\Users\\liyh\\.conda\\envs\\1\\python.exe';
const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const children = [], checks = [], issues = [], commands = [], serviceOutput = [];
const started = new Date().toISOString();
let browser, state;
function briefError(error) { return String(error.message || error).split(/\r?\n/)[0].slice(0,240); }
function sha(bytes) { return crypto.createHash('sha256').update(bytes).digest('hex'); }
function sourceHashes() {
  return Object.fromEntries(Object.keys(candidate.source_sha256).map(relative => [relative, sha(fs.readFileSync(path.join(root, relative)))]));
}
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
  const waiting = page.waitForResponse(response => new URL(response.url()).pathname.endsWith(suffix) && response.request().method() === (suffix === '/state' ? 'GET' : 'POST'));
  await operation(); const response = await waiting, body = await response.json();
  record(label, body, response.status()); assert.equal(response.status(), expected, label + ' HTTP result');
  return body;
}

function visual() { return state?.level_version === '3.4.0' && state?.room.room_id === 'R1'; }
async function closeDrawer(page) {
  const backdrop=page.getByRole('button',{name:'关闭面板',exact:true});
  if(await backdrop.isVisible()) await backdrop.click({position:{x:5,y:5}});
}
async function menu(page) {
  if(visual() && !await page.locator('.save-panel').isVisible()) {
    await closeDrawer(page); await page.getByRole('button',{name:'游戏菜单',exact:true}).click();
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
async function canvasInput(page,id,tool='object',keyboard=false) {
  const host=page.locator('.game-canvas-host');await expect(host).toHaveAttribute('data-assets-ready','true');
  await expect(host.locator('canvas')).toHaveCount(1);
  const hotspot=host.locator(`.scene-keyboard-hotspot[data-object-id="${id}"][data-scene-action="${tool}"]`);
  await expect(hotspot).toHaveCount(1);await expect(hotspot).toBeEnabled();
  if(keyboard) { await hotspot.focus();await hotspot.press('Enter'); }
  else {
    const values=(await hotspot.getAttribute('data-bounds')).split(',').map(Number), box=await host.locator('canvas').boundingBox();
    assert(box);const x=box.x+(values[0]+values[2]/2)*box.width/1600,y=box.y+(values[1]+values[3]/2)*box.height/900;
    const hit=await page.evaluate(({x,y})=>document.elementFromPoint(x,y)?.tagName,{x,y});assert.equal(hit,'CANVAS','Mouse input must hit actual canvas');
    await page.mouse.click(x,y);
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
    if(action.tool==='take'||id==='r1_cabinet') await page.locator('.game-canvas-host canvas').screenshot({path:path.join(folder,id+'-before-'+action.tool+'.png')});
    const body=await http(page,action.tool+':'+id,()=>page.locator(`.closeup-actions [data-scene-action="${action.tool}"][data-target-id="${id}"]`).click());
    if(action.tool==='take'||id==='r1_cabinet') {
      await expect.poll(async()=> (await markers(page)).includes(action.tool)).toBe(true);
      await page.locator('.game-canvas-host canvas').screenshot({path:path.join(folder,id+'-receipt-frame-'+action.tool+'.png')});
      await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-animation','idle');
      await page.locator('.game-canvas-host canvas').screenshot({path:path.join(folder,id+'-settled-'+action.tool+'.png')});
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
  await select(page, 'r2_monitor'); await page.getByRole('button', { name: /^互动$/ }).click();
  await page.getByLabel('用户名', { exact: true }).fill(username); await page.getByLabel('密码', { exact: true }).fill(password);
  return http(page, 'submit_login', () => page.locator('.login-form').getByRole('button', { name: '提交登录', exact: true }).click(), expected);
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
  if(visual()) {await select(page,'r1_door');return http(page,'move:'+destination,()=>page.locator('.closeup-actions [data-scene-action="move"]').click(),expected);}
  return http(page,'move:'+destination,()=>page.locator('.exit-button').filter({hasText:exit.name}).click(),expected);
}
async function control(page, operation) {
  await menu(page);
  return http(page, operation, async () => {
    await page.getByRole('button', { name: operation === 'save' ? '保存进度' : operation === 'restore' ? '恢复存档' : '重新开始', exact: true }).click();
    if (operation !== 'save') await page.getByRole('dialog').getByRole('button', { name: operation === 'restore' ? '确认恢复' : '确认开始', exact: true }).click();
  }, 200, '/' + operation);
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
  const before=structuredClone(state),row=page.locator(`.save-slot[data-save-id="${moment.slot.save_id}"]`);
  await expect(row).toBeVisible();await row.locator('.save-slot-restore').click();
  const dialog=page.getByRole('dialog');await expect(dialog.getByRole('heading',{name:'读取指定存档？',exact:true})).toBeVisible();
  if(checkCancel) {
    await dialog.screenshot({path:path.join(folder,'desktop-selected-restore-confirmation.png')});
    await dialog.getByRole('button',{name:'取消',exact:true}).click();assert.deepEqual(state,before);
    await row.locator('.save-slot-restore').click();
  }
  const body=await http(page,'archive-selected-restore',() => dialog.getByRole('button',{name:'读取此存档',exact:true}).click(),200,`/saves/${moment.slot.save_id}/restore`);
  assert.equal(body.data.slot.save_id,moment.slot.save_id);assert.equal(body.data.replayed,false);
  assert.deepEqual(publicGame(state),publicGame(moment.state));assert.equal(state.revision,before.revision+1);assert.notEqual(state.generation,before.generation);
  await menu(page);await expect(row).toBeVisible();
  checks.push({check:'user-selected-moment-restores-game-statistics-new-generation',name:moment.slot.name,cancel_checked:checkCancel,passed:true});
}
async function refresh(page) {
  await page.reload({ waitUntil: 'networkidle' });
  await http(page, 'state', () => page.locator('.welcome-buttons').getByRole('button', { name: '继续当前游戏', exact: true }).click(), 200, '/state');
}
async function layout(page, width, label) {
  if(visual()) {await closeDrawer(page);await expect(page.locator('.game-canvas-host canvas')).toHaveCount(1);await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-assets-ready','true');await canvasPixels(page,label);}
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
async function openCircuit(page) { await select(page,'r2_powerbox'); await page.getByRole('button',{name:/^互动$/}).click(); await expect(page.locator('.circuit-submit')).toBeVisible(); }
async function rotate(page, id) { return http(page,'rotate:'+id,() => page.locator(`.circuit-cell[data-module-id="${id}"]`).click()); }
async function submitCircuit(page, expected=200) { return http(page,'submit_circuit',() => page.locator('.circuit-submit').click(),expected); }
async function openSequence(page) { await select(page,'r3_panel'); await page.getByRole('button',{name:/^互动$/}).click(); await expect(page.locator('.sequence-submit')).toBeVisible(); }
async function draftSequence(page, ids) { if (await page.locator('.sequence-clear').isEnabled()) await page.locator('.sequence-clear').click(); for (const id of ids) await page.locator(`.sequence-device[data-device-id="${id}"]`).click(); }
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
  await trackMarkers(page);await select(page,'r1_clock',true);await canvasPixels(page,'R1-clock-closeup');await page.locator('.visual-room').screenshot({path:path.join(folder,'R1-clock-closeup.png')});
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
  const previous=structuredClone(state), markerCount=(await markers(page)).length;
  await page.locator('#code-r1_cabinet').fill('0000');await http(page,'R1-wrong-lock-code',()=>page.locator('.code-form').getByRole('button',{name:'提交',exact:true}).click(),409);
  countedMistake(previous);assert.equal(state.device_states.cabinet,'LOCKED');assert.equal((await markers(page)).length,markerCount);
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
  state = undefined; await page.goto(service.frontendURL, { waitUntil: 'networkidle' });
  await page.evaluate(() => sessionStorage.setItem('campus-lab-session-upgrade-v3.4', 'qa-preserve-v34'));
  await http(page, 'create', () => page.getByRole('button', { name: '开始新游戏 →', exact: true }).click(), 201, '/api/sessions');
  assert.equal(state.level_version, level); if (version === 'v3.2' || version === 'v3.3') assert(state.puzzle_states); else assert.equal(state.puzzle_states, undefined); if (version === 'v3.3') assert(state.minigames); else assert.equal(state.minigames, undefined); assert.equal(state.statistics,undefined); assert.equal(state.settlement,undefined);
  assert(await page.evaluate(key => !!sessionStorage.getItem(key), key));
  assert.equal(await page.evaluate(() => sessionStorage.getItem('campus-lab-session-upgrade-v3.4')), 'qa-preserve-v34');
  await observe(page, 'r1_cabinet'); const saved = (await control(page, 'save')).data.visible_state;
  await control(page, 'reset'); await control(page, 'restore'); assert.deepEqual(publicGame(state), publicGame(saved));
  checks.push({ check: 'light-old-mode-selection-save-slot-and-namespace', mode: version, level, passed: true }); await context.close();
}
async function readable(page,label) {
  const actual=await page.evaluate(()=>{
    const rect=element=>{const r=element.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};};
    const overlaps=(a,b)=>Math.min(a.right,b.right)>Math.max(a.left,b.left)&&Math.min(a.bottom,b.bottom)>Math.max(a.top,b.top);
    const feedback=[...document.querySelectorAll('.feedback p')].filter(element=>element.getClientRects().length).map(rect);
    const content=[...document.querySelectorAll('.game-hud button,.closeup-reading,.closeup-description,.closeup-controls button,.closeup-controls input,.closeup-controls label')].filter(element=>element.getClientRects().length).map(rect);
    return {feedback_count:feedback.length,content_count:content.length,feedback_overlaps:feedback.flatMap(a=>content.filter(b=>overlaps(a,b))).length,outside_horizontal:content.filter(r=>r.left<0||r.right>innerWidth).length,controls_below_viewport:[...document.querySelectorAll('.closeup-controls button,.closeup-controls input')].filter(element=>element.getClientRects().length).map(rect).filter(r=>r.top>=innerHeight).length};
  });
  assert.equal(actual.feedback_overlaps,0,'Feedback obscures readable clue/controls');assert.equal(actual.outside_horizontal,0);
  checks.push({check:'fixed-feedback-does-not-cover-reading-return-input',label,...actual,passed:true});
  await page.screenshot({path:path.join(folder,label+'.png'),fullPage:true});await canvasPixels(page,label);
}
async function widths(page,id,label) {
  for(const width of [1920,1280]) {
    await page.setViewportSize({width,height:width===1920?1080:900});
    await observe(page,id);await readable(page,label+'-'+width);
  }
}
try {
  assert(fs.existsSync(chromePath));const service=await pair('v3.4');
  browser=await chromium.launch({headless:true,executablePath:chromePath});
  const context=await browser.newContext({viewport:{width:1920,height:1080}}),page=await context.newPage(),pageErrors=[];
  page.on('pageerror',()=>pageErrors.push('uncaught browser exception'));
  await page.goto(service.frontendURL,{waitUntil:'networkidle'});
  await http(page,'create',()=>page.getByRole('button',{name:'开始新游戏 →',exact:true}).click(),201,'/api/sessions');await trackMarkers(page);
  const svgArgs=['-B','-X','utf8',path.join(root,'evidence/upgrade/v4.0/qa/svg_check.py')];
  const svg=spawnSync(python,svgArgs,{cwd:root,encoding:'utf8',windowsHide:true});commands.push({label:'fixed-public-SVG-clock-lock-geometry',executable:python,arguments:svgArgs,cwd:root,exit_code:svg.status,stdout:svg.stdout.trim(),stderr:svg.stderr.trim()});assert.equal(svg.status,0);checks.push({check:'public-SVG-clock-21-17-four-lock-wheels',...JSON.parse(svg.stdout)});
  await widths(page,'r1_clock','fixed-clock-reading');await widths(page,'r1_record','fixed-record-reading');await widths(page,'r1_plaque','fixed-plaque-reading');
  await observe(page,'sample_slide');await interact(page,'sample_slide');await use(page,'sample_slide','r1_microscope');assert.equal(state.puzzle_states.microscope,'SLIDE_PLACED');
  await widths(page,'r1_microscope','fixed-eyepiece-reading');
  await widths(page,'r1_cabinet','fixed-four-wheel-lock');
  for(const width of [1920,1280]) {
    await page.setViewportSize({width,height:width===1920?1080:900});await select(page,'r1_cabinet');
    const before=structuredClone(state);await page.locator('#code-r1_cabinet').fill('0000');await http(page,'fixed-visible-wrong-code-'+width,()=>page.locator('.code-form').getByRole('button',{name:'提交',exact:true}).click(),409);countedMistake(before);await readable(page,'fixed-wrong-code-'+width);
  }
  await page.setViewportSize({width:1280,height:900});await code(page,'r1_cabinet','4217');assert.equal(state.device_states.cabinet,'CODE_ACCEPTED');await readable(page,'fixed-accepted-closed');
  await interact(page,'r1_cabinet');assert.equal(state.device_states.cabinet,'OPEN');await readable(page,'fixed-cabinet-open');
  await observe(page,'r1_fuse');await interact(page,'r1_fuse');await widths(page,'r1_photo','fixed-photo-reading');
  const saved=(await control(page,'save')).data.visible_state;await control(page,'reset');await control(page,'restore');assert.deepEqual(publicGame(state),publicGame(saved));
  await closeDrawer(page);await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-animation','idle');await widths(page,'r1_photo','fixed-restored-photo-reading');
  assert.equal(pageErrors.length,0);checks.push({check:'narrow-fixed-R1-css-clock-lock-and-restored-snapshot',passed:true});await context.close();
} catch (error) { issues.push({ check: 'runner', error: briefError(error) }); }
finally {
  await browser?.close();
  for (const child of children) { try { await stop(child); } catch (error) { issues.push({ check: 'owned-process-cleanup', error: briefError(error) }); } }
  try {
    const resolved = fs.realpathSync(temp), temporaryRoot = fs.realpathSync(os.tmpdir());
    assert.equal(path.dirname(resolved).toLowerCase(), temporaryRoot.toLowerCase()); assert(path.basename(resolved).startsWith('campus-visual-v40-browser-')); assert.equal(path.resolve(temp).toLowerCase(), resolved.toLowerCase());
    fs.rmSync(resolved, { recursive: true });
  } catch (error) { issues.push({ check: 'owned-temp-cleanup', error: briefError(error) }); }
  const after = sourceHashes(); if (JSON.stringify(before) !== JSON.stringify(after)) issues.push({ check: 'source-freeze', error: 'Candidate source changed during run' });
  const exitCode = issues.length ? 1 : 0;
  const result = { candidate: candidatePath, candidate_sha256: sha(fs.readFileSync(path.resolve(root, candidatePath))), started, ended: new Date().toISOString(),
    command: [process.execPath, ...process.argv.slice(1)], commands, exit_code: exitCode, provider: 'mock only; no paid model calls', browser: 'Google Chrome headless, isolated contexts',
    source_sha256_before: before, source_sha256_after: after, checks, issues,
    limitations: ['Narrow R1 CSS/clock/four-wheel-lock and restored snapshot recheck; complete route/API/restart reused from prior frozen-candidate epoch', 'No real model quality or human completion-time claim', 'Old-version light smoke uses owned public-created slots, no historical sensitive DB access'] };
  fs.writeFileSync(path.join(folder, 'run.json'), JSON.stringify(result, null, 2));
  if (issues.length) fs.writeFileSync(path.join(folder, 'failure-summary.json'), JSON.stringify({ issues, service_message_count: serviceOutput.length }, null, 2));
  console.log(JSON.stringify({ evidence: folder, exit_code: exitCode, checks: checks.length, issues }, null, 2)); process.exitCode = exitCode;
}
