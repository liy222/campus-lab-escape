// Independent hand-painted rebuild review; no execution until Main GO.
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
const focusOnly = process.argv.includes('--focus-only');
if (process.argv.slice(2).some(arg => arg !== '--focus-only')) throw Error('Only --focus-only is supported');
const relative = `evidence/project/stages/v5-handpainted-rebuild/automated/${focusOnly ? 'focus' : 'browser'}-${started.replace(/[:.]/g, '-')}-${runId.slice(0, 8)}`;
const out = path.join(root, relative), base = 'http://127.0.0.1:8001';
await fs.mkdir(out, { recursive: false });
const checks = [], screenshots = [], actionCounts = {}, errors = [], resources = new Map(), blockedCounts = new Map();
const blockedPaths = new Set();
let manifest, catalog, provenance, themeMode = false, stage = "setup", delayBackground = false;
let server, browser, page, temp, state, panelId = null, external = 0, stopped = false;
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
function check(name, actual, expected, pass) {
  checks.push({ name, actual, expected, pass: Boolean(pass), observed_at_utc: new Date().toISOString(), context: { stage, viewport: page?.viewportSize() || null, synthetic: true } });
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
        await roomEvidence();
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
        await completedArt(object); await shot(`circuit-${state.room.room_id}-completed`);
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
        await completedArt(object); await shot('sequence-completed');
      } else throw Error(`Unsupported synthetic witness tool: ${tool}`);
    }
    actionCounts[tool] = (actionCounts[tool] || 0) + 1;
  }
}
const packPath = 'frontend/src/assets/themes/rainy-astronomy/manifest.json';
async function fingerprint(relative) {
  const bytes = await fs.readFile(path.join(root, relative));
  return { path: relative.replaceAll('\\', '/'), bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') };
}
function variantFor(role, id) { return manifest.objects[role]?.[id]; }
async function dimensions() {
  return page.locator('.v5-closeup img').evaluate(image => ({ src: new URL(image.src).pathname, complete: image.complete, width: image.naturalWidth, height: image.naturalHeight }));
}
async function imageReady() { await page.waitForFunction(() => { const i = document.querySelector('.v5-closeup img'); return i?.complete && i.naturalWidth > 0; }); return dimensions(); }
async function roomEvidence() {
  if (!themeMode || state.status === 'won') return;
  const actual = await page.locator('.v5-scene').getAttribute('data-background');
  const expected = manifest.backgrounds[state.room.background_id || ['neutral_lab', 'neutral_archive', 'neutral_control'][Number(state.room.room_id.slice(1)) - 1]].src;
  const canvas = await page.locator('.v5-scene canvas').evaluate(c => ({ width: c.width, height: c.height, colors: (() => { const ctx=c.getContext('2d'); const data=ctx.getImageData(0,0,c.width,c.height).data;const set=new Set();for(let i=0;i<data.length;i+=4096)set.add(`${data[i]},${data[i+1]},${data[i+2]}`);return set.size; })() }));
  check(`actual ${state.room.room_id} handpainted background`, { src: actual, canvas }, { src: expected, nonblank_canvas: true }, actual === expected && canvas.colors > 8);
  await shot(`theme-${state.room.room_id}`);
}
async function completedArt(object) {
  const id = await page.locator(`.v5-hotspots button[data-object="${object.object_id}"]`).getAttribute('data-variant');
  const variant = variantFor(object.art_id, id);
  const actual = await imageReady();
  check(`completed art ${state.room.room_id} ${object.art_id}`, { variant_id: id, ...actual }, { state: 'completed', closeup: variant?.closeup }, variant?.state === 'completed' && actual.src === new URL(variant.closeup, base).pathname && actual.width > 0);
}
async function layout(label) {
  const controls=await page.locator('button:visible,input:visible,select:visible,textarea:visible').evaluateAll(es=>es.filter(e=>!e.disabled).map((e,index)=>{const r=e.getBoundingClientRect();return {index,width:r.width,height:r.height};}));
  const prose=await page.locator('.v5-room-note:visible,.v5-object-text:visible,.v5-clue p:visible,.v5-empty:visible,.v5-victory-lead:visible').evaluateAll(es=>es.map(e=>({selector:e.className||e.tagName,font_size:parseFloat(getComputedStyle(e).fontSize)})));
  const box=await page.evaluate(()=>({scroll_width:document.documentElement.scrollWidth,viewport_width:innerWidth}));
  check(`44px ${label}`, controls, { minimum:44 }, controls.length>0&&controls.every(c=>c.width>=44&&c.height>=44));
  check(`body 14px ${label}`, prose, { minimum:14 }, prose.length>0&&prose.every(p=>p.font_size>=14));
  check(`no horizontal overflow ${label}`, box, { maximum:box.viewport_width }, box.scroll_width<=box.viewport_width);
}
async function saves() { await close(); await page.getByRole('button',{name:'进度与存档',exact:true}).click(); await stable(); await page.getByRole('heading',{name:'保存与读取',exact:true}).waitFor(); }
async function save(name) { await saves();await page.getByLabel('存档名称',{exact:true}).fill(name);await post(()=>page.getByRole('button',{name:'保存新时刻',exact:true}).click(),'/saves');await page.locator('.v5-save').filter({hasText:name}).waitFor(); }
async function resumeTheme() { panelId=null; await page.reload(); await page.getByRole('heading',{name:'我的关卡',exact:true}).waitFor();const card=page.locator('.v5-level-card').filter({hasText:'3 间房'}).first();await card.getByRole('button',{name:/探索/}).click();await page.locator('.v5-hotspots button:enabled').first().waitFor();await stable(); }
async function sourceContext() {
 const sourcePaths=['tests/v5/run_handpainted_rebuild_browser.mjs','tests/v5/visual_ui_fixture_server.py','frontend/src/v5/GeneratedPlay.tsx','frontend/src/v5/GeneratedScene.tsx','frontend/src/v5/ObjectCloseup.tsx','frontend/src/v5/usePanelFocus.ts','frontend/src/v5/visual/scene.ts','frontend/src/v5/visual/registry.ts','frontend/src/v5/v5.css',packPath];
 const html=await fs.readFile(path.join(root,'frontend/dist-v5/index.html'),'utf8');
 const urls=[...html.matchAll(/(?:src|href)=["'](\/assets\/[^"']+\.(?:js|css))["']/g)].map(m=>m[1]);
 return {git_revision:execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8',windowsHide:true}).trim(),sources:await Promise.all(sourcePaths.map(fingerprint)),build:{index:await fingerprint('frontend/dist-v5/index.html'),entries:await Promise.all([...new Set(urls)].map(u=>fingerprint('frontend/dist-v5'+u))),new_execution_by_QA:false}};
}
try {
 manifest=JSON.parse(await fs.readFile(path.join(root,packPath),'utf8'));catalog=JSON.parse(await fs.readFile(path.join(root,'frontend/src/assets/generated-catalog.json'),'utf8'));provenance=await sourceContext();
 await new Promise((resolve,reject)=>{const probe=net.createServer();probe.once('error',reject);probe.listen(8002,'127.0.0.1',()=>probe.close(resolve));});
 const require=createRequire(path.join(root,'frontend/package.json'));const {chromium}=require('@playwright/test');
 temp=await fs.mkdtemp(path.join(os.tmpdir(),'campus-visual-handpainted-'));
 server=spawn('C:/Users/liyh/.conda/envs/1/python.exe',['-B','-X','utf8','-m','uvicorn','tests.v5.visual_ui_fixture_server:app','--host','127.0.0.1','--port','8002','--no-access-log'],{cwd:root,env:{...process.env,SQLITE_PATH:path.join(temp,'game-v5.sqlite'),GAMEPLAY_VERSION:'v5',AI_PROVIDER:'mock'},stdio:'ignore',windowsHide:true});server.on('error',()=>{});
 let ready=false;for(let i=0;i<100&&!ready;i++){ready=await new Promise(resolve=>{const r=http.get({hostname:'127.0.0.1',port:8002,path:'/health',headers:{host:'127.0.0.1:8001'}},res=>{res.resume();resolve(res.headers['x-qa-synthetic-visual']==='owned-temp-only');});r.on('error',()=>resolve(false));r.setTimeout(800,()=>r.destroy());});if(!ready)await pause(100);}if(!ready)throw Error('Owned Synthetic service unavailable');
 browser=await chromium.launch({headless:true,channel:'chrome'});const context=await browser.newContext({viewport:{width:1280,height:720}});
 await context.addInitScript(()=>{window.__qaCloseupFailures=[];window.addEventListener('error',e=>{if(e.target instanceof HTMLImageElement&&e.target.closest('.v5-closeup'))window.__qaCloseupFailures.push(new URL(e.target.src).pathname);},true);});
 await context.route('**/*',async route=>{const request=route.request(),url=new URL(request.url());if(['data:','blob:'].includes(url.protocol))return route.continue();if(url.origin!==base){external++;return route.abort();}
  if(blockedPaths.has(url.pathname)){blockedCounts.set(url.pathname,(blockedCounts.get(url.pathname)||0)+1);return route.fulfill({status:404,contentType:'text/plain',body:'Synthetic missing artwork'});}
  if(delayBackground&&url.pathname===new URL(manifest.backgrounds.neutral_lab.src,base).pathname){delayBackground=false;await pause(1000);}
  const response=await route.fetch({url:request.url().replace(base,'http://127.0.0.1:8002'),headers:{...request.headers(),host:'127.0.0.1:8001'}});
  if(response.ok()&&(/\.(?:png|jpg|jpeg|webp)$/.test(url.pathname))&&!resources.has(url.pathname)){const bytes=await response.body();const png=bytes.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10]));const size=png&&bytes.length>=24?{width:bytes.readUInt32BE(16),height:bytes.readUInt32BE(20)}:null;resources.set(url.pathname,{src:url.pathname,bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex'),png_size:size});}
  return route.fulfill({response});
 });
 page=await context.newPage();page.setDefaultTimeout(12000);page.on('response',async r=>{if(r.url().includes('/api/v2/sessions'))try{const b=await r.json();if(b.data?.visible_state)state=b.data.visible_state;}catch{}});
 await page.goto(base);await page.getByRole('button',{name:'第一次来？注册本地账户',exact:true}).click();await page.getByLabel('用户名（3–24位字母、数字或下划线）',{exact:true}).fill('handpainted_qa');await page.getByLabel('密码（12–128位）',{exact:true}).fill('Synthetic-Review-only!');await page.getByRole('button',{name:'注册并进入',exact:true}).click();await page.getByRole('heading',{name:'我的关卡',exact:true}).waitFor();

 if(focusOnly) {
  stage='focus-only-diagnostic';await create(1,'easy','Synthetic确认框焦点最小夹具');await save('focus-diagnostic');
  await page.getByRole('button',{name:'删除',exact:true}).click();await page.locator('dialog[open]').waitFor();
  const snapshot=()=>page.evaluate(()=>{const dialog=document.querySelector('dialog[open]'),active=document.activeElement;return {active_tag:active?.tagName||null,active_role:active?.getAttribute('role')||null,active_control_label:active?.matches('button,a,summary')?active.textContent?.trim().slice(0,70):null,document_has_focus:document.hasFocus(),active_is_body:active===document.body,in_dialog:!!dialog?.contains(active),in_v5_panel:!!active?.closest('.v5-overlay'),active_is_background_control:!!active?.matches('button,input,select,textarea,a,summary')&&!dialog?.contains(active),dialog_open:!!dialog?.open,dialog_native_modal:!!dialog?.matches(':modal'),confirm_controls:[...dialog.querySelectorAll('button,input,select,textarea')].map(e=>({tag:e.tagName,role:e.getAttribute('role'),label:e.tagName==='BUTTON'?e.textContent.trim():null}))};});
  const observed=[{key:'before',...await snapshot()}];
  for(const key of ['Shift+Tab','Tab','Tab','Tab','Tab','Tab','Tab','Shift+Tab','Shift+Tab']) {await page.keyboard.press(key);observed.push({key,...await snapshot()});}
  check('native confirm keyboard diagnostic avoids app background controls',observed,{no_background_control_focus:true},observed.every(o=>!o.active_is_background_control));await shot('focus-native-confirm');
  await page.keyboard.press('Escape');await page.waitForFunction(()=>!document.querySelector('dialog[open]'));await pause(80);
  const restored=await page.evaluate(()=>({inside_panel:!!document.activeElement?.closest('.v5-overlay'),active_tag:document.activeElement?.tagName,active_label:document.activeElement?.matches('button')?document.activeElement.textContent.trim():null,document_has_focus:document.hasFocus(),panel_visible:!!document.querySelector('.v5-overlay')}));
  check('native confirm cancel restores current V5 panel focus',restored,{inside_panel:true,panel_visible:true},restored.inside_panel&&restored.panel_visible);await shot('focus-after-native-cancel');
 } else {
 stage='generic-key-and-focus';await create(1,'easy','冬夜图书馆，寻找借阅登记');await open('obj_key');const key=await imageReady(),brass=manifest.objects.key['key-brass'];check('UI-R01 generic key shares resolved brass identity',{...key,scene_source:brass.src,scene_source_requested:resources.has(new URL(brass.src,base).pathname)},{closeup:brass.closeup,not_fuse:true},key.src===new URL(brass.closeup,base).pathname&&!key.src.includes('fuse')&&resources.has(new URL(brass.src,base).pathname));await shot('generic-key');await close();
 await save('focus-only');await page.getByRole('button',{name:'删除',exact:true}).click();await page.locator('dialog[open]').waitFor();await page.keyboard.press('Shift+Tab');let f=await page.evaluate(()=>Boolean(document.activeElement?.closest('dialog[open]')));check('confirmation ShiftTab remains modal',f,true,f);await page.keyboard.press('Escape');await page.waitForFunction(()=>!document.querySelector('dialog[open]'));await page.getByRole('button',{name:'删除',exact:true}).click();await post(()=>page.getByRole('button',{name:'确认删除',exact:true}).click(),'/delete');
 for(const direction of ['Tab','Shift+Tab']){await page.keyboard.press(direction);f=await page.evaluate(()=>Boolean(document.activeElement?.closest('.v5-overlay')));check(`UI-R03 after deleting row ${direction} stays modal`,f,true,f);}await shot('focus-after-delete');await page.keyboard.press('Escape');check('Escape closes save panel',await page.locator('.v5-overlay').count(),0,await page.locator('.v5-overlay').count()===0);panelId=null;
 stage='generic-settlement';await replay(witness(1,'easy'));await page.locator('.v5-victory').waitFor();const ending=await page.locator('.v5-victory-lead').innerText();check('UI-R02 neutral generic settlement',ending,'No astronomy or unsupported archiving claim',!ending.includes('观测记录')&&!ending.includes('归档')&&ending.includes('完成'));await shot('generic-ending');await page.getByRole('button',{name:'我的关卡',exact:true}).click();await page.getByRole('heading',{name:'我的关卡',exact:true}).waitFor();
 stage='themed-loading';themeMode=true;delayBackground=true;
 const creation=create(3,'hard','雨夜里的天文社旧活动室，寻找封存的观测记录');await page.getByText('正在铺开场景…',{exact:true}).waitFor();check('loading status actually visible',await page.getByText('正在铺开场景…',{exact:true}).isVisible(),true,true);await creation;await roomEvidence();
 stage='theme-save-restore';const stableTheme={theme:await page.locator('.v5-scene').getAttribute('data-theme'),background:await page.locator('.v5-scene').getAttribute('data-background'),variant:await page.locator('[data-object="obj_source"]').getAttribute('data-variant')};await save('theme-early');await close();await open('obj_source');check('actual discovery advances before restore',state.clues.length,'greater than zero',state.clues.length>0);await saves();await page.getByRole('button',{name:'读取',exact:true}).click();await post(()=>page.getByRole('button',{name:'确认读取',exact:true}).click(),'/restore');panelId=null;await page.locator('.v5-hotspots button:enabled').first().waitFor();const restoredTheme={theme:await page.locator('.v5-scene').getAttribute('data-theme'),background:await page.locator('.v5-scene').getAttribute('data-background'),variant:await page.locator('[data-object="obj_source"]').getAttribute('data-variant')};check('theme stable after actual selected restore',{...restoredTheme,clues:state.clues.length},{...stableTheme,clues:0},JSON.stringify(stableTheme)===JSON.stringify(restoredTheme)&&state.clues.length===0);
 stage='layout-and-closeup';for(const [w,h] of [[1280,720],[1920,1080]]){await page.setViewportSize({width:w,height:h});await layout(`scene ${w}`);await open('obj_source');const image=await imageReady();check(`actual usable closeup ${w}`,image,{width_positive:true},image.width>0&&image.height>0);await layout(`closeup ${w}`);await shot(`closeup-desktop-${w}`);await close();}await page.setViewportSize({width:1280,height:720});
 stage='dynamic-primary-404';await open('obj_source');const primary=await dimensions();const variantId=await page.locator('[data-object="obj_source"]').getAttribute('data-variant');const selected=variantFor('note',variantId);const candidates=[...new Set([primary.src,selected?.src,selected?.closeup,catalog.assets.find(a=>a.id==='note')?.url].filter(Boolean).map(x=>new URL(x,base).pathname))];await close();blockedPaths.add(primary.src);blockedCounts.clear();await resumeTheme();await open('obj_source');const fallback=await imageReady();check('UI-R04 dynamic actual primary404 usable fallback',{original_src:primary.src,...fallback,intercepts:Object.fromEntries(blockedCounts)},{original_intercepted:true,alternate_usable:true},(blockedCounts.get(primary.src)||0)>0&&fallback.src!==primary.src&&fallback.width>0);await shot('primary404-fallback');
 stage='all-closeup-images-404';await close();blockedPaths.clear();candidates.forEach(x=>blockedPaths.add(x));blockedCounts.clear();await resumeTheme();await open('obj_source');await page.locator('.v5-image-fallback').waitFor();const text=await page.locator('.v5-image-fallback').innerText();const before=Object.fromEntries(blockedCounts);await pause(500);const after=Object.fromEntries(blockedCounts),failures=await page.evaluate(()=>window.__qaCloseupFailures);check('all candidates404 remain readable without retry loop',{candidate_count:candidates.length,intercepts:after,html_failed_sources:failures,text_fallback_visible:!!text,description_visible:await page.locator('.v5-object-text').isVisible()},{text_alternative:true,each_HTML_source_once:true,no_new_requests_after_settle:true},text.includes('仍可继续操作')&&await page.locator('.v5-object-text').isVisible()&&failures.length>0&&failures.length===new Set(failures).size&&failures.length<=3&&JSON.stringify(before)===JSON.stringify(after));await shot('all-images-text-fallback');blockedPaths.clear();await resumeTheme();
 stage='three-room-real-UI-route';await replay(witness(3,'hard'));check('three-room hard actual UI reaches EXIT',{status:state.status,room:state.room.room_id,actions:actionCounts},{status:'won'},state.status==='won');await shot('theme-EXIT');const declared=[...Object.values(manifest.backgrounds).map(v=>({src:v.src,width:v.width,height:v.height})),...Object.values(manifest.objects).flatMap(role=>Object.values(role).flatMap(v=>[{src:v.src,width:v.width,height:v.height},{src:v.closeup,width:v.closeup_width,height:v.closeup_height}]))];const usedDimensions=declared.filter(v=>resources.has(new URL(v.src,base).pathname)).map(v=>({src:v.src,declared:{width:v.width,height:v.height},actual:resources.get(new URL(v.src,base).pathname).png_size}));check('used handpainted PNG dimensions match manifest',usedDimensions,'each loaded PNG matches all declarations',usedDimensions.length>0&&usedDimensions.every(v=>v.actual?.width===v.declared.width&&v.actual?.height===v.declared.height));check('no external requests',external,0,external===0);
}
} catch(error) {errors.push({type:error.constructor.name,stage});try{if(page)await shot('execution-stop');}catch{}}
finally {
 if(browser)await browser.close();if(server)stopped=await new Promise(resolve=>{if(server.exitCode!==null||server.signalCode!==null)return resolve(true);server.once('close',()=>resolve(true));server.kill();setTimeout(()=>resolve(false),4000);});
 const exitCode=errors.length||!stopped||checks.some(c=>!c.pass)?1:0;
 const result={kind:'Independent handpainted rebuild focused browser',run_id:runId,started_at_utc:started,ended_at_utc:new Date().toISOString(),command:'node tests/v5/run_handpainted_rebuild_browser.mjs'+(focusOnly?' --focus-only':''),scope:focusOnly?'minimal-confirm-focus-diagnostic':'full-focused-review',temporary_database:temp,inputs:[{rooms:1,difficulty:'easy',theme:'冬夜图书馆，寻找借阅登记'},{rooms:3,difficulty:'hard',theme:'雨夜里的天文社旧活动室，寻找封存的观测记录'}],provenance,used_image_resources:[...resources.values()],checks,errors,screenshots,exit_code:exitCode,owned_server_stopped:stopped,player8001_contacted:false,paid_calls:0,new_builds:0,limits:['Synthetic fixture and witness only; no real model or human acceptance','Image byte provenance and screenshots do not prove universal semantic consistency','Old failed results remain unchanged']};
 await fs.writeFile(path.join(out,'result.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({output:relative,exit_code:exitCode,checks:checks.length,failures:checks.filter(c=>!c.pass).map(c=>c.name),errors,owned_server_stopped:stopped}));process.exitCode=exitCode;
}
