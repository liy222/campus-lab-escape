"""Final delivery/calibration read-hash QA; no target execution or network."""
from __future__ import annotations
import argparse,hashlib,importlib.abc,importlib.util,json,re,socket,sqlite3,sys,zipfile
from collections import Counter
from contextlib import closing
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
STAMP='20261005T115741Z';COMMIT='833aafb09ad20dc1ba82cfed198485ce13300067'
ZIP_SHA='2979fd06009a9ee27cc13d8e00500b234d8fbf5d5c90a03a9311ed08e163be8a'
PINS_SHA='7e7013be5d40d7639f2e2d48fefacf2d24c8f7ebdf4e1a6aec3dd3b5f9b29977'
REPORT_SHA='52962166c15b8b07209cf83257da9f8ad74d5270007083998763ac1c72777c57'
INDEX_SHA='81230122f1497e4a9d6cf108d3421d2eee391b14f4b70ee222d6322268f9033e'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def digest(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False)
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self,name,path=None,target=None):
        if name.split('.')[0] in {'backend','experiments','scripts','evaluation','frontend'}:raise RuntimeError('TARGET_IMPORT_FORBIDDEN')
def materialize(blob,pin):
    if pin['materialization']=='raw_equal':return blob
    if pin['materialization']!='main_pinned_line_endings':raise ValueError('UNAPPROVED_MATERIALIZATION')
    indices=pin['crlf_newline_indices'];parts=blob.replace(b'\r\n',b'\n').split(b'\n')
    if not all(type(i) is int for i in indices) or indices!=sorted(set(indices)) or any(i<0 or i>=len(parts)-1 for i in indices):raise ValueError('BAD_NEWLINE_PINS')
    selected=set(indices);raw=bytearray()
    for i,b in enumerate(parts):
        raw.extend(b)
        if i<len(parts)-1:raw.extend(b'\r\n' if i in selected else b'\n')
    return bytes(raw)
