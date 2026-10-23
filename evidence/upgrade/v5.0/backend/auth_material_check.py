"""Small owner probes for auth-cookie reuse and canonical material order only."""
import copy,hashlib,json,os,secrets,tempfile,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from backend.app.domain.generated import compile_level,GeneratedRules
from backend.app.storage.sqlite import validate_snapshot
from backend.app.storage.v5 import digest
BASE=Path('evidence/upgrade/v5.0/backend')

def material_probe():
    path=BASE/'auth-material-fix-baseline.json'; before=path.read_bytes(); baseline=json.loads(before)
    records=[]
    for name,fixture in baseline['fixtures'].items():
        compiled=compile_level(fixture['raw'],1,'easy'); rules=GeneratedRules(compiled); state=rules.initial_state()
        assert compiled.definition_hash==fixture['definition_hash'] and compiled.answers==fixture['answers']
        def description(s): return next(o['description'] for o in rules.visible_state('fixture_session',s)['objects'] if o['object_id']=='obj_puzzle_0')
        assert not description(state).startswith('资料组合次序：')
        state,_=rules.apply_action(state,'inspect',{'object_id':'obj_puzzle_0'})
        state,_=rules.apply_action(state,'inspect',{'object_id':'obj_source'})
        assert not description(state).startswith('资料组合次序：') and 'fact_order' not in description(state)
        state,_=rules.apply_action(state,'inspect',{'object_id':'obj_order'})
        public=rules.visible_state('fixture_session',state); titles={c['clue_id']:c['title'] for c in public['clues']}
        target=compiled.draft.puzzles[0]; expected='资料组合次序：'+' → '.join(titles[cid] for cid in target.clue_ids)+'；'
        assert description(state).startswith(expected)
        assert not any(str(answer) in description(state) for answer in compiled.answers.values() if isinstance(answer,str) and len(answer)>=3)
        unobserved=rules.initial_state()
        for oid in ('obj_source','obj_order'): unobserved,_=rules.apply_action(unobserved,'inspect',{'object_id':oid})
        assert not description(unobserved).startswith('资料组合次序：')
        restored=validate_snapshot(fixture['snapshot_json'],'fixture_session',rules.initial_state(),rules)
        assert restored.definition_hash==fixture['definition_hash'] and restored.discovered_clue_ids==['fact_source','fact_order']
        records.append({'fixture':name,'definition_hash_and_answers_unchanged':True,'required_material_and_observation_gate':True,'canonical_title_order_visible':True,'old_snapshot_restores':True})
    conflict=copy.deepcopy(baseline['fixtures']['map_same_value']['raw']); conflict['clues'][1]['symbol_map']['A']='9'
    try: compile_level(conflict,1,'easy'); raise AssertionError('Conflicting material admitted')
    except ValueError as error: assert str(error)=='CONFLICTING_MAP'
    assert path.read_bytes()==before
    return {'valid_fixtures':records,'same_value_map_allowed':True,'conflicting_map_rejected':'CONFLICTING_MAP','baseline_snapshot_file_bytes_unchanged':True}

