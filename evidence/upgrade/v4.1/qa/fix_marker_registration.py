"""Correct new QA observer across full reload; no assertion weakening or product edit."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[4]
qa=Path(__file__).resolve().parent
target=root/'tests/e2e/run_visual_v41.mjs'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(target)=='c0307307bc2ea5cae6df87657d387a0c34d37566278dbcb7951e3206ed4275b1'
epochs=qa/'runner-epochs';epochs.mkdir(exist_ok=True);first=epochs/'first.mjs';assert not first.exists();first.write_bytes(target.read_bytes())
text=target.read_text(encoding='utf-8')
a="await http(page, 'state', () => page.locator('.welcome-buttons').getByRole('button', { name: '继续当前游戏', exact: true }).click(), 200, '/state');"
assert text.count(a)==1;text=text.replace(a,a+"\n  if(visual()) await trackMarkers(page);")
a="function briefError(error) { return String(error.message || error).split(/\\r?\\n/)[0].slice(0,240); }"
assert text.count(a)==1;text=text.replace(a,a+"""
function diagnosticError(error) {
  const result={error:briefError(error),stack_frames:String(error.stack||'').split(/\\r?\\n/).filter(line=>/^\\s+at\\s/.test(line)).map(line=>line.trim())};
  const matcher=error.matcherResult;
  if(matcher&&['boolean','number'].includes(typeof matcher.actual)) result.actual=matcher.actual;
  if(matcher&&['boolean','number'].includes(typeof matcher.expected)) result.expected=matcher.expected;
  return result;
}""")
a="} catch (error) { issues.push({ check: 'runner', error: briefError(error) }); }"
assert text.count(a)==1;text=text.replace(a,"} catch (error) { issues.push({ check: 'runner', ...diagnosticError(error) }); }")
target.write_text(text,encoding='utf-8')
command=['C:/Program Files/nodejs/node.exe','--check',target.relative_to(root).as_posix()]
run=subprocess.run(command,cwd=root,text=True,capture_output=True)
prior=qa/'20261008T010100682Z-browser/run.json';d=json.loads(prior.read_text(encoding='utf-8'))
assert d['exit_code']==1 and len(d['checks'])==204 and d['source_sha256_before']==d['source_sha256_after']
record={'recorded_at':datetime.now(timezone.utc).isoformat(),'failed_attempt':{'path':prior.relative_to(root).as_posix(),'sha256':sha(prior),'exit_code':1,'checks':204,'source123_before_after_same':True,'issues':d['issues'],'complete_original_stack_available':False,'limitation':'First runner catch retained onlyfirst line; closed browser/process state cannot reconstruct original fullstack. Not invented retroactively.'},'diagnosis':'Static new-adapter bug: full page reload removeswindow.qaVisualObserver/qaVisualMarkers; refresh helper omitted re-registration before newlystrict posttake marker check. UI/server take behavior not diagnosed as product failure.','assertion_policy':'Retain actual fresh receipt animation checks, full route/game/state/save/replay assertions. Only re-install observer after successful visual refresh. Future actual errors preserve stack frames and primitive bool/numbermatcher without full-state sensitive dumps.','runner_epochs':[{'path':first.relative_to(root).as_posix(),'sha256':sha(first)},{'path':target.relative_to(root).as_posix(),'sha256':sha(target)}],'syntax_command':command,'syntax_exit_code':run.returncode,'formal_runs_by_this_script':0,'product_edits':0,'paid_calls':0}
(qa/'browser-attempts.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'exit_code':run.returncode,'original204_failure_preserved':True,'new_runner_sha256':sha(target)}))
raise SystemExit(run.returncode)
