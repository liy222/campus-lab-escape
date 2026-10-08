"""Seal actual v4.1 independent QA epochs; no formal execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parents[4];qa=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
rel=lambda p:p.relative_to(root).as_posix()
candidate_path=qa.parent/'candidate.json';candidate=read(candidate_path)
assert sha(candidate_path)=='7ebfaefc93a22a62fd7c002da822f21ab79588641c2dd7609bf3e96d22b18bae'
assert len(candidate['source_sha256'])==123
assert all(sha(root/p)==h for p,h in candidate['source_sha256'].items())
baseline=read(qa.parent/'baseline-candidate.json')
immutable=[p for p in candidate['source_sha256'] if p.startswith(('backend/','contracts/'))]
old_svg=[p for p in baseline['source_sha256'] if p.startswith('frontend/src/assets/') and p.endswith('.svg')]
assert len(immutable)==40 and len(old_svg)==26
assert all(candidate['source_sha256'][p]==baseline['source_sha256'][p] for p in immutable+old_svg)
api_path=qa/'formal-api/run.json';build_path=qa/'formal-build/run.json';browser_path=qa/'20261008T010537916Z-browser/run.json'
api,build,browser=map(read,[api_path,build_path,browser_path])
for run in [api,build,browser]:
    assert run['exit_code']==0 and run['source_sha256_before']==run['source_sha256_after']==candidate['source_sha256']
assert api['tests_before_after_match'] and len(api['test_sha256_before'])==12
assert '6 passed, 1 warning, 3 subtests passed in 11.72s' in (qa/'formal-api/stdout.txt').read_text(encoding='utf-8')
assert len(browser['checks'])==339 and browser['issues']==[] and browser['candidate_sha256']==sha(candidate_path)
prepared=read(qa/'preparation-live-selectors.json')
for key in ['old_e2e13_sha256','old_API12_sha256']:
    assert all(sha(root/p)==h for p,h in prepared[key].items())
assert api['test_sha256_before']==api['test_sha256_after']==prepared['old_API12_sha256']
required=['three-room-route-slots-items-save-restore-reload-actual-server-restart-win','five-immutable-archives-plus-old-slot-persist-reset-refresh-OSrestart','R2-hasTouch-real-canvas-and-independent-keyboard','hasTouch-mobile-actual-touchscreen-tap-and-keyboard-Enter','R2-real-overview-pixels-differ-after-manual-server-switch','R2-take-removes-visible-object-and-auto-returns-overview']
assert all(any(c['check']==label for c in browser['checks']) for label in required)
failed=[]
for folder,count in [('20261008T010100682Z-browser',204),('20261008T010350006Z-browser',278)]:
    p=qa/folder/'run.json';d=read(p)
    assert d['exit_code']==1 and len(d['checks'])==count and d['source_sha256_before']==d['source_sha256_after']==candidate['source_sha256']
    failed.append({'run':rel(p),'sha256':sha(p),'exit_code':1,'compact_records':count,'issues':d['issues']})
third=qa/'runner-epochs/third.mjs';assert not third.exists();third.write_bytes((root/'tests/e2e/run_visual_v41.mjs').read_bytes())
epochs=[{'path':rel(qa/'runner-epochs'/name),'sha256':sha(qa/'runner-epochs'/name),'purpose':'QA source archival snapshot, not runnable entry point'} for name in ['first.mjs','second.mjs','third.mjs']]
assert [e['sha256'] for e in epochs]==['c0307307bc2ea5cae6df87657d387a0c34d37566278dbcb7951e3206ed4275b1','8fb1322e3434037a5c7807a59a5b3a06cad7f12f5a97c7c57e455a0fcd8deb8f','c999fcf488d60793346535b7a4d07b18c7abf31915630923e87d3ae987fc874b']
first_images=['R2-dark-overview-before-switch.png','R2-bright-overview-after-switch.png','R2-partial-circuit.png','R2-monitor-LOGIN_LOCKED.png','R2-DATA_READ-tray-items-not-auto-taken.png','R2-service-label-original-story.png']
third_images=['R2-mobile-circuit.png','R2-mobile-login.png','R2-DATA_READ-tray-mobile.png','research_strip-receipt-frame-take.png','research_strip-settled-take.png','R2-real-touch-keyboard-375.png','R1-visual-desktop.png','R1-visual-mobile.png','R1-clock-closeup.png','mobile-victory.png','desktop-three-archive-list.png']
viewed=[qa/'20261008T010100682Z-browser'/n for n in first_images]+[browser_path.parent/n for n in third_images]
artifacts=[p for dirname in ['formal-api','formal-build','20261008T010100682Z-browser','20261008T010350006Z-browser','20261008T010537916Z-browser','runner-epochs'] for p in (qa/dirname).iterdir() if p.is_file()]
record={
    'status':'Independent v4.1 frozen candidate accepted; SOURCE STOP',
    'recorded_at':datetime.now(timezone.utc).isoformat(),'actual_operator':'visual_qa_oct08',
    'candidate':rel(candidate_path),'candidate_sha256':sha(candidate_path),'source_count':123,'source_123_before_after_current_bound_all_formal_epochs':True,
    'parent_commit':'1047e293ade70e446c9c76be0a0d751f3e3ad81a',
    'immutable':{'backend_contract40_raw_identical_to_actual_v41_baseline':True,'R1_SVG26_raw_identical_to_actual_v41_baseline':True,'old_API12_byte_identical':True,'old_e2e13_byte_identical':True,'test_hash_reference':rel(qa/'preparation-live-selectors.json')},
    'baseline':{'result':rel(qa/'baseline-result.json'),'actual_methods':6,'actual_subtests':3,'API_exit_code':0,'build_exit_code':0,'scope':'Pre-R2 compact baseline, counted separately; not added to final coverage'},
    'historical_full_API_reuse':{'result':'evidence/upgrade/v4.0/qa/baseline-result.json','passed_methods':127,'passed_subtests':337,'scope':'Historical previsual full suite; no repeated127 full run in v4.1'},
    'targeted_API':{'run':rel(api_path),'command':api['command'],'pytest_arguments':api['pytest_arguments'],'exit_code':0,'passed_methods':6,'passed_subtests':3,'duration_seconds':11.72,'warnings':1,'compact_records':api['checks_count']},
    'build':{'run':rel(build_path),'command':build['command'],'exit_code':0,'limitation':'Vite minified chunk>500kB warning; lazy split deferred to4.2'},
    'browser':{'run':rel(browser_path),'command':browser['command'],'started':browser['started'],'ended':browser['ended'],'exit_code':0,'compact_records':339,'issues':[],'pixel_records':sum(c['check']=='real-rendered-canvas-nonblack-nonuniform' for c in browser['checks']),'R2_state_layout_records':sum(c['check']=='R2-public-state-membership-rendering-and-readable-controls' for c in browser['checks']),'R1_actual_touch_keyboard':True,'R2_actual_touch_keyboard':True,'receipt_take_frames':True,'five_archives_plus_legacy_slot':True,'full_three_room_route':True},
    'previous_failed_attempts':failed,'failure_diagnosis':'New QA marker observers were lost after full reload and absent in fresh independent touch context. Re-registration added only to new runner; fresh animation and prior route/state/archive assertions retained. No product edits or candidate epoch changes.',
    'failure_reporting_limit':'First attempt captured onlyfirst message; original fullstack cannot be reconstructed. Second actual stack frames preserved. No retroactive fabricated trace.',
    'runner_epochs':epochs,'repeated_count_policy':'204/278/339 are separate actual attempts; never add repeated records. Final complete green browser is339, not cumulative.',
    'third_run_dispatch_note':'Third complete run was dispatched before Main suggested narrower touch-only recheck. Main authorized normal completion of the already running attempt; no fourth whole route or repeatedAPI/build.',
    'coverage':['R1 sharedCanvas/HUD/Notebook/Assistant regression and original hidden/photo/clock/four-wheel-lock/selection/error/item/archives/reload/restart logic','R2 dark/brighter overview from realpixels and publicpowerstate; sixpowerbox/fivemonitor states','R2 trueCanvas inspect/interact/use-item/move, publicmoduleid rotations+independentkeyboard, separate submit_circuit thenmanualswitch','R2 heldfuse/login/circuit failures retaincore state and countone meaningfulmistake; ownpublicgeometry solver acceptsalternateconnection','POWER_ON-only service label, DATA_READ-only paper/card visible objects, explicittake removesobject/returnsroom with freshreceiptanimation','Early/sample/partialcircuit/powered/win archives plusoldslot, cancel/selectedrestore/reset/reload/directloopbackbackendprocessrestart; snapshotsnoanimation and authoritativeUTCstats','R3 graybox public-derivedsequence/errors/draftclear/exitstatemachine/victorysettlement/scorefreeze; legacy-v3.1-v3.2-v3.3 ownedlight namespace/save smokes','375px truehasTouch context with normalR1 UI acquisition, R2 touchscreen box/module, independentkeyboard guard; DOMmobilecircuit/login/tray readability andscreens'],
    'screens_personally_viewed':{rel(p):sha(p) for p in viewed},'screens_personally_viewed_count':len(viewed),
    'artifact_sha256':{rel(p):sha(p) for p in artifacts},
    'source_sha256_final':candidate['source_sha256'],
    'product_edits_by_QA':0,'old_test_edits':0,'paid_calls':0,
    'limitations':['One existing Starlette/httpx deprecation warning remains.','Vite chunk-size warning remains; lazy/loading/assets gate and audio polish deferred to4.2.','R3 andEXIT remain playablegraybox fallback; no finalR3/EXIT visual acceptance.','Controlledmissing-asset failure/interactiongate not exercised.','RootCMD not interactively launched; directownedloopback backendprocessrestart only.','No audioquality/humanmanualfullroute/humancompletiontime/paidproviderquality claim.','Realprovider selector used syntheticmemoryinput only, never sent; no realcredentials/sensitivehistoricalDB.','ActualR2 hasTouch coversmaintenance/box/module andkeyboard; desktop+375ordinaryviewport completeCRTlogin/traytested, not separatetouchkeyboardforminput.','Firstfailed originalstack truncated byoldnewrunnerhandler; missing details not invented.']
}
(qa/'result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'exit_code':0,'candidate123_match':True,'backend40_match':True,'R1SVG26_match':True,'old_API12_match':True,'old_e2e13_match':True,'browser339':True,'viewedPNG':len(viewed),'result_sha256':sha(qa/'result.json')}))
