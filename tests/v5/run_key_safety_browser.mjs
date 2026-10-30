// Synthetic-only temporary API-key lifecycle check. Browser traffic is routed
// to this run's owned 8002 fixture; no real provider or player database is used.
import fs from 'node:fs/promises';
import fsSync from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import http from 'node:http';
import net from 'node:net';
import {spawn, execFileSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {randomUUID} from 'node:crypto';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const base = 'http://127.0.0.1:8001';
const stageRoot = path.join(root, 'evidence/project/stages/v5-key-safety/automated');
const started = new Date().toISOString(), runId = randomUUID();
const out = path.join(stageRoot, `browser-${started.replace(/[:.]/g, '-')}-${runId.slice(0, 8)}`);
const canaryId = 'KEY-CANARY-01';
const canary = `SYNTH-${randomUUID()}-ONLY`;
const accountA = {username: 'keysafety_alpha', password: 'Synthetic-Key-A!23456'};
const accountB = {username: 'keysafety_beta', password: 'Synthetic-Key-B!23456'};
const records = [], screenshots = [], issues = [];
const exposure = {url: 0, body: 0, non_allowed_request_headers: 0, ordinary_response: 0, local_storage: 0, session_storage: 0, allowed_key_header: 0, target_generation_posts: 0, external_requests: 0};
let server = null, browser = null, context = null, tempRoot = null, serverStopped = true;
let injectNextGenerationFailure = false;
let phase = 'setup';
const pendingResponseScans = new Set();
let checkedResponseCount = 0, unreadResponseCount = 0, gitHead = null, loadedScriptFiles = [];

const check = (name, actual, expected, pass, scope = 'key-safety') => {
  const row = {name, actual, expected, pass: !!pass, scope, observed_at_utc: new Date().toISOString()};
  records.push(row);
  fsSync.appendFileSync(path.join(out, 'records.jsonl'), JSON.stringify(row) + '\n', 'utf8');
};
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const includesCanary = value => typeof value === 'string' && value.includes(canary);

async function requestHealth() {
  return new Promise(resolve => {
    const req = http.get({hostname: '127.0.0.1', port: 8002, path: '/health', headers: {host: '127.0.0.1:8001'}}, response => { response.resume(); resolve(response.statusCode === 200); });
    req.on('error', () => resolve(false)); req.setTimeout(700, () => req.destroy());
  });
}

async function startFixture() {
  const probe = net.createServer();
  await new Promise((resolve, reject) => { probe.once('error', reject); probe.listen(8002, '127.0.0.1', () => probe.close(resolve)); });
  tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'campus-experience-key-safety-'));
  server = spawn('C:/Users/liyh/.conda/envs/1/python.exe', ['-B', '-X', 'utf8', '-m', 'uvicorn', 'tests.v5.experience_fixture_server:app', '--host', '127.0.0.1', '--port', '8002', '--no-access-log'], {
    cwd: root,
    env: {...process.env, SQLITE_PATH: path.join(tempRoot, 'game-v5.sqlite'), GAMEPLAY_VERSION: 'v5', AI_PROVIDER: 'mock', PYTHONDONTWRITEBYTECODE: '1'},
    stdio: 'ignore', windowsHide: true,
  });
  for (let i = 0; i < 100; i++) { if (await requestHealth()) return; if (server.exitCode !== null) break; await pause(100); }
  throw Error('owned synthetic fixture not ready');
}

async function storageScan(page) {
  return page.evaluate(secret => ({
    local: Object.values(localStorage).some(value => value.includes(secret)),
    session: Object.values(sessionStorage).some(value => value.includes(secret)),
  }), canary);
}

async function waitForResponseScans() {
  while (pendingResponseScans.size) await Promise.all([...pendingResponseScans]);
}

async function waitDashboard(page, username) {
  await page.getByRole('heading', {name: '我的关卡', exact: true}).waitFor();
  await page.locator('.v5-account').filter({hasText: username}).waitFor();
  await page.getByLabel(/本次生成的 DeepSeek API Key/).waitFor();
}

