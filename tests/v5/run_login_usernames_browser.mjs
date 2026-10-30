import fs from 'node:fs/promises';
import fsSync from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import http from 'node:http';
import net from 'node:net';
import {spawn} from 'node:child_process';
import {createRequire} from 'node:module';
import {randomUUID} from 'node:crypto';

const root = process.cwd();
const base = 'http://127.0.0.1:8001';
const stage = path.join(root, 'evidence/project/stages/v5-login-usernames/automated');
const started = new Date().toISOString();
const runId = randomUUID();
const out = path.join(stage, `browser-${started.replace(/[:.]/g, '-')}-${runId.slice(0, 8)}`);
const modeSwitchOnly = process.argv.includes('--mode-switch-only');
const syntheticAccounts = [
  {username: 'synth_alpha', password: 'Synthetic-Login-Alpha!'},
  {username: 'synth_beta', password: 'Synthetic-Login-Beta!'},
];
const records = [], screenshots = [], issues = [], credentialEvents = [];
let tempRoot = null, server = null, serverStopped = true, externalRequests = 0, generationPosts = 0;
const check = (name, actual, expected, pass, scope = 'browser') => {
  const row = {name, actual, expected, pass: !!pass, scope, observed_at_utc: new Date().toISOString()};
  records.push(row);
  fsSync.appendFileSync(path.join(out, 'records.jsonl'), JSON.stringify(row) + '\n', 'utf8');
};
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

async function startFixture() {
  const port = net.createServer();
  await new Promise((resolve, reject) => { port.once('error', reject); port.listen(8002, '127.0.0.1', () => port.close(resolve)); });
  if (modeSwitchOnly) {
    const reuseName = process.env.LOGIN_USERNAMES_REUSE_TEMP || '';
    if (!/^campus-visual-login-usernames-[A-Za-z0-9_-]+$/.test(reuseName)) throw Error('Owned auth fixture name is required for mode-switch-only');
    tempRoot = path.join(os.tmpdir(), reuseName);
    await fs.access(path.join(tempRoot, 'game-v5.sqlite'));
  } else {
    tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'campus-visual-login-usernames-'));
  }
  const db = path.join(tempRoot, 'game-v5.sqlite');
  server = spawn('C:/Users/liyh/.conda/envs/1/python.exe', ['-B', '-X', 'utf8', '-m', 'uvicorn', 'tests.v5.visual_ui_fixture_server:app', '--host', '127.0.0.1', '--port', '8002', '--no-access-log'], {
    cwd: root,
    env: {...process.env, SQLITE_PATH: db, GAMEPLAY_VERSION: 'v5', AI_PROVIDER: 'mock', PYTHONDONTWRITEBYTECODE: '1', ...(modeSwitchOnly ? {VISUAL_REUSE_TEMP: '1'} : {})},
    stdio: 'ignore', windowsHide: true,
  });
  let ready = false;
  for (let i = 0; i < 100 && !ready; i++) {
    ready = await new Promise(resolve => {
      const req = http.get({hostname: '127.0.0.1', port: 8002, path: '/health', headers: {host: '127.0.0.1:8001'}}, res => {res.resume(); resolve(res.statusCode === 200);});
      req.on('error', () => resolve(false)); req.setTimeout(700, () => req.destroy());
    });
    if (!ready) await pause(100);
  }
  if (!ready) throw Error('Owned Synthetic auth fixture failed readiness');
}

