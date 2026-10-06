"""Read-only actual-result QA. Not source certification; no target imports or DB access."""
import argparse,hashlib,json
from pathlib import Path
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[1]
arg=argparse.ArgumentParser();arg.add_argument('--output',required=True);args=arg.parse_args()
OUT=ROOT/args.output;OUT.mkdir(parents=True,exist_ok=False)
sha=lambda b:hashlib.sha256(b).hexdigest();pins={};checks=[]
def read(n):
    raw=(ROOT/n).read_bytes();pins[n]=sha(raw);return json.loads(raw)
def check(n,v):checks.append({'name':n,'passed':bool(v)})
preview=read('evidence/integration/revised-evaluation-payload-preview-20261006.json')
human=read('evidence/integration/revised-evaluation-human-approved-20261006.json')
gaterecord=read('evidence/integration/revised-evaluation-gates-20261006.json')
gates=read('evaluation/trusted/paid-gates.json')
cases=read('evaluation/fixtures/cases.json')['cases'];casebyid={c['case_id']:c for c in cases}
schema=read('evaluation/schemas/suggestion.schema.json');outputschema=read('evaluation/schemas/output.schema.json')
oldqa=read('evidence/qa/T27-remaining-20261006T002000Z/result.json')
oldprior=read('evaluation/runs/20261005T120430742113Z/report.json')
oldauth=read('evidence/integration/remaining-evaluation-human-authorized-20261005.json')
oldprocess=read('evidence/integration/paid-evaluation-K1K6-20261005T110203Z-process.json')
expectedoldgates=[oldprocess['gate']]+[j['gate'] for j in oldauth['jobs']]
check('approval exact8/pin/sum',human['human_reply_exact']==gaterecord['human_reply_exact']=='批准这 8 项新版评价载荷外发' and human['maximum_requests']==gaterecord['maximum_new_requests']==len(preview['requests'])==8 and human['preview_raw_sha256']==gaterecord['preview_raw_sha256']==pins['evidence/integration/revised-evaluation-payload-preview-20261006.json']=='43c4a515c4570a2f5fdb3e383c44b09d2a3ef6f60d1be2877953d386cb15d30f')
check('old4 gate tuples preserved/new3append',gates['approvals'][:4]==expectedoldgates and gates['approvals'][4:]==[j['gate'] for j in gaterecord['jobs']] and len(gates['approvals'])==7)
check('finite sum3+2+3',[j['gate']['max_calls'] for j in gaterecord['jobs']]==[3,2,3] and sum(r['reservation_units'] for r in preview['requests'])==gaterecord['reservation_sum_units']==2181664000)
check('original cap only / snapshot not liveDB',gaterecord['budget_before']=={'calls':93,'charged_upper_units':668423280,'original_cap_units':10000000000} and 668423280+2181664000<10000000000)
old_ids={a['provider_metadata']['call_id'] for a in oldprior['audits'] if a['provider_metadata']}|set(oldqa['call_ids'])
for n,h in oldqa['input_sha256_before_after'].items():check('old immutable '+n,sha((ROOT/n).read_bytes())==h)
all_pairs=[];reports=[];source14=None
for prefix,run,count in [('Kfix','20261006T043749352975Z',3),('E1fix','20261006T043806611760Z',2),('CHfix','20261006T043822902164Z',3)]:
    report=read('evaluation/runs/'+run+'/report.json');reports.append(report)
    proc=read('evidence/integration/paid-evaluation-'+prefix+'-20261006T043737Z-process.json')
    gate=next(j['gate'] for j in gaterecord['jobs'] if j['gate']['approval_id'].startswith(prefix+'-'))
    normalized={Path(n).name:h for n,h in proc['evaluator_source_before'].items()}
    if source14 is None:source14=normalized
    check(prefix+' actual0/program command/boundrun',type(proc['actual_exit_code']) is int and proc['actual_exit_code']==report['exit_code']==0 and proc['new_run_directories']==['evaluation\\runs\\'+run] and proc['command'][1:4]==['-B','-X','utf8'])
    check(prefix+' gate actualfinite3/2/3',proc['gate']==gate and report['actual_paid_calls']==count==gate['max_calls'] and gate['max_tokens']==1000 and gate['timeout_seconds']==20)
    check(prefix+' source14 exact unchanged/newversion',len(normalized)==14 and normalized==source14==report['evaluator_source_sha256'] and proc['evaluator_source_before']==proc['evaluator_source_after'] and proc['source_unchanged'] is True and normalized['engine.py']=='2e9778f186c8191a475db9fa359a06dea8725cd4733872c450bf261d0cbfb74c')
    check(prefix+' no target/human/teacher',report['target_code_executed'] is False and report['human_signoff'] is None and report['teacher_approval'] is None)
    paid=[a for a in report['audits'] if a['provider_metadata']]
    check(prefix+' unique sequential IDs',[a['provider_metadata']['call_id'] for a in paid]==['eval_'+gate['approval_id']+'_'+str(i) for i in range(1,count+1)])
    if prefix=='Kfix':
        check('11 original expected recomputed',len(report['results'])==len(report['audits'])==len(cases)==11 and all(r['expected']==casebyid[r['case_id']]['expected']==r['actual'] and r['matches_expected'] is True for r in report['results']))
        check('11matching metrics no falsePASS/wrongFAIL/abstention',report['calibration']['case_count']==report['calibration']['matches']==11 and all(report['calibration'][k]==[] for k in ['false_pass','wrong_failure','unnecessary_abstention']))
        check('paid3 separate deterministic8',len(paid)==3 and [a['case_id'] for a in paid]==['K1-real-valid-evidence','K2-explicit-failure','K4-failure-with-injection'] and sum(a['provider_metadata'] is None for a in report['audits'])==8)
        results={r['case_id']:r['output'] for r in report['results']}
        all_pairs.extend((a,results[a['case_id']]) for a in paid)
        k4=next(a for a in paid if a['case_id']=='K4-failure-with-injection')
        check('K4 deterministicFAIL not waived',results[k4['case_id']]['status']=='FAIL' and k4['raw_suggestion']['status']=='FAIL' and set(k4['deterministic']['failures'])=={'NONZERO_EXIT:calibration_v1:F004','ASSERTION_FAILURE:calibration_v1:F004'})
        check('fixture inputhash unchanged',gate['input_sha256']==report['fixture_set_sha256']==sha((ROOT/'evaluation/fixtures/cases.json').read_bytes()))
    else:
        check(prefix+' full PASScount not retry oldresult',len(report['results'])==count and all(r['status']=='PASS' and a['validation_errors']==[] for r,a in zip(report['results'],report['audits'])))
        check(prefix+' eventfreeze/input remains registered',gate['input_sha256']==report['event']['event_freeze_raw_sha256'] and report['event_final_precheck']['issues']==[])
        all_pairs.extend(zip(report['audits'],report['results']))
