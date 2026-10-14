// Focused closeup isolation / early panel projection. Public API calls are explicit prerequisite fixtures.
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
const candidatePath=process.argv[2];
assert(candidatePath,'Frozen Main candidate required');

const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8').replace(/^\uFEFF/,''));
const plan=read('evidence/integration/panel-submit/plan.json');
const protocol={immutable_sha256:Object.fromEntries(Object.entries(plan.baseline_source_sha256).filter(([p])=>p!=='frontend/src/components/Room3.tsx'))};
const candidate=read(candidatePath),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex');
const hashes=()=>Object.fromEntries(Object.keys(candidate.source_sha256).map(p=>[p,sha(p)]));
const before=hashes();assert.deepEqual(before,candidate.source_sha256);
for(const [p,h] of Object.entries(protocol.immutable_sha256))assert.equal(sha(p),h,p);
const folder=path.join(root,'evidence/integration/panel-submit/qa',new Date().toISOString().replace(/[-:.]/g,'')+'-browser');
fs.mkdirSync(folder,{recursive:true});
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'campus-panel-submit-')),children=[],commands=[],checks=[],issues=[];
let browser,page,state,backendURL,frontendURL;const started=new Date().toISOString();
const viewportCases=[[1920,1080],[1280,900],[375,812],[812,375]];
async function port(){return new Promise((resolve,reject)=>{const s=net.createServer();s.once('error',reject);s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(e=>e?reject(e):resolve(p));});});}
function start(label,exe,args,env,cwd=root){commands.push({label,executable:exe,arguments:args,cwd,public_environment:env});const p=spawn(exe,args,{cwd,env:{...process.env,...env},windowsHide:true,stdio:'ignore'});children.push(p);p.on('error',e=>issues.push({label,error:e.message}));return p;}
async function ready(url){await expect.poll(async()=>{try{return(await fetch(url)).status;}catch{return 0;}},{timeout:30000}).toBe(200);}
async function response(suffix,operation,status=200){const wait=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith(suffix)&&r.request().method()===(suffix==='/state'?'GET':'POST')).catch(error=>({error}));await operation();const r=await wait;if(r.error)throw r.error;const b=await r.json();if(r.status()!==status){const p=r.request().postDataJSON();checks.push({check:'actual-unexpected-UI-response',status:r.status(),error_code:b.error?.code,tool:p?.tool,argument_shapes:Object.fromEntries(Object.entries(p?.arguments||{}).map(([k,v])=>[k,{type:typeof v,length:typeof v==='string'?v.length:undefined}]))});}assert.equal(r.status(),status);if(status>=400)assert(!b.ok);else assert(b.ok,b.error?.code);if(b.data?.visible_state)state=b.data.visible_state;else if(b.visible_state)state=b.visible_state;return b;}
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
async function canvasReady(){await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));await expect.poll(async()=>page.evaluate(()=>{const s=document.querySelector('main.game-stage')?.getBoundingClientRect(),c=document.querySelector('.game-canvas-host canvas')?.getBoundingClientRect();const width=innerWidth<=760&&innerHeight>520?innerWidth:Math.min(innerWidth,innerHeight*1600/900);return !!s&&!!c&&Math.abs(s.width-innerWidth)<1&&Math.abs(s.height-innerHeight)<1&&Math.abs(c.width-width)<2;})).toBe(true);const host=page.locator('.game-canvas-host');await expect(host).toHaveAttribute('data-room',state.room.room_id);await expect(host).toHaveAttribute('data-assets-ready','true');await expect(host).toHaveAttribute('data-animation','idle');await expect.poll(async()=>{const h=await host.boundingBox(),c=await host.locator('canvas').boundingBox();return !!h&&!!c&&Math.abs(h.width-c.width)<1;}).toBe(true);}
async function input(selector,kind='mouse'){
  await canvasReady();const button=page.locator('.scene-keyboard-hotspot'+selector);await expect(button).toHaveCount(1);await expect(button).toBeEnabled();
  if(kind==='keyboard'){await button.focus();await page.keyboard.press('Enter');return;}
  const b=(await button.getAttribute('data-bounds')).split(',').map(Number),c=await page.locator('.game-canvas-host canvas').boundingBox();
  const x=c.x+(b[0]+b[2]/2)*c.width/1600,y=c.y+(b[1]+b[3]/2)*c.height/900;
  if(kind==='touch')await page.touchscreen.tap(x,y);else await page.mouse.click(x,y);
}
async function select(id,kind='mouse'){const back=page.locator('.closeup-back');if(await back.isVisible())await back.click();await response('/actions',()=>input(`[data-object-id="${id}"][data-scene-action="object"]`,kind));await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view',id);}
// Solver copied from the sealed old QA, based only on public reciprocal ports.
const sides=['N','E','S','W'],deltas=[[-1,0],[0,1],[1,0],[0,-1]];
function ports(m,r=m.rotation){return(m.shape==='I'?[0,2]:[0,1]).map(s=>(s+r)%4);}
function connected(board,rotations){const ms=new Map(board.modules.map(m=>[m.module_id,m])),pos=new Map(board.modules.map(m=>[[m.row,m.column].join(','),m.module_id])),ps=new Map(board.modules.map(m=>[m.module_id,ports(m,rotations[m.module_id])]));if(!ps.get(board.source.module_id).includes(sides.indexOf(board.source.side))||!ps.get(board.sink.module_id).includes(sides.indexOf(board.sink.side)))return false;const todo=[board.source.module_id],seen=new Set();while(todo.length){const id=todo.pop();if(seen.has(id))continue;seen.add(id);if(id===board.sink.module_id)return true;const m=ms.get(id);for(const side of ps.get(id)){const [dr,dc]=deltas[side],other=pos.get([m.row+dr,m.column+dc].join(','));if(other&&ps.get(other).includes((side+2)%4))todo.push(other);}}return false;}
function solution(board){let result;function search(i,chosen){if(result)return;if(i===board.modules.length){if(connected(board,chosen))result=chosen;return;}const m=board.modules[i];for(let r=0;r<(m.shape==='I'?2:4);r++)search(i+1,{...chosen,[m.module_id]:r});}search(0,{});assert(result);return result;}
function sequence(){const fact=id=>state.clues.filter(c=>c.object_id===id).map(c=>c.text).join('\n'),symbols=fact('r1_symbols').match(/[▲●■★]/g),positions=fact('research_strip').match(/\d+/g).map(Number),map=Object.fromEntries(state.minigames.sequence.devices.map(d=>[d.symbol,d.device_id]));assert.deepEqual([...positions].sort(),[1,2,3,4]);return positions.map(p=>map[symbols[p-1]]);}
const hot=selector=>page.locator('.scene-keyboard-hotspot'+selector);
let actionRequests=[];
async function overview(){const back=page.locator('.closeup-back');if(await back.isVisible())await back.click();await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view','room');await canvasReady();return hot('').evaluateAll(nodes=>nodes.map(n=>({id:n.dataset.objectId,box:n.dataset.bounds.split(',').map(Number)})));}
// Focused independent R3 test. R1/R2 prerequisites are public API fixtures, not human gameplay.
const semantic=s=>Object.fromEntries(['status','room','inventory','clues','device_states','puzzle_states','progress','minigames','statistics','settlement'].map(k=>[k,s[k]]));
const draft=()=>page.locator('.sequence-draft li[data-device-id]').evaluateAll(ns=>ns.map(n=>n.dataset.deviceId));
const card=()=>page.locator('.inventory-item[data-item-id="access_card"] .item-select-button');
async function readState(){
  state=await page.evaluate(async()=>{const s=JSON.parse(sessionStorage.getItem('campus-lab-session-upgrade-v3.4'));const r=await fetch(`/api/sessions/${s.session_id}/state`,{headers:{'X-Session-Token':s.token}});if(!r.ok)throw Error('Owned state rejected');return(await r.json()).data.visible_state;});return state;
}
async function snapshot(label){await canvasReady();await page.screenshot({path:path.join(folder,label+'.png'),fullPage:true});checks.push({check:'actual-screenshot',label,room:state.room.room_id,exit:state.device_states.exit,panel:state.puzzle_states.panel});}
async function fixture(){
  for(const id of ['r1_clock','r1_record','r1_plaque','r1_microscope'])await object(id);
  await object('sample_slide','take');await api('use_item',{item_id:'sample_slide',target_id:'r1_microscope'});await object('r1_microscope');await object('r1_cabinet','submit_code',{code:'4217'});await object('r1_cabinet','interact');await object('r1_symbols');await object('r1_fuse','take');
  await object('r1_door','interact');await api('move',{destination_id:'R2'});await object('r2_maintenance');await object('r2_powerbox','interact');await object('r2_powerbox','interact');await api('use_item',{item_id:'fuse',target_id:'r2_powerbox'});
  const board=structuredClone(state.minigames.circuit),answer=solution(board);for(const m of board.modules)for(let i=0;i<(answer[m.module_id]-m.rotation+4)%4;i++)await api('rotate_circuit',{target_id:board.target_id,module_id:m.module_id});await api('submit_circuit',{target_id:board.target_id});
  await object('r2_powerbox','interact');await object('r2_monitor','interact');await object('r2_monitor','interact');await api('submit_login',{target_id:'r2_monitor',username:'LAB-42',password:'2117'});await object('r2_monitor','interact');await object('research_strip','take');await object('access_card','take');await object('r2_door','interact');await api('move',{destination_id:'R3'});await sync();
  assert.equal(state.puzzle_states.panel,'EMPTY');assert.equal(state.device_states.exit,'LOCKED');checks.push({check:'public-API-prerequisite-fixture-boundary',scope:'R1/R2 progression only. All R3 actions below are actual UI except explicit pre-card guard probe and authenticated state reads.'});
}
async function heldUse(item,id,kind='mouse'){
  await select(id,kind);await canvasReady();await page.locator(`.inventory-item[data-item-id="${item}"] .item-select-button`).click();
  const b=await response('/actions',()=>page.locator('.closeup-actions .use-button').click());assert.equal(b.data.receipt.tool,'use_item');assert.equal(b.data.receipt.arguments.item_id,item);assert.equal(b.data.receipt.arguments.target_id,id);await canvasReady();
}
async function localDraft(ids,kinds=['mouse','keyboard','touch','mouse']){
  const before=structuredClone(state),requests=actionRequests.length;for(let i=0;i<ids.length;i++)await input(`[data-device-id="${ids[i]}"]`,kinds[i%kinds.length]);
  await expect.poll(draft).toEqual(ids);await readState();assert.deepEqual(state,before);assert.equal(actionRequests.length,requests);checks.push({check:'actual-device-input-local-draft-no-server-use-item',kinds,device_ids:ids,selected_card:await card().getAttribute('aria-pressed')});
}
async function clear(){const n=actionRequests.length;await page.locator('.sequence-clear').click();await expect.poll(draft).toEqual([]);assert.equal(actionRequests.length,n);checks.push({check:'actual-clear-local-draft'});}
async function saveMoment(name){await menu();const snap=structuredClone(state);await page.locator('#save-slot-name').fill(name);const b=await response('/saves',()=>page.locator('.save-slot-create-button').click(),201);assert.deepEqual(state,snap);await close();await canvasReady();checks.push({check:'actual-manual-save',name});return{id:b.data.slot.save_id,state:snap};}
async function restoreMoment(moment){await menu();await page.locator(`[data-save-id="${moment.id}"] .save-slot-restore`).click();await response(`/saves/${moment.id}/restore`,()=>page.locator('dialog[open]').getByRole('button',{name:'读取此存档',exact:true}).click());assert.deepEqual(semantic(state),semantic(moment.state));assert.notEqual(state.generation,moment.state.generation);await close();await canvasReady();await select('r3_panel');await expect.poll(draft).toEqual([]);checks.push({check:'actual-selected-restore-server-state-local-draft-cleared'});}
async function reload(){const before=semantic(state);await page.reload({waitUntil:'networkidle'});await response('/state',()=>page.getByRole('button',{name:'继续当前游戏',exact:true}).click());assert.deepEqual(semantic(state),before);await canvasReady();await select('r3_panel');await expect.poll(draft).toEqual([]);checks.push({check:'actual-reload-server-ready-local-draft-cleared'});}
async function precardGuard(ids){
  const before=structuredClone(state),requests=actionRequests.length;
  const r=await page.evaluate(async({revision,generation,ids})=>{const s=JSON.parse(sessionStorage.getItem('campus-lab-session-upgrade-v3.4'));const r=await fetch(`/api/sessions/${s.session_id}/actions`,{method:'POST',headers:{'Content-Type':'application/json','X-Session-Token':s.token,'X-AI-Provider':'mock'},body:JSON.stringify({request_id:crypto.randomUUID(),revision,generation,tool:'submit_sequence',arguments:{target_id:'r3_panel',device_ids:ids}})});const b=await r.json();return{status:r.status,ok:b.ok,code:b.error?.code};},{revision:state.revision,generation:state.generation,ids});
  assert.equal(r.ok,false);assert.equal(r.code,'PRECONDITION_FAILED');assert(r.status>=400);await readState();assert.deepEqual(state,before);assert.equal(actionRequests.length,requests+1);checks.push({check:'explicit-public-API-precard-authority-guard',...r});
}
async function oneViewport(width,height,kind){
  await page.setViewportSize({width,height});await fixture();await select('r3_legend',kind);await heldUse('research_strip','r3_panel',kind);
  assert.equal(state.device_states.exit,'LOCKED');await expect(hot('[data-device-id]')).toHaveCount(4);await expect(page.locator('.sequence-start')).toHaveCount(0);await expect(page.locator('.sequence-instructions')).toContainText('门禁卡');
  const ids=sequence();await localDraft(ids,[kind,'keyboard',kind,'keyboard']);await expect(page.locator('.sequence-submit')).toBeDisabled();await precardGuard(ids);await clear();await snapshot(`precard-${width}`);
  await heldUse('access_card','exit_door',kind);assert.equal(state.device_states.exit,'CARD_ACCEPTED');await expect(card()).toHaveAttribute('aria-pressed','true');
  // No deselection: actual overview Canvas click must inspect the inserted panel with held card.
  await overview();const open=await response('/actions',()=>input('[data-object-id="r3_panel"][data-scene-action="object"]',kind));assert.equal(open.data.receipt.tool,'inspect');assert.equal(open.data.receipt.arguments.object_id,'r3_panel');await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view','r3_panel');await expect(card()).toHaveAttribute('aria-pressed','true');
  checks.push({check:'natural-held-card-overview-panel-opens-with-inspect',width,height,kind});await localDraft(ids,[kind,'keyboard',kind,'keyboard']);await expect(page.locator('.sequence-submit')).toBeDisabled();await expect(page.locator('.sequence-start')).toBeEnabled();await snapshot(`card-accepted-draft-${width}`);
  const b=await response('/actions',()=>page.locator('.sequence-start').click());assert.equal(b.data.receipt.tool,'interact');assert.equal(b.data.receipt.arguments.target_id,'exit_door');assert.equal(state.device_states.exit,'FINAL_CHECK');await expect(card()).toHaveAttribute('aria-pressed','true');await expect.poll(draft).toEqual(ids);await expect(page.locator('.sequence-start')).toHaveCount(0);await expect(page.locator('.sequence-submit')).toBeEnabled();await snapshot(`started-held-card-${width}`);checks.push({check:'explicit-panel-start-existing-server-door-action-keeps-draft-and-card',width});
  await clear();const wrong=[ids[1],ids[0],ids[2],ids[3]];await localDraft(wrong,[kind,'keyboard',kind,'keyboard']);const mistakes=state.statistics.mistake_count;const bad=await response('/actions',()=>page.locator('.sequence-submit').click(),409);assert.equal(bad.error.code,'WRONG_CODE');await readState();assert.equal(state.progress.check_done,false);assert.equal(state.device_states.exit,'FINAL_CHECK');assert.equal(state.statistics.mistake_count,mistakes+1);await expect.poll(draft).toEqual(wrong);await expect(card()).toHaveAttribute('aria-pressed','true');checks.push({check:'actual-wrong-order-rejected-still-editable',width,error:bad.error.code});await clear();
  await localDraft(ids,[kind,'keyboard',kind,'keyboard']);const moment=await saveMoment('提交前-'+width);await restoreMoment(moment);assert.equal(state.device_states.exit,'FINAL_CHECK');await localDraft(ids,[kind,'keyboard',kind,'keyboard']);await reload();assert.equal(state.device_states.exit,'FINAL_CHECK');
  // Restore/reload intentionally clears page draft and selected item; reselect card to recheck.
  await card().click();await expect(card()).toHaveAttribute('aria-pressed','true');await localDraft(ids,[kind,'keyboard',kind,'keyboard']);await expect(page.locator('.sequence-submit')).toBeEnabled();const submitted=await response('/actions',()=>page.locator('.sequence-submit').click());assert.equal(submitted.data.receipt.tool,'submit_sequence');assert.deepEqual(submitted.data.receipt.arguments.device_ids,ids);assert.equal(state.progress.check_done,true);await expect(page.locator('.sequence-controls')).toHaveAttribute('data-sequence-status','completed');await expect(page.locator('.sequence-submit')).toBeDisabled();await expect(hot('[data-device-id]:enabled')).toHaveCount(0);await snapshot(`passed-${width}`);checks.push({check:'actual-correct-order-held-card-submission-after-save-restore-reload',width});
  // Leave the card selected; native explicit door action preserves the existing authority chain.
  await overview();await response('/actions',()=>input('[data-object-id="exit_door"][data-scene-action="object"]',kind));await canvasReady();
  // Overview object with selected card uses existing use_item semantics, so inspect explicitly using the visible native control.
  if(await page.locator('.game-canvas-host').getAttribute('data-view')!=='exit_door'){
    await page.locator('.cancel-item').click();await select('exit_door',kind);
  }
  await response('/actions',()=>page.locator('.closeup-actions [data-scene-action="interact"]').click());assert.equal(state.device_states.exit,'UNLOCKED');await canvasReady();await snapshot(`unlocked-${width}`);
  await response('/actions',()=>page.locator('.closeup-actions [data-scene-action="interact"]').click());assert.equal(state.device_states.exit,'OPEN');await canvasReady();await snapshot(`open-${width}`);
  await response('/actions',()=>page.locator('.closeup-actions [data-scene-action="move"]').click());assert.equal(state.status,'won');await expect(page.locator('.victory-screen')).toBeVisible();await page.screenshot({path:path.join(folder,`victory-${width}.png`),fullPage:true});checks.push({check:'actual-UI-UNLOCKED-OPEN-EXIT',width});
}
async function run(){
  const context=await browser.newContext({viewport:{width:1280,height:900},hasTouch:true,deviceScaleFactor:1});page=await context.newPage();page.setDefaultTimeout(20000);
  page.on('pageerror',e=>issues.push({check:'uncaught',error:e.message}));page.on('request',r=>{const u=new URL(r.url());if(u.pathname.endsWith('/actions')&&r.method()==='POST'){const b=r.postDataJSON();actionRequests.push({tool:b?.tool,target_id:b?.arguments?.target_id,object_id:b?.arguments?.object_id});}if(!['127.0.0.1','localhost'].includes(u.hostname)&&u.protocol.startsWith('http'))issues.push({check:'unexpected-external-request',hostname:u.hostname});});
  for(const [width,height,kind]of [[1280,900,'mouse'],[375,812,'touch']]){await page.goto(frontendURL,{waitUntil:'networkidle'});await page.evaluate(()=>sessionStorage.clear());await page.reload({waitUntil:'networkidle'});await response('/api/sessions',()=>page.getByRole('button',{name:'开始新游戏 →',exact:true}).click(),201);await oneViewport(width,height,kind);}
  await context.close();
}
let code=0;
try{
  const bp=await port();let fp=await port();while(fp===bp)fp=await port();backendURL=`http://127.0.0.1:${bp}`;frontendURL=`http://127.0.0.1:${fp}`;
  start('owned-mock-backend','C:/Users/liyh/.conda/envs/1/python.exe',['-B','-X','utf8','-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',String(bp),'--no-access-log'],{AI_PROVIDER:'mock',PYTHONUTF8:'1',GAMEPLAY_VERSION:'v3.4',SQLITE_PATH:path.join(temp,'panel-submit.sqlite')});
  start('built-preview',process.execPath,[path.join(root,'frontend/node_modules/vite/bin/vite.js'),'preview','--host','127.0.0.1','--port',String(fp),'--strictPort'],{CAMPUS_BACKEND_URL:backendURL,VITE_GAMEPLAY_VERSION:'v3.4'},path.join(root,'frontend'));
  await Promise.all([ready(backendURL+'/api/health'),ready(frontendURL)]);browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});await run();assert.deepEqual(issues,[]);
}catch(e){code=1;issues.push({check:'runner',error:e.message,stack:String(e.stack).split('\n').filter(x=>x.trim().startsWith('at '))});if(page&&!page.isClosed())try{await page.screenshot({path:path.join(folder,'failure.png'),fullPage:true});}catch{}}
finally{
  if(browser)await browser.close();for(const p of children.reverse())if(p.pid&&p.exitCode===null){const r=spawnSync('taskkill',['/PID',String(p.pid),'/T','/F'],{windowsHide:true,encoding:'utf8'});checks.push({check:'stop-owned-process-tree',exit_code:r.status});}
  const after=hashes();if(JSON.stringify(before)!==JSON.stringify(after)){code=1;issues.push({check:'source-changed'});}for(const[p,h]of Object.entries(protocol.immutable_sha256))if(sha(p)!==h){code=1;issues.push({check:'immutable-changed',path:p});}
  fs.writeFileSync(path.join(folder,'run.json'),JSON.stringify({candidate:candidatePath,candidate_sha256:sha(candidatePath),command:[process.execPath,...process.argv.slice(1)],started,ended:new Date().toISOString(),exit_code:code,commands,source_sha256_before:before,source_sha256_after:after,checks,issues,paid_calls:0,limitations:['Isolated public API prerequisites for R1/R2 are not counted as human or UI main-route execution.','R3 actual UI covers desktop1280/mobile375 mouse,touch,keyboard; no 127-method backend suite or unrelated visual scope rerun.','Page draft intentionally is not archived and clears on selected restore/reload; server stage is archived.','No paid-provider, human timing, historical user DB, OS restart or root launcher claim.','Owned temporary database is not committed; no session tokens/API keys are saved.']},null,2)+'\n');console.log(JSON.stringify({evidence:folder,exit_code:code,checks:checks.length,issues:issues.length}));process.exitCode=code;
}
