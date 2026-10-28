// Focused Synthetic experience check. All browser 8001 requests are forwarded
// to our owned 8002 process; the user's 8001 service is never contacted.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import net from 'node:net';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const require=createRequire(path.join(root,'frontend/package.json'));
const {chromium}=require('@playwright/test');
const remaining=process.argv.includes('--remaining'),tail=process.argv.includes('--tail');
const out=path.join(root,'evidence/upgrade/v5.0/experience-20261028',tail?'browser-tail1':remaining?'browser-run2':'');
await fs.mkdir(out,{recursive:true});
const ownedDirs=tail?(await fs.readdir(os.tmpdir())).filter(n=>n.startsWith('campus-experience-')):[];
const latest=tail?(await Promise.all(ownedDirs.map(async n=>({p:path.join(os.tmpdir(),n),t:(await fs.stat(path.join(os.tmpdir(),n))).mtimeMs})))).sort((a,b)=>b.t-a.t)[0]?.p:null;
const temp=tail?latest:await fs.mkdtemp(path.join(os.tmpdir(),'campus-experience-'));if(!temp||!path.basename(temp).startsWith('campus-experience-'))throw Error('owned TEMP required');
const base='http://127.0.0.1:8001', theme='雨夜里的天文社旧活动室,寻找封存的观测记录';
const checks=[],screenshots=[];let server,browser,page,context,state,stage='start',delayAction=false,omitTheme=false,external=0;
function check(value,name,detail={}){checks.push({name,pass:!!value,...detail});if(!value)throw Error(name);}
const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function stable(){await page.waitForFunction(()=>!document.querySelector('[aria-busy="true"]'));}
async function shot(name){await page.screenshot({path:path.join(out,name+'.png'),fullPage:true});screenshots.push(name+'.png');}
async function sizes(label){const values=await page.locator('button:visible,input:visible,select:visible,textarea:visible').evaluateAll(es=>es.filter(e=>!e.disabled).map(e=>{const r=e.getBoundingClientRect();return {w:r.width,h:r.height};}));check(values.every(r=>r.w>=43.9&&r.h>=43.9),'44px '+label);check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'no overflow '+label);}
async function post(click,suffix='/actions'){
 const wait=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname.endsWith(suffix));
 await click();const response=await wait;const body=await response.json();if(body.data?.visible_state)state=body.data.visible_state;if(body.visible_state)state=body.visible_state;await stable();return {response,body};
}
async function close(){const b=page.getByRole('button',{name:'关闭面板',exact:true});if(await b.isVisible())await b.click();}
async function login(register){if(register)await page.getByRole('button',{name:'第一次来？注册本地账户',exact:true}).click();await page.getByLabel('用户名（3–24位字母、数字或下划线）',{exact:true}).fill('experience_synthetic');await page.getByLabel('密码（12–128位）',{exact:true}).fill('Synthetic-Experience-only!');await page.getByRole('button',{name:register?'注册并进入':'登录',exact:true}).click();await page.getByRole('heading',{name:'我的关卡',exact:true}).waitFor();}
async function startGame(){await page.getByRole('button',{name:/^(开始|继续)探索 →$/}).click();await page.locator('.v5-hotspots button:enabled').first().waitFor();await stable();}
let exit=1,serverClosed=false;
try{
 const available=await new Promise(resolve=>{const s=net.createServer();s.once('error',()=>resolve(false));s.listen(8002,'127.0.0.1',()=>s.close(()=>resolve(true)));});check(available,'owned port8002 available');
 server=spawn('C:/Users/liyh/.conda/envs/1/python.exe',['-B','-X','utf8','-m','uvicorn','tests.v5.experience_fixture_server:app','--host','127.0.0.1','--port','8002','--no-access-log'],{cwd:root,env:{...process.env,SQLITE_PATH:path.join(temp,'game-v5.sqlite'),GAMEPLAY_VERSION:'v5',AI_PROVIDER:'mock',EXPERIENCE_REUSE_TEMP:tail?'1':'0',PYTHONDONTWRITEBYTECODE:'1'},stdio:'ignore',windowsHide:true});
 for(let i=0;i<70;i++){const ok=await new Promise(resolve=>{const req=http.get({hostname:'127.0.0.1',port:8002,path:'/health',headers:{host:'127.0.0.1:8001'}},r=>{r.resume();resolve(r.headers['x-qa-synthetic-experience']==='owned-temp-only');});req.on('error',()=>resolve(false));});if(ok)break;if(i===69)throw Error('owned server readiness');await pause(100);}
 browser=await chromium.launch({headless:true,channel:'chrome'});context=await browser.newContext({viewport:{width:1280,height:720}});
 await context.route('**/*',async route=>{
  const req=route.request(),u=new URL(req.url());if(['data:','blob:'].includes(u.protocol))return route.continue();
  if(u.origin!==base){external++;return route.abort();}
  if(delayAction&&u.pathname.endsWith('/actions')&&req.method()==='POST'){delayAction=false;await pause(650);}
  const r=await route.fetch({url:req.url().replace(base,'http://127.0.0.1:8002'),headers:{...req.headers(),host:'127.0.0.1:8001'}});
  if(omitTheme&&u.pathname.startsWith('/api/v2/levels')&&r.ok()){
   const body=await r.json();if(body.data?.level)delete body.data.level.theme;if(body.data?.levels)body.data.levels.forEach(x=>delete x.theme);return route.fulfill({response:r,json:body});
  }
  return route.fulfill({response:r});
 });
 page=await context.newPage();page.setDefaultTimeout(12000);
 page.on('response',async r=>{if(r.url().includes('/api/v2/sessions')&&r.request().method()==='GET'){try{const b=await r.json();if(b.data?.visible_state)state=b.data.visible_state;}catch{}}});
 stage='registration-and-create';await page.goto(base);if(tail){await login(false);}else{await login(true);if(!remaining){await sizes('create desktop');await shot('create-desktop');}
 stage='theme-field';await page.getByLabel(/校园主题/).fill(theme);stage='room-select';await page.getByLabel(/^房间数量/).selectOption('1');stage='difficulty-select';await page.getByLabel(/^难度/).selectOption('hard');stage='synthetic-key-input';await page.getByLabel(/本次生成的 DeepSeek API Key/).fill('SYNTHETIC-ONLY-NOT-A-REAL-KEY');stage='generate';await page.getByRole('button',{name:'生成关卡 →',exact:true}).click();await page.getByRole('button',{name:'开始探索 →',exact:true}).waitFor({timeout:20000});
 check(await page.locator('.v5-level-description').innerText()===theme,'list theme');check(await page.getByLabel(/本次生成的 DeepSeek API Key/).inputValue()==='','synthetic input cleared');
 await startGame();await page.locator('.v5-story summary').click();check((await page.locator('.v5-story').innerText()).includes(theme)&& (await page.locator('.v5-story').innerText()).includes('封存的观测记录'),'archive theme and Synthetic story');await shot('game-desktop');
 stage='save';await page.getByRole('button',{name:'进度与存档',exact:true}).click();await stable();await page.getByLabel('存档名称',{exact:true}).fill('Synthetic线路前');await post(()=>page.getByRole('button',{name:'保存新时刻',exact:true}).click(),'/saves');await page.locator('.v5-save').waitFor();await close();
 stage='circuit-error-and-busy';await post(()=>page.getByRole('button',{name:'查看观测台配电线路',exact:true}).click());check(await page.locator('.v5-circuit-module').count()===9,'actual 3x3 modules');
 const wrong=await post(()=>page.getByRole('button',{name:'检查线路',exact:true}).click());check(wrong.body.error?.code==='WRONG_CODE','actual disconnected circuit error');check(await page.locator('.v5-error[role="alert"]').isVisible(),'error shown and busy recovered');
 const rotations=[1,1,2,2,0,0,0,1,3];let rotationsSent=0;
 for(let i=0;i<9;i++)for(let n=0;n<rotations[i];n++){
  if(rotationsSent===0){delayAction=true;const wait=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/actions'));await page.locator('.v5-circuit-module').nth(i).click();await page.locator('.v5-generated[aria-busy="true"]').waitFor();check(true,'real pending aria-busy');const response=await wait;state=(await response.json()).data.visible_state;await stable();}
  else await post(()=>page.locator('.v5-circuit-module').nth(i).click());rotationsSent++;
 }
 await post(()=>page.getByRole('button',{name:'检查线路',exact:true}).click());await page.getByRole('button',{name:'线路已接通',exact:true}).waitFor();
 check(await page.locator('.v5-circuit-module').evaluateAll(es=>es.every(e=>e.disabled&&getComputedStyle(e).cursor!=='wait')),'completed modules disabled cursor not wait');check(await page.getByRole('button',{name:'线路已接通',exact:true}).evaluate(e=>e.disabled&&getComputedStyle(e).cursor!=='wait'),'completed submit disabled cursor not wait');
 stage='responsive';for(const [w,h] of [[1280,720],[390,844],[812,375]]){await page.setViewportSize({width:w,height:h});await sizes('circuit '+w);check(await page.locator('.v5-panel').evaluate(e=>e.scrollHeight<=e.clientHeight+1||['auto','scroll'].includes(getComputedStyle(e).overflowY)),'panel scrollable '+w);await shot('circuit-'+w);}
 await close();await page.setViewportSize({width:390,height:844});await sizes('scene mobile');await shot('game-mobile');
 stage='restore';await page.getByRole('button',{name:'进度与存档',exact:true}).click();await stable();await page.getByRole('button',{name:'读取',exact:true}).click();const restored=await post(()=>page.getByRole('button',{name:'确认读取',exact:true}).click(),'/restore');check(restored.response.ok(),'real selected save restore');check(state.minigames.circuits.length===0&&state.clues.length===0,'restore early observation and clues');
 }
 stage='relogin-and-legacy';if(!tail){await page.getByRole('button',{name:'退出登录',exact:true}).click();const toggle=page.getByRole('button',{name:'已有账户，返回登录',exact:true});if(await toggle.isVisible())await toggle.click();await login(false);}check(await page.locator('.v5-level-description').innerText()===theme,'theme survives relogin');omitTheme=true;await page.reload();await page.getByRole('heading',{name:'我的关卡',exact:true}).waitFor();check((await page.locator('.v5-level-description').innerText()).includes('封存的观测记录'),'simulated legacy omission story fallback');await startGame();await page.locator('.v5-story summary').click();check(!(await page.locator('.v5-story').innerText()).includes('你的创作主题'),'simulated legacy no theme accepted');
 check(external===0,'no external browser requests');exit=0;
}catch(error){checks.push({name:'failure',pass:false,stage,error_type:error.constructor.name});}
finally{if(browser)await browser.close();if(server){serverClosed=await new Promise(resolve=>{if(server.exitCode!==null||server.signalCode!==null)return resolve(true);server.once('close',()=>resolve(true));server.kill();setTimeout(()=>resolve(false),4000);});}if(!serverClosed){exit=1;checks.push({name:'owned server stopped',pass:false});}
 const result={kind:'Synthetic focused experience browser',exit_code:exit,checks,screenshots,owned_server_stopped:serverClosed,player8001_service_contacted:false,transport:'isolated context all 8001 requests forwarded to owned8002 with original Host/Origin',paid_calls:0,real_model_semantic_quality_tested:false,legacy_theme_omission_explicit_simulation:true};await fs.writeFile(path.join(out,'browser-result.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({exit_code:exit,stage,checks:checks.length,failed:checks.filter(c=>!c.pass),screenshots:screenshots.length,owned_server_stopped:serverClosed}));}
process.exitCode=exit;
