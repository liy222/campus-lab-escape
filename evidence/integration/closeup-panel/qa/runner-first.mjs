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
const candidatePath=process.argv[2],only=(process.argv.find(x=>x.startsWith('--only='))||'--only=all').slice(7);
assert(candidatePath,'Frozen Main candidate required');
assert(['all','r1','r2','r3'].includes(only));
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8').replace(/^\uFEFF/,''));
const protocol=read('evidence/integration/closeup-panel/qa/preparation.json');
assert(protocol.protocol_ready,'Final owner stage selector must be bound before formal execution');
const candidate=read(candidatePath),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex');
const hashes=()=>Object.fromEntries(Object.keys(candidate.source_sha256).map(p=>[p,sha(p)]));
const before=hashes();assert.deepEqual(before,candidate.source_sha256);
for(const [p,h] of Object.entries(protocol.immutable_sha256))assert.equal(sha(p),h,p);
const folder=path.join(root,'evidence/integration/closeup-panel/qa',new Date().toISOString().replace(/[-:.]/g,'')+'-browser');
fs.mkdirSync(folder,{recursive:true});
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'campus-closeup-panel-')),children=[],commands=[],checks=[],issues=[];
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
// Solver copied from the sealed old QA, based only on public reciprocal ports.
const sides=['N','E','S','W'],deltas=[[-1,0],[0,1],[1,0],[0,-1]];
function ports(m,r=m.rotation){return(m.shape==='I'?[0,2]:[0,1]).map(s=>(s+r)%4);}
function connected(board,rotations){const ms=new Map(board.modules.map(m=>[m.module_id,m])),pos=new Map(board.modules.map(m=>[[m.row,m.column].join(','),m.module_id])),ps=new Map(board.modules.map(m=>[m.module_id,ports(m,rotations[m.module_id])]));if(!ps.get(board.source.module_id).includes(sides.indexOf(board.source.side))||!ps.get(board.sink.module_id).includes(sides.indexOf(board.sink.side)))return false;const todo=[board.source.module_id],seen=new Set();while(todo.length){const id=todo.pop();if(seen.has(id))continue;seen.add(id);if(id===board.sink.module_id)return true;const m=ms.get(id);for(const side of ps.get(id)){const [dr,dc]=deltas[side],other=pos.get([m.row+dr,m.column+dc].join(','));if(other&&ps.get(other).includes((side+2)%4))todo.push(other);}}return false;}
function solution(board){let result;function search(i,chosen){if(result)return;if(i===board.modules.length){if(connected(board,chosen))result=chosen;return;}const m=board.modules[i];for(let r=0;r<(m.shape==='I'?2:4);r++)search(i+1,{...chosen,[m.module_id]:r});}search(0,{});assert(result);return result;}
function sequence(){const fact=id=>state.clues.filter(c=>c.object_id===id).map(c=>c.text).join('\n'),symbols=fact('r1_symbols').match(/[▲●■★]/g),positions=fact('research_strip').match(/\d+/g).map(Number),map=Object.fromEntries(state.minigames.sequence.devices.map(d=>[d.symbol,d.device_id]));assert.deepEqual([...positions].sort(),[1,2,3,4]);return positions.map(p=>map[symbols[p-1]]);}
const hot=selector=>page.locator('.scene-keyboard-hotspot'+selector);
let actionRequests=[];
async function overview(){const back=page.locator('.closeup-back');if(await back.isVisible())await back.click();await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view','room');await canvasReady();return hot('[data-scene-action="object"]').evaluateAll(nodes=>nodes.map(n=>({id:n.dataset.objectId,box:n.dataset.bounds.split(',').map(Number)})));}
async function isolation(id,allowed,label){
  const old=await overview();await select(id);await canvasReady();
  const host=page.locator('.game-canvas-host'),current=await hot('').evaluateAll(nodes=>nodes.map(n=>({id:n.dataset.objectId,box:n.dataset.bounds.split(',').map(Number)})));
  assert(current.length>0);assert(current.every(h=>allowed.includes(h.id)),label+' foreign keyboard hotspot');
  for(let i=0;i<16;i++){await page.keyboard.press('Tab');const focused=await page.evaluate(()=>document.activeElement?.classList.contains('scene-keyboard-hotspot')?document.activeElement.dataset.objectId:null);if(focused)assert(allowed.includes(focused));}
  const canvas=await host.locator('canvas').boundingBox(),minimum=44*1600/canvas.width;
  const inside=(x,y,b)=>{const w=Math.max(minimum,b[2]),h=Math.max(minimum,b[3]),l=b[0]-(w-b[2])/2,t=b[1]-(h-b[3])/2;return x>=l&&x<=l+w&&y>=t&&y<=t+h;};
  const probes=old.filter(o=>!allowed.includes(o.id)).map(o=>({...o,x:o.box[0]+o.box[2]/2,y:o.box[1]+o.box[3]/2})).filter(o=>!current.some(h=>inside(o.x,o.y,h.box)));
  const used=[];const original=structuredClone(state),begin=actionRequests.length;
  for(const o of probes){const x=canvas.x+o.x*canvas.width/1600,y=canvas.y+o.y*canvas.height/900;
    const target=await page.evaluate(({x,y})=>document.elementFromPoint(x,y)?.tagName,{x,y});if(target!=='CANVAS'){checks.push({check:'probe-excluded-native-overlay',label,object:o.id});continue;}
    await page.mouse.click(x,y);await page.touchscreen.tap(x,y);used.push(o.id);
  }
  assert(used.length>0,label+' requires at least one genuine unoccluded stale-background probe');
  await page.waitForTimeout(400);assert.equal(actionRequests.length,begin,label+' stale point caused action');
  await expect(host).toHaveAttribute('data-view',id);
  const visible=await page.evaluate(async()=>{const s=JSON.parse(sessionStorage.getItem('campus-lab-session-upgrade-v3.4'));const r=await fetch(`/api/sessions/${s.session_id}/state`,{headers:{'X-Session-Token':s.token}});if(!r.ok)throw new Error('state read rejected');return(await r.json()).data.visible_state;});assert.deepEqual(visible,original,label+' click-through state changed');
  await page.screenshot({path:path.join(folder,label+'.png'),fullPage:true});checks.push({check:'real-mouse-touch-stale-overview-no-action-and-keyboard-scope',label,probed:used,allowed,revision:state.revision});
}
async function child(id,kind){await response('/actions',()=>input(`[data-object-id="${id}"][data-scene-action="object"]`,kind));await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view',id);}
async function takeSelected(id,kind){await response('/actions',()=>input(`[data-object-id="${id}"][data-scene-action="take"]`,kind));await canvasReady();}
async function archiveReloadRestore(){
  const savedState=structuredClone(state);await menu();await page.locator('#save-slot-name').fill('条带已插入、未刷卡');const saved=await response('/saves',()=>page.locator('.save-slot-create-button').click(),201);const id=saved.data.slot.save_id;await close();
  await object('exit_door');await api('use_item',{item_id:'access_card',target_id:'exit_door'});await sync();assert.equal(state.device_states.exit,'CARD_ACCEPTED');
  await page.reload({waitUntil:'networkidle'});await response('/state',()=>page.getByRole('button',{name:'继续当前游戏',exact:true}).click());await menu();await page.locator(`[data-save-id="${id}"] .save-slot-restore`).click();await response(`/saves/${id}/restore`,()=>page.locator('dialog[open]').getByRole('button',{name:'读取此存档',exact:true}).click());await close();await canvasReady();
  for(const k of ['room','inventory','clues','device_states','puzzle_states','progress','minigames'])assert.deepEqual(state[k],savedState[k],k);assert(state.revision>savedState.revision);assert.notEqual(state.generation,savedState.generation);
  checks.push({check:'actual-named-save-reload-selected-restore-early-board',passed:true});
}
async function run(){
  const context=await browser.newContext({viewport:{width:1280,height:900},hasTouch:true,deviceScaleFactor:1});page=await context.newPage();page.on('pageerror',e=>issues.push({check:'uncaught',error:e.message}));
  page.on('request',r=>{const u=new URL(r.url());if(u.pathname.endsWith('/actions')&&r.method()==='POST')actionRequests.push({tool:r.postDataJSON()?.tool});if(u.hostname==='api.deepseek.com')issues.push({check:'unexpected-paid-endpoint'});});
  await page.goto(frontendURL,{waitUntil:'networkidle'});await response('/api/sessions',()=>page.getByRole('button',{name:'开始新游戏 →',exact:true}).click(),201);
  for(const id of ['r1_clock','r1_record','r1_plaque','r1_microscope'])await object(id);await object('sample_slide','take');await api('use_item',{item_id:'sample_slide',target_id:'r1_microscope'});await object('r1_microscope');await object('r1_cabinet','submit_code',{code:'4217'});await object('r1_cabinet','interact');await sync();
  if(['all','r1'].includes(only)){for(const [w,h] of [[1280,900],[375,812]]){await page.setViewportSize({width:w,height:h});await isolation('r1_cabinet',['r1_cabinet','r1_symbols','r1_fuse'],`R1-cabinet-${w}`);}await child('r1_symbols','keyboard');await select('r1_cabinet');await child('r1_fuse','touch');await takeSelected('r1_fuse','mouse');await select('r1_cabinet');await child('r1_photo','keyboard');checks.push({check:'real-cabinet-child-symbol-fuse-photo-and-back',passed:true});if(only==='r1'){await context.close();return;}}
  else{await object('r1_symbols');await object('r1_fuse','take');}
  await object('r1_door','interact');await api('move',{destination_id:'R2'});await object('r2_maintenance');await object('r2_powerbox','interact');await object('r2_powerbox','interact');await api('use_item',{item_id:'fuse',target_id:'r2_powerbox'});await sync();
  if(['all','r2'].includes(only)){await page.setViewportSize({width:1280,height:900});await isolation('r2_powerbox',['r2_powerbox',...state.minigames.circuit.modules.map(m=>m.module_id)],'R2-circuit');const m=state.minigames.circuit.modules[0];await response('/actions',()=>input(`[data-module-id="${m.module_id}"]`,'keyboard'));assert.equal(state.minigames.circuit.modules[0].rotation,(m.rotation+1)%4);}
  const rotations=solution(state.minigames.circuit);for(const m of [...state.minigames.circuit.modules])for(let t=0;t<(rotations[m.module_id]-m.rotation+4)%4;t++)await api('rotate_circuit',{target_id:'r2_powerbox',module_id:m.module_id});await api('submit_circuit',{target_id:'r2_powerbox'});await object('r2_powerbox','interact');await object('r2_monitor','interact');await object('r2_monitor','interact');await object('r2_monitor','submit_login',{username:'LAB-42',password:'2117'});await object('r2_monitor','interact');await sync();
  if(['all','r2'].includes(only)){for(const [w,h] of [[1280,900],[375,812]]){await page.setViewportSize({width:w,height:h});await isolation('r2_monitor',['r2_monitor','research_strip','access_card'],`R2-tray-${w}`);}await child('research_strip','touch');await takeSelected('research_strip','keyboard');await select('r2_monitor');await child('access_card','mouse');await takeSelected('access_card','touch');await select('r2_powerbox');await child('r2_service_label','keyboard');checks.push({check:'real-tray-items-service-label-and-current-module',passed:true});if(only==='r2'){await context.close();return;}}
  else{await object('research_strip','take');await object('access_card','take');}
  await object('r2_door','interact');await api('move',{destination_id:'R3'});await object('r3_legend');await object('r3_panel');await sync();assert.equal(state.minigames.sequence,null);
  if(['all','r3'].includes(only)){
    await select('r3_panel');await page.locator('[data-item-id="research_strip"] button').click();await response('/actions',()=>page.locator('.use-button').click());assert.equal(state.puzzle_states.panel,'STRIP_INSERTED');assert.equal(state.device_states.exit,'LOCKED');assert.equal(state.progress.check_done,false);assert.equal(state.minigames.sequence.devices.length,4);if(await page.locator('.cancel-item').isVisible())await page.locator('.cancel-item').click();assert(!state.objects.find(o=>o.object_id==='r3_panel').actions.some(a=>a.tool==='submit_sequence'));
    for(const [w,h] of [[1280,900],[375,812]]){await page.setViewportSize({width:w,height:h});await isolation('r3_panel',['r3_panel',...state.minigames.sequence.devices.map(d=>d.device_id)],`R3-early-devices-${w}`);await expect(hot('[data-device-id]')).toHaveCount(4);}
    for(const id of sequence())await input(`[data-device-id="${id}"]`,'keyboard');await expect(page.locator('.sequence-submit')).toBeDisabled();await page.locator('.sequence-clear').click();await archiveReloadRestore();
    await object('exit_door');await api('use_item',{item_id:'access_card',target_id:'exit_door'});await object('exit_door','interact');await sync();await select('r3_panel');const order=sequence();for(let i=0;i<order.length;i++)await input(`[data-device-id="${order[i]}"]`,i%2?'keyboard':'touch');await response('/actions',()=>page.locator('.sequence-submit').click());assert.equal(state.progress.check_done,true);assert.equal(state.minigames.sequence.status,'completed');
    await select('exit_door');await response('/actions',()=>input('[data-object-id="exit_door"][data-scene-action="interact"]','mouse'));await response('/actions',()=>input('[data-object-id="exit_door"][data-scene-action="interact"]','touch'));await response('/actions',()=>input('[data-object-id="exit_door"][data-scene-action="move"]','keyboard'));assert.equal(state.status,'won');await expect(page.locator('.victory-screen')).toBeVisible();await page.screenshot({path:path.join(folder,'EXIT.png'),fullPage:true});checks.push({check:'true-Canvas-finalcheck-sequence-door-EXIT',passed:true});
  }
  await context.close();
}
let code=0;
try{
  const bp=await port();let fp=await port();while(fp===bp)fp=await port();backendURL=`http://127.0.0.1:${bp}`;frontendURL=`http://127.0.0.1:${fp}`;
  start('owned-mock-backend','C:/Users/liyh/.conda/envs/1/python.exe',['-B','-X','utf8','-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',String(bp),'--no-access-log'],{AI_PROVIDER:'mock',PYTHONUTF8:'1',GAMEPLAY_VERSION:'v3.4',SQLITE_PATH:path.join(temp,'closeup.sqlite')});
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
