import hashlib,json
from pathlib import Path
p=Path(__file__).resolve().parent;root=p.parents[2]
sha=lambda b:hashlib.sha256(b).hexdigest()
report=root/'review/findings/T27-revised-real-result-20261006.md'
reviewer=root/'tests/review_revised_evaluation_result.py'
result=json.loads((p/'result.json').read_bytes())
process={'actual_command':'C:\\Users\\liyh\\.conda\\envs\\1\\python.exe -B -X utf8 tests/review_revised_evaluation_result.py --output evidence/qa/T27-revised-real-result-20261006T045000Z','actual_exit_code':0,'chunk_id':'02f6ff','checks':75,'passed':75,'target_evaluator_code_executed_by_QA':False,'actual_model_requests_by_QA':0,'live_ledger_opened':False}
(p/'process-result.json').write_text(json.dumps(process,indent=2)+'\n',encoding='utf-8')
(p/'source-stop.json').write_text(json.dumps({'source_stop':True,'role':'result-only independent QA; no self-certification of engine source','report_sha256':sha(report.read_bytes()),'reviewer_sha256':sha(reviewer.read_bytes()),'result_sha256':sha((p/'result.json').read_bytes()),'input_sources_before_after':result['input_hashes_before_after'],'actual_run_source14':result['source14'],'limits':result['limits']},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
index={f.name:{'sha256':sha(f.read_bytes()),'bytes':f.stat().st_size} for f in sorted(p.iterdir()) if f.is_file() and f.name!='artifact-sha256.json'}
(p/'artifact-sha256.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'report_sha256':sha(report.read_bytes()),'reviewer_sha256':sha(reviewer.read_bytes()),'result_sha256':sha((p/'result.json').read_bytes()),'source_stop_sha256':sha((p/'source-stop.json').read_bytes()),'artifact_index_sha256':sha((p/'artifact-sha256.json').read_bytes()),'artifact_count':len(index)}))