def safe(name):
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name or p.name=='.env' or p.name.startswith('.env.') and p.name!='.env.example' or p.suffix.lower() in {'.sqlite','.sqlite3','.db'}:raise ValueError('UNSAFE_OR_PRIVATE_SOURCE_MEMBER')
def calibration(out,check):
    path=ROOT/'evaluation/runs/20261005T120430742113Z/report.json';process_path=ROOT/'evidence/integration/paid-evaluation-K1K6-20261005T110203Z-process.json'
    d=load(path);p=load(process_path);cases=load(ROOT/'evaluation/fixtures/cases.json')['cases'];case_by={v['case_id']:v for v in cases};audits={a['case_id']:a for a in d['audits']};results={r['case_id']:r for r in d['results']}
    protected={str(x.relative_to(ROOT)).replace('\\','/'):sha(x) for x in [path,process_path,ROOT/'evaluation/trusted/freeze.json',ROOT/'evaluation/fixtures/cases.json',ROOT/'evaluation/trusted/paid-gates.json']}
    for k in ('evaluation\\__init__.py',):pass
    check('actual_process_exit1_report_exit1',p['actual_exit_code']==d['exit_code']==1 and p['source_unchanged'])
    check('source14_beforeafter_exact',len(p['evaluator_source_before'])==14 and p['evaluator_source_before']==p['evaluator_source_after'])
    for name,h in p['evaluator_source_after'].items():check('current_source:'+name,sha(ROOT/name)==h)
    check('report_source14_matches_process',len(d['evaluator_source_sha256'])==14 and all(d['evaluator_source_sha256'][Path(n).name]==h for n,h in p['evaluator_source_after'].items()))
    check('gate_finite3_022_CNY',p['gate']['max_calls']==3 and p['gate']['max_cost_units']==220000000 and p['gate']['max_tokens']==1000 and p['gate']['timeout_seconds']==20 and p['gate']['input_sha256']==d['fixture_set_sha256']==digest((ROOT/'evaluation/fixtures/cases.json').read_bytes()))
    check('actual11_original_case_identities',len(d['results'])==len(d['audits'])==len(cases)==11 and set(results)==set(audits)==set(case_by))
    for id,r in results.items():check('frozen_expected:'+id,r['expected']==case_by[id]['expected'] and r['matches_expected']==(r['actual']==r['expected']) and r['actual']==r['output']['status'])
    k1=audits['K1-real-valid-evidence'];k2=audits['K2-explicit-failure'];k4=audits['K4-failure-with-injection']
    check('K1_invalid_ref_abstains',results[k1['case_id']]['actual']=='INSUFFICIENT_EVIDENCE' and k1['validation_errors']==['MODEL_FAKE_OR_UNREAD_REFERENCE'] and not results[k1['case_id']]['output']['evidence_refs'])
    check('K1_invalid_text_not_reflected',k1['raw_suggestion'] is None and isinstance(k1['raw_suggestion_sha256'],str) and len(k1['raw_suggestion_sha256'])==64 and k1['raw_suggestion_size_bytes']==1768 and not any(k in k1 for k in ('reflection','raw_response','raw_content')))
    check('K1_known_usage_charge',k1['provider_metadata']['usage']==dict(prompt_tokens=3694,completion_tokens=453,prompt_cache_hit_tokens=0,total_tokens=4147) and k1['provider_metadata']['cost_upper_units']==11012000)
    check('K2_unavailable_deterministic_FAIL',results[k2['case_id']]['actual']=='FAIL' and k2['validation_errors']==['MODEL_UNAVAILABLE'] and k2['provider_metadata']['usage'] is None and k2['provider_metadata']['cost_upper_units']==51528000 and k2['deterministic']['failures'])
    check('K4_unknown_stop_no_paid_but_FAIL',results[k4['case_id']]['actual']=='FAIL' and k4['validation_errors']==['PRIOR_CALL_UNKNOWN_STOP'] and k4['provider_metadata'] is None and k4['raw_suggestion'] is None and k4['deterministic']['failures'])
    actual=[a['provider_metadata'] for a in d['audits'] if isinstance(a['provider_metadata'],dict) and a['provider_metadata'].get('actual_network_call')]
    ids={v['call_id'] for v in actual};check('exact2_paid_not3',len(actual)==len(ids)==d['actual_paid_calls']==2 and ids=={'eval_K1K6-20261005T110203Z_1','eval_K1K6-20261005T110203Z_2'})
    c=d['calibration'];check('11cases10matches_no_falsePASS',c['case_count']==11 and c['matches']==10 and c['false_pass']==[] and c['wrong_failure']==[] and c['unnecessary_abstention']==['K1-real-valid-evidence'] and all(r['actual']!='PASS' or r['expected']=='PASS' for r in d['results']))
    check('all_invalid_raw_outputs_digest_or_null',all(a['raw_suggestion'] is None for a in d['audits'] if a['validation_errors']))
    # Original ledger is read only here to bind these two exact accounting rows.
    cols='id,scope,created_at,reserved,charged,state,reason,prompt_tokens,completion_tokens,cache_hit_tokens'
    with closing(sqlite3.connect((ROOT/'data/ai-budget.sqlite').resolve().as_uri()+'?mode=ro',uri=True,isolation_level=None)) as db:
        rows=db.execute('SELECT '+cols+' FROM budget_calls WHERE id LIKE ? ORDER BY id',('eval_K1K6-20261005T110203Z_%',)).fetchall();totals=db.execute('SELECT COUNT(*),SUM(charged) FROM budget_calls').fetchone();states=db.execute('SELECT state,COUNT(*) FROM budget_calls GROUP BY state ORDER BY state').fetchall();config=db.execute('SELECT id,cap,frozen FROM budget_config').fetchall()
    check('original_ledger_exact2_callIDs',{r[0] for r in rows}==ids and len(rows)==2 and all(r[1]=='evaluation' for r in rows))
    first,second=rows
    check('K1_ledger_settled_known_matches',first[5]=='settled' and first[4]==11012000 and first[7:]==(3694,453,0))
    check('K2_ledger_unknown_NULL_fullupper',second[5]=='unknown' and second[6]=='MODEL_UNAVAILABLE' and second[3:5]==(51528000,51528000) and second[7:]==(None,None,None))
    check('pending_hold85_511501840',totals==(85,511501840) and states==[('settled',84),('unknown',1)] and config==[(1,10000000000,0)])
    oldfiles=['evidence/qa/T27-CH01-event-20261005T115700Z/result.json','evidence/qa/T27-evaluation-events-20261005T105300Z/result.json','evaluation/runs/20261005T053334004502Z-formal-real-48d972eb/report.json']
    # Original zero-paid QA/mock evidence is separate, never rewritten to this paid run.
    old={}
    for rel in oldfiles[:2]:
        v=load(ROOT/rel);old[rel]=sha(ROOT/rel);check('old_zero_paid_evidence_retained:'+rel,v['actual_paid_calls']==0)
    check('calibration_sources_reports_bytes_unchanged',all(sha(ROOT/n)==h for n,h in protected.items()))
    result=dict(task='T27-real-calibration-independent-readonly',created_at=datetime.now(timezone.utc).isoformat(),actual_paid_in_original_run=2,QA_actual_paid_calls=0,QA_network_calls=0,actual_run_exit_code=1,Main_process_source=process_path.relative_to(ROOT).as_posix(),Main_process_raw_sha256=sha(process_path),actual_report_raw_sha256=sha(path),gate=p['gate'],audits_of_K1_K2_K4={a['case_id']:a for a in (k1,k2,k4)},original_ledger_readonly=dict(call_rows=rows,totals=totals,states=states,config=config),protected_artifact_hashes=protected,original_zero_paid_artifact_hashes=old,limitations=['Two paid requests observed through saved run metadata and ledger; not three successful real judgements.','K1 invalid reference abstained; K2 and K4 deterministic FAIL despite unavailable/no-request, not successful semantic calibration.','11 fixtures10 matches with falsePASS0 does not establish complete calibration or general language robustness.','Pending unknown51528000 blocks further paid work; fee question not independently resolved by QA.','No raw invalid model text/reflection retained; digest1768-byte metadata only.','Original ledger mode=ro only; no real credential, provider or HTTP execution.'])
    save(out/'calibration-review.json',result);return result
