"""One actual child-process continuation; isolated existing Synthetic DB only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.v5.test_sharing import world, compiled, publication, join, finish_until_last, board, observe


def test_child_process_keeps_start_and_finishes_original_attempt(world):
    w = world; share = publication(w.a, w.lid)['share_id']; state = join(w.b, share)
    original = state['challenge']; state = finish_until_last(w.b, state, w.compiled)
    final = w.compiled.witness[-1]
    request = {'db': str(w.path), 'session_id': state['session_id'], 'share_id': share,
               'attempt_id': original['attempt_id'], 'started_at': original['started_at'],
               'clock_ms': w.clock.ms + 654321, 'action': final, 'parent_pid': os.getpid(),
               'definition_hash': state['definition_hash']}
    env = os.environ.copy(); env['SQLITE_PATH'] = str(w.path.parent / 'child-import-v5.sqlite')
    env.update(GAMEPLAY_VERSION='v5', AI_PROVIDER='mock', PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(Path(__file__).resolve()), '--probe'],
                            input=json.dumps(request), capture_output=True, text=True,
                            encoding='utf-8', env=env, timeout=30, cwd=Path(__file__).resolve().parents[2])
    assert result.returncode == 0, 'Child process continuation failed; no raw stdout/stderr emitted'
    actual = json.loads(result.stdout)
    assert actual == {'different_process': True, 'attempt_unchanged': True, 'start_unchanged': True,
                      'definition_unchanged': True, 'finished': True, 'elapsed_ms': 654321,
                      'one_score': True, 'generation_calls': 0}
    observe('actual-child-process-continuation', {'elapsed_ms': 654321, 'same_attempt': True, 'generation_calls': 0}, actual)


def probe():
    request = json.loads(sys.stdin.read()); db = Path(request['db']).resolve()
    assert db.name == 'game-v5.sqlite' and db.is_relative_to(Path(tempfile.gettempdir()).resolve()) and db.is_file()
    from tests.v5.conftest import Actor
    from backend.app.main import create_v5_app
    from backend.app.storage import sharing
    sharing.now_ms = lambda: request['clock_ms']
    class ForbiddenGeneration:
        calls = 0
        async def generate(self, **kwargs):
            self.calls += 1
            raise AssertionError('Reopen must not generate')
    generator = ForbiddenGeneration()
    app = create_v5_app(db, generation_service=generator)
    actor = Actor(app).authenticate('sharing_beta', False)
    try:
        state = actor.state(request['session_id']); before = state['challenge']
        response = actor.action(state, request['action']['tool'], request['action']['arguments'])
        assert response.status_code == 200
        after = response.json()['data']['visible_state']
        result = actor.get('/shared-levels/' + request['share_id'] + '/leaderboard').json()['data']
        print(json.dumps({'different_process': os.getpid() != request['parent_pid'],
                          'attempt_unchanged': before['attempt_id'] == request['attempt_id'] == after['challenge']['attempt_id'],
                          'start_unchanged': before['started_at'] == request['started_at'] == after['challenge']['started_at'],
                          'definition_unchanged': after['definition_hash'] == request['definition_hash'],
                          'finished': after['status'] == 'won' and after['challenge']['status'] == 'finished',
                          'elapsed_ms': after['challenge']['elapsed_ms'], 'one_score': len(result['entries']) == 1,
                          'generation_calls': generator.calls}))
    finally: actor.client.close()


if __name__ == '__main__':
    if sys.argv[1:] != ['--probe']: raise SystemExit('Probe only')
    probe()