def auth_probe():
    with tempfile.TemporaryDirectory(prefix='v5-auth-material-owner-') as tmp:
        os.environ['GAMEPLAY_VERSION']='v5'; os.environ['SQLITE_PATH']=str(Path(tmp)/'game-v5.sqlite'); os.environ['AI_PROVIDER']='mock'
        from backend.app.main import create_v5_app
        from fastapi.testclient import TestClient
        app=create_v5_app(); db=app.state.v5_database
        client=TestClient(app,base_url='http://127.0.0.1:8001',headers={'Origin':'http://127.0.0.1:8001'})
        initial=client.get('/api/v2/auth/csrf'); assert initial.status_code==200
        first=initial.json()['data']['csrf_token']; nonce=client.cookies.get('campus_v5_csrf')
        with db.transaction() as c: created=c.execute('SELECT created_at FROM anonymous_csrf WHERE nonce_hash=?',(digest(nonce),)).fetchone()[0]
        again=client.get('/api/v2/auth/csrf'); assert again.status_code==200 and again.json()['data']['csrf_token']==first
        assert 'set-cookie' not in again.headers
        with db.transaction() as c:
            row=c.execute('SELECT * FROM anonymous_csrf WHERE nonce_hash=?',(digest(nonce),)).fetchone()
            assert row['created_at']==created and row['nonce_hash']!=nonce and row['csrf_hash']!=first
        client.headers['X-CSRF-Token']=first
        registered=client.post('/api/v2/auth/register',json={'username':'auth_material_a','password':'offline auth material fixture password'}); assert registered.status_code==201,registered.status_code
        auth=registered.json()['data']; client.headers.update({'X-CSRF-Token':auth['csrf_token'],'X-Auth-Context':auth['auth_context']})
        logout=client.post('/api/v2/auth/logout',json={}); assert logout.status_code==200
        anon_after_logout=client.cookies.get('campus_v5_csrf'); assert anon_after_logout and anon_after_logout!=nonce
        assert 'campus_v5_csrf=' in logout.headers.get('set-cookie','') and 'campus_v5_session' not in client.cookies
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(lambda _:client.get('/api/v2/auth/csrf'),range(2)))
        tokens=[response.json()['data']['csrf_token'] for response in responses]
        assert tokens[0]==tokens[1] and all('set-cookie' not in response.headers for response in responses)
        duplicate=[('Origin','http://127.0.0.1:8001'),('X-CSRF-Token',tokens[0]),('X-CSRF-Token','extra-invalid')]
        response=client.post('/api/v2/auth/register',json={'username':'auth_material_b','password':'offline auth material fixture password'},headers=duplicate); assert response.status_code==403
        client.headers['X-CSRF-Token']=tokens[0]
        registered_b=client.post('/api/v2/auth/register',json={'username':'auth_material_b','password':'offline auth material fixture password'}); assert registered_b.status_code==201,registered_b.status_code
        auth_b=registered_b.json()['data']
        stale=client.post('/api/v2/sessions',json={'request_id':'stale-context','mode':'classic'},headers={'X-CSRF-Token':auth_b['csrf_token'],'X-Auth-Context':auth['auth_context']}); assert stale.status_code==403
        temporary_nonce,temporary_csrf=db.anonymous()
        with db.transaction() as c: c.execute('UPDATE anonymous_csrf SET created_at=? WHERE nonce_hash=?',(time.time()-601,digest(temporary_nonce)))
        replaced,_=db.anonymous(temporary_nonce); assert replaced!=temporary_nonce and not db.check_anonymous(temporary_nonce,temporary_csrf)
        legacy_nonce=secrets.token_urlsafe(32); legacy_csrf=secrets.token_urlsafe(32)
        with db.transaction() as c: c.execute('INSERT INTO anonymous_csrf VALUES(?,?,?)',(digest(legacy_nonce),digest(legacy_csrf),time.time()))
        rotated,rotated_csrf=db.anonymous(legacy_nonce); reused,reused_csrf=db.anonymous(rotated)
        assert rotated!=legacy_nonce and rotated==reused and rotated_csrf==reused_csrf and not db.check_anonymous(legacy_nonce,legacy_csrf)
        return {'anon_get_reuses_nonce_and_csrf':True,'get_does_not_slide_database_time_or_cookie_expiry':True,'nonce_and_csrf_hash_only':True,'logout_seeds_anon_cookie_before_parallel_gets':True,'two_parallel_gets_same_csrf':True,'following_registration_status':registered_b.status_code,'duplicate_csrf_status':response.status_code,'stale_auth_context_status':stale.status_code,'expired_nonce_rotates':True,'legacy_random_csrf_row_rotates_once':True,'paid_calls':0,'network_calls':0,'database':'TEMP only'}

def main():
    result={'kind':'owner_narrow_auth_material_probe_not_formal_qa','material':material_probe(),'auth':auth_probe(),'paid_calls':0,'network_calls':0}
    (BASE/'auth-material-probe-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'passed','valid_material_fixtures':len(result['material']['valid_fixtures']),'hashes_answers_old_snapshots_unchanged':True,'conflict_rejected':True,'parallel_anon_csrf_then_register':201,'paid_calls':0,'network_calls':0}))
if __name__=='__main__': main()
