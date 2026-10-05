"""QA evidence finalization only; no evaluator or target imports."""
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
for folder,exitcode,session,chunks,count in [
    ('T27-evaluation-events-20261005T101000Z',0,10570,['4f6510','45abeb'],165),
    (OUT.name,0,41908,['443744','eefc04'],168)]:
    directory=ROOT/'evidence/qa'/folder
    r=json.loads((directory/'result.json').read_text(encoding='utf-8'))
    assert r['checks']==r['passed']==count and not r['failures']
    process=dict(actual_command=[sys.executable,'-B','-X','utf8','tests/review_evaluation_events.py','--output','evidence/qa/'+folder],
        working_directory=str(ROOT),actual_exit_code=exitcode,exec_session_id=session,tool_chunk_ids=chunks,
        checks=count,passed=count,legacy_checks=114,result_raw_sha256=sha(directory/'result.json'),
        interpreter_flags_note='result.command preserves sys.argv; this process record includes actually invoked interpreter flags',
        actual_paid_calls=0,actual_external_network_calls=0)
    if (directory/'process-result.json').exists():
        assert json.loads((directory/'process-result.json').read_text(encoding='utf-8'))==process
    else:save(directory/'process-result.json',process)
result=json.loads((OUT/'result.json').read_text(encoding='utf-8'))
assert result['evaluator_sources_before']==result['evaluator_sources_after']
assert all(sha(ROOT/p)==h for p,h in result['evaluator_sources_after'].items())
assert sha(ROOT/'evidence/integration/run_paid_evaluation.py')==result['Main_relay_raw_sha256']
freeze=json.loads((ROOT/'evaluation/trusted/freeze.json').read_text(encoding='utf-8'))
frozen={p:sha(ROOT/'evaluation'/p) for p in freeze['inputs']}
assert len(frozen)==16 and frozen==freeze['inputs']
save(OUT/'source-stop.json',dict(created_at=datetime.now(timezone.utc).isoformat(),evaluation_sources=result['evaluator_sources_after'],
    original_16_inputs=frozen,original_freeze_chain_files=17,freeze_raw_sha256=sha(ROOT/'evaluation/trusted/freeze.json'),
    independent_harness_raw_sha256=sha(ROOT/'tests/review_evaluation_events.py'),
    Main_relay_raw_sha256=result['Main_relay_raw_sha256'],result_raw_sha256=sha(OUT/'result.json'),
    code_source_stable=True,no_paid_GO_inferred=True))
index={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(OUT.rglob('*')) if p.is_file()}
save(OUT/'artifact-sha256.json',index)
print(json.dumps(dict(result_sha256=sha(OUT/'result.json'),process_sha256=sha(OUT/'process-result.json'),
    source_stop_sha256=sha(OUT/'source-stop.json'),artifact_index_sha256=sha(OUT/'artifact-sha256.json'),
    harness_sha256=sha(ROOT/'tests/review_evaluation_events.py'),relay_sha256=result['Main_relay_raw_sha256'],artifact_count=len(index))))
