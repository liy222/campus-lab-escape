// Independent v3.1 manual-route acceptance. Mock provider only; uses an owned DB.
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
const candidate = process.argv[2];
assert(candidate, 'Pass the frozen candidate identifier explicitly');
const evidenceRoot = path.join(root, 'evidence/upgrade/v3.1/qa');
const folder = path.join(evidenceRoot, new Date().toISOString().replace(/[-:.]/g, '') + '-browser');
fs.mkdirSync(folder, { recursive: true });
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'campus-upgrade-v31-'));
const python = 'C:\\Users\\liyh\\.conda\\envs\\1\\python.exe';
const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const children = [], checks = [], issues = [], logs = [];
let browser;

function sourceHashes() {
  const result = {};
  for (const relative of ['backend/app/domain/upgrade_models.py', 'backend/app/domain/upgrade_rules.py', 'backend/app/storage/sqlite.py', 'backend/app/storage/ai.py', 'backend/app/api/routes.py', 'backend/app/main.py', 'backend/app/ai/runtime.py', 'frontend/src/App.tsx', 'frontend/src/api.ts', 'frontend/src/style.css', 'frontend/src/Assistant.tsx', 'scripts/dev.py', 'contracts/api.schema.json']) {
    result[relative] = crypto.createHash('sha256').update(fs.readFileSync(path.join(root, relative))).digest('hex');
  }
  return result;
}
function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      server.close(error => error ? reject(error) : resolve(port));
    });
  });
}
const before = sourceHashes();
const started = new Date().toISOString();
function start(label, executable, args, env, cwd = root) {
  const child = spawn(executable, args, {
    cwd, env: { ...process.env, AI_PROVIDER: 'mock', PYTHONUTF8: '1', ...env },
    windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
  });
  children.push(child);
  child.on('error', error => issues.push({ stage: 'start', label, error: error.message }));
  for (const stream of ['stdout', 'stderr']) child[stream].on('data', data => logs.push({ label, stream, text: data.toString() }));
  return child;
}
async function ready(url) {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    try { if ((await fetch(url)).ok) return; } catch {}
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error(`Local service did not become ready: ${url}`);
}
async function actionResponse(page, operation) {
  const waiting = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/actions') && response.request().method() === 'POST');
  await operation();
  const response = await waiting;
  return { response, body: await response.json() };
}
async function layout(page, width, stage) {
  const dimensions = await page.evaluate(() => ({
    viewport: innerWidth,
    documentWidth: document.documentElement.scrollWidth,
    controls: [...document.querySelectorAll('button,input,textarea')].filter(e => e.getClientRects().length).map(e => {
      const r = e.getBoundingClientRect(); return { left: r.left, right: r.right, width: r.width };
    }),
  }));
  assert(dimensions.documentWidth <= width + 1, `${stage}: horizontal page overflow`);
  for (const control of dimensions.controls) assert(control.left >= -1 && control.right <= width + 1 && control.width > 0, `${stage}: control outside viewport`);
  checks.push({ stage, width, dimensions });
}
function objectButton(page, name) {
  return page.locator('.object-grid').getByRole('button', { name: new RegExp(name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) });
}
async function selectObject(page, name) { await objectButton(page, name).press('Enter'); }
async function observe(page, name) {
  await selectObject(page, name);
  const result = await actionResponse(page, () => page.getByRole('button', { name: /^观察$/ }).press('Enter'));
  assert.equal(result.response.status(), 200, `${name} observation failed`);
  assert(result.body.data.receipt.observation || result.body.data.receipt.message);
  return result.body.data.visible_state;
}
async function interact(page, name) {
  await selectObject(page, name);
  return actionResponse(page, () => page.getByRole('button', { name: /^互动$/ }).press('Enter'));
}
async function password(page, name, value) {
  await selectObject(page, name);
  await page.getByRole('button', { name: /^互动$/ }).press('Enter');
  const input = page.getByLabel('输入你推理出的数字', { exact: true });
  await expect(input).toBeVisible();
  await input.fill(value);
  const waiting = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/actions') && response.request().method() === 'POST');
  await input.press('Enter');
  const response = await waiting;
  const body = await response.json();
  assert.equal(response.status(), 200, `${name} rejected the frozen route code`);
  return body.data.visible_state;
}
async function useItem(page, itemName, targetName) {
  const itemButton = page.locator('.inventory-item').filter({ hasText: itemName })
    .getByRole('button', { name: /^(选择物品|取消选择)$/ });
  if (await itemButton.getAttribute('aria-pressed') !== 'true') await itemButton.press('Enter');
  await selectObject(page, targetName);
  return actionResponse(page, () => page.getByRole('button', { name: /^使用物品/ }).press('Enter'));
}
async function move(page, roomName) {
  const waiting = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/actions') && response.request().method() === 'POST');
  await page.locator('.exit-button').filter({ hasText: roomName }).press('Enter');
  const response = await waiting, body = await response.json();
  assert.equal(response.status(), 200);
  await expect(page.locator('#room-title')).toHaveText(roomName);
  return body.data.visible_state;
}
async function control(page, operation) {
  const waiting = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/' + operation) && response.request().method() === 'POST');
  if (operation === 'save') await page.getByRole('button', { name: '保存进度', exact: true }).press('Enter');
  else {
    await page.getByRole('button', { name: operation === 'restore' ? '恢复存档' : '重新开始', exact: true }).press('Enter');
    await page.getByRole('dialog').getByRole('button', { name: operation === 'restore' ? '确认恢复' : '确认开始', exact: true }).press('Enter');
  }
  const response = await waiting, body = await response.json();
  assert.equal(response.status(), 200);
  return body.data.visible_state;
}
async function wrongTargets(page, itemName, validTarget, targets) {
  for (const target of targets) {
    if (target === validTarget) continue;
    const result = await useItem(page, itemName, target);
    assert.equal(result.response.status(), 409, `${itemName} unexpectedly worked on ${target}`);
    assert.equal(result.body.error.code, 'PRECONDITION_FAILED');
    assert.match(result.body.error.message, /[\u3400-\u9fff]/, 'Mismatch feedback should be natural Chinese');
    assert.equal(result.body.visible_state.revision, resultBeforeRevision);
    assert.deepEqual(result.body.visible_state.inventory.map(item => item.item_id), resultBeforeInventory);
    checks.push({ stage: 'wrong-item-target', item: itemName, target, status: result.response.status(), revision_unchanged: true, inventory_unchanged: true });
  }
}

