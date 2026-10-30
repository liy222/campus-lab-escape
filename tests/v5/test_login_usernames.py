"""Focused V5 local login-name projection checks; all accounts are synthetic."""
import json

from backend.app.api.v5 import router
from contracts.v2.build_contracts import build as build_contracts
from tests.v5.conftest import Actor, assert_error, rid


def _register(app, username, password):
    actor = Actor(app)
    anonymous = actor.get('/auth/csrf').json()['data']
    actor.headers['X-CSRF-Token'] = anonymous['csrf_token']
    response = actor.post('/auth/register', {'username': username, 'password': password})
    assert response.status_code == 201
    data = response.json()['data']
    actor.auth = data
    actor.headers.update({'X-CSRF-Token': data['csrf_token'], 'X-Auth-Context': data['auth_context']})
    return actor, response


def _login(app, username, password):
    actor = Actor(app)
    anonymous = actor.get('/auth/csrf').json()['data']
    actor.headers['X-CSRF-Token'] = anonymous['csrf_token']
    response = actor.post('/auth/login', {'username': username, 'password': password})
    if response.status_code == 200:
        data = response.json()['data']
        actor.auth = data
        actor.headers.update({'X-CSRF-Token': data['csrf_token'], 'X-Auth-Context': data['auth_context']})
    return actor, response


def test_anonymous_csrf_lists_only_sorted_names_and_authenticated_shape_is_unchanged(system):
    app, _ = system
    empty = Actor(app).get('/auth/csrf').json()['data']
    assert set(empty) == {'csrf_token', 'auth_context', 'user', 'usernames'}
    assert empty['user'] is None and empty['auth_context'] is None and empty['usernames'] == []

    alpha_password = 'Synthetic-Login-Alpha!'
    zulu_password = 'Synthetic-Login-Zulu!'
    alpha, alpha_register = _register(app, 'Alpha_Local', alpha_password)
    zulu, zulu_register = _register(app, 'Zulu_Local', zulu_password)
    assert alpha_register.json()['data']['user']['username'] == 'alpha_local'
    assert zulu_register.json()['data']['user']['username'] == 'zulu_local'
    assert 'usernames' not in alpha_register.json()['data']
    assert 'usernames' not in zulu_register.json()['data']

    anonymous = Actor(app).get('/auth/csrf').json()['data']
    assert anonymous['usernames'] == ['alpha_local', 'zulu_local']
    assert all(type(name) is str for name in anonymous['usernames'])
    assert set(anonymous) == {'csrf_token', 'auth_context', 'user', 'usernames'}
    rendered = json.dumps(anonymous, ensure_ascii=False)
    for forbidden in ('user_id', 'password', 'password_hash', alpha_password, zulu_password):
        assert forbidden not in rendered

    authenticated_csrf = alpha.get('/auth/csrf').json()['data']
    assert set(authenticated_csrf) == {'csrf_token', 'auth_context', 'user'}
    assert authenticated_csrf['user']['username'] == 'alpha_local'
    assert 'usernames' not in authenticated_csrf


def test_distinct_passwords_wrong_password_has_no_identity_and_cross_owner_is_hidden(system):
    app, _ = system
    alpha_password = 'Synthetic-Login-Alpha!'
    zulu_password = 'Synthetic-Login-Zulu!'
    _register(app, 'Alpha_Local', alpha_password)
    _register(app, 'Zulu_Local', zulu_password)

    wrong, failed = _login(app, 'alpha_local', 'Synthetic-Wrong-Password!')
    assert_error(failed, 401, 'INVALID_CREDENTIALS')
    assert_error(wrong.get('/auth/me'), 401, 'AUTH_REQUIRED')
    assert wrong.get('/auth/csrf').json()['data']['usernames'] == ['alpha_local', 'zulu_local']

    alpha, alpha_login = _login(app, 'alpha_local', alpha_password)
    zulu, zulu_login = _login(app, 'zulu_local', zulu_password)
    assert alpha_login.status_code == zulu_login.status_code == 200
    assert alpha_login.json()['data']['user']['username'] == 'alpha_local'
    assert zulu_login.json()['data']['user']['username'] == 'zulu_local'
    assert 'usernames' not in alpha_login.json()['data']
    assert 'usernames' not in zulu_login.json()['data']

    created = alpha.post('/sessions', {'request_id': rid(), 'mode': 'classic'})
    assert created.status_code in (200, 201)
    sid = created.json()['data']['session_id']
    assert_error(zulu.get(f'/sessions/{sid}/state'), 404, 'NOT_FOUND')


def test_auth_contract_artifact_and_twenty_route_surface_are_aligned():
    built = build_contracts()
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    on_disk = json.loads((root / 'contracts/v2/api.schema.json').read_text(encoding='utf-8'))
    routes_file = json.loads((root / 'contracts/v2/routes.json').read_text(encoding='utf-8'))
    assert built['api.schema.json'] == on_disk
    auth = on_disk['$defs']['auth_data']
    assert 'usernames' in auth['properties']
    assert 'usernames' not in auth['required']
    assert auth['properties']['usernames'] == {
        'type': 'array', 'items': {'type': 'string', 'minLength': 3, 'maxLength': 24,
                                    'pattern': '^[a-z0-9_]+$'}}
    routes = routes_file['routes']
    actual = {(method, route.path) for route in router.routes for method in route.methods
              if method in {'GET', 'POST', 'PUT', 'DELETE', 'PATCH'}}
    declared = {(route['method'], route['path']) for route in routes}
    assert len(routes) == 20
    assert actual == declared
