// Frontend owner development check; independent acceptance is owned by QA.
// All gameplay uses UI buttons and only codes derived from already visible clues.
import { chromium, expect } from '@playwright/test';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
import { spawn } from 'node:child_process';

const root = resolve('..');
const stamp = new Date().toISOString().replace(/[:.]/g, '-');
const output = resolve(root, 'evidence/frontend', `T10-owner-m2-${stamp}`);
const temporary = resolve('node_modules/.cache', `owner-m2-${stamp}`);
await mkdir(output, { recursive: true });
await mkdir(temporary, { recursive: true });
const environment = Object.fromEntries(Object.entries(process.env).filter(([key]) => !/^(AI_|MODEL_|DEEPSEEK_|OPENAI_|ANTHROPIC_|VITE_)/i.test(key) && !/(TOKEN|SECRET|PASSWORD|CREDENTIAL|API_KEY|APIKEY)/i.test(key)));
environment.AI_PROVIDER = 'mock';
environment.SQLITE_PATH = resolve(temporary, 'game.sqlite');
environment.PYTHONIOENCODING = 'utf-8';
const backendPort = 8110;
const frontendPort = 5110;
const services = [];
const checks = [];
const errors = [];
const sourcePaths = ['frontend/src/App.tsx', 'frontend/src/api.ts', 'frontend/src/style.css', 'backend/app/domain/rules.py', 'backend/app/storage/sqlite.py', 'backend/app/api/routes.py'];
async function hashes() {
  return Object.fromEntries(await Promise.all(sourcePaths.map(async path => [path, createHash('sha256').update(await readFile(resolve(root, path))).digest('hex')])));
}
const sourceBefore = await hashes();
let browser;
const check = (name, details = {}) => checks.push({ name, result: 'passed', ...details });
const launch = (name, executable, args, env) => {
  const child = spawn(executable, args, { cwd: root, env, stdio: 'ignore', windowsHide: true });
  child.on('error', error => errors.push(`${name} startup: ${error.message}`));
  services.push({ name, child });
  return child;
};
async function waitReady(url) {
  const deadline = Date.now() + 25000;
  while (Date.now() < deadline) {
    if (services.some(({ child }) => child.exitCode !== null)) throw new Error('Local service exited before readiness');
    try { if ((await fetch(url)).ok) return; } catch { /* Startup only. */ }
    await new Promise(done => setTimeout(done, 150));
  }
  throw new Error('Local service readiness timed out');
}
async function stable(page) { await expect(page.locator('.pending')).toHaveCount(0); }
async function click(page, locator) { await locator.click(); await stable(page); }
async function object(page, name) { await click(page, page.locator('.object-tile').filter({ hasText: name })); }
async function inspect(page, name) { await object(page, name); await click(page, page.locator('.object-actions').getByRole('button', { name: '查看', exact: false })); }
async function take(page, name) { await object(page, name); await click(page, page.locator('.object-actions').getByRole('button', { name: '拾取', exact: false })); }
async function use(page, item, target) { await click(page, page.locator('.inventory-item').filter({ hasText: item }).getByRole('button', { name: `使用于${target} ↗`, exact: true })); }
async function move(page, room) { await click(page, page.locator('.exit-button').filter({ hasText: room })); }
function derive(mapping, order, expression) {
  const values = new Map([...mapping.matchAll(expression)].map(match => [match[1], match[2]]));
  const labels = [...values.keys()];
  const tokens = order.match(new RegExp(labels.join('|'), 'g')) || [];
  const code = tokens.map(token => values.get(token)).join('');
  expect(tokens.length).toBeGreaterThan(0);
  expect(code).toMatch(/^[0-9]{1,16}$/);
  return code;
}
async function codeFrom(page, target, mappingTitle, orderTitle, expression) {
  const mapping = await page.locator('.clue-list li').filter({ has: page.getByRole('heading', { name: mappingTitle, exact: true }) }).innerText();
  const order = await page.locator('.clue-list li').filter({ has: page.getByRole('heading', { name: orderTitle, exact: true }) }).innerText();
  await object(page, target);
  await page.getByLabel(`${target}密码`).fill(derive(mapping, order, expression));
  await page.getByLabel(`${target}密码`).press('Enter');
  await stable(page);
}
async function layout(page, stage, width) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
  await page.screenshot({ path: resolve(output, `${stage}-${width}.png`), fullPage: true });
  check('responsive layout without horizontal overflow', { stage, width });
}
async function toR2(page, count = () => {}) {
  await inspect(page, '值班便签'); count('inspect note');
  await inspect(page, '值班柜'); count('inspect cabinet');
  await codeFrom(page, '值班柜', '值班便签', '柜门顺序', /(三角|圆|方)记为([0-9]+)/g); count('submit visible-clue cabinet code');
  await take(page, '门卡'); count('take card');
  await use(page, '门卡', '设备间刷卡门'); count('use card');
  await move(page, '设备间'); count('move R2');
}
async function prepareR2(page, count = () => {}) {
  await take(page, '备用保险丝'); count('take fuse');
  await use(page, '保险丝', '电源箱'); count('use fuse');
  await inspect(page, '屏幕'); count('inspect powered monitor');
  await inspect(page, '抽屉'); count('inspect drawer');
}
async function toR3(page, count = () => {}) {
  await codeFrom(page, '抽屉', '屏幕读数', '抽屉顺序', /(青|橙|紫)色([0-9]+)/g); count('submit visible-clue drawer code');
  await take(page, '应急钥匙'); count('take key');
  await use(page, '应急钥匙', '出口控制室钥匙门'); count('use key');
  await move(page, '出口控制室'); count('move R3');
}
async function finish(page, count = () => {}) {
  await inspect(page, '出口检查单'); count('inspect checklist');
  await inspect(page, '检查面板'); count('inspect panel');
  await codeFrom(page, '检查面板', '设备标签', '出口检查顺序', /(冷却|通风|照明)对应([0-9]+)/g); count('submit visible-clue check code');
  await move(page, '实验室出口'); count('move EXIT');
  await expect(page.locator('.victory')).toContainText('成功逃离实验室');
}
async function confirm(page, operation) {
  await click(page, page.getByRole('button', { name: operation, exact: true }));
  await expect(page.getByRole('dialog')).toBeVisible();
  const confirmButton = page.getByRole('button', { name: operation === '恢复存档' ? '确认恢复' : '确认开始', exact: true });
  await confirmButton.focus();
  await confirmButton.press('Enter');
  await stable(page);
}
try {
  launch('backend', 'C:/Users/liyh/.conda/envs/1/python.exe', ['-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', String(backendPort), '--no-access-log'], environment);
  const frontendEnvironment = { ...environment, CAMPUS_BACKEND_URL: `http://127.0.0.1:${backendPort}` };
  delete frontendEnvironment.SQLITE_PATH;
  delete frontendEnvironment.AI_PROVIDER;
  launch('frontend', process.execPath, [resolve('node_modules/vite/bin/vite.js'), resolve('.'), '--host', '127.0.0.1', '--port', String(frontendPort), '--strictPort'], frontendEnvironment);
  await Promise.all([waitReady(`http://127.0.0.1:${backendPort}/api/health`), waitReady(`http://127.0.0.1:${frontendPort}/`)]);
  browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  for (const width of [1280, 768, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 900 } });
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`http://127.0.0.1:${frontendPort}/`);
    await click(page, page.getByRole('button', { name: '开始新游戏 →', exact: true }));
    await expect(page.getByRole('button', { name: '恢复存档', exact: true })).toBeDisabled();
    await layout(page, 'initial', width);
    const steps = [];
    const count = action => steps.push(action);
    await toR2(page, count);
    await prepareR2(page, count);
    await layout(page, 'r2', width);
    await toR3(page, count);
    await layout(page, 'r3', width);
    await finish(page, count);
    expect(steps).toHaveLength(18);
    await expect(page.locator('.clue-list li')).toHaveCount(6);
    await expect(page.locator('.inventory .use-button')).toHaveCount(0);
    await expect(page.getByRole('button', { name: '保存进度', exact: true })).toBeEnabled();
    await click(page, page.getByRole('button', { name: '查看背包', exact: true }));
    await click(page, page.getByRole('button', { name: '保存进度', exact: true }));
    await expect(page.locator('.save-summary')).toContainText('已有存档');
    await layout(page, 'won', width);
    check('18-step complete manual UI route; post-win inventory and save', { width, steps });
    if (width === 1280) {
      await confirm(page, '重新开始');
      await expect(page.locator('.scene .eyebrow')).toContainText('R1');
      await expect(page.locator('.clue-list li')).toHaveCount(0);
      await expect(page.locator('.history')).toHaveCount(0);
      await expect(page.locator('.save-summary')).toContainText('已有存档');
      await confirm(page, '恢复存档');
      await expect(page.locator('.victory')).toBeVisible();
      check('reset preserves winning save; restore returns to won');
      await confirm(page, '新游戏');
      await toR2(page);
      await inspect(page, '屏幕');
      await expect(page.locator('.observation')).toContainText('当前无显示');
      await expect(page.locator('.clue-list li')).toHaveCount(2);
      await prepareR2(page);
      await click(page, page.getByRole('button', { name: '保存进度', exact: true }));
      const savedText = await page.locator('.save-summary').textContent();
      await toR3(page);
      await object(page, '检查面板');
      await page.getByLabel('检查面板密码').fill('0');
      await confirm(page, '恢复存档');
      await expect(page.locator('.scene .eyebrow')).toContainText('R2');
      await expect(page.locator('.history')).toHaveCount(0);
      await expect(page.locator('.observation')).toHaveCount(0);
      await expect(page.locator('.save-summary')).toHaveText(savedText);
      await object(page, '抽屉');
      await expect(page.getByLabel('抽屉密码')).toHaveValue('');
      await page.reload();
      await click(page, page.locator('.top-actions').getByRole('button', { name: '继续当前游戏', exact: true }));
      await expect(page.locator('.scene .eyebrow')).toContainText('R2');
      await expect(page.locator('.save-summary')).toHaveText(savedText);
      check('R2 save, advance to R3, restore clears temporary input/history, refresh continues');
      await click(page, page.getByRole('button', { name: '重新开始', exact: true }));
      await expect(page.getByRole('dialog')).toContainText('已有存档仍可恢复');
      await expect(page.getByRole('button', { name: '取消', exact: true })).toBeFocused();
      await page.keyboard.press('Escape');
      await expect(page.getByRole('dialog')).not.toBeVisible();
      await expect(page.locator('.scene .eyebrow')).toContainText('R2');
      check('keyboard reset confirmation focuses cancel; Escape preserves progress');
      let resetRequests = 0;
      await object(page, '抽屉');
      await page.getByLabel('抽屉密码').fill('0');
      await page.route('**/reset', async route => { resetRequests++; await route.fetch(); await route.abort('failed'); });
      await confirm(page, '重新开始');
      await expect(page.locator('.scene .eyebrow')).toContainText('R1');
      await expect(page.locator('.notice')).toContainText('已同步服务器上的实际进度');
      await expect(page.locator('.save-summary')).toHaveText(savedText);
      expect(resetRequests).toBe(1);
      await page.unroute('**/reset');
      await confirm(page, '恢复存档');
      await object(page, '抽屉');
      await expect(page.getByLabel('抽屉密码')).toHaveValue('');
      check('lost reset response reconciles with GET without mutation resend; generation clears code');
      let restoreRequests = 0;
      await page.route('**/restore', async route => { restoreRequests++; await route.fetch(); await route.abort('failed'); });
      await page.route('**/state', route => route.abort('failed'));
      await confirm(page, '恢复存档');
      await expect(page.locator('.notice')).toContainText('尚未确认这次操作的结果');
      await expect(page.getByRole('button', { name: '保存进度', exact: true })).toBeDisabled();
      await expect(page.getByRole('button', { name: '重新开始', exact: true })).toBeDisabled();
      expect(restoreRequests).toBe(1);
      await page.unroute('**/restore');
      await page.unroute('**/state');
      await click(page, page.getByRole('button', { name: '同步进度', exact: true }));
      await expect(page.getByRole('button', { name: '保存进度', exact: true })).toBeEnabled();
      check('uncertain control and unavailable GET disables mutations until explicit successful sync');
      await object(page, '抽屉');
      await page.getByLabel('抽屉密码').fill('0');
      await page.getByLabel('抽屉密码').press('Enter');
      await stable(page);
      await expect(page.getByRole('alert')).toBeVisible();
      await expect(page.locator('.scene .eyebrow')).toContainText('R2');
      check('wrong drawer code renders error without progress');
      await expect(page.locator('.assistant')).toContainText('AI 探索伙伴');
    }
    await context.close();
  }
  expect(errors).toEqual([]);
  check('no browser runtime errors observed; no AI request initiated');
} catch (error) {
  errors.push(error.message);
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  const cleanup = [];
  for (const { name, child } of services.reverse()) {
    if (child.exitCode === null) child.kill();
    if (child.exitCode === null) await new Promise(done => child.once('exit', done));
    cleanup.push({ name, exit_code: child.exitCode, signal: child.signalCode, stopped: child.exitCode !== null || child.signalCode !== null });
  }
  const sourceAfter = await hashes();
  const sourceUnchanged = JSON.stringify(sourceBefore) === JSON.stringify(sourceAfter);
  if (!sourceUnchanged) { errors.push('Source changed during owner run; result is not a stable candidate check'); process.exitCode = 1; }
  await writeFile(resolve(output, 'result.json'), JSON.stringify({ scope: 'frontend owner local development; not independent QA or human playtest', provider: 'mock; no model calls', command: 'node scripts/owner-m2-smoke.mjs', source_before: sourceBefore, source_after: sourceAfter, source_unchanged: sourceUnchanged, checks, errors, cleanup, result: errors.length ? 'failed' : 'passed' }, null, 2));
  console.log(JSON.stringify({ passed: checks.length, errors, evidence: output, cleanup }));
}