let backendPort, frontendPort, resultState;
let resultBeforeRevision = 0, resultBeforeInventory = [];
async function keyInput(page) {
  await page.getByRole('radio', { name: /真实 DeepSeek/ }).check();
  await page.getByLabel('DeepSeek API Key', { exact: true }).fill('SYNTHETIC_QA_NOT_A_REAL_KEY');
}
async function keyCleared(page) {
  await expect(page.getByRole('radio', { name: /免费模拟/ })).toBeChecked();
  await page.getByRole('radio', { name: /真实 DeepSeek/ }).check();
  await expect(page.getByLabel('DeepSeek API Key', { exact: true })).toHaveValue('');
  await page.getByRole('radio', { name: /免费模拟/ }).check();
}
function gameplay(state) {
  return Object.fromEntries(Object.entries(state).filter(([key]) => !['revision', 'generation', 'save'].includes(key)));
}
async function expectStage(result, device, stage) {
  assert.equal(result.response.status(), 200);
  assert.equal(result.body.data.visible_state.device_states[device], stage);
  checks.push({ stage: 'device-transition', device, value: stage });
  return result.body.data.visible_state;
}
try {
  assert(fs.existsSync(chromePath), 'Chrome executable not installed at expected path');
  backendPort = await freePort(); frontendPort = await freePort();
  while (frontendPort === backendPort) frontendPort = await freePort();
  const backendURL = `http://127.0.0.1:${backendPort}`, frontendURL = `http://127.0.0.1:${frontendPort}`;
  const backendArgs = ['-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', String(backendPort), '--no-access-log'];
  const backendEnv = { GAMEPLAY_VERSION: 'v3.1', SQLITE_PATH: path.join(temp, 'game-v3.1.sqlite') };
  const backend = start('backend', python, backendArgs, backendEnv);
  start('frontend', process.execPath, [path.join(root, 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', String(frontendPort), '--strictPort'], { CAMPUS_BACKEND_URL: backendURL, VITE_GAMEPLAY_VERSION: 'v3.1' }, path.join(root, 'frontend'));
  await Promise.all([ready(`${backendURL}/api/health`), ready(frontendURL)]);
  browser = await chromium.launch({ headless: true, executablePath: chromePath });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', () => pageErrors.push('uncaught browser exception'));
  await page.goto(frontendURL, { waitUntil: 'networkidle' });
  await page.evaluate(() => sessionStorage.setItem('campus-lab-session-v1', 'qa-preserve-legacy-namespace'));
  await page.getByRole('button', { name: '开始新游戏 →', exact: true }).press('Enter');
  await expect(page.locator('#room-title')).toHaveText('值班室');
  assert(await page.evaluate(() => !!sessionStorage.getItem('campus-lab-session-upgrade-v3.1')));
  assert.equal(await page.evaluate(() => sessionStorage.getItem('campus-lab-session-v1')), 'qa-preserve-legacy-namespace');
  await layout(page, 1280, 'R1-start');
  assert.equal(await page.getByText(/可用于|使用于/).count(), 0);


  await page.setViewportSize({ width: 1280, height: 900 });
  await observe(page, '值班便签'); await observe(page, '值班柜');
  const accepted = await password(page, '值班柜', '382');
  assert.equal(accepted.device_states.cabinet, 'CODE_ACCEPTED');
  assert.equal(await objectButton(page, '门卡').count(), 0);
  await expectStage(await interact(page, '值班柜'), 'cabinet', 'OPEN');
  await observe(page, '门卡');
  await expectStage(await interact(page, '门卡'), 'cabinet', 'ITEM_TAKEN');
  await observe(page, '设备间门');
  const wrong = await useItem(page, '门卡', '值班柜');
  assert.equal(wrong.response.status(), 409);
  assert.equal(wrong.body.error.code, 'PRECONDITION_FAILED');
  assert.equal((await useItem(page, '门卡', '设备间门')).response.status(), 200);
  await move(page, '设备间');
  await observe(page, '备用保险丝'); await interact(page, '备用保险丝');
  await observe(page, '电源箱');
  await expectStage(await interact(page, '电源箱'), 'powerbox', 'OPEN');
  await expectStage(await interact(page, '电源箱'), 'powerbox', 'MISSING_FUSE');
  let installed = await expectStage(await useItem(page, '保险丝', '电源箱'), 'powerbox', 'FUSE_INSTALLED');
  assert.equal(installed.progress.power_on, false);


  await page.setViewportSize({ width: 1280, height: 900 });
  const saved = await control(page, 'save');
  assert.equal(saved.save.level_version, '3.1.0');
  await keyInput(page);
  await expectStage(await interact(page, '电源箱'), 'powerbox', 'CIRCUIT_READY');
  const restored = await control(page, 'restore');
  assert.deepEqual(gameplay(restored), gameplay(saved));
  assert.notEqual(restored.generation, saved.generation);
  await keyCleared(page);
  // Actual OS backend restart, preserving only this runner-owned database.
  const stopped = spawnSync('taskkill', ['/PID', String(backend.pid), '/T', '/F'], { encoding: 'utf8', windowsHide: true });
  assert.equal(stopped.status, 0);
  if (backend.exitCode === null && backend.signalCode === null) await new Promise(resolve => backend.once('exit', resolve));
  start('backend-restarted', python, backendArgs, backendEnv);
  await ready(`${backendURL}/api/health`);
  await keyInput(page);
  await page.reload({ waitUntil: 'networkidle' });
  await page.locator('.welcome-buttons').getByRole('button', { name: '继续当前游戏', exact: true }).press('Enter');
  await expect(page.locator('#room-title')).toHaveText('设备间');
  await keyCleared(page);
  await selectObject(page, '电源箱');
  await expect(page.locator('.object-details')).toContainText('玻璃管已经卡在触点之间');
  await expectStage(await interact(page, '电源箱'), 'powerbox', 'CIRCUIT_READY');
  await expectStage(await interact(page, '电源箱'), 'powerbox', 'POWER_ON');
  await observe(page, '电脑');
  await expectStage(await interact(page, '电脑'), 'computer', 'BOOTING');
  await expectStage(await interact(page, '电脑'), 'computer', 'LOGIN_LOCKED');
  await observe(page, '电脑'); await observe(page, '抽屉');
  let unlocked = await password(page, '电脑', '724');
  assert.equal(unlocked.device_states.computer, 'UNLOCKED');
  await expectStage(await interact(page, '电脑'), 'computer', 'DATA_READ');
  await password(page, '抽屉', '724');
  await observe(page, '应急钥匙'); await interact(page, '应急钥匙');
  await observe(page, '控制室门');
  assert.equal((await useItem(page, '应急钥匙', '控制室门')).response.status(), 200);
  await move(page, '出口控制室');
  await observe(page, '出口检查单'); await observe(page, '检查面板'); await observe(page, '实验室出口');
  await expectStage(await useItem(page, '门卡', '实验室出口'), 'exit', 'CARD_ACCEPTED');
  await expectStage(await interact(page, '实验室出口'), 'exit', 'FINAL_CHECK');
  await password(page, '检查面板', '231');
  await expectStage(await interact(page, '实验室出口'), 'exit', 'UNLOCKED');
  await expectStage(await interact(page, '实验室出口'), 'exit', 'OPEN');
  resultState = await move(page, '实验室出口');
  assert.equal(resultState.status, 'won');
  await expect(page.getByRole('heading', { name: '成功逃离实验室', exact: true })).toBeVisible();
  await layout(page, 1280, 'three-room-victory');



  await keyInput(page);
  await control(page, 'reset'); await keyCleared(page);
  assert.equal(pageErrors.length, 0);
  checks.push({ stage: 'upgrade-route-save-restore-reload-actual-backend-restart-win', passed: true, final_room: resultState.room.room_id, level: saved.level_version });
  await context.close();
  // Same source, explicit legacy selection, original storage key and level-2 slot.
  const legacyBackendPort = await freePort(), legacyFrontendPort = await freePort();
  const legacyBackendURL = `http://127.0.0.1:${legacyBackendPort}`, legacyFrontendURL = `http://127.0.0.1:${legacyFrontendPort}`;
  start('legacy-backend', python, ['-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', String(legacyBackendPort), '--no-access-log'], { GAMEPLAY_VERSION: 'legacy', SQLITE_PATH: path.join(temp, 'legacy.sqlite') });
  start('legacy-frontend', process.execPath, [path.join(root, 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', String(legacyFrontendPort), '--strictPort'], { CAMPUS_BACKEND_URL: legacyBackendURL, VITE_GAMEPLAY_VERSION: 'legacy' }, path.join(root, 'frontend'));
  await Promise.all([ready(`${legacyBackendURL}/api/health`), ready(legacyFrontendURL)]);
  const legacyContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const legacy = await legacyContext.newPage();
  await legacy.goto(legacyFrontendURL, { waitUntil: 'networkidle' });
  await legacy.evaluate(() => sessionStorage.setItem('campus-lab-session-upgrade-v3.1', 'qa-preserve-upgrade-namespace'));
  await legacy.getByRole('button', { name: '开始新游戏 →', exact: true }).press('Enter');
  await expect(legacy.locator('#room-title')).toHaveText('值班室');
  assert(await legacy.evaluate(() => !!sessionStorage.getItem('campus-lab-session-v1')));
  assert.equal(await legacy.evaluate(() => sessionStorage.getItem('campus-lab-session-upgrade-v3.1')), 'qa-preserve-upgrade-namespace');
  await observe(legacy, '值班便签'); await observe(legacy, '值班柜');
  await password(legacy, '值班柜', '382'); await interact(legacy, '门卡');
  assert.equal((await useItem(legacy, '门卡', '设备间刷卡门')).response.status(), 200);
  await move(legacy, '设备间');
  const legacySaved = await control(legacy, 'save');
  assert.equal(legacySaved.level_version, '2.0.0');
  assert.equal(legacySaved.save.level_version, '2.0.0');
  assert.equal(legacySaved.device_states, undefined);
  await control(legacy, 'reset');
  const legacyRestored = await control(legacy, 'restore');
  assert.deepEqual(gameplay(legacyRestored), gameplay(legacySaved));
  await legacy.reload({ waitUntil: 'networkidle' });
  await legacy.locator('.welcome-buttons').getByRole('button', { name: '继续当前游戏', exact: true }).press('Enter');
  await expect(legacy.locator('#room-title')).toHaveText('设备间');

  checks.push({ stage: 'same-source-legacy-mode-level2-slot-and-storage-namespace', passed: true });
  await legacyContext.close();
} catch (error) {
  issues.push({ stage: 'runner', error: error.message });
} finally {
  await browser?.close();
  for (const child of children) if (child.pid && child.exitCode === null && child.signalCode === null) {
    const stopped = spawnSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], { encoding: 'utf8', windowsHide: true });
    checks.push({ stage: 'stop-owned-process-tree', pid: child.pid, exit_code: stopped.status });
  }
  try {
    const resolved = fs.realpathSync(temp), tempRoot = fs.realpathSync(os.tmpdir());
    assert.equal(path.dirname(resolved).toLowerCase(), tempRoot.toLowerCase());
    assert(path.basename(resolved).startsWith('campus-upgrade-v31-'));
    assert.equal(path.resolve(temp).toLowerCase(), resolved.toLowerCase());
    fs.rmSync(resolved, { recursive: true });
  } catch (error) { issues.push({ stage: 'temporary-database-cleanup', error: error.message }); }
  const after = sourceHashes();
  if (JSON.stringify(before) !== JSON.stringify(after)) issues.push({ stage: 'source-freeze', error: 'Candidate source files changed during the run' });
  fs.writeFileSync(path.join(folder, 'checks.json'), JSON.stringify({ checks, issues }, null, 2));
  fs.writeFileSync(path.join(folder, 'server-output.json'), JSON.stringify(logs, null, 2));
  const metadata = {
    candidate, started, ended: new Date().toISOString(), command: [process.execPath, ...process.argv.slice(1)],
    provider: 'AI_PROVIDER=mock; no paid model call', browser: 'Google Chrome, headless isolated context',
    viewport_widths: [1280], backend_port: backendPort, frontend_port: frontendPort,
    source_sha256_before: before, source_sha256_after: after,
    exit_code: issues.length ? 1 : 0,
    limitations: ['This scripted browser route does not measure real-player completion time or human acceptance.'],
  };
  fs.writeFileSync(path.join(folder, 'run.json'), JSON.stringify(metadata, null, 2));
  console.log(JSON.stringify({ evidence: folder, checks, issues, exit_code: metadata.exit_code }, null, 2));
  process.exitCode = metadata.exit_code;
}
