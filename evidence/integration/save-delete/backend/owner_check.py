"""Backend Owner narrow development verification, not independent/formal QA."""
import hashlib
import json
import os
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

checks = []
def check(name, condition):
    assert condition, name
    checks.append({'name': name, 'pass': True})

with TemporaryDirectory(prefix='save-delete-owner-') as temporary:
    os.environ['SQLITE_PATH'] = str(Path(temporary) / 'bootstrap.sqlite')
    from backend.app.main import create_app
    from backend.app.storage.sqlite import canonical
    db_path = Path(temporary) / 'narrow.sqlite'
    app = create_app(db_path, gameplay_version='v3.4')
    store = app.state.store
    schema = json.loads((ROOT / 'contracts/api.schema.json').read_text(encoding='utf-8'))
    validator = Draft202012Validator({'$ref': '#/$defs/delete_save_response', '$defs': schema['$defs']}, format_checker=FormatChecker())
    with TestClient(app, raise_server_exceptions=False) as client, patch('httpx.AsyncClient.send', side_effect=AssertionError('No paid/network calls in Owner verification')):
        session = client.post('/api/sessions', json={}).json()['data']
        other = client.post('/api/sessions', json={}).json()['data']
        headers = {'X-Session-Token': session['token']}
        base = '/api/sessions/' + session['session_id']
        def state():
            return client.get(base + '/state', headers=headers).json()['data']['visible_state']
        def version():
            s = state()
            return {'request_id': uuid4().hex, 'revision': s['revision'], 'generation': s['generation']}
        def archive():
            response = client.post(base + '/saves', json=version(), headers=headers)
            assert response.status_code == 201
            return response.json()['data']['slot']['save_id']
        def delete(save_id, request=None, expected=200, code=None, selected_base=base, selected_headers=headers):
            response = client.post(selected_base + '/saves/' + save_id + '/delete', json=request or version(), headers=selected_headers)
            payload = response.json()
            assert response.status_code == expected, (expected, payload.get('error'))
            if code:
                assert payload['error']['code'] == code, payload['error']
            if payload['ok']:
                assert not list(validator.iter_errors(payload))
                assert set(payload['data']) == {'request_id','replayed','save_id','message','visible_state'}
                assert session['token'] not in json.dumps(payload)
            return payload
        def rows(table):
            with closing(sqlite3.connect(db_path)) as db:
                return db.execute('SELECT * FROM ' + table + ' ORDER BY rowid').fetchall()
        first, second = archive(), archive()
        legacy_request = version()
        assert client.post(base + '/save', json=legacy_request, headers=headers).status_code == 200
        legacy_before = rows('saves')
        before = state()
        request = version()
        removed = delete(first, request)
        check('delete one archive preserves game state/revision/generation and legacy', state() == before and rows('saves') == legacy_before and {r[0] for r in rows('save_slots')} == {second})
        replay = delete(first, request)
        check('completed replay preserves event and does not repeat delete', replay['event_id'] == removed['event_id'] and replay['data']['replayed'])
        assert client.post(base + '/reset', json=version(), headers=headers).status_code == 200
        current = state()
        replay = delete(first, request)
        check('completed replay precedes generation and returns current state', replay['data']['visible_state'] == current and replay['data']['replayed'])
        delete(second, request, 409, 'REQUEST_ID_CONFLICT')
        response = client.post(base + '/saves/' + second + '/restore', json=request, headers=headers)
        check('same request id conflicts for changed slot or operation', response.status_code == 409 and response.json()['error']['code'] == 'REQUEST_ID_CONFLICT')
        before_slots = rows('save_slots')
        delete(second, expected=403, code='FORBIDDEN_SESSION', selected_headers={})
        delete(second, expected=403, code='FORBIDDEN_SESSION', selected_headers={'X-Session-Token':other['token']})
        other_version = {'request_id':uuid4().hex,'revision':other['visible_state']['revision'],'generation':other['visible_state']['generation']}
        delete(second, other_version, 404, 'SAVE_NOT_FOUND', selected_base='/api/sessions/'+other['session_id'], selected_headers={'X-Session-Token':other['token']})
        check('unauthenticated and foreign access leave archives unchanged', rows('save_slots') == before_slots)
        delete('legacy', expected=404, code='SAVE_NOT_FOUND')
        check('legacy reserved id cannot delete original single slot', rows('saves') == legacy_before)
        missing = version()
        failure = delete('missing', missing, 404, 'SAVE_NOT_FOUND')
        assert client.post(base + '/reset', json=version(), headers=headers).status_code == 200
        repeated_failure = delete('missing', missing, 404, 'SAVE_NOT_FOUND')
        check('missing-save error receipt replays before generation', failure['event_id'] == repeated_failure['event_id'])
        stale = {**version(), 'revision':state()['revision']+1}
        delete(second, stale, 409, 'STALE_STATE')
        delete(second, {**version(), 'generation':str(uuid4())}, 409, 'STALE_GENERATION')
        check('new request rejects wrong revision and generation', rows('save_slots') == before_slots)
        delete('bad.identifier', expected=422, code='BAD_ARGUMENT')
        delete(second, {**version(),'extra':True}, 422, 'BAD_ARGUMENT')
        delete(second, {**version(),'revision':True}, 422, 'BAD_ARGUMENT')
        invalid = client.post(base+'/saves/'+second+'/delete', content='not-json', headers=headers)
        check('strict ID/body/version and malformed JSON rejection', invalid.status_code == 422 and invalid.json()['error']['code'] == 'BAD_ARGUMENT')
        pending = version()
        digest = hashlib.sha256(canonical({'operation':'archive_delete', **pending, 'save_id':second}).encode()).hexdigest()
        with store.transaction() as db:
            db.execute("INSERT INTO action_receipts (session_id,request_id,request_hash,generation,response_json,http_status,phase) VALUES (?,?,?,?,?,0,'reserved')", (session['session_id'], pending['request_id'], digest, pending['generation'], '{}'))
        delete(second, pending, 503, 'MODEL_UNAVAILABLE')
        check('unfinished receipt fails closed', rows('save_slots') == before_slots)
        corrupt = archive()
        with store.transaction() as db:
            db.execute('UPDATE save_slots SET snapshot_json=?,metadata_json=? WHERE save_id=?', ('not-json', 'not-json', corrupt))
        before = state()
        delete(corrupt)
        check('corrupt snapshot and metadata removable without parsing or game mutation', state() == before and corrupt not in {r[0] for r in rows('save_slots')})
        rollback = version()
        before = rows('save_slots'), rows('events'), rows('action_receipts'), state()
        original_event = store.event
        def broken_event(*args, **kwargs):
            if args[3] == 'archive_delete' and args[4] == 'committed':
                raise RuntimeError('Owner deliberate post-delete event failure')
            return original_event(*args, **kwargs)
        with patch.object(store, 'event', side_effect=broken_event):
            delete(second, rollback, 500, 'INTERNAL_ERROR')
        check('event failure rolls back deletion/event/receipt/state', before == (rows('save_slots'), rows('events'), rows('action_receipts'), state()))
        receipt_failure = version()
        with store.transaction() as db:
            db.execute("CREATE TRIGGER owner_receipt_failure BEFORE INSERT ON action_receipts WHEN NEW.request_id='" + receipt_failure['request_id'] + "' BEGIN SELECT RAISE(ABORT,'Owner receipt failure'); END")
        before = rows('save_slots'), rows('events'), rows('action_receipts'), state()
        delete(second, receipt_failure, 500, 'INTERNAL_ERROR')
        check('receipt failure rolls back deletion/event/receipt/state', before == (rows('save_slots'), rows('events'), rows('action_receipts'), state()))
        with store.transaction() as db:
            db.execute('DROP TRIGGER owner_receipt_failure')
        delete(second, receipt_failure)
        check('rolled-back request can complete normally later', rows('save_slots') == [] and rows('saves') == legacy_before)
        keeper = archive()
        assert client.post(base + '/saves/' + keeper + '/restore', json=version(), headers=headers).status_code == 200
        assert client.post(base + '/restore', json=version(), headers=headers).status_code == 200
        check('archive create/selected restore and legacy restore stay operational', keeper in {r[0] for r in rows('save_slots')})

report = {'operator':'Backend Owner','scope':'narrow development verification only','exit_code':0,'checks':checks,'check_count':len(checks),'paid_calls':0,'databases':'temporary synthetic only; removed by TemporaryDirectory','limitations':['Not formal independent QA','No browser, full route or full backend suite run','Legacy metadata corruption unrelated to archive delete is unchanged']}
output = Path(__file__).with_name('owner-check.json')
output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'exit_code':0,'check_count':len(checks),'evidence':str(output),'paid_calls':0}))
