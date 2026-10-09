"""Seal actual independent QA results, source hashes and inspected artifacts only."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
from collections import Counter
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'evidence/integration/handpainted/qa'
read=lambda p:json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
candidate_path='evidence/integration/handpainted/candidate.json'
candidate=read(candidate_path)
current={p:sha(p) for p in candidate['source_sha256']}
assert current==candidate['source_sha256']
protocol=read('evidence/integration/handpainted/qa/preparation.json')
assert all(sha(p)==h for p,h in protocol['immutable_sha256'].items())
base='evidence/integration/handpainted/qa/'
static_path=base+'20261009T045232371706-static/run.json'
build_path=base+'20261009T045244235346-build/run.json'
browser_paths=[base+d+'/run.json' for d in ('20261009T045300333Z-browser','20261009T045643974Z-browser','20261009T050000993Z-browser')]
static,build=read(static_path),read(build_path)
assert static['exit_code']==build['exit_code']==0
runs=[read(p) for p in browser_paths]
assert [r['exit_code'] for r in runs]==[1,0,0]
for r in runs:
    assert r['source_sha256_before']==r['source_sha256_after']==candidate['source_sha256']
    assert r['candidate_sha256']==sha(candidate_path)
    assert r['paid_calls']==0
first='20261009T045300333Z-browser/'
second='20261009T045643974Z-browser/'
third='20261009T050000993Z-browser/'
viewed=[first+x for x in ('R1-overview.png','R1-symbols.png','R2-circuit-375.png','R2-overview-on.png','R2-login-375.png','R3-early-panel-375.png','R1-cabinet-OPEN.png','r1_clock-initial.png','R3-overview.png','r1_record-initial.png','R1-microscope-slide.png','R3-legend.png')]
viewed += [second+x for x in ('R3-door-OPEN.png','R3-sequence-draft-375.png','Victory-desktop.png','Victory-mobile.png')]
viewed += [third+'Victory-desktop-settled.png']
assert len(viewed)==17
artifacts={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(QA.rglob('*')) if p.is_file() and p.name not in ('result.json','artifacts.json')}
report='review/findings/handpainted.md'
artifacts[report]=sha(report)
artifact_manifest={'operator':'paint_qa','status':'SOURCE STOP','scope':'All new QA evidence and final QA review report; excludes manifest/result self-reference','files_sha256':artifacts,'file_count':len(artifacts)}
(QA/'artifacts.json').write_text(json.dumps(artifact_manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
summary=[]
scopes=[
    'Real UI R1/R2 through early R3 CARD_ACCEPTED; accepted checkpoints before one QA selected-item protocol failure. PNG retry/lazy/three closeup isolation/mobile edge/restore/reload/one restart actual.',
    'Narrow remaining actual R3 FINAL_CHECK/PASS/UNLOCKED/OPEN/EXIT/end archives/Victory. Public API prerequisites explicitly separate; no completed-route/build/restart/retry/lazy repeat.',
    'Settled desktop Victory screenshot and native buttons only; public fixture through Win. No third UI route.'
]
for p,r,scope in zip(browser_paths,runs,scopes):
    types=dict(Counter(c['check'] for c in r['checks']))
    summary.append({'path':p,'sha256':sha(p),'command':r['command'],'exit_code':r['exit_code'],'records':len(r['checks']),'public_fixture_records':types.get('public-API-fixture-only',0),'scope':scope,'record_types':types,'issues':r['issues']})
result={
    'recorded_at':datetime.now(timezone.utc).isoformat(),'operator':'paint_qa','status':'SOURCE STOP; independent joint scoped QA passed',
    'candidate':candidate_path,'candidate_sha256':sha(candidate_path),'source_count':len(current),'source_sha256':current,
    'qa_source_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'tests/handpainted').glob('*')) if p.is_file()},
    'immutable_count':len(protocol['immutable_sha256']),'immutable_raw_match':True,
    'static':{'path':static_path,'sha256':sha(static_path),'command':['C:/Users/liyh/.conda/envs/1/python.exe','-B','-X','utf8','tests/handpainted/audit_candidate.py',candidate_path],'exit_code':0,'PNG_count':85,'actual_checks':len(static['checks'])},
    'build':{'path':build_path,'sha256':sha(build_path),'command':build['command'],'cwd':build['cwd'],'exit_code':0,'build_count':1,'modules':52,'vite_seconds':2.98,'warning':'Original large Phaser chunk warning remains'},
    'browser_epochs':summary,'browser_record_counts_summed':False,'single_complete_green_browser_claim':False,'backend_full_suite_runs':0,
    'adapter_repairs':[{'classification':'pre-execution only','evidence':base+'adapter-alpha-repair.json'},{'classification':'pre-execution hotspot strengthening','evidence':base+'adapter-hotspot-preparation.json'},{'classification':'actual epoch1 QA failure retained','cause':'uiSelect omitted cancel-item for reusable access_card; existing UI legitimately used selected card and returned409. Only new QA deselect/remaining scope changed, product0fix.'},{'classification':'screenshot timing only','cause':'epoch2 desktop Victory was transient; separate narrow presentation run waited actual transition idle before final screenshot. No product0fix.'}],
    'viewed_actual_PNGs':[{'path':base+p,'sha256':sha(base+p),'purpose':'historical transition frame; not final desktop presentation' if p==second+'Victory-desktop.png' else 'Actual stable-candidate independent representative inspection'} for p in viewed],
    'aesthetic_review_count':17,'all85_aesthetic_certification':False,'product_findings':[],
    'nonblocking_visual_limitations':['R3 wall conduit is slightly right of control-panel conduit in overview; functional hotspots unaffected.','Clock paper patch retains visible texture seam.'],
    'scope_limitations':['Private QA-owned new session/database only; no historical user DB or credentials.','No full127 backend rerun; reused frozen backend and prior narrow actual API acceptance via Main.','No rootCMD interactive launch, OS reboot, real model quality, paid calls or human completion-time claim.','Actual one backend process restart is not a whole operating-system restart.','Desktop1280 and mobile375x812/812x375 representative checks; not every device/browser or every pixel/edge.','Current room preloads all its state/closeup PNGs; first welcome lazy and actual per-room scene route tested, not a loading-performance certification.','44px responsive scene hotspots and selected-restore dialog actual; final settled desktop Victory native78x44 measured.','Run counts include fixtures/checkpoints/cleanup; no aggregate or single full-green claim.'],
    'paid_calls':0,'product_fixes':0,'new_agents':0,'commits':0,
    'qa_report':{'path':report,'sha256':sha(report)},'artifact_manifest':{'path':base+'artifacts.json','sha256':sha(base+'artifacts.json'),'files':len(artifacts)}
}
(QA/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':str(QA/'result.json'),'result_sha256':sha(base+'result.json'),'sources':len(current),'artifacts':len(artifacts),'status':result['status']},ensure_ascii=False))