def clean(out,check):
    parent=ROOT/'data/reproduction'/STAMP;workspace=parent/'clean';base=ROOT/'evidence/integration'/('T32-clean-final-'+STAMP)
    pins_path=ROOT/'evidence/integration'/('reproduction-'+STAMP+'-pins.json');index_path=ROOT/'evidence/integration/T32-clean-final-evidence-index-20261005.json';process_path=ROOT/'evidence/integration/T32-clean-final-process-20261005.json'
    report=load(base/'report.json');pins=load(pins_path);index=load(index_path);process=load(process_path)
    check('Main_report_zip_pins_index_exactraw',sha(base/'report.json')==REPORT_SHA and sha(parent/'source.zip')==ZIP_SHA and sha(pins_path)==PINS_SHA and sha(index_path)==INDEX_SHA)
    check('commit_chain_833aafb',pins['commit']==report['commit']==index['source_commit']==process['source_commit']==COMMIT)
    check('source10778_beforeafter',len(pins['files'])==len(report['source_hashes_before'])==10778 and report['source_hashes_before']==report['source_hashes_after'] and report['source_unchanged'])
    check('actual_Main_exit0_output_override',process['actual_exit_code']==report['exit_code']==0 and process['actual_report_raw_sha256']==REPORT_SHA and process['actual_report']=='evidence/integration/T32-clean-final-'+STAMP+'/report.json' and '--output' in process['actual_command'] and process['actual_command'][process['actual_command'].index('--output')+1]==str(base))
    check('mock_clean_no_env_mutation_paid0',report['provider']=='mock' and report['actual_paid_calls']==0 and report['environment_mutated'] is False)
    check('Main_materialization_exact',load(base/'materialization.json')==pins['files'])
    check('Main_evaluator_candidate_independent_pin',sha(ROOT/pins['evaluator_candidate_independent_qa'])==pins['evaluator_candidate_qa_sha256']=='958c67a1c3fb3d54e1f1af48b14cd8aa57dc1d58e66f187f0ec6e8bd3d9810e0')
    evidence={}
    check('all20_index_files',len(index['files'])==20 and index['base']==base.relative_to(ROOT).as_posix())
    for n,r in index['files'].items():
        safe(n);p=base/n;h=sha(p);check('evidence_byte:'+n,h==r['sha256'] and p.stat().st_size==r['bytes']);evidence[n]=h
    mapping={};before={}
    with zipfile.ZipFile(parent/'source.zip') as z:
        members=[i for i in z.infolist() if not i.is_dir()];names=[i.filename for i in members]
        check('ZIP_members10778_same_unique',len(names)==len(set(names))==10778 and set(names)==set(pins['files']))
        check('ZIP_commit_comment',z.comment.decode('ascii')==COMMIT)
        for name in sorted(names):
            safe(name);blob=z.read(name);pin=pins['files'][name];raw=materialize(blob,pin);expected=digest(raw);actual=sha(workspace/name)
            ok=digest(blob)==pin['git_blob_sha256'] and expected==pin['runtime_raw_sha256']==actual==report['source_hashes_before'][name]==report['source_hashes_after'][name]
            check('raw_materialization:'+name,ok)
            mapping[name]=dict(zip_git_blob_sha256=digest(blob),materialization=pin['materialization'],Main_crlf_indices=pin.get('crlf_newline_indices'),independently_reconstructed_raw_sha256=expected,clean_raw_sha256=actual,Main_source_before_sha256=report['source_hashes_before'][name],Main_source_after_sha256=report['source_hashes_after'][name]);before[name]=actual
    check('clean_env_absent_existence_only',not (workspace/'.env').exists() and not (workspace/'release/archives/baseline_v1/.env').exists())
    lock={s.split('==',1)[0]:s.split('==',1)[1].strip() for s in (workspace/'backend/requirements.lock.txt').read_text(encoding='utf-8').splitlines() if '==' in s and not s.startswith('#')};deps=report['locked_python_dependencies']
    check('28_lock_records_exact_versions',len(lock)==len(deps)==28 and all(deps[n]['expected']==deps[n]['actual']==v for n,v in lock.items()))
    check('8outer_commands_exit0',len(report['steps'])==8 and all(s['exit_code']==0 for s in report['steps']))
    for s in report['steps']:check('outer_log:'+s['name'],sha(base/s['log'])==s['log_sha256'])
    summaries=list((base/'check').glob('*/summary.json'));check('one_unified_summary',len(summaries)==1);summary=load(summaries[0]);check('unified_two_children_exit0',summary['exit_code']==0 and summary['source_unchanged'] and len(summary['steps'])==2 and all(s['exit_code']==0 for s in summary['steps']))
    for s in summary['steps']:check('child_log:'+s['name'],sha(summaries[0].parent/s['log'])==s['sha256'])
    pytest=(summaries[0].parent/'deterministic-tests.txt').read_text(encoding='utf-8');check('73pytest203subtests_not_unique_acceptance','73 passed, 1 warning, 203 subtests passed' in pytest)
    evaluations={}
    for release,count in [('baseline_v1',60),('E1-formal-review-v2',102),('CH01-adversarial-review-v3',162)]:
        log=(base/('evaluator-'+release+'.txt')).read_text(encoding='utf-8');match=re.search(r'^Evidence: (.+)$',log,re.M);p=Path(match.group(1).strip());e=load(p)
        check('precheck_actual_scope:'+release,p.resolve().is_relative_to(workspace/'evaluation/runs') and e['exit_code']==0 and e['actual_paid_calls']==0 and e['target_code_executed'] is False and not e['precheck']['issues'] and len(e['precheck']['source_identities'])==count)
        check('precheck14_source_identity:'+release,len(e['evaluator_source_sha256'])==14 and all(sha(workspace/'evaluation'/n)==h for n,h in e['evaluator_source_sha256'].items()))
        evaluations[release]=dict(report_path=str(p),report_raw_sha256=sha(p),source_count=count,exit_code=e['exit_code'],scope=e['precheck']['scope'],actual_paid_calls=0,target_executed=False)
    services={};stops=[]
    def gamefields(s):return {k:s[k] for k in ('status','room','objects','inventory','clues','exits','progress')}
    for version,name,cwd in [('2.0.0','v2-services.json',workspace),('1.0.0','v1-rollback.json',workspace/'release/archives/baseline_v1')]:
        s=load(base/name);starts=[e for e in s['service_ledger'] if e['event']=='start' and '-m' in e['command'] and 'uvicorn' in e['command']];saved=s['saved_state'];prior=s['state_before_restart'];restored=s['restored_state'];receipt=s['unlock_receipt']
        check('service_status:'+version,s['status']=='PASS' and s['version']==version and s['provider']=='mock' and s['actual_paid_calls']==0)
        check('actual_distinct_restart_PIDs_cwd:'+version,len(starts)==2 and starts[0]['pid']!=starts[1]['pid'] and all(Path(e['cwd']).resolve()==cwd.resolve() for e in starts))
        check('restore_state_revision_generation:'+version,saved['level_version']==prior['level_version']==restored['level_version']==version and gamefields(restored)==gamefields(saved) and restored['revision']==prior['revision']+1 and restored['generation']!=prior['generation'] and restored['save']==saved['save'])
        check('unlock_receipt13_R3:'+version,saved['revision']==receipt['revision_after']==13 and receipt['revision_before']==12 and receipt['changed'] and receipt['arguments']==dict(item_id='emergency_key',target_id='r2_door') and any(e['destination_id']=='R3' and e['unlocked'] for e in restored['exits']))
        key=lambda t:'emergency_key' in [i['item_id'] for i in t['inventory']]
        check('version_key_lifecycle:'+version,(receipt['consumed_item_ids']==['emergency_key'] and not any(key(t) for t in (saved,prior,restored)) and prior['status']=='won' and prior['revision']==18) if version=='2.0.0' else (receipt['consumed_item_ids']==[] and all(key(t) for t in (saved,prior,restored))))
        stops += [e for e in s['service_ledger'] if e['event']=='stop'];services[version]=s
    check('5_intentional_stops_nonzero_preserved',len(stops)==5 and all(e['taskkill_exit_code']==0 and e['exit_code']==1 for e in stops))
    after={name:sha(workspace/name) for name in before};check('all10778_clean_bytes_after_read_equal',before==after)
    save(out/'all10778-materialization.json',mapping)
    result=dict(task='T32-final-independent-read-hash',created_at=datetime.now(timezone.utc).isoformat(),commit_metadata=COMMIT,Main_zip_raw_sha256=ZIP_SHA,Main_pins_raw_sha256=PINS_SHA,Main_report_raw_sha256=REPORT_SHA,Main_index_raw_sha256=INDEX_SHA,Main_actual_process_record=process,all20_index_raw_files=evidence,all10778_clean_before=before,all10778_clean_after=after,materialization_mode_counts=dict(Counter(p['materialization'] for p in pins['files'].values())),eight_outer_steps=report['steps'],nine_leaf_command_count=9,pytest_record=dict(tests=73,subtests=203,warnings=1,reused_M3_unittest_methods=19),lock28_records=deps,three_identity_prechecks=evaluations,v2_v1_recorded_service_results=services,five_owned_intentional_stops=stops,QA_target_code_executed=False,QA_network_calls=0,QA_paid_calls=0,QA_environment_read=False,QA_database_opened=False,limitations=['Main supplied actual clean process exit0/ada9cd; this audit reads saved logs, not rerun.','Full10778 ZIP bytes independently materialized in memory per explicit Main pins and compared to every clean raw file twice; no target execution.','Commit provenance from Main pins/ZIP comment/record; no independent Git history command.','Existing Conda plus recorded frontend npm-ci; no clean OS/environment or dependency installation by QA.','73 pytest include19 reused M3 methods; 203 subtests are not independent human acceptance scenarios.','Automated mock service/restart/save/restore only; no human gameplay/teacher approval/general language proof.','Real experiment/calibration remain separate outcomes and budgets.'])
    save(out/'clean-review.json',result);return result
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['calibration','clean'],required=True);ap.add_argument('--output',required=True);args=ap.parse_args();out=(ROOT/args.output).resolve()
    if not out.is_relative_to(ROOT/'evidence/qa') or out.exists():raise ValueError('NEW_QA_OUTPUT_REQUIRED')
    out.mkdir(parents=True);sys.meta_path.insert(0,Guard())
    def denied(*a,**kw):raise RuntimeError('QA_NETWORK_FORBIDDEN')
    socket.create_connection=denied;socket.socket.connect=denied;checks=[]
    def check(n,v):checks.append(dict(name=n,passed=bool(v)))
    result=None;error=None
    try:result=calibration(out,check) if args.mode=='calibration' else clean(out,check)
    except Exception as e:error=type(e).__name__+': '+str(e)
    failed=[c for c in checks if not c['passed']];code=int(bool(error or failed));save(out/'checks.json',checks)
    final=dict(task='independent-'+args.mode,actual_command=[sys.executable,'-B','-X','utf8',*sys.argv],working_directory=str(ROOT),created_at=datetime.now(timezone.utc).isoformat(),checks=len(checks),passed=sum(c['passed'] for c in checks),failures=failed,error=error,exit_code=code,QA_reviewer_raw_sha256=sha(Path(__file__)),QA_paid_calls=0,QA_network_calls=0,scope='read/hash only, no target import/execution or installation; calibration original ledger mode=ro only')
    save(out/'result.json',final);print(json.dumps(dict(mode=args.mode,checks=final['checks'],passed=final['passed'],failed=len(failed),exit_code=code,error=error,result_sha256=sha(out/'result.json'),output=str(out)),ensure_ascii=False));return code
if __name__=='__main__':raise SystemExit(main())
