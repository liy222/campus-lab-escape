"""Read-only six-result audit. No imports from target, ledger, credentials or network."""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
inputs={}
def read(name):
    p=ROOT/name; raw=p.read_bytes();inputs[name]=sha(raw)
    return json.loads(raw)
checks=[]
def check(name,ok,detail=None): checks.append({'name':name,'passed':bool(ok),'detail':detail})
preview=read('evidence/integration/remaining-evaluation-payload-preview-20261005.json')
auth=read('evidence/integration/remaining-evaluation-human-authorized-20261005.json')
k4=read('evidence/integration/remaining-k4-20261005.json')
started=read('evidence/integration/remaining-k4-20261005-started.json')
prior=read('evaluation/runs/20261005T120430742113Z/report.json')
correction=read('evidence/integration/remaining-preparation-correction-20261006.json')
oldk4=next(a for a in prior['audits'] if a['case_id']==k4['case_id'])
check('exact human reply and preview binding',auth['human_reply_exact']=='批准这6个评价载荷外发' and auth['preview_raw_sha256']==inputs['evidence/integration/remaining-evaluation-payload-preview-20261005.json'])
check('finite six preview / 1+2+3 gates',preview['maximum_requests']==auth['maximum_new_requests']==6 and [j['gate']['max_calls'] for j in auth['jobs']]==[1,2,3])
check('preview zero dispatch/credentials/ledger',all(preview[k]==0 for k in ['network_calls','gate_mutations','ledger_reads_or_writes']) and preview['credentials_included'] is False)
check('exact six ordered claims',[r['claim_id'] for r in preview['requests']]==['A22','E1-formal-review-v2:A24','E1-formal-review-v2:A26','CH01-adversarial-review-v3:A27','CH01-adversarial-review-v3:A21','CH01-adversarial-review-v3:A23'])
check('finite reservation total/cap',sum(r['reservation_units'] for r in preview['requests'])==auth['reservation_sum_units']==preview['reservation_sum_units']==1884048000 and preview['original_project_cap_cny']==10)
check('preparation failure retained without mutation',correction['initial_exit_code']==1 and correction['initial_gate_or_network_mutations']==0 and correction['corrected_exit_code']==0)
sources=k4['evaluator_sources_before']
check('K4 source14 stable',len(sources)==14 and sources==k4['evaluator_sources_after'] and k4['source_unchanged'] is True)
check('K4 once prior actual nevercalled',oldk4['provider_metadata'] is None and oldk4['validation_errors']==['PRIOR_CALL_UNKNOWN_STOP'] and k4['previous_k4_network_calls']==0)
check('K4 precall started matches result',all(k4[k]==v for k,v in started.items()) and started['created_at']<k4['ended_at'])
check('K4 actualpaid1/validFAIL/exit0',k4['actual_paid_calls']==1 and k4['result']['status']==k4['expected']=='FAIL' and k4['exit_code']==0 and k4['audit']['validation_errors']==[])
check('K4 read ref exact',[{'evidence_id':r['evidence_id'],'snippet':r['snippet']} for r in k4['result']['evidence_refs']]==[{'evidence_id':'calibration_v1:F004','snippet':'summary'}])
check('K4 deterministic dominance preserved',set(k4['audit']['deterministic']['failures'])=={'NONZERO_EXIT:calibration_v1:F004','ASSERTION_FAILURE:calibration_v1:F004'} and k4['audit']['raw_suggestion']['status']=='FAIL')
all_audits=[k4['audit']]; all_results=[k4['result']]
for job,run,count,errs in [('E1-formal-review-v2','20261005T155830386817Z',2,['MODEL_FAKE_OR_UNREAD_REFERENCE','MODEL_SCHEMA_OR_PROVIDER_ERROR']),('CH01-adversarial-review-v3','20261005T155947272680Z',3,['MODEL_FAKE_OR_UNREAD_REFERENCE','MODEL_FAKE_OR_UNREAD_REFERENCE','MODEL_INVALID_OUTPUT'])]:
    report=read('evaluation/runs/'+run+'/report.json')
    gate=next(j['gate'] for j in auth['jobs'] if j['job']==job)
    process=read('evidence/integration/paid-evaluation-'+gate['approval_id']+'-process.json')
    before={Path(p).name:h for p,h in process['evaluator_source_before'].items()}
    after={Path(p).name:h for p,h in process['evaluator_source_after'].items()}
    check(job+' actual programexit2',type(process['actual_exit_code']) is int and process['actual_exit_code']==report['exit_code']==2)
    check(job+' exact gate and freeze',gate==process['gate'] and gate['input_sha256']==report['event']['event_freeze_raw_sha256'] and gate['max_calls']==count)
    check(job+' source14 same oldversion',len(before)==14 and before==after==sources==report['evaluator_source_sha256'] and process['source_unchanged'] is True)
    check(job+' actual one process/bound directory',process['new_run_directories']==['evaluation\\runs\\'+run] and process['command'][1:4]==['-B','-X','utf8'] and process['command'][-1]==job)
    check(job+' actualpaid count/IDs',report['actual_paid_calls']==count and [a['provider_metadata']['call_id'] for a in report['audits']]==['eval_'+gate['approval_id']+'_'+str(i) for i in range(1,count+1)])
    check(job+' retained exact failures',[a['validation_errors'] for a in report['audits']]==[[e] for e in errs] and all(r['status']=='INSUFFICIENT_EVIDENCE' for r in report['results']))
    check(job+' strict checks zero/no target/no signature',report['event_final_precheck']['issues']==[] and report['target_code_executed'] is False and report['human_signoff'] is None and report['teacher_approval'] is None)
    check(job+' invalidraw never reflected/missing distinguished',all(a['raw_suggestion'] is None and ((a['validation_errors']==['MODEL_INVALID_OUTPUT'] and a['raw_suggestion_sha256'] is None and a['raw_suggestion_size_bytes'] is None) or (isinstance(a['raw_suggestion_sha256'],str) and len(a['raw_suggestion_sha256'])==64 and a['raw_suggestion_size_bytes']>0)) for a in report['audits']))
    all_audits+=report['audits'];all_results+=report['results']