async function registerOrLogin(page, account, register) {
  if (register) await page.getByRole('button', {name: '第一次来？注册本地账户', exact: true}).click();
  if (register) await page.getByLabel('用户名（3–24位字母、数字或下划线）', {exact: true}).fill(account.username);
  else await page.locator('.v5-auth-panel select').first().selectOption(account.username);
  await page.getByLabel('密码（12–128位）', {exact: true}).fill(account.password);
  await page.getByRole('button', {name: register ? '注册并进入' : '登录', exact: true}).click();
  await waitDashboard(page, account.username);
}

async function run() {
  await startFixture();
  const {chromium} = createRequire(path.join(root, 'frontend/package.json'))('@playwright/test');
  browser = await chromium.launch({headless: true, channel: 'chrome'});
  context = await browser.newContext({viewport: {width: 1280, height: 720}});
  await context.route('**/*', async route => {
    const request = route.request(), url = new URL(request.url()), headers = request.headers();
    if (['data:', 'blob:'].includes(url.protocol)) return route.continue();
    if (url.origin !== base) { exposure.external_requests++; return route.abort(); }

    const pathname = url.pathname;
    const isGeneration = request.method() === 'POST' && pathname === '/api/v2/level-generations';
    const body = request.postData() || '';
    if (includesCanary(request.url())) exposure.url++;
    if (includesCanary(body)) exposure.body++;
    for (const [name, value] of Object.entries(headers)) {
      if (!includesCanary(value)) continue;
      if (isGeneration && name.toLowerCase() === 'x-ai-api-key') exposure.allowed_key_header++;
      else exposure.non_allowed_request_headers++;
    }
    if (isGeneration) exposure.target_generation_posts++;

    if (isGeneration && injectNextGenerationFailure) {
      injectNextGenerationFailure = false;
      return route.fulfill({status: 503, contentType: 'application/json', body: JSON.stringify({ok: false, error: {code: 'MODEL_UNAVAILABLE', message: 'Synthetic controlled failure'}})});
    }
    try {
      const response = await route.fetch({url: request.url().replace(base, 'http://127.0.0.1:8002'), headers: {...headers, host: '127.0.0.1:8001'}});
      return route.fulfill({response});
    } catch {
      return route.abort().catch(() => {});
    }
  });

  const pages = [];
  const attachObservers = page => {
    pages.push(page);
    page.on('response', response => {
      if (!new URL(response.url()).pathname.startsWith('/api/v2/')) return;
      const scan = (async () => {
        try { if (includesCanary(await response.text())) exposure.ordinary_response++; }
        catch { unreadResponseCount++; }
        finally { checkedResponseCount++; }
      })();
      pendingResponseScans.add(scan);
      scan.finally(() => pendingResponseScans.delete(scan));
    });
  };
  const page = await context.newPage(); attachObservers(page); page.setDefaultTimeout(15000);
  phase = 'load-and-register-alpha';
  gitHead = execFileSync('git', ['rev-parse', 'HEAD'], {cwd: root, encoding: 'utf8', windowsHide: true}).trim();
  await page.goto(base);
  loadedScriptFiles = await page.evaluate(() => [...document.scripts].map(script => script.src ? new URL(script.src, location.href).pathname.split('/').pop() : null).filter(Boolean));
  await page.getByRole('heading', {name: '欢迎回来', exact: true}).waitFor();
  await registerOrLogin(page, accountA, true);
  phase = 'configure-synthetic-generation';
  await page.locator('.v5-generator select').first().selectOption('图书馆档案');
  await page.getByLabel(/^房间数量/).selectOption('1');
  await page.getByLabel(/^难度/).selectOption('hard');
  const keyInput = page.getByLabel(/本次生成的 DeepSeek API Key/);
  const generate = page.locator('.v5-generator button.v5-primary');

  await keyInput.fill('');
  phase = 'empty-key-block';
  await page.waitForFunction(() => {
    const shell = document.querySelector('.v5-shell');
    const button = document.querySelector('.v5-generator button.v5-primary');
    return shell?.getAttribute('aria-busy') !== 'true' && button && !button.disabled;
  });
  check('generator is enabled after login refresh settles', {count: await generate.count(), disabled: await generate.isDisabled(), theme: await page.locator('.v5-generator select').first().inputValue(), room_count: await page.locator('.v5-generator select').nth(1).inputValue(), difficulty: await page.locator('.v5-generator select').nth(2).inputValue()}, {count: 1, disabled: false, room_count: '1', difficulty: 'hard'}, await generate.count() === 1 && !await generate.isDisabled() && await page.locator('.v5-generator select').nth(1).inputValue() === '1' && await page.locator('.v5-generator select').nth(2).inputValue() === 'hard');
  const postsBeforeEmpty = exposure.target_generation_posts;
  await generate.click();
  await page.getByRole('alert').waitFor();
  check('empty key blocks generation before request', {generation_posts_delta: exposure.target_generation_posts - postsBeforeEmpty, key_empty: await keyInput.inputValue() === ''}, {generation_posts_delta: 0, key_empty: true}, exposure.target_generation_posts === postsBeforeEmpty && await keyInput.inputValue() === '');

  injectNextGenerationFailure = true;
  phase = 'controlled-failure';
  await keyInput.fill(canary);
  const preSubmitStorage = await storageScan(page);
  const failedResponse = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname === '/api/v2/level-generations');
  await generate.click();
  const failed = await failedResponse;
  await page.waitForFunction(() => {
    const input = document.querySelector('.v5-generator input[type="password"]');
    const alert = document.querySelector('[role="alert"]');
    return input?.value === '' && alert?.textContent?.includes('Synthetic controlled failure');
  });
  check('key cleared after controlled API failure', {http_status: failed.status(), empty: await keyInput.inputValue() === '', alert_has_no_canary: !includesCanary(await page.getByRole('alert').innerText())}, {http_status: 503, empty: true, alert_has_no_canary: true}, failed.status() === 503 && await keyInput.inputValue() === '' && !includesCanary(await page.getByRole('alert').innerText()), 'controlled-failure');
  await page.screenshot({path: path.join(out, 'after-failure-key-cleared.png')}); screenshots.push('after-failure-key-cleared.png');

  await keyInput.fill(canary); await page.reload(); await waitDashboard(page, accountA.username);
  phase = 'refresh-clears-key';
  check('page refresh clears the in-memory key', {empty: await keyInput.inputValue() === ''}, {empty: true}, await keyInput.inputValue() === '', 'refresh');

  await keyInput.fill(canary);
  phase = 'logout-clears-key';
  await page.getByRole('button', {name: '退出登录', exact: true}).click();
  await page.getByRole('heading', {name: '欢迎回来', exact: true}).waitFor();
  await registerOrLogin(page, accountA, false);
  phase = 'prepare-second-identity';
  check('logout and subsequent login do not restore the key', {empty: await keyInput.inputValue() === ''}, {empty: true}, await keyInput.inputValue() === '', 'logout');

  // Register a second local Synthetic identity to exercise the product's real
  // cross-tab logout/login UI and BroadcastChannel identity-change handling.
  await page.getByRole('button', {name: '退出登录', exact: true}).click();
  await page.getByRole('heading', {name: '欢迎回来', exact: true}).waitFor();
  await registerOrLogin(page, accountB, true);
  await page.getByRole('button', {name: '退出登录', exact: true}).click();
  await page.getByRole('heading', {name: '欢迎回来', exact: true}).waitFor();
  await registerOrLogin(page, accountA, false);

  const second = await context.newPage(); attachObservers(second); second.setDefaultTimeout(15000); await second.goto(base); await waitDashboard(second, accountA.username);
  phase = 'cross-tab-identity-change';
  await keyInput.fill(canary);
  await second.getByRole('button', {name: '退出登录', exact: true}).click();
  await second.getByRole('heading', {name: '欢迎回来', exact: true}).waitFor();
  await registerOrLogin(second, accountB, false);
  await page.locator('.v5-account').filter({hasText: accountB.username}).waitFor({timeout: 12000});
  await waitDashboard(page, accountB.username);
  const firstTabKeyEmpty = await page.getByLabel(/本次生成的 DeepSeek API Key/).inputValue() === '';
  check('real second-tab logout/login identity change clears first-tab key', {key_empty: firstTabKeyEmpty, second_tab_user_is_beta: (await second.locator('.v5-account').innerText()).includes(accountB.username)}, {key_empty: true, second_tab_user_is_beta: true}, firstTabKeyEmpty && (await second.locator('.v5-account').innerText()).includes(accountB.username), 'cross-tab');

  phase = 'successful-synthetic-generation';
  await keyInput.fill(canary);
  const successResponse = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname === '/api/v2/level-generations');
  await generate.click();
  const success = await successResponse;
  await page.waitForFunction(() => document.querySelector('.v5-generator input[type="password"]')?.value === '');
  check('Synthetic generation request accepted locally and key cleared after response', {http_status: success.status(), key_empty: await keyInput.inputValue() === '', only_local_target_header_count: exposure.allowed_key_header}, {http_accepted: true, key_empty: true, key_header_present: true}, success.ok() && await keyInput.inputValue() === '' && exposure.allowed_key_header === 2);
  await page.screenshot({path: path.join(out, 'after-success-key-cleared.png')}); screenshots.push('after-success-key-cleared.png');

  const stores = await Promise.all(pages.map(storageScan));
  check('Canary absent from browser local and session storage before and after requests', {pre_submit_local_storage_hit: preSubmitStorage.local, pre_submit_session_storage_hit: preSubmitStorage.session, local_storage_hits: stores.filter(x => x.local).length, session_storage_hits: stores.filter(x => x.session).length}, {pre_submit_local_storage_hit: false, pre_submit_session_storage_hit: false, local_storage_hits: 0, session_storage_hits: 0}, !preSubmitStorage.local && !preSubmitStorage.session && stores.every(x => !x.local && !x.session), 'privacy');
  await waitForResponseScans();
  check('Canary exposure is limited to local generation auth header', {canary_id: canaryId, allowed_key_header_occurrences: exposure.allowed_key_header, url: exposure.url, body: exposure.body, non_allowed_request_headers: exposure.non_allowed_request_headers, ordinary_response: exposure.ordinary_response, checked_response_count: checkedResponseCount, unread_response_count: unreadResponseCount}, {url: 0, body: 0, non_allowed_request_headers: 0, ordinary_response: 0, unread_response_count: 0, storage_hits: 0}, exposure.url === 0 && exposure.body === 0 && exposure.non_allowed_request_headers === 0 && exposure.ordinary_response === 0 && unreadResponseCount === 0 && stores.every(x => !x.local && !x.session));
  check('traffic remained local and used no real provider', {external_requests: exposure.external_requests, synthetic_key_header_occurrences: exposure.allowed_key_header, generation_posts: exposure.target_generation_posts, fixture_provider: 'mock'}, {external_requests: 0, synthetic_key_header_occurrences: 2, fixture_provider: 'mock'}, exposure.external_requests === 0 && exposure.allowed_key_header === 2);
}

