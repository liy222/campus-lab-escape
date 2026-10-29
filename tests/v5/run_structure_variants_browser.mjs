// SD3 true Canvas routes. Only controlled synthetic matrix cache; no model IO.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import net from 'node:net';
import {spawn} from 'node:child_process';
import {createHash,randomUUID} from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const args=process.argv.slice(2), flag=name=>args[args.indexOf(name)+1];
const candidatePath=flag('--candidate'), output=flag('--output'), fixtureIndex=flag('--fixtures'), buildPath=flag('--build-receipt');
const remainingR3=args.includes('--remaining-r3'), firstRunPath=remainingR3?flag('--reuse-first-run'):null;
if([candidatePath,output,fixtureIndex,buildPath].some(x=>!x||x.startsWith('--')))throw Error('Four explicit paths required');
if(remainingR3&&(!firstRunPath||firstRunPath.startsWith('--')))throw Error('Narrow R3 continuation requires the preserved first result');
const qa=path.join(root,'evidence/upgrade/v5.0/structure-diversity/qa');
const within=(base,p)=>{const d=path.relative(base,path.resolve(p));return d!==''&&!d.startsWith('..')&&!path.isAbsolute(d);};
if(!within(qa,output)||!within(qa,fixtureIndex)||!within(qa,buildPath))throw Error('Paths outside assigned QA namespace');
const digest=value=>createHash('sha256').update(value).digest('hex');
const candidateBytes=await fs.readFile(candidatePath), candidate=JSON.parse(candidateBytes), expected=candidate.source_sha256;
if(!expected||!Object.keys(expected).length)throw Error('Frozen source map required');
async function sourceMatches(){for(const [name,hash] of Object.entries(expected)){if(digest(await fs.readFile(path.join(root,name)))!==hash)return false;}return true;}
if(!await sourceMatches())throw Error('Source mismatch before browser');
for(const filename of [fileURLToPath(import.meta.url),path.join(qa,'browser_service.py'),path.join(qa,'run_build.py'),path.resolve(fixtureIndex),path.join(root,'evidence/upgrade/v5.0/structure-diversity/candidate-qa-stage1.json')]){
 const relative=path.relative(root,filename).replaceAll('\\','/');if(expected[relative]!==digest(await fs.readFile(filename)))throw Error('Candidate omits an actual browser input');
}
const index=JSON.parse(await fs.readFile(fixtureIndex,'utf8')), buildReceipt=JSON.parse(await fs.readFile(buildPath,'utf8'));
let build=buildReceipt;
if(buildReceipt.kind==='derived_build_reuse_no_execution'){
 if(buildReceipt.new_build_executed!==false||buildReceipt.exit_code!==0||buildReceipt.candidate_sha256!==digest(candidateBytes))throw Error('Invalid derived build reuse binding');
 const originalPath=path.resolve(root,buildReceipt.original_build_receipt_path), oldCandidatePath=path.resolve(root,buildReceipt.original_build_candidate_path);
 if(!within(qa,originalPath))throw Error('Original build outside assigned QA');
 const originalBytes=await fs.readFile(originalPath), oldCandidateBytes=await fs.readFile(oldCandidatePath);
 if(digest(originalBytes)!==buildReceipt.original_build_receipt_sha256||digest(oldCandidateBytes)!==buildReceipt.original_build_candidate_sha256)throw Error('Original build references changed');
 const oldExpected=JSON.parse(oldCandidateBytes).source_sha256;
 const changes=Object.keys(oldExpected).filter(name=>expected[name]!==oldExpected[name]);
 if(changes.length!==1||changes[0]!=='tests/v5/run_structure_variants_browser.mjs'||JSON.stringify(buildReceipt.only_source_delta_from_build_candidate)!==JSON.stringify(changes))throw Error('Build reuse exceeds one QA-only JS change');
 for(const file of [originalPath,oldCandidatePath]){const relative=path.relative(root,file).replaceAll('\\','/');if(expected[relative]!==digest(await fs.readFile(file)))throw Error('Candidate omits build reuse reference');}
 build=JSON.parse(originalBytes);if(build.candidate_sha256!==digest(oldCandidateBytes))throw Error('Original build candidate mismatch');
}else if(build.candidate_sha256!==digest(candidateBytes))throw Error('Build candidate mismatch');
if(!index.synthetic_only||!within(os.tmpdir(),index.directory))throw Error('Only owned TEMP synthetic cache allowed');
const markerBytes=await fs.readFile(path.join(index.directory,'qa-owned-marker.json'));
if(digest(markerBytes)!==index.marker_sha256||!JSON.parse(markerBytes).synthetic_only)throw Error('Cache ownership marker mismatch');
const stage1=JSON.parse(await fs.readFile(path.join(root,'evidence/upgrade/v5.0/structure-diversity/candidate-qa-stage1.json'),'utf8'));
if(index.source_bundle_sha256!==stage1.source_bundle_sha256)throw Error('Cache source binding mismatch');
for(const [name,hash] of Object.entries(stage1.source_sha256)){if(expected[name]!==hash)throw Error('A stage1 input changed before Canvas');}
if(build.exit_code!==0||!build.source_before_match||!build.source_after_match||!Object.keys(build.dist_sha256||{}).length)throw Error('Successful bound build receipt required');
for(const [name,hash] of Object.entries(build.dist_sha256)){if(digest(await fs.readFile(path.join(root,name)))!==hash)throw Error('Built artifact changed');}
let firstRunSHA=null;
if(remainingR3){
 if(!within(qa,firstRunPath))throw Error('First result outside assigned QA');
 const bytes=await fs.readFile(firstRunPath), first=JSON.parse(bytes), relative=path.relative(root,path.resolve(firstRunPath)).replaceAll('\\','/');
 if(expected[relative]!==digest(bytes)||first.exit_code!==1||!first.source_after_match)throw Error('First result not source-bound/preserved');
 for(const width of [1280])if(!first.records.some(row=>row.label===`explicit-server-and-UI-EXIT-1-${width}`&&row.pass===true))throw Error('Cannot reuse incomplete R1 route');
 firstRunSHA=digest(bytes);
}
const plans={};
for(const rooms of [1,3]){const name=`R${rooms}.json`, bytes=await fs.readFile(path.join(index.directory,name));if(digest(bytes)!==index.files_sha256[name])throw Error('Synthetic fixture hash mismatch');plans[rooms]=JSON.parse(bytes);if(!plans[rooms].synthetic_only)throw Error('Not a synthetic fixture');}
await fs.mkdir(output,{recursive:false});
const privateDir=path.join(output,'raw-sensitive');await fs.mkdir(privateDir);
const base='http://127.0.0.1:8001', python='C:/Users/liyh/.conda/envs/1/python.exe';
const records=[], issues=[], pageErrors=[], assetFailures=[];
const report={kind:'SD3 real Canvas with explicitly injected synthetic generator',actor:'Independent AI QA agent',candidate_sha256:digest(candidateBytes),source_count:Object.keys(expected).length,source_bundle_sha256:candidate.source_bundle_sha256,source_before_match:true,build_receipt_sha256:digest(await fs.readFile(buildPath)),build_reused_without_new_execution:buildReceipt.kind==='derived_build_reuse_no_execution',fixture_index_sha256:digest(await fs.readFile(fixtureIndex)),reused_R1_first_result_sha256:firstRunSHA,route_scope:remainingR3?'Only unfinished R3 desktop; R1 passed first run reused':'Initial R1/R3 desktop',started_utc:new Date().toISOString(),records,issues,real_model_calls:0,paid_calls:0};
const check=(condition,label,facts={})=>{records.push({label,pass:!!condition,...facts});if(!condition)throw Error(label);};
let server,browser,page,temp,ownedServerClosed=false;
const available=await new Promise(resolve=>{const s=net.createServer();s.once('error',()=>resolve(false));s.listen(8001,'127.0.0.1',()=>s.close(()=>resolve(true)));});
if(!available){report.issues.push('OWNED_PORT_UNAVAILABLE_NO_USER_PROCESS_STOPPED');report.exit_code=2;await fs.writeFile(path.join(output,'run.json'),JSON.stringify(report,null,2)+'\n');process.exit(2);}
const require=createRequire(path.join(root,'frontend/package.json')), {chromium}=require('@playwright/test');
const serverLog=path.join(privateDir,'server-output.txt');
let logWrites=Promise.resolve();
function capture(bytes){logWrites=logWrites.then(()=>fs.appendFile(serverLog,bytes));}
async function stopOwnedServer(){if(!server||ownedServerClosed)return;if(server.exitCode===null&&server.signalCode===null)server.kill();await new Promise(resolve=>{server.once('close',resolve);setTimeout(resolve,4000);});if(!ownedServerClosed)issues.push('OWNED_SERVER_DID_NOT_STOP');}
async function state(){return page.evaluate(async()=>{const rows=(await(await fetch('/api/v2/sessions')).json()).data.sessions;const run=rows.find(x=>x.mode==='generated');return run?(await(await fetch(`/api/v2/sessions/${run.session_id}/state`)).json()).data.visible_state:null;});}
async function stable(){await page.waitForFunction(()=>!document.body.innerText.includes('正在处理…'));}
async function closePanel(){if(await page.getByRole('button',{name:'关闭面板',exact:true}).isVisible().catch(()=>false))await page.getByRole('button',{name:'关闭面板',exact:true}).click();}
async function uiAction(current,tool,args,trigger){
 const receipt=page.waitForResponse(response=>{const u=new URL(response.url());if(u.origin!==base||u.pathname!==`/api/v2/sessions/${current.session_id}/actions`||response.request().method()!=='POST')return false;try{const body=response.request().postDataJSON();return body.tool===tool&&Object.keys(body.arguments).length===Object.keys(args).length&&Object.keys(args).every(key=>JSON.stringify(body.arguments[key])===JSON.stringify(args[key]));}catch{return false;}},{timeout:15000});
 const [response]=await Promise.all([receipt,trigger()]);const value=await response.json();
 check(response.status()===200&&value.ok===true&&!!value.data?.visible_state,'owned-UI-action-receipt-'+tool,{http_status:response.status()});
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));await stable();
 return value.data.visible_state;
}
async function screenshot(label){await page.screenshot({path:path.join(output,label+'.png'),fullPage:true});records.push({label:'screenshot',file:label+'.png'});}
async function inspectLayout(label,s){
 await closePanel();await page.locator('.v5-scene canvas').waitFor();await page.locator('.v5-hotspots button:enabled').first().waitFor();
 const pixel=await page.locator('.v5-scene canvas').evaluate(c=>{const ctx=c.getContext('2d'),data=ctx?.getImageData(0,0,c.width,c.height).data;if(!data)return {w:c.width,h:c.height,colors:0};const colors=new Set();for(let y=0;y<c.height;y+=31)for(let x=0;x<c.width;x+=37){const p=(y*c.width+x)*4;colors.add(`${data[p]},${data[p+1]},${data[p+2]},${data[p+3]}`);}return {w:c.width,h:c.height,colors:colors.size};});
 check(pixel.w>0&&pixel.h>0&&pixel.colors>4,'true-rendered-Canvas-'+label,pixel);
 const scene=await page.locator('.v5-scene').boundingBox();
 const bounds=await page.locator('.v5-hotspots button').evaluateAll(es=>es.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height};}));
 check(bounds.length===s.objects.length,'hotspots-equal-server-projection-'+label,{visible_objects:bounds.length});
 check(bounds.every(b=>b.w>=43.9&&b.h>=43.9&&b.x>=scene.x-1&&b.y>=scene.y-1&&b.x+b.w<=scene.x+scene.width+1&&b.y+b.h<=scene.y+scene.height+1),'visible-targets-in-scene-and-44px-'+label);
 check(bounds.every((a,i)=>bounds.slice(i+1).every(b=>Math.min(a.x+a.w,b.x+b.w)-Math.max(a.x,b.x)<=1||Math.min(a.y+a.h,b.y+b.h)-Math.max(a.y,b.y)<=1)),'visible-targets-no-overlap-'+label);
 check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'no-horizontal-overflow-'+label);
 await screenshot(label);
}
async function runCase(rooms,width,height){
 const context=await browser.newContext({viewport:{width,height}});
 await context.route('**/*',route=>{const u=new URL(route.request().url());if(['data:','blob:'].includes(u.protocol)||u.origin===base)return route.continue();issues.push('EXTERNAL_BROWSER_ORIGIN_BLOCKED');return route.abort();});
 page=await context.newPage();page.on('pageerror',error=>{pageErrors.push(error.name);});page.on('response',response=>{if(response.status()>=400&&/\.(png|svg|jpg|webp|js|css)(\?|$)/.test(response.url()))assetFailures.push(response.status());});
 await page.goto(base);await page.getByRole('button',{name:'第一次来？注册本地账户',exact:true}).click();
 await page.getByLabel('用户名（3–24位字母、数字或下划线）',{exact:true}).fill(`sd3_r${rooms}_${width}`);
 await page.getByLabel('密码（12–128位）',{exact:true}).fill('Synthetic-SD3-only-password!');
 await page.getByRole('button',{name:'注册并进入',exact:true}).click();await page.getByRole('heading',{name:'我的关卡',exact:true}).waitFor();
 await page.getByLabel(/^校园主题/).fill('独立合成结构路线');await page.getByLabel(/^房间数量/).selectOption(String(rooms));await page.getByLabel(/^难度/).selectOption('hard');
 const key=page.getByLabel('本次生成的 DeepSeek API Key',{exact:true});await key.fill('SYNTHETIC-STRUCTURE-BROWSER-ONLY');
 await page.getByRole('button',{name:'生成关卡',exact:true}).click();await page.getByRole('button',{name:'开始探索 →',exact:true}).waitFor({timeout:30000});check(await key.inputValue()==='','synthetic-generation-Key-cleared');await page.getByRole('button',{name:'开始探索 →',exact:true}).click();
 await page.locator('.v5-hotspots button:enabled').first().waitFor();
 const plan=plans[rooms], seen=new Map(), pictured=new Set();
 let s=await state();check(s.definition_hash===plan.definition_hash,'browser-level-matches-matrix-definition-'+rooms+'-'+width);
 for(let index=0;index<plan.witness.length;index++){
  s=await state();if(!seen.has(s.room_id))seen.set(s.room_id,new Map());for(const obj of s.objects)seen.get(s.room_id).set(obj.object_id,obj.slot);
  if(!pictured.has(s.room_id)){await inspectLayout(`R${rooms}-${width}-${s.room_id}-entry`,s);pictured.add(s.room_id);}
  const action=plan.witness[index], args=action.arguments;
  if(action.tool==='inspect'){
   await closePanel();const obj=s.objects.find(o=>o.object_id===args.object_id);check(!!obj,'cached-inspect-target-publicly-visible');s=await uiAction(s,'inspect',args,()=>page.getByRole('button',{name:'查看'+obj.name,exact:true}).click());
  }else if(action.tool==='take'){
   await closePanel();const obj=s.objects.find(o=>o.actions.some(a=>a.tool==='take'&&a.arguments.item_id===args.item_id));check(!!obj,'cached-take-target-publicly-visible');s=await uiAction(s,'inspect',{object_id:obj.object_id},()=>page.getByRole('button',{name:'查看'+obj.name,exact:true}).click());s=await uiAction(s,'take',args,()=>page.getByRole('button',{name:'拿取',exact:true}).click());
  }else if(action.tool==='move'){
   await closePanel();await inspectLayout(`R${rooms}-${width}-${s.room_id}-late`,s);const exitIndex=s.exits.findIndex(e=>e.destination_id===args.destination_id);check(exitIndex>=0,'cached-move-public-exit');const exit=s.exits[exitIndex],buttons=page.locator('.v5-exits button');check(await buttons.count()===s.exits.length,'public-exit-button-count');const button=page.locator('.v5-exits button[data-destination="'+args.destination_id+'"]');check(await button.count()===1,'unique-public-destination');check(await button.getAttribute('aria-label')===exit.name&&(await button.locator('.v5-exit-name').innerText()).trim()===exit.name,'public-destination-and-exit-label');check(exit.unlocked&&await button.isEnabled()&&await button.getAttribute('data-locked')==='false','public-exit-unlocked-state');check((await button.locator('.v5-exit-status').innerText()).trim()==='可通行','public-exit-status-label');s=await uiAction(s,'move',args,()=>button.click());
  }else{
   const obj=s.objects.find(o=>o.target_id===args.target_id);check(!!obj,'cached-puzzle-target-publicly-visible');
   if(!await page.getByRole('heading',{name:obj.name,exact:true}).isVisible().catch(()=>false)){await closePanel();s=await uiAction(s,'inspect',{object_id:obj.object_id},()=>page.getByRole('button',{name:'查看'+obj.name,exact:true}).click());}
   await stable();
   if(action.tool==='submit_code'){await page.getByLabel('输入你的推理',{exact:true}).fill(args.code);s=await uiAction(s,action.tool,args,()=>page.getByRole('button',{name:'提交密码',exact:true}).click());}
   else if(action.tool==='use_item'){const item=s.inventory.find(i=>i.item_id===args.item_id);s=await uiAction(s,action.tool,args,()=>page.getByRole('button',{name:'使用 '+item.name,exact:true}).click());}
   else if(action.tool==='rotate_circuit')s=await uiAction(s,action.tool,args,()=>page.getByRole('button',{name:'顺时针旋转 '+args.module_id,exact:true}).click());
   else if(action.tool==='submit_circuit')s=await uiAction(s,action.tool,args,()=>page.getByRole('button',{name:'检查线路',exact:true}).click());
   else if(action.tool==='submit_sequence'){for(const id of args.device_ids)await page.locator('.v5-sequence button').filter({hasText:id}).click();s=await uiAction(s,action.tool,args,()=>page.getByRole('button',{name:'提交顺序',exact:true}).click());}
   else throw Error('UNSUPPORTED_CACHED_LEGAL_ACTION');
  }
  await stable();records.push({label:'actual-UI-legal-step',rooms,width,index,tool:action.tool});
 }
 await page.getByRole('heading',{name:'你找到了出口。',exact:true}).waitFor();s=await state();check(s.status==='won'&&s.room_id==='EXIT','explicit-server-and-UI-EXIT-'+rooms+'-'+width);
 const itemId=plan.draft.rooms.flatMap(x=>x.objects).find(x=>x.kind==='item').item_id;check(s.inventory.some(x=>x.item_id===itemId),'actual-item-retained-EXIT-'+rooms+'-'+width);
 check(seen.size===rooms,'actual-crossroom-route-'+rooms+'-'+width);
 if(rooms===1){check(plan.draft.rooms[0].objects.length===8,'R1-catalog-eight-not-simultaneous-claim');check(seen.values().next().value.size===8,'R1-cumulative-eight-objects');check([...seen.values().next().value.values()].sort((a,b)=>a-b).join(',')==='0,1,2,3,4,5,6,7','R1-all-eight-slots-cumulative');}
 await screenshot(`R${rooms}-${width}-EXIT`);await context.close();page=null;
}
try{
 temp=await fs.mkdtemp(path.join(os.tmpdir(),'campus-structure-browser-'));
 const serviceMarker=randomUUID();
 const env={...process.env,SQLITE_PATH:path.join(temp,'game-v5.sqlite'),GAMEPLAY_VERSION:'v5',AI_PROVIDER:'mock',PYTHONUTF8:'1',PYTHONDONTWRITEBYTECODE:'1',STRUCTURE_FIXTURE_INDEX:path.resolve(fixtureIndex),STRUCTURE_BROWSER_SERVER_RECEIPT:path.join(path.resolve(output),'server-runtime.json'),STRUCTURE_BROWSER_SERVICE_MARKER:serviceMarker};
 server=spawn(python,['-B','-X','utf8','-m','uvicorn','browser_service:app','--app-dir',qa,'--host','127.0.0.1','--port','8001','--no-access-log'],{cwd:root,env,windowsHide:true,stdio:['ignore','pipe','pipe']});
 report.owned_server_PID=server.pid;server.once('close',(code,signal)=>{ownedServerClosed=true;report.owned_server_close={closed:true,exit_code:code,signal_code:signal};});
 server.stdout.on('data',capture);server.stderr.on('data',capture);
 let ready=false;for(let i=0;i<100;i++){if(server.exitCode!==null)throw Error('OWNED_SERVER_EXITED');try{const response=await fetch(base+'/health');if(response.ok&&response.headers.get('X-Synthetic-QA-Instance')===serviceMarker&&(await response.json()).service==='campus-lab-escape-v5'){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,100));}check(ready,'owned-TEMP-service-health-marker-before-browser-auth');
 browser=await chromium.launch({headless:true,channel:'chrome'});
 const caseRooms=remainingR3?[3]:[1,3];for(const rooms of caseRooms)for(const [width,height] of [[1280,720],[1920,1080]])await runCase(rooms,width,height);
 check(pageErrors.length===0,'no-page-errors',{count:pageErrors.length});check(assetFailures.length===0,'no-missing-assets',{count:assetFailures.length});check(issues.length===0,'same-origin-only');
 const receipt=JSON.parse(await fs.readFile(path.join(output,'server-runtime.json'),'utf8'));
 check(receipt.synthetic_generation_calls===caseRooms.length*2&&receipt.network_config_ledger_nonTEMP_denied_attempts===0&&receipt.real_paid_calls===0,'expected-explicit-synthetic-generations-and-runtime-boundary',receipt);
}catch(error){
 issues.push('UI_CASE_FAILED_'+error.name);await fs.writeFile(path.join(privateDir,'failure-detail.json'),JSON.stringify({name:error.name,message:error.message,stack:error.stack},null,2)+'\n');if(page)await screenshot('failure').catch(()=>{});
}finally{
 if(browser)await browser.close();await stopOwnedServer();await logWrites;
 report.source_after_match=await sourceMatches();if(!report.source_after_match)issues.push('SOURCE_CHANGED');
 report.ended_utc=new Date().toISOString();report.exit_code=issues.length?1:0;report.raw_local_log_sha256={};
 for(const name of await fs.readdir(privateDir)){report.raw_local_log_sha256['raw-sensitive/'+name]=digest(await fs.readFile(path.join(privateDir,name)));}
 report.limitations=['Synthetic cached Draft/witness and real Canvas/API only; not model-quality evidence.','R1 catalogue8 means cumulative objects/slots and retained inventory item, not8 simultaneous visible targets.','Desktop viewport emulation, not human difficulty acceptance.','Only the owned backend child is stopped. No user process is killed; no AI/real ledger access.'];
 await fs.writeFile(path.join(output,'run.json'),JSON.stringify(report,null,2)+'\n');
}
console.log(JSON.stringify({exit_code:report.exit_code,records:records.length,source_after_match:report.source_after_match,paid_calls:0}));process.exit(report.exit_code);
