"""Owner checks for the sole Main-pinned legacy archive; no target execution or paid calls."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile

from .baseline_archive import (MAIN_ARCHIVE_PATH, POINTER, POINTER_PATH,
                               load_baseline_archive, read_baseline_source, validate_archive_record)
from .cli import output_folder
from .common import EVALUATOR_ROOT, PROJECT_ROOT, EvaluationError, json_bytes, sha256, strict_json
from .provider import MockProvider
from .engine import Evaluator
from .trust import load_tools, source_precheck


async def run():
    folder=output_folder();results=[]
    before={p.relative_to(EVALUATOR_ROOT).as_posix():sha256(p.read_bytes()) for p in EVALUATOR_ROOT.glob('*.py')}
    _,files,tools=load_tools();manifest=tools.manifests['baseline_v1']
    main_raw=(PROJECT_ROOT/MAIN_ARCHIVE_PATH).read_bytes();record=strict_json(main_raw)
    archive=load_baseline_archive(PROJECT_ROOT,EVALUATOR_ROOT,manifest)
    def check(name,action,expected=True):
        try:
            actual=action()
            if actual!=expected:raise AssertionError()
            results.append({'name':name,'passed':True,'actual':actual})
        except Exception as error:results.append({'name':name,'passed':False,'error_code':error.code if isinstance(error,EvaluationError) else type(error).__name__})
    def rejects(action,code):
        try:action()
        except EvaluationError as error:return error.code==code
        return False
    pre=source_precheck(tools,'baseline_v1')
    check('legacy source precheck reads archive successfully',lambda:pre['issues'],[])
    check('exact 60 source aliases and excluded 41 experiment sources',lambda:(len(archive['locations']),archive['experiment_sources_excluded']),(60,41))
    check('runtime recorded maps still bind original source paths',lambda:all(v['binding']!='unregistered_or_mismatched_runtime_hash' for v in pre['runtime_source_bindings']))
    check('source report discloses archive read, no execution',lambda:all(v['read_path']=='release/archives/baseline_v1/'+p for p,v in pre['source_identities'].items()) and not archive['archive_executed'])
    first=next(iter(manifest['sources']))
    mutations=[
        ('wrong product commit',lambda v:v.update(product_commit='0'*40),'BASELINE_ARCHIVE_VERSION_MISMATCH'),
        ('wrong original manifest pin',lambda v:v.update(baseline_manifest_raw_sha256='0'*64),'BASELINE_ARCHIVE_MANIFEST_PIN_MISMATCH'),
        ('wrong raw source',lambda v:v['sources'][first].update(raw_sha256='0'*64),'BASELINE_ARCHIVE_GIT_OR_RAW_IDENTITY_MISMATCH'),
        ('wrong Git blob OID',lambda v:v['sources'][first].update(git_blob_oid='0'*40),'BASELINE_ARCHIVE_GIT_OR_RAW_IDENTITY_MISMATCH'),
        ('wrong Git blob sha',lambda v:v['sources'][first].update(git_blob_sha256='0'*64),'BASELINE_ARCHIVE_GIT_OR_RAW_IDENTITY_MISMATCH'),
        ('wrong canonical identity',lambda v:v['sources'][first].update(utf8_lf_v1_sha256='0'*64),'BASELINE_ARCHIVE_GIT_OR_RAW_IDENTITY_MISMATCH'),
        ('arbitrary alias path',lambda v:v['sources'][first].update(archive_path='other/'+first),'BASELINE_ARCHIVE_PATH_NOT_FIXED'),
        ('missing baseline source',lambda v:v['sources'][first].update(git_source_commit=v['experiment_commit']),'BASELINE_ARCHIVE_SOURCE_SET_MISMATCH'),
        ('unknown source instead of original',lambda v:v['sources'].update({'unknown/source.py':v['sources'].pop(first)}),'BASELINE_ARCHIVE_SOURCE_SET_MISMATCH'),
        ('extra baseline source from experiment',lambda v:v['sources'][next(p for p,x in v['sources'].items() if x['git_source_commit']==v['experiment_commit'])].update(git_source_commit=v['product_commit']),'BASELINE_ARCHIVE_SOURCE_SET_MISMATCH'),
        ('bool collection count',lambda v:v.update(count=True),'BASELINE_ARCHIVE_COLLECTION_INVALID'),
    ]
    for name,mutate,code in mutations:
        value=deepcopy(record);mutate(value)
        check('reject '+name,lambda value=value,code=code:rejects(lambda:validate_archive_record(value,manifest),code))
    with tempfile.TemporaryDirectory(prefix='baseline-archive-owner-',dir=folder) as owned:
        root=Path(owned);assert root.resolve().is_relative_to(folder.resolve())
        install=root/'evaluation';(install/'trusted').mkdir(parents=True)
        (install/POINTER_PATH).write_bytes(json_bytes(dict(POINTER,main_archive={'path':'arbitrary.json','raw_sha256':'0'*64})))
        check('target cannot select a pointer',lambda:rejects(lambda:load_baseline_archive(root,install,manifest),'BASELINE_ARCHIVE_POINTER_NOT_APPROVED'))
        (install/POINTER_PATH).write_bytes(json_bytes(POINTER));main_path=root/MAIN_ARCHIVE_PATH;main_path.parent.mkdir(parents=True)
        main_path.write_bytes(main_raw+b'\n')
        check('Main record must have exact raw pin',lambda:rejects(lambda:load_baseline_archive(root,install,manifest),'BASELINE_ARCHIVE_MAIN_RAW_HASH_MISMATCH'))
        main_path.write_bytes(main_raw);fake=load_baseline_archive(root,install,manifest)
        path=next(p for p in manifest['sources'] if b'\r\n' in (PROJECT_ROOT/fake['locations'][p]['archive_path']).read_bytes())
        original=manifest['sources'][path];destination=root/fake['locations'][path]['archive_path'];destination.parent.mkdir(parents=True)
        data=(PROJECT_ROOT/fake['locations'][path]['archive_path']).read_bytes();destination.write_bytes(data)
        current=root/path;current.parent.mkdir(parents=True,exist_ok=True);current.write_bytes(b'# synthetic current v2\n')
        check('current v2 ignored, exact archived original still read',lambda:read_baseline_source(root,path,original,fake)==data)
        destination.write_bytes(data.replace(b'\r\n',b'\n'))
        check('archive CRLF change has no canonical fallback',lambda:rejects(lambda:read_baseline_source(root,path,original,fake),'BASELINE_ARCHIVE_RUNTIME_RAW_MISMATCH'))
        check('unknown source has no arbitrary alias',lambda:rejects(lambda:read_baseline_source(root,'unknown.py',original,fake),'BASELINE_ARCHIVE_SOURCE_NOT_REGISTERED'))
    case=next(c for c in files['fixtures/cases.json']['cases'] if c['case_id']=='K1-real-valid-evidence')
    provider=MockProvider([case['mock_suggestion']]);evaluator=Evaluator(tools,files,provider)
    out,audit=await evaluator.evaluate(case['claim'])
    check('frozen K1 enters full mock model path',lambda:(out['status'],provider.calls,audit['raw_suggestion']['status']),('PASS',1,'PASS'))
    check('original frozen K1 refs retained',lambda:len(out['evidence_refs'])==len(case['claim']['evidence_refs']))
    after={p.relative_to(EVALUATOR_ROOT).as_posix():sha256(p.read_bytes()) for p in EVALUATOR_ROOT.glob('*.py')}
    check('stable evaluator sources',lambda:before==after)
    check('no target modules imported',lambda:not any(k=='backend' or k.startswith(('backend.','experiments.','tests.','scripts.')) for k in sys.modules))
    report={'kind':'Owner legacy archive read/hash and synthetic counterexamples; not independent QA or archive execution',
            'command':[sys.executable,'-B','-X','utf8','-m','evaluation.check_baseline_archive'],
            'executed_at':datetime.now(timezone.utc).isoformat(),'checks_count':len(results),'results':results,
            'source_sha256_before':before,'source_sha256_after':after,'archive_proof':archive,
            'actual_paid_calls':0,'network_calls':0,'credentials_read':False,'production_ledger_opened':False,
            'target_modules_imported':False,'target_code_executed':False,'archive_executed':False,'human_signoff':None,'teacher_approval':None}
    code=0 if all(r['passed'] for r in results) else 1;report['exit_code']=code
    (folder/'baseline-archive-owner-check.json').write_bytes(json_bytes(report))
    print('Baseline archive Owner checks',sum(r['passed'] for r in results),'/',len(results),'evidence',folder/'baseline-archive-owner-check.json')
    for result in results:
        if not result['passed']:print('Failed:',result['name'],result.get('error_code'))
    return code


if __name__=='__main__':
    import asyncio
    raise SystemExit(asyncio.run(run()))
