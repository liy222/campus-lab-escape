// Independent browser QA against a frozen local candidate. Never records tokens/headers.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const requireFrontend = createRequire(path.join(root, 'frontend/package.json'));
const { chromium, expect } = requireFrontend('@playwright/test');
const candidate = process.argv[2];
const suite = process.env.QA_SUITE || 'r1';
if (!candidate) throw new Error('Explicit Main-frozen candidate ID is required');
const folder = path.join(root, 'evidence/qa', new Date().toISOString().replace(/[-:.]/g, '') + '-' + suite + '-browser');
fs.mkdirSync(folder, { recursive: true });
const python = 'C:\\Users\\liyh\\.conda\\envs\\1\\python.exe';
const browserPath = process.env.QA_BROWSER_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const backendPort = Number(process.env.QA_BACKEND_PORT || 18108);
const frontendPort = Number(process.env.QA_FRONTEND_PORT || 15108);
const frontendURL = `http://127.0.0.1:${frontendPort}`;
const backendURL = `http://127.0.0.1:${backendPort}`;
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'campus-qa-browser-'));
const children = [], checks = [], issues = [], serverLogs = [];
let browser;
function sourceHashes() {
  const result = {};
  function walk(relative) {
    if (relative.replaceAll('\\', '/').startsWith('backend/app/ai')) return;
    const absolute = path.join(root, relative);
    if (!fs.existsSync(absolute)) return;
    if (fs.statSync(absolute).isDirectory()) {
      for (const entry of fs.readdirSync(absolute)) if (!['node_modules', '__pycache__'].includes(entry)) walk(path.join(relative, entry));
    } else if (/\.(py|json|tsx?|js|css|html|mjs|txt)$/.test(relative)) result[relative.replaceAll('\\', '/')] = crypto.createHash('sha256').update(fs.readFileSync(absolute)).digest('hex');
  }
  for (const entry of ['backend/app', 'backend/requirements.lock.txt', 'frontend/src', 'frontend/dist', 'frontend/index.html', 'frontend/vite.config.ts', 'frontend/package-lock.json', 'contracts', 'tests', 'docs/SPEC.md', 'docs/level_design.md']) walk(entry);
  return result;
}
function gitRead(...args) {
  const result = spawnSync('git', ['-c', `safe.directory=${root.replaceAll('\\', '/')}`, ...args], { cwd: root, encoding: 'utf8', windowsHide: true });
  return { exit_code: result.status, output: result.status === 0 ? result.stdout.trim() : 'Git metadata unavailable' };
}
const before = sourceHashes();
const started = new Date().toISOString();
function start(label, executable, args, env, cwd = root) {
  const child = spawn(executable, args, { cwd, env: { ...process.env, AI_PROVIDER: 'mock', ...env }, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  child.on('error', error => issues.push({ stage: 'server_start', label, error: error.message }));
  for (const stream of ['stdout', 'stderr']) child[stream].on('data', data => serverLogs.push({ label, stream, text: data.toString() }));
  children.push(child);
  return child;
}
async function ready(url) {
  const end = Date.now() + 30000;
  while (Date.now() < end) {
    try { if ((await fetch(url)).ok) return; } catch {}
    await new Promise(resolve => setTimeout(resolve, 150));
  }
  throw new Error(`Local server unavailable: ${url}`);
}
async function visibleLayout(page, width, stage) {
  const result = await page.evaluate(() => ({ viewport: window.innerWidth, document_width: document.documentElement.scrollWidth, controls: [...document.querySelectorAll('button,input')].filter(e => e.getClientRects().length).map(e => { const r = e.getBoundingClientRect(); return { name: e.getAttribute('aria-label') || e.textContent || e.getAttribute('name') || e.tagName, left: r.left, right: r.right, width: r.width }; }) }));
  assert(result.document_width <= width + 1, `Horizontal document overflow at ${width}/${stage}`);
  for (const control of result.controls) assert(control.left >= -1 && control.right <= width + 1 && control.width > 0, `Control outside horizontal viewport at ${width}/${stage}: ${control.name}`);
  checks.push({ width, stage, layout: result });
}
async function act(page, operation) {
  const responsePromise = page.waitForResponse(response => response.url().includes('/actions') && response.request().method() === 'POST');
  await operation();
  const response = await responsePromise;
  const payload = await response.json();
  // Creation is deliberately not observed. Actions must never include a session token.
  assert(!JSON.stringify(payload).includes('"token"'), 'Action response token field');
  return { status: response.status(), payload };
}
async function route(width) {
  const context = await browser.newContext({ viewport: { width, height: 900 } });
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('response', response => { if (response.url().includes('/api/')) checks.push({ width, stage: 'http_status_only_no_headers_or_body', path: new URL(response.url()).pathname, status: response.status() }); });
  await page.goto(frontendURL, { waitUntil: 'networkidle' });
  await visibleLayout(page, width, 'welcome');
  await page.getByRole('button', { name: '开始新游戏 →', exact: true }).click();
  try { await expect(page.locator('#room-title')).toHaveText('值班室'); }
  catch (error) { checks.push({ width, stage: 'creation_failure_visible_UI', visible_text: await page.locator('body').innerText(), page_errors: pageErrors }); await page.screenshot({ path: path.join(folder, `creation-failure-${width}.png`), fullPage: true }); throw error; }
  await expect(page.locator('.inventory')).toContainText('背包还是空的');
  await expect(page.locator('.clues')).toContainText('第一页，等待发现');
  await expect(page.locator('.exit-button')).toBeDisabled();
  assert(!(await page.locator('body').innerText()).includes('三角记为3'), 'Undiscovered note text visible');
  await visibleLayout(page, width, 'initial');
  await page.screenshot({ path: path.join(folder, `initial-${width}.png`), fullPage: true });
  for (const [object, clue] of [['值班便签', '三角记为3'], ['值班柜', '柜门标签从左到右']]) {
    await page.locator('.object-grid').getByRole('button', { name: new RegExp(object) }).click();
    const response = await act(page, () => page.locator('.object-details').getByRole('button', { name: /查看/ }).click());
    assert.equal(response.status, 200);
    await expect(page.locator('.clues')).toContainText(clue);
  }
  const input = page.getByLabel('值班柜密码', { exact: true });
  await input.fill('000');
  const wrong = await act(page, () => input.press('Enter'));
  assert.equal(wrong.status, 409);
  assert.equal(wrong.payload.error.code, 'WRONG_CODE');
  await expect(page.getByRole('alert')).toContainText('密码不正确');
  assert.equal(wrong.payload.visible_state.revision, 2);
  assert.equal(wrong.payload.visible_state.inventory.length, 0);
  await input.fill('382');
  const opened = await act(page, () => input.press('Enter'));
  assert.equal(opened.status, 200);
  assert.equal(opened.payload.data.visible_state.revision, 3);
  await expect(page.locator('.object-grid').getByRole('button', { name: /门卡/ })).toBeVisible();
  await page.locator('.object-grid').getByRole('button', { name: /门卡/ }).click();
  const taken = await act(page, () => page.locator('.object-details').getByRole('button', { name: /拾取/ }).click());
  assert.equal(taken.payload.data.visible_state.revision, 4);
  await expect(page.locator('.inventory')).toContainText('门卡');
  const used = await act(page, () => page.locator('.inventory').getByRole('button', { name: /使用于设备间刷卡门/ }).click());
  assert.equal(used.payload.data.visible_state.revision, 5);
  await expect(page.locator('.exit-button')).toBeEnabled();
  await visibleLayout(page, width, 'unlocked');
  await page.screenshot({ path: path.join(folder, `unlocked-${width}.png`), fullPage: true });
  const moved = await act(page, () => page.locator('.exit-button').click());
  assert.equal(moved.payload.data.visible_state.room.room_id, 'R2');
  await expect(page.locator('#room-title')).toHaveText('设备间');
  await expect(page.locator('.clues .clue-list li')).toHaveCount(2);
  const returned = await act(page, () => page.locator('.exit-button').filter({ hasText: '值班室' }).click());
  assert.equal(returned.payload.data.visible_state.room.room_id, 'R1');
  await expect(page.locator('#room-title')).toHaveText('值班室');
  await page.reload({ waitUntil: 'networkidle' });
  await page.locator('.top-actions').getByRole('button', { name: '继续当前游戏', exact: true }).press('Enter');
  await expect(page.locator('#room-title')).toHaveText('值班室');
  await expect(page.locator('.inventory')).toContainText('门卡');
  await expect(page.locator('.clues .clue-list li')).toHaveCount(2);
  await page.getByRole('button', { name: '新游戏', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('button', { name: '取消', exact: true })).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.locator('.inventory')).toContainText('门卡');
  await visibleLayout(page, width, 'continued');
  await page.screenshot({ path: path.join(folder, `continued-${width}.png`), fullPage: true });
  if (suite === 'm2') await completeM2(page, width);
  assert.deepEqual(pageErrors, [], 'Browser page errors');
  checks.push({ width, route: 'R1 inspect both clues → wrong code denied → keyboard correct code → take → use → R2 → return → reload → keyboard cancel new game', passed: true, revisions: [1, 2, 3, 4, 5, 6, 7], page_errors: pageErrors });
  await context.close();
}
async function select(page, name) {
  await page.locator('.object-grid').getByRole('button', { name: new RegExp(name) }).press('Enter');
}
async function inspect(page, name, text) {
  await select(page, name);
  const response = await act(page, () => page.locator('.object-details').getByRole('button', { name: /查看/ }).press('Enter'));
  assert.equal(response.status, 200);
  await expect(page.locator('.clues')).toContainText(text);
  return response.payload.data.visible_state;
}
async function code(page, objectName, value) {
  await select(page, objectName);
  const input = page.getByLabel(objectName + '密码', { exact: true });
  await input.fill(value);
  const response = await act(page, () => input.press('Enter'));
  assert.equal(response.status, 200);
  return response.payload.data.visible_state;
}
async function take(page, objectName) {
  await select(page, objectName);
  const response = await act(page, () => page.locator('.object-details').getByRole('button', { name: /拾取/ }).press('Enter'));
  assert.equal(response.status, 200);
  return response.payload.data.visible_state;
}
async function use(page, itemName, targetName) {
  const item = page.locator('.inventory-item').filter({ has: page.getByRole('heading', { name: itemName, exact: true }) });
  const response = await act(page, () => item.getByRole('button', { name: new RegExp('使用于' + targetName) }).press('Enter'));
  assert.equal(response.status, 200);
  return response.payload.data.visible_state;
}
async function move(page, roomName) {
  const response = await act(page, () => page.locator('.exit-button').filter({ hasText: roomName }).press('Enter'));
  assert.equal(response.status, 200);
  await expect(page.locator('#room-title')).toHaveText(roomName);
  return response.payload.data.visible_state;
}
async function controlUI(page, operation) {
  const responsePromise = page.waitForResponse(response => response.url().endsWith('/' + operation) && response.request().method() === 'POST');
  if (operation === 'save') await page.getByRole('button', { name: '保存进度', exact: true }).press('Enter');
  else {
    await page.getByRole('button', { name: operation === 'reset' ? '重新开始' : '恢复存档', exact: true }).press('Enter');
    await expect(page.getByRole('dialog')).toBeVisible();
    if (operation === 'reset') await expect(page.getByRole('dialog')).toContainText('已有存档仍可恢复');
    await page.getByRole('dialog').getByRole('button', { name: operation === 'reset' ? '确认开始' : '确认恢复', exact: true }).press('Enter');
  }
  const response = await responsePromise;
  const payload = await response.json();
  assert.equal(response.status(), 200);
  assert(!JSON.stringify(payload).includes('"token"'), 'Control response token field');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  return payload.data.visible_state;
}
function gameProjection(state) {
  return Object.fromEntries(['status', 'room', 'objects', 'inventory', 'clues', 'exits', 'progress'].map(key => [key, state[key]]));
}
async function completeM2(page, width) {
  await move(page, '设备间');
  await expect(page.locator('.exit-button').filter({ hasText: '出口控制室' })).toBeDisabled();
  await select(page, '屏幕');
  const noPower = await act(page, () => page.locator('.object-details').getByRole('button', { name: /查看/ }).press('Enter'));
  assert.equal(noPower.status, 200);
  assert(noPower.payload.data.receipt.observation.includes('当前无显示'));
  assert(!noPower.payload.data.visible_state.clues.some(clue => clue.clue_id === 'r2_monitor_clue'));
  await take(page, '备用保险丝');
  const powered = await use(page, '保险丝', '电源箱');
  assert.equal(powered.progress.power_on, true);
  assert(!powered.inventory.some(item => item.item_id === 'fuse'));
  assert(!powered.clues.some(clue => clue.clue_id === 'r2_monitor_clue'));
  await inspect(page, '屏幕', '青色7');
  await inspect(page, '抽屉', '抽屉标签从左到右');
  const saved = await controlUI(page, 'save');
  await expect(page.locator('.save-panel')).toContainText('已有存档');
  await visibleLayout(page, width, 'R2_saved');
  await page.screenshot({ path: path.join(folder, `R2-saved-${width}.png`), fullPage: true });
  await code(page, '抽屉', '724');
  const progressed = await take(page, '应急钥匙');
  const restored = await controlUI(page, 'restore');
  assert.deepEqual(gameProjection(restored), gameProjection(saved));
  assert.equal(restored.revision, progressed.revision + 1);
  assert.notEqual(restored.generation, progressed.generation);
  await expect(page.locator('.inventory')).not.toContainText('应急钥匙');
  await select(page, '抽屉');
  await expect(page.getByLabel('抽屉密码', { exact: true })).toHaveValue('');
  const reset = await controlUI(page, 'reset');
  assert.equal(reset.room.room_id, 'R1');
  assert.deepEqual(reset.inventory, []);
  assert.deepEqual(reset.clues, []);
  assert.deepEqual(reset.save, saved.save);
  await expect(page.locator('#room-title')).toHaveText('值班室');
  const afterResetRestore = await controlUI(page, 'restore');
  assert.deepEqual(gameProjection(afterResetRestore), gameProjection(saved));
  await expect(page.locator('#room-title')).toHaveText('设备间');
  await code(page, '抽屉', '724');
  await take(page, '应急钥匙');
  const unlocked = await use(page, '应急钥匙', '出口控制室钥匙门');
  assert(unlocked.inventory.some(item => item.item_id === 'emergency_key'));
  await move(page, '出口控制室');
  await expect(page.locator('.exit-button').filter({ hasText: '实验室出口' })).toBeDisabled();
  await inspect(page, '出口检查单', '依次确认');
  await inspect(page, '检查面板', '冷却对应2');
  await visibleLayout(page, width, 'R3_before_check');
  await page.screenshot({ path: path.join(folder, `R3-${width}.png`), fullPage: true });
  const checked = await code(page, '检查面板', '231');
  assert.equal(checked.progress.check_done, true);
  const won = await move(page, '实验室出口');
  assert.equal(won.status, 'won');
  await expect(page.getByRole('heading', { name: '成功逃离实验室', exact: true })).toBeVisible();
  await expect(page.locator('.clues .clue-list li')).toHaveCount(6);
  await visibleLayout(page, width, 'won');
  await page.screenshot({ path: path.join(folder, `won-${width}.png`), fullPage: true });
  checks.push({ width, stage: 'M2_full_manual_save_restore_reset_route', passed: true, evidence: 'Actual UI control responses verified; no session capability recorded', final_status: won.status, final_revision: won.revision });
}
function scanBuiltResources() {
  const dist = path.join(root, 'frontend/dist');
  if (!fs.existsSync(dist)) { issues.push({ stage: 'A10_build_scan', error: 'frontend/dist missing; build scan not performed' }); return; }
  const patterns = ['三角记为3', '柜门标签从左到右是', '青色7、橙色2', '冷却对应2', 'level_design.md', 'opened_containers', 'discovered_clue_ids'];
  let files = 0;
  function walk(dir) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const file = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(file);
      else if (/\.(js|html|css|json|map)$/.test(entry.name)) {
        files++;
        const text = fs.readFileSync(file, 'utf8');
        for (const pattern of patterns) assert(!text.includes(pattern), 'Hidden game configuration or undiscovered clue in built resource: ' + path.relative(dist, file));
      }
    }
  }
  walk(dist);
  checks.push({ stage: 'A10_build_scan', files_scanned: files, forbidden_patterns_checked: patterns.length, passed: true, limitation: 'Targeted frozen-level disclosure patterns; not a proof about arbitrary future secrets or AI contexts.' });
}
try {
  start('backend', python, ['-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', String(backendPort), '--no-access-log'], { SQLITE_PATH: path.join(temp, 'game.sqlite') });
  start('frontend', process.execPath, [path.join(root, 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', String(frontendPort), '--strictPort'], { CAMPUS_BACKEND_URL: backendURL }, path.join(root, 'frontend'));
  await Promise.all([ready(`${backendURL}/api/health`), ready(frontendURL)]);
  browser = await chromium.launch({ headless: true, executablePath: browserPath });
  for (const width of [1280, 768, 390]) {
    try { await route(width); } catch (error) { issues.push({ stage: 'R1_browser', width, error: error.message }); }
  }
  scanBuiltResources();
} catch (error) { issues.push({ stage: 'runner', error: error.message }); }
finally {
  await browser?.close();
  for (const child of children) if (child.pid) {
    const result = spawnSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], { encoding: 'utf8', windowsHide: true });
    checks.push({ stage: 'stop_QA_owned_process_tree', pid: child.pid, exit_code: result.status });
  }
  try {
    const resolvedTemp = fs.realpathSync(temp);
    const resolvedRoot = fs.realpathSync(os.tmpdir());
    assert.equal(path.dirname(resolvedTemp).toLowerCase(), resolvedRoot.toLowerCase(), 'Cleanup path escaped owned temp root');
    assert(path.basename(resolvedTemp).startsWith('campus-qa-browser-'), 'Cleanup path lacks QA-owned prefix');
    assert.equal(path.resolve(temp).toLowerCase(), resolvedTemp.toLowerCase(), 'Cleanup target resolved elsewhere');
    fs.rmSync(resolvedTemp, { recursive: true });
  } catch (error) { issues.push({ stage: 'temporary_database_cleanup', error: error.message }); }
  const after = sourceHashes();
  if (JSON.stringify(before) !== JSON.stringify(after)) issues.push({ stage: 'source_freeze', error: 'Hashed target files changed during test; result cannot certify frozen candidate' });
  fs.writeFileSync(path.join(folder, 'checks.json'), JSON.stringify({ checks, issues }, null, 2));
  fs.writeFileSync(path.join(folder, 'server-output.json'), JSON.stringify(serverLogs, null, 2));
  const evidenceHashes = Object.fromEntries(fs.readdirSync(folder).map(name => [name, crypto.createHash('sha256').update(fs.readFileSync(path.join(folder, name))).digest('hex')]));
  const metadata = { candidate, suite, target: 'Manual baseline working-tree local backend/frontend candidate; backend/app/ai independent provider probe excluded, no gameplay AI calls', head: gitRead('rev-parse', 'HEAD'), working_tree: gitRead('status', '--short'), command: [process.execPath, ...process.argv.slice(1)], started, ended: new Date().toISOString(), provider: 'AI_PROVIDER=mock explicitly; no model call', node: process.version, playwright: requireFrontend('@playwright/test/package.json').version, browser_executable: browserPath, browser_mode: 'new isolated headless context; no user profile', widths: [1280, 768, 390], source_sha256_before: before, source_sha256_after: after, evidence_sha256: evidenceHashes, exit_code: issues.length ? 1 : 0, privacy: 'No create response, request headers, sessionStorage, HAR, or browser trace recorded. Screenshots only UI.' };
  fs.writeFileSync(path.join(folder, 'run.json'), JSON.stringify(metadata, null, 2));
  console.log(JSON.stringify({ evidence: folder, passed_widths: checks.filter(c => c.route && c.passed).map(c => c.width), issues, exit_code: metadata.exit_code }, null, 2));
  process.exitCode = metadata.exit_code;
}
