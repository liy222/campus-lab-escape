"""Read-only follow-up for additive metadata correction; preserves initial review."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
CODE='7821af4efe0613c20a80ea164c1dab1c0f288bab'
REVISION='b1bff748c2ff91c30c143cb529d04f5640659508'
ADDENDUM='evidence/integration/baseline_v1-identity-addendum-20261002.json'
EXPECTED_ADDENDUM='0b181dda973d62cb3c212b4a85766fe576851f6afd98f19c8e5284e38c87ca53'
commands=[]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def lf(raw):
    raw.decode('utf-8',errors='strict')
    return raw.replace(b'\r\n',b'\n')
def data(path):return json.loads((ROOT/path).read_bytes())
def git(*args):
    command=['git','-c',f'safe.directory={ROOT.as_posix()}',*args]
    result=subprocess.run(command,cwd=ROOT,capture_output=True)
    commands.append({'command':command,'actual_exit_code':result.returncode})
    assert result.returncode==0
    return result.stdout

initial_path=ROOT/'evidence/qa/T21-identity-review-20261002.json'
initial_hash=sha(initial_path.read_bytes())
manifest_path=ROOT/'evidence/integration/baseline_v1-manifest.json'
manifest_raw=manifest_path.read_bytes();manifest=json.loads(manifest_raw)
assert sha(manifest_raw)=='9c36943cbb6e4fe08b6e176445ba91835fafa79a2077c2155bbf8d613f8b07c1'
addendum_raw=(ROOT/ADDENDUM).read_bytes();addendum=json.loads(addendum_raw)
assert sha(addendum_raw)==EXPECTED_ADDENDUM
assert addendum['original_manifest_raw_sha256']==sha(manifest_raw) and addendum['original_manifest_not_modified']
assert addendum['product_commit']==CODE and addendum['facts_authoritative_revision']==2
assert addendum['teacher_approval'] is None and addendum['human_signoff'] is None
assert 'T21-META-001' in addendum['reason'] and 'T21-DOC-001' in addendum['reason']
assert git('rev-parse','HEAD').decode().strip()==REVISION
assert git('rev-parse','baseline_v1^{commit}').decode().strip()==CODE
git('merge-base','--is-ancestor',CODE,REVISION)
new_artifacts=[]
for record in addendum['evidence']:
    path=record['path'];raw=(ROOT/path).read_bytes()
    assert record['artifact_source_commit']==REVISION
    blob=git('show',REVISION+':'+path)
    oid=git('rev-parse',REVISION+':'+path).decode().strip()
    assert sha(raw)==record['artifact_raw_sha256']
    assert sha(blob)==record['artifact_git_blob_sha256'] and oid==record['artifact_git_blob_oid']
    assert hashlib.sha1(b'blob '+str(len(blob)).encode()+b'\0'+blob).hexdigest()==oid
    assert lf(raw)==lf(blob) and sha(lf(raw))==record['artifact_utf8_lf_v1_sha256']
    assert raw!=blob and record['artifact_binding']=='approved_crlf_to_lf_only'
    new_artifacts.append({'path':path,'source_commit':REVISION,'recorded_raw_sha256':record['artifact_raw_sha256'],
      'current_raw_sha256':sha(raw),'git_blob_sha256':sha(blob),'git_blob_oid':oid,
      'utf8_lf_v1_sha256':sha(lf(raw)),'raw_equal':False,'canonical_equal':True})
assert len(new_artifacts)==2
preserved=[]
for record in manifest['evidence']:
    path=record['path'];raw=(ROOT/path).read_bytes();blob=git('show',REVISION+':'+path)
    assert sha(raw)==record['artifact_raw_sha256'] and sha(blob)==record['artifact_git_blob_sha256']
    preserved.append({'path':path,'original_raw_sha256':record['artifact_raw_sha256'],'current_raw_sha256':sha(raw),'unchanged':True})
for path,record in manifest['sources'].items():
    assert sha((ROOT/path).read_bytes())==record['candidate_runtime_raw_sha256']
    assert sha(git('show',REVISION+':'+path))==record['git_blob_sha256']
assert lf(git('show',REVISION+':evidence/integration/baseline_v1-manifest.json'))==lf(manifest_raw)
old=data('evidence/integration/acceptance-M3.json');new=data('evidence/integration/acceptance-M3-v2.json')
correction=data('evidence/integration/T21-META-001-correction.json')
assert correction['finding_id']=='T21-META-001'
assert correction['original_raw_sha256']==sha((ROOT/correction['original_artifact']).read_bytes())
assert correction['corrected_raw_sha256']==sha((ROOT/correction['corrected_artifact']).read_bytes())
assert new['commit']==CODE and new['facts_revision']==2
assert new['supersedes_facts_raw_sha256']==correction['original_raw_sha256']
assert new['acceptance']==old['acceptance'] and new['real_scope']==old['real_scope']
assert new['human_signoff'] is None and 'human acceptance not provided' in new['paid_scope']
assert 'controlledT18game1turn/2requests' in new['paid_scope'] and 'firstforcedget_inventory' in new['paid_scope']
assert 'E1/evaluator paid calls not yet run' in new['paid_scope']
assert 'pursuit excluded by direct user request' in new['open_human_course'][0]
assert {r['acceptance_id']:r['status'] for r in new['acceptance']}=={r['acceptance_id']:r['status'] for r in old['acceptance']}
real=data('evidence/qa/20261002T120735404563Z-m3-real/run.json')
before,after=real['ledger_before'],real['ledger_after']
assert real['exit_code']==0 and real['actual_provider_attempts']==2
assert len(before['calls'])==4 and len(after['calls'])==6 and all(r['state']=='settled' for r in after['calls'])
assert all(r['scope']=='probe' for r in before['calls'])
assert len(real['actual_new_ledger_rows'])==2 and all(r['scope']=='game' for r in real['actual_new_ledger_rows'])
assert after['charged_units']==10_354_480 and after['charged_units']-before['charged_units']==8_046_240
assert new['real_scope']['total_upper_cny']==after['charged_units']/1e9
assert new['real_scope']['additional_upper_cny']==(after['charged_units']-before['charged_units'])/1e9
assert not new['real_scope']['provider_bill_verified'] and not new['real_scope']['human_player']
assert sha(initial_path.read_bytes())==initial_hash
remote=git('ls-remote','origin','refs/heads/main','refs/tags/baseline_v1').decode().strip()
result={'review':'T21 append-only correction identity review','actual_exit_code':0,'command':[sys.executable,'-B',str(Path(__file__).resolve())],
 'reviewed_head':REVISION,'product_commit':CODE,'initial_review_preserved_raw_sha256':initial_hash,
 'original_manifest_raw_sha256':sha(manifest_raw),'addendum_raw_sha256':sha(addendum_raw),
 'new_artifacts':new_artifacts,'original_artifacts_preserved':preserved,'source_count_preserved':len(manifest['sources']),
 'accepted_real_run_ledger_record':{'before_rows':4,'after_rows':6,'after_states':['settled']*6,'actual_new_game_rows':2,
   'additional_upper_cny':.00804624,'total_upper_cny':.01035448,'live_ledger_read':False},
 'finding_closure':{'id':'T21-DOC-001','alias':'T21-META-001','status':'CLOSED','reason':'Explicit v2 facts/correction/addendum supersede contradictory derived paid scope and retain immutable original evidence.'},
 'remote_snapshot':remote,'git_commands':commands,'ended':datetime.now(timezone.utc).isoformat(),
 'limitations':['Addendum is verified by supplied current raw identity; its own future commit/publication is Main responsibility.',
 'Correction source commit is local reviewed state; remote snapshot below is separately observed, not an assumed push.',
 'No application/tests/.env/credentials/live ledger/provider/model execution; no human grade/signature/teacher approval.',
 'T22/E1/evaluator/CH01/clean reproduction remains outside this review.']}
out=ROOT/'evidence/qa/T21-identity-correction-review-20261002.json'
out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'actual_exit_code':0,'evidence':out.relative_to(ROOT).as_posix(),'finding':result['finding_closure'],
 'new_artifacts':len(new_artifacts),'original_artifacts_preserved':len(preserved),'sources_preserved':len(manifest['sources']),
 'remote_snapshot':remote},ensure_ascii=False))
