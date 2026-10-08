"""Register QA marker observer in new touch context; add nonmutating mobile PNG capture."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[4];qa=Path(__file__).resolve().parent;target=root/'tests/e2e/run_visual_v41.mjs';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(target)=='8fb1322e3434037a5c7807a59a5b3a06cad7f12f5a97c7c57e455a0fcd8deb8f'
second=qa/'runner-epochs/second.mjs';assert not second.exists();second.write_bytes(target.read_bytes())
text=target.read_text(encoding='utf-8')
a="await page.goto(service.frontendURL,{waitUntil:'networkidle'});await http(page,'R2-touch-create',()=>page.getByRole('button',{name:'开始新游戏 →',exact:true}).click(),201,'/api/sessions');"
assert text.count(a)==1;text=text.replace(a,a+'await trackMarkers(page);')
a="await layout(page,375,'R2-mobile-circuit'); await page.setViewportSize({width:1280,height:900});"
assert text.count(a)==1;text=text.replace(a,"await layout(page,375,'R2-mobile-circuit');await page.screenshot({path:path.join(folder,'R2-mobile-circuit.png'),fullPage:true});await page.setViewportSize({width:1280,height:900});")
a="await layout(page, 375, 'R2-mobile-login'); await page.setViewportSize({ width: 1280, height: 900 });"
assert text.count(a)==1;text=text.replace(a,"await layout(page,375,'R2-mobile-login');await page.screenshot({path:path.join(folder,'R2-mobile-login.png'),fullPage:true});await page.setViewportSize({width:1280,height:900});")
a="assert(!state.inventory.some(item=>['research_strip','access_card'].includes(item.item_id)));await r2Checkpoint(page,'R2-DATA_READ-tray-items-not-auto-taken');"
assert text.count(a)==1;text=text.replace(a,a+"await page.setViewportSize({width:375,height:812});await r2Checkpoint(page,'R2-DATA_READ-tray-mobile');await page.setViewportSize({width:1280,height:900});")
target.write_text(text,encoding='utf-8')
command=['C:/Program Files/nodejs/node.exe','--check',target.relative_to(root).as_posix()];syntax=subprocess.run(command,cwd=root,text=True,capture_output=True)
prior=json.loads((qa/'browser-attempts.json').read_text(encoding='utf-8'));failed_path=qa/'20261008T010350006Z-browser/run.json';failed=json.loads(failed_path.read_text(encoding='utf-8'))
assert failed['exit_code']==1 and len(failed['checks'])==278 and failed['source_sha256_before']==failed['source_sha256_after']
assert any(c['check']=='three-room-route-slots-items-save-restore-reload-actual-server-restart-win' for c in failed['checks'])
prior['second_failed_attempt']={'path':failed_path.relative_to(root).as_posix(),'sha256':sha(failed_path),'exit_code':1,'checks':278,'source123_before_after_same':True,'issues':failed['issues'],'scope':'Desktop complete route completed; new separate touchR2 context omitted observer registration before R1 sample_take setup. Fresh animation assertion retained.'}
prior['runner_epochs'].append({'path':second.relative_to(root).as_posix(),'sha256':sha(second)});prior['runner_epochs'][-2]['path']='tests/e2e/run_visual_v41.mjs (historical second epoch now archived as runner-epochs/second.mjs)'
prior['third_runner']={'path':target.relative_to(root).as_posix(),'sha256':sha(target)}
prior['touch_fix']={'command':command,'exit_code':syntax.returncode,'scope':'New touch observer registration only; nonmutating375 full-page circuit/CRT/tray screenshots added; no assertions removed','recorded_at':datetime.now(timezone.utc).isoformat()}
(qa/'browser-attempts.json').write_text(json.dumps(prior,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'exit_code':syntax.returncode,'second278_failure_preserved':True,'new_runner_sha256':sha(target)}))
raise SystemExit(syntax.returncode)
