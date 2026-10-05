"""Finalize independent QA records and source STOP; no implementation imports."""
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
for name,count,session,chunks in [('T24-continuation-20261005T112300Z',393,99080,['814c56','d31613','b4100e']),(OUT.name,449,23159,['fa2c6d','ef1516'])]:
    d=ROOT/'evidence/qa'/name;r=json.loads((d/'result.json').read_text(encoding='utf-8'))
    assert r['checks']==r['passed']==count and not r['failures']
    save(d/'process-result.json',dict(actual_command=[sys.executable,'-B','-X','utf8','tests/review_e1_continuation.py','--output','evidence/qa/'+name],working_directory=str(ROOT),actual_exit_code=0,session_id=session,tool_chunks=chunks,result_raw_sha256=sha(d/'result.json'),checks=count,passed=count,actual_paid_calls=0,actual_external_network_calls=0,interpreter_flags_note='result.command retains sys.argv; actual flags recorded here'))
r=json.loads((OUT/'result.json').read_text(encoding='utf-8'))
assert r['sources_before']==r['sources_after'] and r['protected_before']==r['protected_after']
for p,h in {**r['sources_after'],**r['protected_after']}.items():assert sha(ROOT/p)==h,p
owner=ROOT/'experiments/runs/20261005T110033349203Z-continuation-plan-50250a53/owner-candidate-report.json'
assert sha(owner)=='234f875816910ebdb21e79e1f1f8dc0d822f27470f36df063bc479ca77946921'
save(OUT/'source-stop.json',dict(created_at=datetime.now(timezone.utc).isoformat(),executor_sources=r['sources_after'],original41_sources=r['original41_sources'],protected_original_bytes=r['protected_after'],plan_raw_sha256=r['plan_raw_sha256'],owner_report_raw_sha256=sha(owner),QA_harness_raw_sha256=sha(ROOT/'tests/review_e1_continuation.py'),result_raw_sha256=sha(OUT/'result.json'),no_real_GO_inferred=True,source_STOP=True))
index={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(OUT.rglob('*')) if p.is_file()}
assert not any(p.endswith(('.sqlite','.env')) for p in index)
save(OUT/'artifact-sha256.json',index)
print(json.dumps(dict(result_sha256=sha(OUT/'result.json'),process_sha256=sha(OUT/'process-result.json'),source_stop_sha256=sha(OUT/'source-stop.json'),artifact_index_sha256=sha(OUT/'artifact-sha256.json'),harness_sha256=sha(ROOT/'tests/review_e1_continuation.py'),artifact_count=len(index))))
