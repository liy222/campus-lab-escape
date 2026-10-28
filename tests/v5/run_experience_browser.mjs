// Synthetic-only focused UI check. All browser 8001 traffic is forwarded to our
// owned 8002 process; the user service and player database are never contacted.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import net from 'node:net';
import http from 'node:http';
import { createHash, randomUUID } from 'node:crypto';
import { spawn, execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { completedCircuitPass, minimumControlSizePass, pendingCircuitPass, runJudgementSelfTest } from './experience_observation.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const runId = randomUUID(), startedAt = new Date().toISOString();
const selfTest = runJudgementSelfTest();
const argumentsList = process.argv.slice(2);
let requestedOutput, resumeFrom;
let finishAuth = false;
function invalidArguments() {
  console.error(JSON.stringify({ run_id: runId, status: 'NOT_RUN', reason: 'Use no arguments, --output <new directory>, --self-test, or --finish-auth --resume-from <first browser-result.json> --output <new directory>. TEMP is never guessed.' }));
  process.exit(2);
}
for (let index = 0; index < argumentsList.length; index++) {
  const argument = argumentsList[index];
  if (argument === '--output' && argumentsList[index + 1] && !argumentsList[index + 1].startsWith('--') && !requestedOutput) requestedOutput = argumentsList[++index];
  else if (argument === '--finish-auth' && !finishAuth) finishAuth = true;
  else if (argument === '--resume-from' && argumentsList[index + 1] && !argumentsList[index + 1].startsWith('--') && !resumeFrom) resumeFrom = argumentsList[++index];
  else if (argument === '--self-test' && argumentsList.length === 1) {
    console.log(JSON.stringify(selfTest, null, 2));
    process.exit(selfTest.pass ? 0 : 1);
  } else invalidArguments();
}
if (finishAuth ? !resumeFrom || !requestedOutput : Boolean(resumeFrom)) invalidArguments();
let out, stageId = null;
if (requestedOutput) out = path.resolve(root, requestedOutput);
else {
  try {
    const index = JSON.parse(await fs.readFile(path.join(root, 'evidence/project/index.json'), 'utf8'));
    if (typeof index.active_stage !== 'string' || !/^[a-z0-9][a-z0-9_-]{0,79}$/.test(index.active_stage)) throw Error('Invalid active stage');
    stageId = index.active_stage;
    out = path.join(root, 'evidence/project/stages', stageId, 'automated', `browser-${startedAt.replace(/[:.]/g, '-')}-${runId.slice(0, 8)}`);
  } catch {
    console.error(JSON.stringify({ run_id: runId, status: 'NOT_RUN', reason: 'Default output requires evidence/project/index.json with a valid active_stage slug; no stage was guessed.' }));
    process.exit(2);
  }
}
try {
  await fs.mkdir(path.dirname(out), { recursive: true });
  await fs.mkdir(out); // Deliberately no recursive/exist_ok: never overwrite a prior run.
} catch (error) {
  console.error(JSON.stringify({ run_id: runId, status: 'NOT_RUN', reason: error.code === 'EEXIST' ? 'Output directory already exists; choose a new directory.' : 'Output directory could not be created.', output: out }));
  process.exit(2);
}
const base = 'http://127.0.0.1:8001';
const theme = '雨夜里的天文社旧活动室,寻找封存的观测记录';
const story = 'Synthetic：雨夜的天文社旧活动室里，封存的观测记录等待查阅。';
const checks = [], screenshots = [];
let server, browser, page, context, state, temp, provenance, firstResult;
let stage = 'context', delayAction = false, omitTheme = false, external = 0, browserExecuted = false;
let exit = 1, serverClosed = null;

function check(name, actual, expected, pass, input = {}) {
  checks.push({ name, pass: Boolean(pass), expected, actual, input, context: { stage, viewport: page?.viewportSize() || null, synthetic: true }, observed_at_utc: new Date().toISOString() });
  if (!pass) throw Error(name);
}
async function fingerprint(relative) {
  const file = await fs.readFile(path.join(root, relative));
  return { path: relative.replaceAll('\\', '/'), bytes: file.length, sha256: createHash('sha256').update(file).digest('hex') };
}
async function sourceContext() {
  const revision = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8', windowsHide: true }).trim();
  const dirty = execFileSync('git', ['status', '--porcelain', '--untracked-files=no'], { cwd: root, encoding: 'utf8', windowsHide: true }).trim().length > 0;
  const sourceFiles = [
    'tests/v5/run_experience_browser.mjs', 'tests/v5/experience_observation.mjs', 'tests/v5/experience_fixture_server.py',
    'frontend/src/v5/CircuitBoard.tsx', 'frontend/src/v5/GeneratedPlay.tsx', 'frontend/src/v5/GeneratedScene.tsx',
    'frontend/src/v5/Workspace.tsx', 'frontend/src/v5/client.ts', 'frontend/src/v5/v5.css',
    'backend/app/api/v5.py', 'backend/app/storage/v5.py', 'backend/app/ai/v5.py',
    'backend/app/domain/generation_content_v2.py', 'backend/app/domain/generation_observability.py',
    'scripts/generation_trace.py',
  ];
  const html = await fs.readFile(path.join(root, 'frontend/dist-v5/index.html'), 'utf8');
  const resources = [...html.matchAll(/(?:src|href)=["'](\/assets\/[^"']+\.(?:js|css))["']/g)].map(match => match[1]);
  if (!resources.some(resource => resource.endsWith('.js'))) throw Error('Built main entry missing');
  const assets = [];
  for (const resource of new Set(resources)) {
    if (resource.includes('..') || resource.includes('\\') || resource.includes('?')) throw Error('Unsupported built resource path');
    assets.push(await fingerprint(`frontend/dist-v5${resource}`));
  }
  return { git: { revision, dirty, dirty_scope: 'tracked working tree; no file contents recorded' }, sources: await Promise.all(sourceFiles.map(fingerprint)), build: { index: await fingerprint('frontend/dist-v5/index.html'), entry_resources: assets, freshly_built_by_this_run: false } };
}
async function bindFinishSource() {
  const resultPath = path.resolve(root, resumeFrom);
  const bytes = await fs.readFile(resultPath);
  const first = JSON.parse(bytes.toString('utf8'));
  const coreNames = ['list theme', 'archive theme and Synthetic story', 'completed modules disabled cursor not wait', 'completed submit disabled cursor not wait', 'real pending aria-busy and cursor', 'rotation pending recovered', '44px circuit 1280', '44px circuit 390', '44px circuit 812', 'real selected save restore', 'restore early observation and clues'];
  const currentSources = provenance.sources.filter(source => source.path !== 'tests/v5/run_experience_browser.mjs');
  const originalController = first.provenance?.sources?.find(source => source.path === 'tests/v5/run_experience_browser.mjs');
  const validResult = path.basename(resultPath) === 'browser-result.json' && first.kind === 'Synthetic focused experience browser' && /^[0-9a-f-]{36}$/i.test(first.run_id || '') && !first.first_result && first.browser_executed === true && first.exit_code === 1 && first.execution_status === 'FAILED' && first.owned_server_stopped === true && first.player8001_service_contacted === false && first.paid_calls === 0 && first.checks?.some(item => item.name === 'execution failure' && !item.pass && item.context?.stage === 'relogin-and-legacy') && coreNames.every(name => first.checks?.some(item => item.name === name && item.pass === true)) && /^[0-9a-f]{64}$/i.test(originalController?.sha256 || '');
  const sameSources = currentSources.every(source => first.provenance?.sources?.some(original => original.path === source.path && original.sha256 === source.sha256 && original.bytes === source.bytes)) && first.provenance?.sources?.length === provenance.sources.length;
  const sameBuild = JSON.stringify(first.provenance?.build) === JSON.stringify(provenance.build);
  let ownedTemp = false;
  if (typeof first.owned_temp === 'string') {
    const actualTemp = await fs.realpath(first.owned_temp), tempRoot = await fs.realpath(os.tmpdir());
    const tempStat = await fs.lstat(first.owned_temp), databaseStat = await fs.lstat(path.join(actualTemp, 'game-v5.sqlite'));
    ownedTemp = path.dirname(actualTemp).toLowerCase() === tempRoot.toLowerCase() && path.basename(actualTemp).startsWith('campus-experience-') && tempStat.isDirectory() && !tempStat.isSymbolicLink() && databaseStat.isFile() && !databaseStat.isSymbolicLink();
    if (ownedTemp) temp = actualTemp;
  }
  firstResult = { path: path.relative(root, resultPath).replaceAll('\\', '/'), run_id: first.run_id, sha256: createHash('sha256').update(bytes).digest('hex'), original_controller_sha256: originalController?.sha256 || null, current_controller_sha256: provenance.sources.find(source => source.path === 'tests/v5/run_experience_browser.mjs').sha256 };
  check('bound auth finish source', { valid_first_result: validResult, same_product_and_fixture_sources: sameSources, same_actual_build: sameBuild, explicit_owned_temp_valid: ownedTemp }, { valid_first_result: true, same_product_and_fixture_sources: true, same_actual_build: true, explicit_owned_temp_valid: true }, validResult && sameSources && sameBuild && ownedTemp, { first_result: firstResult.path, first_run_id: firstResult.run_id, scope: 'auth-and-legacy-only' });
}
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function stable() { await page.waitForFunction(() => !document.querySelector('[aria-busy="true"]')); }
async function shot(name) {
  const filename = name + '.png';
  await page.screenshot({ path: path.join(out, filename), fullPage: true });
  screenshots.push({ path: filename, stage, viewport: page.viewportSize(), captured_at_utc: new Date().toISOString() });
}
async function sizes(label) {
  const values = await page.locator('button:visible,input:visible,select:visible,textarea:visible').evaluateAll(elements => elements.filter(element => !element.disabled).map((element, index) => {
    const rect = element.getBoundingClientRect();
    return { index, tag: element.tagName.toLowerCase(), type: element.getAttribute('type'), label: (element.getAttribute('aria-label') || (element.tagName === 'BUTTON' ? element.innerText : '')).slice(0, 150), width: rect.width, height: rect.height };
  }));
  check('44px ' + label, { controls: values, minimum_width: Math.min(...values.map(value => value.width)), minimum_height: Math.min(...values.map(value => value.height)) }, { minimum_width: 44, minimum_height: 44, at_least_one_control: true }, minimumControlSizePass(values), { scope: 'visible enabled buttons and form controls', label });
  const layout = await page.evaluate(() => ({ scroll_width: document.documentElement.scrollWidth, viewport_width: innerWidth, viewport_height: innerHeight }));
  check('no overflow ' + label, layout, { scroll_width_at_most: layout.viewport_width + 1 }, layout.scroll_width <= layout.viewport_width + 1, { tolerance_px: 1 });
}
function publicCounts(visibleState) {
  const circuits = visibleState?.minigames?.circuits || [visibleState?.minigames?.circuit].filter(Boolean);
  return { status: visibleState?.status || null, objects: visibleState?.objects?.length ?? null, clues: visibleState?.clues?.length ?? null, inventory: visibleState?.inventory?.length ?? null, circuits: circuits.length, completed_circuits: circuits.filter(circuit => circuit.status === 'completed').length };
}
async function modules() {
  return page.locator('.v5-circuit-module').evaluateAll(elements => elements.map((element, index) => ({ index, label: element.getAttribute('aria-label'), completed: Boolean(element.closest('.v5-circuit-panel.is-completed')), disabled: element.disabled, cursor: getComputedStyle(element).cursor })));
}
async function post(click, suffix = '/actions') {
  const wait = page.waitForResponse(response => response.request().method() === 'POST' && new URL(response.url()).pathname.endsWith(suffix));
  await click();
  const response = await wait, body = await response.json();
  if (body.data?.visible_state) state = body.data.visible_state;
  if (body.visible_state) state = body.visible_state;
  await stable();
  return { response, body };
}
async function close() { const button = page.getByRole('button', { name: '关闭面板', exact: true }); if (await button.isVisible()) await button.click(); }
async function login(register) {
  if (register) await page.getByRole('button', { name: '第一次来？注册本地账户', exact: true }).click();
  await page.getByLabel('用户名（3–24位字母、数字或下划线）', { exact: true }).fill('experience_synthetic');
  await page.getByLabel('密码（12–128位）', { exact: true }).fill('Synthetic-Experience-only!');
  await page.getByRole('button', { name: register ? '注册并进入' : '登录', exact: true }).click();
  await page.getByRole('heading', { name: '我的关卡', exact: true }).waitFor();
}
async function logoutForRelogin() {
  const responseWait = page.waitForResponse(response => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/v2/auth/logout');
  await page.getByRole('button', { name: '退出登录', exact: true }).click();
  const response = await responseWait;
  await page.getByLabel('用户名（3–24位字母、数字或下划线）', { exact: true }).waitFor();
  await stable();
  const toggle = page.getByRole('button', { name: '已有账户，返回登录', exact: true });
  if (await toggle.isVisible()) await toggle.click();
  await page.getByRole('button', { name: '登录', exact: true }).waitFor();
  const form = { logout_http_status: response.status(), auth_form_visible: await page.locator('.v5-auth').isVisible(), login_button_visible: await page.getByRole('button', { name: '登录', exact: true }).isVisible(), busy_elements: await page.locator('[aria-busy="true"]').count() };
  check('logout completed before relogin', form, { logout_http_ok: true, auth_form_visible: true, login_button_visible: true, busy_elements: 0 }, response.ok() && form.auth_form_visible && form.login_button_visible && form.busy_elements === 0, { operation: 'logout POST, stable auth form, then login mode' });
}
async function startGame() {
  await page.getByRole('button', { name: /^(开始|继续)探索 →$/ }).click();
  await page.locator('.v5-hotspots button:enabled').first().waitFor();
  await stable();
}

try {
  if (!finishAuth) check('isolated judgement self-test', selfTest, { all_cases_pass: true, real_ui_executed: false }, selfTest.pass);
  provenance = await sourceContext();
  const require = createRequire(path.join(root, 'frontend/package.json'));
  const { chromium } = require('@playwright/test');
  if (finishAuth) await bindFinishSource();
  else temp = await fs.mkdtemp(path.join(os.tmpdir(), 'campus-experience-'));
  const available = await new Promise(resolve => { const listener = net.createServer(); listener.once('error', () => resolve(false)); listener.listen(8002, '127.0.0.1', () => listener.close(() => resolve(true))); });
  check('owned port8002 available', { available, port: 8002 }, { available: true, port: 8002 }, available);
  server = spawn('C:/Users/liyh/.conda/envs/1/python.exe', ['-B', '-X', 'utf8', '-m', 'uvicorn', 'tests.v5.experience_fixture_server:app', '--host', '127.0.0.1', '--port', '8002', '--no-access-log'], { cwd: root, env: { ...process.env, SQLITE_PATH: path.join(temp, 'game-v5.sqlite'), GAMEPLAY_VERSION: 'v5', AI_PROVIDER: 'mock', EXPERIENCE_REUSE_TEMP: finishAuth ? '1' : '0', PYTHONDONTWRITEBYTECODE: '1' }, stdio: 'ignore', windowsHide: true });
  server.on('error', () => {}); // Readiness below reports a safe context failure, without environment/log contents.
  let readiness = false;
  for (let index = 0; index < 70; index++) {
    readiness = await new Promise(resolve => { const request = http.get({ hostname: '127.0.0.1', port: 8002, path: '/health', headers: { host: '127.0.0.1:8001' } }, response => { response.resume(); resolve(response.headers['x-qa-synthetic-experience'] === 'owned-temp-only'); }); request.on('error', () => resolve(false)); request.setTimeout(1000, () => request.destroy()); });
    if (readiness || server.exitCode !== null) break;
    await pause(100);
  }
  check('owned Synthetic server ready', { ready: readiness, owned_temp_available: Boolean(temp) }, { ready: true, owned_temp_available: true }, readiness);
  browser = await chromium.launch({ headless: true, channel: 'chrome' });
  context = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  await context.route('**/*', async route => {
    const request = route.request(), url = new URL(request.url());
    if (['data:', 'blob:'].includes(url.protocol)) return route.continue();
    if (url.origin !== base) { external++; return route.abort(); }
    if (delayAction && url.pathname.endsWith('/actions') && request.method() === 'POST') { delayAction = false; await pause(650); }
    const response = await route.fetch({ url: request.url().replace(base, 'http://127.0.0.1:8002'), headers: { ...request.headers(), host: '127.0.0.1:8001' } });
    if (omitTheme && url.pathname.startsWith('/api/v2/levels') && response.ok()) {
      const body = await response.json();
      if (body.data?.level) delete body.data.level.theme;
      if (body.data?.levels) body.data.levels.forEach(level => delete level.theme);
      return route.fulfill({ response, json: body });
    }
    return route.fulfill({ response });
  });
  page = await context.newPage();
  page.setDefaultTimeout(12000);
  page.on('response', async response => {
    if (response.url().includes('/api/v2/sessions') && response.request().method() === 'GET') {
      try { const body = await response.json(); if (body.data?.visible_state) state = body.data.visible_state; } catch { /* No raw response is logged. */ }
    }
  });
  stage = 'registration-and-create';
  browserExecuted = true;
  await page.goto(base);
  if (!finishAuth) {
  await login(true);
  await sizes('create desktop'); await shot('create-desktop');
  stage = 'theme-and-generation';
  await page.getByLabel(/校园主题/).fill(theme);
  await page.getByLabel(/^房间数量/).selectOption('1');
  await page.getByLabel(/^难度/).selectOption('hard');
  await page.getByLabel(/本次生成的 DeepSeek API Key/).fill('SYNTHETIC-ONLY-NOT-A-REAL-KEY');
  await page.getByRole('button', { name: '生成关卡 →', exact: true }).click();
  await page.getByRole('button', { name: '开始探索 →', exact: true }).waitFor({ timeout: 20000 });
  const listedTheme = await page.locator('.v5-level-description').innerText();
  check('list theme', listedTheme, theme, listedTheme === theme, { room_count: 1, difficulty: 'hard', theme });
  const inputEmpty = await page.getByLabel(/本次生成的 DeepSeek API Key/).inputValue() === '';
  check('synthetic input cleared', { empty: inputEmpty }, { empty: true }, inputEmpty, { input_value_recorded: false });
  await startGame();
  await page.locator('.v5-story summary').click();
  const archive = await page.locator('.v5-story').innerText();
  check('archive theme and Synthetic story', { theme_present: archive.includes(theme), story_present: archive.includes(story) }, { theme_present: true, story_present: true }, archive.includes(theme) && archive.includes(story), { expected_theme: theme, expected_story: story });
  await shot('game-desktop');
  stage = 'save';
  await page.getByRole('button', { name: '进度与存档', exact: true }).click(); await stable();
  await page.getByLabel('存档名称', { exact: true }).fill('Synthetic线路前');
  const savedCounts = publicCounts(state);
  const saved = await post(() => page.getByRole('button', { name: '保存新时刻', exact: true }).click(), '/saves');
  check('save accepted', { http_status: saved.response.status(), counts: publicCounts(state) }, { http_ok: true, counts: savedCounts }, saved.response.ok() && JSON.stringify(publicCounts(state)) === JSON.stringify(savedCounts), { name: 'Synthetic线路前' });
  await page.locator('.v5-save').waitFor(); await close();
  stage = 'circuit-error-and-busy';
  await post(() => page.getByRole('button', { name: '查看观测台配电线路', exact: true }).click());
  check('actual 3x3 modules', { count: await page.locator('.v5-circuit-module').count() }, { count: 9 }, await page.locator('.v5-circuit-module').count() === 9);
  const wrong = await post(() => page.getByRole('button', { name: '检查线路', exact: true }).click());
  const wrongCode = wrong.body.error?.code || null;
  check('actual disconnected circuit error', { error_code: wrongCode, http_status: wrong.response.status() }, { error_code: 'WRONG_CODE' }, wrongCode === 'WRONG_CODE', { operation: 'submit_circuit', circuit_initially_disconnected: true });
  const recovered = { error_visible: await page.locator('.v5-error[role="alert"]').isVisible(), aria_busy: await page.locator('.v5-generated').getAttribute('aria-busy'), modules: await modules() };
  check('error shown and busy recovered', recovered, { error_visible: true, aria_busy: 'false', modules_enabled: true, cursor_not: ['wait', 'progress'] }, recovered.error_visible && recovered.aria_busy === 'false' && recovered.modules.every(module => !module.disabled && !['wait', 'progress'].includes(module.cursor)));
  const rotations = [1, 1, 2, 2, 0, 0, 0, 1, 3]; let rotationsSent = 0;
  for (let index = 0; index < 9; index++) for (let turn = 0; turn < rotations[index]; turn++) {
    if (rotationsSent === 0) {
      delayAction = true;
      const wait = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/actions'));
      await page.locator('.v5-circuit-module').nth(index).click();
      await page.locator('.v5-generated[aria-busy="true"]').waitFor();
      const pending = { aria_busy: await page.locator('.v5-generated').getAttribute('aria-busy'), modules: await modules() };
      check('real pending aria-busy and cursor', pending, { aria_busy: 'true', module_count: 9, modules_disabled: true, module_cursor: 'wait' }, pendingCircuitPass(pending), { operation: 'rotate_circuit', module_index: index, transport_delay_ms: 650 });
      const response = await wait; state = (await response.json()).data.visible_state; await stable();
      const after = { aria_busy: await page.locator('.v5-generated').getAttribute('aria-busy'), modules: await modules() };
      check('rotation pending recovered', after, { aria_busy: 'false', modules_enabled: true, cursor_not: ['wait', 'progress'] }, after.aria_busy === 'false' && after.modules.every(module => !module.disabled && !['wait', 'progress'].includes(module.cursor)));
    } else await post(() => page.locator('.v5-circuit-module').nth(index).click());
    rotationsSent++;
  }
  await post(() => page.getByRole('button', { name: '检查线路', exact: true }).click());
  await page.getByRole('button', { name: '线路已接通', exact: true }).waitFor();
  const completedModules = await modules();
  check('completed modules disabled cursor not wait', completedModules, { count: 9, each_completed: true, each_disabled: true, cursor_not: ['wait', 'progress'] }, completedCircuitPass(completedModules), { rotations_sent: rotationsSent });
  const completedSubmit = await page.getByRole('button', { name: '线路已接通', exact: true }).evaluate(element => ({ disabled: element.disabled, cursor: getComputedStyle(element).cursor }));
  check('completed submit disabled cursor not wait', completedSubmit, { disabled: true, cursor_not: ['wait', 'progress'] }, completedSubmit.disabled && !['wait', 'progress'].includes(completedSubmit.cursor));
  stage = 'responsive';
  for (const [width, height] of [[1280, 720], [390, 844], [812, 375]]) {
    await page.setViewportSize({ width, height }); await sizes('circuit ' + width);
    const panel = await page.locator('.v5-panel').evaluate(element => ({ scroll_height: element.scrollHeight, client_height: element.clientHeight, overflow_y: getComputedStyle(element).overflowY }));
    check('panel scrollable ' + width, panel, { fits_or_scrollable: true, scrollable_values: ['auto', 'scroll'] }, panel.scroll_height <= panel.client_height + 1 || ['auto', 'scroll'].includes(panel.overflow_y));
    await shot('circuit-' + width);
  }
  await close(); await page.setViewportSize({ width: 390, height: 844 }); await sizes('scene mobile'); await shot('game-mobile');
  stage = 'restore';
  await page.getByRole('button', { name: '进度与存档', exact: true }).click(); await stable();
  await page.getByRole('button', { name: '读取', exact: true }).click();
  const beforeRestore = publicCounts(state);
  const restored = await post(() => page.getByRole('button', { name: '确认读取', exact: true }).click(), '/restore');
  const afterRestore = publicCounts(state);
  check('real selected save restore', { http_status: restored.response.status(), before: beforeRestore, after: afterRestore }, { http_ok: true, after: savedCounts }, restored.response.ok() && JSON.stringify(afterRestore) === JSON.stringify(savedCounts), { selected_synthetic_save_name: 'Synthetic线路前' });
  check('restore early observation and clues', afterRestore, { circuits: 0, clues: 0 }, afterRestore.circuits === 0 && afterRestore.clues === 0);
  } else {
    stage = 'auth-resume-existing-account';
    await login(false);
  }
  stage = 'relogin-and-legacy';
  await logoutForRelogin();
  await login(false);
  const reloggedTheme = await page.locator('.v5-level-description').innerText();
  check('theme survives relogin', reloggedTheme, theme, reloggedTheme === theme);
  omitTheme = true; await page.reload(); await page.getByRole('heading', { name: '我的关卡', exact: true }).waitFor();
  const legacyDescription = await page.locator('.v5-level-description').innerText();
  check('simulated legacy omission story fallback', legacyDescription, story, legacyDescription === story, { simulation: 'theme omitted from public metadata response' });
  await startGame(); await page.locator('.v5-story summary').click();
  const legacyArchive = await page.locator('.v5-story').innerText();
  check('simulated legacy no theme accepted', { theme_heading_present: legacyArchive.includes('你的创作主题'), story_present: legacyArchive.includes(story) }, { theme_heading_present: false, story_present: true }, !legacyArchive.includes('你的创作主题') && legacyArchive.includes(story), { simulation: 'theme omitted from public metadata response' });
  check('no external browser requests', { count: external }, { count: 0 }, external === 0);
  exit = 0;
} catch (error) {
  checks.push({ name: 'execution failure', pass: false, expected: 'focused flow completes', actual: { error_type: error.constructor.name, error_code: typeof error.code === 'string' ? error.code : null }, input: {}, context: { stage, viewport: page?.viewportSize() || null, synthetic: true }, observed_at_utc: new Date().toISOString() });
} finally {
  try { if (browser) await browser.close(); } catch { exit = 1; }
  if (server) {
    serverClosed = await new Promise(resolve => {
      if (server.exitCode !== null || server.signalCode !== null) return resolve(true);
      server.once('close', () => resolve(true)); server.kill(); setTimeout(() => resolve(false), 4000);
    });
    if (!serverClosed) exit = 1;
    checks.push({ name: 'owned server stopped', pass: serverClosed, expected: true, actual: serverClosed, input: { owned_port: 8002 }, context: { stage: 'cleanup', synthetic: true }, observed_at_utc: new Date().toISOString() });
  }
  const result = {
    kind: 'Synthetic focused experience browser', run_id: runId, started_at_utc: startedAt, ended_at_utc: new Date().toISOString(),
    execution_status: !browserExecuted ? 'NOT_RUN' : exit === 0 ? 'COMPLETED' : 'FAILED', browser_executed: browserExecuted, exit_code: exit,
    ...(stageId ? { stage_id: stageId } : {}),
    scope: finishAuth ? 'auth-and-legacy-only' : 'full-focused-flow', first_result: firstResult || null,
    provenance: provenance || null, checks, screenshots, owned_temp: temp || null, owned_server_stopped: serverClosed,
    player8001_service_contacted: false, transport: 'isolated browser context forwards all 8001 requests to owned8002 with original Host/Origin',
    paid_calls: 0, real_model_semantic_quality_tested: false, legacy_theme_omission_explicit_simulation: true,
    privacy: 'Synthetic fixture only; no credential value, Cookie, token, full state, hidden definition, or raw server log is recorded',
  };
  await fs.writeFile(path.join(out, 'browser-result.json'), JSON.stringify(result, null, 2) + '\n', { flag: 'wx' });
  console.log(JSON.stringify({ run_id: runId, execution_status: result.execution_status, exit_code: exit, stage, checks: checks.length, failed: checks.filter(item => !item.pass).map(item => item.name), screenshots: screenshots.length, output: out, owned_server_stopped: serverClosed }));
}
process.exitCode = exit;
