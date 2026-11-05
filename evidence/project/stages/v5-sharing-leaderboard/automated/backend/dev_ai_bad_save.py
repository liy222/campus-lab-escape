"""Narrow owner-only Synthetic AI / invalid snapshot development probe."""
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback
from datetime import datetime

ROOT=Path(__file__).resolve().parents[6]
sys.path.insert(0,str(ROOT))


def main():
    checks=[]
    def check(name,condition):
        assert condition,name
        checks.append(name)
    with tempfile.TemporaryDirectory(prefix='v5-sharing-ai-owner-') as directory:
        path=Path(directory)/'game-v5.sqlite'
        os.environ.update(SQLITE_PATH=str(path),GAMEPLAY_VERSION='v5',AI_PROVIDER='mock')
        from fastapi.testclient import TestClient
        from backend.app.api.v5 import create_v5_application, GenerationRequest, COOKIE
        from backend.app.storage.sqlite import new_id
        from backend.app.domain.generated import make_fixture,compile_level
        app=create_v5_application(path); db=app.state.v5_database
        uid=new_id()
        with db.transaction() as c:
            c.execute('INSERT INTO users VALUES(?,?,?,?)',(uid,'synthetic_owner','unused_synthetic_hash',0))
        token,csrf,auth=db.rotate(uid)
        client=TestClient(app,base_url='http://127.0.0.1:8001')
        client.cookies.set(COOKIE,token,path='/api/v2')
        client.headers.update({'Origin':'http://127.0.0.1:8001','X-CSRF-Token':csrf,'X-Auth-Context':auth['auth_context']})
        _,job,_=db.reserve_job(uid,GenerationRequest(request_id='fixture',theme='Synthetic',room_count=1,difficulty='easy'))
        db.job_phase(job['job_id'],'validating'); db.commit_level(job['job_id'],compile_level(make_fixture(1,'easy'),1,'easy'))
        lid=db.levels(uid)[0]['level_id']; _,data=db.set_sharing(uid,lid,True,0); share=data['sharing']['share_id']
        joined=client.post(f'/api/v2/shared-levels/{share}/sessions',json={'request_id':'join'}).json()['data']; sid=joined['session_id']
        def current(): return client.get(f'/api/v2/sessions/{sid}/state').json()['data']['visible_state']
        def body(rid,**extra):
            state=current()
            return {'request_id':rid,'revision':state['revision'],'generation':state['generation'],**extra}
        class Fake:
            mode='success'
            async def turn(self,**kwargs):
                if self.mode=='timeout': raise TimeoutError('Synthetic')
                if self.mode=='invalid': return {'answer':'<script>','clue_refs':[]}
                result={'answer':'可以先查看可见资料，再比较装置说明与材料的局部关系。','clue_refs':[],'count_hint':False}
                if self.mode=='local': result['usage']={'model_calls':0}
                return result
        fake=Fake(); app.state.companion_service=fake
        headers={'X-AI-Provider':'deepseek','X-AI-Api-Key':'Synthetic-not-a-provider-key'}
        before=current(); request=body('success',message='讨论局部关系',hint_level=1)
        response=client.post(f'/api/v2/sessions/{sid}/ai/turns',headers=headers,json=request)
        check('synthetic_reply_delivered',response.status_code==200)
        after=current()
        check('count_hint_false_optional_usage_companion_counted',after['challenge']['companion_count']==1 and after['challenge']['hint_count']==0)
        check('challenge_mutation_revision_increment',after['revision']==before['revision']+1)
        replay=client.post(f'/api/v2/sessions/{sid}/ai/turns',headers=headers,json=request)
        check('ai_receipt_replay_no_double_count',replay.status_code==200 and current()['challenge']==after['challenge'] and current()['revision']==after['revision'])
        for mode,expected in [('invalid',502),('timeout',504),('local',200)]:
            fake.mode=mode; prior=current()
            result=client.post(f'/api/v2/sessions/{sid}/ai/turns',headers=headers,json=body(mode,message='讨论局部关系',hint_level=1))
            check(mode+'_status',result.status_code==expected)
            check(mode+'_no_assistance_or_revision_change',current()['challenge']==prior['challenge'] and current()['revision']==prior['revision'])
        saved=client.post(f'/api/v2/sessions/{sid}/saves',json=body('save',name='corrupt Synthetic')).json()['data']['slot']['save_id']
        before=current()
        with db.transaction() as c:
            c.execute('UPDATE save_slots SET snapshot_json=? WHERE save_id=?',('{"checksum":"invalid"}',saved))
        response=client.post(f'/api/v2/sessions/{sid}/saves/{saved}/restore',json=body('bad_restore'))
        check('bad_snapshot_rejected',response.status_code==409 and response.json()['error']['code']=='INVALID_SNAPSHOT')
        check('bad_snapshot_preserves_challenge_and_state',current()==before)
        client.close()
    return checks


if __name__=='__main__':
    try:
        checks=main(); result={'exit_code':0,'checks':checks,'count':len(checks)}; code=0
    except BaseException:
        result={'exit_code':1,'failure':traceback.format_exc()}; code=1
    result.update(kind='backend_owner_development_not_formal_qa',database='TEMP only',model_calls=0,paid_calls=0)
    output=Path(__file__).parent/('ai-bad-save-'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.json')
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'exit_code':code,'result':str(output),'count':result.get('count'),'failure':result.get('failure')},ensure_ascii=False))
    raise SystemExit(code)
