"""Trust roots are evaluator-owned and explicitly pinned by Main, never target-selected."""
from __future__ import annotations

from .common import EVALUATOR_ROOT, PROJECT_ROOT, EvaluationError, exact_keys, identifier, sha256, strict_json
from .reader import EvidenceTools, safe_read, verify_identity

MAIN_MANIFEST = ('evidence/integration/baseline_v1-manifest.json', '9c36943cbb6e4fe08b6e176445ba91835fafa79a2077c2155bbf8d613f8b07c1')
MAIN_ADDENDUM = ('evidence/integration/baseline_v1-identity-addendum-20261002.json', '0b181dda973d62cb3c212b4a85766fe576851f6afd98f19c8e5284e38c87ca53')
PRODUCT_COMMIT = '7821af4efe0613c20a80ea164c1dab1c0f288bab'
REVIEW_RECORDS = [
    ('baseline_v1:REV001','evidence/qa/T21-identity-correction-review-20261002.json','b1b514c95d2041e62b669cc9f05ee8f976b5224c19999312aade695d9fb45a50','c91ccd5b2c7c5079b1518d7e28db425d9835de3fcb87b94f1f4b5fdd3affd5e8'),
    ('baseline_v1:REV002','evidence/qa/T21-identity-review-20261002.json','1db7981fe052cb33d666496aaae0aa07401bc6c44aad4caefd3062624c5642e4','2c199afbaa7be87cd39f98743beb86f4e028c0a3eda1cd3f6038858560c91278'),
    ('baseline_v1:REV003','review/findings/T21-identity-review-20261002.md','1049010d4cdb5badf8158cedb8d9ab20d9370cf6d39f2f8d1d742e88ed93e0a4','1049010d4cdb5badf8158cedb8d9ab20d9370cf6d39f2f8d1d742e88ed93e0a4'),
    ('baseline_v1:REV004',MAIN_ADDENDUM[0],MAIN_ADDENDUM[1],'a6fdf2a7d252ab7fda52397678b53d31905a0838ab19c0d6e164c20791da70c3')]


def pinned_main(path_and_hash):
    path, digest = path_and_hash
    data = safe_read(PROJECT_ROOT,path)
    if sha256(data) != digest: raise EvaluationError('TRUSTED_MAIN_HASH_MISMATCH')
    return strict_json(data)


def approved_manifest():
    manifest=pinned_main(MAIN_MANIFEST)
    if manifest.get('release_id')!='baseline_v1' or manifest.get('commit')!=PRODUCT_COMMIT:
        raise EvaluationError('MAIN_RELEASE_MISMATCH')
    addendum=pinned_main(MAIN_ADDENDUM)
    if addendum.get('original_manifest_raw_sha256')!=MAIN_MANIFEST[1] or addendum.get('product_commit')!=PRODUCT_COMMIT or addendum.get('facts_authoritative_revision')!=2:
        raise EvaluationError('MAIN_ADDENDUM_MISMATCH')
    manifest['evidence']=manifest['evidence']+addendum['evidence']
    manifest['superseded_evidence_ids']=['baseline_v1:E012']
    manifest['facts_authoritative_evidence_id']='baseline_v1:ADD001'
    manifest['addendum_id']=addendum['addendum_id']
    for eid,path,raw,canon in REVIEW_RECORDS:
        manifest['evidence'].append({'evidence_id':eid,'release_id':'baseline_v1','path':path,
            'artifact_raw_sha256':raw,'artifact_git_blob_sha256':canon,'artifact_utf8_lf_v1_sha256':canon,
            'artifact_binding':'raw_equal' if raw==canon else 'approved_crlf_to_lf_only',
            'artifact_source_commit':'9702fe39432aa78fc7286f796aa11c616355ec84'})
    return manifest


def load_trusted():
    # freeze.json is part of the trusted evaluator installation, not a target manifest.
    freeze=strict_json(safe_read(EVALUATOR_ROOT,'trusted/freeze.json'))
    exact_keys(freeze,['freeze_id','inputs','fixture_set_sha256','frozen_before_calls','authority','teacher_approval','human_signoff'],['case_sha256','frozen_at'])
    if freeze['frozen_before_calls'] is not True or freeze['authority']!='Main implementation GO; evaluator-owned calibration inputs':
        raise EvaluationError('UNFROZEN_INPUTS')
    files={}
    for relative,digest in freeze['inputs'].items():
        if not relative.startswith(('trusted/','fixtures/','schemas/')): raise EvaluationError('UNSAFE_TRUSTED_INPUT')
        data=safe_read(EVALUATOR_ROOT,relative)
        if sha256(data)!=digest: raise EvaluationError('FROZEN_INPUT_HASH_MISMATCH')
        files[relative]=strict_json(data)
    return freeze,files


