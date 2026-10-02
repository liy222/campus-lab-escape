"""Independent E1 prepilot QA. Synthetic transport only; never reads .env."""
from __future__ import annotations
import argparse, asyncio, contextlib, hashlib, json, os, sqlite3, subprocess, sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / 'experiments'

def hash_sources():
    paths = [p for d in ('experiments', 'backend', 'frontend/src', 'contracts', 'scripts')
             for p in (ROOT/d).rglob('*') if p.is_file() and not any(x in p.parts for x in
             ('runs', '.runtime', '__pycache__', 'node_modules', 'authorizations'))]
    paths += [ROOT/'frontend/package.json', ROOT/'frontend/package-lock.json', ROOT/'evidence/integration/baseline_v1-manifest.json']
    return {str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f: json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False)

def snapshot(ledger):
    with contextlib.closing(sqlite3.connect(ledger.path)) as db:
        db.row_factory=sqlite3.Row
        cap,frozen=db.execute('SELECT cap,frozen FROM budget_config WHERE id=1').fetchone()
        calls=[dict(r) for r in db.execute('SELECT * FROM budget_calls')]
    charged=sum(r['charged'] for r in calls)
    return dict(cap_units=cap,charged_units=charged,remaining_units=max(0,cap-charged),frozen=bool(frozen),calls=calls)

@contextlib.contextmanager
def isolate(out):
    import experiments.runner as r, experiments.summarize as s
    def inside(path):
        p=Path(path).resolve()
        if not p.is_relative_to(out.resolve()): raise ValueError('QA_OUTPUT_ESCAPE')
        return p
    def write(path,value):
        from experiments.common import encoded
        p=inside(path);p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(encoded(value)+b'\n')
    out.mkdir(parents=True,exist_ok=True)
    for name in ('fixtures','ground_truth'):
        (out/name).mkdir(exist_ok=True)
        for p in (EXP/name).glob('*.json'):(out/name/p.name).write_bytes(p.read_bytes())
    with patch.object(r,'HOME',out),patch.object(r,'inside',inside),patch.object(r,'write_new',write),patch.object(s,'inside',inside),patch.object(s,'write_new',write):
        yield r,s

def transport_cases(out, check):
    import httpx
    import backend.app.ai.provider as p
    from backend.app.ai.budget import BudgetLedger
    from experiments.plan import make_plan
    plan=make_plan('pilot'); original=p.DeepSeekProvider
    records=[]
    for name in ('401','403','429','503','connect_error','timeout','malformed_200','success'):
        work=out/name
        with isolate(work) as (r,s):
            ledger=BudgetLedger(work/'fake-budget.sqlite')
            calls=[]
            def fake(request):
                calls.append({'request_sha256':hashlib.sha256(request.content).hexdigest()})
                journal=(directory/'journal.jsonl').read_text(encoding='utf-8')
                check(name+'_journal_before_transport', 'invocation_started' in journal)
                if name=='connect_error':raise httpx.ConnectError('synthetic',request=request)
                if name=='timeout':raise httpx.ReadTimeout('synthetic',request=request)
                if name.isdigit():return httpx.Response(int(name),json={'error':'synthetic'})
                if name=='malformed_200':return httpx.Response(200,content=b'{broken')
                return httpx.Response(200,json={'model':'deepseek-flash','choices':[{'finish_reason':'stop','message':{'role':'assistant','content':r.mock_content('C02')}}], 'usage':{'prompt_tokens':10,'completion_tokens':5,'total_tokens':15,'prompt_cache_hit_tokens':0}})
            config=p.DeepSeekConfig('synthetic-not-a-credential')
            def factory(_):return original(config,ledger,transport=httpx.MockTransport(fake))
            directory=r.new_run(plan,'synthetic-transport')
            with patch.object(p.DeepSeekConfig,'from_environment',return_value=config),patch.object(p,'DeepSeekProvider',factory),patch.object(r,'ledger_read',side_effect=lambda:snapshot(ledger)):
                rows=asyncio.run(r.execute(plan,directory,'real',{'additional_upper_cap_units':1_000_000_000}))
            summary=s.summarize(directory)
            rec={'case':name,'synthetic_only':True,'network_calls':0,'actual_paid_calls':0,'transport_invocations':len(calls),'rows':rows,'summary':summary,'fake_ledger':snapshot(ledger)}
            records.append(rec)
            first=rows[0]
            if name in ('401','403','429','503','malformed_200'):
                check(name+'_response_received',first['response_received'] is True,first['response_received'])
                check(name+'_delivery_known',first['upstream_delivery_known'] is True,first['upstream_delivery_known'])
            elif name in ('connect_error','timeout'):
                check(name+'_response_unknown',first['response_received'] is None,first['response_received'])
                check(name+'_delivery_unknown',first['upstream_delivery_known'] is None)
            if name!='success':check(name+'_no_resend',len(calls)==1 and all(x['status']=='not_called' for x in rows[1:]))
            check(name+'_wire_hash',calls[0]['request_sha256']==plan['rows'][0]['input_hash'])
    dump(out/'transport-results.json',records)
    return records

