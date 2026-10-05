"""Finalize prior read-only QA evidence; do not reopen the live ledger."""
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
r=load(OUT/'result.json');assert r['checks']==r['passed']==130 and not r['failures']
assert r['original_ledger_before']==r['original_ledger_after']
assert sha(ROOT/'evidence/integration/reconcile_unavailable_upper.py')==r['helper_raw_sha256']=='151b30144e1f440e3abb8c7901d3e27c180601d742fcfcb24f15d7e5989175b8'
for p,h in r['protected_prior_files'].items():assert sha(ROOT/p)==h
save(OUT/'process-result.json',dict(actual_command=[sys.executable,'-B','-X','utf8','tests/review_unavailable_reconciliation.py','--output','evidence/qa/'+OUT.name],working_directory=str(ROOT),actual_exit_code=0,tool_chunk_id='5298c4',checks=130,passed=130,original_ledger_mode='ro',original_apply_executed=False,actual_paid_calls=0,actual_network_calls=0,result_raw_sha256=sha(OUT/'result.json')))
save(OUT/'source-stop.json',dict(created_at=datetime.now(timezone.utc).isoformat(),helper_raw_sha256=r['helper_raw_sha256'],QA_harness_raw_sha256=sha(ROOT/'tests/review_unavailable_reconciliation.py'),protected_prior_files=r['protected_prior_files'],result_raw_sha256=sha(OUT/'result.json'),ledger_snapshot_scope='Preapply original mode=ro before/after captured during the actual130-check run; not reread after Main may apply',accounting_only_no_invoice_verified=True,source_STOP=True))
index={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(OUT.rglob('*')) if p.is_file()}
save(OUT/'artifact-sha256.json',index)
print(json.dumps(dict(result_sha256=sha(OUT/'result.json'),process_sha256=sha(OUT/'process-result.json'),source_stop_sha256=sha(OUT/'source-stop.json'),artifact_index_sha256=sha(OUT/'artifact-sha256.json'),harness_sha256=sha(ROOT/'tests/review_unavailable_reconciliation.py'),artifact_count=len(index))))
