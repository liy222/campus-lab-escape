"""Independent read-only consistency review of actual finite A28 game evidence."""
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
CLEAN=ROOT/'data/reproduction/A28-junction-20261006/clean'
COPY=ROOT/'evidence/integration/A28-real-20261006'
def forbidden(*args,**kwargs):raise AssertionError('NO_QA_NETWORK_OR_DATABASE')
socket.socket.connect=forbidden
socket.create_connection=forbidden
sqlite3.connect=forbidden
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

def main():
    out=ROOT/('evidence/qa/A28-real-result-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));out.mkdir()
    checks,before=[],{}
    def check(name,value):checks.append({'name':name,'passed':bool(value)})
    def read(p):
        before[p.relative_to(ROOT).as_posix()]=sha(p)
        return load(p)
    index=read(COPY/'index.json');process=read(ROOT/'evidence/integration/A28-junction-real-process-20261006.json')
    origin=Path(index['original']);data={}
    for name,pin in index['files'].items():
        data[name]=read(COPY/name);read(origin/name)
        check('exact-copy:'+name,sha(COPY/name)==sha(origin/name)==pin)
    run,exchanges,trace,observations=[data[n]for n in ('run.json','http-exchanges.json','public-runtime-trace.json','checks.json')]
    check('actual-Main-command-exit',index['actual_tool_completion_chunk']=='6c6318' and index['actual_exit_code']==process['process_exit_code']==run['exit_code']==0 and run['status']==process['actual_result_status']=='PASS')
    check('candidate-source-cwd',process['candidate_commit']==index['candidate_commit']=='833aafb09ad20dc1ba82cfed198485ce13300067' and Path(process['clean'])==CLEAN and origin.is_relative_to(CLEAN) and process['command'][1:6]==['-B','-X','utf8','-m','tests.real_m3_runner'])
    check('run-hash-and-started',sha(COPY/'run.json')==process['run_sha256'] and process['process_started'] is True)
    check('63-collected-source-before-after',len(run['source_sha256_before'])==63 and run['source_sha256_before']==run['source_sha256_after'])
    current_sources={}
    for name,pin in run['source_sha256_before'].items():
        p=CLEAN/name;digest=sha(p);before[p.relative_to(ROOT).as_posix()]=digest;current_sources[name]=digest
        check('actual-clean-current-source:'+name,digest==pin)
    root_pins={}
    for name,pin in process['sources_before'].items():
        p=ROOT/name;digest=sha(p);before[name]=digest;root_pins[name]=digest
        check('11-Root-clean-source:'+name,digest==pin==current_sources[name]==process['sources_after'][name])
    check('11-actual-identity-bindings',len(root_pins)==11)
    ledger=ROOT/'data/ai-budget.sqlite';alias=CLEAN/'data/ai-budget.sqlite'
    check('physical-canonical-ledger-metadata',alias.resolve(strict=True)==ledger.resolve(strict=True) and os.path.samefile(alias,ledger) and process['runtime_link_resolves_to_original'] is True and run['canonical_ledger']==str(ledger))
    old=read(ROOT/'evidence/integration/A28-real-fresh-process-20261006.json')
    check('original-zero-call-blocker-preserved',old['actual_paid_calls']==0 and old['process_started'] is False and old['process_exit_code']==1 and sha(ROOT/'evidence/integration/A28-real-fresh-process-20261006.json')=='d0963248437b1ebb9d5c46377be8498c3c61c487d1f947644c9b76bffd8d5a85')
    provider=[e for e in trace if e['kind']=='provider_result']
    ledger_before,ledger_after=run['ledger_before'],run['ledger_after']
    initial_ids={x['call_id']for x in ledger_before['calls']}
    added=[x for x in ledger_after['calls'] if x['call_id']not in initial_ids]
    check('two-real-call-bindings',len(added)==len(provider)==run['actual_provider_attempts']==process['actual_paid_calls']==index['actual_paid_calls']==2 and {x['call_id']for x in added}=={x['call_id']for x in provider}=={x['call_id']for x in run['actual_new_ledger_rows']})
    check('canonical-snapshot-scope-and-cap',all(v['canonical_ledger']==str(ledger) and v['cap_units']==10_000_000_000 and not v['frozen']for v in (ledger_before,ledger_after)) and all(x['scope']=='game' and x['state']=='settled' and x['prompt_tokens'] is not None for x in added))
    check('finite-limit-records',run['AI_turns_max']==1 and run['provider_attempts_max']==process['maximum_calls']==3 and run['additional_cap_cny']==process['additional_upper_cap_cny']==.5 and 0<run['additional_conservative_charge_cny']<=.5 and run['additional_conservative_charge_cny']==process['additional_conservative_charge_cny'])
    check('recognized-real-model-and-usage',all(x['provider']=='deepseek' and x['requested_model']==x['reported_model']=='deepseek-flash' and x['usage']['total_tokens']==x['usage']['prompt_tokens']+x['usage']['completion_tokens']for x in provider))
    check('trace-real-tool-order',[e['kind']for e in trace]==['turn_started','provider_result','read_tool','provider_result','answer','turn_finished'] and provider[0]['finish_reason']=='tool_calls' and provider[1]['finish_reason']=='stop')
    read_tool=next(e for e in trace if e['kind']=='read_tool')
    check('inventory-tool-return',read_tool['tool']=='get_inventory' and read_tool['arguments']=={} and read_tool['ok'] is True and read_tool['observation']=='背包：空' and read_tool['revision']==2 and read_tool['new_clue_ids']==[])
    limits=trace[0]['limits']
    check('actual1000-20-no-retry-limits',limits['model_calls']==3 and limits['output_tokens']==1000 and limits['call_seconds']==20 and limits['format_retries']==0 and limits['progress_proposals']==1)
    check('six-successful-http-exchanges',len(exchanges)==6 and all(x['http_status']==200 and x['response']['ok']for x in exchanges))
    first,second,turn,replayed,confirm,again=exchanges
    check('two-public-inspections',first['request']['tool']==second['request']['tool']=='inspect' and first['request']['arguments']=={'object_id':'r1_note'} and second['request']['arguments']=={'object_id':'r1_cabinet'} and second['response']['data']['visible_state']['revision']==2)
    t1,t2=[e['response']['data']for e in (turn,replayed)]
    check('one-AI-turn-replayed',turn['path']==replayed['path']=='ai/turns' and turn['request']==replayed['request'] and t1==t2 and t1['status']=='completed' and t1['stop_reason'] is None)
    check('tool-usage-agrees',t1['usage']==trace[-1]['usage'] and t1['usage']['model_calls']==2 and t1['usage']['read_tool_calls']==1 and t1['usage']['input_tokens']==sum(e['usage']['prompt_tokens']for e in provider) and t1['usage']['output_tokens']==sum(e['usage']['completion_tokens']for e in provider))
    proposal=t1['proposal'];state=t1['visible_state']
    check('progress-pending-only',proposal['status']=='pending' and proposal['tool']=='submit_code' and proposal['arguments']=={'target_id':'r1_cabinet','code':'382'} and state['revision']==proposal['revision']==2 and state['inventory']==[] and state['level_version']=='2.0.0')
    known={c['clue_id']for c in state['clues']}
    check('proposal-public-clue-binding',set(proposal['clue_refs'])==known=={'r1_note_clue','r1_cabinet_clue'} and set(t1['clue_refs'])<=known)
    check('no-hidden-answer-in-input-request',all(code not in turn['request']['message']for code in ('382','724','231')) and hashlib.sha256(turn['request']['message'].encode()).hexdigest()==trace[0]['message_sha256'])
    c1,c2=[e['response']['data']for e in (confirm,again)]
    receipt=c1['receipt']
    check('confirmation-once',confirm['path']==again['path']==f"proposals/{proposal['proposal_id']}/confirm" and c1['replayed'] is False and c1['proposal']['status']=='committed' and receipt['revision_before']==2 and receipt['revision_after']==3 and receipt['request_id']==proposal['proposal_id'] and receipt['changed'] is True)
    check('confirmation-replay-same-receipt-state',c2['replayed'] is True and c2['receipt']==receipt and c2['visible_state']==c1['visible_state'] and c2['visible_state']['revision']==3 and confirm['response']['event_id']==again['response']['event_id']==receipt['event_id'])
    check('checks-and-global-no-new-replay-call',len(observations)==1 and observations[0]['AI_turns']==1 and observations[0]['provider_attempts']==2 and observations[0]['replays_no_new_provider'] is True and observations[0]['proposal']==proposal and observations[0]['confirm_receipt']==receipt and len(added)==2)
    secret_fields=[]
    def scan(value,path=''):
        if isinstance(value,dict):
            for k,v in value.items():
                if k.lower()in {'api_key','model_api_key','authorization','x-session-token','token'} and v not in ('[REDACTED]',None,''):secret_fields.append(path+'.'+k)
                scan(v,path+'.'+k)
        elif isinstance(value,list):
            for i,v in enumerate(value):scan(v,path+f'[{i}]')
    for name,value in data.items():scan(value,name)
    check('no-secret-fields-in-sanitized-artifacts',not secret_fields)
    check('human-and-teacher-unapproved',index['human_signoff'] is None and index['teacher_approval'] is None)
    after={p:sha(ROOT/p)for p in before}
    check('independent-all-read-source-STOP',before==after)
    failures=[x['name']for x in checks if not x['passed']]
    result={'kind':'A28-independent-actual-real-review','at_utc':datetime.now(timezone.utc).isoformat(),'command':[sys.executable,'-B','-X','utf8','tests/review_a28_real_result.py'],'exit_code':int(bool(failures)),'checks':checks,'failures':failures,'source_before':before,'source_after':after,'current63_clean_sources':current_sources,'current11_Root_sources':root_pins,'actual_Main_command':index['actual_command'],'actual_Main_chunk':index['actual_tool_completion_chunk'],'actual_Main_exit_code':0,'candidate_commit':index['candidate_commit'],'real_AI_turns':1,'actual_paid_calls_by_Main':2,'paid_calls_by_QA':0,'recorded_segment_upper_cny':run['additional_conservative_charge_cny'],'human_signoff':None,'teacher_approval':None,'source_STOP':not failures,'limits':['Controlled known-R1 segment, first inventory call forced; not autonomous whole-game or human gameplay.','Actual module paths inferred from clean cwd, cleared PYTHONPATH/PYTHONHOME and fresh -m startup plus sourcecollector; no separate runtime __file__ inventory was recorded.','Sanitized artifacts omit full outbound prompt/raw provider envelope; public request/clues and server trace are verified, not fresh packet capture.','No live database or env read, model request, regression, paid evaluation or original evidence modification by QA.']}
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'evidence':str(out),'exit_code':result['exit_code'],'checks':len(checks),'failures':failures,'sources':len(before),'actual_Main_paid':2,'QA_paid':0},ensure_ascii=False))
    return result['exit_code']

if __name__=='__main__':sys.exit(main())