def data_checks(out, check):
    from experiments.common import load,encoded,sha,baseline_binding
    from experiments.context import pack,unpack,build,facts
    import experiments.plan as p
    from experiments.judger import judge
    from backend.app.domain.models import GameState
    from backend.app.domain.rules import apply_action,visible_state,CLUES
    from jsonschema import Draft202012Validator
    binding=baseline_binding()
    check('approved_manifest_raw',binding['manifest_raw_sha256']=='9c36943cbb6e4fe08b6e176445ba91835fafa79a2077c2155bbf8d613f8b07c1')
    check('approved_baseline_cardinality',len(binding['sources'])==60 and len(binding['artifacts'])==14 and len(binding['unbound_prior_source_records'])==6)
    expected={
      'C01':[('inspect',{'object_id':'r1_note'}),('inspect',{'object_id':'r1_cabinet'})],
      'C02':[('inspect',{'object_id':'r1_cabinet'})],
      'C03':[('submit_code',{'target_id':'r1_cabinet','code':'382'})],
      'C04':[('take',{'item_id':'access_card'})],
      'C05':[('use_item',{'item_id':'access_card','target_id':'r1_door'})],
      'C06':[('take',{'item_id':'fuse'}),('inspect',{'object_id':'r2_drawer'})],
      'C07':[('inspect',{'object_id':'r2_monitor'}),('inspect',{'object_id':'r2_drawer'})],
      'C08':[('submit_code',{'target_id':'r2_drawer','code':'724'})],
      'C09':[('take',{'item_id':'emergency_key'})],
      'C10':[('use_item',{'item_id':'emergency_key','target_id':'r2_door'})],
      'C11':[('inspect',{'object_id':'r3_panel'})],
      'C12':[('submit_code',{'target_id':'r3_panel','code':'231'})]}
    fixtures={}
    for sid,gold in expected.items():
        sample=load(EXP/'fixtures'/f'{sid}.json');fixtures[sid]=sample
        truth=load(EXP/'ground_truth'/f'{sid}.json')
        st=GameState(generation=sample['visible_state']['generation']);discovered=set()
        for j,event in enumerate(sample['visible_history']):
            st,res=apply_action(st,event['tool'],deepcopy(event['arguments']))
            check(sid+f'_prefix_{j}',all(event[k]==res[k] for k in ('observation','new_clue_ids','message')) and st.revision==event['revision'])
            discovered.update(res['new_clue_ids'])
            check(sid+f'_discovery_{j}',set(event['new_clue_ids'])<=set(st.discovered_clue_ids))
        check(sid+'_visible_exact_replay',visible_state('E1-synthetic',st)==sample['visible_state'])
        check(sid+'_offline_exact_replay',st.model_dump()==truth['state'])
        check(sid+'_independent_expected_gold',truth['acceptable_actions']==[dict(tool=t,arguments=a) for t,a in gold])
        check(sid+'_public_truth_binding',truth['public_sample_hash']==sha(sample))
        raw_before=sha(sample)
        def public_load(path):
            if 'ground_truth' in Path(path).parts or Path(path).name=='.env':raise AssertionError('PRIVATE_REQUEST_READ')
            return load(path)
        with patch.object(p,'load',side_effect=public_load):
            am,at,ah=p.input_for(sample,'full_history');bm,bt,bh=p.input_for(sample,'structured_summary')
        ac=json.loads(am[1]['content']);bc=json.loads(bm[1]['content'])
        check(sid+'_AB_exact_decode_facts',facts(ac)==facts(bc)==dict(visible_state=sample['visible_state'],message=sample['message'],visible_history=sample['visible_history']))
        check(sid+'_AB_only_representation',am[0]==bm[0] and at==bt and {k:v for k,v in ac.items() if k!='visible_history'}=={k:v for k,v in bc.items() if k!='visible_history_summary'})
        check(sid+'_summary_roundtrip',unpack(pack(sample['visible_history']))==sample['visible_history'])
        check(sid+'_input_no_private',all(x not in am[1]['content']+bm[1]['content'] for x in ('acceptable_actions','required_code_refs','ground_truth','opened_containers','discovered_clue_ids')))
        known=set(st.discovered_clue_ids)
        def semantics(v):
            if isinstance(v,dict):return {k:semantics(x) for k,x in v.items() if k not in ('generation','session_id')}
            if isinstance(v,list):return [semantics(x) for x in v]
            return v
        semantic=encoded(semantics(facts(ac))).decode()
        check(sid+'_no_undiscovered_clue_ids_or_text',all(cid not in semantic and clue['text'] not in semantic for cid,clue in CLUES.items() if cid not in known))
        if sid in ('C01','C02'):check(sid+'_no_unknown_full_code',all(code not in semantic for code in ('382','724','231')))
        if sid=='C07':check(sid+'_no_unknown_R2_R3_codes',all(code not in semantic for code in ('724','231')))
        if sid=='C11':check(sid+'_no_unknown_R3_code','231' not in semantic)
        refs=truth['required_code_refs']
        for tool,args in gold:
            result=judge(encoded(dict(answer='独立预期',clue_refs=refs,next_action=dict(tool=tool,arguments=args,clue_refs=refs,summary='独立下一步'))).decode(),sample)
            check(sid+'_'+tool+'_gold_judged',all(result[k] is True for k in ('parse_valid','legal','correct','reference_valid','reference_sufficient')))
        check(sid+'_judger_no_mutation',sha(sample)==raw_before)
    literal=[{'kind':'action','arguments':{'encoding':'e1-columns-v1','groups':[None],'indices':[2]},'observation':None}, {'kind':'ai_turn','answer':'null'}, {'kind':'action','observation':''}, {}, {'kind':'action','observation':None}, {'kind':'action','arguments':{'encoding':'e1-columns-v1','groups':[None],'indices':[2]},'observation':None}]
    check('literal_marker_nested_dictionary_collision_order_null_missing',unpack(pack(literal))==literal)
    check('empty_history',unpack(pack([]))==[])
    original=deepcopy(literal);packed=pack(literal);packed['groups'][0]['rows'][0][1]['groups'][0]='mutated'
    check('pack_is_deepcopy',literal==original)
    for name,edit in [('boolean_index',lambda x:x['groups'][0]['indices'].__setitem__(0,True)),('duplicate_index',lambda x:x['groups'][0]['indices'].__setitem__(1,0)),('duplicate_field',lambda x:x['groups'][0]['fields'].__setitem__(1,'kind')),('missing_record',lambda x:x.__setitem__('record_count',7)),('unknown_field',lambda x:x['groups'][0]['fields'].__setitem__(1,'hidden'))]:
        corrupted=pack(literal);edit(corrupted)
        try:unpack(corrupted)
        except ValueError:check('corrupt_summary_'+name,True)
        else:check('corrupt_summary_'+name,False)
    representatives=[('C01','inspect',{'object_id':'r1_note'}),('C01','get_inventory',{}),('C04','take',{'item_id':'access_card'}),('C05','use_item',{'item_id':'access_card','target_id':'r1_door'}),('C03','submit_code',{'target_id':'r1_cabinet','code':'382'}),('C06','move',{'destination_id':'R1'})]
    for sid,tool,args in representatives:
        value=dict(answer='独立',clue_refs=[],next_action=dict(tool=tool,arguments=args,clue_refs=[],summary='独立'))
        check(tool+'_schema_accepts',judge(encoded(value).decode(),fixtures[sid])['parse_valid'])
        for name,mutate in [('arg_extra',lambda v:v['next_action']['arguments'].update(hidden=1)),('proposal_extra',lambda v:v['next_action'].update(execute=True)),('top_extra',lambda v:v.update(state={})),('tool_unknown',lambda v:v['next_action'].update(tool='shell')),('refs_duplicate',lambda v:v.update(clue_refs=['x','x']))]:
            bad=deepcopy(value);mutate(bad)
            check(tool+'_reject_'+name,not judge(encoded(bad).decode(),fixtures[sid])['parse_valid'])
    sample=fixtures['C03'];value=dict(answer='独立',clue_refs=['r1_note_clue','r1_cabinet_clue'],next_action=dict(tool='submit_code',arguments={'target_id':'r1_cabinet','code':'382'},clue_refs=[],summary='独立'))
    v=judge(encoded(value).decode(),sample);check('answer_refs_not_proposal_sufficient',v['legal'] and v['correct'] and v['reference_valid'] and not v['reference_sufficient'])
    value['next_action']['clue_refs']=['unknown'];v=judge(encoded(value).decode(),sample)
    check('correct_independent_of_reference_existence',v['legal'] and v['correct'] and not v['reference_valid'] and not v['reference_sufficient'])
    inv=dict(answer='独立',clue_refs=[],next_action=dict(tool='get_inventory',arguments={},clue_refs=[],summary='独立'))
    v=judge(encoded(inv).decode(),fixtures['C01']);check('legality_distinct_from_usefulness',v['legal'] and not v['correct'])
    inv['next_action']=dict(tool='take',arguments={'item_id':'access_card'},clue_refs=[],summary='独立');v=judge(encoded(inv).decode(),fixtures['C01'])
    check('hidden_item_illegal',v['parse_valid'] and not v['legal'] and not v['correct'])
    check('strict_duplicate_JSON',not judge('{"answer":"a","answer":"b","clue_refs":[],"next_action":null}',fixtures['C01'])['parse_valid'])
    check('strict_nonfinite_JSON',not judge('{"answer":"a","clue_refs":[],"next_action":NaN}',fixtures['C01'])['parse_valid'])
    changed=deepcopy(fixtures['C01']);changed['message']='changed'
    try:judge(encoded(inv).decode(),changed)
    except ValueError:check('truth_mismatch_refuses',True)
    else:check('truth_mismatch_refuses',False)
    formal,pilot=p.make_plan('formal'),p.make_plan('pilot')
    check('formal_72_unique',len(formal['rows'])==72 and len({x['row_id'] for x in formal['rows']})==72)
    check('pilot_6_separate',len(pilot['rows'])==6 and not set(x['row_id'] for x in pilot['rows'])&set(x['row_id'] for x in formal['rows']))
    check('formal_balanced18AB18BA',sum(formal['rows'][i]['variant']=='full_history' for i in range(0,72,2))==18)
    for sid in expected:
        selected=[r for r in formal['rows'] if r['sample_id']==sid]
        check(sid+'_balanced_repeats',sorted((r['variant'],r['repeat']) for r in selected)==sorted((v,i) for v in ('full_history','structured_summary') for i in range(1,4)))
    check('planned_null_not_zero',all(r['status']=='not_called' and r['usage'] is None and r['response'] is None and r['charged_upper_cny'] is None and r['actually_called'] is False for r in formal['rows']))
    dump(out/'formal-plan.json',formal);dump(out/'pilot-plan.json',pilot)
    return formal,pilot

