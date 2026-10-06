// Independent v3.0 manual-route acceptance. Mock provider only; uses an owned DB.
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
const evidenceRoot = path.join(root, 'evidence/upgrade/v3.0/qa');
const folder = path.join(evidenceRoot, new Date().toISOString().replace(/[-:.]/g, '') + '-browser');
fs.mkdirSync(folder, { recursive: true });
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'campus-upgrade-v30-'));
const python = 'C:\\Users\\liyh\\.conda\\envs\\1\\python.exe';
const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const children = [], checks = [], issues = [], logs = [];
let browser;

function sourceHashes() {
  const result = {};
  for (const relative of ['backend/app/domain/rules.py', 'frontend/src/App.tsx', 'frontend/src/api.ts', 'frontend/src/style.css']) {
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
try {
  assert(fs.existsSync(chromePath), 'Chrome executable not installed at expected path');
  backendPort = await freePort(); frontendPort = await freePort();
  while (frontendPort === backendPort) frontendPort = await freePort();
  const backendURL = `http://127.0.0.1:${backendPort}`, frontendURL = `http://127.0.0.1:${frontendPort}`;
  start('backend', python, ['-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', String(backendPort), '--no-access-log'], { SQLITE_PATH: path.join(temp, 'game.sqlite') });
  start('frontend', process.execPath, [path.join(root, 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', String(frontendPort), '--strictPort'], { CAMPUS_BACKEND_URL: backendURL }, path.join(root, 'frontend'));
  await Promise.all([ready(`${backendURL}/api/health`), ready(frontendURL)]);
  browser = await chromium.launch({ headless: true, executablePath: chromePath });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', () => pageErrors.push('uncaught browser exception'));
  await page.goto(frontendURL, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: '开始新游戏 →', exact: true }).press('Enter');
  await expect(page.locator('#room-title')).toHaveText('值班室');
  await layout(page, 1280, 'R1-start');
  assert.equal(await page.getByLabel('输入你推理出的数字', { exact: true }).count(), 0, 'A password entry must not be visible before object interaction');
  assert.equal(await page.getByText(/可用于|使用于/).count(), 0, 'Item-target mapping shown in UI');

  await observe(page, '值班便签');
  await observe(page, '值班柜');
  await selectObject(page, '值班柜');
  assert.equal(await page.getByLabel('输入你推理出的数字', { exact: true }).count(), 0, 'Password field appeared before interaction');
  await page.getByRole('button', { name: /^互动$/ }).press('Enter');
  assert.equal(await page.getByLabel('输入你推理出的数字', { exact: true }).count(), 1, 'Interaction did not reveal the keypad');
  await page.getByLabel('输入你推理出的数字', { exact: true }).fill('382');
  let responsePromise = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/actions') && response.request().method() === 'POST');
  await page.getByLabel('输入你推理出的数字', { exact: true }).press('Enter');
  let response = await responsePromise; assert.equal(response.status(), 200);
  await interact(page, '门卡');
  await expect(page.locator('.inventory')).toContainText('门卡');

  // Read the visible targets from the scene; every wrong target must be
  // available for trial, and each refusal must preserve the public state.
  const r1Targets = await page.locator('.object-tile strong').allTextContents();
  const beforeWrong = await page.locator('footer').innerText();
  resultBeforeRevision = Number(beforeWrong.match(/进度\s+(\d+)/)?.[1]);
  resultBeforeInventory = ['access_card'];
  await wrongTargets(page, '门卡', '设备间刷卡门', ['值班便签', '值班柜']);
  const usedCard = await useItem(page, '门卡', '设备间刷卡门');
  assert.equal(usedCard.response.status(), 200);
  await move(page, '设备间');

  await interact(page, '备用保险丝');
  const r2Targets = await page.locator('.object-tile strong').allTextContents();
  resultBeforeInventory = ['access_card', 'fuse'];
  resultBeforeRevision = Number((await page.locator('footer').innerText()).match(/进度\s+(\d+)/)?.[1]);
  await wrongTargets(page, '保险丝', '电源箱', r2Targets.filter(name => name !== '备用保险丝'));
  const powered = await useItem(page, '保险丝', '电源箱');
  assert.equal(powered.response.status(), 200);
  await observe(page, '屏幕');
  await observe(page, '抽屉');
  const saved = await control(page, 'save');
  assert.equal(saved.save.level_version, '2.0.0', 'Existing level-2 save compatibility changed');

  await password(page, '抽屉', '724');
  await interact(page, '应急钥匙');
  await expect(page.locator('.inventory')).toContainText('应急钥匙');
  const keyTargets = await page.locator('.object-tile strong').allTextContents();
  resultBeforeInventory = ['access_card', 'emergency_key'];
  resultBeforeRevision = Number((await page.locator('footer').innerText()).match(/进度\s+(\d+)/)?.[1]);
  await wrongTargets(page, '应急钥匙', '出口控制室钥匙门', keyTargets.filter(name => name !== '应急钥匙'));

  const restored = await control(page, 'restore');
  assert.equal(restored.room.room_id, 'R2');
  assert(!restored.inventory.some(item => item.item_id === 'emergency_key'));
  await page.reload({ waitUntil: 'networkidle' });
  await page.locator('.welcome-buttons').getByRole('button', { name: '继续当前游戏', exact: true }).press('Enter');
  await expect(page.locator('#room-title')).toHaveText('设备间');
  await expect(page.locator('.inventory')).not.toContainText('应急钥匙');
  await password(page, '抽屉', '724');
  await interact(page, '应急钥匙');
  const opened = await useItem(page, '应急钥匙', '出口控制室钥匙门');
  assert.equal(opened.response.status(), 200);
  await move(page, '出口控制室');
  await observe(page, '出口检查单');
  await observe(page, '检查面板');
  await password(page, '检查面板', '231');
  resultState = await move(page, '实验室出口');
  assert.equal(resultState.status, 'won');
  await expect(page.getByRole('heading', { name: '成功逃离实验室', exact: true })).toBeVisible();
  await layout(page, 1280, 'three-room-victory');

  await page.setViewportSize({ width: 375, height: 812 });
  await layout(page, 375, 'mobile-victory');
  assert.equal(pageErrors.length, 0);
  checks.push({ stage: 'three-room-route-save-restore-refresh-win', passed: true, final_room: resultState.room.room_id, legacy_level: saved.level_version, mobile_width: 375 });
  await page.screenshot({ path: path.join(folder, 'mobile-victory.png'), fullPage: true });
  await context.close();
} catch (error) {
  issues.push({ stage: 'runner', error: error.message });
} finally {
  await browser?.close();
  for (const child of children) if (child.pid) {
    const stopped = spawnSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], { encoding: 'utf8', windowsHide: true });
    checks.push({ stage: 'stop-owned-process-tree', pid: child.pid, exit_code: stopped.status });
  }
  try {
    const resolved = fs.realpathSync(temp), tempRoot = fs.realpathSync(os.tmpdir());
    assert.equal(path.dirname(resolved).toLowerCase(), tempRoot.toLowerCase());
    assert(path.basename(resolved).startsWith('campus-upgrade-v30-'));
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
    viewport_widths: [1280, 375], backend_port: backendPort, frontend_port: frontendPort,
    source_sha256_before: before, source_sha256_after: after,
    exit_code: issues.length ? 1 : 0,
    limitations: ['This scripted browser route does not measure real-player completion time or human acceptance.'],
  };
  fs.writeFileSync(path.join(folder, 'run.json'), JSON.stringify(metadata, null, 2));
  console.log(JSON.stringify({ evidence: folder, checks, issues, exit_code: metadata.exit_code }, null, 2));
  process.exitCode = metadata.exit_code;
}
