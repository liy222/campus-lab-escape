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
assert.equal(only,'all');
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8').replace(/^\uFEFF/,''));
const protocol=read('evidence/integration/handpainted/qa/preparation.json');
assert(protocol.protocol_ready,'Final owner stage selector must be bound before formal execution');
const candidate=read(candidatePath),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex');
const hashes=()=>Object.fromEntries(Object.keys(candidate.source_sha256).map(p=>[p,sha(p)]));
const before=hashes();assert.deepEqual(before,candidate.source_sha256);
for(const [p,h] of Object.entries(protocol.immutable_sha256))assert.equal(sha(p),h,p);
const folder=path.join(root,'evidence/integration/handpainted/qa',new Date().toISOString().replace(/[-:.]/g,'')+'-browser');
fs.mkdirSync(folder,{recursive:true});
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'campus-handpainted-')),children=[],commands=[],checks=[],issues=[];
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
// New independent route body. Shared helpers above are copied from sealed successful QA.
const renderSnapshots=[];
const semantic = s => Object.fromEntries(['status','room','inventory','clues','device_states','puzzle_states','progress','minigames','statistics','settlement'].map(k=>[k,s[k]]));
async function idle(){await canvasReady();await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-animation','idle');}
async function edgeInput(selector,kind){
  await idle();const button=hot(selector);await expect(button).toHaveCount(1);await expect(button).toBeEnabled();
  const bounds=(await button.getAttribute('data-bounds')).split(',').map(Number),canvas=await page.locator('.game-canvas-host canvas').boundingBox();assert(canvas);
  const left=canvas.x+bounds[0]*canvas.width/1600,top=canvas.y+bounds[1]*canvas.height/900,w=bounds[2]*canvas.width/1600,h=bounds[3]*canvas.height/900;
  const inset=3;assert(w>inset*2&&h>inset*2);
  const candidates=[{side:'left',x:left+inset,y:top+h/2},{side:'right',x:left+w-inset,y:top+h/2},{side:'top',x:left+w/2,y:top+inset},{side:'bottom',x:left+w/2,y:top+h-inset}];
  let point;for(const p of candidates)if(await page.evaluate(({x,y})=>document.elementFromPoint(x,y)?.tagName,p)==='CANVAS'){point=p;break;}
  assert(point,'An unoccluded actual Canvas edge must be reachable: '+selector);if(kind==='touch')await page.touchscreen.tap(point.x,point.y);else await page.mouse.click(point.x,point.y);
  checks.push({check:'actual-Canvas-edge-input',selector,kind,inset_css_px:inset,side:point.side,width:w,height:h});
}
async function uiSelect(id,kind='mouse'){
  await overview();
  if(['r1_symbols','r1_fuse','r1_photo'].includes(id))await select('r1_cabinet');
  if(['research_strip','access_card'].includes(id)&&!await hot(`[data-object-id="${id}"][data-scene-action="object"]`).count())await select('r2_monitor');
  if(id==='r2_service_label'&&!await hot(`[data-object-id="${id}"][data-scene-action="object"]`).count())await select('r2_powerbox');
  await response('/actions',()=>input(`[data-object-id="${id}"][data-scene-action="object"]`,kind));
  await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view',id);await idle();
  const clue=state.clues.find(c=>c.object_id===id);
  if(clue){await expect(page.locator('.closeup-reading')).toContainText(clue.text);checks.push({check:'exact-server-clue-readable',object_id:id,text:clue.text});}
  checks.push({check:'real-UI-inspect',object_id:id,kind});
}
async function uiAction(id,tool='interact',kind='mouse'){
  await uiSelect(id);const action=state.objects.find(o=>o.object_id===id)?.actions.find(a=>a.tool===tool);assert(action,id+':'+tool+' actual affordance');
  const mirror=hot(`[data-object-id="${id}"][data-scene-action="${tool}"]`);
  await response('/actions',()=>mirror.count().then(n=>n===1?input(`[data-object-id="${id}"][data-scene-action="${tool}"]`,kind):page.locator(`.closeup-actions [data-target-id="${id}"][data-scene-action="${tool}"]`).click()));await idle();
  checks.push({check:'real-UI-action',object_id:id,tool,kind});
}
async function uiUse(item,id){
  await uiSelect(id);const name=state.inventory.find(i=>i.item_id===item)?.name;assert(name,'owned '+item);
  await page.locator('.inventory-item').filter({hasText:name}).locator('.item-select-button').click();
  await response('/actions',()=>page.locator('.closeup-actions .use-button').click());await idle();
  checks.push({check:'real-UI-held-item',item_id:item,target_id:id});
}
async function uiMove(to){
  const from=state.room.room_id;
  if(to==='R1'||(from==='R3'&&to==='R2')){await overview();await response('/actions',()=>input(`[data-object-id="return_${to}"][data-scene-action="move"]`));}
  else {const id=from==='R1'?'r1_door':from==='R2'?'r2_door':'exit_door';await uiSelect(id);await response('/actions',()=>page.locator('.closeup-actions [data-scene-action="move"]').click());}
  if(to==='EXIT')await expect(page.locator('.victory-screen')).toBeVisible();else await idle();checks.push({check:'real-UI-room-move',from,to});
}
async function checkpoint(label){
  if(state.status!=='won'){
    await idle();const host=page.locator('.game-canvas-host');
    await expect(host).toHaveAttribute('data-paint-frame',protocol.paint_frame_marker);
    const view=await host.getAttribute('data-view');
    const controlledClues=state.clues.filter(c=>c.object_id===view||(view==='r1_cabinet'&&c.object_id==='r1_symbols')).map(c=>c.object_id).join(',');
    await expect(host).toHaveAttribute('data-controlled-clues',controlledClues);
    for(const [key,value]of Object.entries({...state.device_states,...state.puzzle_states})){
      const attr={cabinet:'cabinet',microscope:'microscope',powerbox:'powerbox',computer:'computer',panel:'panel',exit:'exit'}[key];if(attr)await expect(host).toHaveAttribute(`data-${attr}-state`,value);
    }
    const shots=await hot('').evaluateAll(ns=>ns.map(n=>{const r=n.getBoundingClientRect();return{id:n.dataset.objectId,device:n.dataset.deviceId,module:n.dataset.moduleId,box:n.dataset.bounds,width:r.width,height:r.height,left:r.left,right:r.right,top:r.top,bottom:r.bottom,disabled:n.disabled};}));
    for(const h of shots)assert(h.width>=43.9&&h.height>=43.9,label+' 44px '+h.id);
    for(const group of ['module','device']){
      const cells=shots.filter(h=>h[group]);for(let a=0;a<cells.length;a++)for(let b=a+1;b<cells.length;b++){
        const overlapX=Math.min(cells[a].right,cells[b].right)-Math.max(cells[a].left,cells[b].left),overlapY=Math.min(cells[a].bottom,cells[b].bottom)-Math.max(cells[a].top,cells[b].top);
        assert(!(overlapX>.05&&overlapY>.05),`${label} ${group} overlapping real rectangles: ${cells[a].id}/${cells[b].id} ${overlapX}x${overlapY}`);
      }
      if(cells.length)checks.push({check:'actual-minigame-hotspot-pairwise-nonoverlap',label,group,cells:cells.length,epsilon_css_px:.05});
    }
    const reading=page.locator('.closeup-reading');if(await reading.isVisible()){const r=await reading.boundingBox();assert(r.width>0&&r.height>0);}
    renderSnapshots.push({label,room:state.room.room_id,devices:state.device_states,puzzles:state.puzzle_states,view,controlledClues,paintFrame:protocol.paint_frame_marker,hotspots:shots});
  }
  const dimensions=await page.evaluate(()=>({w:innerWidth,h:innerHeight,scroll:document.documentElement.scrollWidth}));assert(dimensions.scroll<=dimensions.w+1,'horizontal overflow');
  await page.screenshot({path:path.join(folder,label+'.png'),fullPage:true});checks.push({check:'actual-render-state-44px-and-overflow',label,...dimensions});
}
async function mobile(label){
  for(const [width,height]of [[375,812],[812,375]]){await page.setViewportSize({width,height});await checkpoint(label+'-'+width);
    if(width===375&&label==='R1-clock'){
      for(const kind of ['mouse','touch']){await overview();const b=await response('/actions',()=>edgeInput('[data-object-id="r1_clock"][data-scene-action="object"]',kind));assert.equal(b.data.receipt.tool,'inspect');assert.equal(b.data.receipt.arguments.object_id,'r1_clock');await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view','r1_clock');checks.push({check:'R1-edge-mouse-touch-correct-object-receipt',kind});}
    }
    if(width===375&&label==='R2-circuit'){
      const id=state.minigames.circuit.modules[0].module_id;for(const kind of ['mouse','touch']){const before=state.minigames.circuit.modules.find(m=>m.module_id===id).rotation;const b=await response('/actions',()=>edgeInput(`[data-module-id="${id}"]`,kind));assert.equal(b.data.receipt.tool,'rotate_circuit');assert.equal(b.data.receipt.arguments.module_id,id);assert.equal(state.minigames.circuit.modules.find(m=>m.module_id===id).rotation,(before+1)%4);checks.push({check:'R2-edge-mouse-touch-correct-module-receipt',kind,module_id:id});}
    }
    if(width===375&&label==='R3-early-panel'){
      const id=state.minigames.sequence.devices[0].device_id,before=structuredClone(state);for(const kind of ['mouse','touch'])await edgeInput(`[data-device-id="${id}"]`,kind);
      assert.deepEqual(await page.locator('.sequence-draft li[data-device-id]').evaluateAll(ns=>ns.map(n=>n.dataset.deviceId)),[id,id]);assert.deepEqual(state,before);await expect(page.locator('.sequence-submit')).toBeDisabled();await page.locator('.sequence-clear').click();checks.push({check:'R3-edge-mouse-touch-correct-device-local-draft',device_id:id});
    }
    if(state.room.room_id==='R3'&&await hot('[data-device-id]:enabled').count()>=2&&await page.locator('.sequence-submit').isDisabled()){
      const publicIds=state.minigames.sequence.devices.map(d=>d.device_id),before=structuredClone(state);await input(`[data-device-id="${publicIds[0]}"]`,'touch');await input(`[data-device-id="${publicIds[1]}"]`,'keyboard');assert.deepEqual(state,before);await expect(page.locator('.sequence-submit')).toBeDisabled();await page.locator('.sequence-clear').click();checks.push({check:'actual-responsive-touch-and-keyboard-local-draft',width,height});
    }
  }
  await page.setViewportSize({width:1280,height:900});await idle();
}
async function saveMoment(name){await menu();const snap=structuredClone(state);await page.locator('#save-slot-name').fill(name);const b=await response('/saves',()=>page.locator('.save-slot-create-button').click(),201);assert.deepEqual(state,snap);await close();return{id:b.data.slot.save_id,state:snap,name};}
async function restoreMoment(moment,cancel=false){
  await menu();const row=page.locator(`[data-save-id="${moment.id}"]`);await row.locator('.save-slot-restore').click();const dialog=page.locator('dialog[open]');
  const sizes=await dialog.locator('button').evaluateAll(ns=>ns.map(n=>{const r=n.getBoundingClientRect();return{w:r.width,h:r.height};}));for(const s of sizes)assert(s.w>=43.9&&s.h>=43.9);
  if(cancel){const before=structuredClone(state);await dialog.getByRole('button',{name:'取消',exact:true}).click();assert.deepEqual(state,before);await row.locator('.save-slot-restore').click();}
  await response(`/saves/${moment.id}/restore`,()=>dialog.getByRole('button',{name:'读取此存档',exact:true}).click());assert.deepEqual(semantic(state),semantic(moment.state));assert.notEqual(state.generation,moment.state.generation);await close();
  if(state.status==='won')await expect(page.locator('.victory-screen')).toBeVisible();else await idle();checks.push({check:'actual-UI-selected-archive-restore',name:moment.name,cancel});
}
async function reload(){await page.reload({waitUntil:'networkidle'});await response('/state',()=>page.getByRole('button',{name:'继续当前游戏',exact:true}).click());if(state.status==='won')await expect(page.locator('.victory-screen')).toBeVisible();else await idle();checks.push({check:'actual-reload-owned-session'});}
let backendProcess,backendArgs,backendEnv;
async function restart(){const before=structuredClone(state);const kill=spawnSync('taskkill',['/PID',String(backendProcess.pid),'/T','/F'],{windowsHide:true,encoding:'utf8'});assert.equal(kill.status,0);backendProcess=start('actual-owned-backend-restarted','C:/Users/liyh/.conda/envs/1/python.exe',backendArgs,backendEnv);await ready(backendURL+'/api/health');await menu();await response('/state',()=>page.locator('.save-panel').getByRole('button',{name:'同步进度',exact:true}).click());assert.deepEqual(state,before);await close();await idle();checks.push({check:'actual-one-owned-backend-process-restart'});}
async function pngFailure(){
  const asset=protocol.failure_asset;assert(asset&&asset.includes('.png'),'Final external PNG protocol required');const snapshot=structuredClone(state);let aborted=0;
  const block=async route=>{aborted++;await route.abort('failed');};await page.route(asset,block);await page.reload({waitUntil:'networkidle'});await response('/state',()=>page.getByRole('button',{name:'继续当前游戏',exact:true}).click());
  await expect(page.locator('.canvas-error')).toBeVisible();assert(aborted>0);await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-assets-ready','false');
  const count=actionRequests.length;assert(await hot('').evaluateAll(ns=>ns.length>0&&ns.every(n=>n.disabled)));await hot('').first().evaluate(n=>n.focus());await page.keyboard.press('Enter');
  const box=await page.locator('.game-canvas-host canvas').boundingBox();await page.mouse.click(box.x+box.width*.15,box.y+box.height*.15);await page.waitForTimeout(250);assert.equal(actionRequests.length,count);assert.deepEqual(state,snapshot);
  await page.screenshot({path:path.join(folder,'R1-missing-PNG.png'),fullPage:true});await page.unroute(asset,block);await page.locator('.canvas-retry').click();await idle();assert.equal(actionRequests.length,count);assert.deepEqual(state,snapshot);checks.push({check:'actual-external-PNG-abort-blocked-input-retry',aborted,pattern:asset});
}
async function run(){
  const context=await browser.newContext({viewport:{width:1280,height:900},hasTouch:true,deviceScaleFactor:1});page=await context.newPage();page.on('pageerror',e=>issues.push({check:'uncaught',error:e.message}));
  const resources=[];page.on('request',r=>{const u=new URL(r.url());resources.push({path:u.pathname,method:r.method()});if(u.pathname.endsWith('/actions')&&r.method()==='POST')actionRequests.push({tool:r.postDataJSON()?.tool});if(u.hostname==='api.deepseek.com')issues.push({check:'unexpected-paid-endpoint'});});
  await page.goto(frontendURL,{waitUntil:'networkidle'});assert(!resources.some(r=>/phaser|Room[123]|GameCanvas/.test(r.path)),'Engine lazily loaded after Start only');checks.push({check:'production-welcome-lazy-network',requests:structuredClone(resources)});
  await response('/api/sessions',()=>page.getByRole('button',{name:'开始新游戏 →',exact:true}).click(),201);await idle();await checkpoint('R1-overview');const early=await saveMoment('初始手绘房间');await pngFailure();
  for(const id of ['r1_clock','r1_record','r1_plaque','r1_microscope']){await uiSelect(id,id==='r1_clock'?'keyboard':'mouse');await checkpoint(id+'-initial');}await uiSelect('r1_clock');await mobile('R1-clock');
  await uiAction('sample_slide','take','touch');await uiUse('sample_slide','r1_microscope');await uiSelect('r1_microscope');await checkpoint('R1-microscope-slide');
  await uiSelect('r1_cabinet');await checkpoint('R1-cabinet-LOCKED');await page.locator('#code-r1_cabinet').fill('4217');await response('/actions',()=>page.locator('.code-form button').click());await checkpoint('R1-cabinet-CODE_ACCEPTED');
  await uiAction('r1_cabinet');await checkpoint('R1-cabinet-OPEN');await isolation('r1_cabinet',['r1_cabinet','r1_symbols','r1_fuse'],'R1-real-closeup-isolation');await uiSelect('r1_symbols');await checkpoint('R1-symbols');await uiAction('r1_fuse','take');await uiSelect('r1_cabinet');await checkpoint('R1-cabinet-ITEM_TAKEN');await uiSelect('r1_photo');await checkpoint('R1-hidden-photo');
  const r1=await saveMoment('已取保险丝');await uiAction('r1_door');await uiMove('R2');await overview();await checkpoint('R2-overview-dark');await uiSelect('r2_maintenance');await checkpoint('R2-maintenance');await uiSelect('r2_monitor');await checkpoint('R2-computer-OFF');
  await uiSelect('r2_powerbox');await checkpoint('R2-powerbox-CLOSED');await uiAction('r2_powerbox');await checkpoint('R2-powerbox-OPEN');await uiAction('r2_powerbox');await checkpoint('R2-powerbox-MISSING_FUSE');await uiUse('fuse','r2_powerbox');await checkpoint('R2-powerbox-FUSE_INSTALLED');
  await isolation('r2_powerbox',['r2_powerbox',...state.minigames.circuit.modules.map(m=>m.module_id)],'R2-real-closeup-isolation');await mobile('R2-circuit');
  const board=structuredClone(state.minigames.circuit),answer=solution(board);for(const m of board.modules)for(let i=0;i<(answer[m.module_id]-m.rotation+4)%4;i++)await response('/actions',()=>input(`[data-module-id="${m.module_id}"]`,i===0?'touch':'mouse'));
  await response('/actions',()=>page.locator('.circuit-submit').click());assert.equal(state.device_states.powerbox,'CIRCUIT_READY');assert.equal(state.progress.power_on,false);await checkpoint('R2-powerbox-CIRCUIT_READY');const dark=await saveMoment('线路完成仍未通电');
  await uiAction('r2_powerbox');await checkpoint('R2-powerbox-POWER_ON');await overview();await checkpoint('R2-overview-on');await uiSelect('r2_service_label');await checkpoint('R2-hidden-maintenance');
  await uiMove('R1');await checkpoint('R1-return-powered');await uiMove('R2');await restoreMoment(dark);assert.equal(state.progress.power_on,false);await overview();await checkpoint('R2-restored-dark');await uiAction('r2_powerbox');
  await uiAction('r2_monitor');await checkpoint('R2-computer-BOOTING');await uiAction('r2_monitor');await checkpoint('R2-computer-LOGIN_LOCKED');await mobile('R2-login');await page.locator('#terminal-username').fill('LAB-42');await page.locator('#terminal-password').fill('2117');await response('/actions',()=>page.locator('.login-form [data-scene-action="submit_login"]').click());await checkpoint('R2-computer-UNLOCKED');
  await uiAction('r2_monitor');await checkpoint('R2-computer-DATA_READ');await uiSelect('research_strip');await checkpoint('R2-research-strip');await uiAction('research_strip','take');await uiAction('access_card','take','touch');await uiAction('r2_door');await uiMove('R3');await overview();await checkpoint('R3-overview');await uiSelect('r3_legend');await checkpoint('R3-legend');
  await uiSelect('r3_panel');await checkpoint('R3-panel-EMPTY');await uiUse('research_strip','r3_panel');assert.equal(state.device_states.exit,'LOCKED');await expect(hot('[data-device-id]')).toHaveCount(4);await expect(page.locator('.sequence-submit')).toBeDisabled();await checkpoint('R3-panel-early-STRIP_INSERTED');await mobile('R3-early-panel');
  const panel=await saveMoment('纸条已插入未刷卡');await uiMove('R2');await uiMove('R3');await uiSelect('r3_panel');await expect(hot('[data-device-id]')).toHaveCount(4);await reload();await restoreMoment(panel,true);await restart();await uiSelect('r3_panel');await isolation('r3_panel',state.minigames.sequence.devices.map(d=>d.device_id),'R3-real-closeup-isolation');
  await uiSelect('exit_door');await checkpoint('R3-door-LOCKED');await uiUse('access_card','exit_door');await checkpoint('R3-door-CARD_ACCEPTED');await uiSelect('r3_panel');await expect(hot('[data-device-id]')).toHaveCount(4);await expect(page.locator('.sequence-submit')).toBeDisabled();
  await uiAction('exit_door');await checkpoint('R3-door-FINAL_CHECK');await uiSelect('r3_panel');await checkpoint('R3-panel-FINAL_CHECK');const ids=sequence();const draftBefore=structuredClone(state);
  for(let i=0;i<ids.length;i++)await input(`[data-device-id="${ids[i]}"]`,i===0?'touch':i===1?'keyboard':'mouse');assert.deepEqual(state,draftBefore);await mobile('R3-sequence-draft');await response('/actions',()=>page.locator('.sequence-submit').click());await checkpoint('R3-panel-passed');
  await uiAction('exit_door');await checkpoint('R3-door-UNLOCKED');await uiAction('exit_door');await checkpoint('R3-door-OPEN');await uiMove('EXIT');
  const s=state.settlement,time=[Math.floor(s.elapsed_seconds/3600),Math.floor(s.elapsed_seconds/60)%60,Math.floor(s.elapsed_seconds)%60].map(v=>String(v).padStart(2,'0')).join(':');const values={elapsed_seconds:time,clues_found:`${s.clues_found}/${s.clues_total}`,hidden_found:`${s.hidden_found}/${s.hidden_total}`,hint_count:String(s.hint_count),mistake_count:String(s.mistake_count),rating:s.rating};for(const[k,v]of Object.entries(values))await expect(page.locator(`.victory-screen [data-stat="${k}"]`)).toHaveText(v);assert.equal(await page.locator('.game-canvas-host').count(),0);await checkpoint('Victory-desktop');
  const win=await saveMoment('已逃出');await page.setViewportSize({width:375,height:812});await restoreMoment(early,true);await checkpoint('R1-mobile-selected-restore');await restoreMoment(r1);await restoreMoment(win);await checkpoint('Victory-mobile');await reload();assert.deepEqual(state.settlement,s);checks.push({check:'authoritative-Victory-six-fields-multiple-moments-restore-reload',values,archives:5});await context.close();
}
let code=0;
try{
  const bp=await port();let fp=await port();while(fp===bp)fp=await port();backendURL=`http://127.0.0.1:${bp}`;frontendURL=`http://127.0.0.1:${fp}`;
  backendArgs=['-B','-X','utf8','-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',String(bp),'--no-access-log'];backendEnv={AI_PROVIDER:'mock',PYTHONUTF8:'1',GAMEPLAY_VERSION:'v3.4',SQLITE_PATH:path.join(temp,'handpainted.sqlite')};
  backendProcess=start('owned-mock-backend','C:/Users/liyh/.conda/envs/1/python.exe',backendArgs,backendEnv);
  start('built-preview',process.execPath,[path.join(root,'frontend/node_modules/vite/bin/vite.js'),'preview','--host','127.0.0.1','--port',String(fp),'--strictPort'],{CAMPUS_BACKEND_URL:backendURL,VITE_GAMEPLAY_VERSION:'v3.4'},path.join(root,'frontend'));
  await Promise.all([ready(backendURL+'/api/health'),ready(frontendURL)]);browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});await run();assert.deepEqual(issues,[]);
}catch(e){code=1;issues.push({check:'runner',error:e.message,stack:String(e.stack).split('\n').filter(x=>x.trim().startsWith('at '))});}
finally{
  if(browser)await browser.close();for(const p of children.reverse())if(p.pid&&p.exitCode===null){const r=spawnSync('taskkill',['/PID',String(p.pid),'/T','/F'],{windowsHide:true,encoding:'utf8'});checks.push({check:'stop-owned-process-tree',exit_code:r.status});}
  const after=hashes();if(JSON.stringify(before)!==JSON.stringify(after)){code=1;issues.push({check:'source-changed'});}for(const[p,h]of Object.entries(protocol.immutable_sha256))if(sha(p)!==h){code=1;issues.push({check:'immutable-changed',path:p});}
  fs.writeFileSync(path.join(folder,'render-snapshots.json'),JSON.stringify(renderSnapshots,null,2)+'\n');fs.writeFileSync(path.join(folder,'run.json'),JSON.stringify({candidate:candidatePath,candidate_sha256:sha(candidatePath),command:[process.execPath,...process.argv.slice(1)],started,ended:new Date().toISOString(),exit_code:code,commands,source_sha256_before:before,source_sha256_after:after,checks,issues,paid_calls:0,limitations:['Real UI main route; full backend suite omitted because backend is frozen.','No real provider quality, historical user database, root CMD interactive launch or human play-time claim.','Pixel appearance requires actual saved representative PNG inspection; automated state markers alone do not certify art quality.','Isolated QA SQLite lives only in an owned temporary directory; no credentials/session tokens recorded.']},null,2)+'\n');console.log(JSON.stringify({evidence:folder,exit_code:code,checks:checks.length,issues:issues.length}));process.exitCode=code;
}
