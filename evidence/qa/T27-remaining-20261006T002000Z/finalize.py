import hashlib,json
from pathlib import Path
p=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
report=p.parents[2]/'review/findings/T27-remaining-evaluation-20261006.md'
record={'actual_command':'C:\\Users\\liyh\\.conda\\envs\\1\\python.exe -B -X utf8 evidence/qa/T27-remaining-20261006T002000Z/review.py','actual_exit_code':0,'chunk_id':'06888f','checks':73,'passed':73,'previous_actual_exit_code':1,'previous_chunk':'c4b06b','limits':'Only new independent QA read/hash harness executed; no target imports, ledger access or paid calls.'}
(p/'process-result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
result=json.loads((p/'result.json').read_bytes())
(p/'source-stop.json').write_text(json.dumps({'source_stop':True,'role':'independent QA','result_sha256':sha((p/'result.json').read_bytes()),'report_sha256':sha(report.read_bytes()),'reviewer_sha256':sha((p/'review.py').read_bytes()),'evaluator_source14':result['source14_before_after'],'actual_paid_calls_by_QA':0,'live_ledger_opened':False,'remaining_limits':result['limits']},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
index={f.name:{'sha256':sha(f.read_bytes()),'bytes':f.stat().st_size} for f in sorted(p.iterdir()) if f.is_file() and f.name!='artifact-sha256.json'}
(p/'artifact-sha256.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'files':len(index),'report_sha256':sha(report.read_bytes()),'reviewer_sha256':sha((p/'review.py').read_bytes()),'result_sha256':sha((p/'result.json').read_bytes()),'source_stop_sha256':sha((p/'source-stop.json').read_bytes()),'artifact_index_sha256':sha((p/'artifact-sha256.json').read_bytes())}))
