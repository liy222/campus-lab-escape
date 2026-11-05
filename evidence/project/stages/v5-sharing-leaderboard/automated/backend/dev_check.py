"""Backend owner development probe; TEMP/Synthetic only, not formal QA."""
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import traceback
from contextlib import closing
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).parent


def main():
    checks = []
    def check(name, value):
        assert value, name
        checks.append(name)
    with tempfile.TemporaryDirectory(prefix='v5-sharing-owner-') as directory:
        database = Path(directory) / 'game-v5.sqlite'
        os.environ.update(SQLITE_PATH=str(database), GAMEPLAY_VERSION='v5', AI_PROVIDER='mock')
        from fastapi.testclient import TestClient
        from jsonschema import Draft202012Validator
        from backend.app.api.v5 import create_v5_application, GenerationRequest
        from backend.app.domain.generated import make_fixture, compile_level
        from backend.app.storage import sharing
        from backend.app.storage.v5 import V5Database
        spec = importlib.util.spec_from_file_location('sharing_contract_build', ROOT/'contracts/v2/build_contracts.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        artifacts = module.build()
        for name in ('api.schema.json', 'routes.json'):
            (ROOT/'contracts/v2'/name).write_text(json.dumps(artifacts[name], ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        schema = artifacts['api.schema.json']
        def validate(name, value):
            Draft202012Validator({'$defs': schema['$defs'], '$ref': '#/$defs/'+name}).validate(value)
        app = create_v5_application(database)
        db = app.state.v5_database
        clients = []
        for name in ('share_owner', 'share_guest', 'share_outsider'):
            client = TestClient(app, base_url='http://127.0.0.1:8001')
            csrf = client.get('/api/v2/auth/csrf').json()['data']['csrf_token']
            response = client.post('/api/v2/auth/register', headers={'Origin':'http://127.0.0.1:8001', 'X-CSRF-Token':csrf}, json={'username':name,'password':'Synthetic-password-Only'})
            assert response.status_code == 201
            auth = response.json()['data']
            client.headers.update({'Origin':'http://127.0.0.1:8001','X-CSRF-Token':auth['csrf_token'],'X-Auth-Context':auth['auth_context']})
            clients.append(client)
        a,b,c = clients
        uid = a.get('/api/v2/auth/me').json()['data']['user']['user_id']
        request = GenerationRequest(request_id='owner_fixture',theme='Synthetic offline fixture',room_count=1,difficulty='easy')
        _,job,_=db.reserve_job(uid,request); db.job_phase(job['job_id'],'validating')
        compiled = compile_level(make_fixture(1,'easy'),1,'easy')
        db.commit_level(job['job_id'],compiled)
        level = db.levels(uid)[0]; lid=level['level_id']
        check('unpublished_defaults',level['sharing']=={'share_id':None,'published':False,'revision':0,'published_at':None})
        published = a.post(f'/api/v2/levels/{lid}/sharing',json={'published':True,'revision':0})
        check('publish_and_contract',published.status_code==200)
        validate('sharing_response',published.json())
        state=published.json()['data']['sharing']; share=state['share_id']
        check('non_author_private_metadata_404',b.get(f'/api/v2/levels/{lid}').status_code==404)
        check('non_author_publish_404',b.post(f'/api/v2/levels/{lid}/sharing',json={'published':False,'revision':1}).status_code==404)
        check('stale_publication_409',a.post(f'/api/v2/levels/{lid}/sharing',json={'published':False,'revision':0}).status_code==409)
        hall=b.get('/api/v2/shared-levels'); validate('shared_levels_response',hall.json())
        check('hall_same_definition_and_date',hall.json()['data']['shared_levels'][0]['definition_hash']==level['definition_hash'] and hall.json()['data']['shared_levels'][0]['created_at']==level['created_at'])
        instant=[2_000_000_000_000]
        with patch.object(sharing,'now_ms',lambda:instant[0]):
            join=b.post(f'/api/v2/shared-levels/{share}/sessions',json={'request_id':'guest_join'})
            validate('session_response',join.json()); check('first_shared_join_201',join.status_code==201)
            sid=join.json()['data']['session_id']; initial=join.json()['data']['visible_state']; attempt=initial['challenge']['attempt_id']
            check('repeat_join_200',b.post(f'/api/v2/shared-levels/{share}/sessions',json={'request_id':'guest_join'}).status_code==200)
            author_join=a.post(f'/api/v2/shared-levels/{share}/sessions',json={'request_id':'author_join'}).json()['data']
            private=a.post('/api/v2/sessions',json={'request_id':'private','mode':'generated','level_id':lid}).json()['data']
            check('author_private_shared_independent',author_join['session_id']!=private['session_id'] and 'share_id' not in private['visible_state'])
            check('cross_user_state_404',a.get(f'/api/v2/sessions/{sid}/state').status_code==404)
            def current(): return b.get(f'/api/v2/sessions/{sid}/state').json()['data']['visible_state']
            sequence=[0]
            def mutate(endpoint, extra=None):
                sequence[0]+=1; s=current()
                body={'request_id':'mutation_'+str(sequence[0]),'generation':s['generation'],'revision':s['revision'],**(extra or {})}
                response=b.post(f'/api/v2/sessions/{sid}/'+endpoint,json=body)
                check('mutation_'+str(sequence[0]),response.status_code in (200,201))
                return response.json(),body
            saved,_=mutate('saves',{'name':'same attempt'})
            save_id=saved['data']['slot']['save_id']
            instant[0]+=2000
            restored,_=mutate(f'saves/{save_id}/restore')
            check('same_attempt_restore_clock_preserved',restored['data']['visible_state']['challenge']['attempt_id']==attempt and restored['data']['visible_state']['challenge']['status']=='active')
            hint,_=mutate('ai/turns',{'message':'请提示','hint_level':1})
            check('free_hint_cumulative',hint['data']['visible_state']['challenge']['hint_count']==1)
            for action in compiled.witness:
                instant[0]+=1000
                last,body=mutate('actions',action)
            finished=last['data']['visible_state']['challenge']
            check('action_finish_exact_elapsed',finished['status']=='finished' and finished['elapsed_ms']==2000+1000*len(compiled.witness))
            check('hint_count_survives_restore',finished['hint_count']==1)
            replay=b.post(f'/api/v2/sessions/{sid}/actions',json=body)
            check('win_receipt_replay',replay.status_code==200 and replay.json()['data']['replayed'])
            leaderboard=b.get(f'/api/v2/shared-levels/{share}/leaderboard').json(); validate('leaderboard_response',leaderboard)
            check('one_best_entry',leaderboard['data']['total_players']==1 and leaderboard['data']['own_entry']['elapsed_ms']==finished['elapsed_ms'])
            mutate('reset')
            cross,_=mutate(f'saves/{save_id}/restore')
            check('cross_attempt_restore_practice',cross['data']['visible_state']['challenge']['status']=='practice')
            for action in compiled.witness: mutate('actions',action)
            check('practice_win_no_score',b.get(f'/api/v2/shared-levels/{share}/leaderboard').json()['data']['own_entry']['attempt_id']==attempt)
            mutate('reset')
            for action in compiled.witness:
                instant[0]+=1; faster,_=mutate('actions',action)
            check('new_fastest_best',b.get(f'/api/v2/shared-levels/{share}/leaderboard').json()['data']['own_entry']['elapsed_ms']==len(compiled.witness))
            before=current()['challenge']; restored,_=mutate(f'saves/{save_id}/restore')
            check('finished_record_immutable_new_practice',restored['data']['visible_state']['challenge']['status']=='practice' and restored['data']['visible_state']['challenge']['attempt_id']!=before['attempt_id'])
            with db.transaction() as connection:
                before_count=connection.execute('SELECT COUNT(*) FROM save_slots').fetchone()[0]
            with patch.object(sharing,'after_mutation',side_effect=RuntimeError('Synthetic rollback only')):
                s=current(); result=b.post(f'/api/v2/sessions/{sid}/saves',json={'request_id':'fault','revision':s['revision'],'generation':s['generation']})
                check('hook_failure_500',result.status_code==500)
            with db.transaction() as connection:
                check('hook_failure_atomic_rollback',connection.execute('SELECT COUNT(*) FROM save_slots').fetchone()[0]==before_count and connection.execute("SELECT COUNT(*) FROM action_receipts WHERE request_id='fault'").fetchone()[0]==0)
            a.post(f'/api/v2/levels/{lid}/sharing',json={'published':False,'revision':1})
            check('cancel_blocks_new_join',c.post(f'/api/v2/shared-levels/{share}/sessions',json={'request_id':'new_join'}).status_code==404)
            check('cancel_preserves_joined',b.get('/api/v2/shared-levels?view=joined').json()['data']['shared_levels'][0]['published'] is False and b.get(f'/api/v2/shared-levels/{share}').status_code==200)
            check('cancel_hides_hall',c.get('/api/v2/shared-levels').json()['data']['total']==0)
            check('cancel_existing_resume',b.post(f'/api/v2/shared-levels/{share}/sessions',json={'request_id':'resume_cancelled'}).status_code==200)
            republish=a.post(f'/api/v2/levels/{lid}/sharing',json={'published':True,'revision':2}).json()['data']['sharing']
            check('republish_same_identity',republish['share_id']==share and republish['published_at']==state['published_at'])
            validate('sessions_response',b.get('/api/v2/sessions').json())
            check('private_session_bypass_404',b.post('/api/v2/sessions',json={'request_id':'bypass','mode':'generated','level_id':lid}).status_code==404)
        before_restart=b.get(f'/api/v2/sessions/{sid}/state').json()['data']['visible_state']['challenge']
        reopened=V5Database(database)
        with reopened.transaction() as connection:
            check('restart_challenge_persisted',sharing.challenge_projection(connection,sid)==before_restart)
            check('migration_marker',connection.execute("SELECT value FROM v5_metadata WHERE key='sharing_schema_version'").fetchone()[0]=='1')
        check('new_db_no_backup',not (database.parent/'backups').exists())
        # Simulate a pre-sharing V5 copy entirely within TEMP; snapshots unchanged.
        old=Path(directory)/'old-game-v5.sqlite'
        with closing(sqlite3.connect(database)) as source, closing(sqlite3.connect(old)) as dest: source.backup(dest)
        with closing(sqlite3.connect(old)) as connection:
            for table in ('shared_save_origins','challenge_attempts','shared_sessions','shared_levels'): connection.execute('DROP TABLE '+table)
            connection.execute("DELETE FROM v5_metadata WHERE key='sharing_schema_version'")
            connection.commit()
        V5Database(old)
        backups=list((old.parent/'backups').glob('old-game-v5-sharing-v1-*.sqlite'))
        check('old_v5_consistent_backup_once',len(backups)==1)
        V5Database(old)
        check('migration_idempotent_no_second_backup',len(list((old.parent/'backups').glob('old-game-v5-sharing-v1-*.sqlite')))==1)
        with closing(sqlite3.connect(backups[0])) as connection:
            check('backup_is_pre_migration',connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='shared_levels'").fetchone()[0]==0)
        for client in clients: client.close()
        return checks


if __name__=='__main__':
    try:
        checks=main()
        result={'kind':'backend_owner_development_not_formal_qa','exit_code':0,'checks':checks,'count':len(checks),'database':'TEMP only','model_calls':0,'paid_calls':0}
        code=0
    except BaseException:
        result={'kind':'backend_owner_development_not_formal_qa','exit_code':1,'failure':traceback.format_exc(),'database':'TEMP only','model_calls':0,'paid_calls':0}
        code=1
    name='dev-result-'+__import__('datetime').datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.json'
    (OUT/name).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'exit_code':code,'count':result.get('count'),'result':str(OUT/name),'failure':result.get('failure')},ensure_ascii=False))
    raise SystemExit(code)
