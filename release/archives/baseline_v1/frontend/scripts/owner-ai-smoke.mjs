// Owner development checks for T17. Independent acceptance belongs to QA.
// Browser faults below are explicitly local response/transport fixtures, not provider evidence.
import { chromium, expect } from '@playwright/test';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
import { spawn } from 'node:child_process';

const root = resolve('..');
const stamp = new Date().toISOString().replace(/[:.]/g, '-');
const output = resolve(root, 'evidence/frontend', `T17-owner-${stamp}`);
const temporary = resolve('node_modules/.cache', `owner-ai-${stamp}`);
await mkdir(output, { recursive: true }); await mkdir(temporary, { recursive: true });
const environment = Object.fromEntries(Object.entries(process.env).filter(([key]) => !/^(AI_|MODEL_|DEEPSEEK_|OPENAI_|ANTHROPIC_|VITE_)/i.test(key) && !/(TOKEN|SECRET|PASSWORD|CREDENTIAL|API_KEY|APIKEY)/i.test(key)));
Object.assign(environment, { AI_PROVIDER: 'mock', SQLITE_PATH: resolve(temporary, 'game.sqlite'), PYTHONIOENCODING: 'utf-8' });
const sourcePaths = ['frontend/scripts/owner-ai-smoke.mjs', 'frontend/src/App.tsx', 'frontend/src/Assistant.tsx', 'frontend/src/api.ts', 'frontend/src/style.css', 'backend/app/api/routes.py', 'backend/app/domain/rules.py', 'backend/app/storage/sqlite.py', 'backend/app/main.py', 'backend/app/ai/runtime.py', 'backend/app/ai/types.py', 'backend/app/ai/context.py', 'backend/app/ai/provider.py', 'backend/app/ai/mock.py', 'backend/app/ai/budget.py'];
async function hashes() { return Object.fromEntries(await Promise.all(sourcePaths.map(async path => [path, createHash('sha256').update(await readFile(resolve(root, path))).digest('hex')]))); }
const sourceBefore = await hashes();
const services = []; const checks = []; const errors = []; const requests = [];
let browser;
const check = (name, details = {}) => checks.push({ name, result: 'passed', ...details });
function launch(name, executable, args, env) { const child = spawn(executable, args, { cwd: root, env, stdio: 'ignore', windowsHide: true }); child.on('error', error => errors.push(`${name}: ${error.message}`)); services.push({ name, child }); }
async function ready(url) { const deadline = Date.now() + 25000; while (Date.now() < deadline) { try { if ((await fetch(url)).ok) return; } catch {} await new Promise(done => setTimeout(done, 150)); } throw new Error('Local service readiness timed out'); }
async function manualStable(page) { await expect(page.locator('.feedback .pending')).toHaveCount(0); }
async function aiStable(page) { await expect(page.locator('.ai-feedback .pending')).toHaveCount(0, { timeout: 60000 }); }
async function click(page, locator) { await locator.click(); await manualStable(page); }
async function ask(page, message = '下一步可以做什么？') { await page.getByLabel('想问探索伙伴什么？').fill(message); await page.getByRole('button', { name: '询问伙伴', exact: true }).click(); await aiStable(page); }
async function object(page, name) { await click(page, page.locator('.object-tile').filter({ hasText: name })); }
async function reset(page) { await click(page, page.getByRole('button', { name: '重新开始', exact: true })); await page.getByRole('button', { name: '确认开始', exact: true }).press('Enter'); await manualStable(page); }
async function restore(page) { await click(page, page.getByRole('button', { name: '恢复存档', exact: true })); await page.getByRole('button', { name: '确认恢复', exact: true }).press('Enter'); await manualStable(page); }
async function screenshot(page, stage, width) { expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false); await page.screenshot({ path: resolve(output, `${stage}-${width}.png`), fullPage: true }); check('no horizontal overflow', { stage, width }); }
async function proposal(page) { await expect(page.locator('.proposal-status')).toContainText('proposed'); await expect(page.getByRole('button', { name: '确认执行', exact: true })).toBeEnabled(); }
try {
  launch('backend', 'C:/Users/liyh/.conda/envs/1/python.exe', ['-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8117', '--no-access-log'], environment);
  const frontendEnvironment = { ...environment, CAMPUS_BACKEND_URL: 'http://127.0.0.1:8117' }; delete frontendEnvironment.SQLITE_PATH; delete frontendEnvironment.AI_PROVIDER;
  launch('frontend', process.execPath, [resolve('node_modules/vite/bin/vite.js'), resolve('.'), '--host', '127.0.0.1', '--port', '5117', '--strictPort'], frontendEnvironment);
  await Promise.all([ready('http://127.0.0.1:8117/api/health'), ready('http://127.0.0.1:5117/')]);
  browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  for (const width of [1280, 768, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 900 } }); const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => { const path = new URL(request.url()).pathname; if (/\/proposals\/[^/]+\/(confirm|cancel)$/.test(path)) { const body = request.postDataJSON(); expect(body).toEqual({}); requests.push({ operation: path.endsWith('/confirm') ? 'confirm' : 'cancel', body }); } });
    await page.goto('http://127.0.0.1:5117/'); await click(page, page.getByRole('button', { name: '开始新游戏 →', exact: true }));
    await expect(page.getByLabel('想问探索伙伴什么？')).toHaveAttribute('maxlength', '2000');
    await expect(page.getByRole('button', { name: '询问伙伴', exact: true })).toBeDisabled();
    await ask(page); await proposal(page); await expect(page.locator('.clue-list li')).toHaveCount(2);
    await expect(page.locator('.provider-badge')).toContainText('开发模拟');
    await expect(page.locator('.proposal-parameters input')).toHaveCount(0);
    await page.locator('.usage summary').click(); await expect(page.locator('.usage')).toContainText('输入 token：未提供'); await expect(page.locator('.usage')).toContainText('服务调用尝试');
    const refs = page.locator('.ai-answer .ai-references a'); expect(await refs.count()).toBeGreaterThan(0);
    const href = await refs.first().getAttribute('href'); await refs.first().focus(); await page.keyboard.press('Enter'); await expect(page.locator(href)).toBeVisible(); await expect(page.locator(href)).toBeFocused();
    await screenshot(page, 'proposed', width);
    await page.getByRole('button', { name: '取消建议', exact: true }).focus(); await page.keyboard.press('Enter'); await aiStable(page);
    await expect(page.locator('.proposal-status')).toContainText('cancelled'); await expect(page.locator('.committed-receipt')).toHaveCount(0);
    await expect(page.locator('.object-tile').filter({ hasText: '门卡' })).toHaveCount(0);
    check('mock actual clue references keyboard reachable, readonly fixed proposal, keyboard cancel without progression', { width });
    await ask(page); await proposal(page);
    const confirmed = page.waitForResponse(response => /\/confirm$/.test(new URL(response.url()).pathname));
    await page.getByRole('button', { name: '确认执行', exact: true }).focus(); await page.keyboard.press('Enter'); await aiStable(page);
    const confirmedData = (await (await confirmed).json()).data;
    await expect(page.locator('.proposal-status')).toContainText('committed'); await expect(page.locator('.committed-receipt')).toContainText(confirmedData.receipt.message);
    await expect(page.getByRole('button', { name: '确认执行', exact: true })).toBeDisabled();
    await expect(page.locator('.object-tile').filter({ hasText: '门卡' })).toBeVisible();
    await page.locator('.ai-trace summary').click(); await expect(page.locator('.ai-trace')).toContainText(confirmedData.receipt.event_id);
    await screenshot(page, 'committed', width);
    check('new mock proposal confirmed by keyboard; real receipt only; repeated UI confirm disabled', { width, receipt_revision_before: confirmedData.receipt.revision_before, receipt_revision_after: confirmedData.receipt.revision_after });
    if (width === 1280) {
      await click(page, page.getByRole('button', { name: '保存进度', exact: true }));
      await ask(page); await proposal(page);
      await object(page, '门卡'); await click(page, page.locator('.object-actions').getByRole('button', { name: '拾取', exact: false }));
      await expect(page.locator('.proposal-status')).toContainText('已失效'); await expect(page.getByRole('button', { name: '确认执行', exact: true })).toBeDisabled();
      await expect(page.locator('.proposal-parameters')).toHaveCount(0);
      await ask(page); await proposal(page); await restore(page);
      await expect(page.locator('.proposal-card')).toHaveCount(0); await expect(page.locator('.ai-answer')).toHaveCount(0); await expect(page.getByLabel('想问探索伙伴什么？')).toHaveValue('');
      check('manual revision invalidates pending proposal; restore generation clears assistant and question');
      await ask(page); await proposal(page);
      const siblingReady = context.waitForEvent('page'); await page.evaluate(() => window.open(location.href, 'owner-peer')); const peer = await siblingReady;
      await peer.waitForLoadState('domcontentloaded'); await click(peer, peer.locator('.top-actions').getByRole('button', { name: '继续当前游戏', exact: true }));
      await object(peer, '门卡'); await click(peer, peer.locator('.object-actions').getByRole('button', { name: '拾取', exact: false }));
      await page.getByRole('button', { name: '确认执行', exact: true }).click(); await aiStable(page);
      await expect(page.locator('.ai-feedback [role=alert]')).toBeVisible(); await expect(page.getByRole('button', { name: '确认执行', exact: true })).toBeDisabled();
      await expect(page.locator('.inventory-item')).toContainText('门卡'); await peer.close();
      check('another UI client changes version; server rejects stale confirmation and current state remains');
      let delayed = 0;
      await page.route('**/ai/turns', async route => { const response = await route.fetch(); delayed++; await new Promise(done => setTimeout(done, 16000)); await route.fulfill({ response }); });
      const started = Date.now(); await page.getByLabel('想问探索伙伴什么？').fill('下一步可以做什么？'); await page.getByRole('button', { name: '询问伙伴', exact: true }).click();
      await expect(page.locator('.ai-feedback .pending')).toBeVisible(); await expect(page.getByRole('button', { name: '查看背包', exact: true })).toBeEnabled();
      await click(page, page.getByRole('button', { name: '查看背包', exact: true })); await aiStable(page); await proposal(page);
      expect(Date.now() - started).toBeGreaterThanOrEqual(16000); expect(delayed).toBe(1); await page.unroute('**/ai/turns');
      await page.getByRole('button', { name: '取消建议', exact: true }).click(); await aiStable(page);
      check('AI response delayed beyond 15s succeeds; manual inventory remains usable', { delay_ms: 16000, fixture: 'local transport delay; actual backend mock response' });
      let release; const gate = new Promise(done => { release = done; }); let fetched; const fetchedReady = new Promise(done => { fetched = done; });
      await page.route('**/ai/turns', async route => { const response = await route.fetch(); fetched(); await gate; await route.fulfill({ response }); });
      await page.getByLabel('想问探索伙伴什么？').fill('下一步可以做什么？'); await page.getByRole('button', { name: '询问伙伴', exact: true }).click(); await fetchedReady; await reset(page); release(); await aiStable(page); await page.unroute('**/ai/turns');
      await expect(page.locator('.clue-list li')).toHaveCount(0); await expect(page.locator('.scene .eyebrow')).toContainText('R1'); await expect(page.locator('.proposal-card')).toHaveCount(0); await expect(page.locator('.ai-answer')).toHaveCount(0);
      check('delayed AI response from retired generation cannot overwrite reset state', { fixture: 'local transport gate around actual backend response' });
      let releaseOlder; const olderGate = new Promise(done => { releaseOlder = done; }); let olderFetched; const olderReady = new Promise(done => { olderFetched = done; }); let olderRevision;
      await page.route('**/ai/turns', async route => { const response = await route.fetch(); const value = await response.json(); olderRevision = value.data.visible_state.revision; olderFetched(); await olderGate; await route.fulfill({ response }); });
      await page.getByLabel('想问探索伙伴什么？').fill('下一步可以做什么？'); await page.getByRole('button', { name: '询问伙伴', exact: true }).click(); await olderReady;
      await click(page, page.getByRole('button', { name: '同步进度', exact: true }));
      const mapping = await page.locator('.clue-list li').filter({ has: page.getByRole('heading', { name: '值班便签', exact: true }) }).innerText();
      const order = await page.locator('.clue-list li').filter({ has: page.getByRole('heading', { name: '柜门顺序', exact: true }) }).innerText();
      const values = new Map([...mapping.matchAll(/(三角|圆|方)记为([0-9]+)/g)].map(match => [match[1], match[2]]));
      const digits = (order.match(/三角|圆|方/g) || []).map(symbol => values.get(symbol)).join(''); expect(digits).toMatch(/^[0-9]{1,16}$/);
      await object(page, '值班柜'); await page.getByLabel('值班柜密码').fill(digits); await page.getByLabel('值班柜密码').press('Enter'); await manualStable(page);
      await expect(page.locator('.object-tile').filter({ hasText: '门卡' })).toBeVisible(); releaseOlder(); await aiStable(page); await page.unroute('**/ai/turns');
      await expect(page.locator('.object-tile').filter({ hasText: '门卡' })).toBeVisible(); await expect(page.locator('.proposal-card')).toHaveCount(0); await expect(page.locator('.ai-answer')).toHaveCount(0); await expect(page.locator('.ai-feedback .notice')).toContainText('较早');
      check('lower revision delayed AI projection cannot overwrite actual manual cabinet progress', { returned_revision: olderRevision, fixture: 'local transport gate; both projections are actual backend states' });
      await reset(page);
      await page.route('**/ai/turns', async route => { const response = await route.fetch(); const value = await response.json(); Object.assign(value.data, { status: 'stopped', stop_reason: 'MODEL_TIMEOUT', proposal: null, answer: '本地界面模拟：已停止本次问答。' }); await route.fulfill({ response, json: value }); });
      await ask(page); await page.unroute('**/ai/turns'); await expect(page.locator('.ai-status')).toContainText('已停止'); await expect(page.locator('.stop-reason')).toContainText('时间内'); await expect(page.locator('.clue-list li')).toHaveCount(2);
      check('stopped status/reason rendered and actual newly discovered clues retained', { fixture: 'local browser response injection, not provider timeout' });
      await page.route('**/ai/turns', async route => { const response = await route.fetch(); const value = await response.json(); value.data.clue_refs = ['owner_unknown_reference']; await route.fulfill({ response, json: value }); });
      await ask(page); await page.unroute('**/ai/turns'); await expect(page.locator('.ai-feedback [role=alert]')).toContainText('无法核对'); await expect(page.locator('.proposal-card')).toHaveCount(0);
      check('unknown clue references refused without losing game', { fixture: 'local malformed response injection' });
      await ask(page); await proposal(page);
      await page.route('**/confirm', async route => { const response = await route.fetch(); const value = await response.json(); const projection = value.data.visible_state; await route.fulfill({ status: 409, json: { ok: false, event_id: value.event_id, error: { code: 'PROPOSAL_REJECTED', message: '本地界面模拟：建议被拒绝。' }, visible_state: projection } }); });
      await page.getByRole('button', { name: '确认执行', exact: true }).click(); await aiStable(page); await page.unroute('**/confirm');
      await expect(page.locator('.proposal-status')).toContainText('rejected'); await expect(page.locator('.committed-receipt')).toHaveCount(0);
      check('rejected display never invents committed receipt', { fixture: 'local browser response injection after actual confirm; not server rejection evidence' });
      await reset(page); await ask(page); await proposal(page);
      await page.clock.install(); await page.clock.fastForward(121000); await expect(page.locator('.proposal-status')).toContainText('已过期'); await expect(page.getByRole('button', { name: '确认执行', exact: true })).toBeDisabled(); await page.clock.resume();
      check('client expiry blocks confirm', { fixture: 'local browser clock acceleration; server TTL owned by QA' });
      await page.evaluate(() => { window.ownerOriginalTimeout = window.setTimeout; window.setTimeout = function(callback, delay, ...args) { if (delay === 55000) { window.ownerAiBudget = delay; return window.ownerOriginalTimeout(callback, 50, ...args); } return window.ownerOriginalTimeout(callback, delay, ...args); }; });
      await page.route('**/ai/turns', async route => { await new Promise(done => setTimeout(done, 250)); try { await route.abort('timedout'); } catch {} });
      await ask(page); await page.unroute('**/ai/turns'); expect(await page.evaluate(() => window.ownerAiBudget)).toBe(55000);
      await page.evaluate(() => { window.setTimeout = window.ownerOriginalTimeout; });
      await expect(page.locator('.ai-feedback [role=alert]')).toBeVisible(); await expect(page.locator('.ai-feedback .notice')).toContainText('已同步实际进度'); await expect(page.locator('.clue-list li')).toHaveCount(2);
      check('dedicated 55s AI timer registered; locally accelerated abort reconciles without resend', { fixture: 'local timeout acceleration and network hold, not real model timeout' });
    }
    await context.close();
  }
  expect(errors).toEqual([]); check('no page runtime errors; request bodies for every confirm/cancel exactly empty object', { confirmation_requests: requests.length });
} catch (error) { errors.push(error.message); process.exitCode = 1; }
finally {
  if (browser) await browser.close(); const cleanup = [];
  for (const { name, child } of services.reverse()) { if (child.exitCode === null) child.kill(); if (child.exitCode === null) await new Promise(done => child.once('exit', done)); cleanup.push({ name, exit_code: child.exitCode, signal: child.signalCode, stopped: child.exitCode !== null || child.signalCode !== null }); }
  const sourceAfter = await hashes(); const sourceUnchanged = JSON.stringify(sourceBefore) === JSON.stringify(sourceAfter);
  if (!sourceUnchanged) { errors.push('Source changed during owner check'); process.exitCode = 1; }
  await writeFile(resolve(output, 'result.json'), JSON.stringify({ scope: 'frontend owner development, not independent QA/human playtest/real AI acceptance', provider: 'mock', command: 'node scripts/owner-ai-smoke.mjs', source_before: sourceBefore, source_after: sourceAfter, source_unchanged: sourceUnchanged, checks, errors, confirm_cancel_requests: requests, cleanup, result: errors.length ? 'failed' : 'passed' }, null, 2));
  console.log(JSON.stringify({ passed: checks.length, errors, evidence: output, cleanup }));
}
