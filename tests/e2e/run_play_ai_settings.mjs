// Independent focused browser acceptance. Explicitly synthetic credentials only.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const { chromium, expect } = createRequire(path.join(root, 'frontend/package.json'))('@playwright/test');
const candidate = process.argv[2];
assert(candidate, 'Main SOURCE STOP candidate required');
const folder = path.join(root, 'evidence/qa/play-ai-settings-20261006', 'browser-' + new Date().toISOString().replace(/[-:.]/g, ''));
fs.mkdirSync(folder, { recursive: true });
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'play-ai-browser-qa-'));
const python = 'C:\\Users\\liyh\\.conda\\envs\\1\\python.exe';
const backendURL = 'http://127.0.0.1:18146', frontendURL = 'http://127.0.0.1:15146';
const key = 'SYNTHETIC_BROWSER_QA_NOT_A_REAL_API_KEY';
const children = [], checks = [], issues = [], requests = [];
const source = ['backend/app/api/routes.py', 'backend/app/ai/runtime.py', 'frontend/src/Assistant.tsx', 'frontend/src/api.ts', 'frontend/src/style.css'];
const hashes = () => Object.fromEntries(source.map(f => [f, crypto.createHash('sha256').update(fs.readFileSync(path.join(root, f))).digest('hex')]));
const before = hashes();
function start(exe, args, env, cwd = root) {
  const child = spawn(exe, args, { cwd, env: { ...process.env, AI_PROVIDER: 'mock', PYTHONUTF8: '1', ...env }, windowsHide: true, stdio: ['ignore', 'ignore', 'ignore'] });
  children.push(child); child.on('error', () => issues.push('Owned loopback process failed to start'));
}
async function ready(url) {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) { try { if ((await fetch(url)).ok) return; } catch {} await new Promise(r => setTimeout(r, 100)); }
  throw new Error('Owned loopback service did not become ready');
}
async function post(page, suffix, action) {
  const waited = page.waitForResponse(r => new URL(r.url()).pathname.endsWith(suffix) && r.request().method() === 'POST');
  await action(); const r = await waited;
  assert.equal(r.status(), 200, 'Expected operation rejected');
  const value = await r.json(); assert(!JSON.stringify(value).includes(key), 'Credential in response'); return value;
}
async function layout(page, stage) {
  const data = await page.evaluate(() => ({ viewport: innerWidth, width: document.documentElement.scrollWidth,
    controls: [...document.querySelectorAll('.assistant input,.assistant button,.assistant textarea')].filter(e => e.getClientRects().length).map(e => { const r = e.getBoundingClientRect(); return { left: r.left, right: r.right, width: r.width }; }) }));
  assert(data.width <= data.viewport + 1, 'Horizontal document overflow');
  assert(data.controls.every(r => r.left >= -1 && r.right <= data.viewport + 1 && r.width > 0), 'Assistant control overflow');
  checks.push({ stage, ...data });
  await page.screenshot({ path: path.join(folder, stage + '.png'), fullPage: true });
}
async function storage(page) {
  const clean = await page.evaluate(sentinel => {
    const values = [...Object.values(localStorage), ...Object.values(sessionStorage), document.cookie];
    return values.every(value => !value.includes(sentinel));
  }, key);
  assert(clean, 'Credential persisted in browser storage/cookie');
}
let browser;
try {
  const executablePath = ['C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'].find(p => fs.existsSync(p));
  assert(executablePath, 'Installed Chromium browser required');
  start(python, ['-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '18146', '--no-access-log'], { SQLITE_PATH: path.join(temp, 'game.sqlite') });
  start(process.execPath, [path.join(root, 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '15146', '--strictPort'], { CAMPUS_BACKEND_URL: backendURL }, path.join(root, 'frontend'));
  await Promise.all([ready(backendURL + '/api/health'), ready(frontendURL)]);
  browser = await chromium.launch({ headless: true, executablePath });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage(); let realIntercepts = 0, realRequest = null;
  page.on('pageerror', () => issues.push('Uncaught browser exception'));
  // Block all non-loopback requests, including any external provider calls.
  await context.route('**/*', async route => {
    const req = route.request(), url = new URL(req.url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
    if (url.pathname.startsWith('/api/')) {
      const headers = req.headers(), isAi = url.pathname.endsWith('/ai/turns');
      const record = { path: url.pathname.replace(/sessions\/[^/]+/, 'sessions/<redacted-session>'), method: req.method(), provider: headers['x-ai-provider'] || null,
        keyPresent: !!headers['x-ai-api-key'], syntheticKeyMatches: headers['x-ai-api-key'] === key, bodyHasKey: (req.postData() || '').includes(key), isAi };
      requests.push(record);
      assert(!record.bodyHasKey, 'Credential entered request body');
      if (!isAi) assert(!record.keyPresent && !record.provider, 'AI headers on non-AI request');
      if (isAi && record.provider === 'deepseek') {
        assert(record.syntheticKeyMatches, 'Request credential mismatch');
        realIntercepts++; realRequest = req.postDataJSON();
        // Real branch never reaches backend/provider. Current state supplies a valid UI envelope.
        const stateRequest = await route.fetch({ url: req.url().replace(/\/ai\/turns$/, '/state'), method: 'GET', postData: undefined, headers: { 'X-Session-Token': headers['x-session-token'] } });
        const current = (await stateRequest.json()).data.visible_state;
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, event_id: crypto.randomUUID(), data: {
          turn_id: crypto.randomUUID(), answer: '浏览器离线拦截结果：继续观察。', clue_refs: [], proposal: null, status: 'no_suggestion', stop_reason: null,
          usage: { provider: 'deepseek', model: 'deepseek-flash', input_tokens: 11, output_tokens: 7, model_calls: 1, read_tool_calls: 0 }, visible_state: current } }) });
      }
    }
    await route.continue();
  });
  await page.goto(frontendURL, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: '开始新游戏 →', exact: true }).click();
  await expect(page.locator('#room-title')).toHaveText('值班室');
  const mock = page.getByRole('radio', { name: /免费模拟/ }), real = page.getByRole('radio', { name: /真实 DeepSeek/ });
  const input = page.getByLabel('DeepSeek API Key', { exact: true }), ask = page.getByRole('button', { name: '询问伙伴', exact: true });
  const question = page.getByLabel('想问探索伙伴什么？', { exact: true });
  await expect(mock).toBeChecked(); await expect(input).toHaveCount(0);
  await question.fill('请给下一步建议');
  await real.check(); await expect(input).toHaveAttribute('type', 'password'); await expect(ask).toBeDisabled();
  assert.equal(requests.filter(r => r.isAi).length, 0, 'Selecting real issued AI call');
  await layout(page, 'desktop-real-missing-key');
  await input.fill(key); await storage(page); await expect(ask).toBeEnabled();
  await page.getByRole('button', { name: '清除密钥', exact: true }).click(); await expect(input).toHaveValue(''); await expect(ask).toBeDisabled();
  await input.fill(key); await mock.check(); await expect(input).toHaveCount(0); await real.check(); await expect(input).toHaveValue('');
  assert.equal(requests.filter(r => r.isAi).length, 0, 'Editing/clearing modes issued AI call');
  await input.fill(key); await storage(page); await layout(page, 'desktop-real-synthetic-password');
  await post(page, '/save', () => page.getByRole('button', { name: '保存进度', exact: true }).click());
  await post(page, '/actions', () => page.getByRole('button', { name: '查看背包', exact: true }).click());
  await expect(input).toHaveValue(key);
  await post(page, '/reset', async () => {
    await page.getByRole('button', { name: '重新开始', exact: true }).click();
    await page.getByRole('dialog').getByRole('button', { name: '确认开始', exact: true }).click();
  });
  await expect(mock).toBeChecked(); await real.check(); await expect(input).toHaveValue(''); await input.fill(key);
  await post(page, '/restore', async () => {
    await page.getByRole('button', { name: '恢复存档', exact: true }).click();
    await page.getByRole('dialog').getByRole('button', { name: '确认恢复', exact: true }).click();
  });
  await expect(mock).toBeChecked(); await real.check(); await expect(input).toHaveValue(''); await input.fill(key);
  await question.fill('请给下一步建议');
  await post(page, '/ai/turns', () => ask.click());
  assert.equal(realIntercepts, 1); assert.deepEqual(Object.keys(realRequest).sort(), ['generation', 'message', 'request_id', 'revision']);
  await expect(page.locator('.provider-badge')).toHaveText('本次回答：真实 DeepSeek');
  await mock.check(); await expect(page.locator('.provider-badge')).toHaveText('本次回答：真实 DeepSeek');
  await storage(page); await real.check(); await expect(input).toHaveValue(''); await input.fill(key);
  await page.reload({ waitUntil: 'networkidle' });
  await expect(page.getByRole('heading', { name: '从这里开始探索', exact: true })).toBeVisible();
  await page.locator('.welcome-buttons').getByRole('button', { name: '继续当前游戏', exact: true }).click();
  await expect(mock).toBeChecked(); await expect(input).toHaveCount(0); await real.check(); await expect(input).toHaveValue('');
  await input.fill(key); await page.getByRole('button', { name: '新游戏', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: '确认开始', exact: true }).click();
  await expect(mock).toBeChecked(); await real.check(); await expect(input).toHaveValue(''); await storage(page);
  await mock.check(); await question.fill('请根据已发现线索建议下一步');
  const result = await post(page, '/ai/turns', () => ask.click());
  assert.equal(result.data.usage.provider, 'mock'); assert.equal(requests.filter(r => r.isAi && r.provider === 'mock').length, 1);
  assert.equal(requests.filter(r => r.isAi && r.provider === 'mock' && r.keyPresent).length, 0);
  await expect(page.locator('.provider-badge')).toHaveText('本次回答：免费模拟');
  await expect(page.locator('.proposal-card')).toBeVisible();
  await post(page, '/cancel', () => page.getByRole('button', { name: '取消建议', exact: true }).click());
  await expect(page.locator('.proposal-status')).toContainText('cancelled');
  await question.fill('请建议下一步'); await post(page, '/ai/turns', () => ask.click());
  await post(page, '/confirm', () => page.getByRole('button', { name: '确认执行', exact: true }).click());
  await expect(page.locator('.committed-receipt')).toBeVisible();
  await page.locator('.object-grid').getByRole('button', { name: /值班便签/ }).click();
  await post(page, '/actions', () => page.locator('.object-details').getByRole('button', { name: /查看/ }).click());
  await layout(page, 'desktop-mock-proposal-and-manual');
  await page.setViewportSize({ width: 1280, height: 900 }); await real.check(); await input.fill(key); await layout(page, 'desktop-real-synthetic-password');
  await storage(page);
  const dbScan = spawnSync(python, ['-c', 'import pathlib,sqlite3,sys; p=pathlib.Path(sys.argv[1]); c=sqlite3.connect(p); s=sys.argv[2]; clean=s not in "\\n".join(c.iterdump()) and all(s.encode() not in f.read_bytes() for f in p.parent.glob("game.sqlite*")); c.close(); print("clean" if clean else "found"); sys.exit(0 if clean else 1)', path.join(temp, 'game.sqlite'), key], { windowsHide: true, encoding: 'utf8' });
  assert.equal(dbScan.status, 0, 'Synthetic browser credential entered owned game DB/save');
  checks.push({ stage: 'functional', passed: true, realIntercepts, paidCalls: 0, realProviderEvidence: false,
    assertions: ['default mock', 'missing-key blocked', 'password', 'clear', 'mock clears key', 'refresh clears key', 'new session clears key', 'reset clears key', 'restore clears key', 'storage clean', 'owned DB/save clean', 'AI-only headers', 'only ask calls', 'historical badge stable', 'body unchanged', 'mock proposal cancel and confirm', 'manual action preserved'] });
  await context.close();
} catch (error) { issues.push(error.message); }
finally {
  if (browser) await browser.close();
  for (const child of children) if (child.pid) spawnSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
  const resolved = fs.realpathSync(temp), tempRoot = fs.realpathSync(os.tmpdir());
  assert.equal(path.dirname(resolved).toLowerCase(), tempRoot.toLowerCase()); assert(path.basename(resolved).startsWith('play-ai-browser-qa-'));
  fs.rmSync(resolved, { recursive: true });
  const after = hashes(); if (JSON.stringify(before) !== JSON.stringify(after)) issues.push('SOURCE STOP files changed during browser QA');
  const run = { candidate, command: [process.execPath, ...process.argv.slice(1)], checks, issues, requests,
    source_sha256_before: before, source_sha256_after: after, exit_code: issues.length ? 1 : 0,
    limitation: 'DeepSeek branch is browser interception plus separate Python offline adapter tests; no real provider response or paid network call.',
    privacy: 'No session tokens, full request headers, raw server logs, HAR, or databases retained. Screenshots use password input with synthetic sentinel only.' };
  fs.writeFileSync(path.join(folder, 'run.json'), JSON.stringify(run, null, 2));
  console.log(JSON.stringify({ evidence: folder, checks: checks.map(c => c.stage), issues, exit_code: run.exit_code }, null, 2)); process.exitCode = run.exit_code;
}