async function runBrowser() {
  await startFixture();
  const {chromium} = createRequire(path.join(root, 'frontend/package.json'))('@playwright/test');
  const browser = await chromium.launch({headless: true, channel: 'chrome'});
  let context;
  try {
    context = await browser.newContext({viewport: {width: 1280, height: 720}});
    await context.route('**/*', async route => {
      const request = route.request(), url = new URL(request.url());
      if (['data:', 'blob:'].includes(url.protocol)) return route.continue();
      if (url.origin !== base) { externalRequests++; return route.abort(); }
      try {
        const response = await route.fetch({url: request.url().replace(base, 'http://127.0.0.1:8002'), headers: {...request.headers(), host: '127.0.0.1:8001'}});
        return await route.fulfill({response});
      } catch {
        return route.abort().catch(() => {});
      }
    });
    const page = await context.newPage();
    page.setDefaultTimeout(15000);
    page.on('request', request => {
      const url = new URL(request.url());
      if (request.method() === 'POST' && url.pathname.endsWith('/level-generations')) generationPosts++;
      if (request.method() === 'POST' && /\/auth\/(register|login)$/.test(url.pathname)) {
        try {
          const body = request.postDataJSON();
          credentialEvents.push({operation: url.pathname.endsWith('/register') ? 'register' : 'login', username: body.username, password_present: typeof body.password === 'string' && body.password.length > 0});
        } catch { credentialEvents.push({operation: 'unparsed', password_present: null}); }
      }
    });

    await page.goto(base);
    await page.getByRole('heading', {name: '欢迎回来', exact: true}).waitFor();
    const select = page.locator('.v5-auth-panel select').first();
    const password = page.getByLabel('密码（12–128位）', {exact: true});
    const registerToggle = page.getByRole('button', {name: '第一次来？注册本地账户', exact: true});
    const readOptions = async () => select.locator('option').evaluateAll(items => items.map(item => ({text: item.textContent?.trim(), value: item.value})));
    if (modeSwitchOnly) {
      const expectedNames = ['synth_alpha', 'synth_beta'];
      const beforeOptions = await readOptions();
      check('reused owned Synthetic fixture exposes the expected two names', {options: beforeOptions, selected: await select.inputValue()}, {names: expectedNames, selected: expectedNames[0]}, JSON.stringify(beforeOptions.map(x => x.value)) === JSON.stringify(expectedNames) && await select.inputValue() === expectedNames[0], 'mode-switch');
      await password.fill(syntheticAccounts[0].password);
      await registerToggle.click();
      const registerPassword = page.getByLabel('密码（12–128位）', {exact: true});
      const registerUsername = page.getByLabel('用户名（3–24位字母、数字或下划线）', {exact: true});
      check('switching from login to registration clears password', {password_empty: await registerPassword.inputValue() === '', registration_username_empty: await registerUsername.inputValue() === ''}, {password_empty: true, registration_username_empty: true}, await registerPassword.inputValue() === '' && await registerUsername.inputValue() === '', 'mode-switch');
      await page.getByRole('button', {name: '已有账户，返回登录', exact: true}).click();
      const afterOptions = await readOptions();
      check('switching back retains names/default and leaves password empty', {options: afterOptions.map(x => x.value), selected: await select.inputValue(), password_empty: await password.inputValue() === ''}, {options: expectedNames, selected: expectedNames[0], password_empty: true}, JSON.stringify(afterOptions.map(x => x.value)) === JSON.stringify(expectedNames) && await select.inputValue() === expectedNames[0] && await password.inputValue() === '', 'mode-switch');
      check('mode-switch-only branch made no auth, generation, or external requests', {credential_posts: credentialEvents.length, generation_posts: generationPosts, external_requests: externalRequests}, {credential_posts: 0, generation_posts: 0, external_requests: 0}, credentialEvents.length === 0 && generationPosts === 0 && externalRequests === 0, 'scope');
      return;
    }
    const initialOptions = await readOptions();
    check('empty local user list shows register guidance and disables login', {options: initialOptions, note: await page.locator('.v5-auth-note').last().innerText(), login_disabled: await page.getByRole('button', {name: '登录', exact: true}).isDisabled()}, {options: [{text: '暂无已有用户名', value: ''}], guidance: true, login_disabled: true}, initialOptions.length === 1 && initialOptions[0].value === '' && (await page.locator('.v5-auth-note').last().innerText()).includes('请先注册本地账户') && await page.getByRole('button', {name: '登录', exact: true}).isDisabled(), 'empty-list');
    check('empty-list login has no password or freeform username prefill', {password_empty: await password.inputValue() === '', username_textbox_count: await page.locator('input[autocomplete="username"]').count()}, {password_empty: true, username_textbox_count: 0}, await password.inputValue() === '' && await page.locator('input[autocomplete="username"]').count() === 0, 'empty-list');

    for (const account of syntheticAccounts) {
      await registerToggle.click();
      const usernameInput = page.getByLabel('用户名（3–24位字母、数字或下划线）', {exact: true});
      await usernameInput.fill(account.username);
      await password.fill(account.password);
      check(`registration form retains typed username ${account.username}`, await usernameInput.inputValue(), account.username, await usernameInput.inputValue() === account.username, 'register');
      const responseWait = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname.endsWith('/auth/register'));
      await page.getByRole('button', {name: '注册并进入', exact: true}).click();
      const response = await responseWait;
      check(`Synthetic registration accepted ${account.username}`, response.status(), 201, response.status() === 201, 'register');
      await page.getByRole('heading', {name: '我的关卡', exact: true}).waitFor();
      await page.getByRole('button', {name: '退出登录', exact: true}).click();
      await page.getByRole('heading', {name: '欢迎回来', exact: true}).waitFor();
    }

    const expected = syntheticAccounts.map(x => x.username).sort();
    const options = await readOptions();
    check('logout refresh lists registered names in normalized sorted order', {options, selected: await select.inputValue(), password_empty: await password.inputValue() === ''}, {options: expected.map(x => ({text: x, value: x})), selected: expected[0], password_empty: true}, JSON.stringify(options) === JSON.stringify(expected.map(x => ({text: x, value: x}))) && await select.inputValue() === expected[0] && await password.inputValue() === '', 'login-list');
    await page.screenshot({path: path.join(out, 'login-names-1280x720.png')}); screenshots.push('login-names-1280x720.png');
    await page.setViewportSize({width: 1920, height: 1080}); await pause(100);
    await page.screenshot({path: path.join(out, 'login-names-1920x1080.png')}); screenshots.push('login-names-1920x1080.png');

    await password.fill(syntheticAccounts[0].password);
    await select.selectOption(expected[1]);
    check('changing selected local username clears password', {selected: await select.inputValue(), password_empty: await password.inputValue() === ''}, {selected: expected[1], password_empty: true}, await select.inputValue() === expected[1] && await password.inputValue() === '', 'login-list');
    await password.fill('Synthetic-Wrong-Password!');
    const failedLoginWait = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname.endsWith('/auth/login'));
    await page.getByRole('button', {name: '登录', exact: true}).click();
    const failedLogin = await failedLoginWait;
    await page.getByRole('alert').waitFor();
    const preserved = await readOptions();
    check('wrong password remains a 401 and retains names after auth invalidation', {status: failedLogin.status(), selected: await select.inputValue(), names: preserved.map(x => x.value), password_empty: await password.inputValue() === '', alert_present: await page.getByRole('alert').count() > 0}, {status: 401, selected: expected[1], names: expected, password_empty: true, alert_present: true}, failedLogin.status() === 401 && await select.inputValue() === expected[1] && JSON.stringify(preserved.map(x => x.value)) === JSON.stringify(expected) && await password.inputValue() === '' && await page.getByRole('alert').count() > 0, 'wrong-password');

    await password.fill(syntheticAccounts[1].password);
    const goodLoginWait = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname.endsWith('/auth/login'));
    await page.getByRole('button', {name: '登录', exact: true}).click();
    const goodLogin = await goodLoginWait;
    await page.getByRole('heading', {name: '我的关卡', exact: true}).waitFor();
    check('correct distinct password succeeds after csrf refresh', {status: goodLogin.status(), account_visible: (await page.locator('.v5-account').innerText()).includes(expected[1])}, {status: 200, account_visible: true}, goodLogin.status() === 200 && (await page.locator('.v5-account').innerText()).includes(expected[1]), 'login');
    const localStorageContainsSecret = await page.evaluate(values => Object.values(localStorage).some(value => values.some(secret => value.includes(secret))), syntheticAccounts.map(x => x.password));
    check('Synthetic passwords are not stored in localStorage', localStorageContainsSecret, false, !localStorageContainsSecret, 'privacy');
    check('no generation or third-party request in auth flow', {generation_posts: generationPosts, external_requests: externalRequests}, {generation_posts: 0, external_requests: 0}, generationPosts === 0 && externalRequests === 0, 'scope');
    check('all credential request observations contain only expected synthetic account names and presence flags', credentialEvents, {operations: ['register', 'register', 'login', 'login'], usernames: ['synth_alpha', 'synth_beta', 'synth_beta', 'synth_beta'], all_passwords_present: true}, credentialEvents.length === 4 && credentialEvents.every((x, i) => x.password_present === true && x.username === ['synth_alpha', 'synth_beta', 'synth_beta', 'synth_beta'][i]), 'scope');
  } finally {
    try { await context?.unrouteAll({behavior: 'ignoreErrors'}); } catch {}
    try { await context?.close(); } catch {}
    try { await browser.close(); } catch {}
  }
}

