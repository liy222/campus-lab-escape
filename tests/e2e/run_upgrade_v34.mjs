// Independent v3.4 Chrome acceptance: compact stage/refusal evidence, owned DBs.
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
const folder = path.join(root, 'evidence/upgrade/v3.4/qa', new Date().toISOString().replace(/[-:.]/g, '') + '-browser');
fs.mkdirSync(folder, { recursive: true });
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'campus-v34-browser-'));
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
async function select(page, id) {
  const object = state.objects.find(object => object.object_id === id); assert(object, 'Object must be currently visible: ' + id);
  const escaped = object.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  await page.locator('.object-grid').getByRole('button', { name: new RegExp(escaped) }).click();
}
async function observe(page, id) {
  await select(page, id); return http(page, 'inspect:' + id, () => page.getByRole('button', { name: /^观察$/ }).click());
}
async function interact(page, id) {
  await select(page, id); return http(page, 'interact:' + id, () => page.getByRole('button', { name: /^互动$/ }).click());
}
async function code(page, id, value, expected = 200) {
  await select(page, id); await page.getByRole('button', { name: /^互动$/ }).click();
  await page.getByLabel('输入你推理出的数字', { exact: true }).fill(value);
  return http(page, 'code:' + id, () => page.locator('.code-form').getByRole('button', { name: '提交', exact: true }).click(), expected);
}
async function login(page, username, password, expected = 200) {
  await select(page, 'r2_monitor'); await page.getByRole('button', { name: /^互动$/ }).click();
  await page.getByLabel('用户名', { exact: true }).fill(username); await page.getByLabel('密码', { exact: true }).fill(password);
  return http(page, 'submit_login', () => page.locator('.login-form').getByRole('button', { name: '提交登录', exact: true }).click(), expected);
}
async function use(page, itemId, targetId, expected = 200) {
  const item = state.inventory.find(item => item.item_id === itemId); assert(item, 'Owned item: ' + itemId);
  const button = page.locator('.inventory-item').filter({ hasText: item.name }).getByRole('button', { name: /^(选择物品|取消选择)$/ });
  if (await button.getAttribute('aria-pressed') !== 'true') await button.click();
  await select(page, targetId); return http(page, 'use:' + itemId + ':' + targetId, () => page.getByRole('button', { name: /^使用物品/ }).click(), expected);
}
async function move(page, destination, expected = 200) {
  const exit = state.exits.find(exit => exit.destination_id === destination); assert(exit, 'Visible passage: ' + destination);
  return http(page, 'move:' + destination, () => page.locator('.exit-button').filter({ hasText: exit.name }).click(), expected);
}
async function control(page, operation) {
  return http(page, operation, async () => {
    await page.getByRole('button', { name: operation === 'save' ? '保存进度' : operation === 'restore' ? '恢复存档' : '重新开始', exact: true }).click();
    if (operation !== 'save') await page.getByRole('dialog').getByRole('button', { name: operation === 'restore' ? '确认恢复' : '确认开始', exact: true }).click();
  }, 200, '/' + operation);
}
async function refresh(page) {
  await page.reload({ waitUntil: 'networkidle' });
  await http(page, 'state', () => page.locator('.welcome-buttons').getByRole('button', { name: '继续当前游戏', exact: true }).click(), 200, '/state');
}
async function layout(page, width, label) {
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
try {
  assert(fs.existsSync(chromePath));
  const service = await pair('v3.4');
  browser = await chromium.launch({ headless: true, executablePath: chromePath });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } }), page = await context.newPage();
  const pageErrors = []; page.on('pageerror', () => pageErrors.push('uncaught browser exception'));
  await page.goto(service.frontendURL, { waitUntil: 'networkidle' });
  await page.evaluate(() => { sessionStorage.setItem('campus-lab-session-v1', 'qa-preserve-legacy'); sessionStorage.setItem('campus-lab-session-upgrade-v3.1', 'qa-preserve-v31'); sessionStorage.setItem('campus-lab-session-upgrade-v3.2', 'qa-preserve-v32'); sessionStorage.setItem('campus-lab-session-upgrade-v3.3', 'qa-preserve-v33'); });
  await http(page, 'create', () => page.getByRole('button', { name: '开始新游戏 →', exact: true }).click(), 201, '/api/sessions');
  assert.equal(state.level_version, '3.4.0'); assert.equal(state.schema_version, '1.4.0');
  assert(await page.evaluate(() => !!sessionStorage.getItem('campus-lab-session-upgrade-v3.4')));
  assert.equal(await page.evaluate(() => sessionStorage.getItem('campus-lab-session-v1')), 'qa-preserve-legacy');
  assert.equal(await page.evaluate(() => sessionStorage.getItem('campus-lab-session-upgrade-v3.1')), 'qa-preserve-v31');
  assert.equal(await page.evaluate(() => sessionStorage.getItem('campus-lab-session-upgrade-v3.2')), 'qa-preserve-v32');
  assert.equal(await page.evaluate(() => sessionStorage.getItem('campus-lab-session-upgrade-v3.3')), 'qa-preserve-v33');
  assert.deepEqual(state.minigames, { circuit: null, sequence: null });
  assert.equal(state.statistics.clues_total,10); assert.equal(state.statistics.hidden_total,2); assert.equal(state.statistics.hint_count,0); assert.equal(state.settlement,null); await hint(page,3,false);
  await layout(page, 1280, 'R1-graybox'); await page.screenshot({ path: path.join(folder, 'R1-graybox.png'), fullPage: true });
    await page.setViewportSize({ width: 1280, height: 900 });
  // Prove early exploration, before obtaining any item or powering/login.
  await observe(page, 'r1_door'); await interact(page, 'r1_door'); await move(page, 'R2');
  await observe(page, 'r2_door'); await interact(page, 'r2_door'); await move(page, 'R3'); await observe(page, 'r3_legend');
  assert.equal(state.inventory.length, 0); assert.equal(state.device_states.computer, 'OFF');
  await layout(page, 1280, 'R3-early-graybox'); await page.screenshot({ path: path.join(folder, 'R3-graybox.png'), fullPage: true });
    await page.setViewportSize({ width: 1280, height: 900 });
  await move(page, 'R2'); await move(page, 'R1');
  await observe(page, 'r1_clock'); await observe(page, 'r1_record'); await observe(page, 'r1_plaque');
  const levelAnswers=[]; for(const level of [1,2,3]) levelAnswers.push(await hint(page,level)); assert.equal(new Set(levelAnswers).size,3); await expect(page.locator('.run-statistics [data-stat="hint_count"]')).toHaveText('3');
  await observe(page, 'r1_microscope'); await observe(page, 'sample_slide'); await interact(page, 'sample_slide');
  await use(page, 'sample_slide', 'r1_microscope'); assert.equal(state.puzzle_states.microscope, 'SLIDE_PLACED');
  await observe(page, 'r1_microscope'); assert(state.clues.some(clue => clue.object_id === 'r1_microscope' && clue.text.includes('42')));
  await observe(page, 'r1_cabinet'); await code(page, 'r1_cabinet', '4217'); await interact(page, 'r1_cabinet');
  await observe(page, 'r1_symbols'); await observe(page, 'r1_fuse'); await interact(page, 'r1_fuse'); await observe(page,'r1_photo'); assert.equal(state.statistics.hidden_found,1); await move(page, 'R2');
  await observe(page, 'r2_maintenance'); await observe(page, 'r2_powerbox');
  await interact(page, 'r2_powerbox'); await interact(page, 'r2_powerbox'); await use(page, 'fuse', 'r2_powerbox');
  assert.equal(state.progress.power_on, false); assert.equal(state.minigames.circuit.status,'editing');
  await openCircuit(page); assert.equal(await page.locator('.circuit-cell').count(),9);
  const disconnected = structuredClone(state); assert.equal(connected(state.minigames.circuit),false);
  await submitCircuit(page,409); countedMistake(disconnected);
  const initialModule = state.minigames.circuit.modules[0]; await rotate(page,initialModule.module_id);
  const partial = structuredClone(state); assert.equal(state.device_states.powerbox,'FUSE_INSTALLED'); assert.equal(state.progress.power_on,false);
  const partialSaved = (await control(page,'save')).data.visible_state; await control(page,'reset'); await control(page,'restore'); assert.deepEqual(publicGame(state),publicGame(partialSaved));
  await refresh(page); assert.deepEqual(publicGame(state),publicGame(partial));
  const beforeBoardRestart = structuredClone(state); await stop(service.backend);
  start('v3.4-backend-partial-board-restarted',python,service.backendArgs,service.backendEnv); await ready(service.backendURL+'/api/health');
  await http(page,'state',() => page.getByRole('button',{name:'同步进度',exact:true}).click(),200,'/state'); assert.deepEqual(state,beforeBoardRestart);
  await openCircuit(page); await layout(page,1280,'R2-partial-circuit'); await page.screenshot({path:path.join(folder,'R2-partial-circuit.png'),fullPage:true});
    await page.setViewportSize({width:1280,height:900});
  const solution = deriveCircuit(state.minigames.circuit), alternate = {...solution};
  const straight = state.minigames.circuit.modules.find(module => module.shape==='I'); alternate[straight.module_id]=(alternate[straight.module_id]+2)%4;
  assert(connected(state.minigames.circuit,solution)); assert(connected(state.minigames.circuit,alternate)); assert.notDeepEqual(solution,alternate);
  for (const module of [...state.minigames.circuit.modules]) for(let turn=0;turn<(alternate[module.module_id]-module.rotation+4)%4;turn++) await rotate(page,module.module_id);
  await submitCircuit(page); assert.equal(state.device_states.powerbox,'CIRCUIT_READY'); assert.equal(state.progress.power_on,false); assert.equal(state.minigames.circuit.status,'completed');
  await expect(page.locator('.circuit-cell').first()).toBeDisabled();
  checks.push({check:'partial-circuit-save-restore-refresh-OSrestart-and-alternate-public-connection',passed:true,public_derived_solution:solution,alternate});
  await interact(page,'r2_powerbox'); await observe(page,'r2_service_label'); assert.equal(state.statistics.hidden_found,2);
  await observe(page, 'r2_monitor'); await interact(page, 'r2_monitor'); await interact(page, 'r2_monitor');
  assert.equal(state.device_states.computer, 'LOGIN_LOCKED'); const saved = (await control(page, 'save')).data.visible_state;
  const beforeWrong = structuredClone(state); await login(page, 'LAB-41', '2117', 409); countedMistake(beforeWrong);
  await login(page, 'LAB-42', '2117'); assert.equal(state.device_states.computer, 'UNLOCKED');
  await control(page, 'restore'); assert.deepEqual(publicGame(state), publicGame(saved));
  await refresh(page); assert.equal(state.device_states.computer, 'LOGIN_LOCKED');
  const beforeRestart = structuredClone(state); await stop(service.backend);
  start('v3.4-backend-restarted', python, service.backendArgs, service.backendEnv); await ready(service.backendURL + '/api/health');
  await http(page, 'state', () => page.getByRole('button', { name: '同步进度', exact: true }).click(), 200, '/state');
  assert.deepEqual(state, beforeRestart);
  await select(page, 'r2_monitor'); await page.getByRole('button', { name: /^互动$/ }).click();
  await expect(page.getByLabel('用户名', { exact: true })).toHaveValue(''); await expect(page.getByLabel('密码', { exact: true })).toHaveValue('');
  await layout(page, 1280, 'R2-login-graybox'); await page.screenshot({ path: path.join(folder, 'R2-graybox.png'), fullPage: true });
    await page.setViewportSize({ width: 1280, height: 900 });
  await login(page, 'LAB-42', '2117'); await interact(page, 'r2_monitor');
  await observe(page, 'research_strip'); await interact(page, 'research_strip'); await observe(page, 'access_card'); await interact(page, 'access_card');
  await move(page, 'R3'); await observe(page, 'r3_panel'); await observe(page, 'exit_door');
  await use(page, 'research_strip', 'r3_panel'); assert.equal(state.puzzle_states.panel, 'STRIP_INSERTED');
  await use(page, 'access_card', 'exit_door'); assert.equal(state.device_states.exit, 'CARD_ACCEPTED');
  const cardState = structuredClone(state); await move(page, 'EXIT', 409); assert.deepEqual(state, cardState);
  await interact(page,'exit_door'); await openSequence(page); const beforeSequence=structuredClone(state), derivedSequence=deriveSequence(state);
  const draftBeforeState=structuredClone(state); const wrongSequence=derivedSequence.slice(1).concat(derivedSequence[0]);
  await draftSequence(page,wrongSequence.slice(0,3)); await expect(page.locator('.sequence-submit')).toBeDisabled(); assert.deepEqual(state,draftBeforeState);
  await page.locator(`.sequence-device[data-device-id="${wrongSequence[3]}"]`).click(); await submitSequence(page,409); countedMistake(beforeSequence);
  const wrongDraft=await page.locator('.sequence-draft li').allTextContents(); assert.equal(wrongDraft.length,4); for(let index=0;index<4;index++) assert(wrongDraft[index].includes(state.minigames.sequence.devices.find(device => device.device_id===wrongSequence[index]).label));
  await draftSequence(page,[derivedSequence[0],derivedSequence[0],derivedSequence[2],derivedSequence[3]]); const beforeDuplicate=structuredClone(state); await submitSequence(page,422); assert.deepEqual(state,beforeDuplicate);
  await draftSequence(page,derivedSequence.slice(0,2)); const draftSaved=(await control(page,'save')).data.visible_state;
  await control(page,'restore'); assert.deepEqual(publicGame(state),publicGame(draftSaved)); await openSequence(page); await expect(page.locator('.sequence-submit')).toBeDisabled();
  await draftSequence(page,derivedSequence.slice(0,2)); await refresh(page); await openSequence(page); await expect(page.locator('.sequence-submit')).toBeDisabled();
  await draftSequence(page,derivedSequence.slice(0,2)); await move(page,'R2'); await move(page,'R3'); await openSequence(page); await expect(page.locator('.sequence-submit')).toBeDisabled();
  await layout(page,1280,'R3-sequence-panel'); await page.screenshot({path:path.join(folder,'R3-sequence-panel.png'),fullPage:true});
    await page.setViewportSize({width:1280,height:900});
  await draftSequence(page,derivedSequence); await submitSequence(page); assert.equal(state.progress.check_done,true); assert.equal(state.device_states.exit,'FINAL_CHECK');
  const miniCompleted=(await control(page,'save')).data.visible_state; await control(page,'reset'); await control(page,'restore'); await refresh(page); assert.deepEqual(publicGame(state),publicGame(miniCompleted));
  checks.push({check:'cross-room-public-sequence-wrong-duplicates-draft-clears-restore-reload-room-and-completed-save',passed:true,derived_sequence:derivedSequence});
  const checkedState = structuredClone(state); await move(page, 'EXIT', 409); assert.deepEqual(state, checkedState);
  await interact(page, 'exit_door'); assert.equal(state.device_states.exit, 'UNLOCKED');
  await interact(page, 'exit_door'); await move(page, 'EXIT'); assert.equal(state.status, 'won');
  await expect(page.getByRole('heading', { name: '成功逃离实验室', exact: true })).toBeVisible();
  const score=structuredClone(state.settlement); assert(score); assert.equal(score.clues_found,10); assert.equal(score.hidden_found,2); assert.equal(score.hint_count,3); assert.equal(score.rating,publicRating(score));
  assert.equal(score.elapsed_seconds,Math.max(0,Math.floor((Date.parse(state.statistics.finished_at)-Date.parse(state.statistics.started_at))/1000)));
  await expect(page.locator('.settlement-panel [data-stat="rating"]')).toHaveText(score.rating);
  await expect(page.locator('.settlement-panel [data-stat="clues_found"]')).toHaveText('10/10'); await expect(page.locator('.settlement-panel [data-stat="hidden_found"]')).toHaveText('2/2');
  const wonSaved=(await control(page,'save')).data.visible_state; await refresh(page); assert.deepEqual(publicGame(state),publicGame(wonSaved));
  const frozenWin=structuredClone(state); await stop(service.backend); start('v3.4-backend-win-restarted',python,service.backendArgs,service.backendEnv); await ready(service.backendURL+'/api/health');
  await http(page,'state',() => page.getByRole('button',{name:'同步进度',exact:true}).click(),200,'/state'); assert.deepEqual(state,frozenWin); assert.deepEqual(state.settlement,score);
  await control(page,'reset'); assert.equal(state.statistics.hint_count,0); assert.equal(state.statistics.mistake_count,0); assert.equal(state.statistics.finished_at,null); assert.equal(state.settlement,null); assert(state.save);
  await control(page,'restore'); assert.deepEqual(publicGame(state),publicGame(wonSaved)); assert.deepEqual(state.settlement,score);
  checks.push({check:'settlement-authoritative-UTC-score-winfreeze-reset-slot-restore-refresh-OSrestart',passed:true,settlement:score});

   assert.equal(pageErrors.length, 0);
  checks.push({ check: 'three-room-route-slots-items-save-restore-reload-actual-server-restart-win', passed: true, final_room: state.room.room_id });
  await context.close();
  await lightOldVersion('legacy', '2.0.0', 'campus-lab-session-v1');
  await lightOldVersion('v3.1', '3.1.0', 'campus-lab-session-upgrade-v3.1');
  await lightOldVersion('v3.2', '3.2.0', 'campus-lab-session-upgrade-v3.2');
  await lightOldVersion('v3.3', '3.3.0', 'campus-lab-session-upgrade-v3.3');
} catch (error) { issues.push({ check: 'runner', error: briefError(error) }); }
finally {
  await browser?.close();
  for (const child of children) { try { await stop(child); } catch (error) { issues.push({ check: 'owned-process-cleanup', error: briefError(error) }); } }
  try {
    const resolved = fs.realpathSync(temp), temporaryRoot = fs.realpathSync(os.tmpdir());
    assert.equal(path.dirname(resolved).toLowerCase(), temporaryRoot.toLowerCase()); assert(path.basename(resolved).startsWith('campus-v34-browser-')); assert.equal(path.resolve(temp).toLowerCase(), resolved.toLowerCase());
    fs.rmSync(resolved, { recursive: true });
  } catch (error) { issues.push({ check: 'owned-temp-cleanup', error: briefError(error) }); }
  const after = sourceHashes(); if (JSON.stringify(before) !== JSON.stringify(after)) issues.push({ check: 'source-freeze', error: 'Candidate source changed during run' });
  const exitCode = issues.length ? 1 : 0;
  const result = { candidate: candidatePath, candidate_sha256: sha(fs.readFileSync(path.resolve(root, candidatePath))), started, ended: new Date().toISOString(),
    command: [process.execPath, ...process.argv.slice(1)], commands, exit_code: exitCode, provider: 'mock only; no paid model calls', browser: 'Google Chrome headless, isolated contexts',
    source_sha256_before: before, source_sha256_after: after, checks, issues,
    limitations: ['No actual root CMD startup; direct loopback module launches only; partial circuit OS restart exercised', 'No real model quality or human completion-time claim', 'Old-version light smoke uses owned public-created slots, no historical sensitive DB access'] };
  fs.writeFileSync(path.join(folder, 'run.json'), JSON.stringify(result, null, 2));
  if (issues.length) fs.writeFileSync(path.join(folder, 'failure-summary.json'), JSON.stringify({ issues, service_message_count: serviceOutput.length }, null, 2));
  console.log(JSON.stringify({ evidence: folder, exit_code: exitCode, checks: checks.length, issues }, null, 2)); process.exitCode = exitCode;
}