def lifecycle_checks(out,check,formal,pilot):
    from experiments.common import encoded,sha
    from unittest.mock import Mock
    import backend.app.ai.provider as provider
    with isolate(out) as (r,s):
        for name,plan,scenario in [('formal-success',formal,'success'),('pilot-mixed',pilot,'mixed')]:
            directory=r.new_run(plan,'mock')
            with patch.object(provider.DeepSeekConfig,'from_environment',side_effect=AssertionError('CREDENTIAL_READ')),patch.object(provider,'DeepSeekProvider',side_effect=AssertionError('PROVIDER_CONSTRUCTED')),patch.object(r,'ledger_read',side_effect=AssertionError('ORIGINAL_LEDGER_READ')):
                rows=asyncio.run(r.execute(plan,directory,'mock',scenario=scenario))
            summary=s.summarize(directory)
            check(name+'_all_rows_exact_identity',[x['row_id'] for x in rows]==[x['row_id'] for x in plan['rows']])
            check(name+'_null_fake_usage_cost',all(x['usage'] is None and x['charged_upper_cny'] is None and x['actually_called'] is False and not x['provider_invoked'] for x in rows))
            for variant in ('full_history','structured_summary'):
                group=summary['by_variant'][variant];selected=[x for x in rows if x['variant']==variant]
                check(name+'_'+variant+'_raw_denominators',group['planned']==len(selected) and group['completed']==sum(x['status']=='completed' for x in selected) and group['correct']==sum(x['correct'] is True for x in selected) and group['paid_attempts_confirmed']==0 and group['completed_per_paid_attempt'] is None and group['usage_known_rows']==0 and group['charged_upper_sum_known_cny'] is None)
            if scenario=='mixed':check('mixed_failure_retained',rows[0]['status']=='parse_invalid' and rows[1]['status']=='timeout' and rows[2]['reference_valid'] is False)
        directory=r.new_run(pilot,'plan')
        for row in pilot['rows']:r.append(directory/'raw.jsonl',row)
        check('plan_untouched_summary',s.summarize(directory)['row_count']==6)
        original=(directory/'raw.jsonl').read_bytes(); rows=deepcopy(pilot['rows']);rows.reverse();(directory/'raw.jsonl').write_bytes(b''.join(encoded(x)+b'\n' for x in rows))
        try:s.summarize(directory,output_name='bad-summary')
        except ValueError:check('summary_reorder_reject',True)
        else:check('summary_reorder_reject',False)
        (directory/'raw.jsonl').write_bytes(original)
        with patch.object(provider.DeepSeekConfig,'from_environment',side_effect=AssertionError('CREDENTIAL_READ')),patch.object(provider,'DeepSeekProvider',side_effect=AssertionError('PROVIDER_CONSTRUCTED')),patch.object(r,'ledger_read',side_effect=AssertionError('ORIGINAL_LEDGER_READ')),patch.object(sys,'argv',['experiments.runner','pilot','--mode','real']):
            try:r.main()
            except ValueError as e:check('no_gate_CLI_refuses_before_credential_provider_ledger',str(e)=='REAL_REQUIRES_SEPARATE_MAIN_GO')
            else:check('no_gate_CLI_refuses_before_credential_provider_ledger',False)
        interrupted=r.new_run(pilot,'synthetic-real-recovery')
        r.append(interrupted/'journal.jsonl',dict(event='invocation_started',at='2026-10-02T00:00:00+00:00',row_id=pilot['rows'][0]['row_id'],mode='real',experiment_ids_before=[]))
        call=dict(id='synthetic-known',scope='experiments',created_at='2026-10-02T00:00:01+00:00',reserved=100,charged=100,state='unknown',reason='SYNTHETIC',prompt_tokens=None,completion_tokens=None,cache_hit_tokens=None)
        snap=dict(calls=[call],cap_units=1000,charged_units=100,remaining_units=900,frozen=False)
        with patch.object(provider,'DeepSeekProvider',side_effect=AssertionError('REPLAY_PROVIDER')),patch.object(r,'ledger_read',side_effect=AssertionError('ORIGINAL_LEDGER_READ')):
            suffix=r.reconcile(interrupted,snap);recover=s.read_rows(interrupted/(suffix+'.jsonl'))
            check('crash_unique_reservation_not_delivery',len(recover)==6 and recover[0]['actually_called'] is True and recover[0]['response_received'] is None and recover[0]['upstream_delivery_known'] is None and recover[0]['usage'] is None and all(x['status']=='not_called' and x['response_received'] is False for x in recover[1:]))
            ambiguous={**snap,'calls':[call,{**call,'id':'synthetic-other'}]};suffix=r.reconcile(interrupted,ambiguous);recover=s.read_rows(interrupted/(suffix+'.jsonl'))
            check('crash_ambiguous_no_inferred_call',recover[0]['actually_called'] is None and recover[0]['call_id'] is None)
            check('unknown_summary_preserved',s.calculate(recover)['by_variant'][recover[0]['variant']]['paid_attempts_uncertain']==1)
        # OS lock, not an in-memory boolean: the child must fail while held.
        code="from pathlib import Path; from unittest.mock import patch; import experiments.runner as r; import sys\nroot=Path(sys.argv[1]); r.HOME=root; r.inside=lambda p:Path(p)\ntry:\n with r.exclusive(): print('acquired')\nexcept OSError: print('blocked'); sys.exit(21)"
        with r.exclusive():
            child=subprocess.run([sys.executable,'-B','-X','utf8','-c',code,str(out)],cwd=ROOT,capture_output=True,text=True)
        free=subprocess.run([sys.executable,'-B','-X','utf8','-c',code,str(out)],cwd=ROOT,capture_output=True,text=True)
        check('OS_lock_blocks_other_process',child.returncode==21 and child.stdout.strip()=='blocked')
        check('OS_lock_releases',free.returncode==0 and free.stdout.strip()=='acquired')
        dump(out/'lock-processes.json',dict(blocked_exit=child.returncode,blocked_stdout=child.stdout,free_exit=free.returncode,free_stdout=free.stdout))
        # Abrupt independent subprocess exit after durable journal/reservation,
        # before any HTTP construction. This is synthetic, not a real paid crash.
        crash=r.new_run(pilot,'synthetic-real-recovery')
        crash_code="""import os,sys,json
from pathlib import Path
from unittest.mock import patch
import experiments.runner as r
from backend.app.ai.budget import BudgetLedger
directory=Path(sys.argv[1]); ledger=BudgetLedger(Path(sys.argv[2])); plan=json.loads((directory/'plan.json').read_text(encoding='utf-8'))
with patch.object(r,'inside',lambda p:Path(p)):
 r.append(directory/'journal.jsonl',dict(event='invocation_started',at=r.now(),row_id=plan['rows'][0]['row_id'],mode='real',experiment_ids_before=[]))
 ledger.reserve('experiments',plan['rows'][0]['reservation_units'])
os._exit(19)
"""
        ledger_path=out/'crash-fake-budget.sqlite'
        child=subprocess.run([sys.executable,'-B','-X','utf8','-c',crash_code,str(crash),str(ledger_path)],cwd=ROOT,capture_output=True,text=True)
        from backend.app.ai.budget import BudgetLedger
        fake=BudgetLedger(ledger_path)
        raw_exists=(crash/'raw.jsonl').exists()
        with patch.object(provider,'DeepSeekProvider',side_effect=AssertionError('CRASH_REPLAY_PROVIDER')),patch.object(r,'ledger_read',side_effect=AssertionError('ORIGINAL_LEDGER_READ')):
            suffix=r.reconcile(crash,snapshot(fake));recovered=s.read_rows(crash/(suffix+'.jsonl'))
        check('actual_process_crash_exit19',child.returncode==19 and not raw_exists)
        check('actual_process_crash_reservation_no_resend',len(recovered)==6 and recovered[0]['actually_called'] is True and recovered[0]['usage'] is None and recovered[0]['response_received'] is None and fake.snapshot()['calls']==1)
        dump(out/'crash-process.json',dict(command=[sys.executable,'-B','-X','utf8','-c','<recorded crash_code in tests/review_e1.py>',str(crash),str(ledger_path)],exit_code=child.returncode,stdout=child.stdout,stderr=child.stderr,synthetic_only=True,network_calls=0,actual_paid_calls=0,rows=recovered))

