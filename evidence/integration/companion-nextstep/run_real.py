"""Two new production-path samples using a legal clone of reported public stage."""
from pathlib import Path
from datetime import datetime,timezone
import importlib.util
import hashlib
import json
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SEALED=ROOT/'evidence/integration/ai-companion-real/run_playtest.py'
spec=importlib.util.spec_from_file_location('nextstep_sealed_executor',SEALED)
executor=importlib.util.module_from_spec(spec);spec.loader.exec_module(executor)
STEPS=[('inspect',{'object_id':x}) for x in ('r1_record','r1_microscope','sample_slide','r1_clock','r1_cabinet','r1_door')]+[('interact',{'target_id':'r1_door'}),('inspect',{'object_id':'r1_plaque'}),('move',{'destination_id':'R2'}),('inspect',{'object_id':'r2_maintenance'})]
executor.route=lambda:[{'tool':tool,'arguments':args} for tool,args in STEPS]
executor.OUT=HERE/'paid';executor.LIMIT=0.16
executor.CASES=[('N01',10,'reported_stage_nextstep','下一步怎么做'),('N02',10,'followup','为什么先看这件东西？我想自己操作，请只解释你建议的依据。')]
plain_body=executor.request_body

def request_body(messages,max_tokens=600):
 body=plain_body(messages,max_tokens);body['response_format']={'type':'json_object'};return body
executor.request_body=request_body

def prepare():
 from backend.app.ai.companion import SYSTEM,build_companion_context,provider_companion_context
 executor.OUT.mkdir(exist_ok=True)
 state=executor.projection(10)
 assert state['room']['room_id']=='R2' and state['device_states']['powerbox']=='CLOSED' and state['device_states']['computer']=='OFF'
 assert state['puzzle_states']['microscope']=='EMPTY' and state['inventory']==[] and len(state['clues'])==4
 previews=[]
 for cid,n,kind,question in executor.CASES:
  history=() if kind!='followup' else ({'kind':'dialogue','question':executor.CASES[0][3],'answer':'[Actual accepted N01 answer at execution, maximum360 characters]','clue_refs':[]},)
  context=provider_companion_context(build_companion_context(state,question,history),state)
  body=request_body([{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps(context,ensure_ascii=False)}])
  previews.append({'case_id':cid,'kind':kind,'legal_route_prefix':n,'body':body,'offline_bound_cny':executor.bound(body)})
 plan={'recorded_at':datetime.now(timezone.utc).isoformat(),'authorization':'Targeted validation of user-reported paid companion bug within previously approved project CNY10 budget.','endpoint':'https://api.deepseek.com/chat/completions','model':'deepseek-flash','baseline_source_sha256':executor.source_map(),'executor_sha256':hashlib.sha256(SEALED.read_bytes()).hexdigest(),'maximum_real_calls':2,'round_limit_cny':0.16,'no_retries':True,'stage':'Legal API clone of public reported stage only; no live user DB mutation or session export.','cases':previews,'limits':['Original rejected reply was not persisted, so this does not reproduce its exact raw output.','N02 uses actual accepted N01 same-session history; skipped if parent fails.','At most two new calls, no retry, unknown/freeze/clear disclosure stops.']}
 executor.dump(executor.OUT/'payload-preview.json',plan)
 print(json.dumps({'preview':str(executor.OUT/'payload-preview.json'),'calls_max':2,'reservation_upper':sum(c['offline_bound_cny'] for c in previews)},ensure_ascii=False))

def execute():
 plan=json.loads((executor.OUT/'payload-preview.json').read_text(encoding='utf-8'))
 assert len(executor.CASES)==plan['maximum_real_calls']==2 and executor.LIMIT==plan['round_limit_cny']==0.16
 assert not list(executor.OUT.glob('*-real')),'No replay'
 assert hashlib.sha256(SEALED.read_bytes()).hexdigest()==plan['executor_sha256']
 code=executor.execute()
 paths=list(executor.OUT.glob('*-real/result.json'));assert len(paths)==1
 result=json.loads(paths[0].read_text(encoding='utf-8'));assert result['actual_provider_dispatches']<=2
 summary={key:result[key] for key in ('recorded_at','source_sha256','source_matches_prepared','before_budget','after_budget','actual_provider_dispatches','actual_charged_cny','new_unknown_count','stopped_reason','limitations')}
 summary.update(authorization=plan['authorization'],maximum_real_calls=2,round_limit_cny=0.16,executor_exit_code=code,result_path=paths[0].relative_to(ROOT).as_posix(),result_sha256=hashlib.sha256(paths[0].read_bytes()).hexdigest(),legacy_executor_note='Sealed executor historical authorization wording says8/1.50; current wrapper enforces two cases and0.16. JSON-mode wire included and matches production. No old unknown/user call retried.')
 executor.dump(HERE/'paid-summary.json',summary)
 return code

if __name__=='__main__':
 if sys.argv[1:]==['--prepare']:prepare()
 elif sys.argv[1:]==['--execute']:sys.exit(execute())
 else:raise SystemExit('Use --prepare offline or --execute once')
