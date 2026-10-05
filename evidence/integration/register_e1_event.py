"""Main derives pinned E1 identities from immutable execution records and raw archive.

Source maps below retain their stated provenance; no reconstructed map is claimed
to be a separately captured immediate runtime before/after snapshot.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = '7821af4efe0613c20a80ea164c1dab1c0f288bab'
EVIDENCE_COMMIT = 'ab8aee96fa3376df68f9ffab257f4481236c66df'
RELEASE = 'E1-formal-v1'
EVENT = 'e1-formal-v1'
RUN = 'experiments/runs/20261005T053334004502Z-formal-real-48d972eb'
QA = 'evidence/qa/T25-independent-20261005T055600Z'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def load(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))

def git(*args):
    return subprocess.check_output(['git', '-c', 'safe.directory=D:/深度能力', *args], cwd=ROOT)

def write_new(path, value):
    target = ROOT/path
    if target.exists():
        raise ValueError('append-only registration already exists: '+path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def main():
    archive = load('evidence/integration/E1-source-archive-20261005.json')
    run = load(RUN+'/run.json')
    plan = load(RUN+'/plan.json')
    review = load(QA+'/result.json')
    accounting = load(RUN+'/source-timeout-accounting.json')
    if run['baseline']['commit'] != PRODUCT or not review['passed'] or review['checks'] != 1829:
        raise ValueError('independent accepted execution required')
    original = {p: v['raw_sha256'] for p,v in run['baseline']['sources'].items()}
    original.update(plan['freeze']['source_hashes'])
    if set(original) != set(archive['sources']):
        raise ValueError('original recorded runtime and archive source set differs')
    for p,h in original.items():
        a = archive['sources'][p]
        if a['raw_sha256'] != h or sha((ROOT/a['archive_path']).read_bytes()) != h:
            raise ValueError('raw archive mismatch: '+p)
    qa_path = 'tests/review_e1_results.py'
    qa_raw = (ROOT/qa_path).read_bytes()
    if sha(qa_raw) != 'a6432a28143a859f3b01f0eca329a3489b7bba1941112bcea3a634ade02b33ee':
        raise ValueError('QA stable source report mismatch')
    qa_archive = 'release/archives/baseline_v1/'+qa_path
    qa_target = ROOT/qa_archive
    if qa_target.exists():
        raise ValueError('new QA archive already exists')
    qa_target.parent.mkdir(parents=True, exist_ok=True)
    qa_target.write_bytes(qa_raw)
    qa_blob = git('show', EVIDENCE_COMMIT+':'+qa_path)
    canon = qa_raw.decode('utf-8').replace('\r\n','\n').encode('utf-8')
    if canon != qa_blob.decode('utf-8').replace('\r\n','\n').encode('utf-8'):
        raise ValueError('QA Git blob identity mismatch')
    records = dict(archive['sources'])
    records[qa_path] = {'archive_release_id':'baseline_v1', 'archive_path':qa_archive,
                        'raw_sha256':sha(qa_raw), 'git_source_commit':EVIDENCE_COMMIT,
                        'git_blob_oid':git('rev-parse',EVIDENCE_COMMIT+':'+qa_path).decode().strip(),
                        'git_blob_sha256':sha(qa_blob), 'utf8_lf_v1_sha256':sha(canon),
                        'binding':'raw_equal' if qa_blob == qa_raw else 'approved_crlf_to_lf_only'}
    artifacts = [
        ('SUMMARY',RUN+'/summary.json','execution',{'summary':{'kind':'json_fields','fields':['by_variant','row_count','phase','mode','run_id','limits']}}),
        ('RAW',RUN+'/raw.jsonl','execution',{'completed':{'kind':'lines','start':1,'count':2},'stopped':{'kind':'lines','start':23,'count':2}}),
        ('RUN',RUN+'/run.json','execution',{'scope':{'kind':'json_fields','fields':['run_id','phase','mode','planned','limitations']}}),
        ('PROCESS',RUN+'/process-result.json','execution',{'process':{'kind':'json_fields','fields':['actual_command','actual_exit_code','planned','completed','timeout','not_called','retries','extra_probes','stop_reason']}}),
        ('QA',QA+'/result.json','execution',{'verification':{'kind':'json_fields','fields':['task','passed','checks','failures','baseline_commit','summary_independent','limitations']}}),
        ('QA-PROCESS',QA+'/process-result.json','execution',{'process':{'kind':'lines','start':1,'count':20}}),
        ('PLAN',RUN+'/plan.json','support',{'controls':{'kind':'json_fields','fields':['controls','phase','planned']}}),
        ('INPUT-A',RUN+'/inputs/formal-C01-full_history-1.json','support',{'input':{'kind':'json_fields','fields':['messages']}}),
        ('INPUT-B',RUN+'/inputs/formal-C01-structured_summary-1.json','support',{'input':{'kind':'json_fields','fields':['messages']}}),
        ('REVIEW','review/findings/T25-independent-formal-20261005.md','support',{'review':{'kind':'lines','start':1,'count':55}}),
        ('ARCHIVE','evidence/integration/E1-source-archive-20261005.json','support',{'scope':{'kind':'json_fields','fields':['count','product_commit','experiment_commit','scope']}}),
    ]
    # Main identity records bind already-executed material, with explicit sources.
    formal_hashes = {RELEASE+':'+eid:sha((ROOT/p).read_bytes()) for eid,p,role,_ in artifacts if role=='execution' and not eid.startswith('QA')}
    qa_hashes = {RELEASE+':'+eid:sha((ROOT/p).read_bytes()) for eid,p,role,_ in artifacts if role=='execution' and eid.startswith('QA')}
    formal_after = {p:sha((ROOT/records[p]['archive_path']).read_bytes()) for p in original}
    qa_sources = dict(review['experiment_source_hashes']);qa_sources[qa_path]=sha(qa_raw)
    qa_after = {p:sha((ROOT/records[p]['archive_path']).read_bytes()) for p in qa_sources}
    if original != formal_after or qa_sources != qa_after:
        raise ValueError('captured/approved identity disagrees with actual archive')
    base_identity = {'release_id':RELEASE,'product_commit':PRODUCT,'exit_code':0,
                     'teacher_approval':None,'human_signoff':None,'derived_by':'Main',
                     'created_at':datetime.now(timezone.utc).isoformat()}
    formal_identity = dict(base_identity, source_before=original,source_after=formal_after,artifact_hashes=formal_hashes,
        provenance={'before_product':'Original formal run.baseline.sources: actual runner admission hashes before HTTP.',
                    'before_experiment':'Original formal plan.freeze.source_hashes; runner verified frozen implementation before HTTP.',
                    'after':'Main actual raw archival check after formal completion, before CH01, archive-E1-process exit0; 41 experiment hashes also match Owner source-timeout-accounting and independent T25.',
                    'scope':'Derived historical identity binding, not a separately captured immediate pre/post runner snapshot.',
                    'process_exit_basis':RUN+'/process-result.json; independent T25 verifies orderly stop, not 72 successful requests.',
                    'evidence_commit':EVIDENCE_COMMIT})
    qa_identity = dict(base_identity, source_before=qa_sources,source_after=qa_after,artifact_hashes=qa_hashes,
        provenance={'before':'Independent T25 result.experiment_source_hashes plus explicit stable QA source STOP hash; QA report/checks attest unchanged before/after audit.',
                    'after':'Main independently reads exact raw archive plus new QA source archive after T25 source STOP.',
                    'scope':'Derived identity for offline QA invocation; not invented immediate runtime snapshots.',
                    'actual_command':'C:\\Users\\liyh\\.conda\\envs\\1\\python.exe -B -X utf8 tests/review_e1_results.py --run '+RUN+' --formal-plan experiments/runs/20261002T125600594673Z-formal-plan-949ddff0 --output '+QA,
                    'process_exit_basis':QA+'/process-result.json','qa_paid_calls':0})
    for label,value in [('FORMAL-ID',formal_identity),('QA-ID',qa_identity)]:
        path='evidence/integration/event-'+EVENT+'-'+label.lower()+'.json'
        write_new(path,value)
        artifacts.append((label,path,'identity',{'scope':{'kind':'json_fields','fields':['release_id','product_commit','exit_code','provenance']}}))
    evidence=[];windows={};roles={};runtime=[]
    for eid,p,role,w in artifacts:
        ident=RELEASE+':'+eid;raw=(ROOT/p).read_bytes()
        record={'evidence_id':ident,'path':p,'release_id':RELEASE,'artifact_raw_sha256':sha(raw),'artifact_binding':'raw_equal'}
        if role != 'identity':
            blob=git('show',EVIDENCE_COMMIT+':'+p)
            c=raw.decode('utf-8').replace('\r\n','\n').encode('utf-8')
            if c != blob.decode('utf-8').replace('\r\n','\n').encode('utf-8'):
                raise ValueError('actual artifact differs from reviewed Git identity: '+p)
            record.update(artifact_git_blob_oid=git('rev-parse',EVIDENCE_COMMIT+':'+p).decode().strip(),
                          artifact_git_blob_sha256=sha(blob),artifact_utf8_lf_v1_sha256=sha(c),
                          artifact_source_commit=EVIDENCE_COMMIT,
                          artifact_binding='raw_equal' if blob==raw else 'approved_crlf_to_lf_only')
        evidence.append(record);windows[ident]=w;roles[ident]=role
        if role=='execution':
            isqa=eid.startswith('QA')
            runtime.append({'evidence_id':ident,'identity_evidence_id':RELEASE+(':QA-ID' if isqa else ':FORMAL-ID'),
                            'release_id_field':'release_id','commit_field':'product_commit','exit_code_field':'exit_code',
                            'source_before_field':'source_before','source_after_field':'source_after','artifact_hashes_field':'artifact_hashes',
                            'source_paths':sorted(qa_sources if isqa else original)})
    refs=[{'evidence_id':RELEASE+':'+eid,'snippet':snippet} for eid,snippet in
          [('SUMMARY','summary'),('RAW','stopped'),('QA','verification'),('REVIEW','review'),('INPUT-A','input'),('INPUT-B','input')]]
    statements={'A24':'分母与缺失解释正确；地面判定资料未送模型。','A26':'引用存在且指向所称版本；缺证不能被自动补写通过。'}
    claims=[{'claim_id':RELEASE+':'+criterion,'criterion_id':criterion,'release_id':RELEASE,
             'statement':statement,'declared_scope':'Fixed v1 next-action experiment; 72 planned terminal rows,22completed/1timeout/49not_called. No full-run, superiority, human signoff or independent supplier invoice claim.',
             'declared_na':False,'evidence_refs':refs,'known_scope_status':'INDEPENDENT_T25_SCOPE_ONLY_REVIEW_PENDING'} for criterion,statement in statements.items()]
    sources={v['archive_path']:{'candidate_runtime_raw_sha256':v['raw_sha256'],'git_blob_sha256':v['git_blob_sha256'],
                             'git_blob_oid':v['git_blob_oid'],'utf8_lf_v1_sha256':v['utf8_lf_v1_sha256'],
                             'binding':v['binding'],'evidence':[RELEASE+':FORMAL-ID' if p!=qa_path else RELEASE+':QA-ID']} for p,v in records.items()}
    registration={'schema_id':'event-registration-v1','event_id':EVENT,'release_id':RELEASE,'product_commit':PRODUCT,
        'approved_by':'Main','approved_at':datetime.now(timezone.utc).isoformat(),
        'manifest':{'release_id':RELEASE,'commit':PRODUCT,'sources':sources,'evidence':evidence,
                    'teacher_approval':None,'human_signoff':None,'limitations':['Archives read as historical raw bytes; archive was not executed.','Main derived identity provenance is explicit; original runtime records unchanged.','Complete formal three-repeat response target is not achieved.']},
        'claims':{'release_id':RELEASE,'claims':claims},'windows':windows,'evidence_roles':roles,'runtime_records':runtime,
        'coverage':[{'claim_id':c['claim_id'],'criterion_id':c['criterion_id'],'status':'full','gaps':[],
                     'required_refs':refs} for c in claims],
        'source_locations':{p:{'archive_release_id':'baseline_v1','archive_path':v['archive_path'],'raw_sha256':v['raw_sha256']} for p,v in records.items()},
        'teacher_approval':None,'human_signoff':None}
    Draft202012Validator(load('evaluation/schemas/event-registration-v1.schema.json')).validate(registration)
    path='evidence/integration/event-'+EVENT+'-registration.json'
    write_new(path,registration)
    print(json.dumps({'path':path,'raw_sha256':sha((ROOT/path).read_bytes()),'sources':len(sources),'claims':len(claims),'paid_calls':0}))

if __name__=='__main__':
    main()
