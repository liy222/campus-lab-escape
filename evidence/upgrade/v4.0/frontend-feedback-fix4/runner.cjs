const fs=require('fs'),path=require('path'),os=require('os'),net=require('net'),{spawn,spawnSync}=require('child_process');
const root=process.cwd();const {chromium,expect}=require(path.join(root,'frontend/node_modules/@playwright/test'));const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'v40-owner-'));const out=path.join(root,'evidence/upgrade/v4.0/frontend-feedback-fix4');fs.mkdirSync(out,{recursive:true});
const env=Object.fromEntries(Object.entries(process.env).filter(([k])=>!/(TOKEN|SECRET|PASSWORD|CREDENTIAL|API.?KEY)/i.test(k)&&!/^(AI_|VITE_|MODEL_|DEEPSEEK_|OPENAI_)/i.test(k)));const kids=[],checks=[],errors=[];let browser,state,page;
const port=()=>new Promise(r=>{const s=net.createServer();s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(()=>r(p));});});const ready=async u=>{for(let i=0;i<160;i++){try{if((await fetch(u)).ok)return;}catch{}await new Promise(r=>setTimeout(r,150));}throw Error('startup timeout');};
const launch=(cmd,args,extra,cwd=root)=>{const k=spawn(cmd,args,{cwd,env:{...env,...extra},windowsHide:true,stdio:'ignore'});kids.push(k);};
(async()=>{try{const bp=await port(),fp=await port();launch('C:/Users/liyh/.conda/envs/1/python.exe',['-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',String(bp),'--no-access-log'],{GAMEPLAY_VERSION:'v3.4',AI_PROVIDER:'mock',SQLITE_PATH:path.join(tmp,'game.sqlite'),PYTHONUTF8:'1'});launch(process.execPath,[path.join(root,'frontend/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port',String(fp),'--strictPort'],{CAMPUS_BACKEND_URL:`http://127.0.0.1:${bp}`,VITE_GAMEPLAY_VERSION:'v3.4'},path.join(root,'frontend'));await Promise.all([ready(`http://127.0.0.1:${bp}/api/health`),ready(`http://127.0.0.1:${fp}`)]);
browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});page=await browser.newPage({viewport:{width:1365,height:900}});page.on('pageerror',e=>errors.push(e.stack));page.on('response',async r=>{if(new URL(r.url()).pathname.startsWith('/api/')){try{const b=await r.json();state=b.data?.visible_state||b.visible_state||state;}catch{}}});await page.goto(`http://127.0.0.1:${fp}`);await page.getByRole('button',{name:'开始新游戏 →',exact:true}).click();await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-assets-ready','true');checks.push('actual Canvas assets loaded '+await page.locator('.game-canvas-host').getAttribute('data-renderer'));
const stable=async()=>await expect(page.locator('.feedback .pending')).toHaveCount(0);const point=async id=>{const h=await page.locator('.game-canvas-host').boundingBox();const b=(await page.locator(`.scene-keyboard-hotspot[data-object-id="${id}"]`).getAttribute('data-bounds')).split(',').map(Number);await page.mouse.click(h.x+(b[0]+b[2]/2)/1600*h.width,h.y+(b[1]+b[3]/2)/900*h.height);await stable();};const back=async()=>{if(await page.getByRole('button',{name:'← 返回房间'}).count())await page.getByRole('button',{name:'← 返回房间'}).click();};

const intersects=(a,b)=>a&&b&&a.x<b.x+b.width&&a.x+a.width>b.x&&a.y<b.y+b.height&&a.y+a.height>b.y;
const unobscured=async selectors=>{const feedback=await page.locator('.feedback').boundingBox();for(const selector of selectors){const element=page.locator(selector);await expect(element).toBeVisible();const box=await element.boundingBox();if(intersects(feedback,box))throw Error('feedback overlaps '+selector);}};
for(const [width,height] of [[1920,1080],[1280,800],[375,812]]){
 await page.setViewportSize({width,height}); await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))); await expect.poll(async()=>{const host=await page.locator('.game-canvas-host').boundingBox();const canvas=await page.locator('.game-canvas-host canvas').boundingBox();return Math.abs(host.width-canvas.width);}).toBeLessThan(1);
 for(const id of ['r1_clock','r1_record','r1_plaque']){
  await point(id);await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view',id);
  await unobscured(['.game-hud','.closeup-reading','.closeup-back']);
  const text=await page.locator('.closeup-reading p').innerText();if(!text.trim())throw Error('missing original clue text');
  if(id==='r1_clock')await page.screenshot({path:path.join(out,`clock-${width}.png`),fullPage:true});
  await back();
 }
 await point('r1_cabinet');await page.locator('#code-r1_cabinet').fill('0000');await page.locator('.mechanical-lock').getByRole('button',{name:'提交',exact:true}).click();await stable();
 await expect(page.locator('.feedback .error')).toBeVisible();
 await unobscured(['.game-hud','.closeup-back','#code-r1_cabinet','.mechanical-lock button']);

 await page.screenshot({path:path.join(out,`error-${width}.png`),fullPage:true});await back();
 checks.push(`${width}px: clock/record/plaque original text, return and cabinet lock input unobscured; error visible`);
}
if(errors.length)process.exitCode=1;
}catch(e){errors.push(String(e.stack)); if(page) { await page.screenshot({path:path.join(out,"failure.png"),fullPage:true}); if(await page.locator(".game-canvas-host").count())errors.push(await page.locator(".game-canvas-host").getAttribute("data-view")); errors.push(await page.locator(".feedback").innerText()); } process.exitCode=1;}finally{if(browser)await browser.close();for(const k of kids.reverse())if(k.exitCode===null)spawnSync('taskkill',['/PID',String(k.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({scope:'owner development smoke; not independent QA/human playtest',checks,errors},null,2));console.log(JSON.stringify({checks,errors,out}));}})();






