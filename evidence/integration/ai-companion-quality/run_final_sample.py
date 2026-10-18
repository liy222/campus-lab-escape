"""One new fixed-source sample; fourth and final paid call of this epoch."""
from pathlib import Path
from datetime import datetime, timezone
import importlib.util
import hashlib
import json
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SEALED=ROOT/'evidence/integration/ai-companion-real/run_playtest.py'
spec=importlib.util.spec_from_file_location('sealed_json_mode_sample',SEALED)
executor=importlib.util.module_from_spec(spec);spec.loader.exec_module(executor)
executor.OUT=HERE/'final-paid';executor.LIMIT=0.10
executor.CASES=[('Q05',40,'fixed_login_reasoning','屏幕已经显示登录通过，可我还在想是不是该重新输密码。你能只根据电脑现在的反馈，帮我区分已经完成的事和仍不确定的事吗？')]
original_body=executor.request_body

def json_body(messages,max_tokens=600):
 body=original_body(messages,max_tokens)
 body['response_format']={'type':'json_object'}
 return body
executor.request_body=json_body

def prepare():
 from backend.app.ai.companion import SYSTEM,build_companion_context,provider_companion_context
 executor.OUT.mkdir(exist_ok=True)
 first=json.loads((HERE/'paid-summary.json').read_text(encoding='utf-8'))
 assert first['actual_provider_dispatches']==3 and first['new_unknown_count']==0
 state=executor.projection(40);context=provider_companion_context(build_companion_context(state,executor.CASES[0][3]),state)
 body=json_body([{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps(context,ensure_ascii=False)}])
 plan={'recorded_at':datetime.now(timezone.utc).isoformat(),'authorization':'One new sample under original user paid quality/fix request and CNY10; cumulative epoch maximum4calls/0.30.','baseline_source_sha256':executor.source_map(),'executor_sha256':hashlib.sha256(SEALED.read_bytes()).hexdigest(),'endpoint':'https://api.deepseek.com/chat/completions','model':'deepseek-flash','maximum_real_calls':1,'round_limit_cny':0.10,'epoch_maximum_calls':4,'epoch_maximum_cny':0.30,'no_retries':True,'prior_summary_sha256':hashlib.sha256((HERE/'paid-summary.json').read_bytes()).hexdigest(),'cases':[{'case_id':'Q05','legal_route_prefix':40,'body':body,'offline_bound_cny':executor.bound(body)}]}
 executor.dump(executor.OUT/'payload-preview.json',plan)
 print(json.dumps({'case':'Q05','maximum_calls':1,'upper_reservation':executor.bound(body)},ensure_ascii=False))

def execute():
 plan=json.loads((executor.OUT/'payload-preview.json').read_text(encoding='utf-8'))
 assert not list(executor.OUT.glob('*-real')),'No replay'
 first=json.loads((HERE/'paid-summary.json').read_text(encoding='utf-8'))
 assert first['actual_provider_dispatches']==3 and first['new_unknown_count']==0
 assert first['actual_charged_cny']+executor.LIMIT<=0.30
 assert hashlib.sha256((HERE/'paid-summary.json').read_bytes()).hexdigest()==plan['prior_summary_sha256']
 assert hashlib.sha256(SEALED.read_bytes()).hexdigest()==plan['executor_sha256']
 code=executor.execute()
 results=list(executor.OUT.glob('*-real/result.json'));assert len(results)==1
 result=json.loads(results[0].read_text(encoding='utf-8'))
 assert result['actual_provider_dispatches']<=1
 summary={key:result[key] for key in ('recorded_at','source_sha256','source_matches_prepared','before_budget','after_budget','actual_provider_dispatches','actual_charged_cny','new_unknown_count','stopped_reason','limitations')}
 summary.update(authorization=plan['authorization'],result_path=results[0].relative_to(ROOT).as_posix(),result_sha256=hashlib.sha256(results[0].read_bytes()).hexdigest(),executor_exit_code=code,epoch_paid_calls=first['actual_provider_dispatches']+result['actual_provider_dispatches'],epoch_charge_upper_cny=round(first['actual_charged_cny']+result['actual_charged_cny'],9),legacy_executor_note='Sealed executor historical authorization text mentions8/1.50; wrapper enforces1newcall and0.10, epoch4/0.30. response_format is included in preview and outgoing capture, matches production json_modeTrue.')
 executor.dump(HERE/'final-paid-summary.json',summary)
 return code

if __name__=='__main__':
 if sys.argv[1:]==['--prepare']:prepare()
 elif sys.argv[1:]==['--execute']:sys.exit(execute())
 else:raise SystemExit('Use --prepare offline or --execute once')
