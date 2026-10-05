"""Independent CH01 identity-archive review; no target imports or paid I/O."""
from __future__ import annotations
import argparse,asyncio,hashlib,importlib.abc,importlib.util,json,os,socket,sys
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));EVAL=ROOT/'evaluation'
HANDOFF=EVAL/'runs/ch01-v3-identity-alias-handoff'
PINS={'source-sha256.json':'60d20f3a77bfe93053acd696815199b313cc6604d28ffef0273a9a6d09a28e9d','stable-handoff.json':'bee52c1456c3a65d22d2a9a08b16ee761d6473c7d4377e620b05d905e547ab0f','source-diff.patch':'ccb00954ded3fc759b6b35f945c1fbc9db57d702de174c08a80abc2021d06aa3'}
CARD=ROOT/'evidence/integration/event-ch01-adversarial-review-v3-registration.json'
CARD_SHA='95169a12bf1ecb11f6e4eb3664c5e7d27154ef995ef3f462421da342f3178048'
RELAY=ROOT/'evidence/integration/run_paid_evaluation.py'
RELAY_SHA='a1561ac38f8756856642a1d7e991d9545d04c5afa591b71d281987f3ab6ebd41'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False)
def sources():return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(EVAL.rglob('*')) if p.is_file() and not any(x in p.relative_to(EVAL).parts for x in ('runs','.runtime','__pycache__'))}
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self,name,path=None,target=None):
        if name.split('.')[0] in {'backend','experiments','scripts','product'}:raise RuntimeError('TARGET_CODE_IMPORT_FORBIDDEN')