for i,(row,audit,result) in enumerate(zip(preview['requests'],all_audits,all_results),1):
    payload=row['payload']; messages=payload['messages']; data=json.loads(messages[1]['content'])
    check(str(i)+' preview wireexact/params',sha(json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode())==row['wire_sha256'] and payload['model']=='deepseek-flash' and payload['max_tokens']==1000 and payload['thinking']=={'type':'disabled'} and payload['stream'] is False)
    check(str(i)+' preview trusted/target and exactclaim',set(data)=={'TRUSTED_RUBRIC','DETERMINISTIC_CHECKS','TARGET_DATA'} and data['TARGET_DATA']['claim']['claim_id']==row['claim_id']==result['claim_id'] and [m['role'] for m in messages]==['system','user'])
    md=audit['provider_metadata'];u=md['usage']
    check(str(i)+' actual knownusage arithmetic/cost',md['actual_network_call'] is True and all(type(u[k]) is int and u[k]>=0 for k in ['prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens']) and u['total_tokens']==u['prompt_tokens']+u['completion_tokens'] and u['prompt_cache_hit_tokens']<=u['prompt_tokens'] and md['cost_upper_units']>0)
    allowed={(x['reference']['evidence_id'],x['reference']['snippet']) for x in data['TARGET_DATA']['evidence']}
    check(str(i)+' final references read/hashbound/no falsePASS',all((r['evidence_id'],r['snippet']) in allowed and r['raw_equal'] is True and r['artifact_raw_sha256']==r['observed_raw_sha256'] for r in result['evidence_refs']) and result['status']!='PASS')
    check(str(i)+' pendinghuman/execution accurately one',result['human_signoff'] is None and result['human_signoff_status']=='pending' and result['execution_scope']['actual_model_requests_this_claim']==1 and result['execution_scope']['target_execution']=='none; existing evidence read only')
check('six unique calls/no K1 K2 replay',len({a['provider_metadata']['call_id'] for a in all_audits})==6 and not {a['provider_metadata']['call_id'] for a in all_audits}&{a['provider_metadata']['call_id'] for a in prior['audits'] if a['provider_metadata']})
check('K4 exact wire dispatch assertion',k4['wire_sha256']==preview['requests'][0]['wire_sha256'])
check('CH01 output1000 failure retained',all_audits[-1]['provider_metadata']['usage']['completion_tokens']==1000 and all_results[-1]['reason']=='MODEL_INVALID_OUTPUT')
check('K4 known usage/cache/cost',k4['audit']['provider_metadata']['usage']=={'prompt_tokens':961,'completion_tokens':142,'total_tokens':1103,'prompt_cache_hit_tokens':256} and k4['audit']['provider_metadata']['cost_upper_units']==2556240)
current={p.name:sha(p.read_bytes()) for p in (ROOT/'evaluation').glob('*.py')}
check('actual current oldsource still pinned14',current==sources)
for name,h in list(inputs.items()): check('immutable '+name,sha((ROOT/name).read_bytes())==h)
record={'checks':len(checks),'passed':sum(c['passed'] for c in checks),'failed':[c for c in checks if not c['passed']],'actual_paid_calls_observed':6,'statuses':[r['status'] for r in all_results],'call_ids':[a['provider_metadata']['call_id'] for a in all_audits],'known_usage_cost_units':sum(a['provider_metadata']['cost_upper_units'] for a in all_audits),'input_sha256_before_after':inputs,'source14_before_after':sources,'limits':['No ledger opened; 91-settled accounting is Main reported, not newly independently queried.','Generic E1/CH01 reports omit actual HTTP wire digests; preview semantics and source version are bound, but no independent packet capture is claimed. K4 exact wire assertion is recorded.','Four invalid content replies retain digest/size only. CH01 A23 provider-invalid output has neither digest nor size. No invalid body is independently rejudged.','No target/evaluator/provider code imported/executed, no paid calls, credentials, Git, network, or service.','No human signoff or general-language/full-game calibration; future prompt changes excluded.']}
(OUT/'checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'checks':record['checks'],'passed':record['passed'],'failed':record['failed'],'result_sha256':sha((OUT/'result.json').read_bytes())},ensure_ascii=False))
raise SystemExit(0 if not record['failed'] else 1)