def load_tools():
    freeze,files=load_trusted()
    contract=files['trusted/contract.json']
    manifests={'baseline_v1':approved_manifest(), 'calibration_v1':files['fixtures/calibration-manifest.json']}
    windows=files['trusted/windows.json']
    # Main-added identity reviews are registered here; target data cannot add IDs.
    for eid,_,_,_ in REVIEW_RECORDS:
        windows[eid]={'summary':{'kind':'lines','start':1,'count':30}}
    known=set()
    for release,manifest in manifests.items():
        if manifest['release_id']!=release:raise EvaluationError('MANIFEST_RELEASE_MISMATCH')
        for record in manifest['evidence']:
            identifier(record['evidence_id'])
            if record['evidence_id'] in known or record['release_id']!=release:raise EvaluationError('DUPLICATE_OR_FOREIGN_EVIDENCE')
            known.add(record['evidence_id'])
    from jsonschema import Draft202012Validator
    Draft202012Validator(files['schemas/contract.schema.json']).validate(contract)
    for c in files['trusted/claims-baseline-v1.json']['claims']:
        Draft202012Validator(files['schemas/claim.schema.json']).validate(c)
    for manifest in manifests.values():
        Draft202012Validator(files['schemas/manifest.schema.json']).validate(manifest)
    cases=files['fixtures/cases.json']['cases']
    from .common import json_bytes
    if not freeze.get('case_sha256') or any(freeze['case_sha256'].get(c['case_id'])!=sha256(json_bytes(c)) for c in cases):
        raise EvaluationError('CASE_HASH_MISMATCH')
    from .events import load_registered_events
    contexts,event_manifests,event_windows=load_registered_events(PROJECT_ROOT,EVALUATOR_ROOT,files,manifests,windows)
    manifests.update(event_manifests);windows.update(event_windows)
    tools=EvidenceTools(PROJECT_ROOT,contract,manifests,windows)
    tools.event_contexts=contexts
    return freeze,files,tools


def source_precheck(tools, release):
    if release not in tools.manifests: raise EvaluationError('UNKNOWN_RELEASE')
    if release in getattr(tools,'event_contexts',{}):
        return tools.event_contexts[release].precheck(tools)
    manifest=tools.manifests[release]
    identities={};issues=[];historical=[];runtime_bindings=[]
    archive=None
    if release=='baseline_v1':
        from .baseline_archive import load_baseline_archive
        try:archive=load_baseline_archive(tools.root,tools.root/'evaluation',manifest)
        except EvaluationError as error:issues.append({'code':error.code})
    for path,record in manifest.get('sources',{}).items():
        try:
            if release=='baseline_v1':
                if archive is None:raise EvaluationError('BASELINE_ARCHIVE_IDENTITY_UNAVAILABLE')
                from .baseline_archive import read_baseline_source
                data=read_baseline_source(tools.root,path,record,archive)
            else:data=safe_read(tools.root,path)
            identities[path]=verify_identity(data,record,source=True)
            if archive:identities[path]['read_path']=archive['locations'][path]['archive_path']
        except EvaluationError as error:issues.append({'path':path,'code':error.code})
    # Preserve explicit historical exclusions; do not represent these as a match.
    for entry in manifest.get('unbound_prior_source_records',[]):
        historical.append({'evidence':entry['evidence'],'path':entry['path'],
                           'recorded_raw_sha256':entry['recorded_raw_sha256'],
                           'current_raw_sha256':entry['current_raw_sha256'],'binding':entry['binding']})
    for record in manifest['evidence']:
        try:
            data=safe_read(tools.root,record['path']);verify_identity(data,record)
            if record['path'].endswith(('run.json','summary.json')):
                value=strict_json(data)
                before=value.get('source_sha256_before');after=value.get('source_sha256_after')
                if before is not None or after is not None:
                    if not isinstance(before,dict) or not isinstance(after,dict) or before!=after:
                        issues.append({'evidence_id':record['evidence_id'],'code':'RUNTIME_SOURCE_CHANGED_OR_MISSING_MAP'})
                    raw_map=before if isinstance(before,dict) else {}
                else:raw_map=value.get('source_hashes',{})
                if not isinstance(raw_map,dict):raise EvaluationError('INVALID_RUNTIME_HASH_MAP')
                for path,digest in raw_map.items():
                    source=manifest.get('sources',{}).get(path)
                    generated=manifest.get('generated_artifacts',{}).get(path)
                    excluded=next((v for v in historical if v['evidence']==record['path'] and v['path']==path and v['recorded_raw_sha256']==digest),None)
                    if source and source['candidate_runtime_raw_sha256']==digest:binding='exact_recorded_runtime_hash_bound'
                    elif generated and generated['runtime_raw_sha256']==digest:binding='runtime_build_artifact_only'
                    elif excluded:binding='historical_unbound_not_same_runtime_bytes'
                    else:
                        binding='unregistered_or_mismatched_runtime_hash'
                        issues.append({'evidence_id':record['evidence_id'],'path':path,'code':'RUNTIME_HASH_NOT_BOUND'})
                    runtime_bindings.append({'evidence_id':record['evidence_id'],'path':path,'recorded_raw_sha256':digest,'binding':binding})
        except EvaluationError as error:issues.append({'evidence_id':record['evidence_id'],'code':error.code})
    generated=[]
    for path,record in manifest.get('generated_artifacts',{}).items():
        try:
            digest=sha256(safe_read(tools.root,path))
            generated.append({'path':path,'status':'runtime_raw_match' if digest==record['runtime_raw_sha256'] else 'runtime_hash_mismatch',
                              'binding':record['binding'],'raw_sha256':digest})
        except EvaluationError as error:generated.append({'path':path,'status':error.code,'binding':record['binding']})
    return {'release_id':release,'source_identities':identities,'issues':issues,
            'historical_unbound_records':historical,'generated_runtime_only':generated,
            'runtime_source_bindings':runtime_bindings,
            'baseline_source_archive':archive,
            'scope':'Read and hash only; target tests/scripts were not executed; no Git command or target module imported.'}
