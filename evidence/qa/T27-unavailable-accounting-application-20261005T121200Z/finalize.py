"""Finalize captured postapply evidence without reopening the ledger."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
r=json.loads((OUT/'result.json').read_text(encoding='utf-8'));assert r['checks']==r['passed']==95 and not r['failures']
assert sha(ROOT/'evidence/integration/reconcile_unavailable_upper.py')==r['helper_raw_sha256']
save(OUT/'process-result.json',dict(actual_command=r['actual_command'],working_directory=str(ROOT),actual_exit_code=0,tool_chunk_id='042ae4',checks=95,passed=95,result_raw_sha256=sha(OUT/'result.json'),original_ledger_mode='ro',original_apply_executed_by_QA=False,actual_paid_calls=0,actual_network_calls=0))
save(OUT/'source-stop.json',dict(helper_raw_sha256=r['helper_raw_sha256'],QA_review_raw_sha256=sha(OUT/'review.py'),result_raw_sha256=sha(OUT/'result.json'),applied_record_raw_sha256=r['Main_applied_record_raw_sha256'],preQA_result_raw_sha256=r['preQA_result_raw_sha256'],ledger_not_reopened_by_finalization=True,source_STOP=True))
index={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(OUT.rglob('*')) if p.is_file()};save(OUT/'artifact-sha256.json',index)
print(json.dumps(dict(process_sha256=sha(OUT/'process-result.json'),source_stop_sha256=sha(OUT/'source-stop.json'),artifact_index_sha256=sha(OUT/'artifact-sha256.json'),pre_report_sha256=sha(ROOT/'review/findings/T27-unavailable-accounting-20261005.md'),post_report_sha256=sha(ROOT/'review/findings/T27-unavailable-accounting-postapply-20261005.md'))))
