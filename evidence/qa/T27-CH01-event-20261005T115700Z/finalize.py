"""QA evidence finalization; no target imports or original ledger access."""
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
r=load(OUT/'result.json');assert r['checks']==r['passed']==79 and not r['failures']
assert r['sources_before']==r['sources_after']
for p,h in {**r['sources_after'],**r['protected_Main_archive_bytes']}.items():assert sha(ROOT/p)==h,p
save(OUT/'process-result.json',dict(actual_command=[sys.executable,'-B','-X','utf8','tests/review_ch01_evaluation.py','--output','evidence/qa/'+OUT.name],working_directory=str(ROOT),actual_exit_code=0,tool_chunk_id='484a1a',checks=79,passed=79,actual_paid_calls=0,actual_external_network_calls=0,mock_cli_internal_exit_code=2,result_raw_sha256=sha(OUT/'result.json'),flags_note='result.command retains sys.argv; interpreter flags actually invoked are included here'))
save(OUT/'source-stop.json',dict(created_at=datetime.now(timezone.utc).isoformat(),candidate52_sources=r['sources_after'],protected_Main_and162_archived_source_bytes=r['protected_Main_archive_bytes'],QA_harness_raw_sha256=sha(ROOT/'tests/review_ch01_evaluation.py'),result_raw_sha256=sha(OUT/'result.json'),legacy_gate_failure_preserved=True,Main_relay_comparison_scope='Current QA raw-byte comparison to prior independent pin; not an Owner immediate snapshot',target_execution=False,archive_execution=False,no_new_paid_GO=True,source_STOP=True))
index={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(OUT.rglob('*')) if p.is_file()}
assert not any(p.endswith(('.sqlite','.env')) for p in index)
save(OUT/'artifact-sha256.json',index)
print(json.dumps(dict(result_sha256=sha(OUT/'result.json'),process_sha256=sha(OUT/'process-result.json'),source_stop_sha256=sha(OUT/'source-stop.json'),artifact_index_sha256=sha(OUT/'artifact-sha256.json'),harness_sha256=sha(ROOT/'tests/review_ch01_evaluation.py'),artifact_count=len(index))))