def budget_checks(out,check,pilot):
    import httpx
    import backend.app.ai.provider as p
    from backend.app.ai.budget import BudgetLedger,CAP_UNITS
    from experiments.common import sha
    original=p.DeepSeekProvider
    for case in ('phase_includes_next_reservation','shared_remaining','shared_pending_start','shared_frozen_start'):
        work=out/case
        with isolate(work) as (r,s):
            ledger=BudgetLedger(work/'fake-budget.sqlite');calls=[]
            if case=='shared_remaining':ledger.reserve('game',CAP_UNITS-pilot['rows'][0]['reservation_units']+1)
            if case=='shared_pending_start':ledger.reserve('game',100)
            if case=='shared_frozen_start':ledger.freeze()
            def fake(request):
                calls.append(sha(request.content));bound=len(request.content)*4+8192
                return httpx.Response(200,json={'model':'deepseek-flash','choices':[{'finish_reason':'stop','message':{'role':'assistant','content':r.mock_content('C02')}}],'usage':{'prompt_tokens':bound,'completion_tokens':1000,'total_tokens':bound+1000,'prompt_cache_hit_tokens':0}})
            config=p.DeepSeekConfig('synthetic-not-a-credential')
            directory=r.new_run(pilot,'synthetic-budget')
            if case in ('shared_pending_start','shared_frozen_start'):
                pricing=work/'synthetic-price.json';price=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),peak_cny_per_million={'input_miss':2,'input_hit':.04,'output':8});dump(pricing,price)
                from datetime import timedelta
                gate=dict(approved_by='Main',approved=True,phase='pilot',freeze_hash=sha(pilot['freeze']),plan_hash=sha(pilot),max_calls=6,additional_upper_cap_units=1_000_000_000,id='SYNTHETIC_NOT_MAIN_APPROVAL',expires_at=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat(),pricing_evidence=str(pricing.relative_to(ROOT)),pricing_sha256=sha(pricing.read_bytes()))
                auth=work/'authorizations/synthetic-only.json';dump(auth,gate)
                with patch.object(r,'ledger_read',side_effect=lambda:snapshot(ledger)),patch.object(p.DeepSeekConfig,'from_environment',side_effect=AssertionError('CREDENTIAL_READ')):
                    try:r.approve(auth,sha(auth.read_bytes()),pilot)
                    except ValueError as e:check(case+'_approve_refuses',str(e)=='SHARED_PENDING_OR_UNKNOWN_BLOCKS_PHASE_START')
                    else:check(case+'_approve_refuses',False)
                check(case+'_no_transport',not calls)
                continue
            gate=dict(additional_upper_cap_units=pilot['rows'][0]['reservation_units'] if case=='phase_includes_next_reservation' else 1_000_000_000)
            with patch.object(p.DeepSeekConfig,'from_environment',return_value=config),patch.object(p,'DeepSeekProvider',side_effect=lambda _:original(config,ledger,transport=httpx.MockTransport(fake))),patch.object(r,'ledger_read',side_effect=lambda:snapshot(ledger)):
                rows=asyncio.run(r.execute(pilot,directory,'real',gate))
            if case=='phase_includes_next_reservation':
                check('phase_cap_spent_plus_next_reservation',len(calls)==1 and rows[0]['charged_upper_cny']==pilot['rows'][0]['reservation_units']/1e9 and all(x['error']=='PHASE_UPPER_CAP_STOP' and x['status']=='not_called' for x in rows[1:]))
            else:check('shared_original_allowance_not_renewed',not calls and all(x['error']=='SHARED_BUDGET_STOP' and x['status']=='not_called' for x in rows))
            dump(work/'synthetic-result.json',dict(rows=rows,fake_ledger=snapshot(ledger),actual_paid_calls=0,network_calls=0,synthetic_only=True))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--transport-only',action='store_true');args=parser.parse_args()
    out=ROOT/'evidence/qa'/('T22-experiments-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    out.mkdir(parents=True,exist_ok=False);before=hash_sources(); checks=[]
    def check(name,condition,observed=None): checks.append(dict(name=name,passed=bool(condition),observed=observed))
    try:
        if not args.transport_only:
            formal,pilot=data_checks(out,check)
            lifecycle_checks(out/'lifecycle',check,formal,pilot)
            budget_checks(out/'budget',check,pilot)
        transport_cases(out/'transport',check)
    except Exception as exc:
        checks.append(dict(name='harness_exception',passed=False,observed=type(exc).__name__+':'+str(exc)))
    after=hash_sources();check('product_sources_unchanged',before==after)
    result=dict(kind='independent-T22-prepilot-QA',command=sys.argv,python=sys.executable,checks=checks,
                failed=[c for c in checks if not c['passed']],passed=all(c['passed'] for c in checks),
                source_before=before,source_after=after,actual_paid_calls=0,network_calls=0,credentials_read=False)
    dump(out/'result.json',result);print(str(out/'result.json'));print('checks='+str(len(checks))+' failed='+str(len(result['failed'])))
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
