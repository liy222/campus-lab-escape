"""Backend-owner development checks; isolated fixtures, never paid provider calls."""
import copy
import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient

def main():
    with tempfile.TemporaryDirectory(prefix='v5-backend-owner-') as tmp:
        os.environ['GAMEPLAY_VERSION']='v5'
        os.environ['SQLITE_PATH']=str(Path(tmp)/'game-v5.sqlite')
        from backend.app.main import create_v5_app
        from backend.app.domain.generated import make_fixture,compile_level,GeneratedRules
        results=[]
        for rooms in (1,2,3):
            for difficulty in ('easy','normal','hard'):
                compiled=compile_level(make_fixture(rooms,difficulty),rooms,difficulty)
                rules=GeneratedRules(compiled); state=rules.initial_state()
                for action in compiled.witness: state,_=rules.apply_action(state,action['tool'],action['arguments'])
                assert state.status=='won'
                results.append({'rooms':rooms,'difficulty':difficulty,'actions':len(compiled.witness)})
        raw=make_fixture(1,'normal')
        for puzzle in raw['puzzles']:
            if puzzle['mechanism']=='code': puzzle['clue_ids']=['fact_source']; puzzle['recipe']='concat'
        old=compile_level(raw,1,'normal',policy_version='0.9.0')
        try: compile_level(raw,1,'normal'); raise AssertionError('policy1 accepted single clue normal')
        except ValueError as error: assert str(error)=='COMBINATION_COUNT'
        assert old.policy_version=='0.9.0'
        bad=copy.deepcopy(make_fixture(1,'easy')); bad['rooms'][0]['objects'][1]['locked_by']=['puzzle_0']
        try: compile_level(bad,1,'easy'); raise AssertionError('selflock admitted')
        except ValueError: pass
        class FixtureGeneration:
            calls=0
            async def generate(self,**kwargs):
                self.calls+=1
                return make_fixture(kwargs['room_count'],kwargs['difficulty'])
        fixture=FixtureGeneration(); app=create_v5_app(generation_service=fixture)
        headers={'Origin':'http://127.0.0.1:8001'}
        a=TestClient(app,base_url='http://127.0.0.1:8001',headers=headers)
        def register(client,name):
            csrf=client.get('/api/v2/auth/csrf').json()['data']['csrf_token']
            client.headers['X-CSRF-Token']=csrf
            response=client.post('/api/v2/auth/register',json={'username':name,'password':'offline fixture password 123'})
            assert response.status_code==201,response.text
            auth=response.json()['data']
            client.headers.update({'X-CSRF-Token':auth['csrf_token'],'X-Auth-Context':auth['auth_context']})
            return auth
        auth=register(a,'fixture_A')
        assert a.get('/api/v2/auth/me').json()['data']['csrf_token']==auth['csrf_token']
        def version(state): return {'request_id':str(uuid4()),'revision':state['revision'],'generation':state['generation']}
        classic=a.post('/api/v2/sessions',json={'request_id':'classic','mode':'classic'}); assert classic.status_code==201,classic.text
        cs=classic.json()['data']['visible_state']; cid=classic.json()['data']['session_id']
        ai=a.post(f'/api/v2/sessions/{cid}/ai/turns',json={**version(cs),'message':'next','hint_level':1},headers={'X-AI-Provider':'mock'}); assert ai.status_code==200,ai.text
        payload={'request_id':'generation1','theme':'offline fixture','room_count':3,'difficulty':'hard'}
        job=a.post('/api/v2/level-generations',json=payload,headers={'X-AI-Api-Key':'offline-fixture-placeholder'}); assert job.status_code==202,job.text
        jid=job.json()['data']['job']['job_id']; job=a.get('/api/v2/level-generations/'+jid)
        assert job.json()['data']['job']['status']=='ready',job.text
        replay=a.post('/api/v2/level-generations',json=payload,headers={'X-AI-Api-Key':'offline-fixture-placeholder'}); assert replay.status_code==200 and fixture.calls==1
        lid=job.json()['data']['job']['level_id']; response=a.post('/api/v2/sessions',json={'request_id':'generated','mode':'generated','level_id':lid}); assert response.status_code==201,response.text
        sid=response.json()['data']['session_id']; state=response.json()['data']['visible_state']
        ai=a.post(f'/api/v2/sessions/{sid}/ai/turns',json={**version(state),'message':'next','hint_level':1},headers={'X-AI-Provider':'mock'}); assert ai.status_code==200,ai.text
        state=ai.json()['data']['visible_state']
        response=a.post(f'/api/v2/sessions/{sid}/saves',json={**version(state),'name':'early'}); assert response.status_code==201,response.text
        save_id=response.json()['data']['slot']['save_id']
        owner=app.state.v5_database.authenticate(a.cookies.get('campus_v5_session')); store=app.state.v5_database.owned(owner,sid)
        for action in store.rules.compiled.witness:
            response=a.post(f'/api/v2/sessions/{sid}/actions',json={**version(state),**action}); assert response.status_code==200,response.text
            state=response.json()['data']['visible_state']
        assert state['status']=='won'
        response=a.post(f'/api/v2/sessions/{sid}/saves/{save_id}/restore',json=version(state)); assert response.status_code==200,response.text
        restored=response.json()['data']['visible_state']; assert restored['generation']!=state['generation']
        b=TestClient(app,base_url='http://127.0.0.1:8001',headers=headers); register(b,'fixture_B')
        assert b.get(f'/api/v2/sessions/{sid}/state').status_code==404
        assert b.get('/api/v2/levels/'+lid).status_code==404
        assert a.post('/api/sessions',json={}).status_code==404
        assert a.post('/api/v2/sessions',json={'request_id':'bad','mode':'classic'},headers={'Origin':'null'}).status_code==403
        assert a.post('/api/v2/sessions',content='{}',headers={'Content-Type':'text/plain'}).status_code==415
        assert a.get('/api/v2/auth/me',headers={'X-Forwarded-Host':'localhost'}).status_code==400
        old_db=Path(tmp)/'old.sqlite'; connection=sqlite3.connect(old_db); connection.execute('CREATE TABLE valuable(value TEXT)'); connection.commit(); connection.close()
        before=hashlib.sha256(old_db.read_bytes()).hexdigest()
        try: create_v5_app(old_db); raise AssertionError('old DB accepted')
        except ValueError: pass
        assert before==hashlib.sha256(old_db.read_bytes()).hexdigest()
        # The definition hash includes versions. Corruption must preserve live bytes.
        with app.state.v5_database.transaction() as connection:
            live_before=connection.execute('SELECT state_json FROM sessions WHERE session_id=?',(sid,)).fetchone()[0]
            connection.execute("UPDATE generated_levels SET definition_hash='invalid' WHERE level_id=?",(lid,))
        response=a.post(f'/api/v2/sessions/{sid}/saves/{save_id}/restore',json=version(restored)); assert response.status_code==409,response.text
        with app.state.v5_database.transaction() as connection: assert connection.execute('SELECT state_json FROM sessions WHERE session_id=?',(sid,)).fetchone()[0]==live_before
        result={'kind':'owner_development_not_formal_qa','fixtures':results,'policy_0_9_private_rehearsal':True,'policy_1_0_rejects_single_clue_normal':True,'selflock_rejected':True,'api_integration':'passed','generated_actions':len(store.rules.compiled.witness),'fixture_service_calls':fixture.calls,'paid_provider_calls':0,'old_database_unchanged':True,'definition_corruption_preserves_live':True}
        print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__': main()
