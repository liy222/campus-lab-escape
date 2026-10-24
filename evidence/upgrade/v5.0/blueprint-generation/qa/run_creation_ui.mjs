// Narrow creation-page copy/layout check. No generation submission or model call.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import net from 'node:net';
import {spawn} from 'node:child_process';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../../../..');
const args=process.argv.slice(2), value=name=>args[args.indexOf(name)+1];
const candidatePath=value('--candidate'), output=value('--output');
if(!candidatePath||!output||candidatePath.startsWith('--')||output.startsWith('--'))throw Error('--candidate and --output required');
const allowed=path.resolve(root,'evidence/upgrade/v5.0/blueprint-generation/qa');
if(path.relative(allowed,path.resolve(output)).startsWith('..'))throw Error('Output outside assigned QA directory');
await fs.mkdir(output,{recursive:false});
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
const candidateBytes=await fs.readFile(candidatePath), candidate=JSON.parse(candidateBytes);
const expected=candidate.source_sha256||candidate.source_hashes;
if(!expected||!Object.keys(expected).length)throw Error('Nonempty candidate required');
const hashes=async()=>Object.fromEntries(await Promise.all(Object.keys(expected).map(async name=>[name,digest(await fs.readFile(path.join(root,name)))])));
const same=(a,b)=>Object.keys(a).length===Object.keys(b).length&&Object.keys(a).every(k=>a[k]===b[k]);
const before=await hashes();
const report={scope:'Only changed creation-page copy/layout; no game route or old API suite repeated',
 candidate:candidatePath,candidate_sha256:digest(candidateBytes),source_before:before,started_at:new Date().toISOString(),
 records:[],issues:[],paid_calls:0,real_model_calls:0,generation_submissions:0};
const check=(ok,name,data={})=>{report.records.push({name,pass:!!ok,...data});if(!ok)throw Error(name);};
const portFree=await new Promise(resolve=>{const s=net.createServer();s.once('error',()=>resolve(false));s.listen(8001,'127.0.0.1',()=>s.close(()=>resolve(true)));});
let browser,server,page;
const base='http://127.0.0.1:8001';
const temp=await fs.mkdtemp(path.join(os.tmpdir(),'campus-blueprint-copy-'));
const env={...process.env,SQLITE_PATH:path.join(temp,'game-v5.sqlite'),AI_PROVIDER:'mock',GAMEPLAY_VERSION:'v5',PYTHONUTF8:'1',PYTHONDONTWRITEBYTECODE:'1'};
try{
 check(same(before,expected),'candidate sources match before UI check');
 if(!portFree)throw Error('8001 occupied; no existing process stopped');
 server=spawn('C:/Users/liyh/.conda/envs/1/python.exe',['-B','-X','utf8','-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8001','--no-access-log'],{cwd:root,env,stdio:['ignore','ignore','ignore'],windowsHide:true});
 let ready=false;
 for(let i=0;i<100;i++){
  if(server.exitCode!==null)throw Error('Owned QA server exited before readiness');
  try{const response=await fetch(base+'/health');if(response.ok&&(await response.json()).service==='campus-lab-escape-v5'){ready=true;break;}}catch{}
  await new Promise(resolve=>setTimeout(resolve,100));
 }
 check(ready,'production V5 app ready on isolated TEMP database');
 const require=createRequire(path.join(root,'frontend/package.json'));
 const {chromium}=require('@playwright/test');
 browser=await chromium.launch({headless:true,channel:'chrome'});
 page=await browser.newPage({viewport:{width:1280,height:720},hasTouch:true});
 page.on('pageerror',error=>report.issues.push('page error: '+error.message));
 page.on('request',request=>{
  const url=new URL(request.url());
  if(!['data:','blob:'].includes(url.protocol)&&url.origin!==base)report.issues.push('Unexpected external origin');
  if(request.method()==='POST'&&url.pathname==='/api/v2/level-generations'){report.generation_submissions++;report.issues.push('Unexpected generation submission');}
 });
 await page.goto(base);
 await page.getByRole('button',{name:'第一次来？注册本地账户',exact:true}).click();
 await page.getByLabel('用户名（3–24位字母、数字或下划线）',{exact:true}).fill('blueprint_layout');
 await page.getByLabel('密码（12–128位）',{exact:true}).fill('Synthetic-copy-layout-only!');
 await page.getByRole('button',{name:'注册并进入',exact:true}).click();
 await page.getByRole('heading',{name:'生成我的校园关卡',exact:true}).waitFor();
 for(const [width,height] of [[1280,720],[390,844],[812,375]]){
  await page.setViewportSize({width,height});
  const card=page.locator('.v5-generator'), copy=card.locator(':scope > p').first();
  const text=await copy.innerText();
  check(text.includes('程序')&&text.includes('结构')&&text.includes('AI')&&text.includes('校验'),'creation copy states Host structure, AI content and admission '+width,{text});
  check(!/AI.{0,6}自由设计.{0,6}依赖|无限玩法|任意新结构/.test(text),'copy makes no unrestricted structure claim '+width);
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'no horizontal overflow '+width);
  const layout=await copy.evaluate(element=>{const r=element.getBoundingClientRect();return {left:r.left,right:r.right,width:r.width,height:r.height,scrollWidth:element.scrollWidth,clientWidth:element.clientWidth};});
  check(layout.left>=0&&layout.right<=width+1&&layout.height>0&&layout.scrollWidth<=layout.clientWidth+1,'explanation wraps inside viewport '+width,{layout});
  for(const locator of [page.getByLabel(/^校园主题/),page.getByLabel(/^房间数量/),page.getByLabel(/^难度/),page.getByLabel('本次生成的 DeepSeek API Key',{exact:true}),page.getByRole('button',{name:'生成关卡',exact:true})]){
   await locator.scrollIntoViewIfNeeded();
   const bounds=await locator.boundingBox();
   check(bounds&&bounds.width>=44&&bounds.height>=44,'creation control remains 44px '+width,{bounds});
  }
  await copy.scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(output,'creation-'+width+'.png'),fullPage:true});
 }
 check(report.generation_submissions===0,'zero model/generation submissions');
}catch(error){report.issues.push(String(error.message||error));if(page)await page.screenshot({path:path.join(output,'failure.png'),fullPage:true}).catch(()=>{});}
finally{
 if(browser)await browser.close();
 if(server&&server.exitCode===null){server.kill();await new Promise(resolve=>{server.once('exit',resolve);setTimeout(resolve,4000);});}
 report.source_after=await hashes();report.source_unchanged=same(before,report.source_after);
 if(!report.source_unchanged)report.issues.push('Source changed during UI check');
 report.ended_at=new Date().toISOString();report.exit_code=report.issues.length?1:0;
 report.limitations=['Browser viewport emulation, not physical mobile or human usability acceptance.','Creation-page copy/layout only; no model-quality or gameplay-route claim.','Owned QA backend only; no user process or existing database modified.'];
 await fs.writeFile(path.join(output,'run.json'),JSON.stringify(report,null,2)+'\n');
}
console.log(JSON.stringify({evidence:output,exit_code:report.exit_code}));
process.exit(report.exit_code);
