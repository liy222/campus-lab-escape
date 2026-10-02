// Owner development check. Independent acceptance tests are owned by QA in tests/.
import { chromium, expect } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const output = resolve('..', 'evidence', 'frontend', 'T07-owner-smoke-20261002');
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const checks = [];
const failures = [];
page.on('pageerror', error => failures.push(error.message));
const check = (name, details = {}) => checks.push({ name, result: 'passed', ...details });
try {
  await page.goto(process.env.FRONTEND_SMOKE_URL || 'http://127.0.0.1:5107/');
  await page.getByRole('button', { name: '开始新游戏 →', exact: true }).click();
  await expect(page.locator('#room-title')).toBeVisible();
  await expect(page.locator('.clues')).toContainText('第一页，等待发现');
  await expect(page.locator('.inventory')).toContainText('背包还是空的');
  check('create: initial room, empty inventory and undiscovered clues');
  for (const width of [1280, 768, 390]) {
    await page.setViewportSize({ width, height: 900 });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    expect(overflow).toBe(false);
    await page.screenshot({ path: resolve(output, `initial-${width}.png`), fullPage: true });
    check('responsive: no horizontal overflow', { width });
  }
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.locator('.object-tile').filter({ hasText: '值班便签' }).click();
  await page.locator('.object-actions').getByRole('button', { name: '查看', exact: false }).click();
  await expect(page.locator('.clue-list li')).toHaveCount(1);
  const note = await page.locator('.clue-list li').first().innerText();
  await page.locator('.object-tile').filter({ hasText: '值班柜' }).click();
  await page.locator('.object-actions').getByRole('button', { name: '查看', exact: false }).click();
  await expect(page.locator('.clue-list li')).toHaveCount(2);
  check('inspect: note and cabinet clues discovered through UI');
  await page.getByLabel('值班柜密码').fill('0');
  await page.getByRole('button', { name: '输入密码', exact: true }).click();
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.locator('.inventory')).toContainText('背包还是空的');
  await page.screenshot({ path: resolve(output, 'wrong-code.png'), fullPage: true });
  check('wrong user code: error visible and cabinet remains closed');
  // Derive input only from text already discovered by this player. No secret answer fixture.
  const symbolValues = new Map([...note.matchAll(/(三角|圆|方)记为([0-9]+)/g)].map(match => [match[1], match[2]]));
  const cabinetClue = await page.locator('.clue-list li').nth(1).innerText();
  const symbols = [...cabinetClue.matchAll(/三角|圆|方/g)].map(match => match[0]);
  const code = symbols.map(symbol => symbolValues.get(symbol)).join('');
  expect(code.length).toBeGreaterThan(0);
  await page.getByLabel('值班柜密码').fill(code);
  await page.getByRole('button', { name: '输入密码', exact: true }).click();
  await expect(page.locator('.object-tile').filter({ hasText: '门卡' })).toBeVisible();
  await page.locator('.object-tile').filter({ hasText: '门卡' }).click();
  await page.getByRole('button', { name: '拾取', exact: false }).click();
  await expect(page.locator('.inventory-item')).toContainText('门卡');
  await page.locator('.inventory-item .use-button').click();
  await expect(page.locator('.exit-button')).toBeEnabled();
  await page.locator('.exit-button').click();
  await expect(page.locator('.scene .eyebrow')).toContainText('R2');
  await expect(page.locator('.clue-list li')).toHaveCount(2);
  await page.screenshot({ path: resolve(output, 'r2-entered.png'), fullPage: true });
  check('manual R1: code from visible clues, take card, unlock, move to R2');
  await page.reload();
  await page.locator('.top-actions').getByRole('button', { name: '继续当前游戏', exact: true }).click();
  await expect(page.locator('.scene .eyebrow')).toContainText('R2');
  check('reload: continue existing session from sessionStorage');
  await expect(page.getByRole('button', { name: '保存进度', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: '重新开始', exact: true })).toBeDisabled();
  check('deferred controls explicitly unavailable');
  expect(failures).toEqual([]);
  check('no page runtime errors');
  await writeFile(resolve(output, 'result.json'), JSON.stringify({ scope: 'frontend owner local development smoke; not independent QA or human playtest', checks, runtime_errors: failures }, null, 2));
  console.log(JSON.stringify({ passed: checks.length, evidence: output }));
} catch (error) {
  await writeFile(resolve(output, 'failure.json'), JSON.stringify({ checks, error: error.message, runtime_errors: failures }, null, 2));
  throw error;
} finally { await browser.close(); }
