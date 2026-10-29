import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import net from 'node:net';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {randomUUID} from 'node:crypto';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const runId=randomUUID(),started=new Date().toISOString();
const revealOnly=process.argv.includes('--reveal-only');
if(process.argv.slice(2).some(arg=>arg!=='--reveal-only'))throw Error('Only --reveal-only is supported');
const out=path.join(root,'evidence/project/stages/v5-passage-semantics/automated',`qa-browser-${started.replace(/[:.]/g,'-')}-${runId.slice(0,8)}`);
await fs.mkdir(out,{recursive:false});
const base='http://127.0.0.1:8001',cache=process.env.SP_CACHE_DIR;
if(!cache||!path.resolve(cache).startsWith(path.resolve(os.tmpdir())))throw Error('Owned TEMP cache required');
const records=[],screenshots=[],issues=[];let server,browser,context,page,stopped=true,state,moveCalls=0,external=0;
const pause=ms=>new Promise(r=>setTimeout(r,ms));
function record(name,actual,expected,pass){records.push({name,actual,expected,pass:!!pass,observed_at_utc:new Date().toISOString(),synthetic:true});if(!pass)throw Error(name);}
async function shot(name){await page.screenshot({path:path.join(out,`qa-browser-${name}.png`),fullPage:true});screenshots.push(`qa-browser-${name}.png`);}
async function stable(){await page.waitForFunction(()=>document.querySelector('.v5-game')?.getAttribute('aria-busy')!=='true');await pause(100);}
async function textureStatus(label){
 await page.waitForFunction(()=>{const s=document.querySelector('.v5-scene');return s?.dataset.loadingTextures==='false';},null,{timeout:12000});
 const actual=await page.locator('.v5-scene').evaluate(s=>({background:s.dataset.background,theme:s.dataset.theme,missing:Number(s.dataset.missingTextures),loading:s.dataset.loadingTextures,aliases:(s.dataset.textures||'').split(/\s+/).filter(Boolean),variants:[...s.querySelectorAll('.v5-hotspots button[data-variant]')].map(b=>b.dataset.variant).filter(v=>v&&v!=='generic')}));
 const catalog=JSON.parse(await fs.readFile(path.join(root,'frontend/src/assets/generated-catalog.json'),'utf8'));
 const assetId=role=>role==='key'?'key':catalog.assets.find(asset=>asset.id===role)?.id??catalog.assets.find(asset=>asset.id==='note').id;
 const expectedAliases=actual.theme==='generic'?state.objects.map((object,index)=>`legacy:${assetId(object.art_id)}:${index}`):actual.variants.map(id=>`theme:${id}`);
 const loadedAliases=expectedAliases.filter(key=>actual.aliases.includes(key));
 record(`${label} images loaded for current aliases`,{theme:actual.theme,missing:actual.missing,loading:actual.loading,current_objects:expectedAliases.length,loaded_current_aliases:loadedAliases.length},{missing:0,loading:'false',all_current_aliases_loaded:true},actual.missing===0&&actual.loading==='false'&&expectedAliases.length>0&&loadedAliases.length===expectedAliases.length);
 return actual;
}
async function post(click){const wait=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname.endsWith('/actions'));await click();const r=await wait,b=await r.json();if(b.data?.visible_state)state=b.data.visible_state;await stable();if(!r.ok())throw Error(`synthetic action status ${r.status()}`);return b;}
async function close(){const b=page.getByRole('button',{name:'关闭面板',exact:true});if(await b.isVisible())await b.click();}
async function open(id){await close();await post(()=>page.locator(`.v5-hotspots button[data-object="${id}"]`).click());await page.locator('.v5-sheet').waitFor();}
async function dispatch(step){const {tool,arguments:a}=step;
 if(tool==='inspect'){if(!(state.observed_object_ids||[]).includes(a.object_id))await open(a.object_id);return;}
 if(tool==='move')return;
 let obj=tool==='take'?state.objects.find(o=>o.actions.some(x=>x.tool==='take'&&x.arguments.item_id===a.item_id)):state.objects.find(o=>(o.target_id||o.object_id)===(a.target_id||a.object_id));
 if(!obj)throw Error(`synthetic target unavailable: ${tool}`);await open(obj.object_id);
 if(tool==='submit_code'){await page.locator('.v5-code input').fill(a.code);await post(()=>page.getByRole('button',{name:'提交密码',exact:true}).click());}
 else if(tool==='submit_login'){await page.locator('.v5-login input').nth(0).fill(a.username);await page.locator('.v5-login input').nth(1).fill(a.password);await post(()=>page.getByRole('button',{name:'提交终端登录',exact:true}).click());}
 else if(tool==='take'){const act=obj.actions.find(x=>x.tool==='take');await post(()=>page.getByRole('button',{name:act.label,exact:true}).click());}
 else if(tool==='use_item'){const item=state.inventory.find(x=>x.item_id===a.item_id);await post(()=>page.getByRole('button',{name:`使用 ${item.name}`,exact:true}).click());}
 else if(tool==='interact'||tool==='get_inventory'){const act=obj.actions.find(x=>x.tool===tool&&Object.entries(a).every(([k,v])=>x.arguments[k]===v));if(!act)throw Error(`synthetic affordance unavailable: ${tool}`);await post(()=>page.getByRole('button',{name:act.label,exact:true}).click());}
 else if(tool==='rotate_circuit'){const board=(state.minigames.circuits||[state.minigames.circuit]).find(x=>x.target_id===a.target_id),i=board.modules.findIndex(x=>x.module_id===a.module_id);await post(()=>page.locator('.v5-circuit-module').nth(i).click());}
 else if(tool==='submit_circuit'){await post(()=>page.getByRole('button',{name:'检查线路',exact:true}).click());}
 else if(tool==='submit_sequence'){const board=(state.minigames.sequences||[state.minigames.sequence]).find(x=>x.target_id===a.target_id);await page.getByRole('button',{name:'清除草稿',exact:true}).click();for(const id of a.device_ids){const d=board.devices.find(x=>x.device_id===id);await page.getByRole('button',{name:`${d.symbol} ${d.label}`,exact:true}).click();}await post(()=>page.getByRole('button',{name:'提交顺序',exact:true}).click());}
 else throw Error(`unsupported witness action: ${tool}`);
}
async function sample(rooms){
 const theme=`SP synthetic passage ${rooms}`;await page.getByLabel(/校园主题/).fill(theme);await page.getByLabel(/^房间数量/).selectOption(String(rooms));await page.getByLabel(/^难度/).selectOption('hard');await page.getByLabel(/本次生成的 DeepSeek API Key/).fill('SYNTHETIC-ONLY-NOT-A-REAL-KEY');await page.getByRole('button',{name:/^生成关卡/}).click();
 const card=page.locator('.v5-level-card').filter({hasText:`${rooms} 间房`}).first();await card.waitFor({timeout:20000});await card.getByRole('button',{name:/探索/}).click();await page.locator('.v5-hotspots button:enabled').first().waitFor();await stable();
 const exit=state.exits[0],button=page.locator(`.v5-exits button[data-destination="${exit.destination_id}"]`);record(`R${rooms} initial visible exit`,{disabled:await button.isDisabled(),status:await button.locator('.v5-exit-status').innerText(),describedby:await button.getAttribute('aria-describedby')},{disabled:true,status:'已锁定',describedby_present:true},await button.isDisabled()&&(await button.locator('.v5-exit-status').innerText())==='已锁定'&&!!await button.getAttribute('aria-describedby'));await shot(`R${rooms}-locked`);
 const before=moveCalls,box=await button.boundingBox();await page.mouse.click(box.x+box.width/2,box.y+box.height/2);await pause(200);record(`R${rooms} physical click while locked emits no move`,moveCalls-before,0,moveCalls===before);
 const witness=JSON.parse(await fs.readFile(path.join(cache,`R${rooms}.json`),'utf8')).witness;let reached=false;
 for(const step of witness){if(step.tool==='move'){await close();const current=state.exits.find(x=>x.destination_id===step.arguments.destination_id),nav=page.locator(`.v5-exits button[data-destination="${step.arguments.destination_id}"]`);record(`R${rooms} witness unlocks forward exit`,{unlocked:current?.unlocked,disabled:await nav.isDisabled(),status:await nav.locator('.v5-exit-status').innerText()},'enabled and 可通行',!!current?.unlocked&&!await nav.isDisabled()&&(await nav.locator('.v5-exit-status').innerText())==='可通行');if(revealOnly){await textureStatus('R3 door open before room transition');await shot('R3-door-open-textures');}else await shot(`R${rooms}-unlocked`);const previousBackground=await page.locator('.v5-scene').getAttribute('data-background');const count=moveCalls;await nav.click();await page.waitForFunction(()=>document.querySelector('.v5-game')?.getAttribute('aria-busy')!=='true');await stable();record(`R${rooms} one actual UI move reaches expected destination`,{move_requests:moveCalls-count,room:state.room.room_id,status:state.status},{move_requests:1,room:step.arguments.destination_id==='EXIT'?'EXIT':step.arguments.destination_id},moveCalls-count===1&&state.room.room_id===(step.arguments.destination_id==='EXIT'?'EXIT':step.arguments.destination_id));if(revealOnly){const textures=await textureStatus('G1 to G2 actual room transition');const catalog=JSON.parse(await fs.readFile(path.join(root,'frontend/src/assets/generated-catalog.json'),'utf8'));const backgroundId=state.room.background_art_id||state.room.background_id||'neutral_lab';const expectedBackground=catalog.assets.find(asset=>asset.id===backgroundId)?.url;record('G2 uses its actual public room background after move',{from:previousBackground,to:textures.background,room_background_id:backgroundId},{to:expectedBackground,changed:true},previousBackground!==textures.background&&textures.background===expectedBackground);await shot('R3-G2-background-textures');}else await shot(`R${rooms}-destination`);reached=true;break;}await dispatch(step);if(revealOnly&&rooms===3&&((step.tool==='take')||(step.tool==='use_item')||(step.tool==='inspect'&&step.arguments.object_id==='obj_relation')||(step.tool==='submit_sequence'))){await textureStatus(`R3 reveal after ${step.tool}${step.arguments.object_id?` ${step.arguments.object_id}`:''}`);if(step.tool==='take'||(step.tool==='inspect'&&step.arguments.object_id==='obj_relation')||step.tool==='submit_sequence')await shot(`R3-reveal-${step.tool}-${step.arguments.object_id||step.arguments.item_id||step.arguments.target_id}`);}}
 record(`R${rooms} reached first witness exit`,reached,true,reached);
}
try{
 const probe=net.createServer();await new Promise((resolve,reject)=>{probe.once('error',reject);probe.listen(8002,'127.0.0.1',()=>probe.close(resolve));});
 const db=path.join(cache,'qa-import.sqlite');
 server=spawn('C:/Users/liyh/.conda/envs/1/python.exe',['-B','-X','utf8','-m','uvicorn','tests.v5.test_passage_semantics:browser_app','--host','127.0.0.1','--port','8002','--no-access-log'],{cwd:root,env:{...process.env,SQLITE_PATH:db,SP_CACHE_DIR:cache,SP_BROWSER_FIXTURE:'1',GAMEPLAY_VERSION:'v5',AI_PROVIDER:'mock',PYTHONDONTWRITEBYTECODE:'1'},stdio:'ignore',windowsHide:true});
 let ready=false;for(let i=0;i<100&&!ready;i++){ready=await new Promise(resolve=>{const r=http.get({hostname:'127.0.0.1',port:8002,path:'/health',headers:{host:'127.0.0.1:8001'}},res=>{res.resume();resolve(res.statusCode===200);});r.on('error',()=>resolve(false));r.setTimeout(600,()=>r.destroy());});if(!ready)await pause(100);}if(!ready)throw Error('owned fixture service unavailable');
 const {chromium}=createRequire(path.join(root,'frontend/package.json'))('@playwright/test');browser=await chromium.launch({headless:true,channel:'chrome'});context=await browser.newContext({viewport:{width:1280,height:720}});
 await context.route('**/*',async route=>{const req=route.request(),u=new URL(req.url());if(['data:','blob:'].includes(u.protocol))return route.continue();if(u.origin!==base){external++;return route.abort();}return route.fetch({url:req.url().replace(base,'http://127.0.0.1:8002'),headers:{...req.headers(),host:'127.0.0.1:8001'}}).then(response=>route.fulfill({response}));});
 page=await context.newPage();page.setDefaultTimeout(12000);page.on('request',req=>{if(req.method()==='POST'&&new URL(req.url()).pathname.endsWith('/actions')){try{if(JSON.parse(req.postData()||'{}').tool==='move')moveCalls++;}catch{}}});page.on('response',async r=>{if(new URL(r.url()).pathname.includes('/sessions/'))try{const b=await r.json();if(b.data?.visible_state)state=b.data.visible_state;}catch{}});
 await page.goto(base);await page.getByRole('button',{name:'第一次来？注册本地账户',exact:true}).click();await page.getByLabel('用户名（3–24位字母、数字或下划线）',{exact:true}).fill('passage_qa');await page.getByLabel('密码（12–128位）',{exact:true}).fill('Synthetic-Passage-only!');await page.getByRole('button',{name:'注册并进入',exact:true}).click();await page.getByRole('heading',{name:'我的关卡',exact:true}).waitFor();
 if(revealOnly)await sample(3);else{await sample(1);await page.getByRole('button',{name:'我的关卡',exact:true}).click();await page.getByRole('heading',{name:'我的关卡',exact:true}).waitFor();await sample(3);}
 record('no external requests',external,0,external===0);
}catch(e){issues.push({type:e?.constructor?.name||'Error',message:String(e?.message||'unknown').split('\n')[0].slice(0,120)});try{if(page)await shot('failure');}catch{}}
finally{try{await context?.unrouteAll({behavior:'ignoreErrors'});}catch{}try{await context?.close();}catch{}try{await browser?.close();}catch{}if(server)stopped=await new Promise(resolve=>{if(server.exitCode!==null||server.signalCode!==null)return resolve(true);server.once('close',()=>resolve(true));server.kill();setTimeout(()=>resolve(false),4000);});
 const exit=issues.length||!stopped||records.some(r=>!r.pass)?1:0;const result={run_id:runId,command:'node tests/v5/run_passage_semantics_browser.mjs'+(revealOnly?' --reveal-only':''),scope:revealOnly?'R3 cached witness through G1 gate and first G1→G2 move; dynamic textures only':'R1/R3 synthetic cached drafts; locked physical click; replay to first witness move; unlocked UI click; one actual move per sample',owned_service_port:8002,owned_server_stopped:stopped,external_requests:external,real_provider_calls:0,player_database_access:false,cache_files:['R1.json','R3.json'],records,screenshots,issues,exit_code:exit,limitations:['Synthetic witnesses only; not model-following or complete route acceptance','No save, classic, mobile or human acceptance claim']};await fs.writeFile(path.join(out,'qa-browser-result.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});process.exitCode=exit;}
