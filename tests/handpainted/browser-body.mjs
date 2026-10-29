// New independent route body. Shared helpers above are copied from sealed successful QA.
const renderSnapshots=[];
const paintedMetadata=read('frontend/src/assets/painted-metadata.json');
const semantic = s => Object.fromEntries(['status','room','inventory','clues','device_states','puzzle_states','progress','minigames','statistics','settlement'].map(k=>[k,s[k]]));
async function idle(){await canvasReady();await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-animation','idle');}
async function edgeInput(selector,kind){
  await idle();const button=hot(selector);await expect(button).toHaveCount(1);await expect(button).toBeEnabled();
  const bounds=(await button.getAttribute('data-bounds')).split(',').map(Number),canvas=await page.locator('.game-canvas-host canvas').boundingBox();assert(canvas);
  const left=canvas.x+bounds[0]*canvas.width/1600,top=canvas.y+bounds[1]*canvas.height/900,w=bounds[2]*canvas.width/1600,h=bounds[3]*canvas.height/900;
  const inset=3;assert(w>inset*2&&h>inset*2);
  const candidates=[{side:'left',x:left+inset,y:top+h/2},{side:'right',x:left+w-inset,y:top+h/2},{side:'top',x:left+w/2,y:top+inset},{side:'bottom',x:left+w/2,y:top+h-inset}];
  let point;for(const p of candidates)if(await page.evaluate(({x,y})=>document.elementFromPoint(x,y)?.tagName,p)==='CANVAS'){point=p;break;}
  assert(point,'An unoccluded actual Canvas edge must be reachable: '+selector);await page.mouse.click(point.x,point.y);
  checks.push({check:'actual-Canvas-edge-input',selector,kind,inset_css_px:inset,side:point.side,width:w,height:h});
}
async function uiSelect(id,kind='mouse'){
  const cancel=page.locator('.cancel-item');if(await cancel.isVisible())await cancel.click();
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
    const frames=JSON.parse(await host.locator('canvas').getAttribute('data-painted-frames')||'[]');assert(frames.length>0,label+' actual painted frames');
    for(const frame of frames){
      const meta=paintedMetadata[frame.key==='background'?'r1_background':frame.key];assert(meta,label+' known PNG key '+frame.key);
      assert.deepEqual(frame.source,[meta.bbox.x,meta.bbox.y,meta.bbox.width,meta.bbox.height],label+' exact source frame');
      assert(Math.abs(frame.box[2]/frame.source[2]-frame.box[3]/frame.source[3])<1e-8,label+' uniform aspect scale '+frame.key);
    }
    checks.push({check:'actual-render-frame-source-and-uniform-proportions',label,frames:frames.length});
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
    renderSnapshots.push({label,room:state.room.room_id,devices:state.device_states,puzzles:state.puzzle_states,view,controlledClues,paintFrame:protocol.paint_frame_marker,paintedFrames:frames,hotspots:shots});
  }
  const dimensions=await page.evaluate(()=>({w:innerWidth,h:innerHeight,scroll:document.documentElement.scrollWidth}));assert(dimensions.scroll<=dimensions.w+1,'horizontal overflow');
  await page.screenshot({path:path.join(folder,label+'.png'),fullPage:true});checks.push({check:'actual-render-state-44px-and-overflow',label,...dimensions});
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
async function finishRoute(early,r1){
  await uiAction('exit_door');await checkpoint('R3-door-FINAL_CHECK');await uiSelect('r3_panel');await checkpoint('R3-panel-FINAL_CHECK');const ids=sequence();const draftBefore=structuredClone(state);
  for(let i=0;i<ids.length;i++)await input(`[data-device-id="${ids[i]}"]`,i===0?'mouse':i===1?'keyboard':'mouse');assert.deepEqual(state,draftBefore);await response('/actions',()=>page.locator('.sequence-submit').click());await checkpoint('R3-panel-passed');
  await uiAction('exit_door');await checkpoint('R3-door-UNLOCKED');await uiAction('exit_door');await checkpoint('R3-door-OPEN');await uiMove('EXIT');
  const s=state.settlement,time=[Math.floor(s.elapsed_seconds/3600),Math.floor(s.elapsed_seconds/60)%60,Math.floor(s.elapsed_seconds)%60].map(v=>String(v).padStart(2,'0')).join(':');const values={elapsed_seconds:time,clues_found:`${s.clues_found}/${s.clues_total}`,hidden_found:`${s.hidden_found}/${s.hidden_total}`,hint_count:String(s.hint_count),mistake_count:String(s.mistake_count),rating:s.rating};for(const[k,v]of Object.entries(values))await expect(page.locator(`.victory-screen [data-stat="${k}"]`)).toHaveText(v);assert.equal(await page.locator('.game-canvas-host').count(),0);await checkpoint('Victory-desktop');
  const win=await saveMoment('已逃出');await restoreMoment(early,true);await restoreMoment(r1);await restoreMoment(win);await reload();assert.deepEqual(state.settlement,s);checks.push({check:'authoritative-Victory-six-fields-multiple-moments-restore-reload',values,archives:5});
}
async function remaining(){
  const context=await browser.newContext({viewport:{width:1280,height:900},deviceScaleFactor:1});page=await context.newPage();page.on('pageerror',e=>issues.push({check:'uncaught',error:e.message}));page.on('request',r=>{const u=new URL(r.url());if(u.pathname.endsWith('/actions')&&r.method()==='POST')actionRequests.push({tool:r.postDataJSON()?.tool});if(u.hostname==='api.deepseek.com')issues.push({check:'unexpected-paid-endpoint'});});
  await page.goto(frontendURL,{waitUntil:'networkidle'});await response('/api/sessions',()=>page.getByRole('button',{name:'开始新游戏 →',exact:true}).click(),201);
  async function fixtureSave(name){const snap=structuredClone(state),b=await api('fixture-archive',{name},'/saves');return{id:b.data.slot.save_id,state:snap,name};}
  const early=await fixtureSave('公开fixture初始');
  for(const id of ['r1_clock','r1_record','r1_plaque','r1_microscope'])await object(id);await object('sample_slide','take');await api('use_item',{item_id:'sample_slide',target_id:'r1_microscope'});await object('r1_microscope');await object('r1_cabinet','submit_code',{code:'4217'});await object('r1_cabinet','interact');await object('r1_symbols');await object('r1_fuse','take');await object('r1_photo');const r1=await fixtureSave('公开fixture取保险丝');
  await object('r1_door','interact');await api('move',{destination_id:'R2'});await object('r2_maintenance');await object('r2_powerbox','interact');await object('r2_powerbox','interact');await api('use_item',{item_id:'fuse',target_id:'r2_powerbox'});const board=structuredClone(state.minigames.circuit),answer=solution(board);for(const m of board.modules)for(let i=0;i<(answer[m.module_id]-m.rotation+4)%4;i++)await api('rotate_circuit',{target_id:board.target_id,module_id:m.module_id});await api('submit_circuit',{target_id:board.target_id});await fixtureSave('公开fixture线路已完成');await object('r2_powerbox','interact');await object('r2_service_label');await object('r2_monitor','interact');await object('r2_monitor','interact');await api('submit_login',{target_id:'r2_monitor',username:'LAB-42',password:'2117'});await object('r2_monitor','interact');await object('research_strip','take');await object('access_card','take');await object('r2_door','interact');await api('move',{destination_id:'R3'});await object('r3_legend');await object('r3_panel');await api('use_item',{item_id:'research_strip',target_id:'r3_panel'});await fixtureSave('公开fixture纸条已插入');await object('exit_door');await api('use_item',{item_id:'access_card',target_id:'exit_door'});await sync();
  checks.push({check:'continuation-fixture-boundary',scope:'Public API only prepares a fresh owned session through CARD_ACCEPTED; not counted as UI route. Prior first run covers UI R1/R2/earlyR3, restore/reload/restart/missingPNG/lazy. Only remaining FINAL_CHECK/PASS/UNLOCKED/OPEN/EXIT and end archive/Victory UI follow.'});
  if(only==='presentation'){
    await object('exit_door','interact');await object('r3_panel');await api('submit_sequence',{target_id:state.minigames.sequence.target_id,device_ids:sequence()});await object('exit_door','interact');await object('exit_door','interact');await api('move',{destination_id:'EXIT'});await sync();
    const transition=page.locator('.room-transition');if(await transition.count())await expect.poll(async()=>Number(await transition.evaluate(n=>getComputedStyle(n).opacity))).toBe(0);
    await expect(page.locator('.victory-screen')).toBeVisible();await expect(page.locator('.game-canvas-host')).toHaveCount(0);
    const native=await page.locator('.victory-screen button').evaluateAll(ns=>ns.map(n=>{const r=n.getBoundingClientRect();return{label:n.textContent,width:r.width,height:r.height};}));assert.equal(native.length,2);for(const b of native)assert(b.width>=43.9&&b.height>=43.9);
    const settledOpacity=await transition.count()?await transition.evaluate(n=>getComputedStyle(n).opacity):'absent';await page.screenshot({path:path.join(folder,'Victory-desktop-settled.png'),fullPage:true});checks.push({check:'settled-Victory-presentation-only',transition_opacity:settledOpacity,native_controls:native,scope:'Public fixture through Win; no route/build/restart/missing/lazy rerun. Final actual desktop screenshot and native controls only.'});await context.close();return;
  }
  await finishRoute(early,r1);await context.close();
}
async function run(){
  if(['remaining','presentation'].includes(only))return remaining();
  const context=await browser.newContext({viewport:{width:1280,height:900},deviceScaleFactor:1});page=await context.newPage();page.on('pageerror',e=>issues.push({check:'uncaught',error:e.message}));
  const resources=[];page.on('request',r=>{const u=new URL(r.url());resources.push({path:u.pathname,method:r.method()});if(u.pathname.endsWith('/actions')&&r.method()==='POST')actionRequests.push({tool:r.postDataJSON()?.tool});if(u.hostname==='api.deepseek.com')issues.push({check:'unexpected-paid-endpoint'});});
  await page.goto(frontendURL,{waitUntil:'networkidle'});assert(!resources.some(r=>/phaser|Room[123]|GameCanvas/.test(r.path)),'Engine lazily loaded after Start only');checks.push({check:'production-welcome-lazy-network',requests:structuredClone(resources)});
  await response('/api/sessions',()=>page.getByRole('button',{name:'开始新游戏 →',exact:true}).click(),201);await idle();await checkpoint('R1-overview');const early=await saveMoment('初始手绘房间');await pngFailure();
  for(const id of ['r1_clock','r1_record','r1_plaque','r1_microscope']){await uiSelect(id,id==='r1_clock'?'keyboard':'mouse');await checkpoint(id+'-initial');}await uiSelect('r1_clock');
  await uiAction('sample_slide','take','mouse');await uiUse('sample_slide','r1_microscope');await uiSelect('r1_microscope');await checkpoint('R1-microscope-slide');
  await uiSelect('r1_cabinet');await checkpoint('R1-cabinet-LOCKED');await page.locator('#code-r1_cabinet').fill('4217');await response('/actions',()=>page.locator('.code-form button').click());await checkpoint('R1-cabinet-CODE_ACCEPTED');
  await uiAction('r1_cabinet');await checkpoint('R1-cabinet-OPEN');await isolation('r1_cabinet',['r1_cabinet','r1_symbols','r1_fuse'],'R1-real-closeup-isolation');await uiSelect('r1_symbols');await checkpoint('R1-symbols');await uiAction('r1_fuse','take');await uiSelect('r1_cabinet');await checkpoint('R1-cabinet-ITEM_TAKEN');await uiSelect('r1_photo');await checkpoint('R1-hidden-photo');
  const r1=await saveMoment('已取保险丝');await uiAction('r1_door');await uiMove('R2');await overview();await checkpoint('R2-overview-dark');await uiSelect('r2_maintenance');await checkpoint('R2-maintenance');await uiSelect('r2_monitor');await checkpoint('R2-computer-OFF');
  await uiSelect('r2_powerbox');await checkpoint('R2-powerbox-CLOSED');await uiAction('r2_powerbox');await checkpoint('R2-powerbox-OPEN');await uiAction('r2_powerbox');await checkpoint('R2-powerbox-MISSING_FUSE');await uiUse('fuse','r2_powerbox');await checkpoint('R2-powerbox-FUSE_INSTALLED');
  await isolation('r2_powerbox',['r2_powerbox',...state.minigames.circuit.modules.map(m=>m.module_id)],'R2-real-closeup-isolation');
  const board=structuredClone(state.minigames.circuit),answer=solution(board);for(const m of board.modules)for(let i=0;i<(answer[m.module_id]-m.rotation+4)%4;i++)await response('/actions',()=>input(`[data-module-id="${m.module_id}"]`,i===0?'mouse':'mouse'));
  await response('/actions',()=>page.locator('.circuit-submit').click());assert.equal(state.device_states.powerbox,'CIRCUIT_READY');assert.equal(state.progress.power_on,false);await checkpoint('R2-powerbox-CIRCUIT_READY');const dark=await saveMoment('线路完成仍未通电');
  await uiAction('r2_powerbox');await checkpoint('R2-powerbox-POWER_ON');await overview();await checkpoint('R2-overview-on');await uiSelect('r2_service_label');await checkpoint('R2-hidden-maintenance');
  await uiMove('R1');await checkpoint('R1-return-powered');await uiMove('R2');await restoreMoment(dark);assert.equal(state.progress.power_on,false);await overview();await checkpoint('R2-restored-dark');await uiAction('r2_powerbox');
  await uiAction('r2_monitor');await checkpoint('R2-computer-BOOTING');await uiAction('r2_monitor');await checkpoint('R2-computer-LOGIN_LOCKED');await page.locator('#terminal-username').fill('LAB-42');await page.locator('#terminal-password').fill('2117');await response('/actions',()=>page.locator('.login-form [data-scene-action="submit_login"]').click());await checkpoint('R2-computer-UNLOCKED');
  await uiAction('r2_monitor');await checkpoint('R2-computer-DATA_READ');await uiSelect('research_strip');await checkpoint('R2-research-strip');await uiAction('research_strip','take');await uiAction('access_card','take','mouse');await uiAction('r2_door');await uiMove('R3');await overview();await checkpoint('R3-overview');await uiSelect('r3_legend');await checkpoint('R3-legend');
  await uiSelect('r3_panel');await checkpoint('R3-panel-EMPTY');await uiUse('research_strip','r3_panel');assert.equal(state.device_states.exit,'LOCKED');await expect(hot('[data-device-id]')).toHaveCount(4);await expect(page.locator('.sequence-submit')).toBeDisabled();await checkpoint('R3-panel-early-STRIP_INSERTED');
  const panel=await saveMoment('纸条已插入未刷卡');await uiMove('R2');await uiMove('R3');await uiSelect('r3_panel');await expect(hot('[data-device-id]')).toHaveCount(4);await reload();await restoreMoment(panel,true);await restart();await uiSelect('r3_panel');await isolation('r3_panel',state.minigames.sequence.devices.map(d=>d.device_id),'R3-real-closeup-isolation');
  await uiSelect('exit_door');await checkpoint('R3-door-LOCKED');await uiUse('access_card','exit_door');await checkpoint('R3-door-CARD_ACCEPTED');await uiSelect('r3_panel');await expect(hot('[data-device-id]')).toHaveCount(4);await expect(page.locator('.sequence-submit')).toBeDisabled();
  await finishRoute(early,r1);await context.close();
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
  fs.writeFileSync(path.join(folder,'render-snapshots.json'),JSON.stringify(renderSnapshots,null,2)+'\n');fs.writeFileSync(path.join(folder,'run.json'),JSON.stringify({candidate:candidatePath,candidate_sha256:sha(candidatePath),command:[process.execPath,...process.argv.slice(1)],started,ended:new Date().toISOString(),exit_code:code,necessary_scope:only,commands,source_sha256_before:before,source_sha256_after:after,checks,issues,paid_calls:0,limitations:['Full backend suite omitted because backend is frozen; public fixture checks are explicitly separate from real UI progression.','No real provider quality, historical user database, root CMD interactive launch or human play-time claim.','Pixel appearance requires actual saved representative PNG inspection; automated state markers alone do not certify art quality.','Isolated QA SQLite lives only in an owned temporary directory; no credentials/session tokens recorded.']},null,2)+'\n');console.log(JSON.stringify({evidence:folder,exit_code:code,checks:checks.length,issues:issues.length}));process.exitCode=code;
}
