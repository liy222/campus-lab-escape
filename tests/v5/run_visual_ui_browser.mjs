// Synthetic visual-UI check for the rainy-astronomy theme stage.
// The player's own 8001 service is never contacted: every browser request to
// 127.0.0.1:8001 is forwarded to an owned 8002 fixture with a TEMP database.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import http from 'node:http';
import { createHash, randomUUID } from 'node:crypto';
import { spawn, execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const runId = randomUUID();
const startedAt = new Date().toISOString();
const args = process.argv.slice(2);
let requestedOutput = null;
for (let index = 0; index < args.length; index++) {
  if (args[index] === '--output' && args[index + 1] && !args[index + 1].startsWith('--')) requestedOutput = args[++index];
  else {
    console.error(JSON.stringify({ run_id: runId, status: 'NOT_RUN', reason: 'Only --output <new directory> is supported.' }));
    process.exit(2);
  }
}
let out, stageId = null;
if (requestedOutput) out = path.resolve(root, requestedOutput);
else {
  try {
    const index = JSON.parse(await fs.readFile(path.join(root, 'evidence/project/index.json'), 'utf8'));
    if (typeof index.active_stage !== 'string' || !/^[a-z0-9][a-z0-9_-]{0,79}$/.test(index.active_stage)) throw Error('bad stage');
    stageId = index.active_stage;
    out = path.join(root, 'evidence/project/stages', stageId, 'automated', `browser-${startedAt.replace(/[:.]/g, '-')}-${runId.slice(0, 8)}`);
  } catch {
    console.error(JSON.stringify({ run_id: runId, status: 'NOT_RUN', reason: 'Default output needs a valid evidence/project/index.json active_stage.' }));
    process.exit(2);
  }
}
try {
  await fs.mkdir(path.dirname(out), { recursive: true });
  await fs.mkdir(out);
} catch (error) {
  console.error(JSON.stringify({ run_id: runId, status: 'NOT_RUN', reason: error.code === 'EEXIST' ? 'Output directory already exists.' : 'Output directory could not be created.', output: out }));
  process.exit(2);
}

const base = 'http://127.0.0.1:8001';
const theme = '雨夜里的天文社旧活动室，寻找封存的观测记录';
const otherTheme = '冬夜的图书馆与借阅登记';
const checks = [], screenshots = [];
let server, browser, context, page, temp, provenance, state = null;
let stage = 'startup', external = 0, browserExecuted = false, exit = 1, serverClosed = null;

const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
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
  const sources = [
    'tests/v5/run_visual_ui_browser.mjs', 'tests/v5/visual_ui_fixture_server.py',
    'frontend/src/v5/GeneratedPlay.tsx', 'frontend/src/v5/GeneratedScene.tsx', 'frontend/src/v5/Workspace.tsx',
    'frontend/src/v5/v5.css', 'frontend/src/v5/visual/types.ts', 'frontend/src/v5/visual/registry.ts',
    'frontend/src/v5/visual/scene.ts', 'frontend/src/assets/themes/rainy-astronomy/manifest.json',
  ];
  const html = await fs.readFile(path.join(root, 'frontend/dist-v5/index.html'), 'utf8');
  const resources = [...new Set([...html.matchAll(/(?:src|href)=["'](\/assets\/[^"']+\.(?:js|css))["']/g)].map(match => match[1]))];
  if (!resources.some(resource => resource.endsWith('.js'))) throw Error('built entry missing');
  const assets = [];
  for (const resource of resources) assets.push(await fingerprint(`frontend/dist-v5${resource}`));
  const manifest = JSON.parse(await fs.readFile(path.join(root, 'frontend/src/assets/themes/rainy-astronomy/manifest.json'), 'utf8'));
  const art = [];
  for (const background of Object.values(manifest.backgrounds)) art.push(await fingerprint(`frontend/public${background.src}`));
  for (const group of Object.values(manifest.objects)) for (const variant of Object.values(group)) {
    art.push(await fingerprint(`frontend/public${variant.src}`), await fingerprint(`frontend/public${variant.closeup}`));
  }
  return {
    git: { revision, dirty, dirty_scope: 'tracked working tree; no contents recorded' },
    sources: await Promise.all(sources.map(fingerprint)),
    build: { index: await fingerprint('frontend/dist-v5/index.html'), entry_resources: assets, freshly_built_by_this_run: false },
    art: { pack: manifest.theme_id, version: manifest.pack_version, files: art },
  };
}
async function shot(name, { full = true } = {}) {
  const filename = `${name}.png`;
  await page.screenshot({ path: path.join(out, filename), fullPage: full });
  screenshots.push({ path: filename, stage, viewport: page.viewportSize(), full_page: full, captured_at_utc: new Date().toISOString() });
}
/** Viewport-sized hero shot at 1440x900, then back to the checked 1280x720 layout. */
async function heroShot(name) {
  await page.setViewportSize({ width: 1440, height: 1040 });
  await pause(700);
  await shot(name, { full: false });
  await page.setViewportSize({ width: 1280, height: 720 });
  await pause(500);
}
async function stable() { await page.waitForFunction(() => !document.querySelector('[aria-busy="true"]')); }
async function sizes(label) {
  const controls = await page.locator('button:visible,input:visible,select:visible,textarea:visible').evaluateAll(elements => elements.filter(element => !element.disabled).map((element, index) => {
    const rect = element.getBoundingClientRect();
    return { index, tag: element.tagName.toLowerCase(), label: (element.getAttribute('aria-label') || (element.tagName === 'BUTTON' ? element.innerText : '')).slice(0, 120), width: Math.round(rect.width), height: Math.round(rect.height) };
  }));
  const minimumWidth = Math.min(...controls.map(control => control.width)), minimumHeight = Math.min(...controls.map(control => control.height));
  check(`44px ${label}`, { controls: controls.length, minimum_width: minimumWidth, minimum_height: minimumHeight }, { minimum_width: 44, minimum_height: 44 }, controls.length > 0 && minimumWidth >= 44 && minimumHeight >= 44, { label, smallest: controls.filter(control => control.width < 44 || control.height < 44).slice(0, 5) });
  const layout = await page.evaluate(() => ({ scroll_width: document.documentElement.scrollWidth, viewport_width: innerWidth }));
  check(`no overflow ${label}`, layout, { scroll_width_at_most: layout.viewport_width + 1 }, layout.scroll_width <= layout.viewport_width + 1, { tolerance_px: 1 });
}
async function post(click, suffix = '/actions') {
  const wait = page.waitForResponse(response => response.request().method() === 'POST' && new URL(response.url()).pathname.endsWith(suffix));
  await click();
  const response = await wait;
  const body = await response.json();
  if (body.data?.visible_state) state = body.data.visible_state;
  await stable();
  return { response, body };
}
async function closePanel() {
  const button = page.getByRole('button', { name: '关闭面板', exact: true });
  if (await button.isVisible()) await button.click();
  await pause(250);
}
async function openObjectById(id) {
  await page.locator(`.v5-hotspots button[data-object="${id}"]`).click();
  await page.locator('.v5-sheet').waitFor();
  await pause(300);
}
async function openObject(name) {
  await page.locator(`.v5-hotspots button[aria-label^="查看${name}"]`).click();
  await page.locator('.v5-sheet').waitFor();
  await pause(300);
}
async function login(register) {
  if (register) await page.getByRole('button', { name: '第一次来？注册本地账户', exact: true }).click();
  await page.getByLabel('用户名（3–24位字母、数字或下划线）', { exact: true }).fill('visual_synthetic');
  await page.getByLabel('密码（12–128位）', { exact: true }).fill('Synthetic-Visual-only!');
  await page.getByRole('button', { name: register ? '注册并进入' : '登录', exact: true }).click();
  await page.getByRole('heading', { name: '我的关卡', exact: true }).waitFor();
  await stable();
}
async function createLevel({ roomCount, difficulty, text, marker }) {
  await page.getByLabel(/校园主题/).fill(text);
  await page.getByLabel(/^房间数量/).selectOption(String(roomCount));
  await page.getByLabel(/^难度/).selectOption(difficulty);
  await page.getByLabel(/本次生成的 DeepSeek API Key/).fill('SYNTHETIC-ONLY-NOT-A-REAL-KEY');
  await page.getByRole('button', { name: /^生成关卡/ }).click();
  const card = page.locator('.v5-level-card').filter({ hasText: `${roomCount} 间房` }).filter({ hasText: marker }).first();
  for (let attempt = 0; attempt < 8; attempt++) {
    if (await card.count() && await card.isVisible()) { await stable(); return; }
    await pause(2000);
    await page.getByRole('button', { name: '刷新列表', exact: true }).click().catch(() => {});
  }
  await stable();
  throw Error(`generated level not listed: ${roomCount} rooms / ${marker}`);
}
async function enterLevel(rooms, marker) {
  const card = page.locator('.v5-level-card').filter({ hasText: `${rooms} 间房` }).filter({ hasText: marker }).first();
  await card.getByRole('button', { name: /探索/ }).click();
  await page.locator('.v5-hotspots button').first().waitFor({ timeout: 20000 });
  await pause(1400);
}
async function variants() {
  return page.locator('.v5-hotspots button').evaluateAll(elements => elements.map(element => ({ object: element.getAttribute('data-object'), variant: element.getAttribute('data-variant'), label: element.getAttribute('aria-label') })));
}
async function digits(texts) {
  return texts.map(text => (text.match(/[0-9]/g) || []).join(''));
}
async function solveCode(objectId, answer) {
  await openObjectById(objectId);
  await page.locator('.v5-code input').fill(answer);
  await post(() => page.getByRole('button', { name: '提交密码', exact: true }).click());
  await closePanel();
}

