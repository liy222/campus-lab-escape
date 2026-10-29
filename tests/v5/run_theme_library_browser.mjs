// QA entry for the first local campus theme-library batch.
// Do not run until Main freezes all four manifests and artwork and gives GO.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import zlib from 'node:zlib';
import net from 'node:net';
import http from 'node:http';
import {spawn,execFileSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {randomUUID} from 'node:crypto';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const started=new Date().toISOString(),runId=randomUUID();
const stage='evidence/project/stages/v5-campus-theme-library/automated';
const out=path.join(root,stage,`qa-${started.replace(/[:.]/g,'-')}-${runId.slice(0,8)}`);
await fs.mkdir(out,{recursive:false});
const base='http://127.0.0.1:8001';
const packs=[
 {dir:'library-archive',theme:'图书馆旧档案室，借阅记录和校史资料',display:'图书馆档案'},
 {dir:'chemistry-lab',theme:'化学实验室，准备室里的安全实验记录',display:'化学实验室'},
 {dir:'computer-room',theme:'计算机机房，信息技术课的设备维护记录',display:'计算机机房'},
 {dir:'campus-broadcast',theme:'校园广播室，广播站的节目资料',display:'校园广播室'},
];
const resumeArg=process.argv.indexOf('--resume-from');
const resumeFrom=resumeArg>=0?process.argv[resumeArg+1]:null;
if(process.argv.length>2&&(!resumeFrom||process.argv.length!==4||resumeArg!==2||!packs.some(item=>item.dir===resumeFrom)))throw Error('Expected optional --resume-from <package-dir>');
const resumePackDirs=resumeFrom?packs.slice(packs.findIndex(item=>item.dir===resumeFrom)).map(item=>item.dir):[];
const records=[],screenshots=[],issues=[];let page,context,browser,server,serverStopped=true,external=0,state=null;
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function check(name,actual,expected,pass,scope='static') { records.push({name,actual,expected,pass:!!pass,scope,observed_at_utc:new Date().toISOString()}); }
async function writeProgress(){await fs.writeFile(path.join(out,'records.jsonl'),records.map(x=>JSON.stringify(x)).join('\n')+'\n');}
async function shot(name){await page.screenshot({path:path.join(out,`${name}.png`),fullPage:true});screenshots.push(`${name}.png`);}
function failIfNeeded(name,actual,expected,pass,scope){check(name,actual,expected,pass,scope);if(!pass)throw Error(name);}
function paeth(a,b,c){const p=a+b-c,pa=Math.abs(p-a),pb=Math.abs(p-b),pc=Math.abs(p-c);return pa<=pb&&pa<=pc?a:pb<=pc?b:c;}
async function pngInfo(file){
 const bytes=await fs.readFile(file);if(bytes.length<33||!bytes.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])))throw Error('PNG signature invalid');
 let pos=8,width,height,depth,color,interlace,palette=null,transparency=null;const idats=[];
 while(pos+12<=bytes.length){const len=bytes.readUInt32BE(pos),type=bytes.toString('ascii',pos+4,pos+8),data=bytes.subarray(pos+8,pos+8+len);pos+=len+12;
  if(type==='IHDR'){width=data.readUInt32BE(0);height=data.readUInt32BE(4);depth=data[8];color=data[9];interlace=data[12];}
  else if(type==='PLTE')palette=data;else if(type==='tRNS')transparency=data;else if(type==='IDAT')idats.push(data);else if(type==='IEND')break;
 }
 if(depth!==8||interlace!==0||![0,2,3,4,6].includes(color))throw Error(`Unsupported PNG encoding ${depth}/${color}/${interlace}`);
 const channels=({0:1,2:3,3:1,4:2,6:4})[color],bpp=channels,rowSize=width*channels,raw=zlib.inflateSync(Buffer.concat(idats));
 let previous=Buffer.alloc(rowSize),transparent=0,opaque=0,minX=width,minY=height,maxX=-1,maxY=-1,offset=0;
 for(let y=0;y<height;y++){
  const filter=raw[offset++],row=Buffer.from(raw.subarray(offset,offset+rowSize));offset+=rowSize;
  for(let i=0;i<rowSize;i++){const left=i>=bpp?row[i-bpp]:0,up=previous[i],ul=i>=bpp?previous[i-bpp]:0;
   if(filter===1)row[i]=(row[i]+left)&255;else if(filter===2)row[i]=(row[i]+up)&255;else if(filter===3)row[i]=(row[i]+Math.floor((left+up)/2))&255;else if(filter===4)row[i]=(row[i]+paeth(left,up,ul))&255;else if(filter!==0)throw Error(`Unknown PNG filter ${filter}`);
  }
  for(let x=0;x<width;x++){let alpha=255;if(color===6)alpha=row[x*4+3];else if(color===4)alpha=row[x*2+1];else if(color===3)alpha=transparency?.[row[x]]??255;
   if(alpha===0)transparent++;else{opaque++;if(x<minX)minX=x;if(x>maxX)maxX=x;if(y<minY)minY=y;if(y>maxY)maxY=y;}
  }
  previous=row;
 }
 return {width,height,bit_depth:depth,color_type:color,alpha_pixels:{transparent,nontransparent:opaque},alpha_bbox:maxX<0?null:{x:minX,y:minY,width:maxX-minX+1,height:maxY-minY+1}};
}
function within(box,width,height){return box&&Number.isInteger(box.x)&&Number.isInteger(box.y)&&Number.isInteger(box.width)&&Number.isInteger(box.height)&&box.x>=0&&box.y>=0&&box.width>0&&box.height>0&&box.x+box.width<=width&&box.y+box.height<=height;}
function overlap(a,b){return a&&b&&a.x<b.x+b.width&&b.x<a.x+a.width&&a.y<b.y+b.height&&b.y<a.y+a.height;}
async function staticAudit(){
 const rainy=JSON.parse(await fs.readFile(path.join(root,'frontend/src/assets/themes/rainy-astronomy/manifest.json'),'utf8'));
 const pngCache=new Map();const staticFiles=[];
 for(const spec of packs){
  const file=path.join(root,'frontend/src/assets/themes',spec.dir,'manifest.json');const pack=JSON.parse(await fs.readFile(file,'utf8'));
  check(`${spec.dir} manifest schema/identity`,{schema:pack.schema_version,theme_id:pack.theme_id,version:pack.pack_version},{schema:1,theme_id:spec.dir,version_major:1},pack.schema_version===1&&pack.theme_id===spec.dir&&String(pack.pack_version).split('.')[0]==='1');
  check(`${spec.dir} three semantic backgrounds`,Object.keys(pack.backgrounds).sort(),['neutral_archive','neutral_control','neutral_lab'],JSON.stringify(Object.keys(pack.backgrounds).sort())===JSON.stringify(['neutral_archive','neutral_control','neutral_lab']));
  const roles=Object.keys(pack.objects).sort();check(`${spec.dir} six object roles`,roles,['cabinet','circuit','key','note','panel','terminal'],JSON.stringify(roles)===JSON.stringify(['cabinet','circuit','key','note','panel','terminal']));
  for(const role of ['key','cabinet','circuit','panel'])check(`${spec.dir} shared ${role} metadata`,pack.objects[role],rainy.objects[role],JSON.stringify(pack.objects[role])===JSON.stringify(rainy.objects[role]));
  const expectedNotes=[`${spec.dir}-note-logbook`,`${spec.dir}-note-sealed`],expectedTerminals=[`${spec.dir}-terminal-off`,`${spec.dir}-terminal-on`];
  check(`${spec.dir} two note styles`,Object.keys(pack.objects.note).sort(),expectedNotes.slice().sort(),JSON.stringify(Object.keys(pack.objects.note).sort())===JSON.stringify(expectedNotes.slice().sort())&&pack.objects.note[expectedNotes[0]].state==='default'&&pack.objects.note[expectedNotes[0]].note_style==='logbook'&&pack.objects.note[expectedNotes[1]].state==='default'&&pack.objects.note[expectedNotes[1]].note_style==='sealed-note');
  check(`${spec.dir} terminal off/on states`,Object.keys(pack.objects.terminal).sort(),expectedTerminals.slice().sort(),JSON.stringify(Object.keys(pack.objects.terminal).sort())===JSON.stringify(expectedTerminals.slice().sort())&&pack.objects.terminal[expectedTerminals[0]].state==='default'&&pack.objects.terminal[expectedTerminals[1]].state==='completed');
  const originals=new Set();
  for(const [id,item] of Object.entries(pack.backgrounds)){
   const local=path.join(root,'frontend/public',item.src.replace(/^\//,''));originals.add(item.src);
   const info=pngCache.get(local)??await pngInfo(local);pngCache.set(local,info);
   const bbox=item.bbox;const ok=info.width===item.width&&info.height===item.height&&within(bbox,info.width,info.height)&&overlap(info.alpha_bbox,bbox);
   check(`${spec.dir} background ${id} pixel/alpha/bbox`,{src:item.src,...info,bbox},{dimensions:[item.width,item.height],valid_alpha_bbox:true,declared_bbox_inside:true},ok);staticFiles.push({pack:spec.dir,role:'background',variant:id,path:item.src,...info,declared_bbox:bbox});
  }
  for(const role of ['note','terminal'])for(const [id,item] of Object.entries(pack.objects[role])){
   const local=path.join(root,'frontend/public',item.src.replace(/^\//,''));originals.add(item.src);
   const info=pngCache.get(local)??await pngInfo(local);pngCache.set(local,info);
   const closePath=item.closeup||item.src,closeLocal=path.join(root,'frontend/public',closePath.replace(/^\//,''));const close=pngCache.get(closeLocal)??await pngInfo(closeLocal);pngCache.set(closeLocal,close);
   const bboxOk=within(item.bbox,info.width,info.height)&&overlap(info.alpha_bbox,item.bbox);const closeBboxOk=within(item.closeup_bbox,close.width,close.height)&&overlap(close.alpha_bbox,item.closeup_bbox);
   const valid=info.width===item.width&&info.height===item.height&&close.width===item.closeup_width&&close.height===item.closeup_height&&bboxOk&&closeBboxOk&&info.alpha_pixels.transparent>0&&info.alpha_pixels.nontransparent>0;
   check(`${spec.dir} ${role}/${id} pixels alpha and bbox`,{src:item.src,...info,closeup:closePath,close_dimensions:[close.width,close.height],close_alpha_bbox:close.alpha_bbox,bbox:item.bbox,closeup_bbox:item.closeup_bbox},{manifest_dimensions:true,nonempty_alpha:true,valid_bboxes:true},valid);staticFiles.push({pack:spec.dir,role,variant:id,path:item.src,...info,declared_bbox:item.bbox,closeup:closePath,close_alpha_bbox:close.alpha_bbox,closeup_bbox:item.closeup_bbox});
  }
  check(`${spec.dir} seven new source images`,[...originals],7,originals.size===7);
 }
 await fs.writeFile(path.join(out,'static-image-observations.json'),JSON.stringify({generated_at:new Date().toISOString(),packs:staticFiles},null,2)+'\n',{flag:'wx'});
}
async function stable(){await page.waitForFunction(()=>document.querySelector('.v5-game')?.getAttribute('aria-busy')!=='true');await pause(90);}
async function syncState(){await page.waitForFunction(()=>!!window.__themeQaState, null,{timeout:12000});state=await page.evaluate(()=>window.__themeQaState);}
async function waitScene(packId,roomKey){await page.waitForFunction(()=>{const s=document.querySelector('.v5-scene');return s?.dataset.loadingTextures==='false';},null,{timeout:15000});await stable();const info=await page.locator('.v5-scene').evaluate(s=>({theme:s.dataset.theme,background:s.dataset.background,missing:Number(s.dataset.missingTextures),loading:s.dataset.loadingTextures,aliases:(s.dataset.textures||'').split(/\s+/).filter(Boolean),variants:[...s.querySelectorAll('.v5-hotspots button[data-variant]')].map(b=>b.dataset.variant).filter(v=>v&&v!=='generic')}));const pack=JSON.parse(await fs.readFile(path.join(root,'frontend/src/assets/themes',packId,'manifest.json'),'utf8'));const expectedAliases=info.variants.map(id=>`theme:${id}`),loaded=expectedAliases.filter(key=>info.aliases.includes(key));check(`${packId} actual room ${roomKey} assets`,{...info,current_theme_aliases:loaded.length}, {theme:pack.theme_id,background:pack.backgrounds[roomKey].src,missing:0,loading:'false',all_current_aliases_loaded:true},info.theme===pack.theme_id&&info.background===pack.backgrounds[roomKey].src&&info.missing===0&&info.loading==='false'&&expectedAliases.length>0&&loaded.length===expectedAliases.length,'browser');return info;}
async function screenshotFor(tag,sceneOnly=false){const target=sceneOnly?page.locator('.v5-stage'):page;await target.screenshot({path:path.join(out,`${tag}.png`),...(sceneOnly?{}:{fullPage:true})});screenshots.push(`${tag}.png`);}
async function post(click){const wait=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname.endsWith('/actions'));await click();const response=await wait,body=await response.json();if(body.data?.visible_state)state=body.data.visible_state;await stable();if(!response.ok())throw Error(`synthetic action http ${response.status()}`);return body;}
async function openObject(id){const close=page.getByRole('button',{name:'关闭面板',exact:true});if(await close.isVisible())await close.click();await post(()=>page.locator(`.v5-hotspots button[data-object="${id}"]`).click());await page.locator('.v5-sheet').waitFor();}
async function inspectImage(pack,object,tag){await openObject(object.object_id);const id=await page.locator(`.v5-hotspots button[data-object="${object.object_id}"]`).getAttribute('data-variant');const image=page.locator('.v5-closeup img');await image.waitFor();await page.waitForFunction(el=>el.complete&&el.naturalWidth>0,await image.elementHandle());const src=await image.evaluate(el=>new URL(el.src).pathname);const item=pack.objects[object.art_id]?.[id];check(`${pack.theme_id} actual ${object.art_id} closeup`,{id,src,naturalWidth:await image.evaluate(el=>el.naturalWidth)},{expected_src:item?.closeup,width_gt_zero:true},!!item&&src===item.closeup&&(await image.evaluate(el=>el.naturalWidth))>0,'browser');await screenshotFor(`${tag}-${object.art_id}-closeup`);await page.getByRole('button',{name:'关闭面板',exact:true}).click();return id;}
let witnessCache=null;
async function apiWitness(){if(!witnessCache){const code="import json; from backend.app.domain.generated import make_fixture,compile_level; print(json.dumps(compile_level(make_fixture(3,'hard'),3,'hard').witness))";witnessCache=JSON.parse(execFileSync('C:/Users/liyh/.conda/envs/1/python.exe',['-B','-X','utf8','-c',code],{cwd:root,encoding:'utf8',windowsHide:true,timeout:30000}));}return witnessCache;}
async function dispatch(step){const {tool,arguments:a}=step;if(tool==='inspect'){if(!(state.observed_object_ids||[]).includes(a.object_id))await openObject(a.object_id);return;}
 if(tool==='move'){const index=state.exits.findIndex(x=>x.destination_id===a.destination_id);if(index<0||!state.exits[index].unlocked)throw Error('witness move is not publicly unlocked');const nav=page.locator('.v5-exits button').nth(index);await page.getByRole('button',{name:'关闭面板',exact:true}).click().catch(()=>{});await post(()=>nav.click());return;}
 const object=tool==='take'?state.objects.find(o=>o.actions.some(x=>x.tool==='take'&&x.arguments.item_id===a.item_id)):state.objects.find(o=>(o.target_id||o.object_id)===(a.target_id||a.object_id));if(!object)throw Error(`synthetic object missing for ${tool}`);await openObject(object.object_id);
 if(tool==='take'){const act=object.actions.find(x=>x.tool==='take');await post(()=>page.getByRole('button',{name:act.label,exact:true}).click());}
 else if(tool==='use_item'){const item=state.inventory.find(x=>x.item_id===a.item_id);await post(()=>page.getByRole('button',{name:`使用 ${item.name}`,exact:true}).click());}
 else if(tool==='submit_code'){await page.locator('.v5-code input').fill(a.code);await post(()=>page.getByRole('button',{name:'提交密码',exact:true}).click());}
 else if(tool==='submit_login'){await page.locator('.v5-login input').nth(0).fill(a.username);await page.locator('.v5-login input').nth(1).fill(a.password);await post(()=>page.getByRole('button',{name:'提交终端登录',exact:true}).click());}
 else if(tool==='rotate_circuit'){const board=(state.minigames.circuits||[state.minigames.circuit]).find(x=>x.target_id===a.target_id),i=board.modules.findIndex(x=>x.module_id===a.module_id);await post(()=>page.locator('.v5-circuit-module').nth(i).click());}
 else if(tool==='submit_circuit'){await post(()=>page.getByRole('button',{name:'检查线路',exact:true}).click());}
 else if(tool==='submit_sequence'){const board=(state.minigames.sequences||[state.minigames.sequence]).find(x=>x.target_id===a.target_id);await page.getByRole('button',{name:'清除草稿',exact:true}).click();for(const id of a.device_ids){const device=board.devices.find(x=>x.device_id===id);await page.getByRole('button',{name:`${device.symbol} ${device.label}`,exact:true}).click();}await post(()=>page.getByRole('button',{name:'提交顺序',exact:true}).click());}
 else if(tool==='interact'||tool==='get_inventory'){const act=object.actions.find(x=>x.tool===tool);if(!act)throw Error(`affordance missing for ${tool}`);await post(()=>page.getByRole('button',{name:act.label,exact:true}).click());}
 else throw Error(`unsupported synthetic action ${tool}`);
}
async function chooseRoomTheme(text,expectedName){const input=page.getByLabel(/校园主题/);await input.fill(text);await pause(80);const selected=page.locator('.v5-coverage.is-on'),selectedCount=await selected.count();if(expectedName){const actual=selectedCount===1?await selected.innerText():'';const displayName=actual.match(/「([^」]+)」/)?.[1]??null;check(`theme coverage ${text}`,{selected_count:selectedCount,display_name:displayName},expectedName,selectedCount===1&&displayName===expectedName,'browser');}else{const dynamic=page.locator('.v5-coverage:not(.is-on)').last(),actual=await dynamic.innerText();check(`theme coverage ${text}`,{selected_count:selectedCount,dynamic_message:actual},'generic fallback',selectedCount===0&&actual.includes('这个主题还没有专属素材'),'browser');}}
async function packDisplayName(dir){return JSON.parse(await fs.readFile(path.join(root,'frontend/src/assets/themes',dir,'manifest.json'),'utf8')).display_name;}
async function explorePack(spec,index){
 const themeInput=page.getByLabel(/校园主题/);await themeInput.fill(spec.theme);await page.getByLabel(/^房间数量/).selectOption('3');await page.getByLabel(/^难度/).selectOption('hard');await page.getByLabel(/本次生成的 DeepSeek API Key/).fill('SYNTHETIC-ONLY-NOT-A-REAL-KEY');const submitted=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname.endsWith('/level-generations'));await page.getByRole('button',{name:/^生成关卡/}).click();const jobResponse=await submitted,jobBody=await jobResponse.json(),job=jobBody.data?.job;if(!job?.job_id)throw Error('Synthetic generation job was not accepted');check(`${spec.dir} synthetic job accepted`,{status:job.status},'accepted',true,'browser');let actualJob=null;for(let i=0;i<80;i++){actualJob=await page.evaluate(async id=>{const response=await fetch(`/api/v2/level-generations/${encodeURIComponent(id)}`);if(!response.ok)return {http_status:response.status};const body=await response.json();const job=body.data?.job;return job?{job_id:job.job_id,status:job.status,error_code:job.error_code??null}:null;},job.job_id);if(actualJob?.status==='ready'||actualJob?.status==='failed'||actualJob?.status==='unknown')break;await pause(250);}check(`${spec.dir} synthetic job service status`,actualJob,{job_id:job.job_id,status:'ready',error_code:null},actualJob?.status==='ready'&&actualJob?.job_id===job.job_id);if(actualJob?.status!=='ready')throw Error(`Synthetic job not ready (${actualJob?.status||'unavailable'}${actualJob?.error_code?`, ${actualJob.error_code}`:''})`);const listResponse=page.waitForResponse(r=>r.request().method()==='GET'&&new URL(r.url()).pathname.endsWith('/levels'));await page.getByRole('button',{name:'刷新列表',exact:true}).click();await listResponse;
 const card=page.locator('.v5-level-card').filter({hasText:spec.theme.slice(0,9)}).first();await card.waitFor({timeout:25000});await card.getByRole('button',{name:/探索/}).click();await page.locator('.v5-hotspots button:enabled').first().waitFor();await syncState();
 const pack=JSON.parse(await fs.readFile(path.join(root,'frontend/src/assets/themes',spec.dir,'manifest.json'),'utf8'));
 let roomIndex=0;const witness=await apiWitness();let completedTerminal=false,representativeNote=false,terminalDefault=false;const noteStyles=[];
 await waitScene(spec.dir,'neutral_lab');await screenshotFor(`${spec.dir}-R1`,true);
 for(const target of [{object_id:'obj_source',style:'logbook'},{object_id:'obj_order',style:'sealed-note'}]){const note=state.objects.find(o=>o.object_id===target.object_id&&o.art_id==='note');if(!note){check(`${spec.dir} ${target.style} synthetic note exists`,null,target.object_id,false,'browser');continue;}const variantId=await inspectImage(pack,note,`${spec.dir}-R${roomIndex+1}`),style=pack.objects.note[variantId]?.note_style;check(`${spec.dir} visible ${target.style} note variant`,{object_id:note.object_id,variant_id:variantId,note_style:style},target.style,style===target.style,'browser');noteStyles.push(style);representativeNote=noteStyles.length===2;}
 const initialTerminal=state.objects.find(o=>o.art_id==='terminal'&&!o.completed);if(initialTerminal){const id=await inspectImage(pack,initialTerminal,`${spec.dir}-R1`);const expected=Object.keys(pack.objects.terminal).find(key=>pack.objects.terminal[key].state==='default');check(`${spec.dir} terminal default state`,id,expected,id===expected,'browser');terminalDefault=id===expected;}
 for(const step of witness){
  if(step.tool==='move'){
   const gate=state.objects.find(o=>o.art_id==='terminal'&&o.completed);if(gate){const id=await page.locator(`.v5-hotspots button[data-object="${gate.object_id}"]`).getAttribute('data-variant');check(`${spec.dir} terminal completed state`,id,Object.keys(pack.objects.terminal).find(k=>pack.objects.terminal[k].state==='completed'),id===Object.keys(pack.objects.terminal).find(k=>pack.objects.terminal[k].state==='completed'),'browser');completedTerminal=true;}
   if(roomIndex>=2)break;
   const idx=state.exits.findIndex(x=>x.destination_id===step.arguments.destination_id);if(idx<0||!state.exits[idx].unlocked)throw Error('witness destination not publicly unlocked');await page.getByRole('button',{name:'关闭面板',exact:true}).click().catch(()=>{});await post(()=>page.locator('.v5-exits button').nth(idx).click());roomIndex++;await syncState();const roomKey=['neutral_lab','neutral_archive','neutral_control'][roomIndex];await waitScene(spec.dir,roomKey);await screenshotFor(`${spec.dir}-R${roomIndex+1}`,true);
   const nextNote=state.objects.find(o=>o.art_id==='note');if(nextNote&&!representativeNote){await inspectImage(pack,nextNote,`${spec.dir}-R${roomIndex+1}`);representativeNote=true;}
   if(roomIndex===2)break;
  }else{await dispatch(step);await syncState();await page.waitForFunction(()=>document.querySelector('.v5-scene')?.dataset.loadingTextures==='false',null,{timeout:12000});const terminal=state.objects.find(o=>o.art_id==='terminal'&&!o.completed);if(terminal&&!terminalDefault){const id=await page.locator(`.v5-hotspots button[data-object="${terminal.object_id}"]`).getAttribute('data-variant');const offId=Object.keys(pack.objects.terminal).find(k=>pack.objects.terminal[k].state==='default');if(id===offId){const chosen=await inspectImage(pack,terminal,`${spec.dir}-terminal-off`);check(`${spec.dir} terminal default closeup`,chosen,offId,chosen===offId,'browser');terminalDefault=true;}}const done=state.objects.find(o=>o.art_id==='terminal'&&o.completed);if(done&&!completedTerminal){const id=await page.locator(`.v5-hotspots button[data-object="${done.object_id}"]`).getAttribute('data-variant');const onId=Object.keys(pack.objects.terminal).find(k=>pack.objects.terminal[k].state==='completed');const chosen=await inspectImage(pack,done,`${spec.dir}-terminal-on`);check(`${spec.dir} terminal completed state`,{variant:id,closeup:chosen},{variant:onId,closeup:onId},id===onId&&chosen===onId,'browser');completedTerminal=id===onId&&chosen===onId;}}
 }
 check(`${spec.dir} reached both note styles and terminal states`,{representativeNote,note_styles:noteStyles,terminalDefault,completedTerminal},{representativeNote:true,note_styles:['logbook','sealed-note'],terminalDefault:true,completedTerminal:true},representativeNote&&noteStyles.includes('logbook')&&noteStyles.includes('sealed-note')&&terminalDefault&&completedTerminal,'browser');
 const sceneBefore=await page.locator('.v5-scene').evaluate(s=>({theme:s.dataset.theme,background:s.dataset.background,variants:[...s.querySelectorAll('.v5-hotspots button')].map(b=>[b.dataset.object,b.dataset.variant])}));
 await page.reload();await page.getByRole('heading',{name:'我的关卡',exact:true}).waitFor();const resumed=page.locator('.v5-level-card').filter({hasText:spec.theme.slice(0,9)}).first();await resumed.getByRole('button',{name:/探索/}).click();await page.locator('.v5-hotspots button:enabled').first().waitFor();await syncState();await page.waitForFunction(()=>document.querySelector('.v5-scene')?.dataset.loadingTextures==='false',null,{timeout:15000});const sceneAfter=await page.locator('.v5-scene').evaluate(s=>({theme:s.dataset.theme,background:s.dataset.background,variants:[...s.querySelectorAll('.v5-hotspots button')].map(b=>[b.dataset.object,b.dataset.variant])}));check(`${spec.dir} reload keeps resolved theme and variants`,sceneAfter,sceneBefore,JSON.stringify(sceneAfter)===JSON.stringify(sceneBefore),'browser');
 await page.getByRole('button',{name:'我的关卡',exact:true}).click();await page.getByRole('heading',{name:'我的关卡',exact:true}).waitFor();
}
async function galleryAudit(){
 await page.goto(`${base}/art-themes/campus-theme-library.html`);
 await page.locator('main').waitFor();
 const actual=await page.locator('img').evaluateAll(async images=>{for(const image of images)image.loading='eager';await Promise.all(images.map(image=>image.decode().catch(()=>null)));return images.map(image=>({src:new URL(image.src).pathname,complete:image.complete,width:image.naturalWidth,height:image.naturalHeight}));});
 check('static theme gallery loads 28 source images',{count:actual.length,loaded:actual.filter(x=>x.complete&&x.width>0&&x.height>0).length},{count:28,all_loaded:true},actual.length===28&&actual.every(x=>x.complete&&x.width>0&&x.height>0),'browser');
 await screenshotFor('theme-library-gallery');
}
async function browserAudit(){
 const port=net.createServer();await new Promise((resolve,reject)=>{port.once('error',reject);port.listen(8002,'127.0.0.1',()=>port.close(resolve));});
 const temp=await fs.mkdtemp(path.join(os.tmpdir(),'campus-visual-theme-library-'));browserTemp=temp;
 const db=path.join(temp,'game-v5.sqlite');server=spawn('C:/Users/liyh/.conda/envs/1/python.exe',['-B','-X','utf8','-m','uvicorn','tests.v5.theme_library_fixture_server:app','--host','127.0.0.1','--port','8002','--no-access-log'],{cwd:root,env:{...process.env,SQLITE_PATH:db,GAMEPLAY_VERSION:'v5',AI_PROVIDER:'mock',PYTHONDONTWRITEBYTECODE:'1'},stdio:'ignore',windowsHide:true});
 let ready=false;for(let i=0;i<100&&!ready;i++){ready=await new Promise(resolve=>{const r=http.get({hostname:'127.0.0.1',port:8002,path:'/health',headers:{host:'127.0.0.1:8001'}},res=>{res.resume();resolve(res.statusCode===200);});r.on('error',()=>resolve(false));r.setTimeout(700,()=>r.destroy());});if(!ready)await pause(100);}if(!ready)throw Error('Owned fixture service did not become ready');
 const {chromium}=createRequire(path.join(root,'frontend/package.json'))('@playwright/test');browser=await chromium.launch({headless:true,channel:'chrome'});context=await browser.newContext({viewport:{width:1280,height:720}});
 await context.route('**/*',async route=>{const req=route.request(),url=new URL(req.url());if(['data:','blob:'].includes(url.protocol))return route.continue();if(url.origin!==base){external++;return route.abort();}return route.fetch({url:req.url().replace(base,'http://127.0.0.1:8002'),headers:{...req.headers(),host:'127.0.0.1:8001'}}).then(response=>route.fulfill({response}));});
 page=await context.newPage();page.setDefaultTimeout(12000);page.on('response',async response=>{if(new URL(response.url()).pathname.includes('/sessions/'))try{const value=await response.json();if(value.data?.visible_state){state=value.data.visible_state;await page.evaluate(s=>{window.__themeQaState=s;},state).catch(()=>{});}}catch{}});
 await page.goto(base);await page.getByRole('button',{name:'第一次来？注册本地账户',exact:true}).click();await page.getByLabel('用户名（3–24位字母、数字或下划线）',{exact:true}).fill(`themeqa_${runId.slice(0,8)}`);await page.getByLabel('密码（12–128位）',{exact:true}).fill('Synthetic-Theme-library-only!');await page.getByRole('button',{name:'注册并进入',exact:true}).click();await page.getByRole('heading',{name:'我的关卡',exact:true}).waitFor();
 if(!resumeFrom){for(const spec of packs)await chooseRoomTheme(spec.theme,await packDisplayName(spec.dir));await chooseRoomTheme('计算机机房与图书馆档案',await packDisplayName('computer-room'));await chooseRoomTheme('图书馆档案，随后进入广播室',await packDisplayName('library-archive'));await chooseRoomTheme('深海生物观察','');}
 const firstIndex=resumeFrom?packs.findIndex(item=>item.dir===resumeFrom):0;
 for(let i=firstIndex;i<packs.length;i++)await explorePack(packs[i],i);
 if(resumeFrom)await galleryAudit();
 check('no external network requests',external,0,external===0,'browser');
 return temp;
}
let browserTemp=null;
try{
 if(!resumeFrom)await staticAudit();await writeProgress();browserTemp=await browserAudit();await writeProgress();
}catch(error){issues.push({type:error?.constructor?.name||'Error',scope:'theme-library QA',message:String(error?.message||'unknown').split('\n')[0].slice(0,140)});try{if(page)await shot('failure');}catch{}await writeProgress().catch(()=>{});}
finally{
 try{await context?.unrouteAll({behavior:'ignoreErrors'});}catch{}try{await context?.close();}catch{}try{await browser?.close();}catch{}
 if(server)serverStopped=await new Promise(resolve=>{if(server.exitCode!==null||server.signalCode!==null)return resolve(true);server.once('close',()=>resolve(true));server.kill();setTimeout(()=>resolve(false),4000);});
 const exit=issues.length||!serverStopped||records.some(x=>!x.pass)?1:0;const result={run_id:runId,command:'node tests/v5/run_theme_library_browser.mjs'+(resumeFrom?` --resume-from ${resumeFrom}`:''),started_at_utc:started,finished_at_utc:new Date().toISOString(),scope:resumeFrom?`Synthetic browser runs for ${resumePackDirs.join(', ')}; static/topic-matching results reused from first run; partial witness only`:'four new theme packs static asset audit, explicit/earliest/mixed/generic theme matching, four isolated three-room Synthetic browser runs, representative note and terminal states/closeups, reload consistency; partial witness only',static_audit_reused_from:resumeFrom?'automated/qa-2026-10-29T17-33-54-163Z-e6732213/static-image-observations.json':null,browser_TEMP:browserTemp?path.basename(browserTemp):null,server_port:8002,server_stopped:serverStopped,external_requests:external,real_provider_calls:0,paid_calls:0,player_database_access:false,records,screenshots,issues,exit_code:exit,limitations:['Synthetic public fixture only; no real model outputs or human acceptance','Does not complete full three-room games or cover saves/classic/mobile','Original and shared artwork must be distinguished in static result']};await fs.writeFile(path.join(out,'result.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});process.exitCode=exit;
}
