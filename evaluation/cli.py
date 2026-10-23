"""Independent evaluator CLI. Default is deterministic-only; paid gates are empty."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime,timezone
from pathlib import Path
import sys

from .common import EVALUATOR_ROOT, EvaluationError, identifier, json_bytes, sha256, strict_json
from .engine import Evaluator
from .provider import MockProvider, PaidProvider
from .reader import safe_read
from .trust import load_tools, source_precheck


def output_folder():
    folder=EVALUATOR_ROOT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True,exist_ok=False)
    return folder


def find_gate(approval_id,input_hash,purpose):
    identifier(approval_id)
    # This file is trusted evaluator-root configuration, not supplied by target CLI arguments.
    gates=strict_json(safe_read(EVALUATOR_ROOT,'trusted/paid-gates.json'))
    candidates=[v for v in gates.get('approvals',[]) if v.get('approval_id')==approval_id]
    if len(candidates)!=1 or candidates[0].get('purpose')!=purpose:raise EvaluationError('MAIN_FINITE_PAID_GO_REQUIRED')
    return PaidProvider(candidates[0],input_hash)


async def run(args):
    if getattr(args,'release',None)=='v5.0-engineering' or getattr(args,'fixture_set',None)=='v5-k1-k6-v1':
        from .v5 import run_v5
        return await run_v5(args)
    freeze,files,tools=load_tools()
    event=getattr(tools,'event_contexts',{}).get(getattr(args,'release',None))
    folder=output_folder()
    report={'command':[sys.executable,'-m','evaluation.cli',*sys.argv[1:]],'python':sys.version,
            'started':datetime.now(timezone.utc).isoformat(),'mode':getattr(args,'mode','deterministic'),
            'fixture_set_sha256':freeze['fixture_set_sha256'],'target_code_executed':False,'actual_paid_calls':0,
            'human_signoff':None,'teacher_approval':None,'limitations':['Owner checks are not independent QA or paid LLM calibration.']}
    if event:
        report['event']={'event_id':event.event_id,'release_id':event.release_id,
                         'product_commit':event.product_commit,'event_freeze_raw_sha256':event.input_sha256}
    if args.action=='precheck':
        precheck=source_precheck(tools,args.release);report['precheck']=precheck
        code=0 if not precheck['issues'] else 2
    else:
        calibration=args.action=='calibrate'
        if calibration:
            cases=files['fixtures/cases.json']['cases']
            if args.fixture_set!='k1-k6-v1':raise EvaluationError('UNKNOWN_FIXTURE_SET')
            input_hash=freeze['fixture_set_sha256']
            entries=[(c['claim'],c['contract_id'],c['contract_version'],c) for c in cases]
        else:
            if args.release=='baseline_v1':
                claims=files['trusted/claims-baseline-v1.json']['claims']
                input_hash=freeze['inputs']['trusted/claims-baseline-v1.json']
            elif event:
                preflight=source_precheck(tools,args.release)
                if preflight['issues']:raise EvaluationError('EVENT_IDENTITY_PRECHECK_FAILED')
                claims=event.claims;input_hash=event.input_sha256
            else:raise EvaluationError('UNKNOWN_RELEASE')
            entries=[(c,'campus-lab-engineering','1.0.0',None) for c in claims]
        provider=None
        if args.mode=='paid':
            if not args.approval_id:raise EvaluationError('MAIN_FINITE_PAID_GO_REQUIRED')
            provider=find_gate(args.approval_id,input_hash,'calibration' if calibration else 'claims')
        rows=[];audits=[];event_stopped=False
        evaluator=Evaluator(tools,files,provider)
        for claim,contract_id,version,case in entries:
            if args.mode=='mock':
                if case:script=case['mock_suggestion']
                else:script={'claim_id':claim['claim_id'],'release_id':claim['release_id'],'status':'INSUFFICIENT_EVIDENCE',
                             'evidence_refs':[{'evidence_id':r['evidence_id'],'snippet':r['snippet']} for r in claim['evidence_refs']],
                             'reason':'Scripted mock does not establish a paid or independent semantic assessment.','missing_check':['Run approved real evaluator judgement.']}
                evaluator.provider=MockProvider([script])
            if event_stopped:
                result=evaluator._output(claim,'INSUFFICIENT_EVIDENCE',[],
                    'EVENT_RUN_STOPPED_AFTER_IDENTITY_CHANGE',['Refreeze and independently verify the changed event inputs.'],'not_run')
                audit={'claim_id':claim['claim_id'],'raw_suggestion':None,'provider_metadata':None,
                       'validation_errors':['EVENT_RUN_STOPPED_AFTER_IDENTITY_CHANGE']}
            else:
                result,audit=await evaluator.evaluate(claim,contract_id,version)
                if event and evaluator.prechecks.get(args.release,{}).get('issues'):event_stopped=True
            if case:
                rows.append({'case_id':case['case_id'],'expected':case['expected'],'actual':result['status'],
                             'matches_expected':result['status']==case['expected'],'output':result})
                audit['case_id']=case['case_id']
            else:rows.append(result)
            audits.append(audit)
        report['results']=rows;report['audits']=audits;report['prechecks']=evaluator.prechecks
        if event:
            final_check=source_precheck(tools,args.release);report['event_final_precheck']=final_check
            if final_check['issues']:
                for result in rows:
                    result.update(status='INSUFFICIENT_EVIDENCE',evidence_refs=[],
                        reason='EVENT_IDENTITY_CHANGED_BEFORE_REPORT',
                        missing_check=['Refreeze and independently verify the changed event inputs.'])
                report['event_stopped_on_identity_change']=True
        report['actual_paid_calls']=len({r['provider_metadata']['call_id'] for r in audits if isinstance(r.get('provider_metadata'),dict)
                                       and r['provider_metadata'].get('actual_network_call') and r['provider_metadata'].get('call_id')})
        if calibration:
            report['calibration']={'case_count':len(rows),'matches':sum(v['matches_expected'] for v in rows),
                'false_pass':[v['case_id'] for v in rows if v['actual']=='PASS' and v['expected']!='PASS'],
                'wrong_failure':[v['case_id'] for v in rows if v['actual']=='FAIL' and v['expected']!='FAIL'],
                'unnecessary_abstention':[v['case_id'] for v in rows if v['actual']=='INSUFFICIENT_EVIDENCE' and v['expected'] in {'PASS','FAIL','NOT_APPLICABLE'}],
                'valid_reference_outputs':sum(bool(v['output']['evidence_refs']) for v in rows),
                'synthetic_inputs':True,'real_paid_calibration':args.mode=='paid'}
            code=0 if all(v['matches_expected'] for v in rows) else 1
        else:code=1 if any(v['status']=='FAIL' for v in rows) else 2 if any(v['status']=='INSUFFICIENT_EVIDENCE' for v in rows) else 0
    report['exit_code']=code;report['ended']=datetime.now(timezone.utc).isoformat()
    report['evaluator_source_sha256']={p.relative_to(EVALUATOR_ROOT).as_posix():sha256(p.read_bytes()) for p in sorted(EVALUATOR_ROOT.glob('*.py'))}
    path=folder/'report.json';path.write_bytes(json_bytes(report))
    print('Evidence:',path);print('Exit:',code,'; actual paid calls:',report['actual_paid_calls'])
    return code


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    pre=sub.add_parser('precheck');pre.add_argument('--release',required=True)
    for name in ('evaluate','calibrate'):
        p=sub.add_parser(name);p.add_argument('--mode',choices=['deterministic','mock','paid'],default='deterministic')
        p.add_argument('--approval-id')
        if name=='evaluate':p.add_argument('--release',required=True)
        else:p.add_argument('--fixture-set',required=True)
    args=parser.parse_args()
    try:return asyncio.run(run(args))
    except EvaluationError as error:
        folder=output_folder()
        path=folder/'stopped.json'
        path.write_bytes(json_bytes({'command':[sys.executable,'-m','evaluation.cli',*sys.argv[1:]],
                    'exit_code':2,'error_code':error.code,'actual_paid_calls':0,
                    'target_code_executed':False,'human_signoff':None,'teacher_approval':None}))
        print('Evaluator stopped:',error.code,'; evidence:',path);return 2


if __name__=='__main__':raise SystemExit(main())
