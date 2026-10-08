"""Generate the new visual adapter; do not execute browser acceptance here."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[4]
source = root / 'tests/e2e/run_multiple_saves.mjs'
target = root / 'tests/e2e/run_visual_v40.mjs'
original = source.read_bytes()
text = original.decode('utf-8')
newline = '\r\n' if b'\r\n' in original else '\n'
text = text.replace('\r\n', '\n')
text = text.replace('// Independent multiple-save Chrome acceptance; v3.4 route retained, owned mock DBs.', '// Independent v4.0 R1 visual adapter; complete prior route/assertions retained, owned mock DBs.')
text = text.replace('evidence/integration/multiple-saves/qa', 'evidence/upgrade/v4.0/qa')
text = text.replace('campus-multiple-saves-browser-', 'campus-visual-v40-browser-')

def replace_block(start, end, replacement):
    global text
    begin, finish = text.index(start), text.index(end)
    text = text[:begin] + replacement.rstrip() + '\n' + text[finish:]

replace_block('async function select(page, id)', 'async function login(page', r'''
function visual() { return state?.level_version === '3.4.0' && state?.room.room_id === 'R1'; }
async function closeDrawer(page) {
  const backdrop=page.getByRole('button',{name:'关闭面板',exact:true});
  if(await backdrop.isVisible()) await backdrop.click({position:{x:5,y:5}});
}
async function menu(page) {
  if(visual() && !await page.locator('.save-panel').isVisible()) {
    await closeDrawer(page); await page.getByRole('button',{name:'游戏菜单',exact:true}).click();
  }
}
async function partner(page) {
  if(visual() && !await page.locator('#hint-level').isVisible()) {
    await closeDrawer(page); await page.getByRole('button',{name:'AI 探索伙伴',exact:true}).click();
  }
}
async function roomView(page) {
  await closeDrawer(page);
  const cancel=page.locator('.cancel-item');if(await cancel.isVisible()) await cancel.click();
  if(await page.locator('.closeup-back').isVisible()) {
    const before=structuredClone(state);await page.locator('.closeup-back').click();assert.deepEqual(state,before);
  }
  await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view','room');
}
async function canvasInput(page,id,tool='object',keyboard=false,touch=false) {
  const host=page.locator('.game-canvas-host');await expect(host).toHaveAttribute('data-assets-ready','true');
  await expect(host.locator('canvas')).toHaveCount(1);
  const hotspot=host.locator(`.scene-keyboard-hotspot[data-object-id="${id}"][data-scene-action="${tool}"]`);
  await expect(hotspot).toHaveCount(1);await expect(hotspot).toBeEnabled();
  if(keyboard) { await hotspot.focus();await hotspot.press('Enter'); }
  else {
    const values=(await hotspot.getAttribute('data-bounds')).split(',').map(Number), box=await host.locator('canvas').boundingBox();
    assert(box);const x=box.x+(values[0]+values[2]/2)*box.width/1600,y=box.y+(values[1]+values[3]/2)*box.height/900;
    const hit=await page.evaluate(({x,y})=>document.elementFromPoint(x,y)?.tagName,{x,y});assert.equal(hit,'CANVAS','Mouse input must hit actual canvas');
    if(touch) await page.touchscreen.tap(x,y);else await page.mouse.click(x,y);
  }
}
async function select(page,id,keyboard=false) {
  const object=state.objects.find(object=>object.object_id===id);assert(object,'Object must be currently visible: '+id);
  if(visual()) {
    await roomView(page);
    if(['r1_symbols','r1_fuse','r1_photo'].includes(id)) {
      await http(page,'canvas-inspect:r1_cabinet',()=>canvasInput(page,'r1_cabinet'));
      await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view','r1_cabinet');
    }
    let count=0;const listener=request=>{if(new URL(request.url()).pathname.endsWith('/actions')) count++;};page.on('request',listener);
    const body=await http(page,(keyboard?'keyboard':'canvas')+'-inspect:'+id,()=>canvasInput(page,id,'object',keyboard));
    await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view',id);page.off('request',listener);
    assert.equal(count,1);assert.equal(body.data.receipt.tool,'inspect');assert.equal(body.data.receipt.arguments.object_id,id);
    checks.push({check:keyboard?'keyboard-independent-hotspot':'real-canvas-one-inspect-closeup',object_id:id,passed:true});
    if(['r1_record','r1_plaque','r1_microscope','r1_photo'].includes(id)) {
      const stage=id==='r1_microscope'?(state.puzzle_states.microscope+(state.clues.some(clue=>clue.object_id===id)?'-eyepiece':'')):'reading';
      const imagePath=path.join(folder,id+'-'+stage+'.png');if(!fs.existsSync(imagePath)) {await canvasPixels(page,id+'-'+stage);await page.locator('.visual-room').screenshot({path:imagePath});}
    }return body;
  }
  const escaped=object.name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  await page.locator('.object-grid').getByRole('button',{name:new RegExp(escaped)}).click();
}
async function observe(page,id) {
  if(visual()) return select(page,id);
  await select(page,id);return http(page,'inspect:'+id,()=>page.getByRole('button',{name:/^观察$/}).click());
}
async function interact(page,id) {
  await select(page,id);
  if(visual()) {
    const object=state.objects.find(value=>value.object_id===id),action=object.actions.find(value=>value.tool==='interact')||object.actions.find(value=>value.tool==='take')||object.actions.find(value=>value.tool==='inspect');
    assert(action);
    if(action.tool==='take'||id==='r1_cabinet') await page.locator('.game-canvas-host canvas').screenshot({path:path.join(folder,id+'-before-'+action.tool+'.png')});
    const body=await http(page,action.tool+':'+id,()=>page.locator(`.closeup-actions [data-scene-action="${action.tool}"][data-target-id="${id}"]`).click());
    if(action.tool==='take'||id==='r1_cabinet') {
      await expect.poll(async()=> (await markers(page)).includes(action.tool)).toBe(true);
      await page.locator('.game-canvas-host canvas').screenshot({path:path.join(folder,id+'-receipt-frame-'+action.tool+'.png')});
      await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-animation','idle');
      await page.locator('.game-canvas-host canvas').screenshot({path:path.join(folder,id+'-settled-'+action.tool+'.png')});
      checks.push({check:'receipt-animation-frames-for-independent-visual-review',object_id:id,tool:action.tool,passed:true});
    }return body;
  }
  return http(page,'interact:'+id,()=>page.getByRole('button',{name:/^互动$/}).click());
}
async function code(page,id,value,expected=200) {
  await select(page,id);if(!visual()) await page.getByRole('button',{name:/^互动$/}).click();
  await page.getByLabel('输入你推理出的数字',{exact:true}).fill(value);
  return http(page,'code:'+id,()=>page.locator('.code-form').getByRole('button',{name:'提交',exact:true}).click(),expected);
}
''')
replace_block('async function use(page, itemId', 'async function control(page', r'''
async function use(page,itemId,targetId,expected=200) {
  const item=state.inventory.find(item=>item.item_id===itemId);assert(item,'Owned item: '+itemId);
  await select(page,targetId);
  let canvasTool=null;
  if(visual()) {
    const zone=page.locator(`.game-canvas-host .scene-keyboard-hotspot[data-object-id="${targetId}"]`);
    if(await zone.count()===1) canvasTool=await zone.getAttribute('data-scene-action');
    else {await roomView(page);canvasTool='object';}
  }
  const button=page.locator('.inventory-item').filter({hasText:item.name}).locator('.item-select-button');
  if(await button.getAttribute('aria-pressed')!=='true') await button.click();
  const body=await http(page,'use:'+itemId+':'+targetId,()=>canvasTool?canvasInput(page,targetId,canvasTool):page.getByRole('button',{name:/^使用物品/}).click(),expected);
  if(canvasTool) {if(expected===200) assert.equal(body.data.receipt.tool,'use_item');checks.push({check:'actual-canvas-held-item-server-authority',item_id:itemId,target_id:targetId,http_status:expected,passed:true});}
  if(expected!==200) await expect(button).toHaveAttribute('aria-pressed','true');return body;
}
async function move(page,destination,expected=200) {
  const exit=state.exits.find(exit=>exit.destination_id===destination);assert(exit,'Visible passage: '+destination);
  if(visual()) {await select(page,'r1_door');return http(page,'move:'+destination,()=>page.locator('.closeup-actions [data-scene-action="move"]').click(),expected);}
  return http(page,'move:'+destination,()=>page.locator('.exit-button').filter({hasText:exit.name}).click(),expected);
}
''')
text = text.replace("async function control(page, operation) {\n  return", "async function control(page, operation) {\n  await menu(page);\n  return")
text = text.replace("async function appendMoment(page,name) {\n  const", "async function appendMoment(page,name) {\n  await menu(page);\n  const")
text = text.replace("async function retrieveMoment(page,moment,checkCancel=false) {\n  const", "async function retrieveMoment(page,moment,checkCancel=false) {\n  await menu(page);\n  const")
text = text.replace("  await expect(row).toBeVisible();\n  checks.push", "  await menu(page);await expect(row).toBeVisible();\n  checks.push")
text = text.replace("async function hint(page,level,expectAccepted=true) {\n  let", "async function hint(page,level,expectAccepted=true) {\n  await partner(page);\n  let")
text = text.replace("const context = await browser.newContext({ viewport: { width: 1280, height: 900 } }), page = await context.newPage();", "const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } }), page = await context.newPage();", 1)
text = text.replace("  await layout(page, 1280, 'R1-graybox'); await page.screenshot({ path: path.join(folder, 'R1-graybox.png'), fullPage: true });", "  await visualOpening(page); await closeDrawer(page); await layout(page,1920,'R1-visual-desktop'); await page.screenshot({path:path.join(folder,'R1-visual-desktop.png'),fullPage:true});")
text = text.replace("await layout(page, 375, 'R1-mobile'); await page.setViewportSize({ width: 1280, height: 900 });", "await layout(page,375,'R1-mobile');await page.screenshot({path:path.join(folder,'R1-visual-mobile.png'),fullPage:true});await page.setViewportSize({width:1280,height:900});")
text = text.replace("await expect(page.locator('.run-statistics [data-stat=\"hint_count\"]')).toHaveText('3');", "await closeDrawer(page);await menu(page);await expect(page.locator('.menu-statistics [data-stat=\"hint_count\"]')).toHaveText('3');await closeDrawer(page);")
text = text.replace("  await use(page, 'sample_slide', 'r1_microscope');", "  await visualSampleSnapshots(page,service,earlyArchive);\n  await use(page, 'sample_slide', 'r1_microscope');")
text = text.replace("  await observe(page, 'r1_cabinet'); await code(page, 'r1_cabinet', '4217'); await interact(page, 'r1_cabinet');", "  await visualCabinet(page);\n  await observe(page, 'r1_cabinet'); await code(page, 'r1_cabinet', '4217');assert.equal(state.device_states.cabinet,'CODE_ACCEPTED');await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-cabinet-state','CODE_ACCEPTED');await page.locator('.visual-room').screenshot({path:path.join(folder,'R1-code-accepted-still-closed.png')});await interact(page,'r1_cabinet');assert.equal(state.device_states.cabinet,'OPEN');await page.locator('.visual-room').screenshot({path:path.join(folder,'R1-cabinet-open.png')});")
text = text.replace("await expect(page.locator('.save-slot')).toHaveCount(3)", "await expect(page.locator('.save-slot')).toHaveCount(4)")
text = text.replace("await expect(page.locator('.save-slot')).toHaveCount(4)", "await expect(page.locator('.save-slot')).toHaveCount(5)")
# Early + extra sample archive + partial archive + legacy = four before won.
text = text.replace("  await expect(page.locator('.save-slot')).toHaveCount(5);\n  await refresh(page); assert.deepEqual(publicGame(state),publicGame(partial));", "  await expect(page.locator('.save-slot')).toHaveCount(4);\n  await refresh(page); assert.deepEqual(publicGame(state),publicGame(partial));")
text = text.replace("archive_count:3,legacy_count:1", "archive_count:4,legacy_count:1")
text = text.replace("three-immutable-archives-plus-old-slot", "four-immutable-archives-plus-old-slot")
text = text.replace("  await context.close();\n  await lightOldVersion", "  await context.close();\n  await touchSmoke(service);\n  await lightOldVersion", 1)
text = text.replace("assert.equal(state.device_states.cabinet,'CODE_ACCEPTED');await expect", "assert.equal(state.device_states.cabinet,'CODE_ACCEPTED');await expect.poll(async()=> (await markers(page)).includes('submit_code')).toBe(true);await expect")
text = text.replace("async function layout(page, width, label) {", "async function layout(page, width, label) {\n  if(visual()) {await closeDrawer(page);await expect(page.locator('.game-canvas-host canvas')).toHaveCount(1);await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-assets-ready','true');await canvasPixels(page,label);}\n  else {await expect(page.locator('.game-canvas-host canvas')).toHaveCount(0);await expect(page.locator('.object-grid button')).toHaveCount(state.objects.length);}")
insert = r'''
async function touchSmoke(service) {
  const context=await browser.newContext({viewport:{width:375,height:812},hasTouch:true,isMobile:true,deviceScaleFactor:1}),page=await context.newPage();
  const errors=[];page.on('pageerror',()=>errors.push('uncaught touch browser exception'));state=undefined;
  await page.goto(service.frontendURL,{waitUntil:'networkidle'});
  await http(page,'touch-create',()=>page.getByRole('button',{name:'开始新游戏 →',exact:true}).click(),201,'/api/sessions');
  await http(page,'real-touchscreen-canvas-clock-inspect',()=>canvasInput(page,'r1_clock','object',false,true));
  await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view','r1_clock');assert(state.clues.some(clue=>clue.object_id==='r1_clock'));
  await canvasPixels(page,'R1-touch-clock-closeup');await page.screenshot({path:path.join(folder,'R1-touch-clock-closeup.png'),fullPage:true});
  await select(page,'r1_record',true);assert(state.clues.some(clue=>clue.object_id==='r1_record'));
  await layout(page,375,'R1-actual-touch-keyboard');assert.equal(errors.length,0);
  checks.push({check:'hasTouch-mobile-actual-touchscreen-tap-and-keyboard-Enter',passed:true,width:375});await context.close();
}
async function canvasPixels(page,label) {
  const host=page.locator('.game-canvas-host');
  await expect(host).toHaveAttribute('data-assets-ready','true');
  const renderer=await host.getAttribute('data-renderer');assert(['canvas','webgl'].includes(renderer),'Renderer must be explicitly ready');
  const imagePath=path.join(folder,label+'-canvas-pixels.png');await host.locator('canvas').screenshot({path:imagePath});
  const args=['-B','-X','utf8',path.join(root,'evidence/upgrade/v4.0/qa/pixel_check.py'),imagePath];
  const result=spawnSync(python,args,{cwd:root,encoding:'utf8',windowsHide:true});
  commands.push({label:'canvas-pixel-check:'+label,executable:python,arguments:args,cwd:root,exit_code:result.status,stdout:result.stdout.trim(),stderr:result.stderr.trim()});
  assert.equal(result.status,0,'Canvas screenshot is black/uniform or pixel reader failed');
  checks.push({check:'real-rendered-canvas-nonblack-nonuniform',label,renderer,...JSON.parse(result.stdout)});
}
async function markers(page) {return page.evaluate(()=>window.qaVisualMarkers||[]);}
async function trackMarkers(page) {
  await page.evaluate(()=>{
    window.qaVisualMarkers=[];window.qaVisualObserver?.disconnect();
    window.qaVisualObserver=new MutationObserver(records=>{for(const record of records) if(record.attributeName==='data-animation') {
      for(const value of [record.oldValue,record.target.getAttribute('data-animation')]) if(value&&value!=='idle') window.qaVisualMarkers.push(value);
    }});window.qaVisualObserver.observe(document.body,{subtree:true,attributes:true,attributeOldValue:true,attributeFilter:['data-animation']});
  });
}
async function visualOpening(page) {
  await roomView(page);await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-assets-ready','true');
  assert.equal(await page.locator('.game-canvas-host canvas').count(),1);assert.equal(await page.locator('.object-grid').count(),0);
  assert.equal(state.clues.length,0);assert(!state.objects.some(object=>['r1_photo','r1_symbols','r1_fuse'].includes(object.object_id)));
  assert.equal(await page.locator('.scene-keyboard-hotspot[data-object-id="r1_photo"]').count(),0);
  assert(!await page.locator('body').innerText().then(value=>value.includes('4217')));
  await trackMarkers(page);await select(page,'r1_clock',true);await canvasPixels(page,'R1-clock-closeup');await page.locator('.visual-room').screenshot({path:path.join(folder,'R1-clock-closeup.png')});
  await roomView(page);await page.getByRole('button',{name:'线索笔记',exact:true}).click();
  const notebook=page.locator('.notebook-modal');await expect(notebook).toBeVisible();
  assert.equal(await notebook.locator('.clue-list li').count(),1);await expect(notebook).toContainText(state.clues[0].text);
  await notebook.getByRole('button',{name:'合上笔记',exact:true}).click();
  // Synthetic UI input only: never press ask with the real-provider option selected.
  await partner(page);let calls=0;const listener=request=>{if(new URL(request.url()).pathname.endsWith('/ai/turns')) calls++;};page.on('request',listener);
  await page.locator('input[name="ai-provider"][value="deepseek"]').check();await page.locator('#ai-api-key').fill('QA-NOT-A-CREDENTIAL');
  await page.getByRole('button',{name:'关闭伙伴',exact:true}).click();await partner(page);await expect(page.locator('#ai-api-key')).toHaveValue('QA-NOT-A-CREDENTIAL');
  await page.locator('input[name="ai-provider"][value="mock"]').check();await page.locator('input[name="ai-provider"][value="deepseek"]').check();await expect(page.locator('#ai-api-key')).toHaveValue('');
  await page.locator('input[name="ai-provider"][value="mock"]').check();assert.equal(calls,0);page.off('request',listener);await closeDrawer(page);
  checks.push({check:'assistant-local-close-open-preserves-ephemeral-input-mock-clears-no-call',passed:true});
  checks.push({check:'scene-ready-one-canvas-hidden-membership-notebook-original-fact',passed:true});
}
async function visualSampleSnapshots(page,service,earlyArchive) {
  // Correct action follows wrong visible observed target; only statistics change on the failure.
  await observe(page,'r1_clock');const before=structuredClone(state);
  await use(page,'sample_slide','r1_clock',409);countedMistake(before);
  const sample=await appendMoment(page,'样本拿取时刻');await retrieveMoment(page,earlyArchive);
  await closeDrawer(page);await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-view','room');
  await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-cabinet-state','LOCKED');assert.equal(state.inventory.length,0);
  const beforeMarkers=(await markers(page)).length;await retrieveMoment(page,sample);
  await closeDrawer(page);await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-animation','idle');assert.equal((await markers(page)).length,beforeMarkers);
  await refresh(page);assert.deepEqual(publicGame(state),publicGame(sample.state));
  const restart=structuredClone(state);await stop(service.backend);start('visual-R1-sample-backend-restarted',python,service.backendArgs,service.backendEnv);await ready(service.backendURL+'/api/health');
  await menu(page);await http(page,'state',()=>page.getByRole('button',{name:'同步进度',exact:true}).click(),200,'/state');assert.deepEqual(state,restart);
  await closeDrawer(page);await expect(page.locator('.game-canvas-host canvas')).toHaveCount(1);
  await trackMarkers(page);
  checks.push({check:'R1-wrong-held-item-preserved-and-selected-archives-reload-process-restart-snapshot-only',passed:true});
}
async function visualCabinet(page) {
  await select(page,'r1_cabinet');await expect(page.locator('#code-r1_cabinet')).toHaveValue('');
  assert.equal(await page.locator('.scene-keyboard-hotspot[data-object-id="r1_photo"]').count(),0);
  const previous=structuredClone(state), markerCount=(await markers(page)).length;
  await page.locator('#code-r1_cabinet').fill('0000');await http(page,'R1-wrong-lock-code',()=>page.locator('.code-form').getByRole('button',{name:'提交',exact:true}).click(),409);
  countedMistake(previous);assert.equal(state.device_states.cabinet,'LOCKED');assert.equal((await markers(page)).length,markerCount);
  await page.locator('.visual-room').screenshot({path:path.join(folder,'R1-wrong-code-locked.png')});
  await roomView(page);await page.getByRole('button',{name:'线索笔记',exact:true}).click();
  const notebook=page.locator('.notebook-modal'),texts=[];
  do {
    const rows=await notebook.locator('.clue-list li p').allTextContents();assert(rows.length<=2);texts.push(...rows);
    if(!await notebook.getByRole('button',{name:'下一页',exact:true}).isEnabled()) break;
    await notebook.getByRole('button',{name:'下一页',exact:true}).click();
  }while(true);
  assert.deepEqual(texts,state.clues.map(clue=>clue.text));await notebook.getByRole('button',{name:'合上笔记',exact:true}).click();
  checks.push({check:'locked-no-autofill-wrong-receipt-no-animation-notebook-pages-original-facts',passed:true});
}
'''
text = text.replace("async function lightOldVersion", insert + '\nasync function lightOldVersion')
target.write_bytes(text.replace('\n', newline).encode('utf-8'))
assert source.read_bytes() == original
api_source = root / 'evidence/upgrade/v4.0/qa/baseline-api/runner.py'
api_target = root / 'evidence/upgrade/v4.0/qa/formal-api/runner.py'
api_target.parent.mkdir(exist_ok=True)
api_text = api_source.read_text(encoding='utf-8').replace('Independent full API revalidation', 'Independent targeted API/state binding to v4.0 visual candidate').replace('campus-qa-v40-baseline-', 'campus-qa-v40-formal-')
selection = [
    'tests/api/test_upgrade_v34.py::UpgradeV34Acceptance::test_three_levels_only_known_context_no_auto_inspect_no_private_full_solution',
    'tests/api/test_upgrade_v34.py::UpgradeV34Acceptance::test_meaningful_numeric_login_circuit_sequence_wrong_item_count_once_only',
    'tests/api/test_upgrade_v34.py::UpgradeV34Acceptance::test_optional_story_objects_visibility_discoveries_total_ten_and_win_score',
    'tests/api/test_upgrade_v34.py::UpgradeV34Acceptance::test_server_UTC_offline_elapsed_reset_saved_run_restore_and_win_freeze',
    'tests/api/test_multiple_saves.py::MultipleSavesAcceptance::test_append_immutable_three_moments_restore_stats_reset_and_reopen',
    'tests/api/test_multiple_saves.py::MultipleSavesAcceptance::test_selected_restore_expires_pending_mock_hint_without_stats_mutation',
]
api_text = api_text.replace("['tests/api', '-q', '--tb=short', '-p', 'no:cacheprovider']", repr(selection + ['-q', '--tb=short', '-p', 'no:cacheprovider']))
api_target.write_text(api_text, encoding='utf-8', newline='\n')
build_source = root / 'evidence/upgrade/v4.0/qa/baseline_build.py'
build_text = build_source.read_text(encoding='utf-8').replace("/'baseline-build'", "/'formal-build'")
build_text = build_text.replace("CANDIDATE=Path('evidence/upgrade/v4.0/baseline-candidate.json')", "import sys\nif len(sys.argv)!=2:raise SystemExit('Pass frozen Main candidate JSON explicitly')\nCANDIDATE=Path(sys.argv[1])")
(root / 'evidence/upgrade/v4.0/qa/formal_build.py').write_text(build_text, encoding='utf-8', newline='\n')
print(json.dumps({'runner': str(target.relative_to(root)), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'prior_runner_unchanged_sha256': hashlib.sha256(original).hexdigest(), 'formal_runs': 0}))