try {
  provenance = await sourceContext();
  const require = createRequire(path.join(root, 'frontend/package.json'));
  const { chromium } = require('@playwright/test');
  temp = await fs.mkdtemp(path.join(os.tmpdir(), 'campus-visual-'));
  server = spawn('C:/Users/liyh/.conda/envs/1/python.exe', ['-B', '-X', 'utf8', '-m', 'uvicorn', 'tests.v5.visual_ui_fixture_server:app', '--host', '127.0.0.1', '--port', '8002', '--no-access-log'], {
    cwd: root,
    env: { ...process.env, SQLITE_PATH: path.join(temp, 'game-v5.sqlite'), GAMEPLAY_VERSION: 'v5', AI_PROVIDER: 'mock', PYTHONDONTWRITEBYTECODE: '1' },
    stdio: 'ignore', windowsHide: true,
  });
  server.on('error', () => {});
  let readiness = false;
  for (let index = 0; index < 90; index++) {
    readiness = await new Promise(resolve => {
      const request = http.get({ hostname: '127.0.0.1', port: 8002, path: '/health', headers: { host: '127.0.0.1:8001' } }, response => {
        response.resume();
        resolve(response.headers['x-qa-synthetic-visual'] === 'owned-temp-only');
      });
      request.on('error', () => resolve(false));
      request.setTimeout(1000, () => request.destroy());
    });
    if (readiness || server.exitCode !== null) break;
    await pause(100);
  }
  check('owned synthetic server ready', { ready: readiness, owned_temp: Boolean(temp) }, { ready: true, owned_temp: true }, readiness);

  browser = await chromium.launch({ headless: true, channel: 'chrome' });
  context = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  await context.route('**/*', async route => {
    const request = route.request(), url = new URL(request.url());
    if (['data:', 'blob:'].includes(url.protocol)) return route.continue();
    if (url.origin !== base) { external++; return route.abort(); }
    const response = await route.fetch({ url: request.url().replace(base, 'http://127.0.0.1:8002'), headers: { ...request.headers(), host: '127.0.0.1:8001' } });
    return route.fulfill({ response });
  });
  page = await context.newPage();
  page.setDefaultTimeout(15000);
  page.on('response', async response => {
    if (response.url().includes('/api/v2/sessions') && response.request().method() === 'GET') {
      try { const body = await response.json(); if (body.data?.visible_state) state = body.data.visible_state; } catch { /* no raw body logged */ }
    }
    if (response.request().method() === 'POST' && /\/actions$|\/saves(\/|$)/.test(new URL(response.url()).pathname)) {
      try { const body = await response.json(); const next = body.data?.visible_state || body.visible_state; if (next) state = next; } catch { /* no raw body logged */ }
    }
  });
  browserExecuted = true;
  stage = 'landing-and-create';
  await page.goto(base);
  await page.getByRole('heading', { name: '校园里的另一扇门' }).waitFor();
  await shot('01-landing');
  await login(true);
  await shot('02-dashboard');
  await createLevel({ roomCount: 1, difficulty: 'easy', text: theme, marker: '天文社' });
  const coverage = await page.locator('.v5-coverage.is-on').innerText().catch(() => '');
  check('creation shows supported theme', { text: coverage }, { mentions_pack: true }, coverage.includes('雨夜天文社'), { theme });

  stage = 'theme-scene';
  await enterLevel(1, "天文社");
  const scene = page.locator('.v5-scene');
  const sceneTheme = await scene.getAttribute('data-theme');
  const background = await scene.getAttribute('data-background');
  check('astronomy pack resolves background', { theme: sceneTheme, background }, { theme: 'rainy-astronomy', background_contains: '/art-themes/rainy-astronomy/backgrounds/neutral_lab.png' }, sceneTheme === 'rainy-astronomy' && (background || '').includes('/art-themes/rainy-astronomy/backgrounds/neutral_lab.png'));
  const mapping = await variants();
  check('every visible object maps to a theme variant', mapping, { count: state.objects.length, all_themed: true }, mapping.length === state.objects.length && mapping.every(entry => entry.variant && entry.variant !== 'generic'), { mapping });
  check('key is a key', mapping.find(entry => entry.label?.includes('黄铜钥匙')), { variant: 'key-brass' }, mapping.some(entry => entry.variant === 'key-brass'));
  await sizes('game 1280');
  await heroShot('03-game-desktop');

  stage = 'closeup';
  await openObject('观测记录册');
  const closeup = await page.locator('.v5-closeup img').getAttribute('data-closeup-src');
  await heroShot('04-closeup-note');
  check('close-up uses theme artwork', { closeup }, { under: '/art-themes/rainy-astronomy/closeups/' }, (closeup || '').startsWith('/art-themes/rainy-astronomy/closeups/'), { object: '观测记录册' });

  stage = 'overlay-behaviour';
  const beforeEscape = await page.locator('.v5-sheet').isVisible();
  await page.keyboard.press('Escape');
  await pause(300);
  const afterEscape = await page.locator('.v5-sheet').count();
  check('escape closes the sheet', { before: beforeEscape, after: afterEscape }, { before: true, after: 0 }, beforeEscape && afterEscape === 0);
  await openObject('观测记录册');
  await page.mouse.click(6, 6);
  await pause(250);
  check('backdrop click does not leak to the scene', { sheet_still_open: await page.locator('.v5-sheet').isVisible(), hotspots_disabled: await page.locator('.v5-hotspots button').first().isDisabled() }, { sheet_still_open: true, hotspots_disabled: true }, await page.locator('.v5-sheet').isVisible() && await page.locator('.v5-hotspots button').first().isDisabled());
  await closePanel();

  stage = 'resize';
  for (const [width, height] of [[1280, 720], [390, 844], [812, 375]]) {
    await page.setViewportSize({ width, height });
    await pause(500);
    await sizes(`game ${width}`);
    await shot(`10-game-${width}`);
  }
  await page.setViewportSize({ width: 1280, height: 720 });

  stage = 'stability';
  const before = await variants();
  await page.reload();
  await page.getByRole('heading', { name: '我的关卡', exact: true }).waitFor();
  await enterLevel(1, "天文社");
  const after = await variants();
  check('theme variants stable across reload', { before, after }, { identical: true }, JSON.stringify(before) === JSON.stringify(after));

  stage = 'early-save';
  await page.getByRole('button', { name: '进度与存档', exact: true }).click();
  await stable();
  await page.getByLabel('存档名称', { exact: true }).fill('提前存档');
  await post(() => page.getByRole('button', { name: '保存新时刻', exact: true }).click(), '/saves');
  await page.locator('.v5-save').first().waitFor();
  const earlyClues = state.clues.length;
  check('early save is listed', { name: await page.locator('.v5-save h3').first().innerText(), clues: earlyClues }, { name: '提前存档', clues_at_most: 1 }, (await page.locator('.v5-save h3').first().innerText()) === '提前存档' && earlyClues <= 1);
  await closePanel();

  stage = 'puzzles-and-victory';
  await openObject('星图资料页');
  await closePanel();
  await openObject('观测记录册');
  await closePanel();
  const clueTexts = (state.clues || []).map(clue => clue.text);
  const [tokens, order] = await digits(clueTexts);
  const answer = order.split('').map(index => tokens[Number(index) - 1]).join('');
  check('code derived from public clues', { tokens, order, answer }, { answer_length: 4 }, answer.length === 4 && /^[0-9]{4}$/.test(answer));
  await openObject('黄铜钥匙');
  const take = page.getByRole('button', { name: /拿取|拿起/ });
  await post(() => take.first().click());
  await closePanel();
  check('key can be taken', { inventory: state.inventory.map(item => item.name) }, { inventory_contains: '黄铜钥匙' }, state.inventory.some(item => item.name === '黄铜钥匙'));
  await openObject('资料终端');
  await page.locator('.v5-code input').fill(answer);
  await heroShot('05-code-panel');
  await post(() => page.getByRole('button', { name: '提交密码', exact: true }).click());
  await closePanel();
  await openObject('封存资料柜');
  const use = page.getByRole('button', { name: /使用 黄铜钥匙/ });
  await post(() => use.first().click());
  await closePanel();
  check('device reaches completed state', { objects: state.objects.map(object => ({ name: object.name, completed: object.completed })) }, { cabinet_completed: true }, state.objects.some(object => object.name.includes('资料柜') && object.completed));
  const mapped = (await variants()).map(entry => entry.variant);
  const loaded = ((await page.locator('.v5-scene').getAttribute('data-textures')) || '').split(' ').filter(Boolean);
  check('completed state art is loaded and drawn', { mapped, loaded }, { every_mapped_variant_loaded: true }, mapped.length > 0 && mapped.every(variant => loaded.includes(`theme:${variant}`)) && loaded.includes('theme:terminal-on') && loaded.includes('theme:cabinet-open'));
  await page.locator('.v5-exits button:enabled').first().click();
  await page.locator('.v5-victory').waitFor();
  await pause(700);
  const settlement = await page.locator('.v5-stats').innerText();
  check('settlement shows server statistics', { settlement, status: state.status }, { status: 'won', has_rating: true }, state.status === 'won' && /评级/.test(settlement) && /线索/.test(settlement));
  await heroShot('06-victory');
  await page.setViewportSize({ width: 390, height: 844 });
  await pause(600);
  const fit = await page.evaluate(() => {
    const stageBox = document.querySelector('.v5-stage').getBoundingClientRect();
    const actions = document.querySelector('.v5-victory-actions').getBoundingClientRect();
    return { stage_bottom: Math.round(stageBox.bottom), actions_bottom: Math.round(actions.bottom), stage_top: Math.round(stageBox.top), actions_top: Math.round(actions.top) };
  });
  check('settlement fits inside the stage on a phone viewport', fit, { actions_within_stage: true }, fit.actions_bottom <= fit.stage_bottom + 1 && fit.actions_top >= fit.stage_top - 1);
  await shot('06b-victory-390', { full: false });
  await page.setViewportSize({ width: 1280, height: 720 });
  await pause(500);
  await page.getByRole('button', { name: '再看一眼场景' }).click();
  await pause(400);
  check('scenery stays visible after closing settlement', { theme: await scene.getAttribute('data-theme'), hotspots: await page.locator('.v5-hotspots button').count() }, { theme: 'rainy-astronomy', hotspots_at_least: 1 }, (await scene.getAttribute('data-theme')) === 'rainy-astronomy' && (await page.locator('.v5-hotspots button').count()) > 0);
  await heroShot('07-victory-scene');

  stage = 'saves-and-notebook';
  await page.getByRole('button', { name: '进度与存档', exact: true }).click();
  await stable();
  await heroShot('08-saves');
  const saveName = await page.locator('.v5-save h3').first().innerText();
  check('save slot is listed', { saveName, clues: state.clues.length }, { name: '提前存档', clues: 2 }, saveName === '提前存档' && state.clues.length === 2);  await closePanel();
  await page.getByRole('button', { name: /^笔记/ }).click();
  await page.locator('.v5-sheet').waitFor();
  const notebookClues = await page.locator('.v5-sheet .v5-clue').count();
  await heroShot('09-notebook');
  check('notebook lists discovered clues', { notebookClues, clueCount: state.clues.length }, { equal: true }, notebookClues === state.clues.length);
  await closePanel();

  stage = 'restore-and-reload';
  await page.getByRole('button', { name: '进度与存档', exact: true }).click();
  await stable();
  await page.getByRole('button', { name: '读取', exact: true }).click();
  const restored = await post(() => page.getByRole('button', { name: '确认读取', exact: true }).click(), '/restore');
  await pause(700);
  check('selected save restores the earlier progress', { http: restored.response.status(), status: state.status, clues: state.clues.length, solved: state.objects.filter(object => object.completed).length }, { http_ok: true, status: 'playing', clues: earlyClues, solved: 0 }, restored.response.ok() && state.status === 'playing' && state.clues.length === earlyClues && state.objects.every(object => !object.completed));
  await page.reload();
  await page.getByRole('heading', { name: '我的关卡', exact: true }).waitFor();
  await enterLevel(1, "天文社");
  const afterRestore = await variants();
  check('theme and variants stay stable after restore and reload', { theme: await page.locator('.v5-scene').getAttribute('data-theme'), variants: afterRestore }, { theme: 'rainy-astronomy', identical_to_first_entry: true }, (await page.locator('.v5-scene').getAttribute('data-theme')) === 'rainy-astronomy' && JSON.stringify(afterRestore) === JSON.stringify(before));
  await page.getByRole('button', { name: '进度与存档', exact: true }).click();
  await stable();
  await page.getByRole('button', { name: '删除', exact: true }).click();
  const deleted = await post(() => page.getByRole('button', { name: '确认删除', exact: true }).click(), '/delete');
  await pause(500);
  check('deleting the slot removes only that save', { http: deleted.response.status(), remaining: await page.locator('.v5-save').count(), status: state.status }, { http_ok: true, remaining: 0, status: 'playing' }, deleted.response.ok() && await page.locator('.v5-save').count() === 0 && state.status === 'playing');
  await closePanel();
  await page.getByRole('button', { name: '我的关卡', exact: true }).click();
  await page.getByRole('heading', { name: '我的关卡', exact: true }).waitFor();

  stage = 'three-rooms';
  await createLevel({ roomCount: 3, difficulty: 'hard', text: theme, marker: '天文社' });
  await enterLevel(3, "天文社");
  const roomOneBackground = await page.locator('.v5-scene').getAttribute('data-background');
  await openObject('观测记录册');
  await closePanel();
  await openObject('星图资料页');
  await closePanel();
  await solveCode('obj_puzzle_0', answer);
  await solveCode('obj_puzzle_1', answer);
  check('three-room level keeps the theme', { background: roomOneBackground, hotspots: await page.locator('.v5-hotspots button').count() }, { themed: true }, (roomOneBackground || '').includes('/art-themes/rainy-astronomy/'));
  await heroShot('11-room1-three-rooms');

  stage = 'circuit-and-sequence';
  await page.locator('.v5-exits button:enabled').first().click();
  await pause(1500);
  await stable();
  const circuitTarget = page.locator('.v5-hotspots button').filter({ hasText: /配电|线路|电源/ }).first();
  if (await circuitTarget.count()) {
    await circuitTarget.click();
    await page.locator('.v5-sheet').waitFor();
    await pause(400);
    const modules = await page.locator('.v5-circuit-module').count();
    check('circuit panel renders nine modules', { modules }, { modules: 9 }, modules === 9);
    await heroShot('12-circuit-panel');
    await closePanel();
  }
  const sequenceTarget = page.locator('.v5-hotspots button').filter({ hasText: /顺序|设备盘/ }).first();
  if (await sequenceTarget.count()) {
    await sequenceTarget.click();
    await page.locator('.v5-sheet').waitFor();
    await pause(400);
    const devices = await page.locator('.v5-sequence-buttons button').count();
    check('sequence panel renders four devices', { devices }, { devices: 4 }, devices === 4);
    await heroShot('13-sequence-panel');
    await closePanel();
  }

  stage = 'fallback-theme';
  await page.getByRole('button', { name: '我的关卡', exact: true }).click();
  await page.getByRole('heading', { name: '我的关卡', exact: true }).waitFor();
  await createLevel({ roomCount: 1, difficulty: 'easy', text: otherTheme, marker: '冬夜' });
  const fallbackCoverage = await page.locator('.v5-coverage').first().innerText().catch(() => '');
  await enterLevel(1, "冬夜");
  const fallbackTheme = await page.locator('.v5-scene').getAttribute('data-theme');
  const fallbackBackground = await page.locator('.v5-scene').getAttribute('data-background');
  check('unsupported theme falls back to generic art', { theme: fallbackTheme, background: fallbackBackground, note: fallbackCoverage }, { theme: 'generic', background_contains: '/art-handpainted/' }, fallbackTheme === 'generic' && (fallbackBackground || '').includes('/art-handpainted/'));
  await heroShot('14-fallback-theme');
  check('no external browser requests', { count: external }, { count: 0 }, external === 0);
  exit = 0;
} catch (error) {
  checks.push({ name: 'execution failure', pass: false, expected: 'visual flow completes', actual: { error_type: error.constructor.name, message: String(error.message).slice(0, 300) }, input: {}, context: { stage, viewport: page?.viewportSize() || null, synthetic: true }, observed_at_utc: new Date().toISOString() });
  try { if (page) await page.screenshot({ path: path.join(out, 'failure-state.png'), fullPage: true }); } catch { /* screenshot is best effort */ }
} finally {
  try { if (browser) await browser.close(); } catch { exit = 1; }
  if (server) {
    serverClosed = await new Promise(resolve => {
      if (server.exitCode !== null || server.signalCode !== null) return resolve(true);
      server.once('close', () => resolve(true));
      server.kill();
      setTimeout(() => resolve(false), 4000);
    });
    if (!serverClosed) exit = 1;
    checks.push({ name: 'owned server stopped', pass: Boolean(serverClosed), expected: true, actual: Boolean(serverClosed), input: { owned_port: 8002 }, context: { stage: 'cleanup', synthetic: true }, observed_at_utc: new Date().toISOString() });
  }
  const result = {
    kind: 'Synthetic visual UI browser', run_id: runId, started_at_utc: startedAt, ended_at_utc: new Date().toISOString(),
    execution_status: !browserExecuted ? 'NOT_RUN' : exit === 0 ? 'COMPLETED' : 'FAILED',
    browser_executed: browserExecuted, exit_code: exit, ...(stageId ? { stage_id: stageId } : {}),
    provenance: provenance || null, checks, screenshots, owned_temp: temp || null, owned_server_stopped: serverClosed,
    player8001_service_contacted: false,
    transport: 'isolated browser context forwards all 8001 requests to owned 8002 with original Host/Origin',
    paid_calls: 0, real_model_semantic_quality_tested: false,
    privacy: 'Synthetic fixture only; no credential, Cookie, token, full state, hidden definition or raw server log is recorded',
  };
  await fs.writeFile(path.join(out, 'browser-result.json'), JSON.stringify(result, null, 2) + '\n', { flag: 'wx' });
  console.log(JSON.stringify({ run_id: runId, execution_status: result.execution_status, exit_code: exit, stage, checks: checks.length, failed: checks.filter(item => !item.pass).map(item => item.name), screenshots: screenshots.length, output: out, owned_server_stopped: serverClosed }));
}
process.exitCode = exit;