async function main() {
  await fs.mkdir(out, {recursive: false});
  await fs.writeFile(path.join(out, 'records.jsonl'), '', {flag: 'wx'});
  await runBrowser();
}

let exit = 0;
try { await main(); }
catch (error) { issues.push({type: error?.constructor?.name || 'Error', message: String(error?.message || 'unknown').split('\n')[0].slice(0, 180)}); exit = 1; }
finally {
  if (server) serverStopped = await new Promise(resolve => {
    if (server.exitCode !== null || server.signalCode !== null) return resolve(true);
    server.once('close', () => resolve(true)); server.kill(); setTimeout(() => resolve(false), 4000);
  });
  exit = exit || (records.some(x => !x.pass) || !serverStopped ? 1 : 0);
  const result = {run_id: runId, command: `node tests/v5/run_login_usernames_browser.mjs${modeSwitchOnly ? ' --mode-switch-only' : ''}`, started_at_utc: started, finished_at_utc: new Date().toISOString(), scope: modeSwitchOnly ? 'mode-toggle clears password and preserves local username list/default only; no auth or generation requests' : 'empty-list/register-two-Synthetic-users/sorted-login-picker/account-switch-clear/wrong-password-retention/correct-login; desktop 1280x720 and 1920x1080', TEMP: tempRoot ? path.basename(tempRoot) : null, server_port: 8002, server_stopped: serverStopped, external_requests: externalRequests, generation_POSTs: generationPosts, synthetic_credential_observations: credentialEvents, passwords_recorded: false, player_database_access: false, model_calls: 0, paid_calls: 0, screenshots, records, issues, exit_code: exit};
  await fs.writeFile(path.join(out, 'result.json'), JSON.stringify(result, null, 2) + '\n', {flag: 'wx'}).catch(() => {});
  process.exitCode = exit;
}
