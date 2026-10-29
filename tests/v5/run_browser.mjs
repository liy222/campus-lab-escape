// Independent same-origin production UI QA. No intercepted API or paid model call.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import net from 'node:net';
import {spawn,execFileSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const require=createRequire(path.join(root,'frontend/package.json'));
const {chromium}=require('@playwright/test');
const output=process.argv[process.argv.indexOf('--output')+1];
const identityOnly=process.argv.includes('--identity-only')||process.env.V5_QA_BROWSER_IDENTITY_ONLY==='1';
const finalPhase=identityOnly||process.argv.includes('--identity-material-only')||process.env.V5_QA_BROWSER_IDENTITY_MATERIAL_ONLY==='1';
const afterTakeFix=process.argv.includes('--after-take-fix')||process.env.V5_QA_BROWSER_AFTER_TAKE_FIX==='1';
const remaining=finalPhase||afterTakeFix||process.argv.includes('--remaining')||process.env.V5_QA_BROWSER_REMAINING==='1';
if(!output||output==='--output')throw Error('--output directory required');
await fs.mkdir(output,{recursive:true});
const base='http://127.0.0.1:8001', python='C:/Users/liyh/.conda/envs/1/python.exe';
const temp=await fs.mkdtemp(path.join(os.tmpdir(),'campus-v5-browser-'));
const env={...process.env,SQLITE_PATH:path.join(temp,'game-v5.sqlite'),AI_PROVIDER:'mock',GAMEPLAY_VERSION:'v5',PYTHONUTF8:'1',PYTHONDONTWRITEBYTECODE:'1'};
const records=[],issues=[],errors=[],assetFailures=[];let server,browser,page;
const record=(name,details={})=>records.push({name,...details});
const check=(condition,name,details={})=>{record(name,{pass:!!condition,...details});if(!condition)throw Error(name);};
const available=await new Promise(resolve=>{const s=net.createServer();s.once('error',()=>resolve(false));s.listen(8001,'127.0.0.1',()=>s.close(()=>resolve(true)));});
if(!available){await fs.writeFile(path.join(output,'browser.json'),JSON.stringify({status:'BLOCKED',reason:'127.0.0.1:8001 already occupied; no user process stopped',paid_calls:0},null,2));process.exit(2);}
const plan=finalPhase?null:JSON.parse(execFileSync(python,['-B','-X','utf8','-m','tests.v5.browser_plan'],{cwd:root,env,encoding:'utf8',windowsHide:true}));
async function start(){
 server=spawn(python,['-B','-X','utf8','-m','uvicorn','tests.v5.fixture_server:app','--host','127.0.0.1','--port','8001','--no-access-log'],{cwd:root,env,stdio:['ignore','pipe','pipe'],windowsHide:true});
 for(let i=0;i<100;i++){if(server.exitCode!==null)throw Error('QA server exited before readiness');try{let r=await fetch(base+'/health');if(r.ok){check((await r.json()).service==='campus-lab-escape-v5','production health');return;}}catch{}await new Promise(r=>setTimeout(r,100));}throw Error('QA server readiness timeout');
}
async function stop(){if(!server||server.exitCode!==null)return;server.kill();await new Promise(resolve=>{server.once('exit',resolve);setTimeout(resolve,4000);});}
async function stable(){await page.waitForFunction(()=>!document.body.innerText.includes('正在处理…'));}
async function state(){return await page.evaluate(async()=>{const sessions=(await(await fetch('/api/v2/sessions')).json()).data.sessions;const run=sessions.find(s=>s.mode==='generated');return run?(await(await fetch(`/api/v2/sessions/${run.session_id}/state`)).json()).data.visible_state:null;});}
async function snap(label){await page.screenshot({path:path.join(output,label+'.png'),fullPage:true});record('screenshot',{file:label+'.png'});}
async function close(){if(await page.getByRole('button',{name:'关闭面板',exact:true}).isVisible().catch(()=>false))await page.getByRole('button',{name:'关闭面板',exact:true}).click();}
async function controlSizes(label){
 const sizes=await page.locator('button:visible,input:visible,select:visible,textarea:visible').evaluateAll(es=>es.filter(e=>!e.disabled).map(e=>{const r=e.getBoundingClientRect();return {label:e.getAttribute('aria-label')||e.textContent?.slice(0,36)||e.tagName,w:r.width,h:r.height};}));
 check(sizes.every(s=>s.w>=43.9&&s.h>=43.9),'44px controls '+label,{sizes});
 check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'no horizontal overflow '+label);
}
async function save(name){await close();await page.getByRole('button',{name:'进度与存档',exact:true}).click();await page.getByLabel('存档名称',{exact:true}).fill(name);await page.getByRole('button',{name:'保存新时刻',exact:true}).click();await stable();await page.locator('.v5-save').filter({has:page.getByRole('heading',{name,exact:true})}).waitFor();await close();}
async function login(register=false,name='qa_browser'){
 if(register)await page.getByRole('button',{name:'第一次来？注册本地账户',exact:true}).click();
 await page.getByLabel('用户名（3–24位字母、数字或下划线）',{exact:true}).fill(name);
 await page.getByLabel('密码（12–128位）',{exact:true}).fill('Synthetic-browser-password!');
 await page.getByRole('button',{name:register?'注册并进入':'登录',exact:true}).click();await page.getByRole('heading',{name:'我的关卡',exact:true}).waitFor();
}
try{
 await start();browser=await chromium.launch({headless:true,channel:'chrome'});const context=await browser.newContext({viewport:{width:1280,height:720}});page=await context.newPage();
 context.on('page',p=>p.on('pageerror',e=>errors.push(e.message)));
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{const u=new URL(r.url());if(!['data:','blob:'].includes(u.protocol)&&u.origin!==base)issues.push('unexpected external request origin');});
 page.on('response',r=>{if(r.status()>=400&&/\.(png|svg|jpg|webp|js|css)(\?|$)/.test(r.url()))assetFailures.push(r.url().replace(base,''));});
 await page.goto(base);await login(true);
 if(!remaining){await controlSizes('dashboard');await snap('dashboard-1280');
 await page.getByRole('button',{name:'进入经典关卡 →',exact:true}).click();
 await page.locator('.game-canvas-host[data-assets-ready="true"] canvas').waitFor();
    check(await page.locator('.game-canvas-host canvas').evaluate(c=>c.width>0&&c.height>0),'actual classic Phaser canvas ready');
    for(const [width,height] of [[1280,720],[1920,1080]]){await page.setViewportSize({width,height});await controlSizes('classic-'+width);await snap('classic-'+width);}
    await page.setViewportSize({width:1280,height:720});
 await page.getByRole('button',{name:'← 我的关卡',exact:true}).click();
 }else record('remaining continuation',{reused_scope:'first browser epoch dashboard/classic actual Canvas and three viewports; not repeated or added to this run count'});
 await page.getByLabel(/^校园主题/).fill('离线合成校园；不是实际模型样本');await page.getByLabel(/^房间数量/).selectOption(finalPhase?'1':'3');await page.getByLabel(/^难度/).selectOption(finalPhase?'normal':'hard');
 const keyInput=page.getByLabel('本次生成的 DeepSeek API Key',{exact:true});await keyInput.fill('SYNTHETIC-BROWSER-CREDENTIAL-ONLY');
 await page.getByRole('button',{name:'生成关卡',exact:true}).click();await page.getByRole('button',{name:'开始探索 →',exact:true}).waitFor({timeout:25000});
 check(await keyInput.inputValue()==='','generation clears key');await page.getByRole('button',{name:'开始探索 →',exact:true}).click();
 await page.locator('.v5-scene canvas').waitFor();await page.locator('.v5-hotspots button:enabled').first().waitFor();
 if(!finalPhase){await save('early');
 let viewed=new Set(afterTakeFix?[(await state()).room_id]:[]),checkedCloseup=false;
 if(afterTakeFix)record('take-fix continuation',{reused_scope:'G1 three-viewports 44px/no-overflow matrix from preceding epoch; unchanged CSS/layout, not repeated or added to this run count'});
 for(let index=0;index<plan.witness.length;index++){
  const action=plan.witness[index];const args=action.arguments;let s=await state();
  if(!viewed.has(s.room_id)){
   await close();
   for(const [width,height] of [[1280,720],[1920,1080]]){await page.setViewportSize({width,height});await controlSizes(s.room_id+'-'+width);await snap(s.room_id+'-'+width);}
   await page.setViewportSize({width:1280,height:720});viewed.add(s.room_id);
  }
  if(index===Math.floor(plan.witness.length/2))await save('middle');
  if(index===plan.witness.length-1)await save('late');
  if(action.tool==='inspect'){
   await close();const object=s.objects.find(o=>o.object_id===args.object_id);check(!!object,'witness object publicly visible');
   const button=page.getByRole('button',{name:'查看'+object.name,exact:true});
   if(!checkedCloseup){await button.focus();await page.keyboard.press('Enter');}else await button.click();
   await stable();
   if(!checkedCloseup){const before=(await state()).revision;check(await page.locator('.v5-hotspots button:enabled').count()===0,'closeup disables background targets');await page.locator('.v5-scene canvas').click({position:{x:10,y:10},force:true});check((await state()).revision===before,'closeup background no action');await snap('closeup-public-clue');checkedCloseup=true;record('first actual inspect keyboard Enter opens closeup',{pass:true});}
  }else if(action.tool==='take'){
   await close();const object=s.objects.find(o=>o.actions.some(a=>a.tool==='take'&&a.arguments.item_id===args.item_id));await page.getByRole('button',{name:'查看'+object.name,exact:true}).click();await stable();await page.getByRole('button',{name:'拿取',exact:true}).click();await stable();await page.locator('.v5-hotspots button:enabled').first().waitFor({timeout:5000});check(await page.locator('.v5-hotspots button').evaluateAll(es=>es.length>0&&es.every(e=>!e.disabled)),'take removes invalid closeup and releases visible hotspots without Escape');
  }else if(action.tool==='move'){
   await close();const exit=s.exits.find(e=>e.destination_id===args.destination_id);await page.getByRole('button',{name:exit.name+' →',exact:true}).click();
  }else{
   const obj=s.objects.find(o=>o.target_id===args.target_id);const heading=page.getByRole('heading',{name:obj.name,exact:true});
   if(!await heading.isVisible().catch(()=>false)){await close();await page.getByRole('button',{name:'查看'+obj.name,exact:true}).click();await stable();}
   if(action.tool==='submit_code'){await page.getByLabel('输入你的推理',{exact:true}).fill(args.code);await page.getByRole('button',{name:'提交密码',exact:true}).click();}
   else if(action.tool==='use_item'){const item=s.inventory.find(i=>i.item_id===args.item_id);await page.getByRole('button',{name:'使用 '+item.name,exact:true}).click();}
   else if(action.tool==='rotate_circuit')await page.getByRole('button',{name:'顺时针旋转 '+args.module_id,exact:true}).click();
   else if(action.tool==='submit_circuit')await page.getByRole('button',{name:'检查线路',exact:true}).click();
   else if(action.tool==='submit_sequence'){for(const id of args.device_ids)await page.locator('.v5-sequence button').filter({hasText:id}).click();await page.getByRole('button',{name:'提交顺序',exact:true}).click();}
   else throw Error('Unhandled legal witness tool');
  }
  await stable();record('actual UI legal action',{index,tool:action.tool});
 }
 await page.getByRole('heading',{name:'你找到了出口。',exact:true}).waitFor();check((await state()).status==='won','UI and server explicit EXIT won');await snap('victory');
 await page.getByRole('button',{name:'查看存档',exact:true}).click();check(await page.locator('.v5-save').count()===3,'three UI archives');
 const middle=page.locator('.v5-save').filter({has:page.getByRole('heading',{name:'middle',exact:true})});await middle.getByRole('button',{name:'删除',exact:true}).click();await page.getByRole('button',{name:'取消',exact:true}).click();check(await page.locator('.v5-save').count()===3,'cancel delete preserves archives');
 await middle.getByRole('button',{name:'删除',exact:true}).click();await page.getByRole('button',{name:'确认删除',exact:true}).click();await stable();check(await page.locator('.v5-save').count()===2,'selected delete only');
 await page.locator('.v5-save').filter({has:page.getByRole('heading',{name:'early',exact:true})}).getByRole('button',{name:'读取',exact:true}).click();await page.getByRole('button',{name:'确认读取',exact:true}).click();await stable();check((await state()).status==='playing','restore early leaves victory');await page.reload();await page.getByRole('button',{name:'继续探索 →',exact:true}).click();await page.locator('.v5-hotspots button:enabled').first().waitFor();check((await state()).clues.length===0,'reload restored early facts');
 await stop();await start();await page.reload();await page.getByRole('button',{name:'继续探索 →',exact:true}).click();await page.locator('.v5-hotspots button:enabled').first().waitFor();check((await state()).clues.length===0,'process restart restored early facts');
 await page.getByRole('button',{name:'退出登录',exact:true}).click();await login(false);await page.getByRole('button',{name:'继续探索 →',exact:true}).click();await page.locator('.v5-hotspots button:enabled').first().waitFor();check((await state()).clues.length===0,'relogin restores owned progress');
 }else{
  record('identity/material-only continuation',{reused_scope:'38-action route, take fix, keyboard/background, all viewport matrices, archives/reload/restart/relogin from preceding epochs; not rerun or summed'});
  if(!identityOnly){
  async function inspectMaterial(name){await close();await page.getByRole('button',{name:'查看'+name,exact:true}).click();await stable();}
  await inspectMaterial('装置1');let text=await page.locator('.v5-panel').innerText();check(!text.includes('fact_source')&&!text.includes('fact_order'),'unobserved materials absent from puzzle modal');
  await inspectMaterial('数据纸');await inspectMaterial('装置1');text=await page.locator('.v5-panel').innerText();check(!text.includes('fact_order'),'one material insufficient to reveal hidden material order');
  await inspectMaterial('读取说明');await inspectMaterial('装置1');text=await page.locator('.v5-panel').innerText();check(text.includes('fact_source')&&text.includes('fact_order')&&text.indexOf('fact_source')<text.indexOf('fact_order'),'actual modal renders discovered material combination order');await snap('public-material-order');await close();
  }else record('identity-only continuation',{reused_scope:'public material modal three-condition spotcheck from preceding epoch; setup level is real, modal checks not repeated'});
 }
 await page.getByRole('button',{name:'← 我的关卡',exact:true}).click();const tab=await context.newPage();await tab.goto(base);await tab.getByRole('heading',{name:'我的关卡',exact:true}).waitFor();await keyInput.fill('SYNTHETIC-CROSS-TAB-CREDENTIAL');await tab.getByRole('button',{name:'退出登录',exact:true}).click();await page.locator('.v5-auth').waitFor();await page.locator('.v5-auth form').getByRole('button',{name:/^(登录|注册并进入)$/}).waitFor();record('cross-tab logout shows valid anonymous auth form',{pass:true});
 const originalPage=page;page=tab;await login(true,'qa_browser_b');page=originalPage;
 await page.getByRole('heading',{name:'我的关卡',exact:true}).waitFor();
 check(await keyInput.inputValue()==='','cross-tab identity change clears key');
 check(await page.locator('.v5-account').innerText().then(t=>t.includes('qa_browser_b')),'cross-tab adopts new identity');
 check(await page.locator('.v5-levels li').count()===0,'new identity has no old owner levels');
 check(await page.evaluate(()=>!Object.keys(localStorage).concat(Object.keys(sessionStorage)).some(k=>/campus-lab-session|key|credential/i.test(k))),'no key or legacy bearer browser storage');
 check(errors.length===0,'no browser page errors');check(assetFailures.length===0,'no missing asset response');check(issues.length===0,'only same-origin requests');
}catch(error){issues.push(String(error.message||error));if(page)await snap('failure').catch(()=>{});}finally{
 if(browser)await browser.close();await stop();await fs.writeFile(path.join(output,'browser.json'),JSON.stringify({status:issues.length?'FAIL':'PASS',kind:'independent production UI plus explicitly synthetic injected generator',scope:identityOnly?'only unfinished cross-account identity/Key scope; prior material modal reused':finalPhase?'only changed public material modal and unfinished cross-account identity scope':afterTakeFix?'remaining after take fix; classic and G1 size matrices reused from preceding epochs':remaining?'remaining generated route and identity scope; classic matrix reused from first epoch':'initial full scope',records,issues,page_errors:errors,missing_assets:assetFailures,paid_calls:0,real_model_calls:0,limitations:['Synthetic generator proves offline pipeline/UI only; no real model quality claim.','Process restart is the owned QA backend only; no OS restart or interactive root CMD claim.','Desktop viewports are browser emulation.']},null,2)+'\n');
}process.exit(issues.length?1:0);
