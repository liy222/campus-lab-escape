"""Four new targeted samples; reuse sealed real production-path executor, no retries."""
from pathlib import Path
from datetime import datetime, timezone
import importlib.util
import json
import hashlib
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SEALED = ROOT/'evidence/integration/ai-companion-real/run_playtest.py'
spec = importlib.util.spec_from_file_location('sealed_real_playtest', SEALED)
executor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(executor)
executor.OUT = HERE/'paid'
executor.LIMIT = 0.30
executor.CASES = [
 ('Q01',10,'cabinet_scope','柜门仍合着，但刚才输入后绿灯亮了。这说明什么？是不是只有柜子能继续观察？'),
 ('Q02',10,'followup','刚才还是没明白：灯亮和柜门打开有什么区别，为什么这能说明不用继续猜数字？'),
 ('Q03',23,'circuit','线路有点乱，我不知道该怎么判断两块能不能连上。请只讲一个局部检查方法，不给旋转步骤。'),
 ('Q04',40,'login_done','我已经登录了，屏幕没再要求输入信息。现在是还要解密码，还是应该换一种观察方式？'),
]


def prepare():
 from backend.app.ai.companion import SYSTEM,build_companion_context,provider_companion_context
 executor.OUT.mkdir(exist_ok=True)
 previews=[]
 for cid,n,kind,question in executor.CASES:
  history=() if kind!='followup' else ({'kind':'dialogue','question':executor.CASES[0][3],'answer':'[Execution uses only actual accepted Q01 answer, last 360 characters]','clue_refs':[]},)
  state=executor.projection(n)
  context=provider_companion_context(build_companion_context(state,question,history),state)
  body=executor.request_body([{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps(context,ensure_ascii=False)}])
  previews.append({'case_id':cid,'kind':kind,'legal_route_prefix':n,'body':body,'offline_bound_cny':executor.bound(body)})
 plan={'recorded_at':datetime.now(timezone.utc).isoformat(),'authorization':'User requested paid model quality playtesting then correction; targeted validation within original approved CNY10.','endpoint':'https://api.deepseek.com/chat/completions','model':'deepseek-flash','baseline_source_sha256':executor.source_map(),'executor_sha256':hashlib.sha256(SEALED.read_bytes()).hexdigest(),'maximum_real_calls':4,'round_limit_cny':0.30,'no_retries':True,'cases':previews,'limits':['Four new scenario samples; not statistical proof or a human UI playthrough.','Q02 includes actual accepted Q01 reply and is skipped if Q01 is stopped.','No old requests or unknown calls replayed.']}
 executor.dump(executor.OUT/'payload-preview.json',plan)
 print(json.dumps({'preview':str(executor.OUT/'payload-preview.json'),'maximum_calls':4,'reservation_upper_cny':sum(x['offline_bound_cny'] for x in previews)},ensure_ascii=False))


def execute():
 plan=json.loads((executor.OUT/'payload-preview.json').read_text(encoding='utf-8'))
 assert not list(executor.OUT.glob('*-real')),'One execution only; no replay'
 assert hashlib.sha256(SEALED.read_bytes()).hexdigest()==plan['executor_sha256']
 assert len(executor.CASES)==plan['maximum_real_calls']==4
 assert executor.LIMIT==plan['round_limit_cny']==0.30
 code=executor.execute()
 results=list(executor.OUT.glob('*-real/result.json'))
 assert len(results)==1
 result=json.loads(results[0].read_text(encoding='utf-8'))
 assert result['actual_provider_dispatches']<=4
 summary={key:result[key] for key in ('recorded_at','source_sha256','source_matches_prepared','original_cap_cny','round_limit_cny','before_budget','after_budget','actual_provider_dispatches','actual_charged_cny','historical_unknown_retried','new_unknown_count','stopped_reason','limitations')}
 summary.update(authorization=plan['authorization'],maximum_real_calls=4,result_path=results[0].relative_to(ROOT).as_posix(),result_sha256=hashlib.sha256(results[0].read_bytes()).hexdigest(),executor_sha256=plan['executor_sha256'],executor_exit_code=code,legacy_executor_note='Original sealed executor result contains its historical broader <=8/1.50 authorization wording; this wrapper enforces four cases and 0.30 round limit. The new result actual counts and budget fields are authoritative.')
 executor.dump(HERE/'paid-summary.json',summary)
 return code


if __name__=='__main__':
 if sys.argv[1:]==['--prepare']:prepare()
 elif sys.argv[1:]==['--execute']:sys.exit(execute())
 else:raise SystemExit('Use --prepare offline or --execute paid once')
