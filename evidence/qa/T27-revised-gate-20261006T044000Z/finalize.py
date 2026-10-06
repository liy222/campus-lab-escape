import hashlib,json
from pathlib import Path
p=Path(__file__).resolve().parent;root=p.parents[2]
sha=lambda b:hashlib.sha256(b).hexdigest()
result=json.loads((p/'result.json').read_bytes())
assert all(sha((root/n).read_bytes())==h for n,h in result['source_hashes_before_after'].items() if n!='evaluation/trusted/paid-gates.json')
report=root/'review/findings/T27-revised-gate-20261006.md'
process={'actual_command':'C:\\Users\\liyh\\.conda\\envs\\1\\python.exe -B -X utf8 evidence/qa/T27-revised-gate-20261006T044000Z/readcheck.py','actual_exit_code':0,'chunk':'5c586c','checks':54,'passed':54,'helper_executed_by_QA':False,'live_ledger_opened':False,'real_model_calls_by_QA':0,'postreview_Main_gate_mutation':'See sealing-failure.json; not part of original54-check epoch.'}
(p/'process-result.json').write_text(json.dumps(process,indent=2)+'\n',encoding='utf-8')
(p/'source-stop.json').write_text(json.dumps({'source_stop':True,'role':'independent static Main finite gate helper review only','helper_sha256':result['source_hashes_before_after']['evidence/integration/authorize_revised_evaluation.py'],'result_sha256':sha((p/'result.json').read_bytes()),'report_sha256':sha(report.read_bytes()),'runtime_preflight_still_required':True,'no_self_engine_certification':True,'limits':result['limitations']},indent=2)+'\n',encoding='utf-8')
index={f.name:{'sha256':sha(f.read_bytes()),'bytes':f.stat().st_size} for f in sorted(p.iterdir()) if f.is_file() and f.name!='artifact-sha256.json'}
(p/'artifact-sha256.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'report_sha256':sha(report.read_bytes()),'source_stop_sha256':sha((p/'source-stop.json').read_bytes()),'artifact_index_sha256':sha((p/'artifact-sha256.json').read_bytes()),'result_sha256':sha((p/'result.json').read_bytes()),'files':len(index)}))
