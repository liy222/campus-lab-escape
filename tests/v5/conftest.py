"""Private fixtures. Set isolation before importing main's module-level app."""
import copy
import hashlib
import json
import os
import re
import tempfile
import uuid
from pathlib import Path

_IMPORT_HOME = tempfile.TemporaryDirectory(prefix='campus-v5-qa-import-')
os.environ['SQLITE_PATH'] = str(Path(_IMPORT_HOME.name) / 'game-v5.sqlite')
os.environ['GAMEPLAY_VERSION'] = 'v5'
os.environ['AI_PROVIDER'] = 'mock'

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from fastapi.testclient import TestClient

BASE = 'http://127.0.0.1:8001'
PASSWORD = 'Synthetic-QA-only-Password!'
# Synthetic transport input, never a real credential. Do not echo actual cookies.
CANARY = 'QA-SYNTHETIC-CREDENTIAL-ONLY-9c584e'
_CONTRACT_ROOT=Path(__file__).resolve().parents[2]/'contracts'/'v2'

def validate_response(response,method=None,url=None):
    """Validate real HTTP bodies against the independently maintained contract."""
    schema=json.loads((_CONTRACT_ROOT/'api.schema.json').read_text(encoding='utf-8-sig'))
    body=response.json()
    if response.status_code>=400: definition='error_response'
    else:
        routes=json.loads((_CONTRACT_ROOT/'routes.json').read_text(encoding='utf-8-sig'))['routes']
        route=next((r for r in routes if r['method']==method and re.fullmatch(re.sub(r'\{[^}]+\}',r'[^/]+',r['path']),'/api/v2'+url)),None)
        assert route is not None, 'No V5 route contract for successful response'
        assert response.status_code in route['success_statuses'], (method,url,response.status_code)
        definition=route['response']
    validator=Draft202012Validator({'$defs':schema['$defs'],'$ref':'#/$defs/'+definition},format_checker=FormatChecker())
    errors=list(validator.iter_errors(body))
    assert not errors, '; '.join(f"{list(e.path)}: {e.message}" for e in errors[:3])

def rid(): return str(uuid.uuid4())

def make_fixture(*args,**kwargs):
    from backend.app.domain.generated import make_fixture as implementation
    return implementation(*args,**kwargs)

def compile_level(*args,**kwargs):
    from backend.app.domain.generated import compile_level as implementation
    return implementation(*args,**kwargs)

class FixtureGenerator:
    """Injected deterministic test generator; not real AI or paid evidence."""
    def __init__(self): self.calls = []; self.output = None; self.error = None
    async def generate(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        if self.error: raise self.error
        return copy.deepcopy(self.output if self.output is not None else make_fixture(kwargs['room_count'], kwargs['difficulty']))

class Actor:
    def __init__(self, app):
        self.client = TestClient(app, base_url=BASE, raise_server_exceptions=False)
        self.headers = {'Origin': BASE}
        self.auth = None
    def request(self, method, url, **kwargs):
        headers = {**self.headers, **kwargs.pop('headers', {})}
        response=self.client.request(method, '/api/v2' + url, headers=headers, **kwargs)
        validate_response(response,method,url)
        return response
    def get(self, url, **kwargs): return self.request('GET', url, **kwargs)
    def post(self, url, body=None, **kwargs): return self.request('POST', url, json={} if body is None else body, **kwargs)
    def authenticate(self, name, register=True):
        anon = self.get('/auth/csrf').json()['data']
        self.headers.update({'X-CSRF-Token': anon['csrf_token']})
        response = self.post('/auth/register' if register else '/auth/login', {'username': name, 'password': PASSWORD})
        assert response.status_code == (201 if register else 200), response.text
        self.auth = response.json()['data']
        self.headers.update({'X-CSRF-Token': self.auth['csrf_token'], 'X-Auth-Context': self.auth['auth_context']})
        return self
    def session(self, mode='classic', level_id=None):
        body = {'request_id':rid(), 'mode':mode}
        if level_id: body['level_id'] = level_id
        response = self.post('/sessions', body)
        assert response.status_code in (200, 201), response.text
        return response.json()['data']['visible_state']
    def state(self, sid):
        response = self.get(f'/sessions/{sid}/state')
        assert response.status_code == 200, response.text
        return response.json()['data']['visible_state']
    def versioned(self, state, **extra):
        return {'request_id':rid(), 'revision':state['revision'], 'generation':state['generation'], **extra}
    def action(self, state, tool, arguments, **extra):
        return self.post(f"/sessions/{state['session_id']}/actions", self.versioned(state, tool=tool, arguments=arguments, **extra))
    def generate(self, rooms=1, difficulty='easy', **updates):
        response = self.post('/level-generations', {'request_id':rid(), 'theme':'离线校园测试', 'room_count':rooms, 'difficulty':difficulty, **updates}, headers={'X-AI-Api-Key':CANARY})
        assert response.status_code == 202, response.text
        job = self.get('/level-generations/' + response.json()['data']['job']['job_id']).json()['data']['job']
        assert job['status'] == 'ready', job
        return job

@pytest.fixture
def system(tmp_path):
    from backend.app.main import create_v5_app
    generator = FixtureGenerator()
    app = create_v5_app(tmp_path / 'game-v5.sqlite', generation_service=generator)
    return app, generator

@pytest.fixture
def actor(system): return Actor(system[0]).authenticate('qa_alpha')

def assert_error(response, status, code=None):
    assert response.status_code == status, response.text
    value = response.json()
    assert value['ok'] is False and value['event_id']
    assert isinstance(value['error']['message'], str)
    if code: assert value['error']['code'] == code, value
    assert 'Traceback' not in response.text
    validate_response(response)

def replay(actor, state, compiled, actions=None):
    for action in compiled.witness if actions is None else actions:
        response = actor.action(state, action['tool'], action['arguments'])
        assert response.status_code == 200, (action['tool'], response.text)
        state = response.json()['data']['visible_state']
    return state

HASH_METHOD='SHA256 of UTF-8 JSON; sorted keys, ensure_ascii=False, separators=(comma,colon); exactly Store.rules.game_fields excluding revision/generation; no private values emitted'

def private_game_hash(db,sid,game_fields):
    with db.transaction() as c:
        state=json.loads(c.execute('SELECT state_json FROM sessions WHERE session_id=?',(sid,)).fetchone()[0])
    fields=set(game_fields)-{'revision','generation'}
    assert fields and fields<=set(state)
    encoded=json.dumps({key:state[key] for key in fields},sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()

def private_full_state_hash(db,sid):
    with db.transaction() as c:
        state=json.loads(c.execute('SELECT state_json FROM sessions WHERE session_id=?',(sid,)).fetchone()[0])
    return hashlib.sha256(json.dumps(state,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()

def observed_output(name,value):
    """Write only during an actual runner invocation, never prefill evidence."""
    directory=os.environ.get('V5_QA_OUTPUT')
    if not directory:return
    target=Path(directory).resolve()
    target.relative_to(Path(__file__).resolve().parents[2]/'evidence/upgrade/v5.0/qa')
    assert Path(name).name==name and name.endswith('.json')
    target.mkdir(parents=True,exist_ok=True)
    (target/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
