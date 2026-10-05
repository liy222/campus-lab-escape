"""Owner-only offline checks. Fake transport/temporary ledgers; never .env."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from collections import Counter
import asyncio
import json
import socket
import sqlite3
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import executor as e
import httpx
from backend.app.ai.provider import DeepSeekProvider, DeepSeekConfig
from backend.app.ai.budget import BudgetLedger


def main():
    checks = []
    # Windows asyncio creates a loopback socketpair for its own event loop.
    # Construct it before blocking external socket operations, then reuse it.
    loop = asyncio.new_event_loop()
    def run(coro):
        return loop.run_until_complete(coro)
    destination = e.RUNS / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-continuation-owner-checks-" + uuid.uuid4().hex[:8])
    destination.mkdir(exist_ok=False)
    def check(name, truth, detail=None):
        checks.append({"name": name, "passed": bool(truth), "detail": detail})
    def reject(name, call):
        try:
            call()
        except Exception as error:
            check(name, True, type(error).__name__)
        else:
            check(name, False)
    def no_network(*args, **kwargs):
        raise RuntimeError("OWNER_NETWORK_FORBIDDEN")
    socket.create_connection = no_network
    socket.socket.connect = no_network
    def no_credentials(*args, **kwargs):
        raise RuntimeError("OWNER_CREDENTIALS_FORBIDDEN")
    DeepSeekConfig.from_environment = classmethod(no_credentials)
    protected = {"origin/" + name: e.rawhash(e.ORIGIN / name) for name in e.ORIGIN_HASHES}
    protected.update({"archive/" + rel: e.rawhash(e.ROOT / record["archive_path"]) for rel, record in e.load(e.ARCHIVE_INDEX)["sources"].items()})
    protected["canonical_ledger"] = e.rawhash(e.LEDGER)
    original_sources, execution_sources = e.experiment_hashes(), e.source_manifest()
    plan = e.prepare()
    check("49_whitelist", len(plan["rows"]) == 49 and [r["order"] for r in plan["rows"]] == list(range(24,73)))
    check("variant_and_repeat_counts", Counter(r["variant"] for r in plan["rows"]) == {"full_history":24,"structured_summary":25} and Counter(r["repeat"] for r in plan["rows"]) == {1:1,2:24,3:24})
    check("reservation_exact", plan["reservation_sum_units"] == 5299680000)
    old = e.lines(e.ORIGIN / "raw.jsonl")
    attempted_ids = {r["row_id"] for r in old if r["actually_called"] is True}
    check("original_23_attempts_excluded", not attempted_ids & {r["row_id"] for r in plan["rows"]})
    for row in plan["rows"]:
        saved=e.load(e.ORIGIN / "inputs" / (row["row_id"]+".json"))
        payload=e.wire_bytes(saved)
        check("wire_identity:"+row["row_id"], e.sha(payload)==row["input_hash"] and len(payload)==row["payload_utf8_bytes"])
        value=json.loads(payload)
        check("wire_controls:"+row["row_id"], value['tool_choice']=='none' and value['max_tokens']==1000 and value['thinking']=={'type':'disabled'} and value['stream'] is False and not {'temperature','seed'} & set(value))
    previous=[r for r in old if r['status']=='completed']
    judged=e.judge_batch([{'sample_id':r['sample_id'],'content':r['response']} for r in previous])
    e.write(destination/'historical-v1-judgement.json',judged)
    for row,result in zip(previous,judged['results']):
        check('historical_judge:'+row['row_id'],all(result[k]==row[k] for k in ['legal','correct','reference_valid','reference_sufficient']) and result['next_action']==row['tool_proposal'])
    check('worker_actual_v1_paths',judged['level_version']=='1.0.0' and all(Path(v['file']).is_relative_to(e.ARCHIVE) for v in judged['modules'].values()) and not judged['provider_imported'] and not judged['canonical_product_imported'] and not judged['ledger_accessed'])
    from backend.app.domain.rules import LEVEL_VERSION
    check('canonical_product_current_v2',LEVEL_VERSION=='2.0.0')
    from backend.app.domain.models import GameState
    from backend.app.domain.rules import apply_action
    state=GameState.model_validate(e.load(e.ARCHIVE/'experiments/ground_truth/C10.json')['state'])
    changed,_=apply_action(state.model_copy(deep=True),'use_item',{'item_id':'emergency_key','target_id':'r2_door'})
    check('actual_v1_vs_v2_key_semantics',judged['v1_key_retention_probe'] and 'emergency_key' not in changed.inventory and changed.flags['r3_unlocked'])
    check('parent_provider_canonical',Path(sys.modules['backend.app.ai.provider'].__file__).resolve()==(e.ROOT/'backend/app/ai/provider.py').resolve())
    reject('worker_rejects_arbitrary_sample',lambda:e.judge_batch([{'sample_id':'../../secret','content':'{}'}]))
    reject('gate_required_before_credentials',lambda:e.admit(None,None,plan))
    reject('production_ledger_override_rejected',lambda:DeepSeekProvider(DeepSeekConfig('synthetic'),BudgetLedger(destination/'bad-ledger.sqlite')))
    reject('origin_output_forbidden',lambda:e.write(e.ORIGIN/'forbidden.json',{}))

    mock=e.new_run(plan,'mock',destination/'mock-complete')
    mock_rows=run(e.execute(plan,mock,'mock'))
    check('49_pure_mock_complete',all(r['status']=='completed' and r['correct'] and r['actually_called'] is False and r['usage'] is None and r['charged_upper_cny'] is None for r in mock_rows))
    check('mock_paid_denominator_zero',all(g['paid_attempts_confirmed']==0 and g['completed_per_paid_attempt'] is None for g in e.load(mock/'summary.json')['by_variant'].values()))
    wire_observations=[]
    def scenario(name,kind,*,cap=5300000000,crash=False,freeze=False):
        folder=e.new_run(plan,'synthetic-transport',destination/name)
        ledger=BudgetLedger(folder/'synthetic-ledger.sqlite')
        if freeze:ledger.freeze()
        called=[]
        def response(request):
            called.append(e.sha(request.content));wire_observations.append({'scenario':name,'request_index':len(called),'payload_sha256':e.sha(request.content),'payload_utf8_bytes':len(request.content)})
            if kind=='timeout':raise httpx.ReadTimeout('synthetic')
            if kind=='connection':raise httpx.ConnectError('synthetic')
            if kind in {'401','429','503'}:return httpx.Response(int(kind),json={'error':'local'})
            row=plan['rows'][len(called)-1]
            body={'model':'unapproved-synthetic' if kind=='model' else 'deepseek-flash','choices':[{'message':{'role':'assistant','content':'{bad' if kind=='format' else e.local_content(row['sample_id'])},'finish_reason':'stop'}]}
            if kind!='missing-usage':body['usage']={'prompt_tokens':100,'completion_tokens':10,'total_tokens':110,'prompt_cache_hit_tokens':0}
            return httpx.Response(200,json=body)
        provider=DeepSeekProvider(DeepSeekConfig('synthetic-owner-key-not-real'),ledger,transport=httpx.MockTransport(response))
        if crash:
            try:run(e.execute(plan,folder,'synthetic-transport',provider=provider,cap_units=cap,crash_after_call=True))
            except e.IntentionalSyntheticCrash:pass
            else:check('synthetic_crash_triggered',False)
            return folder,called,ledger,None
        rows=run(e.execute(plan,folder,'synthetic-transport',provider=provider,cap_units=cap))
        return folder,called,ledger,rows
    success,calls,successledger,successrows=scenario('transport-complete','success')
    check('49_fake_wire_requests_once',calls==[r['input_hash'] for r in plan['rows']])
    check('synthetic_49_complete_knownusage',all(r['status']=='completed' and r['usage_known'] and r['actually_called'] is False and r['synthetic_reservation'] for r in successrows))
    check('synthetic_ledger_49_settled',len(e.read_ledger(successledger.path)['calls'])==49 and not e.safe_snapshot(e.read_ledger(successledger.path))['pending_or_unknown'])
    for kind in ['timeout','connection','missing-usage','401','429','503','model']:
        folder,calls,ledger,rows=scenario(kind,kind)
        check(kind+'_one_call_no_retry',len(calls)==1 and len(rows)==49 and all(r['status']=='not_called' for r in rows[1:]))
        check(kind+'_stop_persisted',e.load(folder/'completion.json')['stop_reason']=='STOP_AFTER_UNKNOWN_TIMEOUT_OR_PROVIDER_ABNORMALITY')
        check(kind+'_receipt',rows[0]['response_received'] is (None if kind in {'timeout','connection'} else True))
        if kind!='model':check(kind+'_usage_unknown_retained',not rows[0]['usage_known'] and rows[0]['usage'] is None and rows[0]['charged_upper_cny']==plan['rows'][0]['reservation_units']/1e9)
    folder,calls,ledger,rows=scenario('known-format-failures','format')
    check('known_format_failures_stop_after_two',len(calls)==2 and rows[0]['status']==rows[1]['status']=='parse_invalid' and all(r['status']=='not_called' for r in rows[2:]))
    check('format_known_fee_retained',rows[0]['usage_known'] and rows[1]['usage_known'])
    for name,kwargs in [('phase-cap',{'cap':1}),('frozen-shared',{'freeze':True})]:
        folder,calls,ledger,rows=scenario(name,'success',**kwargs)
        check(name+'_no_request',not calls and all(r['status']=='not_called' for r in rows))

    crash,calls,crashledger,_=scenario('crash-after-reservation','success',crash=True)
    check('precall_journal_no_final_row',len(calls)==1 and len(e.lines(crash/'journal.jsonl'))==1 and not (crash/'raw.jsonl').exists() and not (crash/'completion.json').exists())
    snap=e.read_ledger(crashledger.path)
    stem=e.reconcile(crash,synthetic_snapshot=snap)
    recovered=e.lines(crash/(stem+'.jsonl'))
    check('crash_reconcile_no_resend',len(calls)==1 and len(recovered)==49 and recovered[0]['call_id']==snap['calls'][0]['id'] and recovered[0]['response_received'] is None and recovered[0]['usage_known'] and all(r['status']=='not_called' for r in recovered[1:]))
    ambiguous=deepcopy(snap);duplicate=deepcopy(ambiguous['calls'][0]);duplicate['id']='synthetic-second-id';ambiguous['calls'].append(duplicate)
    stem=e.reconcile(crash,synthetic_snapshot=ambiguous)
    check('ambiguous_crash_remains_unknown',e.lines(crash/(stem+'.jsonl'))[0]['actually_called'] is None)
    manual=deepcopy(snap);manual['calls'][0].update(state='settled',prompt_tokens=None,completion_tokens=None,cache_hit_tokens=None)
    stem=e.reconcile(crash,synthetic_snapshot=manual)
    check('settled_null_is_not_known_usage',e.lines(crash/(stem+'.jsonl'))[0]['usage'] is None and not e.lines(crash/(stem+'.jsonl'))[0]['usage_known'])
    reject('origin_once_guard',lambda:e.started_guard_records(plan,{'id':'new-synthetic-id'},[{'mode':'real','origin_run_id':plan['origin_run_id'],'authorization_id':'different-id'}]))
    reject('consumed_id_guard',lambda:e.started_guard_records(plan,{'id':'same-synthetic-id'},[{'mode':'real','origin_run_id':'other-origin','authorization_id':'same-synthetic-id'}]))

    merged=e.merge(success,destination/'merged-synthetic',allow_synthetic=True)
    check('merged_72_order',len(merged)==72 and [r['row_id'] for r in merged]==[r['row_id'] for r in old])
    for oldrow in old:
        if oldrow['status']!='not_called':check('preserved_original:'+oldrow['row_id'],merged[oldrow['order']-1]==oldrow)
    summary=e.load(destination/'merged-synthetic/summary.json')
    check('merged_71complete_original_timeout',sum(r['status']=='completed' for r in merged)==71 and sum(r['status']=='timeout' for r in merged)==1)
    check('merged_denominators36',all(g['planned']==36 for g in summary['by_variant'].values()))
    timeout=merged[22]
    check('original_timeout_null_and_reserve',timeout['usage'] is None and timeout['response_received'] is None and timeout['charged_upper_cny']==.16292 and timeout['call_id']=='520a5c50b9204960a3f9915952ed9b97')
    reject('synthetic_cannot_production_merge',lambda:e.merge(success,destination/'forbidden-real-merge'))
    # Duplicate and wrong-input mutations affect only copied synthetic outputs.
    tampered=e.new_run(plan,'synthetic-transport',destination/'duplicate-test')
    duplicate_rows=deepcopy(successrows);duplicate_rows[1]=deepcopy(duplicate_rows[0])
    for row in duplicate_rows:e.append(tampered/'raw.jsonl',row)
    reject('duplicate_unit_rejected',lambda:e.merge(tampered,destination/'duplicate-merge',allow_synthetic=True))
    altered=e.new_run(plan,'synthetic-transport',destination/'wrong-input-test')
    altered_rows=deepcopy(successrows);altered_rows[0]['input_hash']='0'*64
    for row in altered_rows:e.append(altered/'raw.jsonl',row)
    reject('changed_input_merge_rejected',lambda:e.merge(altered,destination/'wrong-input-merge',allow_synthetic=True))

    # Pure finite gate validation uses explicit synthetic snapshots and existing
    # registered evidence as hashed fixtures; it is not a Main real authorization.
    price='evidence/integration/pricing-check-20261005-live.json'
    checked=datetime.fromisoformat(e.load(e.ROOT/price)['checked_at_utc'].replace('Z','+00:00'))
    gate={'id':'SYNTHETIC-OWNER-GATE-NOT-AUTHORIZATION','approved_by':'Main','approved':True,'kind':e.KIND,'phase':'continuation',
          'max_calls':49,'additional_upper_cap_units':5300000000,'expires_at':(checked+timedelta(hours=1)).isoformat(),
          'plan_hash':e.sha(plan),'original_freeze_hash':e.FREEZE_SHA,'original_plan_hash':e.PLAN_SHA,'origin_run_id':e.ORIGIN.name,
          'selected_identity_hash':plan['selected_identity_hash'],'execution_sources_hash':e.sha(plan['execution_sources']),
          'archive_index_sha256':e.ARCHIVE_SHA,'baseline_manifest_sha256':e.MANIFEST_SHA,'dependencies_hash':e.sha(plan['dependencies']),
          'pricing_evidence':price,'pricing_sha256':e.rawhash(e.ROOT/price),'pilot_run_id':'20261005T052822923700Z-pilot-real-0378672e',
          'pilot_summary_sha256':'a6ee9d903668c0285d30619c0b43d93f2ca7e231560118664ebfb2e0a38fa79a','pilot_review_accepted':True,
          'candidate_qa_evidence':'evidence/qa/T22-experiments-20261002T164754631028Z/result.json',
          'candidate_qa_sha256':e.rawhash(e.ROOT/'evidence/qa/T22-experiments-20261002T164754631028Z/result.json'),'candidate_qa_accepted':True,
          'accounting_closure_evidence':'evidence/integration/E1-source-archive-20261005.json','accounting_closure_sha256':e.ARCHIVE_SHA,'accounting_closure_accepted':True,
          'note':'SYNTHETIC validator fixture only; references are not candidate QA/closure acceptance and this is never issued under authorizations.'}
    snapshot={'cap_units':10000000000,'remaining_units':9000000000,'charged_units':1000000000,'frozen':False,'calls':[]}
    check('synthetic_gate_bindings_valid',e.validate_gate(gate,plan,snapshot,at=checked+timedelta(minutes=5))==gate)
    for field in ['plan_hash','selected_identity_hash','execution_sources_hash','dependencies_hash','archive_index_sha256','original_freeze_hash']:
        bad=deepcopy(gate);bad[field]='0'*64
        reject('gate_identity_reject:'+field,lambda b=bad:e.validate_gate(b,plan,snapshot,at=checked+timedelta(minutes=5)))
    for field,value in [('max_calls',72),('additional_upper_cap_units',5300000001),('candidate_qa_accepted',False),('accounting_closure_accepted',False)]:
        bad=deepcopy(gate);bad[field]=value
        reject('gate_constraint_reject:'+field,lambda b=bad:e.validate_gate(b,plan,snapshot,at=checked+timedelta(minutes=5)))
    reject('expired_gate_rejected',lambda:e.validate_gate(gate,plan,snapshot,at=checked+timedelta(hours=2)))
    blocked=deepcopy(snapshot);blocked['calls']=[{'state':'unknown'}]
    reject('unknown_shared_ledger_rejected',lambda:e.validate_gate(gate,plan,blocked,at=checked+timedelta(minutes=5)))
    blocked=deepcopy(snapshot);blocked['frozen']=True
    reject('frozen_shared_ledger_rejected',lambda:e.validate_gate(gate,plan,blocked,at=checked+timedelta(minutes=5)))
    e.write(destination/'wire-observations.json',wire_observations)
    after={"origin/"+name:e.rawhash(e.ORIGIN/name) for name in e.ORIGIN_HASHES}
    after.update({"archive/"+rel:e.rawhash(e.ROOT/record['archive_path']) for rel,record in e.load(e.ARCHIVE_INDEX)['sources'].items()})
    after['canonical_ledger']=e.rawhash(e.LEDGER)
    check('protected_artifacts_and_original_ledger_unchanged',protected==after)
    check('original41_source_unchanged',original_sources==e.experiment_hashes())
    check('new_executor_sources_unchanged',execution_sources==e.source_manifest())
    failures=sum(not item['passed'] for item in checks)
    report={'kind':'Owner synthetic checks, not independent QA or paid E1 results','checks':checks,'count':len(checks),'failures':failures,'passed':failures==0,
            'actual_command':sys.argv,'python':sys.executable,'sources_before':execution_sources,'sources_after':e.source_manifest(),
            'protected_before':protected,'protected_after':after,'original_experiment_sources':original_sources,'plan_hash':e.sha(plan),
            'env_read':False,'original_ledger_mutated':False,'network_calls':0,'paid_calls':0,
            'limitations':['Owner tests do not certify independent QA acceptance or real continuation outcome.','HTTP/usage/failure cases are scripted; SQLite is isolated synthetic test data.','Gate tests use labeled validator fixtures, not Main-issued real approval.']}
    e.write(destination/'result.json',report)
    loop.close()
    print(json.dumps({'output':str(destination),'count':len(checks),'failures':failures,'passed':failures==0,'result_raw_sha256':e.rawhash(destination/'result.json')}))
    return 0 if not failures else 1


if __name__=='__main__':
    raise SystemExit(main())