async function main() {
  await fs.mkdir(out, {recursive: false});
  await fs.writeFile(path.join(out, 'records.jsonl'), '', {flag: 'wx'});
  await run();
}

let exit = 0;
try { await main(); }
catch (error) { issues.push({type: error?.constructor?.name || 'Error', phase, message: String(error?.message || 'unknown').split('\n')[0].slice(0, 160)}); exit = 1; }
finally {
  try { await context?.unrouteAll({behavior: 'ignoreErrors'}); } catch {}
  try { await context?.close(); } catch {}
  try { await browser?.close(); } catch {}
  if (server) serverStopped = await new Promise(resolve => {
    if (server.exitCode !== null || server.signalCode !== null) return resolve(true);
    server.once('close', () => resolve(true)); server.kill(); setTimeout(() => resolve(false), 4000);
  });
  exit = exit || (records.some(row => !row.pass) || !serverStopped ? 1 : 0);
  const result = {
    run_id: runId, command: 'node tests/v5/run_key_safety_browser.mjs', started_at_utc: started, finished_at_utc: new Date().toISOString(),
    scope: 'isolated Synthetic V5 UI; empty key; success; controlled local 503; refresh/logout; second-tab real logout/login; canary transmission scan',
    canary_id: canaryId, canary_value_recorded: false, fixture_temp: tempRoot ? path.basename(tempRoot) : null, owned_server_port: 8002, owned_server_stopped: serverStopped,
    git_head: gitHead, loaded_script_files: loadedScriptFiles, checked_response_count: checkedResponseCount, unread_response_count: unreadResponseCount,
    exposure, storage_values_recorded: false, credentials_recorded: false, cookies_or_tokens_recorded: false, player_database_access: false, real_model_calls: 0, paid_calls: 0, screenshots, records, issues, exit_code: exit,
  };
  await fs.writeFile(path.join(out, 'result.json'), JSON.stringify(result, null, 2) + '\n', {flag: 'wx'}).catch(() => {});
  process.exitCode = exit;
}
