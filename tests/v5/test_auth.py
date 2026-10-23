"""N06/P01: authentication, rotation, expiry, hashing and limits."""
import time
import pytest
from .conftest import Actor, PASSWORD, BASE, assert_error
from backend.app.storage.v5 import digest, PASSWORD_HASHER, HASH_SLOTS

def test_register_normalizes_and_hashes_with_salt(system):
    app, _ = system
    a = Actor(app).authenticate('QA_Alpha')
    b = Actor(app).authenticate('qa_beta')
    assert a.auth['user']['username'] == 'qa_alpha'
    with app.state.v5_database.transaction() as c:
        rows = c.execute('SELECT password_hash FROM users ORDER BY username').fetchall()
        auth = c.execute('SELECT token_hash,csrf_hash FROM auth_sessions').fetchall()
    assert len(rows) == 2 and rows[0][0] != rows[1][0]
    for row in rows:
        assert row[0].startswith('$argon2id$v=19$m=19456,t=2,p=1$')
        assert PASSWORD_HASHER.verify(row[0], PASSWORD)
    for row in auth:
        assert len(row[0]) == len(row[1]) == 64
        assert row[0] not in a.client.cookies.values()
    headers = a.get('/auth/csrf').json()['data']
    assert headers['csrf_token'] == a.auth['csrf_token']
    assert a.get('/auth/csrf').json()['data'] == headers
    response = a.post('/auth/register', {'username':'qa_ALPHA','password':PASSWORD})
    assert_error(response,409,'USERNAME_UNAVAILABLE')

def test_same_owner_rotation_revokes_actual_old_cookie_and_logout(actor, system):
    app,_=system
    old=actor.client.cookies.get('campus_v5_session')
    old_context=dict(actor.headers)
    result=actor.post('/auth/login', {'username':'QA_ALPHA','password':PASSWORD})
    assert result.status_code==200
    data=result.json()['data']; assert data['auth_context']!=actor.auth['auth_context']
    actor.headers.update({'X-CSRF-Token':data['csrf_token'],'X-Auth-Context':data['auth_context']})
    other=Actor(app); other.client.cookies.set('campus_v5_session',old,path='/api/v2')
    assert_error(other.get('/auth/me'),401,'AUTH_REQUIRED')
    assert_error(actor.post('/sessions',{'request_id':'rotation-stale','mode':'classic'},headers=old_context),403,'CSRF_FAILED')
    assert actor.post('/auth/logout').status_code==200
    assert_error(actor.get('/auth/me'),401,'AUTH_REQUIRED')
    cookie=result.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'samesite=strict' in cookie and 'path=/api/v2' in cookie
    assert 'domain=' not in cookie

@pytest.mark.parametrize('field,age',[('last_seen',1801),('created_at',28801)])
def test_expired_sessions_refused(actor, system, field, age):
    with system[0].state.v5_database.transaction() as c:
        c.execute(f'UPDATE auth_sessions SET {field}=?',(time.time()-age,))
    assert_error(actor.get('/auth/me'),401,'AUTH_REQUIRED')

def test_wrong_password_rate_and_cooldown(system):
    app,_=system; a=Actor(app).authenticate('qa_alpha')
    assert a.post('/auth/logout').status_code==200
    a.headers.pop('X-Auth-Context'); a.headers['X-CSRF-Token']=a.get('/auth/csrf').json()['data']['csrf_token']
    for _ in range(5): assert_error(a.post('/auth/login',{'username':'qa_alpha','password':'Synthetic-wrong-password'}),401,'INVALID_CREDENTIALS')
    assert_error(a.post('/auth/login',{'username':'qa_alpha','password':PASSWORD}),429,'AUTH_LIMIT_REACHED')
    with app.state.v5_database.transaction() as c: c.execute('UPDATE auth_limits SET at=?',(time.time()-61,))
    assert a.post('/auth/login',{'username':'qa_alpha','password':PASSWORD}).status_code==200

def test_source_registration_hash_limits(system):
    db=system[0].state.v5_database
    for _ in range(30): db.rate_record('source',digest('testclient'))
    a=Actor(system[0]); a.headers['X-CSRF-Token']=a.get('/auth/csrf').json()['data']['csrf_token']
    assert_error(a.post('/auth/register',{'username':'qa_new','password':PASSWORD}),429)
    with db.transaction() as c: c.execute('DELETE FROM auth_limits')
    for _ in range(10): db.rate_record('register',digest('testclient'))
    assert_error(a.post('/auth/register',{'username':'qa_new','password':PASSWORD}),429)
    with db.transaction() as c: c.execute('DELETE FROM auth_limits')
    HASH_SLOTS.acquire(); HASH_SLOTS.acquire()
    try: assert_error(a.post('/auth/register',{'username':'qa_new','password':PASSWORD}),429)
    finally: HASH_SLOTS.release(); HASH_SLOTS.release()

@pytest.mark.parametrize('name,password',[('a',PASSWORD),('中文用户',PASSWORD),('qa_abc','short'),('qa_abc','x'*129)])
def test_credentials_strict(system,name,password):
    a=Actor(system[0]); a.headers['X-CSRF-Token']=a.get('/auth/csrf').json()['data']['csrf_token']
    assert_error(a.post('/auth/register',{'username':name,'password':password}),422,'BAD_ARGUMENT')

def test_anonymous_csrf_expiry_missing_and_duplicates(system):
    app,_=system; a=Actor(app)
    assert_error(a.post('/auth/register',{'username':'qa_anon','password':PASSWORD}),403,'CSRF_FAILED')
    token=a.get('/auth/csrf').json()['data']['csrf_token']
    headers=[('Origin',BASE),('Content-Type','application/json'),('X-CSRF-Token',token),('X-CSRF-Token','duplicate')]
    response=a.client.post('/api/v2/auth/register',headers=headers,json={'username':'qa_anon','password':PASSWORD})
    assert_error(response,403,'CSRF_FAILED')
    with app.state.v5_database.transaction() as c: c.execute('UPDATE anonymous_csrf SET created_at=?',(time.time()-601,))
    a.headers['X-CSRF-Token']=token
    assert_error(a.post('/auth/register',{'username':'qa_anon','password':PASSWORD}),403,'CSRF_FAILED')
