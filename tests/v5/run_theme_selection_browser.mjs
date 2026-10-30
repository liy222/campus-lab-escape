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
const stage = path.join(root, 'evidence/project/stages/v5-theme-selection/automated');
const started = new Date().toISOString();
const runId = randomUUID();
const out = path.join(stage, `qa-${started.replace(/[:.]/g, '-')}-${runId.slice(0, 8)}`);
const keyboardOnly = process.argv.includes('--keyboard-only');
const expectedThemes = ['雨夜天文社', '图书馆档案', '化学实验室', '计算机机房', '校园广播室'];
const records = [], screenshots = [], issues = [];
let browserTemp = null, server = null, serverStopped = true, externalRequests = 0;
const check = (name, actual, expected, pass, scope = 'browser') => {
  const row = {name, actual, expected, pass: !!pass, scope, observed_at_utc: new Date().toISOString()};
  records.push(row);
  fsSync.appendFileSync(path.join(out, 'records.jsonl'), JSON.stringify(row) + '\n', 'utf8');
};
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

async function runBrowser() {
  const port = net.createServer();
  await new Promise((resolve, reject) => { port.once('error', reject); port.listen(8002, '127.0.0.1', () => port.close(resolve)); });
  browserTemp = await fs.mkdtemp(path.join(os.tmpdir(), 'campus-visual-theme-selection-'));
  const db = path.join(browserTemp, 'game-v5.sqlite');
  server = spawn('C:/Users/liyh/.conda/envs/1/python.exe', ['-B', '-X', 'utf8', '-m', 'uvicorn', 'tests.v5.visual_ui_fixture_server:app', '--host', '127.0.0.1', '--port', '8002', '--no-access-log'], {cwd: root, env: {...process.env, SQLITE_PATH: db, GAMEPLAY_VERSION: 'v5', AI_PROVIDER: 'mock', PYTHONDONTWRITEBYTECODE: '1'}, stdio: 'ignore', windowsHide: true});
  let ready = false;
  for (let i = 0; i < 100 && !ready; i++) {
    ready = await new Promise(resolve => { const req = http.get({hostname: '127.0.0.1', port: 8002, path: '/health', headers: {host: '127.0.0.1:8001'}}, res => {res.resume(); resolve(res.statusCode === 200);}); req.on('error', () => resolve(false)); req.setTimeout(700, () => req.destroy()); });
    if (!ready) await pause(100);
  }
  if (!ready) throw Error('Owned synthetic fixture failed readiness');
  const {chromium} = createRequire(path.join(root, 'frontend/package.json'))('@playwright/test');
  const browser = await chromium.launch({headless: true, channel: 'chrome'});
  let context;
  try {
    context = await browser.newContext({viewport: {width: 1280, height: 720}});
    await context.route('**/*', async route => {
      const request = route.request(), url = new URL(request.url());
      if (['data:', 'blob:'].includes(url.protocol)) return route.continue();
      if (url.origin !== base) { externalRequests++; return route.abort(); }
      return route.fetch({url: request.url().replace(base, 'http://127.0.0.1:8002'), headers: {...request.headers(), host: '127.0.0.1:8001'}}).then(response => route.fulfill({response}));
    });
    const page = await context.newPage();
    page.setDefaultTimeout(15000);
    let levelPostCount = 0, submittedFields = null, credentialIncludedInBody = false;
    page.on('request', request => {
      const url = new URL(request.url());
      if (request.method() !== 'POST' || !url.pathname.endsWith('/level-generations')) return;
      levelPostCount++;
      try {
        const body = request.postDataJSON();
        submittedFields = {theme: body.theme, room_count: body.room_count, difficulty: body.difficulty};
        credentialIncludedInBody = JSON.stringify(body).includes('SYNTHETIC-ONLY-NOT-A-REAL-KEY');
      } catch { submittedFields = {parse_error: true}; }
    });

    await page.goto(base);
    await page.getByRole('button', {name: '第一次来？注册本地账户', exact: true}).click();
    await page.getByLabel('用户名（3–24位字母、数字或下划线）', {exact: true}).fill(`selection_${runId.slice(0, 8)}`);
    await page.getByLabel('密码（12–128位）', {exact: true}).fill('Synthetic-Selection-only!');
    await page.getByRole('button', {name: '注册并进入', exact: true}).click();
    await page.getByRole('heading', {name: '我的关卡', exact: true}).waitFor();

    const generator = page.locator('.v5-generator');
    const theme = generator.locator('select').first();
    const structure = await generator.evaluate(el => ({textarea_count: el.querySelectorAll('textarea').length, character_counter_count: el.querySelectorAll('[data-character-count],.v5-character-count,.v5-char-count').length, character_counter_text: (el.innerText.match(/\b\d+\s*\/\s*\d+\b|\b\d+\s*(?:字|字符)\b/g) || []), selects: [...el.querySelectorAll('select')].map(x => ({label: [...(x.closest('label')?.childNodes ?? [])].filter(n => n.nodeType === Node.TEXT_NODE).map(n => n.textContent?.trim()).filter(Boolean).join(' '), value: x.value, options: [...x.options].map(o => ({text: o.textContent?.trim(), value: o.value}))}))}));
    const themeSelect = structure.selects.find(x => x.label === '校园主题');
    const themeOptions = themeSelect?.options ?? [];
    if (keyboardOnly) {
      const initial = await theme.inputValue();
      await theme.click();
      await theme.press('Home');
      await theme.press('ArrowDown');
      await theme.press('Enter');
      const keyboardValue = await theme.inputValue();
      const active = page.locator('.v5-coverage.is-on');
      const coverage = await active.count() === 1 ? await active.innerText() : '';
      check('fresh native keyboard selection updates value and coverage', {initial, value: keyboardValue, coverage: coverage.match(/「([^」]+)」/)?.[1] ?? null}, {initial: expectedThemes[0], value: expectedThemes[1], coverage: expectedThemes[1]}, initial === expectedThemes[0] && keyboardValue === expectedThemes[1] && coverage.includes(`「${expectedThemes[1]}」`), 'form');
      check('keyboard-only follow-up submits no generation', levelPostCount, 0, levelPostCount === 0, 'scope');
      check('no external network requests', externalRequests, 0, externalRequests === 0, 'scope');
      return;
    }
    check('theme control is a fixed five-option select with original names', {tag: await theme.evaluate(el => el.tagName), default_value: await theme.inputValue(), option_count: themeOptions.length, options: themeOptions, textarea_count: structure.textarea_count, character_counter_count: structure.character_counter_count, character_counter_text: structure.character_counter_text}, {tag: 'SELECT', default_value: expectedThemes[0], options: expectedThemes.map(x => ({text: x, value: x})), textarea_count: 0, character_counter_count: 0, character_counter_text: []}, await theme.evaluate(el => el.tagName === 'SELECT') && await theme.inputValue() === expectedThemes[0] && JSON.stringify(themeOptions) === JSON.stringify(expectedThemes.map(x => ({text: x, value: x}))) && structure.textarea_count === 0 && structure.character_counter_count === 0 && structure.character_counter_text.length === 0, 'form');

    const coverageResults = [];
    for (const value of expectedThemes) {
      await theme.scrollIntoViewIfNeeded();
      await theme.click();
      await theme.selectOption(value);
      await pause(60);
      const active = page.locator('.v5-coverage.is-on');
      const count = await active.count();
      const text = count === 1 ? await active.innerText() : '';
      const name = text.match(/「([^」]+)」/)?.[1] ?? null;
      const item = {selected_value: await theme.inputValue(), active_count: count, coverage_name: name};
      coverageResults.push(item);
      check(`mouse-controlled theme option coverage ${value}`, item, value, item.selected_value === value && count === 1 && name === value, 'form');
    }
    await theme.selectOption(expectedThemes[0]);
    await theme.focus();
    await theme.press('ArrowDown');
    await theme.press('Enter');
    const keyboardValue = await theme.inputValue();
    const keyboardCoverage = await page.locator('.v5-coverage.is-on').innerText();
    check('keyboard selection updates value and coverage', {value: keyboardValue, coverage: keyboardCoverage.match(/「([^」]+)」/)?.[1] ?? null}, {value: expectedThemes[1], coverage: expectedThemes[1]}, keyboardValue === expectedThemes[1] && keyboardCoverage.includes(`「${expectedThemes[1]}」`), 'form');

    const selectedTheme = '化学实验室';
    await theme.click();
    await theme.selectOption(selectedTheme);
    await page.getByLabel(/^房间数量/).selectOption('2');
    await page.getByLabel(/^难度/).selectOption('normal');
    const keyInput = page.getByLabel(/本次生成的 DeepSeek API Key/);
    await keyInput.fill('SYNTHETIC-ONLY-NOT-A-REAL-KEY');
    await page.screenshot({path: path.join(out, 'selection-form-1280x720.png')});
    screenshots.push('selection-form-1280x720.png');

    const postResponse = page.waitForResponse(response => response.request().method() === 'POST' && new URL(response.url()).pathname.endsWith('/level-generations'));
    await page.getByRole('button', {name: /^生成关卡/}).click();
    const response = await postResponse, responseBody = await response.json(), job = responseBody.data?.job;
    check('single generation preserves selected theme and size fields', {request_count: levelPostCount, submitted: submittedFields, accepted: response.ok(), status: job?.status ?? null}, {request_count: 1, submitted: {theme: selectedTheme, room_count: 2, difficulty: 'normal'}, accepted: true}, levelPostCount === 1 && submittedFields?.theme === selectedTheme && submittedFields?.room_count === 2 && submittedFields?.difficulty === 'normal' && response.ok() && !!job?.job_id, 'submit');
    const cleared = await keyInput.inputValue();
    check('temporary key field clears after submission', {empty: cleared === ''}, {empty: true}, cleared === '', 'submit');
    check('temporary key is absent from submitted JSON body', {credential_in_body: credentialIncludedInBody}, {credential_in_body: false}, !credentialIncludedInBody, 'submit');
    let status = null;
    for (let i = 0; i < 100; i++) {
      status = await page.evaluate(async id => { const response = await fetch(`/api/v2/level-generations/${encodeURIComponent(id)}`); if (!response.ok) return {http_status: response.status}; const body = await response.json(); const job = body.data?.job; return job ? {status: job.status, error_code: job.error_code ?? null, room_count: job.room_count, difficulty: job.difficulty} : null; }, job.job_id);
      if (status?.status === 'ready' || status?.status === 'failed' || status?.status === 'unknown') break;
      await pause(250);
    }
    check('submitted generation reaches ready on public task endpoint', status, {status: 'ready', error_code: null, room_count: 2, difficulty: 'normal'}, status?.status === 'ready' && status?.error_code === null && status?.room_count === 2 && status?.difficulty === 'normal', 'submit');
    if (status?.status !== 'ready') throw Error(`Synthetic generation did not become ready (${status?.status || 'unavailable'}${status?.error_code ? ` / ${status.error_code}` : ''})`);

    const listResponse = page.waitForResponse(r => r.request().method() === 'GET' && new URL(r.url()).pathname.endsWith('/levels'));
    await page.getByRole('button', {name: '刷新列表', exact: true}).click();
    const listBody = await (await listResponse).json();
    const stored = listBody.data?.levels?.find(level => level.theme === selectedTheme);
    check('refresh exposes the selected theme level', stored ? {theme: stored.theme, room_count: stored.room_count, difficulty: stored.difficulty} : null, {theme: selectedTheme, room_count: 2, difficulty: 'normal'}, !!stored && stored.room_count === 2 && stored.difficulty === 'normal', 'submit');
    const card = page.locator('.v5-level-card').filter({hasText: selectedTheme}).first();
    await card.waitFor();
    await card.getByRole('button', {name: /探索/}).click();
    await page.locator('.v5-hotspots button:enabled').first().waitFor();
    await page.waitForFunction(() => document.querySelector('.v5-scene')?.dataset.loadingTextures === 'false', null, {timeout: 20000});
    const scene = await page.locator('.v5-scene').evaluate(el => ({theme: el.dataset.theme, background: el.dataset.background, missing: Number(el.dataset.missingTextures), loading: el.dataset.loadingTextures}));
    check('selected-theme level opens in its matching themed scene', scene, {theme: 'chemistry-lab', missing: 0, loading: 'false'}, scene.theme === 'chemistry-lab' && scene.missing === 0 && scene.loading === 'false', 'submit');
    await page.screenshot({path: path.join(out, 'selected-theme-scene-1280x720.png')});
    screenshots.push('selected-theme-scene-1280x720.png');
    await page.setViewportSize({width: 1920, height: 1080});
    await pause(120);
    const wide = await page.locator('.v5-scene').evaluate(el => ({theme: el.dataset.theme, missing: Number(el.dataset.missingTextures), loading: el.dataset.loadingTextures}));
    check('selected-theme scene remains loaded at 1920x1080', wide, {theme: 'chemistry-lab', missing: 0, loading: 'false'}, wide.theme === 'chemistry-lab' && wide.missing === 0 && wide.loading === 'false', 'submit');
    await page.screenshot({path: path.join(out, 'selected-theme-scene-1920x1080.png')});
    screenshots.push('selected-theme-scene-1920x1080.png');
    check('only one theme generation was submitted', levelPostCount, 1, levelPostCount === 1, 'scope');
    check('no external network requests', externalRequests, 0, externalRequests === 0, 'scope');
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
    server.once('close', () => resolve(true));
    server.kill();
    setTimeout(() => resolve(false), 4000);
  });
  exit = exit || (records.some(x => !x.pass) || !serverStopped ? 1 : 0);
  const result = {run_id: runId, command: `node tests/v5/run_theme_selection_browser.mjs${keyboardOnly ? ' --keyboard-only' : ''}`, started_at_utc: started, finished_at_utc: new Date().toISOString(), scope: keyboardOnly ? 'fresh native keyboard selection and matching coverage only; zero generation submissions' : 'fixed five-theme select/default/coverage, pointer+keyboard, one Synthetic generation and list entry; desktop 1280x720 and 1920x1080', browser_TEMP: browserTemp ? path.basename(browserTemp) : null, server_port: 8002, server_stopped: serverStopped, external_requests: externalRequests, generation_POSTs: keyboardOnly ? 0 : records.find(x => x.name === 'only one theme generation was submitted')?.actual ?? null, temporary_key_value_recorded: false, paid_calls: 0, real_model_calls: 0, player_database_access: false, screenshots, records, issues, exit_code: exit};
  await fs.writeFile(path.join(out, 'result.json'), JSON.stringify(result, null, 2) + '\n', {flag: 'wx'}).catch(() => {});
  process.exitCode = exit;
}
