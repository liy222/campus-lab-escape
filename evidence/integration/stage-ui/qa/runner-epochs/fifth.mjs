// Focused stage UI regression. Public API fixtures are setup, never UI route coverage.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import net from 'node:net';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {spawn,spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const {chromium,expect}=createRequire(path.join(root,'frontend/package.json'))('@playwright/test');
const candidatePath=process.argv[2],only=(process.argv.find(x=>x.startsWith('--only='))||'--only=all').slice(7);
assert(candidatePath,'Frozen Main candidate required');
assert(['all','lock','circuit','login','sequence','victory','panels','remaining','tail'].includes(only));
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8').replace(/^\uFEFF/,''));
const protocol=read('evidence/integration/stage-ui/qa/preparation.json');
assert(protocol.protocol_ready,'Final owner stage selector must be bound before formal execution');
const candidate=read(candidatePath),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex');
const hashes=()=>Object.fromEntries(Object.keys(candidate.source_sha256).map(p=>[p,sha(p)]));
const before=hashes();assert.deepEqual(before,candidate.source_sha256);
for(const [p,h] of Object.entries(protocol.immutable_sha256))assert.equal(sha(p),h,p);
const folder=path.join(root,'evidence/integration/stage-ui/qa',new Date().toISOString().replace(/[-:.]/g,'')+'-browser');
fs.mkdirSync(folder,{recursive:true});
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'campus-stage-ui-')),children=[],commands=[],checks=[],issues=[];
let browser,page,state,backendURL,frontendURL;const started=new Date().toISOString();
const viewportCases=[[1920,1080],[1280,900],[375,812],[812,375]];
async function port(){return new Promise((resolve,reject)=>{const s=net.createServer();s.once('error',reject);s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(e=>e?reject(e):resolve(p));});});}
function start(label,exe,args,env,cwd=root){commands.push({label,executable:exe,arguments:args,cwd,public_environment:env});const p=spawn(exe,args,{cwd,env:{...process.env,...env},windowsHide:true,stdio:'ignore'});children.push(p);p.on('error',e=>issues.push({label,error:e.message}));return p;}
async function ready(url){await expect.poll(async()=>{try{return(await fetch(url)).status;}catch{return 0;}},{timeout:30000}).toBe(200);}
async function response(suffix,operation,status=200){const wait=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith(suffix)&&r.request().method()===(suffix==='/state'?'GET':'POST')).catch(error=>({error}));await operation();const r=await wait;if(r.error)throw r.error;const b=await r.json();if(r.status()!==status){const p=r.request().postDataJSON();checks.push({check:'actual-unexpected-UI-response',status:r.status(),error_code:b.error?.code,tool:p?.tool,argument_shapes:Object.fromEntries(Object.entries(p?.arguments||{}).map(([k,v])=>[k,{type:typeof v,length:typeof v==='string'?v.length:undefined}]))});}assert.equal(r.status(),status);assert(b.ok,b.error?.code);state=b.data.visible_state;return b;}
async function api(tool,args={},suffix='/actions'){
  const r=await page.evaluate(async({tool,args,suffix,revision,generation})=>{
    const session=JSON.parse(sessionStorage.getItem('campus-lab-session-upgrade-v3.4'));
    const v={request_id:crypto.randomUUID(),revision,generation};
    const body=suffix==='/actions'?{...v,tool,arguments:args}:{...v,...args};
    const r=await fetch(`/api/sessions/${session.session_id}${suffix}`,{method:'POST',headers:{'Content-Type':'application/json','X-Session-Token':session.token,'X-AI-Provider':'mock'},body:JSON.stringify(body)});
    return{status:r.status,body:await r.json()};
  },{tool,args,suffix,revision:state.revision,generation:state.generation});
  assert(r.body.ok,'Public fixture '+tool+': '+r.body.error?.code);state=r.body.data.visible_state;
  checks.push({check:'public-API-fixture-only',tool,room:state.room.room_id,revision:state.revision});return r.body;
}
async function object(id,tool='inspect',extra={}){if(tool!=='inspect')await api('inspect',{object_id:id});const a=state.objects.find(o=>o.object_id===id)?.actions.find(a=>a.tool===tool);assert(a,'Actual affordance '+id+':'+tool);return api(tool,{...a.arguments,...extra});}
async function close(){const backdrop=page.getByRole('button',{name:'关闭面板',exact:true});if(await backdrop.isVisible())await backdrop.click({position:{x:5,y:5}});await expect(page.locator('.drawer-backdrop')).toHaveCount(0);}
async function menu(){await close();if(await page.locator('.victory-records').isVisible())await page.locator('.victory-records').click();else await page.getByRole('button',{name:'游戏菜单',exact:true}).click();await expect(page.locator('.save-panel')).toBeVisible();}
async function sync(){await menu();await response('/state',()=>page.locator('.save-panel').getByRole('button',{name:'同步进度',exact:true}).click());await close();if(state.status==='won')await expect(page.locator('.victory-screen')).toBeVisible();else await canvasReady();}
async function canvasReady(){const host=page.locator('.game-canvas-host');await expect(host).toHaveAttribute('data-room',state.room.room_id);await expect(host).toHaveAttribute('data-assets-ready','true');await expect(host).toHaveAttribute('data-animation','idle');await expect.poll(async()=>{const h=await host.boundingBox(),c=await host.locator('canvas').boundingBox();return !!h&&!!c&&Math.abs(h.width-c.width)<1;}).toBe(true);}
async function input(selector,kind='mouse'){
  await canvasReady();const button=page.locator('.scene-keyboard-hotspot'+selector);await expect(button).toHaveCount(1);await expect(button).toBeEnabled();
  if(kind==='keyboard'){await button.focus();await page.keyboard.press('Enter');return;}
  const b=(await button.getAttribute('data-bounds')).split(',').map(Number),c=await page.locator('.game-canvas-host canvas').boundingBox();
  const x=c.x+(b[0]+b[2]/2)*c.width/1600,y=c.y+(b[1]+b[3]/2)*c.height/900;
  if(kind==='touch')await page.touchscreen.tap(x,y);else await page.mouse.click(x,y);
}
async function select(id,kind='mouse'){const back=page.locator('.closeup-back');if(await back.isVisible())await back.click();await response('/actions',()=>input(`[data-object-id="${id}"][data-scene-action="object"]`,kind));await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view',id);}
async function geometry(label){
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  const measured=await page.evaluate(stageSelector=>{
    const stage=document.querySelector(stageSelector);if(!stage)return{missing_stage:true};
    const rect=n=>{const r=n.getBoundingClientRect();return{x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height};};
    const visible=n=>n.getClientRects().length&&getComputedStyle(n).visibility!=='hidden'&&getComputedStyle(n).display!=='none';
    const bound=rect(stage),within=(r,b=bound)=>r.x>=b.x-1&&r.y>=b.y-1&&r.right<=b.right+1&&r.bottom<=b.bottom+1;
    const canvas=document.querySelector('.game-canvas-host canvas'),frame=canvas?rect(canvas):null,desktop=innerWidth>760&&innerHeight>520;
    const clippedRect=n=>{let r=rect(n);for(let p=n.parentElement;p&&p!==stage;p=p.parentElement){const s=getComputedStyle(p);if(/auto|scroll|hidden|clip/.test(s.overflow+s.overflowX+s.overflowY)){const b=rect(p);r={...r,x:Math.max(r.x,b.x),y:Math.max(r.y,b.y),right:Math.min(r.right,b.right),bottom:Math.min(r.bottom,b.bottom)};}}return r;};
    const regions=[...document.querySelectorAll('.game-hud,.inventory-bar,.closeup-controls,.crt-login,.sequence-controls,.feedback,.notebook-modal,.visual-support [role="dialog"],dialog[open],.victory-screen')].filter(visible);
    const modal=document.querySelector('dialog[open]')||[...document.querySelectorAll('.notebook-modal,.visual-support [role="dialog"]')].find(visible);
    const controls=modal?[...modal.querySelectorAll('button,input:not([type=checkbox]):not([type=radio]),textarea,select')].filter(visible):[...document.querySelectorAll('.game-hud button,.inventory-bar button,.closeup-controls button,.closeup-controls input,.crt-login input,.crt-login button,.sequence-controls button,.scene-keyboard-hotspot')].filter(visible);
    const nativeOutsideCanvas=[];
    const unreachable=controls.filter(n=>{if(n.disabled||n.classList.contains('scene-keyboard-hotspot'))return false;n.scrollIntoView({block:'nearest',inline:'nearest'});const r=rect(n),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);if(desktop&&frame&&!modal&&!within(r,frame))nativeOutsideCanvas.push(n.className);return !(within(r)&&hit&&(n===hit||n.contains(hit)));});
    return{stage:bound,viewport:{width:innerWidth,height:innerHeight},document:{width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight},
      canvas:frame,desktop_canvas_rule:desktop,compact_stage_panel_exception:!desktop,
      outside_regions:regions.filter(n=>!within(clippedRect(n))).map(n=>n.className),
      primary_regions_outside_canvas:desktop&&frame?regions.filter(n=>n.matches('.game-hud,.inventory-bar,.closeup-controls,.crt-login,.sequence-controls,.feedback')&&!within(clippedRect(n),frame)).map(n=>n.className):[],
      native_controls_outside_canvas:nativeOutsideCanvas,
      undersized:controls.filter(n=>{const r=rect(n);return r.width<43.5||r.height<43.5;}).map(n=>({class:n.className,size:rect(n)})),
      unreachable:unreachable.map(n=>n.className),
      old_visible:[...document.querySelectorAll('.game-grid,.graybox-props,.object-grid,.topbar,.page-heading,.history,footer')].filter(visible).map(n=>n.className||n.tagName)};
  },protocol.stage_selector);
  assert(!measured.missing_stage,'Single stage missing');assert.deepEqual(measured.old_visible,[],'Legacy UI exposed');assert.deepEqual(measured.outside_regions,[],'Region outside game stage');
  assert(Math.abs(measured.stage.x)<1&&Math.abs(measured.stage.y)<1&&Math.abs(measured.stage.width-measured.viewport.width)<1&&Math.abs(measured.stage.height-measured.viewport.height)<1,'Stage must match viewport');
  assert.deepEqual(measured.primary_regions_outside_canvas,[],'Desktop HUD/bag/controls outside real Canvas');assert.deepEqual(measured.native_controls_outside_canvas,[],'Desktop primary native controls outside real Canvas');
  assert(measured.document.width<=measured.viewport.width+1&&measured.document.height<=measured.viewport.height+1,'Document extends beyond fixed stage viewport');
  assert.deepEqual(measured.undersized,[],'Controls smaller than 44px');assert.deepEqual(measured.unreachable,[],'Control center obstructed');
  checks.push({check:'fixed-stage-geometry',label,...measured});await page.screenshot({path:path.join(folder,label+'.png'),fullPage:true});
}
async function matrix(label){for(const [width,height] of viewportCases){await page.setViewportSize({width,height});if(state.status!=='won')await canvasReady();await geometry(`${label}-${width}x${height}`);}await page.setViewportSize({width:1280,height:900});if(state.status!=='won')await canvasReady();}

