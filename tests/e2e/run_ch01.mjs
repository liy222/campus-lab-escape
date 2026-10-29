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
const folder = path.join(root,'evidence/qa','T30-'+new Date().toISOString().replace(/[-:.]/g,'')+'-CH01-browser');
fs.mkdirSync(folder,{recursive:true});
const temp = fs.mkdtempSync(path.join(os.tmpdir(),'campus-qa-CH01-browser-'));
const checks=[], issues=[], children=[], logs=[];
const python='C:\\Users\\liyh\\.conda\\envs\\1\\python.exe';
const backendPort=18130, frontendPort=15130;
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
  const pageErrors=[];page.on('pageerror',()=>pageErrors.push('uncaught browser exception'));
  const records=[];
  async function action(operation){const body=await response(page,'/actions',operation);records.push({stage:'manual-action',...body.data});return body.data;}
  async function inspect(object){return action(async()=>{await page.locator('.object-grid').getByRole('button',{name:new RegExp(object)}).press('Enter');await page.locator('.object-details').getByRole('button',{name:/查看/}).press('Enter');});}
  async function take(object){return action(async()=>{await page.locator('.object-grid').getByRole('button',{name:new RegExp(object)}).press('Enter');await page.locator('.object-details').getByRole('button',{name:/拾取/}).press('Enter');});}
  async function code(object,value){return action(async()=>{await page.locator('.object-grid').getByRole('button',{name:new RegExp(object)}).press('Enter');const input=page.getByLabel(object+'密码',{exact:true});await input.fill(value);await input.press('Enter');});}
  async function use(item,target){return action(()=>page.locator('.inventory-item').filter({has:page.getByRole('heading',{name:item,exact:true})}).getByRole('button',{name:new RegExp('使用于'+target)}).press('Enter'));}
  async function move(room){const data=await action(()=>page.locator('.exit-button').filter({hasText:room}).press('Enter'));await expect(page.locator('#room-title')).toHaveText(room);return data;}
  async function shot(stage){await layout(page,name,width,stage);await page.screenshot({path:path.join(folder,`${name}-${width}-${stage}.png`),fullPage:true});}
  await page.goto(frontendURL,{waitUntil:'networkidle'});
  await page.getByRole('button',{name:'开始新游戏 →',exact:true}).press('Enter');
  await expect(page.locator('#room-title')).toHaveText('值班室');
  await inspect('值班便签');await inspect('值班柜');await code('值班柜','382');await take('门卡');
  await use('门卡','设备间刷卡门');await move('设备间');await take('备用保险丝');await use('保险丝','电源箱');
  await inspect('屏幕');await inspect('抽屉');await code('抽屉','724');const held=await take('应急钥匙');
  assert.equal(held.visible_state.level_version,'2.0.0');assert(held.visible_state.inventory.some(i=>i.item_id==='emergency_key'));
  await expect(page.locator('.inventory')).toContainText('应急钥匙');
  const beforeSave=await control(page,'save');records.push({stage:'before-unlock-save',...beforeSave.data});
  const proposed=await ask(page);records.push({stage:'proposed',...proposed.data});
  assert.deepEqual(proposed.data.proposal.arguments,{item_id:'emergency_key',target_id:'r2_door'});
  assert.equal(proposed.data.visible_state.revision,held.visible_state.revision);
  await expect(page.locator('.inventory')).toContainText('应急钥匙');await shot('proposed-key-held');
  const cancelled=await decide(page,'cancel');records.push({stage:'cancelled',...cancelled.data});
  assert.equal(cancelled.data.visible_state.revision,held.visible_state.revision);
  await expect(page.locator('.inventory')).toContainText('应急钥匙');await expect(page.locator('.proposal-status')).toContainText('cancelled');await shot('cancelled-key-held');
  const fresh=await ask(page);records.push({stage:'fresh-proposed',...fresh.data});
  let duplicate=0;
  await page.route('**/confirm',async route=>{duplicate++;const original=await route.fetch();const first=await original.json();const replay=await route.fetch();const second=await replay.json();assert.equal(second.data.replayed,true);assert.deepEqual(second.data.receipt,first.data.receipt);records.push({stage:'original-confirm',...first.data},{stage:'actual-HTTP-replay-confirm',...second.data});await route.fulfill({response:replay});});
  const committed=await decide(page,'confirm');await page.unroute('**/confirm');
  assert.equal(duplicate,1);assert.deepEqual(committed.data.receipt.consumed_item_ids,['emergency_key']);
  assert.equal(committed.data.visible_state.revision,held.visible_state.revision+1);
  assert(!committed.data.visible_state.inventory.some(i=>i.item_id==='emergency_key'));
  await expect(page.locator('.inventory')).not.toContainText('应急钥匙');
  await expect(page.locator('.committed-receipt')).toContainText('应急钥匙已消耗');
  await expect(page.locator('.committed-receipt')).toContainText('返回原执行记录');
  await shot('committed-replayed-key-consumed');
  await page.locator('.ai-trace summary').press('Enter');const trace=await page.locator('.ai-trace').innerText();
  assert(!/(authorization|api_key|x-session-token|"token"|opened_containers|game_fields)/i.test(trace));
  fs.writeFileSync(path.join(folder,`${name}-${width}-UI-trace.txt`),trace);
  const afterSave=await control(page,'save');records.push({stage:'after-unlock-save',...afterSave.data});
  await move('出口控制室');await move('设备间');
  const observed=await inspect('抽屉');assert(observed.receipt.observation.includes('应急钥匙已使用'));
  await expect(page.locator('.object-grid')).not.toContainText('应急钥匙');
  const bag=await response(page,'/actions',()=>page.getByRole('button',{name:'查看背包',exact:true}).press('Enter'));records.push({stage:'consumed-bag',...bag.data});
  assert(!bag.data.visible_state.inventory.some(i=>i.item_id==='emergency_key'));
  const restored=await control(page,'restore');records.push({stage:'after-unlock-restored',...restored.data});
  assert.equal(restored.data.visible_state.save.level_version,'2.0.0');assert.notEqual(restored.data.visible_state.generation,afterSave.data.visible_state.generation);
  assert(restored.data.visible_state.exits.find(e=>e.destination_id==='R3').unlocked);
  await expect(page.locator('.inventory')).not.toContainText('应急钥匙');await expect(page.locator('.proposal-card')).toHaveCount(0);await shot('restored-key-consumed');
  await move('出口控制室');await inspect('出口检查单');await inspect('检查面板');await code('检查面板','231');const won=await move('实验室出口');
  assert.equal(won.visible_state.status,'won');assert.deepEqual(won.visible_state.inventory.map(i=>i.item_id),['access_card']);
  await expect(page.getByRole('heading',{name:'成功逃离实验室',exact:true})).toBeVisible();await shot('won-no-key');
  fs.writeFileSync(path.join(folder,`${name}-${width}-states.json`),JSON.stringify(records,null,2));
  assert.equal(pageErrors.length,0);checks.push({browser:name,width,stage:'route',passed:true,proposal_id:fresh.data.proposal.proposal_id,original_receipt:committed.data.receipt,restored_generation:restored.data.visible_state.generation,final_state:won.visible_state,duplicate_confirm_mode:'intercept: actual upstream first POST then identical replay POST; UI displays replay response'});
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
  assert.equal(path.dirname(resolved).toLowerCase(),tempRoot.toLowerCase());assert(path.basename(resolved).startsWith('campus-qa-CH01-browser-'));assert.equal(path.resolve(temp).toLowerCase(),resolved.toLowerCase());
  fs.rmSync(resolved,{recursive:true});
  const after=hashes();if(JSON.stringify(before)!==JSON.stringify(after))issues.push({stage:'source-freeze',error:'Candidate source changed during run'});
  fs.writeFileSync(path.join(folder,'checks.json'),JSON.stringify({checks,issues},null,2));
  fs.writeFileSync(path.join(folder,'server-startup-only.json'),JSON.stringify(logs,null,2));
  const evidenceHashes=Object.fromEntries(fs.readdirSync(folder).map(name=>[name,crypto.createHash('sha256').update(fs.readFileSync(path.join(folder,name))).digest('hex')]));
  const result={candidate,command:[process.execPath,...process.argv.slice(1)],provider:'deterministic mock only, no paid network provider',started,ended:new Date().toISOString(),browsers,widths:[1280,1920],source_sha256_before:before,source_sha256_after:after,evidence_sha256:evidenceHashes,
    exit_code:issues.length?1:0,
    privacy:'No creation response, headers, token/sessionStorage, HAR, raw provider data or private DB exported. UI trace saved as public visible text.'};
  fs.writeFileSync(path.join(folder,'run.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify({evidence:folder,routes:checks.filter(c=>c.stage==='route'),issues,exit_code:result.exit_code},null,2));process.exitCode=result.exit_code;
}
