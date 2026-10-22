"""Narrow owner check: simulated service metadata, never a provider/network call."""
import json,os,tempfile
from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient

def main():
    with tempfile.TemporaryDirectory(prefix='v5-history-owner-') as tmp:
        os.environ['GAMEPLAY_VERSION']='v5'; os.environ['SQLITE_PATH']=str(Path(tmp)/'game-v5.sqlite')
        from backend.app.main import create_v5_app
        from backend.app.ai.v5 import local_hint
        class FixtureService:
            def __init__(self): self.captured=[]
            async def turn(self,**kwargs):
                self.captured.append({'message':kwargs['message'],'history':kwargs['history']})
                if kwargs['provider']=='mock': return local_hint(kwargs['public_state'],kwargs['hint_level'])
                calls=0 if kwargs['message']=='local-reminder' else 1
                return {'answer':'可以先点击墙钟查看。','clue_refs':[],'count_hint':bool(calls),'status':'completed','stop_reason':None,'usage':{'provider':'deepseek','model':'deepseek-flash' if calls else None,'input_tokens':1 if calls else None,'output_tokens':1 if calls else None,'model_calls':calls,'read_tool_calls':0}}
        service=FixtureService(); app=create_v5_app(companion_service=service)
        client=TestClient(app,base_url='http://127.0.0.1:8001',headers={'Origin':'http://127.0.0.1:8001'})
        csrf=client.get('/api/v2/auth/csrf').json()['data']['csrf_token']; client.headers['X-CSRF-Token']=csrf
        response=client.post('/api/v2/auth/register',json={'username':'history_fixture','password':'offline history fixture password'}); assert response.status_code==201
        auth=response.json()['data']; client.headers.update({'X-CSRF-Token':auth['csrf_token'],'X-Auth-Context':auth['auth_context']})
        response=client.post('/api/v2/sessions',json={'request_id':'session','mode':'classic'}); assert response.status_code==201
        sid=response.json()['data']['session_id']; state=response.json()['data']['visible_state']
        def version(): return {'request_id':str(uuid4()),'revision':state['revision'],'generation':state['generation']}
        response=client.post(f'/api/v2/sessions/{sid}/saves',json={**version(),'name':'before-history'}); assert response.status_code==201
        save_id=response.json()['data']['slot']['save_id']
        def turn(message,provider):
            nonlocal state
            response=client.post(f'/api/v2/sessions/{sid}/ai/turns',json={**version(),'message':message,'hint_level':1},headers={'X-AI-Provider':provider,'X-AI-Api-Key':'offline-fixture-placeholder'} if provider=='deepseek' else {'X-AI-Provider':'mock'})
            assert response.status_code==200,response.text
            state=response.json()['data']['visible_state']
            return service.captured[-1]['history']
        assert turn('free-1','mock')==[]
        assert turn('real-1','deepseek')==[]
        assert [x['question'] for x in turn('local-reminder','deepseek') if x['kind']=='dialogue']==['real-1']
        assert [x['question'] for x in turn('free-2','mock') if x['kind']=='dialogue']==['real-1']
        assert [x['question'] for x in turn('real-2','deepseek') if x['kind']=='dialogue']==['real-1']
        response=client.post(f'/api/v2/sessions/{sid}/actions',json={**version(),'tool':'inspect','arguments':{'object_id':'r1_clock'}}); assert response.status_code==200
        state=response.json()['data']['visible_state']
        history=turn('real-3','deepseek')
        assert [x['question'] for x in history if x['kind']=='dialogue']==['real-1','real-2']
        assert [x for x in history if x['kind']=='action']==[{'kind':'action','tool':'inspect'}]
        turn('real-4','deepseek'); history=turn('real-5','deepseek')
        assert [x['question'] for x in history if x['kind']=='dialogue']==['real-2','real-3','real-4']
        response=client.post(f'/api/v2/sessions/{sid}/saves/{save_id}/restore',json=version()); assert response.status_code==200
        state=response.json()['data']['visible_state']; assert turn('after-restore','deepseek')==[]
        response=client.post(f'/api/v2/sessions/{sid}/reset',json=version()); assert response.status_code==200
        state=response.json()['data']['visible_state']; assert turn('after-reset','deepseek')==[]
        print(json.dumps({'status':'passed','mock_and_local_reminders_excluded':True,'last_three_successful_model_dialogues':True,'actions_parameter_free':True,'restore_generation_history_empty':True,'reset_generation_history_empty':True,'simulated_service_calls':len(service.captured),'network_calls':0,'paid_provider_calls':0}))
if __name__=='__main__': main()
