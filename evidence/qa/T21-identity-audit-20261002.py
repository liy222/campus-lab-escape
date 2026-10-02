"""Independent read-only Git/content identity review. No app imports/env/test runs."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/'evidence/integration/baseline_v1-manifest.json'
EXPECTED_MANIFEST_RAW='9c36943cbb6e4fe08b6e176445ba91835fafa79a2077c2155bbf8d613f8b07c1'
CODE='7821af4efe0613c20a80ea164c1dab1c0f288bab'
METADATA='1fe091b3310021f697a0f0fc3a8ac3b8c0fecba4'
commands=[]
def git(*args, expected=0):
    command=['git','-c',f'safe.directory={ROOT.as_posix()}',*args]
    result=subprocess.run(command,cwd=ROOT,capture_output=True)
    commands.append({'command':command,'actual_exit_code':result.returncode})
    assert result.returncode==expected, 'Unexpected read-only Git command outcome'
    return result.stdout
def sha(raw):return hashlib.sha256(raw).hexdigest()
def lf(raw):
    raw.decode('utf-8',errors='strict')
    return raw.replace(b'\r\n',b'\n')  # Byte-level CRLF only, no EOF/BOM changes.
def safe(path):
    value=(ROOT/path).resolve()
    value.relative_to(ROOT)
    assert value.name!='.env' and value.suffix.lower() not in {'.sqlite','.sqlite3','.db'}
    return value
def source_map(payload):
    before=payload.get('source_sha256_before',payload.get('source_hashes',{}))
    after=payload.get('source_sha256_after',before if payload.get('source_unchanged') else {})
    assert before==after
    return {name.replace('\\','/'):digest for name,digest in before.items()}

raw=MANIFEST.read_bytes();manifest=json.loads(raw)
assert sha(raw)==EXPECTED_MANIFEST_RAW
assert manifest['commit']==CODE
head=git('rev-parse','HEAD').decode().strip()
assert head==METADATA
assert git('rev-parse','refs/tags/baseline_v1^{commit}').decode().strip()==CODE
assert git('rev-parse',CODE+'^{tree}').decode().strip()==manifest['tree']
git('merge-base','--is-ancestor',CODE,METADATA)
remote=git('ls-remote','origin','refs/heads/main','refs/tags/baseline_v1').decode().strip()
remote_map={reference:oid for oid,reference in (line.split() for line in remote.splitlines())}
assert remote_map['refs/heads/main']==METADATA and remote_map['refs/tags/baseline_v1']==CODE
metadata_manifest=git('show',METADATA+':evidence/integration/baseline_v1-manifest.json')
assert lf(metadata_manifest)==lf(raw)

sources=[];artifacts=[];generated=[];unbound=[];cached={}
def payload(path):
    if path not in cached:cached[path]=json.loads(safe(path).read_bytes())
    return cached[path]
for path,record in manifest['sources'].items():
    current=safe(path).read_bytes();blob=git('show',CODE+':'+path)
    oid=git('rev-parse',CODE+':'+path).decode().strip()
    metadata_blob=git('show',METADATA+':'+path)
    assert current and sha(current)==record['candidate_runtime_raw_sha256']
    assert sha(blob)==record['git_blob_sha256'] and oid==record['git_blob_oid']
    assert hashlib.sha1(b'blob '+str(len(blob)).encode()+b'\0'+blob).hexdigest()==oid
    assert sha(lf(current))==record['utf8_lf_v1_sha256'] and lf(current)==lf(blob)
    assert metadata_blob==blob
    binding='raw_equal' if current==blob else 'approved_crlf_to_lf_only'
    assert binding==record['binding']
    for evidence in record['evidence']:
        assert source_map(payload(evidence))[path]==sha(current)
    sources.append({'path':path,'recorded_runtime_raw_sha256':record['candidate_runtime_raw_sha256'],
      'current_raw_sha256':sha(current),'code_commit_blob_sha256':sha(blob),'git_blob_oid':oid,
      'utf8_lf_v1_sha256':sha(lf(current)),'binding':binding,'metadata_product_blob_unchanged':True})
for record in manifest['evidence']:
    path=record['path'];current=safe(path).read_bytes();blob=git('show',CODE+':'+path)
    oid=git('rev-parse',CODE+':'+path).decode().strip()
    assert sha(current)==record['artifact_raw_sha256']
    assert sha(blob)==record['artifact_git_blob_sha256'] and oid==record['artifact_git_blob_oid']
    assert sha(lf(current))==record['artifact_utf8_lf_v1_sha256'] and lf(current)==lf(blob)
    assert git('show',METADATA+':'+path)==blob
    binding='raw_equal' if current==blob else 'approved_crlf_to_lf_only'
    assert binding==record['artifact_binding']
    artifacts.append({'evidence_id':record['evidence_id'],'path':path,
      'original_recorded_raw_sha256':record['artifact_raw_sha256'],'current_raw_sha256':sha(current),
      'git_blob_sha256':sha(blob),'git_blob_oid':oid,'utf8_lf_v1_sha256':sha(lf(current)),
      'binding':binding,'metadata_artifact_blob_unchanged':True})
for path,record in manifest['generated_artifacts'].items():
    current=safe(path).read_bytes()
    assert sha(current)==record['runtime_raw_sha256']
    git('check-ignore','-q',path)
    git('cat-file','-e',CODE+':'+path,expected=128)
    for evidence in record['evidence']:
        assert source_map(payload(evidence))[path]==sha(current)
    generated.append({'path':path,'recorded_runtime_raw_sha256':record['runtime_raw_sha256'],
                      'current_raw_sha256':sha(current),'ignored':True,'code_commit_blob_present':False})
for record in manifest['unbound_prior_source_records']:
    path=record['path'];current=safe(path).read_bytes()
    assert path in {'tests/api/test_r1.py','tests/api/test_m2.py','tests/api/test_m3.py'}
    assert source_map(payload(record['evidence']))[path]==record['recorded_raw_sha256']
    assert sha(current)==record['current_raw_sha256'] and sha(current)!=record['recorded_raw_sha256']
    assert manifest['sources'][path]['candidate_runtime_raw_sha256']==sha(current)
    unbound.append({**record,'independent_current_raw_sha256':sha(current),'historical_identity_bound':False})
assert len(sources)==60 and len(artifacts)==14 and len(generated)==3 and len(unbound)==6
all_recorded_mismatches=[];browser_identity=[]
for evidence in ['evidence/qa/20261002T115503579Z-m3-browser/run.json','evidence/qa/20261002T115601621Z-m2-browser/run.json']:
    snapshot=source_map(payload(evidence))
    for path,recorded in snapshot.items():
        current=safe(path).read_bytes()
        if sha(current)!=recorded:all_recorded_mismatches.append((evidence,path))
        if path.startswith('tests/e2e/'):
            assert sha(current)==recorded
            browser_identity.append({'evidence':evidence,'runner':path,'raw_sha256':recorded,'unchanged':True})
assert Counter(all_recorded_mismatches)==Counter((r['evidence'],r['path']) for r in unbound)
helper=safe(manifest['builder_command'][1]).read_bytes()
assert sha(helper)==manifest['builder_raw_sha256']
helper_metadata=git('show',METADATA+':'+manifest['builder_command'][1])
assert lf(helper)==lf(helper_metadata)
attempts=[payload('evidence/integration/freeze-v1-attempt1.json'),payload('evidence/integration/freeze-v1-attempt2.json')]
assert [r['exit_code'] for r in attempts]==[1,1]
assert all(not r['manifest_created'] and not r['product_source_changed'] for r in attempts)

acceptance=payload('evidence/integration/acceptance-M3.json')
rows=acceptance['acceptance']
assert {r['acceptance_id'] for r in rows}=={f'A{i:02}' for i in range(1,29)}
statuses={r['acceptance_id']:r['status'] for r in rows}
assert all(statuses[k]=='NOT_RUN' for k in ('A24','A25','A27','A28'))
assert all(statuses[k]=='PARTIAL_SCOPE' for k in ('A11','A17','A26'))
assert acceptance['human_signoff'] is None and manifest['human_signoff'] is None and manifest['teacher_approval'] is None
assert acceptance['real_scope']['turns']==1 and acceptance['real_scope']['actual_calls']==2
assert acceptance['real_scope']['forced_first_tool']=='get_inventory'
assert acceptance['real_scope']['provider_bill_verified'] is False and acceptance['real_scope']['human_player'] is False
findings=[]
if 'no gameAI' in acceptance.get('paid_scope',''):
    findings.append({'id':'T21-DOC-001','priority':'P2','path':'evidence/integration/acceptance-M3.json',
      'field':'paid_scope','observed_value':acceptance['paid_scope'],
      'reason':'Legacy paid_scope contradicts real_scope and recorded accepted controlled gameplay AI. Correct through explicit superseding metadata, not by claiming old raw hash unchanged.'})
result={'review':'T21 independent identity-only review','command':[sys.executable,str(Path(__file__).resolve())],
 'actual_exit_code':0,'started_from_main_expected_head':METADATA,'observed_head':head,'code_commit':CODE,
 'code_tree':manifest['tree'],'remote_refs':remote_map,'manifest_recorded_raw_sha256':EXPECTED_MANIFEST_RAW,
 'manifest_current_raw_sha256':sha(raw),'manifest_metadata_blob_sha256':sha(metadata_manifest),
 'sources':sources,'source_binding_counts':dict(Counter(r['binding'] for r in sources)),
 'artifacts':artifacts,'artifact_binding_counts':dict(Counter(r['binding'] for r in artifacts)),
 'generated_runtime_only':generated,'unbound_prior_QA_harness_records':unbound,'browser_runner_identity':browser_identity,
 'builder':{'path':manifest['builder_command'][1],'recorded_raw_sha256':manifest['builder_raw_sha256'],'current_raw_sha256':sha(helper),
            'metadata_blob_sha256':sha(helper_metadata),'recorded_command':manifest['builder_command'],'failed_attempt_records':attempts},
 'acceptance_statuses':statuses,'findings':findings,'git_commands':commands,
 'ended':datetime.now(timezone.utc).isoformat(),
 'limitations':['Identity review only; no product tests rerun, no application imports, no .env/ledger/credentials/model calls.',
 'Canonical LF identity never asserts raw equality; all exact original/current/Git hashes remain separate.',
 'Failed helper attempt records are reviewed claims; historical helper bytes are not all independently recoverable from these two records.',
 'Historical browser QA Python test hashes remain unbound; only unchanged actual browser runners/product sources support browser scope.',
 'T22 experiments/evaluation implementations were not reviewed or accepted.']}
out=ROOT/'evidence/qa/T21-identity-review-20261002.json'
out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'actual_exit_code':0,'evidence':out.relative_to(ROOT).as_posix(),'sources':len(sources),'artifacts':len(artifacts),
 'source_binding_counts':result['source_binding_counts'],'artifact_binding_counts':result['artifact_binding_counts'],
 'generated':len(generated),'unbound_harness_records':len(unbound),'findings':findings},ensure_ascii=False))