for i,(row,(audit,result)) in enumerate(zip(preview['requests'],all_pairs),1):
    payload=row['payload'];body=json.loads(payload['messages'][1]['content']);md=audit['provider_metadata'];u=md['usage']
    check(str(i)+' approved preview exact serialization/claim',sha(json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode())==row['wire_sha256'] and row['claim_id']==audit['claim_id']==result['claim_id'])
    check(str(i)+' actual knownusage cost cache arithmetic',md['actual_network_call'] is True and all(type(u[k]) is int and u[k]>=0 for k in ['prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens']) and u['prompt_tokens']+u['completion_tokens']==u['total_tokens'] and u['prompt_cache_hit_tokens']<=u['prompt_tokens'] and md['cost_upper_units']==(u['prompt_tokens']-u['prompt_cache_hit_tokens'])*2000+u['prompt_cache_hit_tokens']*40+u['completion_tokens']*8000 and u['completion_tokens']<=1000)
    suggestion=audit['raw_suggestion'];validsuggestion=not list(Draft202012Validator(schema).iter_errors(suggestion));validoutput=not list(Draft202012Validator(outputschema).iter_errors(result))
    allowed={(r['evidence_id'],r['snippet']) for r in body['TRUSTED_OUTPUT_CONTRACT']['allowed_citations']}
    expectedrefs={ (e['reference']['evidence_id'],e['reference']['snippet']):e['reference'] for e in body['TARGET_DATA']['evidence'] }
    check(str(i)+' strict valid audited schema/refs',validsuggestion and validoutput and audit['validation_errors']==[] and all((r['evidence_id'],r['snippet']) in allowed for r in suggestion['evidence_refs']) and all(expectedrefs.get((r['evidence_id'],r['snippet']))==r for r in result['evidence_refs']))
    check(str(i)+' digest only valid content metadata/scope',len(audit['raw_suggestion_sha256'])==64 and audit['raw_suggestion_size_bytes']>0 and result['execution_scope']['actual_model_requests_this_claim']==1 and result['execution_scope']['target_execution']=='none; existing evidence read only' and result['human_signoff'] is None and result['human_signoff_status']=='pending')
ids=[a['provider_metadata']['call_id'] for a,r in all_pairs]
check('exact8 distinct no oldIDs reused',len(ids)==len(set(ids))==8 and not set(ids)&old_ids)
check('historical10/11 preserved',oldprior['actual_paid_calls']==2 and oldprior['calibration']['matches']==10 and oldprior['calibration']['case_count']==11)
check('historical5INSUF kept distinct',oldqa['statuses']==['FAIL']+['INSUFFICIENT_EVIDENCE']*5)
check('all report/process/approval byte stable',all(sha((ROOT/n).read_bytes())==h for n,h in pins.items()))
check('current14 still matches actualrun snapshot',{p.name:sha(p.read_bytes()) for p in (ROOT/'evaluation').glob('*.py')}==source14)
result={'checks':len(checks),'passed':sum(c['passed'] for c in checks),'failed':[c for c in checks if not c['passed']],'actual_new_paid_calls_observed':8,'call_ids':ids,'known_usage_cost_units':sum(a['provider_metadata']['cost_upper_units'] for a,r in all_pairs),'source14':source14,'input_hashes_before_after':pins,'limits':['Result-only independent read/hash audit; engine source independent acceptance belongs to qa_ch01, not this agent.','No live ledger/env/model/network/Git/target code import or execution; totals do not independently establish current ledger state.','Generic reports preserve approved preview and pinned source semantics, not an actual HTTP packet capture/wire digest.','11/11 calibration matches include3 paid model calls and8 deterministic fixtures; not11 paid completions or general-language calibration.','E1 PASS concerns registered original stopped22complete/1timeout/49notcalled materials, not merged69 outcomes or72successful model requests.','CH01 PASS concerns scripted engineering evidence, not natural autonomy/fullgame/teacher grade/human signoff.','Newversion calls are explicitly separately approved; old failure/privacy metadata and outcome hashes remain immutable.']}
(OUT/'checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'checks':result['checks'],'passed':result['passed'],'failed':result['failed'],'result_sha256':sha((OUT/'result.json').read_bytes()),'known_usage_cost_units':result['known_usage_cost_units']},ensure_ascii=False))
raise SystemExit(0 if not result['failed'] else 1)
