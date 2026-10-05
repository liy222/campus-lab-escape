"""Finalize clean/calibration QA evidence; no ledger or target access."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
items=[('T32-final-20261005T123100Z',10842,0,['36b045','199dac']),('T27-calibration-20261005T123100Z',45,1,['b05e62']),('T27-calibration-20261005T160500Z',46,0,['293a4d'])]
for name,count,exitcode,chunks in items:
    d=ROOT/'evidence/qa'/name;r=load(d/'result.json');assert r['checks']==count and r['exit_code']==exitcode
    if exitcode==0:assert r['passed']==count and not r['failures']
    save(d/'process-result.json',dict(actual_command=r['actual_command'],working_directory=str(ROOT),actual_exit_code=exitcode,tool_chunks=chunks,result_raw_sha256=sha(d/'result.json'),checks=count,passed=r['passed'],failures=r['failures'],QA_paid_calls=0,QA_network_calls=0))
    executed=d/'reviewer-source-at-execution.py' if name.startswith('T32') else ROOT/'tests/review_final_delivery.py'
    if name.startswith('T32'):assert sha(executed)==r['QA_reviewer_raw_sha256']
    save(d/'source-stop.json',dict(executed_QA_source_raw_sha256=r['QA_reviewer_raw_sha256'],current_QA_harness_raw_sha256=sha(ROOT/'tests/review_final_delivery.py'),executed_source_snapshot=str(executed) if name.startswith('T32') else None,result_raw_sha256=sha(d/'result.json'),scope='Original ledger STOP; later6 requests not reviewed. Clean review complete10778 bytes without rerun. Calibration current facts use captured epoch.',source_STOP=True,original_ledger_reopened_by_finalization=False))
    index={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(d.rglob('*')) if p.is_file()};save(d/'artifact-sha256.json',index)
    print(json.dumps(dict(directory=name,result_sha256=sha(d/'result.json'),process_sha256=sha(d/'process-result.json'),source_stop_sha256=sha(d/'source-stop.json'),artifact_index_sha256=sha(d/'artifact-sha256.json'),artifact_count=len(index))))
print(json.dumps(dict(current_harness_sha256=sha(ROOT/'tests/review_final_delivery.py'),T32_report_sha256=sha(ROOT/'review/findings/T32-final-20261005.md'),calibration_report_sha256=sha(ROOT/'review/findings/T27-real-calibration-20261005.md'))))
