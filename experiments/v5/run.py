"""Offline E1/E2/E3 runner. Prepare expected outcomes before executing.

All account credentials and API keys below are synthetic fixtures. Runtime SQLite
files exist only inside TemporaryDirectory and are never included in evidence.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import time
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from .dataset import inputs

ROOT=Path(__file__).resolve().parents[2]
def encoded(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def hashed(value): return hashlib.sha256(value.encode()).hexdigest()
def stamp(): return datetime.now(timezone.utc).isoformat()
def write(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def source():
    paths=list((ROOT/'backend'/'app').rglob('*.py'))+[ROOT/'frontend/src/assets/generated-catalog.json',Path(__file__),Path(__file__).with_name('dataset.py')]
    return {str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
def prepare(output):
    output.mkdir(parents=True,exist_ok=False)
    rows=inputs()
    write(output/'expected.json',{'prepared_at':stamp(),'kind':'preregistered_offline_owner_experiments','source':source(),'case_expectations':[{k:v for k,v in r.items() if k!='raw'}|{'input_sha256':hashed(encoded(r['raw']))} for r in rows], 'e2_expected':{'old_policy':'0.9.0','new_policy':'1.0.0','new_single_clue_normal':'reject','old_definition_and_save_unchanged':True,'restore_original_definition_after_restart':True,'llm_calls':0},'e3_expected':{'real_crossuser_session_restore':404,'real_crossuser_archive_restore':404,'real_target_state_unchanged':True,'isolated_control_without_owner_predicate':'private_archive_read_leak','product_code_modified':False},'scope_notes':['Schema-only means strict Draft shape validation, without compiler/solver.','Full admission rejects unknown proof; unknown is not a claim of unsolvability.','LIMIT-03 disables only the deadline in a controlled harness to reach the actual state-count guard.','LIMIT-04 uses a controlled clock crossing the existing five-second branch; it is not five seconds of observed CPU.','E3 control is a read-only query on an isolated SQLite backup, not a product vulnerability or a successful product restore.','Synthetic examples are not real AI generation; paid provider and network calls are zero.']})
    write(output/'inputs.json',[{k:v for k,v in r.items()} for r in rows])
    print(encoded({'prepared':True,'path':str(output),'cases':len(rows)}))

def comparison(row):
    from backend.app.domain import generated as domain
    raw=row['raw']; start=time.perf_counter()
    try:
        if isinstance(raw,str): domain.Draft.model_validate_json(raw)
        else: domain.Draft.model_validate(raw)
        schema={'status':'accept'}
    except (ValueError,TypeError,RecursionError): schema={'status':'reject'}
    schema['elapsed_seconds']=time.perf_counter()-start
    original_time=domain.time; calls=0; observed={}
    if row.get('clock')=='disable_deadline_only': domain.time=SimpleNamespace(monotonic=lambda:0.0)
    if row.get('clock')=='controlled_boundary':
        def clock():
            nonlocal calls
            calls+=1
            return 0.0 if calls==1 else 6.0
        domain.time=SimpleNamespace(monotonic=clock)
    old_trace=sys.gettrace()
    def trace(frame,event,arg):
        if event=='call':
            if frame.f_code.co_name!='solve' or frame.f_globals.get('__name__')!='backend.app.domain.generated': return None
            frame.f_trace_lines=False
        if event=='exception' and frame.f_code.co_name=='solve' and str(arg[1])=='PROOF_UNKNOWN': observed['abstract_states']=len(frame.f_locals.get('seen',()))
        return trace
    if row.get('limit')=='planner_states': sys.settrace(trace)
    start=time.perf_counter()
    try:
        compiled=domain.compile_level(raw,row['room_count'],row['difficulty'])
        full={'status':'accept','definition_hash':compiled.definition_hash,'witness_actions':len(compiled.witness),'witness_sha256':hashed(encoded(compiled.witness))}
    except (ValueError,TypeError,KeyError,RecursionError) as error:
        unknown=str(error)=='PROOF_UNKNOWN'
        full={'status':'unknown' if unknown else 'reject','reason':str(error) if isinstance(error,ValueError) and len(str(error))<80 and '\n' not in str(error) else type(error).__name__}
    finally:
        domain.time=original_time
        sys.settrace(old_trace)
    full['elapsed_seconds']=time.perf_counter()-start
    full.update(observed)
    if row.get('clock'): full['controlled_clock']=row['clock']
    if row.get('limit')=='planner_states' and full['status']=='unknown': assert full.get('abstract_states',0)>25000,'State-count guard not actually reached'
    return {'case_id':row['case_id'],'category':row['category'],'input_sha256':hashed(encoded(raw)),'expected_full':row['expected_full'],'schema_only':schema,'full_admission':full,'matches_preregistered':full['status']==row['expected_full']}

def account_experiments():
    from fastapi.testclient import TestClient
    from backend.app.domain.generated import make_fixture,compile_level
    from backend.app.api.v5 import GenerationRequest
    from backend.app.storage.sqlite import canonical
    with tempfile.TemporaryDirectory(prefix='v5-offline-experiment-') as tmp:
        db_path=Path(tmp)/'game-v5.sqlite'
        os.environ['GAMEPLAY_VERSION']='v5'; os.environ['SQLITE_PATH']=str(db_path)
        from backend.app.main import create_v5_app
        class NeverGenerate:
            calls=0
            async def generate(self,**kwargs): self.calls+=1; raise AssertionError('Experiments must not call LLM')
        never=NeverGenerate(); app=create_v5_app(db_path,generation_service=never)
        headers={'Origin':'http://127.0.0.1:8001'}
        def client(application): return TestClient(application,base_url='http://127.0.0.1:8001',headers=headers)
        def auth(c,name,register=True):
            csrf=c.get('/api/v2/auth/csrf').json()['data']['csrf_token']; c.headers['X-CSRF-Token']=csrf
            response=c.post('/api/v2/auth/'+('register' if register else 'login'),json={'username':name,'password':'offline experiment fixture password'})
            assert response.status_code==(201 if register else 200),response.status_code
            data=response.json()['data']; c.headers.update({'X-CSRF-Token':data['csrf_token'],'X-Auth-Context':data['auth_context']}); return data['user']['user_id']
        def version(s): return {'request_id':str(uuid4()),'revision':s['revision'],'generation':s['generation']}
        a=client(app); uid=auth(a,'experiment_a'); raw=make_fixture(1,'normal')
        for puzzle in raw['puzzles']:
            if puzzle['mechanism']=='code': puzzle.update(clue_ids=['fact_source'],recipe='concat')
        old_compiled=compile_level(raw,1,'normal',policy_version='0.9.0')
        request=GenerationRequest(request_id='private-policy-rehearsal',theme='private fixture, not AI output',room_count=1,difficulty='normal')
        status,job,dispatch=app.state.v5_database.reserve_job(uid,request); assert status==202
        app.state.v5_database.job_phase(job['job_id'],'validating'); app.state.v5_database.commit_level(job['job_id'],old_compiled)
        lid=app.state.v5_database.jobs(uid,job['job_id'])['level_id']
        response=a.post('/api/v2/sessions',json={'request_id':'old-policy-session','mode':'generated','level_id':lid}); assert response.status_code==201,response.status_code
        sid=response.json()['data']['session_id']; state=response.json()['data']['visible_state']
        response=a.post(f'/api/v2/sessions/{sid}/saves',json={**version(state),'name':'policy0.9 original archive'}); assert response.status_code==201
        save_id=response.json()['data']['slot']['save_id']
        with app.state.v5_database.transaction() as connection:
            old_definition=connection.execute('SELECT definition_json FROM generated_levels WHERE level_id=?',(lid,)).fetchone()[0]
            old_snapshot=connection.execute('SELECT snapshot_json FROM save_slots WHERE save_id=?',(save_id,)).fetchone()[0]
        for action in old_compiled.witness[:3]:
            response=a.post(f'/api/v2/sessions/{sid}/actions',json={**version(state),**action}); assert response.status_code==200
            state=response.json()['data']['visible_state']
        try: compile_level(raw,1,'normal'); raise AssertionError('New policy accepted old single clue input')
        except ValueError as error: assert str(error)=='COMBINATION_COUNT'
        restarted=create_v5_app(db_path,generation_service=never); a2=client(restarted); assert auth(a2,'experiment_a',False)==uid
        response=a2.get(f'/api/v2/sessions/{sid}/state'); assert response.status_code==200
        current=response.json()['data']['visible_state']
        response=a2.post(f'/api/v2/sessions/{sid}/saves/{save_id}/restore',json=version(current)); assert response.status_code==200,response.status_code
        restored=response.json()['data']['visible_state']; assert restored['definition_hash']==old_compiled.definition_hash and restored['generation']!=current['generation']
        with restarted.state.v5_database.transaction() as connection:
            assert connection.execute('SELECT definition_json FROM generated_levels WHERE level_id=?',(lid,)).fetchone()[0]==old_definition
            assert connection.execute('SELECT snapshot_json FROM save_slots WHERE save_id=?',(save_id,)).fetchone()[0]==old_snapshot
        e2={'status':'passed','private_rehearsal_only':True,'old_policy':'0.9.0','new_policy':'1.0.0','new_input_rejected':'COMBINATION_COUNT','old_definition_hash':old_compiled.definition_hash,'old_definition_bytes_unchanged':True,'old_snapshot_bytes_unchanged':True,'restart_restore_http_status':200,'restored_original_definition':True,'new_generation':True,'llm_calls':never.calls}
        b=client(restarted); bid=auth(b,'experiment_b')
        response=b.post('/api/v2/sessions',json={'request_id':'b-classic','mode':'classic'}); assert response.status_code==201
        bsid=response.json()['data']['session_id']; bstate=response.json()['data']['visible_state']
        with restarted.state.v5_database.transaction() as connection:
            before={r['session_id']:r['state_json'] for r in connection.execute('SELECT session_id,state_json FROM sessions WHERE session_id IN (?,?)',(sid,bsid))}
        direct=b.post(f'/api/v2/sessions/{sid}/saves/{save_id}/restore',json=version(restored))
        swapped=b.post(f'/api/v2/sessions/{bsid}/saves/{save_id}/restore',json=version(bstate))
        assert direct.status_code==404 and swapped.status_code==404
        with restarted.state.v5_database.transaction() as connection:
            after={r['session_id']:r['state_json'] for r in connection.execute('SELECT session_id,state_json FROM sessions WHERE session_id IN (?,?)',(sid,bsid))}
        assert before==after
        control_path=Path(tmp)/'isolated-control.sqlite'
        source_db=sqlite3.connect(db_path); control=sqlite3.connect(control_path); source_db.backup(control); source_db.close()
        guarded_sql='SELECT s.snapshot_json FROM save_slots s JOIN session_owners o ON o.session_id=s.session_id WHERE s.save_id=? AND o.user_id=?'
        weakened_sql=guarded_sql.replace(' AND o.user_id=?','')
        assert control.execute(guarded_sql,(save_id,bid)).fetchone() is None
        leaked=control.execute(weakened_sql,(save_id,)).fetchone(); assert leaked and leaked[0]==old_snapshot
        control.close()
        e3={'status':'passed','real_direct_foreign_session_restore_status':direct.status_code,'real_foreign_archive_on_own_session_restore_status':swapped.status_code,'real_live_states_unchanged':before==after,'guarded_control_read':'denied','weakened_isolated_control_read':'private_archive_disclosed','control_private_snapshot_sha256':hashed(leaked[0]),'control_only_removed_predicate':' AND o.user_id=?','control_guarded_sql':guarded_sql,'control_weakened_sql':weakened_sql,'product_code_modified':False,'control_is_product_vulnerability':False,'control_performed_restore':False,'database_storage':'TEMP only','llm_calls':never.calls}
        return e2,e3

def execute(output):
    expected=json.loads((output/'expected.json').read_text(encoding='utf-8'))
    if any((output/name).exists() for name in ('result.json','e1.json','e2.json','e3.json','failure.json')): raise ValueError('Refuse to overwrite prior execution epoch')
    if source()!=expected['source']: raise ValueError('Source changed after preregistration')
    before=source(); start=stamp(); run_results=[]
    try:
        rows=json.loads((output/'inputs.json').read_text(encoding='utf-8'))
        for row in rows:
            result=comparison(row); run_results.append(result)
            write(output/'e1-progress.json',run_results)
            print(encoded({'case_id':result['case_id'],'schema':result['schema_only']['status'],'full':result['full_admission']['status'],'expected':result['expected_full']}),flush=True)
        write(output/'e1.json',run_results)
        e2,e3=account_experiments(); write(output/'e2.json',e2); write(output/'e3.json',e3)
        assert source()==before,'Source changed during execution'
        good=[r for r in run_results if r['category']=='good']; bad=[r for r in run_results if r['category'] not in {'good','limit'}]; limits=[r for r in run_results if r['category']=='limit']
        summary={'good_admitted':sum(r['full_admission']['status']=='accept' for r in good),'good_total':len(good),'bad_false_admissions':sum(r['full_admission']['status']=='accept' for r in bad),'bad_total':len(bad),'bad_schema_only_accepts':sum(r['schema_only']['status']=='accept' for r in bad),'limits_expected_matches':sum(r['matches_preregistered'] for r in limits),'limits_total':len(limits)}
        passed=all(r['matches_preregistered'] for r in run_results)
        result={'kind':'owner_offline_experiments_not_formal_qa','status':'passed' if passed else 'failed','start_utc':start,'end_utc':stamp(),'source_before':before,'source_after':source(),'summary':summary,'e2':e2['status'],'e3':e3['status'],'network_calls':0,'paid_calls':0,'limitations':expected['scope_notes']}
        write(output/'result.json',result); print(encoded(result['summary']))
        return 0 if passed else 1
    except BaseException as error:
        write(output/'failure.json',{'status':'failed','start_utc':start,'end_utc':stamp(),'completed_comparisons':len(run_results),'exception_type':type(error).__name__,'reason':str(error)[:240] if isinstance(error,(AssertionError,ValueError)) else 'sanitized','source_before':before,'source_after':source(),'paid_calls':0})
        raise

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output',required=True,type=Path); parser.add_argument('--prepare',action='store_true'); args=parser.parse_args()
    output=args.output.resolve()
    if not output.is_relative_to((ROOT/'evidence/upgrade/v5.0/experiments-owner').resolve()): raise ValueError('Output must stay in owner evidence directory')
    if args.prepare: prepare(output); return 0
    return execute(output)
if __name__=='__main__': raise SystemExit(main())