async def run(out):
    def no_network(*a,**kw):raise RuntimeError('QA_REAL_NETWORK_FORBIDDEN')
    socket.create_connection=no_network;socket.socket.connect=no_network
    sys.meta_path.insert(0,Guard());checks=[];cases=[]
    def check(n,v,d=None):checks.append(dict(name=n,passed=bool(v),details=d))
    before=sources();installed=load(HANDOFF/'source-sha256.json')
    for p,h in PINS.items():check('Main_pin:'+p,sha(HANDOFF/p)==h)
    check('candidate_exact52_installed',len(installed)==52 and before==installed)
    if not all(c['passed'] for c in checks):raise RuntimeError('CANDIDATE_NOT_MAIN_PINNED')
    old=load(HANDOFF/'source-before.json');changed={p for p,h in old.items() if before.get(p)!=h};new=set(before)-set(old)
    check('only3_old_files_changed',len(old)==48 and changed=={'evaluation/events.py','evaluation/check_events.py','evaluation/trusted/events-registry-v1.json'},sorted(changed))
    check('only4_new_inputs',len(new)==4 and all(p.startswith('evaluation/trusted/events/ch01-adversarial-review-v3/') for p in new),sorted(new))
    check('45_others_unchanged',sum(before[p]==h for p,h in old.items())==45)
    check('relay_current_byte_matches_old_independent_pin',sha(RELAY)==RELAY_SHA,dict(scope='Current QA byte comparison to prior independent pin; not Owner historical snapshot',sha256=sha(RELAY)))
    protected={p:sha(ROOT/p) for p in ('evidence/integration/event-e1-formal-review-v2-registration.json','evidence/integration/event-ch01-adversarial-review-v3-registration.json','evidence/integration/E1-source-archive-20261005.json','evidence/integration/run_paid_evaluation.py')}
    from evaluation.trust import load_tools,source_precheck
    from evaluation.engine import Evaluator
    from evaluation.provider import MockProvider
    from evaluation.common import EvaluationError
    from evaluation import cli
    freeze,files,tools=load_tools();card=load(CARD);release=card['release_id'];event=tools.event_contexts[release]
    check('CH01_Main_exact_rawpin',sha(CARD)==CARD_SHA)
    check('CH01_newfreeze_exact',event.input_sha256=='5eb36ad053d05a5285fd6dd22fe25983d575c5597abe5d8441fb5ed6457aee6d')
    pre=source_precheck(tools,release)
    check('real162_sources10_evidence2_execution',not pre['issues'] and len(pre['source_identities'])==162 and len(card['manifest']['evidence'])==10 and len(pre['runtime_source_bindings'])==2,pre['issues'])
    check('all162_unique_aliases',len(card['source_locations'])==162 and len({v['archive_path'] for v in card['source_locations'].values()})==162)
    check('60_CH01_102_baseline_exactraw',sum(v['archive_release_id']=='CH01_v2' for v in card['source_locations'].values())==60 and sum(v['archive_release_id']=='baseline_v1' for v in card['source_locations'].values())==102)
    for key,location in card['source_locations'].items():protected[location['archive_path']]=sha(ROOT/location['archive_path'])
    check('binding_full_maps153_57',sorted(v['source_count'] for v in pre['runtime_source_bindings'])==[57,153] and all(v['source_before']==v['source_after'] and len(v['source_before'])==v['source_count'] and type(v['exit_code']) is int and v['release_id']==release and v['product_commit']==card['product_commit'] for v in pre['runtime_source_bindings']))
    runtime={v['evidence_id']:v for v in pre['runtime_source_bindings']}
    for r in card['runtime_records']:check('explicit_full_binding:'+r['evidence_id'],set(runtime[r['evidence_id']]['source_before'])==set(r['source_paths']))
    check('union_covers_exact162',{p for r in card['runtime_records'] for p in r['source_paths']}==set(card['source_locations']))
    check('three_full_original_MUST_noNA',len(event.claims)==3 and {c['criterion_id'] for c in event.claims}=={'A27','A21','A23'} and all(c['statement']==files['trusted/contract.json']['criteria'][c['criterion_id']]['must_observe'] and c['declared_na'] is False and event.coverage[c['claim_id']]['status']=='full' and not event.coverage[c['claim_id']]['gaps'] for c in event.claims))
    window_bytes={}
    for c in event.claims:
        sizes=[]
        for r in c['evidence_refs']:
            v=tools.read_evidence(r['evidence_id'],r['snippet']);sizes.append(len(v['text'].encode('utf-8')))
            check('registered_window_hash:'+c['criterion_id']+':'+r['evidence_id'],v['reference']['artifact_raw_sha256']==r['expected_raw_sha256'] and sizes[-1]<=16384)
        window_bytes[c['claim_id']]=sum(sizes);check('claim_65536_limit:'+c['claim_id'],sum(sizes)<=65536,sum(sizes))
        v,a=await Evaluator(tools,files).evaluate(c);check('structural_no_semantic_PASS:'+c['claim_id'],v['status']=='INSUFFICIENT_EVIDENCE' and a['raw_suggestion'] is None and v['execution_scope']['actual_model_requests_this_claim']==0)
    e1=source_precheck(tools,'E1-formal-review-v2');check('old_E1_still102_13_6',not e1['issues'] and len(e1['source_identities'])==102 and len(tools.manifests['E1-formal-review-v2']['evidence'])==13 and len(e1['runtime_source_bindings'])==6)
    check('old17_chain_frozen',len(freeze['inputs'])==16 and all(sha(EVAL/p)==h for p,h in freeze['inputs'].items()))
    # Execute only the public mock CLI mode. find_gate is a trap to establish
    # that no current finite paid approval or credential path is entered.
    mockdir=out/'mock-cli';mockdir.mkdir()
    with patch.object(cli,'output_folder',lambda:mockdir),patch.object(cli,'find_gate',side_effect=RuntimeError('PAID_GATE_MUST_NOT_BE_ENTERED')):
        code=await cli.run(SimpleNamespace(action='evaluate',release=release,mode='mock',approval_id=None))
    report=load(mockdir/'report.json')
    check('real_three_mock_INSufficient_exit2_paid0',code==2 and len(report['results'])==3 and all(v['status']=='INSUFFICIENT_EVIDENCE' for v in report['results']) and report['actual_paid_calls']==0)
    check('three_actual_MockProvider_audits',len(report['audits'])==3 and all(a['raw_suggestion'] is not None and a['raw_suggestion']['status']=='INSUFFICIENT_EVIDENCE' and a['provider_metadata']['actual_network_call'] is False for a in report['audits']))
    save(out/'real-structural.json',dict(CH01=pre,E1=e1,claim_window_bytes=window_bytes,actual_paid_calls=0,target_executed=False,archive_executed=False))
    # Own previous QA's fixture constructor, not Owner's tests. These sources
    # are data probes under a new QA root and are never imported or executed.
    spec=importlib.util.spec_from_file_location('qa_prior_fixture',ROOT/'tests/review_evaluation_events.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
    serial=0
    def fresh():
        nonlocal serial
        serial+=1;p=out/'isolated-events'/str(serial);p.mkdir(parents=True);return q.Fixture(p,files)
    def identity(f):
        f.archive();oldkey=f.source;loc=f.main['source_locations'].pop(oldkey);f.source=loc['archive_path'];f.main['source_locations']={f.source:loc};f.main['runtime_records'][0]['source_paths']=[f.source]
        f.identity_change(lambda v:v.update(source_before={f.source:loc['raw_sha256']},source_after={f.source:loc['raw_sha256']}));return f
    def renamekey(f,key):
        loc=f.main['source_locations'].pop(f.source);record=f.main['manifest']['sources'].pop(f.source);loc['archive_path']=key;f.source=key;f.main['source_locations']={key:loc};f.main['manifest']['sources']={key:record};f.main['runtime_records'][0]['source_paths']=[key]
        f.identity_change(lambda v:v.update(source_before={key:loc['raw_sha256']},source_after={key:loc['raw_sha256']}))
    def suggestion(f,c):return dict(claim_id=c['claim_id'],release_id=f.release,status='PASS',evidence_refs=[dict(evidence_id=f.runid,snippet='summary')],reason='Synthetic probe only',missing_check=[])
    async def denied(name,mut):
        f=identity(fresh());mut(f);f.seal();error=None;result=None;provider=None;issues=[]
        try:
            t=f.tools();issues=source_precheck(t,f.release)['issues'];c=f.main['claims']['claims'][0];provider=MockProvider([suggestion(f,c)]);result,audit=await Evaluator(t,files,provider).evaluate(c)
        except EvaluationError as e:error=e.code
        check('deny:'+name,error is not None or result and result['status']!='PASS',dict(error=error,status=result['status'] if result else None,issues=issues))
        cases.append(dict(name=name,error=error,result=result,issues=issues,mock_calls=provider.calls if provider else 0,synthetic=True))
    f=identity(fresh());t=f.tools();p=source_precheck(t,f.release)
    check('identity_alias_legitimate_same_key',not p['issues'] and p['runtime_source_bindings'][0]['source_locations'][f.source]['archive_path']==f.source)
    c=f.main['claims']['claims'][0];provider=MockProvider([suggestion(f,c)]);v,a=await Evaluator(t,files,provider).evaluate(c)
    check('identity_alias_positive_really_enters_mock',v['status']=='PASS' and provider.calls==1 and a['raw_suggestion']['status']=='PASS')
    for name,fn in [
        ('wrong_safeid',lambda f:f.main['source_locations'][f.source].update(archive_release_id='different')),
        ('unsafe_safeid',lambda f:f.main['source_locations'][f.source].update(archive_release_id='../qa_v1')),
        ('wrongpath',lambda f:f.main['source_locations'][f.source].update(archive_path='product/source.py')),
        ('sameprefix_differentpath',lambda f:f.main['source_locations'][f.source].update(archive_path=f.source+'.different')),
        ('empty_tail',lambda f:renamekey(f,'release/archives/qa_v1/')),
        ('lookalike_prefix',lambda f:renamekey(f,'release/archives/qa_v10/product/source.py')),
        ('traversal',lambda f:renamekey(f,'release/archives/qa_v1/../product/source.py')),
        ('backslash',lambda f:renamekey(f,'release/archives/qa_v1/product\\source.py')),
        ('absolute_tail',lambda f:renamekey(f,'release/archives/qa_v1/C:/outside.py')),
        ('duplicate_archive_value',lambda f:f.main['source_locations'].update({'product/alias.py':deepcopy(f.main['source_locations'][f.source])})),
        ('missing_all_aliases',lambda f:f.main['source_locations'].pop(f.source)),
        ('declared_raw_mismatch',lambda f:f.main['source_locations'][f.source].update(raw_sha256='0'*64)),
        ('cross_release',lambda f:f.identity_change(lambda v:v.update(release_id='current_v2'))),
        ('cross_productcommit',lambda f:f.identity_change(lambda v:v.update(product_commit='b'*40))),
        ('missing_execution_binding',lambda f:f.main.update(runtime_records=[])),
        ('missing_full_map',lambda f:f.identity_change(lambda v:v.update(source_after={}))),
        ('beforeafter_drift',lambda f:f.identity_change(lambda v:v['source_after'].update({f.source:'0'*64}))),
        ('bool_exit',lambda f:f.identity_change(lambda v:v.update(exit_code=True))),
        ('partial_coverage',lambda f:f.main['coverage'][0].update(status='partial',gaps=['Full MUST unavailable'])),
        ('low_MUST',lambda f:f.main['claims']['claims'][0].update(statement='easy self-asserted requirement')),
        ('execution_support_bypass',lambda f:f.main['evidence_roles'].update({f.runid:'support'})),
    ]:await denied(name,fn)
    f=identity(fresh());t=f.tools();(f.root/f.source).write_bytes((f.root/f.source).read_bytes().replace(b'\r\n',b'\n'));p=source_precheck(t,f.release)
    check('identity_raw_no_canonical_fallback',any(i['code']=='EVENT_ARCHIVE_RUNTIME_RAW_MISMATCH' for i in p['issues']),p['issues'])
    # Original runtime aliases remain bound to archived v1; current-path drift
    # must not be certified as current v2 by reusing the pinned archive.
    f=fresh();arch=f.archive();(f.root/f.source).write_bytes(b"raise RuntimeError('CURRENT_VERSION_NEVER_EXECUTE')\n");t=f.tools();p=source_precheck(t,f.release)
    check('original_alias_reads_only_archive_no_current_certification',not p['issues'] and set(p['source_identities'])=={arch.relative_to(f.root).as_posix()} and p['runtime_source_bindings'][0]['source_before'][f.source]==sha(arch))
    f=identity(fresh());parent=(f.root/f.source).parent;destination=f.root/'owned-junction-destination'
    if not parent.resolve().is_relative_to(f.root.resolve()) or not destination.resolve().is_relative_to(f.root.resolve()):raise RuntimeError('QA_JUNCTION_SCOPE')
    raw=(f.root/f.source).read_bytes();parent.rename(destination)
    from evaluation.check import junction
    try:
        junction(parent,destination)
        try:f.tools()
        except EvaluationError as e:check('identity_actual_Windows_junction_matchingraw_rejected',e.code=='REPARSE_POINT')
        else:check('identity_actual_Windows_junction_matchingraw_rejected',False)
        check('junction_target_not_modified',(destination/'source.py').read_bytes()==raw)
    finally:
        if parent.exists():os.rmdir(parent) if os.name=='nt' else parent.unlink()
    f=identity(fresh());t=f.tools();c=f.main['claims']['claims'][0]
    class Drifting(MockProvider):
        async def complete(self,msgs):
            reply=await super().complete(msgs);f.identity_change(lambda v:v['source_after'].update({f.source:'0'*64}));return reply
    v,a=await Evaluator(t,files,Drifting([suggestion(f,c)])).evaluate(c)
    check('identity_drift_after_mock_cannot_PASS',v['status']=='INSUFFICIENT_EVIDENCE' and not v['evidence_refs'])
    save(out/'identity-counterexamples.json',cases)
    # Independently reproduce only the obsolete empty-gate assertion. Do not
    # clear Main's finite gate or claim the Owner legacy114 as independent.
    gates=load(EVAL/'trusted/paid-gates.json');legacy_assertion_failed=False
    try:assert gates['approvals']==[]
    except AssertionError:legacy_assertion_failed=True
    check('legacy_empty_gate_conflict_honestly_reproduced',legacy_assertion_failed and sha(EVAL/'trusted/paid-gates.json')=='82d515ec1f538ebde9d19e4f01418eebdb41fabb9b7988c7be97e9989b68b1a6')
    handoff=load(HANDOFF/'stable-handoff.json');record=next(r for r in handoff['evidence'] if r['kind']=='legacy_owner');old_report=load(ROOT/record['path'])
    save(out/'checks-before-legacy-observation.json',checks)
    check('Owner_113_114_actual_evidence_pin_retained',sha(ROOT/record['path'])==record['raw_sha256'] and record['actual_program_exit_code']==1 and record['checks']==114 and record['passed']==113 and [r['name'] for r in old_report['results'] if not r['passed']]==['paid gates disabled'])
    save(out/'legacy-gate-observation.json',dict(independent_reproduced_assertion=dict(name='paid gates disabled',passed=False,error='AssertionError',actual_approval_count=len(gates['approvals'])),Owner_report=record,gate_raw_sha256=sha(EVAL/'trusted/paid-gates.json'),gate_unchanged=True,no_independent_legacy114_rerun=True,actual_paid_calls=0))
    check('no_target_module_imported',not any(n=='backend' or n.startswith(('backend.','experiments.','scripts.','product.')) for n in sys.modules))
    check('all52_candidate_bytes_stable',before==sources());check('protected_Main_archive_bytes_stable',all(sha(ROOT/p)==h for p,h in protected.items()))
    result=dict(task='T27-CH01-event-independent',created_at=datetime.now(timezone.utc).isoformat(),checks=len(checks),passed=sum(c['passed'] for c in checks),failures=[c for c in checks if not c['passed']],command=[sys.executable,*sys.argv],sources_before=before,sources_after=sources(),protected_Main_archive_bytes=protected,actual_paid_calls=0,actual_external_network_calls=0,original_ledger_opened=False,real_env_read=False,target_or_archive_code_executed=False,limitations=['CH01 162-source/2-execution identities read/hash only; not current product rerun or semantic acceptance.','Real registered mock3 concludes INSUFFICIENT_EVIDENCE, not independent human/model judgement.','Synthetic identity-alias probes establish tested protocol behavior only.','Main relay current byte matches previous independent pin; Owner immediate snapshot not available.','Legacy empty-gate assertion genuinely fails after Main finite gate; Owner113/114 pinned, not independently rerun.'])
    save(out/'checks.json',checks);save(out/'result.json',result);print(json.dumps(dict(checks=result['checks'],passed=result['passed'],failed=len(result['failures']),output=str(out)),ensure_ascii=False));return bool(result['failures'])
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=(ROOT/a.output).resolve()
    if not out.is_relative_to(ROOT/'evidence/qa') or out.exists():raise ValueError('NEW_QA_OUTPUT_REQUIRED')
    out.mkdir(parents=True);return asyncio.run(run(out))
if __name__=='__main__':raise SystemExit(main())
