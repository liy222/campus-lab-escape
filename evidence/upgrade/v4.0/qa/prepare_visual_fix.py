"""Prepare a narrow public-UI recheck; no acceptance runs here."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[4]
source = root / 'tests/e2e/run_visual_v40.mjs'
target = root / 'tests/e2e/run_visual_v40_fix.mjs'
original = source.read_bytes()
text = original.decode().replace('\r\n', '\n')
start = text.index('try {\n  assert(fs.existsSync(chromePath));')
end = text.index('} catch (error) { issues.push', start)
replacement = r'''
async function readable(page,label) {
  const actual=await page.evaluate(()=>{
    const rect=element=>{const r=element.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};};
    const overlaps=(a,b)=>Math.min(a.right,b.right)>Math.max(a.left,b.left)&&Math.min(a.bottom,b.bottom)>Math.max(a.top,b.top);
    const feedback=[...document.querySelectorAll('.feedback p')].filter(element=>element.getClientRects().length).map(rect);
    const content=[...document.querySelectorAll('.game-hud button,.closeup-reading,.closeup-description,.closeup-controls button,.closeup-controls input,.closeup-controls label')].filter(element=>element.getClientRects().length).map(rect);
    return {feedback_count:feedback.length,content_count:content.length,feedback_overlaps:feedback.flatMap(a=>content.filter(b=>overlaps(a,b))).length,outside_horizontal:content.filter(r=>r.left<0||r.right>innerWidth).length,controls_below_viewport:[...document.querySelectorAll('.closeup-controls button,.closeup-controls input')].filter(element=>element.getClientRects().length).map(rect).filter(r=>r.top>=innerHeight).length};
  });
  assert.equal(actual.feedback_overlaps,0,'Feedback obscures readable clue/controls');assert.equal(actual.outside_horizontal,0);
  checks.push({check:'fixed-feedback-does-not-cover-reading-return-input',label,...actual,passed:true});
  await page.screenshot({path:path.join(folder,label+'.png'),fullPage:true});await canvasPixels(page,label);
}
async function widths(page,id,label) {
  for(const width of [1920,1280,375]) {
    await page.setViewportSize({width,height:width===375?812:width===1920?1080:900});
    await observe(page,id);await readable(page,label+'-'+width);
  }
}
try {
  assert(fs.existsSync(chromePath));const service=await pair('v3.4');
  browser=await chromium.launch({headless:true,executablePath:chromePath});
  const context=await browser.newContext({viewport:{width:1920,height:1080}}),page=await context.newPage(),pageErrors=[];
  page.on('pageerror',()=>pageErrors.push('uncaught browser exception'));
  await page.goto(service.frontendURL,{waitUntil:'networkidle'});
  await http(page,'create',()=>page.getByRole('button',{name:'开始新游戏 →',exact:true}).click(),201,'/api/sessions');await trackMarkers(page);
  const svgArgs=['-B','-X','utf8',path.join(root,'evidence/upgrade/v4.0/qa/svg_check.py')];
  const svg=spawnSync(python,svgArgs,{cwd:root,encoding:'utf8',windowsHide:true});commands.push({label:'fixed-public-SVG-clock-lock-geometry',executable:python,arguments:svgArgs,cwd:root,exit_code:svg.status,stdout:svg.stdout.trim(),stderr:svg.stderr.trim()});assert.equal(svg.status,0);checks.push({check:'public-SVG-clock-21-17-four-lock-wheels',...JSON.parse(svg.stdout)});
  await widths(page,'r1_clock','fixed-clock-reading');await widths(page,'r1_record','fixed-record-reading');await widths(page,'r1_plaque','fixed-plaque-reading');
  await observe(page,'sample_slide');await interact(page,'sample_slide');await use(page,'sample_slide','r1_microscope');assert.equal(state.puzzle_states.microscope,'SLIDE_PLACED');
  await widths(page,'r1_microscope','fixed-eyepiece-reading');
  await widths(page,'r1_cabinet','fixed-four-wheel-lock');
  for(const width of [1920,1280,375]) {
    await page.setViewportSize({width,height:width===375?812:width===1920?1080:900});await select(page,'r1_cabinet');
    const before=structuredClone(state);await page.locator('#code-r1_cabinet').fill('0000');await http(page,'fixed-visible-wrong-code-'+width,()=>page.locator('.code-form').getByRole('button',{name:'提交',exact:true}).click(),409);countedMistake(before);await readable(page,'fixed-wrong-code-'+width);
  }
  await page.setViewportSize({width:1280,height:900});await code(page,'r1_cabinet','4217');assert.equal(state.device_states.cabinet,'CODE_ACCEPTED');await readable(page,'fixed-accepted-closed');
  await interact(page,'r1_cabinet');assert.equal(state.device_states.cabinet,'OPEN');await readable(page,'fixed-cabinet-open');
  await observe(page,'r1_fuse');await interact(page,'r1_fuse');await widths(page,'r1_photo','fixed-photo-reading');
  const saved=(await control(page,'save')).data.visible_state;await control(page,'reset');await control(page,'restore');assert.deepEqual(publicGame(state),publicGame(saved));
  await closeDrawer(page);await expect(page.locator('.game-canvas-host')).toHaveAttribute('data-animation','idle');await widths(page,'r1_photo','fixed-restored-photo-reading');
  assert.equal(pageErrors.length,0);checks.push({check:'narrow-fixed-R1-css-clock-lock-and-restored-snapshot',passed:true});await context.close();
'''
text = text[:start] + replacement.lstrip() + text[end:]
text = text.replace(" + '-browser'", " + '-browser-fix'")
text = text.replace("// Independent v4.0 R1 visual adapter; complete prior route/assertions retained, owned mock DBs.", "// Narrow v4.0 fixed-candidate R1 visual recheck; original complete runner remains sealed.")
text = text.replace("'No actual root CMD startup; direct loopback module launches only; partial circuit and archive-list process restart exercised'", "'Narrow R1 CSS/clock/four-wheel-lock and restored snapshot recheck; complete route/API/restart reused from prior frozen-candidate epoch'")
target.write_bytes(text.replace('\n', '\r\n').encode())
assert source.read_bytes() == original
build_source = root / 'evidence/upgrade/v4.0/qa/formal_build.py'
build_text = build_source.read_text(encoding='utf-8').replace("/'formal-build'", "/'fixed-build'")
(root / 'evidence/upgrade/v4.0/qa/fixed_build.py').write_text(build_text, encoding='utf-8', newline='\n')
print(json.dumps({'exit_code':0,'runner':str(target.relative_to(root)),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'formal_runs':0}))
