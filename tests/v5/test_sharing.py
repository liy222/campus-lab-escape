"""Independent sharing/ranking QA. Synthetic/TEMP only; Main GO before execution."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest
from .conftest import Actor, CANARY, FixtureGenerator, compile_level, make_fixture, rid


class SyntheticCompanion:
    def __init__(self): self.calls = 0; self.mode = 'success'
    async def turn(self, **kwargs):
        self.calls += 1
        if self.mode == 'timeout': raise TimeoutError('Synthetic controlled timeout')
        if self.mode == 'local': return {'answer': '可以先查看眼前物件。', 'clue_refs': [], 'count_hint': False, 'usage': {'model_calls': 0}}
        if self.mode == 'invalid': return {'answer': '<script>synthetic</script>', 'clue_refs': []}
        return {'answer': '可以先查看眼前物件。', 'clue_refs': [], 'count_hint': True,
                'status': 'completed', 'stop_reason': None,
                'usage': {'provider': 'deepseek', 'model': 'deepseek-flash', 'model_calls': 1,
                          'input_tokens': 1, 'output_tokens': 1, 'read_tool_calls': 0}}


def observe(case, expected, actual):
    directory = os.environ.get('SHARING_QA_OUTPUT')
    if not directory: return
    target = Path(directory).resolve()
    target.relative_to((Path(__file__).resolve().parents[2] / 'evidence/project/stages/v5-sharing-leaderboard/automated').resolve())
    target.mkdir(parents=True, exist_ok=True)
    with (target / 'observations.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({'case': case, 'expected': expected, 'actual': actual}, ensure_ascii=False) + '\n')


@pytest.fixture(scope='module')
def compiled():
    return compile_level(make_fixture(1, 'easy'), 1, 'easy')


@pytest.fixture
def world(tmp_path, monkeypatch, compiled):
    from backend.app.main import create_v5_app
    from backend.app.storage import sharing
    clock = SimpleNamespace(ms=1800000000000)
    monkeypatch.setattr(sharing, 'now_ms', lambda: clock.ms)
    generator = FixtureGenerator(); generator.output = compiled.draft.model_dump()
    companion = SyntheticCompanion()
    app = create_v5_app(tmp_path / 'game-v5.sqlite', generation_service=generator, companion_service=companion)
    a = Actor(app).authenticate('sharing_author')
    b = Actor(app).authenticate('sharing_beta')
    c = Actor(app).authenticate('sharing_gamma')
    job = a.generate(1, 'easy')
    yield SimpleNamespace(app=app, a=a, b=b, c=c, lid=job['level_id'], clock=clock,
                          compiled=compiled, generator=generator, companion=companion, path=tmp_path / 'game-v5.sqlite')
    for actor in (a, b, c): actor.client.close()


def publication(actor, lid, published=True, revision=0):
    response = actor.post(f'/levels/{lid}/sharing', {'published': published, 'revision': revision})
    assert response.status_code == 200
    return response.json()['data']['sharing']


def join(actor, share_id, request_id=None, expected=None):
    response = actor.post(f'/shared-levels/{share_id}/sessions', {'request_id': request_id or rid()})
    assert response.status_code in ((expected,) if expected is not None else (200, 201))
    assert response.json()['data']['share_id'] == share_id
    state = response.json()['data']['visible_state']
    assert state['share_id'] == share_id and state['mode'] == 'generated'
    return state


def board(actor, share_id):
    response = actor.get(f'/shared-levels/{share_id}/leaderboard')
    assert response.status_code == 200
    return response.json()['data']


def action(actor, state, entry):
    response = actor.action(state, entry['tool'], entry['arguments'])
    assert response.status_code == 200
    return response.json()['data']['visible_state']


def finish(actor, state, compiled, actions=None):
    for entry in compiled.witness if actions is None else actions:
        state = action(actor, state, entry)
    assert state['status'] == 'won' and state['challenge']['status'] == 'finished'
    return state


def reset(actor, state):
    response = actor.post(f"/sessions/{state['session_id']}/reset", actor.versioned(state))
    assert response.status_code == 200
    return response.json()['data']['visible_state']


def save(actor, state, kind='archive'):
    if kind == 'legacy':
        db = actor.client.app.state.v5_database
        principal = db.authenticate(actor.client.cookies.get('campus_v5_session'))
        status, body = db.owned(principal, state['session_id']).control(state['session_id'], None, 'save', actor.versioned(state))
        assert status == 200
        return 'legacy', body['data']['visible_state']
    response = actor.post(f"/sessions/{state['session_id']}/saves", actor.versioned(state, name='Synthetic checkpoint'))
    assert response.status_code == 201
    return response.json()['data']['slot']['save_id'], response.json()['data']['visible_state']


def restore(actor, state, save_id):
    response = actor.post(f"/sessions/{state['session_id']}/saves/{save_id}/restore", actor.versioned(state))
    assert response.status_code == 200
    return response.json()['data']['visible_state']


def test_publication_fixed_definition_cancel_republish_and_join_reuse(world):
    w = world
    original = w.a.get(f'/levels/{w.lid}').json()['data']['level']
    assert original['sharing'] == {'share_id': None, 'published': False, 'revision': 0, 'published_at': None}
    shared = publication(w.a, w.lid); sid = shared['share_id']
    assert shared['published'] and shared['revision'] == 1
    assert w.b.post(f'/levels/{w.lid}/sharing', {'published': False, 'revision': 1}).status_code == 404
    stale = w.a.post(f'/levels/{w.lid}/sharing', {'published': False, 'revision': 0})
    assert stale.status_code == 409 and stale.json()['error']['code'] == 'STALE_SHARING'
    detail = w.b.get(f'/shared-levels/{sid}').json()['data']['shared_level']
    for key in ('level_id', 'title', 'story', 'theme', 'room_count', 'difficulty', 'created_at', 'definition_hash'):
        assert detail[key] == original[key]
    assert detail['author_username'] == 'sharing_author' and detail['is_author'] is False
    request_id = rid(); first = join(w.b, sid, request_id, 201); repeated = join(w.b, sid, request_id, 200)
    reused = join(w.b, sid, expected=200)
    assert first['session_id'] == repeated['session_id'] == reused['session_id']
    assert first['challenge']['attempt_id'] == repeated['challenge']['attempt_id'] == reused['challenge']['attempt_id']
    canceled = publication(w.a, w.lid, False, 1)
    assert canceled['share_id'] == sid and canceled['revision'] == 2
    assert w.c.get(f'/shared-levels/{sid}').status_code == 404
    assert w.c.get(f'/shared-levels/{sid}/leaderboard').status_code == 404
    assert w.c.post(f'/shared-levels/{sid}/sessions', {'request_id': rid()}).status_code == 404
    assert w.c.get('/shared-levels', params={'view': 'hall', 'page': 1}).json()['data']['total'] == 0
    joined = w.b.get('/shared-levels', params={'view': 'joined', 'page': 1}).json()['data']['shared_levels']
    assert len(joined) == 1 and joined[0]['published'] is False
    assert join(w.b, sid, expected=200)['session_id'] == first['session_id']
    again = publication(w.a, w.lid, True, 2)
    assert again['share_id'] == sid and again['published_at'] == shared['published_at']
    assert len(w.generator.calls) == 1
    observe('fixed-definition-cancel', {'new_generator_calls_after_sharing': 0, 'new_join_after_cancel': 404}, {'generator_calls_total': len(w.generator.calls), 'share_id_preserved': again['share_id'] == sid})


def test_three_owners_private_resources_and_progress_are_isolated(world):
    w = world; share = publication(w.a, w.lid)['share_id']
    author_private = w.a.session('generated', w.lid)
    states = [join(x, share) for x in (w.a, w.b, w.c)]
    assert len({s['session_id'] for s in states} | {author_private['session_id']}) == 4
    assert len({s['definition_hash'] for s in states + [author_private]}) == 1
    assert states[0]['challenge']['is_author'] and not states[1]['challenge']['is_author']
    progressed = action(w.b, states[1], w.compiled.witness[0]); save_id, progressed = save(w.b, progressed)
    for other in (w.a, w.c):
        assert other.get(f"/sessions/{progressed['session_id']}/state").status_code == 404
        assert other.get(f"/sessions/{progressed['session_id']}/saves").status_code == 404
        assert other.post(f"/sessions/{progressed['session_id']}/saves/{save_id}/restore", other.versioned(progressed)).status_code == 404
        assert other.action(progressed, 'inspect', {'object_id': 'obj_source'}).status_code == 404
    assert w.b.get(f'/levels/{w.lid}').status_code == 404
    assert w.b.post('/sessions', {'request_id': rid(), 'mode': 'generated', 'level_id': w.lid}).status_code == 404
    assert w.b.post('/sessions', {'request_id': rid(), 'mode': 'shared', 'level_id': w.lid}).status_code == 422
    assert w.a.state(states[0]['session_id'])['clues'] == []
    assert w.c.state(states[2]['session_id'])['clues'] == []
    assert w.a.state(author_private['session_id'])['clues'] == []
    run = next(x for x in w.b.get('/sessions').json()['data']['sessions'] if x['session_id'] == progressed['session_id'])
    assert run['share_id'] == share and run['mode'] == 'generated'


def test_continuous_clock_reopen_and_duplicate_final_action_only_one_score(world):
    from backend.app.main import create_v5_app
    w = world; share = publication(w.a, w.lid)['share_id']; state = join(w.b, share)
    started = state['challenge']['started_at']; attempt = state['challenge']['attempt_id']
    state = finish_until_last(w.b, state, w.compiled)
    w.clock.ms += 123456
    reopened = create_v5_app(w.path, generation_service=w.generator, companion_service=w.companion)
    owner = Actor(reopened).authenticate('sharing_beta', False)
    try:
        state = owner.state(state['session_id'])
        assert state['challenge']['attempt_id'] == attempt and state['challenge']['started_at'] == started
        assert board(owner, share)['entries'] == []
        final = w.compiled.witness[-1]
        request = owner.versioned(state, tool=final['tool'], arguments=final['arguments'])
        first = owner.post(f"/sessions/{state['session_id']}/actions", request); assert first.status_code == 200
        won = first.json()['data']['visible_state']
        assert won['challenge']['elapsed_ms'] == 123456
        repeated = owner.post(f"/sessions/{state['session_id']}/actions", request)
        assert repeated.status_code == 200 and repeated.json()['data']['replayed'] is True
        w.clock.ms += 10000
        own = board(owner, share)['own_entry']
        assert own['attempt_id'] == attempt and own['elapsed_ms'] == 123456
        assert board(owner, share)['total_players'] == 1
        assert owner.state(state['session_id'])['challenge']['elapsed_ms'] == 123456
        observe('continuous-time-reopen-replay', {'elapsed_ms': 123456, 'scores': 1}, {'elapsed_ms': own['elapsed_ms'], 'scores': len(board(owner, share)['entries'])})
    finally: owner.client.close()


def finish_until_last(actor, state, compiled):
    for entry in compiled.witness[:-1]: state = action(actor, state, entry)
    assert state['status'] == 'playing'
    return state


@pytest.mark.parametrize('kind', ['archive', 'legacy'])
def test_same_round_restore_keeps_clock_assists_and_cross_round_becomes_practice(world, kind):
    w = world; share = publication(w.a, w.lid)['share_id']; state = join(w.b, share)
    attempt = state['challenge']['attempt_id']; started = state['challenge']['started_at']
    save_id, state = save(w.b, state, kind)
    body = w.b.versioned(state, message='公开方向', hint_level=1)
    response = w.b.post(f"/sessions/{state['session_id']}/ai/turns", body)
    assert response.status_code == 200
    state = response.json()['data']['visible_state']; assert state['challenge']['hint_count'] == 1
    w.clock.ms += 8000; state = restore(w.b, state, save_id)
    assert state['challenge']['status'] == 'active' and state['challenge']['attempt_id'] == attempt
    assert state['challenge']['started_at'] == started and state['challenge']['hint_count'] == 1
    state = finish(w.b, state, w.compiled)
    own_before = board(w.b, share)['own_entry']; assert own_before['elapsed_ms'] == 8000 and own_before['hint_count'] == 1
    state = restore(w.b, state, save_id)
    assert state['challenge']['status'] == 'practice' and board(w.b, share)['own_entry'] == own_before
    state = finish_practice(w.b, state, w.compiled)
    assert board(w.b, share)['own_entry'] == own_before
    state = reset(w.b, state)
    assert state['challenge']['status'] == 'active' and state['challenge']['attempt_id'] != attempt
    active = state['challenge']['attempt_id']; state = restore(w.b, state, save_id)
    assert state['challenge']['status'] == 'practice' and state['challenge']['attempt_id'] == active
    assert board(w.b, share)['own_entry'] == own_before


def finish_practice(actor, state, compiled):
    for entry in compiled.witness: state = action(actor, state, entry)
    assert state['status'] == 'won' and state['challenge']['status'] == 'practice'
    return state


def test_bad_archive_failure_keeps_eligibility_won_restore_never_scores(world):
    w = world; share = publication(w.a, w.lid)['share_id']; state = join(w.b, share)
    bad_id, state = save(w.b, state)
    db = w.app.state.v5_database
    with db.transaction() as c:
        c.execute('UPDATE save_slots SET snapshot_json=? WHERE save_id=?', ('{"broken":true}', bad_id))
    before = copy.deepcopy(state['challenge'])
    response = w.b.post(f"/sessions/{state['session_id']}/saves/{bad_id}/restore", w.b.versioned(state))
    assert response.status_code == 409 and w.b.state(state['session_id'])['challenge'] == before
    w.clock.ms += 5000; state = finish(w.b, state, w.compiled)
    won_id, state = save(w.b, state); entry = board(w.b, share)['own_entry']
    state = reset(w.b, state); state = restore(w.b, state, won_id)
    assert state['status'] == 'won' and state['challenge']['status'] == 'practice'
    assert board(w.b, share)['own_entry'] == entry


def test_final_action_rolls_back_state_attempt_receipt_and_score_together(world, monkeypatch):
    from backend.app.storage.v5 import BoundStore
    w = world; share = publication(w.a, w.lid)['share_id']; state = join(w.b, share)
    state = finish_until_last(w.b, state, w.compiled)
    final = w.compiled.witness[-1]; request = w.b.versioned(state, tool=final['tool'], arguments=final['arguments'])
    original = BoundStore.after_mutation
    def explode(self, c, sid, operation, before, after, save_id=None):
        original(self, c, sid, operation, before, after, save_id=save_id)
        if operation == 'action' and after.status == 'won': raise sqlite3.OperationalError('Synthetic transaction rollback')
    with monkeypatch.context() as patch:
        patch.setattr(BoundStore, 'after_mutation', explode)
        failed = w.b.post(f"/sessions/{state['session_id']}/actions", request)
        assert failed.status_code == 500
    assert w.b.state(state['session_id']) == state and board(w.b, share)['entries'] == []
    with w.app.state.v5_database.transaction() as c:
        assert c.execute('SELECT COUNT(*) FROM action_receipts WHERE session_id=? AND request_id=?', (state['session_id'], request['request_id'])).fetchone()[0] == 0
    response = w.b.post(f"/sessions/{state['session_id']}/actions", request)
    assert response.status_code == 200 and len(board(w.b, share)['entries']) == 1


def test_best_per_account_author_flag_and_tied_times_have_stable_order(world):
    w = world; share = publication(w.a, w.lid)['share_id']
    states = [join(x, share) for x in (w.a, w.b, w.c)]
    w.clock.ms += 10000
    for actor, state in zip((w.c, w.a, w.b), (states[2], states[0], states[1])): finish(actor, state, w.compiled)
    initial = board(w.a, share)
    assert initial['total_players'] == 3 and len(initial['entries']) == 3
    assert [x['rank'] for x in initial['entries']] == [1, 2, 3]
    assert all(x['elapsed_ms'] == 10000 for x in initial['entries'])
    assert [x['attempt_id'] for x in initial['entries']] == sorted(x['attempt_id'] for x in initial['entries'])
    assert next(x for x in initial['entries'] if x['username'] == 'sharing_author')['is_author'] is True
    state = reset(w.a, w.a.state(states[0]['session_id'])); w.clock.ms += 5000; state = finish(w.a, state, w.compiled)
    best = board(w.a, share); assert best['own_entry']['elapsed_ms'] == 5000 and best['own_entry']['rank'] == 1
    state = reset(w.a, state); w.clock.ms += 20000; finish(w.a, state, w.compiled)
    after = board(w.a, share)
    assert after['own_entry'] == best['own_entry'] and after['total_players'] == 3
    publication(w.a, w.lid, False, 1)
    assert board(w.b, share)['entries'] == after['entries']
    publication(w.a, w.lid, True, 2)
    assert board(w.a, share)['entries'] == after['entries']


def test_assists_count_only_success_not_failure_unknown_or_replay(world):
    w = world; share = publication(w.a, w.lid)['share_id']; state = join(w.b, share)
    sid = state['session_id']
    hint_request = w.b.versioned(state, message='免费方向', hint_level=1)
    response = w.b.post(f'/sessions/{sid}/ai/turns', hint_request); assert response.status_code == 200
    state = response.json()['data']['visible_state']
    replayed = w.b.post(f'/sessions/{sid}/ai/turns', hint_request); assert replayed.status_code == 200
    assert replayed.json()['data']['turn_id'] == response.json()['data']['turn_id']
    assert w.b.state(sid)['challenge']['hint_count'] == 1
    headers = {'X-AI-Provider': 'deepseek', 'X-AI-Api-Key': CANARY}
    good_request = w.b.versioned(state, message='下一步该查看什么？', hint_level=1)
    response = w.b.post(f'/sessions/{sid}/ai/turns', good_request, headers=headers); assert response.status_code == 200
    state = response.json()['data']['visible_state']; assert state['challenge']['companion_count'] == 1
    assert w.b.post(f'/sessions/{sid}/ai/turns', good_request, headers=headers).status_code == 200
    assert w.companion.calls == 2
    w.companion.mode = 'local'
    local = w.b.post(f'/sessions/{sid}/ai/turns', w.b.versioned(state, message='下一步该查看什么？', hint_level=1), headers=headers)
    assert local.status_code == 200 and w.b.state(sid)['challenge'] == state['challenge']
    for mode in ('invalid', 'timeout'):
        w.companion.mode = mode
        failed_request = w.b.versioned(state, message='下一步该查看什么？', hint_level=1)
        response = w.b.post(f'/sessions/{sid}/ai/turns', failed_request, headers=headers)
        assert response.status_code == (504 if mode == 'timeout' else 502)
        calls = w.companion.calls
        assert w.b.post(f'/sessions/{sid}/ai/turns', failed_request, headers=headers).status_code == (503 if mode == 'timeout' else 502)
        assert w.companion.calls == calls
        assert w.b.state(sid)['challenge'] == state['challenge']
    assert w.companion.calls == 5
    won = finish(w.b, state, w.compiled); best = board(w.b, share)['own_entry']
    assert best['hint_count'] == 1 and best['companion_count'] == 1
    observe('assistance-counters', {'hint_count': 1, 'companion_count': 1, 'real_model_calls': 0}, {'hint_count': best['hint_count'], 'companion_count': best['companion_count'], 'synthetic_companion_invocations': w.companion.calls})


def test_new_routes_keep_authentication_csrf_and_identity_context(world):
    w = world; anon = Actor(w.app)
    try:
        for path in ['/shared-levels?view=hall&page=1', '/shared-levels?view=joined&page=1', '/shared-levels/missing', '/shared-levels/missing/leaderboard']:
            assert anon.get(path).status_code == 401
        assert anon.post(f'/levels/{w.lid}/sharing', {'published': True, 'revision': 0}).status_code == 401
        assert w.a.post(f'/levels/{w.lid}/sharing', {'published': True, 'revision': 0}, headers={'X-CSRF-Token': 'Synthetic-wrong'}).status_code == 403
        assert w.a.get(f'/levels/{w.lid}').json()['data']['level']['sharing']['published'] is False
        share = publication(w.a, w.lid)['share_id']
        for bad_header in ({'X-CSRF-Token': 'Synthetic-wrong'}, {'X-Auth-Context': 'Synthetic-wrong'}):
            assert w.b.post(f'/shared-levels/{share}/sessions', {'request_id': rid()}, headers=bad_header).status_code == 403
        assert w.b.get('/shared-levels', params={'view': 'joined', 'page': 1}).json()['data']['total'] == 0
        for query in ['view=invalid&page=1', 'view=hall&page=0']:
            assert w.b.get('/shared-levels', params=dict(part.split('=', 1) for part in query.split('&'))).status_code in (400, 422)
    finally: anon.client.close()


def test_existing_v5_backup_and_migration_are_idempotent_preserve_old_json(tmp_path):
    from backend.app.main import create_v5_app
    path = tmp_path / 'old-v5.sqlite'; generator = FixtureGenerator()
    app = create_v5_app(path, generation_service=generator)
    assert not list((tmp_path / 'backups').glob('*.sqlite'))
    actor = Actor(app).authenticate('migration_owner')
    job = actor.generate(1, 'easy'); private = actor.session('generated', job['level_id'])
    classic = actor.session('classic'); archive_id, private = save(actor, private)
    legacy_id, classic = save(actor, classic, 'legacy')
    actor.client.close()
    with sqlite3.connect(path) as c:
        c.execute('PRAGMA foreign_keys=OFF')
        for table in ('shared_save_origins', 'challenge_attempts', 'shared_sessions', 'shared_levels'):
            c.execute('DROP TABLE ' + table)
        c.execute("DELETE FROM v5_metadata WHERE key='sharing_schema_version'")
        original_def = c.execute('SELECT definition_json FROM generated_levels WHERE level_id=?', (job['level_id'],)).fetchone()[0]
        original_state = c.execute('SELECT session_id,state_json FROM sessions ORDER BY session_id').fetchall()
        original_archive = c.execute('SELECT snapshot_json FROM save_slots WHERE save_id=?', (archive_id,)).fetchone()[0]
        original_legacy = c.execute('SELECT snapshot_json FROM saves WHERE session_id=?', (classic['session_id'],)).fetchone()[0]
    reopened = create_v5_app(path, generation_service=generator)
    backups = list((tmp_path / 'backups').glob('old-v5-sharing-v1-*.sqlite'))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as c:
        assert c.execute("SELECT value FROM v5_metadata WHERE key='sharing_schema_version'").fetchone() is None
        assert c.execute('SELECT session_id,state_json FROM sessions ORDER BY session_id').fetchall() == original_state
        assert c.execute('SELECT definition_json FROM generated_levels WHERE level_id=?', (job['level_id'],)).fetchone()[0] == original_def
    for index, current_app in enumerate((reopened, create_v5_app(path, generation_service=generator))):
        db = current_app.state.v5_database
        with db.transaction() as c:
            assert c.execute("SELECT value FROM v5_metadata WHERE key='database_version'").fetchone()[0] == '5'
            assert c.execute("SELECT value FROM v5_metadata WHERE key='sharing_schema_version'").fetchone()[0] == '1'
            if index == 0: assert [tuple(row) for row in c.execute('SELECT session_id,state_json FROM sessions ORDER BY session_id')] == original_state
            assert c.execute('SELECT definition_json FROM generated_levels WHERE level_id=?', (job['level_id'],)).fetchone()[0] == original_def
            assert c.execute('SELECT snapshot_json FROM save_slots WHERE save_id=?', (archive_id,)).fetchone()[0] == original_archive
            assert c.execute('SELECT snapshot_json FROM saves WHERE session_id=?', (classic['session_id'],)).fetchone()[0] == original_legacy
        user = Actor(current_app).authenticate('migration_owner', False)
        try:
            assert 'share_id' not in user.state(private['session_id']) and 'challenge' not in user.state(private['session_id'])
            restored = restore(user, user.state(private['session_id']), archive_id)
            assert restored['definition_hash'] == private['definition_hash']
            restored_classic = restore(user, user.state(classic['session_id']), legacy_id)
            assert restored_classic['mode'] == 'classic' and 'challenge' not in restored_classic
        finally: user.client.close()
    assert len(list((tmp_path / 'backups').glob('*.sqlite'))) == 1
    observe('migration-backup', {'consistent_backup_count': 1, 'old_definition_unchanged': True, 'schema_version': '5'}, {'consistent_backup_count': len(backups), 'old_definition_unchanged': True, 'schema_version': '5'})


def test_top50_keeps_own_best_and_full_rank_outside_visible_window(world):
    """Query fixture only: clone one valid completion into 51 synthetic rows.

    Does not claim 51 additional HTTP routes or human completions.
    """
    import uuid
    w = world; share = publication(w.a, w.lid)['share_id']; state = join(w.b, share)
    w.clock.ms += 90000; state = finish(w.b, state, w.compiled)
    db = w.app.state.v5_database
    with db.transaction() as c:
        attempt = dict(c.execute('SELECT * FROM challenge_attempts WHERE attempt_id=?', (state['challenge']['attempt_id'],)).fetchone())
        session = dict(c.execute('SELECT * FROM sessions WHERE session_id=?', (state['session_id'],)).fetchone())
        owner = dict(c.execute('SELECT * FROM session_owners WHERE session_id=?', (state['session_id'],)).fetchone())
        link = dict(c.execute('SELECT * FROM shared_sessions WHERE session_id=?', (state['session_id'],)).fetchone())
        user = dict(c.execute('SELECT * FROM users WHERE user_id=?', (owner['user_id'],)).fetchone())
        def insert(table, row):
            columns = ','.join(row)
            c.execute(f"INSERT INTO {table}({columns}) VALUES({','.join('?' for _ in row)})", tuple(row.values()))
        for i in range(51):
            uid, sid, aid = (str(uuid.uuid4()) for _ in range(3))
            insert('users', {**user, 'user_id': uid, 'username': 'query_fixture_' + str(i)})
            insert('sessions', {**session, 'session_id': sid, 'token_hash': str(uuid.uuid4())})
            insert('session_owners', {**owner, 'session_id': sid, 'user_id': uid})
            insert('shared_sessions', {**link, 'session_id': sid, 'user_id': uid, 'current_attempt_id': aid})
            insert('challenge_attempts', {**attempt, 'attempt_id': aid, 'session_id': sid, 'user_id': uid, 'elapsed_ms': 1000 + i})
    result = board(w.b, share)
    assert len(result['entries']) == 50 and result['total_players'] == 52
    assert result['own_entry']['rank'] == 52 and result['own_entry']['username'] == 'sharing_beta'
    assert result['own_entry']['elapsed_ms'] == 90000
    assert all(entry['username'] != 'sharing_beta' for entry in result['entries'])
    assert [entry['rank'] for entry in result['entries']] == list(range(1, 51))
    observe('leaderboard-window', {'visible_entries': 50, 'own_rank': 52, 'total_players': 52}, {'visible_entries': len(result['entries']), 'own_rank': result['own_entry']['rank'], 'total_players': result['total_players'], 'fixture': '51 controlled SQL score rows; no additional route/paid claims'})
