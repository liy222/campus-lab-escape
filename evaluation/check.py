"""Owner-only local boundaries and protocol checks; no product tests or real calls."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import ctypes
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
from unittest.mock import patch

import httpx

from .cli import output_folder,find_gate
from .common import EVALUATOR_ROOT, EvaluationError, json_bytes, sha256, strict_json
from .engine import Evaluator
from .provider import CAP, ExistingLedger, FakePaidProvider, MockProvider, PaidProvider, PRODUCTION_LEDGER, cost_units
from .reader import safe_read, verify_identity
from .trust import load_tools


def fake_ledger(path):
    # Fixture creation is confined to this explicit fake helper, never production client.
    with closing(sqlite3.connect(path)) as db:
        db.execute('CREATE TABLE budget_config (id INTEGER PRIMARY KEY CHECK(id=1),cap INTEGER NOT NULL,frozen INTEGER NOT NULL DEFAULT 0)')
        db.execute('INSERT INTO budget_config VALUES(1,?,0)',(CAP,))
        db.execute('CREATE TABLE budget_calls (id TEXT PRIMARY KEY,scope TEXT NOT NULL,created_at TEXT NOT NULL,reserved INTEGER NOT NULL,charged INTEGER NOT NULL,state TEXT NOT NULL,reason TEXT,prompt_tokens INTEGER,completion_tokens INTEGER,cache_hit_tokens INTEGER)')
        db.commit()


def gate(name,input_hash='f'*64,**changes):
    value={'approval_id':name,'approved_by':'SYNTHETIC_TEST_ONLY','purpose':'calibration','input_sha256':input_hash,
           'max_calls':3,'max_cost_units':1_000_000_000,'max_tokens':1000,'timeout_seconds':1,
           'expires_at':'2099-01-01T00:00:00Z','credential_env':'EVALUATION_MODEL_API_KEY',
           'base_url':'https://api.deepseek.com','model':'deepseek-flash'}
    value.update(changes);return value


def response(content='{}',usage=True,model='deepseek-flash'):
    value={'model':model,'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':content}}]}
    if usage:value['usage']={'prompt_tokens':100,'completion_tokens':10,'total_tokens':110,'prompt_cache_hit_tokens':20,'prompt_cache_miss_tokens':80}
    return httpx.Response(200,json=value)


def junction(link,target):
    if os.name!='nt':link.symlink_to(target,target_is_directory=True);return
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    kernel.CreateFileW.restype=wintypes.HANDLE
    kernel.DeviceIoControl.argtypes=[wintypes.HANDLE,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    link.mkdir()
    substitute=('\\??\\'+str(target.resolve())).encode('utf-16-le');display=str(target.resolve()).encode('utf-16-le')
    names=substitute+b'\0\0'+display+b'\0\0'
    data=struct.pack('<LHHHHHH',0xA0000003,8+len(names),0,0,len(substitute),len(substitute)+2,len(display))+names
    handle=kernel.CreateFileW(str(link),0x40000000,0,None,3,0x02200000,None)
    if handle==ctypes.c_void_p(-1).value:raise OSError(ctypes.get_last_error())
    try:
        buffer=ctypes.create_string_buffer(data);written=wintypes.DWORD()
        if not kernel.DeviceIoControl(handle,0x900A4,buffer,len(data),None,0,ctypes.byref(written),None):raise OSError(ctypes.get_last_error())
    finally:kernel.CloseHandle(handle)


async def main_async():
    folder=output_folder();results=[]
    source_before={p.relative_to(EVALUATOR_ROOT).as_posix():sha256(p.read_bytes()) for p in sorted(EVALUATOR_ROOT.glob('*.py'))}
    def record(name,action,expected=None):
        try:
            actual=action()
            if expected is not None:assert actual==expected,(actual,expected)
            results.append({'name':name,'passed':True,'actual':actual})
            return actual
        except Exception as error:
            results.append({'name':name,'passed':False,'error_code':error.code if isinstance(error,EvaluationError) else type(error).__name__})
            return None
    def rejects(action,code=None):
        try:action()
        except EvaluationError as error:
            if code:assert error.code==code,(error.code,code)
            return error.code
        raise AssertionError('Unexpected acceptance')
    freeze,files,tools=load_tools()
    record('unknown contract cannot lower rubric',lambda:rejects(lambda:tools.get_approved_contract('target','1.0.0'),'UNKNOWN_CONTRACT_VERSION'))
    record('unknown version',lambda:rejects(lambda:tools.get_approved_contract('campus-lab-engineering','0.0.0'),'UNKNOWN_CONTRACT_VERSION'))
    record('unknown evidence path is not a tool input',lambda:rejects(lambda:tools.read_evidence('../.env'),'INVALID_ID'))
    record('unregistered snippet',lambda:rejects(lambda:tools.read_evidence('baseline_v1:E001','arbitrary'),'UNREGISTERED_SNIPPET'))
    record('four states only',lambda:len(files['trusted/contract.json']['policy']['states']),4)
    record('all 28 MUST retained',lambda:sum(k.startswith('A') for k in files['trusted/contract.json']['criteria']),28)
    record('paid gates disabled',lambda:strict_json((EVALUATOR_ROOT/'trusted/paid-gates.json').read_bytes())['approvals'],[])
    record('missing Main gate stops before credentials/ledger',lambda:rejects(lambda:find_gate('not-approved','f'*64,'calibration'),'MAIN_FINITE_PAID_GO_REQUIRED'))
    record('K expected frozen before calls',lambda:all(freeze['case_sha256'][c['case_id']]==sha256(json_bytes(c)) for c in files['fixtures/cases.json']['cases']),True)
    with tempfile.TemporaryDirectory(prefix='evaluator-owned-') as owned:
        root=Path(owned);inside=root/'inside';outside=root/'outside';inside.mkdir();outside.mkdir()
        (inside/'safe.json').write_bytes(b'{"ok":true}')
        (outside/'sentinel.json').write_bytes(b'{"private":"outside sentinel"}')
        record('handle verified safe read',lambda:safe_read(inside,'safe.json').decode('utf-8'),'{'+'"ok":true}')
        for rel in ['../outside/sentinel.json','/outside.json','C:/outside.json','safe.json:stream','CON.json','folder\\safe.json','.env','data/game.sqlite','node_modules/a.json']:
            record('path rejects '+rel,lambda rel=rel:rejects(lambda:safe_read(inside,rel)))
        (inside/'big.json').write_bytes(b'x'*100)
        record('size limit before snippet',lambda:rejects(lambda:safe_read(inside,'big.json',10),'EXCESS_SIZE'))
        record('raw mismatch never ignored',lambda:rejects(lambda:verify_identity(b'a\n',{'artifact_raw_sha256':'0'*64,'artifact_binding':'raw_equal'}),'HASH_MISMATCH'))
        record('target cannot self-authorize normalization',lambda:rejects(lambda:verify_identity(b'a\n',{'artifact_raw_sha256':'0'*64,'artifact_binding':'target_normalize','artifact_utf8_lf_v1_sha256':sha256(b'a\n')}),'HASH_MISMATCH'))
        link=inside/'junction'
        try:
            junction(link,outside)
            record('Windows junction / symlink escape rejected',lambda:rejects(lambda:safe_read(inside,'junction/sentinel.json'),'REPARSE_POINT'))
        except OSError as error:results.append({'name':'Windows junction / symlink escape rejected','passed':False,'limitation':'OS reparse fixture creation unavailable','os_code':error.errno})
        finally:
            if link.exists():os.rmdir(link) if os.name=='nt' else link.unlink()
        record('outside sentinel retained',lambda:(outside/'sentinel.json').read_bytes().decode('utf-8'),'{'+'"private":"outside sentinel"}')
        record('strict duplicate JSON rejection',lambda:rejects(lambda:strict_json('{"x":1,"x":2}'),'DUPLICATE_JSON_KEY'))
        record('nonfinite JSON rejection',lambda:rejects(lambda:strict_json('{"x":NaN}'),'NONFINITE_JSON'))
        missing=root/'missing.sqlite'
        record('existing ledger required without initialization',lambda:rejects(lambda:ExistingLedger(_fake_path=missing),'EXISTING_LEDGER_REQUIRED'))
        record('missing ledger remains absent',lambda:missing.exists(),False)
        base=root/'ledger.sqlite';fake_ledger(base);ledger=ExistingLedger(_fake_path=base)
        calls=[]
        def transport(request):
            assert request.url==httpx.URL('https://api.deepseek.com/chat/completions')
            body=strict_json(request.content)
            assert body['thinking']=={'type':'disabled'} and body['stream'] is False and body['max_tokens']==1000
            assert 'tools' not in body
            calls.append(body)
            return response()
        fake=FakePaidProvider(gate('success'),'f'*64,ledger_path=base,transport=httpx.MockTransport(transport))
        reply=await fake.complete([{'role':'system','content':'Synthetic fixture'}])
        record('fake protocol usage real network false',lambda:reply.metadata['actual_network_call'],False)
        record('fake settled cost',lambda:reply.metadata['cost_upper_units'],cost_units(100,10,20))
        record('fake exact one transport attempt',lambda:len(calls),1)
        record('idempotent exact settlement',lambda:ledger.settle(reply.metadata['call_id'],100,10,20),cost_units(100,10,20))
        record('conflicting settlement rejected',lambda:rejects(lambda:ledger.settle(reply.metadata['call_id'],101,10,20),'SETTLEMENT_CONFLICT'))
        unknown=FakePaidProvider(gate('missingusage'),'f'*64,ledger_path=base,transport=httpx.MockTransport(lambda _:response(usage=False)))
        await unknown.complete([{'role':'system','content':'Synthetic fixture'}])
        record('unknown usage retains reservation',lambda:ledger.snapshot()['unknown_or_pending_calls'],1)
        try:await unknown.complete([{'role':'system','content':'Synthetic fixture'}])
        except EvaluationError as error:record('unknown prior call stops blind repetition',lambda:error.code,'PRIOR_CALL_UNKNOWN_STOP')
        else:record('unknown prior call stops blind repetition',lambda:False,True)
        record('no stale previous-call metadata on gate rejection',lambda:unknown.last_metadata is None,True)
        auth_db=root/'auth.sqlite';fake_ledger(auth_db)
        fail=FakePaidProvider(gate('authfailure'),'f'*64,ledger_path=auth_db,transport=httpx.MockTransport(lambda _:httpx.Response(401)))
        try:await fail.complete([{'role':'system','content':'Synthetic fixture'}])
        except EvaluationError as error:record('401 retained no raw errors',lambda:error.code,'MODEL_AUTH_ERROR')
        else:record('401 retained no raw errors',lambda:False,True)
        record('auth failure reservation retained',lambda:fail.ledger.snapshot()['unknown_or_pending_calls'],1)
        concurrency=root/'race.sqlite';fake_ledger(concurrency);race=ExistingLedger(_fake_path=concurrency);race_gate=gate('race',max_calls=1,max_cost_units=CAP)
        def reserve():
            try:return race.reserve(CAP,race_gate)
            except EvaluationError as error:return error.code
        with ThreadPoolExecutor(max_workers=2) as executor:r=list(executor.map(lambda _:reserve(),range(2)))
        record('concurrent shared cap allows one reservation',lambda:sum(v.startswith('eval_') for v in r),1)
        overrun=root/'overrun.sqlite';fake_ledger(overrun);over=ExistingLedger(_fake_path=overrun);call=over.reserve(1,gate('overrun'))
        record('overrun freezes and does not reset budget',lambda:rejects(lambda:over.settle(call,100,10,0),'COST_BOUND_EXCEEDED'))
        record('freeze state retained',lambda:over.snapshot()['frozen'],True)
        record('fake cannot use production ledger',lambda:rejects(lambda:FakePaidProvider(gate('forbidden'),'f'*64,ledger_path=PRODUCTION_LEDGER,transport=httpx.MockTransport(lambda _:response())),'FAKE_CANNOT_USE_PRODUCTION_LEDGER'))
        record('wrong paid base rejected before transport',lambda:rejects(lambda:FakePaidProvider(gate('wrongbase',base_url='https://example.invalid'),'f'*64,ledger_path=base,transport=httpx.MockTransport(lambda _:response())),'UNAPPROVED_PROVIDER_CONFIG'))
        record('wrong gate input rejected before transport',lambda:rejects(lambda:FakePaidProvider(gate('wronginput'),'a'*64,ledger_path=base,transport=httpx.MockTransport(lambda _:response())),'GATE_INPUT_MISMATCH'))
        record('expired gate rejected before transport',lambda:rejects(lambda:FakePaidProvider(gate('expired',expires_at='2000-01-01T00:00:00Z'),'f'*64,ledger_path=base,transport=httpx.MockTransport(lambda _:response())),'GATE_EXPIRED'))
        tight_db=root/'tight.sqlite';fake_ledger(tight_db)
        tight=FakePaidProvider(gate('tight',max_cost_units=1),'f'*64,ledger_path=tight_db,transport=httpx.MockTransport(lambda _:response()))
        try:await tight.complete([{'role':'system','content':'Synthetic fixture'}])
        except EvaluationError as error:record('run cost cap enforced before transport',lambda:error.code,'EVALUATION_GATE_EXHAUSTED')
        else:record('run cost cap enforced before transport',lambda:False,True)
        wrong_model_db=root/'wrong-model.sqlite';fake_ledger(wrong_model_db)
        wrong_model=FakePaidProvider(gate('wrongmodel'),'f'*64,ledger_path=wrong_model_db,transport=httpx.MockTransport(lambda _:response(model='unapproved-model')))
        try:await wrong_model.complete([{'role':'system','content':'Synthetic fixture'}])
        except EvaluationError as error:record('unapproved reported model stops',lambda:error.code,'UNAPPROVED_REPORTED_MODEL')
        else:record('unapproved reported model stops',lambda:False,True)
        record('reported model anomaly freezes shared client',lambda:wrong_model.ledger.snapshot()['frozen'],True)
        timeout_db=root/'timeout.sqlite';fake_ledger(timeout_db)
        def timeout_transport(request):raise httpx.ReadTimeout('Synthetic timeout',request=request)
        timeout_provider=FakePaidProvider(gate('timeout'),'f'*64,ledger_path=timeout_db,transport=httpx.MockTransport(timeout_transport))
        try:await timeout_provider.complete([{'role':'system','content':'Synthetic fixture'}])
        except EvaluationError as error:record('fake timeout stops no retries',lambda:error.code,'MODEL_TIMEOUT')
        else:record('fake timeout stops no retries',lambda:False,True)
        record('timeout unknown reservation retained',lambda:timeout_provider.ledger.snapshot()['unknown_or_pending_calls'],1)
        record('timeout one attempt only',lambda:timeout_provider.calls,1)
        # T26-EVAL-001: unknown/reserved in ANY shared scope or another gate
        # must prevent both entry preflight and atomic reservation/dispatch.
        uncertainty_matrix=[]
        for scope in ('game','experiments','probe','evaluation-current','evaluation-other'):
            for state in ('unknown','reserved'):
                matrix_db=root/(scope+'-'+state+'.sqlite');fake_ledger(matrix_db)
                current_gate=gate('matrix-'+scope.replace('evaluation-',''))
                stored_scope='evaluation' if scope.startswith('evaluation-') else scope
                stored_id=('eval_'+current_gate['approval_id']+'_1' if scope=='evaluation-current' else 'eval_othergate_1' if scope=='evaluation-other' else scope+'_old')
                with closing(sqlite3.connect(matrix_db)) as db:
                    db.execute("INSERT INTO budget_calls(id,scope,created_at,reserved,charged,state,reason) VALUES(?,?,?,1000,1000,?,'SYNTHETIC_PENDING')",
                               (stored_id,stored_scope,datetime.now(timezone.utc).isoformat(),state));db.commit()
                matrix_ledger=ExistingLedger(_fake_path=matrix_db)
                with closing(matrix_ledger._connect()) as db:before_rows=db.execute('SELECT * FROM budget_calls ORDER BY id').fetchall()
                record('shared preflight blocks '+scope+'/'+state,
                       lambda ledger=matrix_ledger:rejects(ledger.assert_ready,'PRIOR_CALL_UNKNOWN_STOP'))
                class CredentialReadForbidden:
                    def get(self,*args):raise AssertionError('Credential read attempted during blocked synthetic preflight')
                # Exercise the production constructor with an explicitly injected
                # owned fake ledger and an environment access trap: no credential
                # or production ledger can be touched by this Owner check.
                production_shape=gate('entry-'+scope.replace('evaluation-',''),approved_by='Main')
                with patch('evaluation.provider.ExistingLedger',return_value=matrix_ledger), patch('evaluation.provider.os.environ',CredentialReadForbidden()):
                    record('paid entry preflight before credential '+scope+'/'+state,
                           lambda production_shape=production_shape:rejects(lambda:PaidProvider(production_shape,'f'*64),'PRIOR_CALL_UNKNOWN_STOP'))
                dispatched=[]
                def matrix_transport(request):dispatched.append(request);return response()
                matrix_provider=FakePaidProvider(current_gate,'f'*64,ledger_path=matrix_db,transport=httpx.MockTransport(matrix_transport))
                blocked=None
                try:await matrix_provider.complete([{'role':'system','content':'Synthetic uncertainty boundary'}])
                except EvaluationError as error:blocked=error.code
                with closing(matrix_ledger._connect()) as db:after_rows=db.execute('SELECT * FROM budget_calls ORDER BY id').fetchall()
                observation={'scope':scope,'stored_scope':stored_scope,'state':state,'error':blocked,'transport_dispatches':len(dispatched),
                             'rows_before':len(before_rows),'rows_after':len(after_rows),'rows_unchanged':before_rows==after_rows,'provider_attempts':matrix_provider.calls}
                uncertainty_matrix.append(observation)
                record('shared atomic gate zero dispatch/no row '+scope+'/'+state,
                       lambda observation=observation:observation['error']=='PRIOR_CALL_UNKNOWN_STOP' and observation['transport_dispatches']==0
                           and observation['provider_attempts']==0 and observation['rows_unchanged'],True)
        settled_db=root/'settled-control.sqlite';fake_ledger(settled_db)
        with closing(sqlite3.connect(settled_db)) as db:
            for ordinal,scope in enumerate(('game','experiments','probe','evaluation')):
                db.execute("INSERT INTO budget_calls(id,scope,created_at,reserved,charged,state,prompt_tokens,completion_tokens,cache_hit_tokens) VALUES(?,?,?,2000,2000,'settled',1,0,0)",
                           ('settled-'+str(ordinal),scope,datetime.now(timezone.utc).isoformat()))
            db.commit()
        settled_ledger=ExistingLedger(_fake_path=settled_db)
        record('all-scope settled preflight allowed',lambda:settled_ledger.assert_ready()['unknown_or_pending_calls'],0)
        settled_dispatch=[]
        def settled_transport(request):settled_dispatch.append(request);return response()
        settled_provider=FakePaidProvider(gate('settled-control'),'f'*64,ledger_path=settled_db,transport=httpx.MockTransport(settled_transport))
        await settled_provider.complete([{'role':'system','content':'Synthetic known-settled control'}])
        record('all-scope settled allows one fake dispatch',lambda:len(settled_dispatch),1)
        record('all-scope settled adds one settled evaluation row',lambda:settled_ledger.snapshot()['calls'],5)
        record('settled control remains no pending',lambda:settled_ledger.snapshot()['unknown_or_pending_calls'],0)
        # Engine mock adversarial output tests use frozen real/fixture evidence.
        cases={c['case_id']:c for c in files['fixtures/cases.json']['cases']}
        k1=cases['K1-real-valid-evidence'];k4=cases['K4-failure-with-injection']
        bogus=dict(k1['mock_suggestion']);bogus['evidence_refs']=[{'evidence_id':'baseline_v1:FAKE','snippet':'summary'}]
        evaluator=Evaluator(tools,files,MockProvider([bogus]))
        value,audit=await evaluator.evaluate(k1['claim'])
        record('model fake citation rejected',lambda:value['status'],'INSUFFICIENT_EVIDENCE')
        record('fake citation validation recorded',lambda:audit['validation_errors'],['MODEL_FAKE_OR_UNREAD_REFERENCE'])
        # T26-EVAL-002: rejected values must never be reflected into persisted audit.
        marker='SYNTHETIC_AUDIT_REJECTION_ONLY'
        invalid_suggestions=[]
        extra=dict(k1['mock_suggestion']);extra['api_key']=marker
        invalid_suggestions.append(('unknown top-level field',extra))
        nested=dict(k1['mock_suggestion'])
        nested['evidence_refs']=[dict(k1['mock_suggestion']['evidence_refs'][0],api_key=marker)]
        invalid_suggestions.append(('unknown nested reference field',nested))
        invalid_reason=dict(k1['mock_suggestion']);invalid_reason['reason']={'api_key':marker}
        invalid_suggestions.append(('invalid reason shape',invalid_reason))
        invalid_text=dict(k1['mock_suggestion']);invalid_text['reason']=marker+'\x00'
        invalid_suggestions.append(('invalid reason text',invalid_text))
        for name,script in invalid_suggestions:
            evaluator=Evaluator(tools,files,MockProvider([script]))
            value,audit=await evaluator.evaluate(k1['claim'])
            record('invalid audit rejected '+name,lambda value=value:value['status'],'INSUFFICIENT_EVIDENCE')
            record('invalid audit raw absent '+name,lambda audit=audit:audit['raw_suggestion'] is None,True)
            record('invalid audit digest only '+name,
                   lambda audit=audit,script=script:audit['raw_suggestion_sha256']==sha256(json.dumps(script,ensure_ascii=False,allow_nan=False).encode('utf-8')),True)
            record('invalid audit no value persisted '+name,
                   lambda value=value,audit=audit:marker not in json.dumps({'output':value,'audit':audit}),True)
        invalid_db=root/'invalid-audit.sqlite';fake_ledger(invalid_db)
        invalid_provider=FakePaidProvider(gate('invalid-audit'),'f'*64,ledger_path=invalid_db,
            transport=httpx.MockTransport(lambda _:response(json.dumps(extra))))
        evaluator=Evaluator(tools,files,invalid_provider)
        value,audit=await evaluator.evaluate(k1['claim'])
        record('fake paid invalid audit returns insufficient',lambda:value['status'],'INSUFFICIENT_EVIDENCE')
        record('fake paid invalid audit raw absent',lambda:audit['raw_suggestion'] is None,True)
        record('fake paid invalid audit no value persisted',lambda:marker not in json.dumps({'output':value,'audit':audit}),True)
        evaluator=Evaluator(tools,files,MockProvider([k4['mock_suggestion']]))
        value,audit=await evaluator.evaluate(k4['claim'])
        record('K4 traverses mock LLM path',lambda:value['execution_scope']['actual_model_requests_this_claim'],1)
        record('K4 raw suggestion PASS retained',lambda:audit['raw_suggestion']['status'],'PASS')
        record('K4 deterministic FAIL dominates',lambda:value['status'],'FAIL')
        record('human signoff always null',lambda:value['human_signoff'] is None,True)
        # The transport fake also exercises the actual adapter -> engine JSON path.
        engine_db=root/'engine.sqlite';fake_ledger(engine_db)
        engine_provider=FakePaidProvider(gate('engine'),'f'*64,ledger_path=engine_db,
            transport=httpx.MockTransport(lambda _:response(json.dumps(k4['mock_suggestion']))))
        evaluator=Evaluator(tools,files,engine_provider)
        value,audit=await evaluator.evaluate(k4['claim'])
        record('fake paid adapter -> engine deterministic FAIL',lambda:value['status'],'FAIL')
        record('fake adapter does not certify paid judgement',lambda:value['execution_scope']['real_paid_judgement'],False)
    record('target modules absent from actual Python imports',lambda:any(k=='backend' or k.startswith(('backend.','tests.','scripts.')) for k in sys.modules),False)
    source_after={p.relative_to(EVALUATOR_ROOT).as_posix():sha256(p.read_bytes()) for p in sorted(EVALUATOR_ROOT.glob('*.py'))}
    record('evaluator source unchanged during Owner run',lambda:source_before==source_after,True)
    report={'kind':'Evaluator Owner local checks; not independent QA','command':[sys.executable,'-B','-X','utf8','-m','evaluation.check'],
            'executed_at':datetime.now(timezone.utc).isoformat(),'results':results,'passed':all(r['passed'] for r in results),
            'checks_count':len(results),'actual_paid_calls':0,'actual_network_calls':0,'production_ledger_opened':False,
            'target_modules_imported':False,'fixture_set_sha256':freeze['fixture_set_sha256'],
            'evaluator_source_sha256_before':source_before,'evaluator_source_sha256_after':source_after,
            'T26_EVAL_001_uncertainty_matrix':uncertainty_matrix,
            'fake_databases':'Owned temporary fixture files removed; never production ledger or committed artifacts.',
            'teacher_approval':None,'human_signoff':None}
    code=0 if report['passed'] else 1;report['exit_code']=code
    (folder/'owner-check.json').write_bytes(json_bytes(report))
    print('Owner checks',sum(r['passed'] for r in results),'/',len(results),'evidence',folder/'owner-check.json')
    for r in results:
        if not r['passed']:print('Failed:',r['name'],r.get('error_code',r.get('limitation')))
    return code


if __name__=='__main__':raise SystemExit(asyncio.run(main_async()))
