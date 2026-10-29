// T18 independent real browser interactions. Only deterministic mock AI.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {spawn, spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const requireFrontend = createRequire(path.join(root,'frontend/package.json'));
const {chromium,expect} = requireFrontend('@playwright/test');
const candidate = process.argv[2];
assert(candidate, 'Explicit Main frozen candidate required');
const folder = path.join(root,'evidence/qa',new Date().toISOString().replace(/[-:.]/g,'')+'-m3-browser');
fs.mkdirSync(folder,{recursive:true});
const temp = fs.mkdtempSync(path.join(os.tmpdir(),'campus-qa-m3-browser-'));
const checks=[], issues=[], children=[], logs=[];
const python='C:\\Users\\liyh\\.conda\\envs\\1\\python.exe';
const backendPort=18118, frontendPort=15118;
const backendURL=`http://127.0.0.1:${backendPort}`, frontendURL=`http://127.0.0.1:${frontendPort}`;
const browsers=[['chrome','C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'],['edge','C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe']].filter(([name,executable])=>fs.existsSync(executable));
function hashes(){
  const result={};
  function walk(relative){
    const absolute=path.join(root,relative);
    if(!fs.existsSync(absolute))return;
    if(fs.statSync(absolute).isDirectory()) for(const name of fs.readdirSync(absolute)) {
      if(!['node_modules','dist','__pycache__','.pytest_cache'].includes(name))walk(path.join(relative,name));
    } else if(/\.(py|json|tsx?|mjs|css|html|txt|md)$/.test(relative)) result[relative.replaceAll('\\','/')]=crypto.createHash('sha256').update(fs.readFileSync(absolute)).digest('hex');
  }
  for(const name of ['backend/app','frontend/src','frontend/package-lock.json','frontend/vite.config.ts','scripts','tests','contracts','docs/SPEC.md'])walk(name);
  return result;
}
const before=hashes(), started=new Date().toISOString();
function start(label,exe,args,env,cwd=root){
  const child=spawn(exe,args,{cwd,env:{...process.env,AI_PROVIDER:'mock',PYTHONUTF8:'1',...env},windowsHide:true,stdio:['ignore','pipe','pipe']});
  children.push(child);
  child.on('error',()=>issues.push({stage:'start',label,error:'QA child process launch failed'}));
  for(const stream of ['stdout','stderr'])child[stream].on('data',data=>logs.push({label,stream,text:data.toString()}));
}
async function ready(url){
  const deadline=Date.now()+30000;
  while(Date.now()<deadline){try{if((await fetch(url)).ok)return;}catch{}await new Promise(r=>setTimeout(r,100));}
  throw new Error('QA loopback service unavailable');
}
async function layout(page,browser,width,stage){
  const dimensions=await page.evaluate(()=>({width:innerWidth,documentWidth:document.documentElement.scrollWidth,
    controls:[...document.querySelectorAll('button,input,textarea')].filter(e=>e.getClientRects().length).map(e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right,width:r.width};})}));
  assert(dimensions.documentWidth<=width+1,`${stage} horizontal overflow`);
  for(const c of dimensions.controls)assert(c.left>=-1&&c.right<=width+1&&c.width>0,`${stage} control outside width`);
  checks.push({browser,width,stage,dimensions});
}
async function response(page,suffix,operation){
  const waiting=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith(suffix)&&r.request().method()==='POST');
  await operation();
  const r=await waiting, body=await r.json();
  assert(!JSON.stringify(body).includes('"token"'));
  assert.equal(r.status(),200,`${suffix} rejected`);
  return body;
}
async function ask(page){
  await page.getByLabel('想问探索伙伴什么？',{exact:true}).fill('请引用已发现线索建议下一步');
  return response(page,'/ai/turns',()=>page.getByRole('button',{name:'询问伙伴',exact:true}).press('Enter'));
}
async function decide(page,operation){return response(page,`/${operation}`,()=>page.getByRole('button',{name:operation==='cancel'?'取消建议':'确认执行',exact:true}).press('Enter'));}
async function control(page,operation){
  return response(page,`/${operation}`,async()=>{
    await page.getByRole('button',{name:operation==='save'?'保存进度':operation==='reset'?'重新开始':'恢复存档',exact:true}).press('Enter');
    if(operation!=='save')await page.getByRole('dialog').getByRole('button',{name:operation==='reset'?'确认开始':'确认恢复',exact:true}).press('Enter');
  });
}
async function manual(page,object,label){
  if(object)await page.locator('.object-grid').getByRole('button',{name:new RegExp(object)}).press('Enter');
  return response(page,'/actions',()=>page.locator('.object-details').getByRole('button',{name:new RegExp(label)}).press('Enter'));
}
async function delayedAsk(page){
  let release, entered;
  const released=new Promise(r=>release=r), seen=new Promise(r=>entered=r);
  const handler=async route=>{const upstream=await route.fetch();entered();await released;await route.fulfill({response:upstream});};
  await page.route('**/ai/turns',handler);
  const waiting=ask(page);
  await seen;
  return {release,waiting,handler};
}
async function run(browser,name,width){
  const context=await browser.newContext({viewport:{width,height:900}}), page=await context.newPage();
  const pageErrors=[];
  page.on('pageerror',()=>pageErrors.push('uncaught browser exception'));
  await page.goto(frontendURL,{waitUntil:'networkidle'});
  await page.getByRole('button',{name:'开始新游戏 →',exact:true}).press('Enter');
  await expect(page.locator('#room-title')).toHaveText('值班室');
  const loading=await delayedAsk(page);
  await expect(page.locator('.ai-feedback')).toContainText('正在查看线索');
  await expect(page.locator('.inventory-refresh')).toBeEnabled();
  await layout(page,name,width,'AI-loading');
  await page.screenshot({path:path.join(folder,`${name}-${width}-loading.png`),fullPage:true});
  loading.release();
  const first=await loading.waiting;
  await page.unroute('**/ai/turns',loading.handler);
  assert.equal(first.data.visible_state.revision,2);
  assert.equal(first.data.proposal.tool,'submit_code');
  assert.equal(first.data.visible_state.inventory.length,0);
  await expect(page.locator('.proposal-card')).toContainText('382');
  await page.locator('.ai-answer .ai-references a').first().press('Enter');
  const focused=await page.evaluate(()=>document.activeElement?.id);
  assert(focused?.startsWith('clue-'),'Reference keyboard did not focus real clue');
  const cancelled=await decide(page,'cancel');
  assert.equal(cancelled.data.visible_state.revision,2);
  await expect(page.locator('.proposal-status')).toContainText('cancelled');
  const fresh=await ask(page);
  assert.notEqual(fresh.data.proposal.proposal_id,first.data.proposal.proposal_id);
  const committed=await decide(page,'confirm');
  assert.equal(committed.data.receipt.revision_before,2);
  assert.equal(committed.data.receipt.revision_after,3);
  await expect(page.locator('.proposal-status')).toContainText('committed');
  await expect(page.locator('.committed-receipt')).toContainText('进度 2 → 3');
  await page.locator('.ai-trace summary').press('Enter');
  const trace=await page.locator('.ai-trace').innerText();
  assert(trace.includes('proposed')&&trace.includes('committed')&&trace.includes('revision_before'));
  assert(!/(authorization|api_key|x-session-token|"token"|opened_containers|game_fields)/i.test(trace));
  fs.writeFileSync(path.join(folder,`${name}-${width}-UI-trace.txt`),trace);
  await layout(page,name,width,'proposed-cancelled-committed');
  await page.screenshot({path:path.join(folder,`${name}-${width}-committed.png`),fullPage:true});
  await control(page,'save');
  await ask(page);
  await manual(page,'门卡','拾取');
  await expect(page.getByRole('button',{name:'确认执行',exact:true})).toBeDisabled();
  await expect(page.locator('.proposal-card')).toContainText('旧建议');
  await ask(page);
  const restored=await control(page,'restore');
  await expect(page.locator('.proposal-card')).toHaveCount(0);
  const oldGeneration=await delayedAsk(page);
  const reset=await control(page,'reset');
  oldGeneration.release(); await oldGeneration.waiting;
  await page.unroute('**/ai/turns',oldGeneration.handler);
  await expect(page.locator('.proposal-card')).toHaveCount(0);
  await expect(page.locator('.clues')).toContainText('第一页，等待发现');
  assert.notEqual(reset.data.visible_state.generation,restored.data.visible_state.generation);
  await control(page,'restore');
  const takeProposal=await ask(page);
  let uncertainCalls=0;
  await page.route('**/confirm',async route=>{uncertainCalls++;await route.fetch();await route.abort('failed');});
  await page.getByRole('button',{name:'确认执行',exact:true}).press('Enter');
  await expect(page.locator('.ai-feedback')).toContainText('未自动重发');
  assert.equal(uncertainCalls,1);
  await expect(page.locator('.inventory')).toContainText('门卡');
  await expect(page.getByRole('button',{name:'确认执行',exact:true})).toBeDisabled();
  await page.unroute('**/confirm');
  const oldRevision=await delayedAsk(page);
  const door=await response(page,'/actions',()=>page.locator('.inventory').getByRole('button',{name:/使用于设备间刷卡门/}).press('Enter'));
  oldRevision.release(); await oldRevision.waiting;
  await page.unroute('**/ai/turns',oldRevision.handler);
  await expect(page.locator('.exit-button')).toBeEnabled();
  await expect(page.locator('.proposal-card')).toHaveCount(0);
  const move=await ask(page);
  assert.equal(move.data.proposal.tool,'move');
  await decide(page,'confirm');
  await expect(page.locator('#room-title')).toHaveText('设备间');
  await layout(page,name,width,'AI-R2-manual-retained');
  await page.screenshot({path:path.join(folder,`${name}-${width}-R2.png`),fullPage:true});
  assert.equal(pageErrors.length,0);
  checks.push({browser:name,width,stage:'route',passed:true,confirmed_receipt:committed.data.receipt,cancel_revision:cancelled.data.visible_state.revision,
    restored_generation:restored.data.visible_state.generation,reset_generation:reset.data.visible_state.generation,uncertain_confirm_requests:uncertainCalls,
    manual_door_revision:door.data.visible_state.revision,uncertain_proposal_id:takeProposal.data.proposal.proposal_id});
  await context.close();
}
try{
  assert(browsers.length>0,'No installed Chromium browser');
  start('backend',python,['-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',String(backendPort),'--no-access-log'],{SQLITE_PATH:path.join(temp,'game.sqlite')});
  start('frontend',process.execPath,[path.join(root,'frontend/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port',String(frontendPort),'--strictPort'],{CAMPUS_BACKEND_URL:backendURL},path.join(root,'frontend'));
  await Promise.all([ready(`${backendURL}/api/health`),ready(frontendURL)]);
  for(const [name,executable] of browsers){
    const browser=await chromium.launch({headless:true,executablePath:executable});
    try{for(const width of [1280,1920])try{await run(browser,name,width);}catch(error){issues.push({browser:name,width,stage:'route',error:error.message});}}finally{await browser.close();}
  }
  const built=[];
  function scan(directory){for(const name of fs.readdirSync(directory)){const p=path.join(directory,name);if(fs.statSync(p).isDirectory())scan(p);else{
    const text=fs.readFileSync(p,'utf8');for(const pattern of ['三角记为3','青色7','冷却对应2','opened_containers','discovered_clue_ids','MODEL_API_KEY','MODEL_BASE_URL','game_fields'])assert(!text.includes(pattern),`Unexpected private pattern in built ${name}`);built.push(path.relative(root,p));}}}
  scan(path.join(root,'frontend/dist'));checks.push({stage:'A18-targeted-built-scan',files:built,passed:true});
}catch(error){issues.push({stage:'runner',error:error.message});}
finally{
  for(const child of children)if(child.pid){const r=spawnSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,encoding:'utf8'});checks.push({stage:'stop-owned-child',pid:child.pid,exit_code:r.status});}
  const resolved=fs.realpathSync(temp), tempRoot=fs.realpathSync(os.tmpdir());
  assert.equal(path.dirname(resolved).toLowerCase(),tempRoot.toLowerCase());assert(path.basename(resolved).startsWith('campus-qa-m3-browser-'));assert.equal(path.resolve(temp).toLowerCase(),resolved.toLowerCase());
  fs.rmSync(resolved,{recursive:true});
  const after=hashes();if(JSON.stringify(before)!==JSON.stringify(after))issues.push({stage:'source-freeze',error:'Candidate source changed during run'});
  fs.writeFileSync(path.join(folder,'checks.json'),JSON.stringify({checks,issues},null,2));
  fs.writeFileSync(path.join(folder,'server-startup-only.json'),JSON.stringify(logs,null,2));
  const evidenceHashes=Object.fromEntries(fs.readdirSync(folder).map(name=>[name,crypto.createHash('sha256').update(fs.readFileSync(path.join(folder,name))).digest('hex')]));
  const result={candidate,command:[process.execPath,...process.argv.slice(1)],provider:'deterministic mock only, no paid network provider',started,ended:new Date().toISOString(),browsers,widths:[1280,1920],source_sha256_before:before,source_sha256_after:after,evidence_sha256:evidenceHashes,
    head:spawnSync('git',['-c',`safe.directory=${root.replaceAll('\\','/')}`,'rev-parse','HEAD'],{cwd:root,encoding:'utf8',windowsHide:true}).stdout.trim(),exit_code:issues.length?1:0,
    privacy:'No creation response, headers, token/sessionStorage, HAR, raw provider data or private DB exported. UI trace saved as public visible text.'};
  fs.writeFileSync(path.join(folder,'run.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify({evidence:folder,routes:checks.filter(c=>c.stage==='route'),issues,exit_code:result.exit_code},null,2));process.exitCode=result.exit_code;
}