// Solver copied from the sealed old QA, based only on public reciprocal ports.
const sides=['N','E','S','W'],deltas=[[-1,0],[0,1],[1,0],[0,-1]];
function ports(m,r=m.rotation){return(m.shape==='I'?[0,2]:[0,1]).map(s=>(s+r)%4);}
function connected(board,rotations){const ms=new Map(board.modules.map(m=>[m.module_id,m])),pos=new Map(board.modules.map(m=>[[m.row,m.column].join(','),m.module_id])),ps=new Map(board.modules.map(m=>[m.module_id,ports(m,rotations[m.module_id])]));if(!ps.get(board.source.module_id).includes(sides.indexOf(board.source.side))||!ps.get(board.sink.module_id).includes(sides.indexOf(board.sink.side)))return false;const todo=[board.source.module_id],seen=new Set();while(todo.length){const id=todo.pop();if(seen.has(id))continue;seen.add(id);if(id===board.sink.module_id)return true;const m=ms.get(id);for(const side of ps.get(id)){const [dr,dc]=deltas[side],other=pos.get([m.row+dr,m.column+dc].join(','));if(other&&ps.get(other).includes((side+2)%4))todo.push(other);}}return false;}
function solution(board){let result;function search(i,chosen){if(result)return;if(i===board.modules.length){if(connected(board,chosen))result=chosen;return;}const m=board.modules[i];for(let r=0;r<(m.shape==='I'?2:4);r++)search(i+1,{...chosen,[m.module_id]:r});}search(0,{});assert(result);return result;}
function sequence(){const fact=id=>state.clues.filter(c=>c.object_id===id).map(c=>c.text).join('\n'),symbols=fact('r1_symbols').match(/[▲●■★]/g),positions=fact('research_strip').match(/\d+/g).map(Number),map=Object.fromEntries(state.minigames.sequence.devices.map(d=>[d.symbol,d.device_id]));assert.deepEqual([...positions].sort(),[1,2,3,4]);return positions.map(p=>map[symbols[p-1]]);}
async function panels(){
  if(only!=='tail'){await page.getByRole('button',{name:'线索笔记',exact:true}).click();await expect(page.locator('.notebook-modal')).toBeVisible();await geometry('notebook');await close();}
  await menu();const snapshot={room:state.room.room_id,revision:state.revision};await page.locator('#save-slot-name').fill('舞台回归');const saved=await response('/saves',()=>page.locator('.save-slot-create-button').click(),201);const id=saved.data.slot.save_id;await geometry('menu-named-save');await close();
  await page.getByRole('button',{name:'AI 探索伙伴',exact:true}).click();await page.locator('input[value="deepseek"]').check();await page.locator('#ai-api-key').fill('qa-fake-noncredential');
  assert(!await page.evaluate(()=>JSON.stringify({...sessionStorage,...localStorage}).includes('qa-fake-noncredential')));
  await page.locator('input[value="mock"]').check();await expect(page.locator('#ai-api-key')).toHaveCount(0);await page.locator('#ai-question').fill('下一步可以关注哪里？');
  const hint=await response('/ai/turns',()=>page.locator('.hint-ask').click());assert.equal(hint.data.usage.provider,'mock');assert.equal(hint.data.usage.model_calls,0);await geometry('mock-assistant');await close();
  await page.reload({waitUntil:'networkidle'});await response('/state',()=>page.getByRole('button',{name:'继续当前游戏',exact:true}).click());await menu();
  await page.locator(`[data-save-id="${id}"] .save-slot-restore`).click();const dialog=page.locator('dialog[open]');await geometry('selected-restore-confirm');await response(`/saves/${id}/restore`,()=>dialog.getByRole('button',{name:'读取此存档',exact:true}).click());assert.equal(state.room.room_id,snapshot.room);assert(state.revision>snapshot.revision);await close();await canvasReady();
  await page.getByRole('button',{name:'AI 探索伙伴',exact:true}).click();await page.locator('input[value="deepseek"]').check();await expect(page.locator('#ai-api-key')).toHaveValue('');await close();
  checks.push({check:'named-save-reload-selected-restore-notebook-mock-key-memory',passed:true});
}
async function run(){
  const context=await browser.newContext({viewport:{width:1280,height:900},hasTouch:true,deviceScaleFactor:1});page=await context.newPage();page.on('pageerror',e=>issues.push({check:'uncaught',error:e.message}));
  page.on('request',r=>{if(r.url().includes('deepseek.com'))issues.push({check:'unexpected-paid-endpoint'});});
  await page.goto(frontendURL,{waitUntil:'networkidle'});await response('/api/sessions',()=>page.getByRole('button',{name:'开始新游戏 →',exact:true}).click(),201);
  for(const id of ['r1_clock','r1_record','r1_plaque','r1_microscope'])await object(id);await object('sample_slide','take');await api('use_item',{item_id:'sample_slide',target_id:'r1_microscope'});await object('r1_microscope');await sync();
  if(['all','lock'].includes(only)){await select('r1_cabinet');await matrix('R1-lock');await response('/actions',async()=>{await page.locator('#code-r1_cabinet').fill('4217');await page.locator('.mechanical-lock button').click();});assert.equal(state.device_states.cabinet,'CODE_ACCEPTED');}
  else await object('r1_cabinet','submit_code',{code:'4217'});
  await object('r1_cabinet','interact');await object('r1_symbols');await object('r1_fuse','take');await object('r1_door','interact');await api('move',{destination_id:'R2'});await object('r2_maintenance');await object('r2_powerbox','interact');await object('r2_powerbox','interact');await api('use_item',{item_id:'fuse',target_id:'r2_powerbox'});await sync();
  if(['all','circuit'].includes(only)){await select('r2_powerbox','touch');await matrix('R2-circuit');const m=state.minigames.circuit.modules[0];await response('/actions',()=>input(`[data-module-id="${m.module_id}"]`,'touch'));assert.equal(state.minigames.circuit.modules[0].rotation,(m.rotation+1)%4);}
  const rotations=solution(state.minigames.circuit);for(const m of [...state.minigames.circuit.modules])for(let t=0;t<(rotations[m.module_id]-m.rotation+4)%4;t++)await api('rotate_circuit',{target_id:'r2_powerbox',module_id:m.module_id});await api('submit_circuit',{target_id:'r2_powerbox'});await object('r2_powerbox','interact');await object('r2_monitor','interact');await object('r2_monitor','interact');await sync();
  if(['all','login','remaining'].includes(only)){await select('r2_monitor');if(only!=='remaining')await matrix('R2-login');await expect(page.locator('.game-canvas-host > .crt-login')).toBeVisible();await response('/actions',async()=>{await page.locator('#terminal-username').fill('LAB-42');await page.locator('#terminal-password').fill('2117');await expect(page.locator('#terminal-username')).toHaveValue('LAB-42');await expect(page.locator('#terminal-password')).toHaveValue('2117');await page.locator('.crt-login button').click();});assert.equal(state.device_states.computer,'UNLOCKED');checks.push({check:'actual-CRT-login-submit',passed:true});}
  else {await object('r2_monitor','submit_login',{username:'LAB-42',password:'2117'});await sync();}
  if(['all','panels','remaining','tail'].includes(only))await panels();
  await object('r2_monitor','interact');await object('research_strip','take');await object('access_card','take');await object('r2_door','interact');await api('move',{destination_id:'R3'});await object('r3_legend');await object('r3_panel');await api('use_item',{item_id:'research_strip',target_id:'r3_panel'});await object('exit_door');await api('use_item',{item_id:'access_card',target_id:'exit_door'});await object('exit_door','interact');await sync();
  const order=sequence();
  if(['all','sequence','remaining','tail'].includes(only)){await select('r3_panel');await matrix('R3-sequence');await page.setViewportSize({width:375,height:812});for(let i=0;i<order.length;i++)await input(`[data-device-id="${order[i]}"]`,i%2?'keyboard':'touch');await expect(page.locator('.sequence-draft li[data-device-id]')).toHaveCount(4);await response('/actions',()=>page.locator('.sequence-submit').click());assert.equal(state.minigames.sequence.status,'completed');}
  else await api('submit_sequence',{target_id:'r3_panel',device_ids:order});
  await object('exit_door','interact');await object('exit_door','interact');await api('move',{destination_id:'EXIT'});await sync();
  if(['all','victory','remaining','tail'].includes(only))await matrix('EXIT-victory');await context.close();
}
let code=0;
try{
  const bp=await port();let fp=await port();while(fp===bp)fp=await port();backendURL=`http://127.0.0.1:${bp}`;frontendURL=`http://127.0.0.1:${fp}`;
  start('owned-mock-backend','C:/Users/liyh/.conda/envs/1/python.exe',['-B','-X','utf8','-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',String(bp),'--no-access-log'],{AI_PROVIDER:'mock',PYTHONUTF8:'1',GAMEPLAY_VERSION:'v3.4',SQLITE_PATH:path.join(temp,'stage.sqlite')});
  start('built-preview',process.execPath,[path.join(root,'frontend/node_modules/vite/bin/vite.js'),'preview','--host','127.0.0.1','--port',String(fp),'--strictPort'],{CAMPUS_BACKEND_URL:backendURL,VITE_GAMEPLAY_VERSION:'v3.4'},path.join(root,'frontend'));
  await Promise.all([ready(backendURL+'/api/health'),ready(frontendURL)]);browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});await run();assert.deepEqual(issues,[]);
}catch(e){code=1;issues.push({check:'runner',error:e.message,stack:String(e.stack).split('\n').filter(x=>x.trim().startsWith('at '))});}
finally{
  if(browser)await browser.close();for(const p of children.reverse())if(p.pid&&p.exitCode===null){const r=spawnSync('taskkill',['/PID',String(p.pid),'/T','/F'],{windowsHide:true,encoding:'utf8'});checks.push({check:'stop-owned-process-tree',exit_code:r.status});}
  const after=hashes();if(JSON.stringify(before)!==JSON.stringify(after)){code=1;issues.push({check:'source-changed'});}
  for(const [p,h] of Object.entries(protocol.immutable_sha256))if(sha(p)!==h){code=1;issues.push({check:'immutable-changed',path:p});}
  fs.writeFileSync(path.join(folder,'run.json'),JSON.stringify({candidate:candidatePath,command:[process.execPath,...process.argv.slice(1)],started,ended:new Date().toISOString(),exit_code:code,necessary_scope:only,commands,source_sha256_before:before,source_sha256_after:after,checks,issues,paid_calls:0,limitations:['Public API fixtures prepare puzzle prerequisites; this is focused UI regression, not full route or API suite.','No user historical DB/real credentials/paid provider quality/human timing.']},null,2)+'\n');
  console.log(JSON.stringify({evidence:folder,exit_code:code,checks:checks.length,issues:issues.length}));process.exitCode=code;
}
