// Independent follow-up of 74eb523: only gaps left by the implementation run.
// Synthetic fixture and owned TEMP only; never sends traffic to the player service.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import net from 'node:net';
import http from 'node:http';
import { createHash, randomUUID } from 'node:crypto';
import { spawn, execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const runId = randomUUID(), started = new Date().toISOString();
const relative = `evidence/project/stages/v5-rainy-astronomy-ui/automated/review-${started.replace(/[:.]/g, '-')}-${runId.slice(0, 8)}`;
const out = path.join(root, relative), base = 'http://127.0.0.1:8001';
await fs.mkdir(out, { recursive: false });
const checks = [], screenshots = [], actionCounts = {}, errors = [];
let server, browser, page, temp, state, panelId = null, external = 0, blocked = null, stopped = false;
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
function check(name, actual, expected, pass) {
  checks.push({ name, actual, expected, pass: Boolean(pass), observed_at_utc: new Date().toISOString() });
}
async function shot(name) {
  await page.screenshot({ path: path.join(out, `${name}.png`), fullPage: true });
  screenshots.push(`${name}.png`);
}
async function stable() {
  await page.waitForFunction(() => document.querySelector('.v5-game')?.getAttribute('aria-busy') !== 'true');
  await pause(70);
}
async function post(click, suffix = '/actions') {
  const waiting = page.waitForResponse(response => response.request().method() === 'POST' && new URL(response.url()).pathname.endsWith(suffix));
  await click();
  const response = await waiting, body = await response.json();
  const next = body.data?.visible_state || body.visible_state;
  if (next) state = next;
  await stable();
  if (!response.ok()) throw Error(`Synthetic action rejected: ${response.status()}`);
  return body;
}
async function close() {
  const button = page.getByRole('button', { name: '关闭面板', exact: true });
  if (await button.isVisible()) await button.click();
  panelId = null;
}
async function open(id) {
  if (panelId === id && await page.locator('.v5-sheet').isVisible()) return;
  await close();
  await post(() => page.locator(`.v5-hotspots button[data-object="${id}"]`).click());
  await page.locator('.v5-sheet').waitFor(); panelId = id;
}
async function create(rooms, difficulty, theme) {
  await page.getByLabel(/校园主题/).fill(theme);
  await page.getByLabel(/^房间数量/).selectOption(String(rooms));
  await page.getByLabel(/^难度/).selectOption(difficulty);
  await page.getByLabel(/本次生成的 DeepSeek API Key/).fill('SYNTHETIC-ONLY-NOT-A-REAL-KEY');
  await page.getByRole('button', { name: /^生成关卡/ }).click();
  const card = page.locator('.v5-level-card').filter({ hasText: `${rooms} 间房` }).first();
  await card.waitFor({ timeout: 20000 });
  await card.getByRole('button', { name: /探索/ }).click();
  await page.locator('.v5-hotspots button:enabled').first().waitFor({ timeout: 20000 });
  await stable();
}
function witness(rooms, difficulty) {
  // Answers belong exclusively to the deterministic synthetic fixture; kept in memory.
  const code = `import json; from backend.app.domain.generated import make_fixture,compile_level; print(json.dumps(compile_level(make_fixture(${rooms},'${difficulty}'),${rooms},'${difficulty}').witness))`;
  return JSON.parse(execFileSync('C:/Users/liyh/.conda/envs/1/python.exe', ['-B', '-X', 'utf8', '-c', code], { cwd: root, encoding: 'utf8', windowsHide: true, timeout: 30000 }));
}
async function replay(steps) {
  for (const step of steps) {
    const { tool, arguments: args } = step;
    if (tool === 'inspect') {
      if (!(state.observed_object_ids || []).includes(args.object_id)) await open(args.object_id);
      continue;
    }
    if (tool === 'move') {
      await close();
      const index = state.exits.findIndex(exit => exit.destination_id === args.destination_id);
      await post(() => page.locator('.v5-exits button').nth(index).click());
      panelId = null;
      if (state.status !== 'won') {
        await page.locator('.v5-hotspots button:enabled').first().waitFor();
        if (state.room.room_id === 'G3') {
          const actual = await page.locator('.v5-scene').getAttribute('data-background');
          check('third room uses themed control background', actual, '/art-themes/rainy-astronomy/backgrounds/neutral_control.png', actual?.endsWith('/neutral_control.png'));
          await shot('third-room');
        }
      }
    } else {
      const object = tool === 'take'
        ? state.objects.find(object => object.actions.some(action => action.tool === 'take' && action.arguments.item_id === args.item_id))
        : state.objects.find(object => (object.target_id || object.object_id) === args.target_id);
      if (!object) throw Error(`Missing synthetic target for ${tool}`);
      await open(object.object_id);
      if (tool === 'take') {
        const action = state.objects.find(value => value.object_id === object.object_id).actions.find(value => value.tool === 'take');
        await post(() => page.getByRole('button', { name: action.label, exact: true }).click());
        panelId = null;
      } else if (tool === 'submit_code') {
        await page.locator('.v5-code input').fill(args.code);
        await post(() => page.getByRole('button', { name: '提交密码', exact: true }).click());
      } else if (tool === 'use_item') {
        const item = state.inventory.find(item => item.item_id === args.item_id);
        await post(() => page.getByRole('button', { name: `使用 ${item.name}`, exact: true }).click());
      } else if (tool === 'rotate_circuit') {
        const boards = state.minigames.circuits || [state.minigames.circuit];
        const board = boards.find(board => board.target_id === args.target_id);
        const index = board.modules.findIndex(module => module.module_id === args.module_id);
        await post(() => page.locator('.v5-circuit-module').nth(index).click());
      } else if (tool === 'submit_circuit') {
        await post(() => page.getByRole('button', { name: '检查线路', exact: true }).click());
        const boards = state.minigames.circuits || [state.minigames.circuit];
        const board = boards.find(board => board.target_id === args.target_id);
        check(`circuit ${state.room.room_id} submits through actual UI`, board.status, 'completed', board.status === 'completed');
      } else if (tool === 'submit_sequence') {
        const boards = state.minigames.sequences || [state.minigames.sequence];
        const board = boards.find(board => board.target_id === args.target_id);
        await page.getByRole('button', { name: '清除草稿', exact: true }).click();
        for (const id of args.device_ids) {
          const device = board.devices.find(device => device.device_id === id);
          await page.getByRole('button', { name: `${device.symbol} ${device.label}`, exact: true }).click();
        }
        await post(() => page.getByRole('button', { name: '提交顺序', exact: true }).click());
        const next = (state.minigames.sequences || [state.minigames.sequence]).find(board => board.target_id === args.target_id);
        check('sequence submits through actual UI', next.status, 'completed', next.status === 'completed');
        await shot('sequence-completed');
      } else throw Error(`Unsupported synthetic witness tool: ${tool}`);
    }
    actionCounts[tool] = (actionCounts[tool] || 0) + 1;
  }
}
try {
  await new Promise((resolve, reject) => { const probe = net.createServer(); probe.once('error', reject); probe.listen(8002, '127.0.0.1', () => probe.close(resolve)); });
  const require = createRequire(path.join(root, 'frontend/package.json'));
  const { chromium } = require('@playwright/test');
  temp = await fs.mkdtemp(path.join(os.tmpdir(), 'campus-visual-review-'));
  server = spawn('C:/Users/liyh/.conda/envs/1/python.exe', ['-B', '-X', 'utf8', '-m', 'uvicorn', 'tests.v5.visual_ui_fixture_server:app', '--host', '127.0.0.1', '--port', '8002', '--no-access-log'], { cwd: root, env: { ...process.env, SQLITE_PATH: path.join(temp, 'game-v5.sqlite'), GAMEPLAY_VERSION: 'v5', AI_PROVIDER: 'mock' }, stdio: 'ignore', windowsHide: true });
  server.on('error', () => {});
  let ready = false;
  for (let i = 0; i < 100 && !ready; i++) {
    ready = await new Promise(resolve => { const request = http.get({ hostname: '127.0.0.1', port: 8002, path: '/health', headers: { host: '127.0.0.1:8001' } }, response => { response.resume(); resolve(response.headers['x-qa-synthetic-visual'] === 'owned-temp-only'); }); request.on('error', () => resolve(false)); request.setTimeout(800, () => request.destroy()); });
    if (!ready) await pause(100);
  }
  if (!ready) throw Error('Owned synthetic server unavailable');
  browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  await context.route('**/*', async route => {
    const request = route.request(), url = new URL(request.url());
    if (['data:', 'blob:'].includes(url.protocol)) return route.continue();
    if (url.origin !== base) { external++; return route.abort(); }
    if (blocked === url.pathname) return route.fulfill({ status: 404, contentType: 'text/plain', body: 'Synthetic missing artwork' });
    const response = await route.fetch({ url: request.url().replace(base, 'http://127.0.0.1:8002'), headers: { ...request.headers(), host: '127.0.0.1:8001' } });
    return route.fulfill({ response });
  });
  page = await context.newPage(); page.setDefaultTimeout(12000);
  page.on('response', async response => {
    if (!response.url().includes('/api/v2/sessions')) return;
    try { const body = await response.json(); if (body.data?.visible_state) state = body.data.visible_state; } catch { /* no raw response retained */ }
  });
  await page.goto(base);
  await page.getByRole('button', { name: '第一次来？注册本地账户', exact: true }).click();
  await page.getByLabel('用户名（3–24位字母、数字或下划线）', { exact: true }).fill('independent_review');
  await page.getByLabel('密码（12–128位）', { exact: true }).fill('Synthetic-Review-only!');
  await page.getByRole('button', { name: '注册并进入', exact: true }).click();
  await page.getByRole('heading', { name: '我的关卡', exact: true }).waitFor();

  await create(1, 'easy', '冬夜图书馆，寻找借阅登记');
  await open('obj_key');
  const keyCloseup = await page.locator('.v5-closeup img').getAttribute('src');
  check('generic key closeup keeps brass-key identity', keyCloseup, 'key artwork, not fuse', !keyCloseup.includes('fuse'));
  await shot('generic-key-closeup'); await close();
  await page.getByRole('button', { name: '进度与存档', exact: true }).click();
  await page.getByLabel('存档名称', { exact: true }).fill('review-focus-only');
  await post(() => page.getByRole('button', { name: '保存新时刻', exact: true }).click(), '/saves');
  await page.getByRole('button', { name: '删除', exact: true }).click();
  await post(() => page.getByRole('button', { name: '确认删除', exact: true }).click(), '/delete');
  await page.keyboard.press('Tab');
  const focus = await page.evaluate(() => ({ in_panel: Boolean(document.activeElement?.closest('.v5-overlay')), text: document.activeElement?.textContent?.trim().slice(0, 60) }));
  check('focus remains in open save panel after deleting focused row', focus, { in_panel: true }, focus.in_panel);
  await shot('focus-after-delete'); await close();
  await replay(witness(1, 'easy'));
  await page.locator('.v5-victory').waitFor();
  const ending = await page.locator('.v5-victory-lead').innerText();
  check('generic ending avoids unrelated fixed astronomy story', ending, 'generic/theme-neutral ending', !ending.includes('观测记录'));
  await shot('generic-ending');
  await page.getByRole('button', { name: '我的关卡', exact: true }).click();
  await page.getByRole('heading', { name: '我的关卡', exact: true }).waitFor();

  await create(3, 'hard', '雨夜里的天文社旧活动室，寻找封存的观测记录');
  blocked = '/art-themes/rainy-astronomy/closeups/note-logbook.png';
  await open('obj_source');
  await page.waitForFunction(() => document.querySelector('.v5-closeup img')?.complete);
  const missing = await page.locator('.v5-closeup img').evaluate(image => ({ src: new URL(image.src).pathname, natural_width: image.naturalWidth }));
  check('missing closeup uses a usable fallback image', missing, { natural_width_greater_than: 0 }, missing.natural_width > 0);
  await shot('missing-closeup'); blocked = null; await close();
  await replay(witness(3, 'hard'));
  check('three-room hard synthetic route reaches server victory', { status: state.status, room: state.room.room_id, action_counts: actionCounts }, { status: 'won' }, state.status === 'won');
  check('no external browser requests', external, 0, external === 0);
} catch (error) {
  errors.push({ type: error.constructor.name, message: String(error.message).split('\n')[0].slice(0, 240) });
  try { if (page) await shot('unexpected-execution-stop'); } catch { /* best effort */ }
} finally {
  if (browser) await browser.close();
  if (server) stopped = await new Promise(resolve => { if (server.exitCode !== null) return resolve(true); server.once('close', () => resolve(true)); server.kill(); setTimeout(() => resolve(false), 4000); });
  const exitCode = errors.length || !stopped || checks.some(check => !check.pass) ? 1 : 0;
  const result = { kind: 'Independent focused visual UI review', run_id: runId, started_at_utc: started, ended_at_utc: new Date().toISOString(), source_commit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8', windowsHide: true }).trim(), controller_sha256: createHash('sha256').update(await fs.readFile(fileURLToPath(import.meta.url))).digest('hex'), original_implementation_result: 'automated/browser-2026-10-28T16-20-30-946Z-97ce062e/browser-result.json', checks, errors, screenshots, exit_code: exitCode, paid_calls: 0, new_builds: 0, player8001_contacted: false, owned_server_stopped: stopped, temporary_database: temp, limits: ['Synthetic fixture only; private synthetic witness kept in memory', 'Not a real-model quality or human acceptance result'] };
  await fs.writeFile(path.join(out, 'result.json'), JSON.stringify(result, null, 2) + '\n', { flag: 'wx' });
  console.log(JSON.stringify({ output: relative, exit_code: exitCode, checks: checks.length, failures: checks.filter(check => !check.pass).map(check => check.name), errors, owned_server_stopped: stopped }));
  process.exitCode = exitCode;
}
