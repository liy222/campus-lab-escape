"""Additional targeted hint completion race, no network or persistent real DB."""
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
with tempfile.TemporaryDirectory(prefix='campus-v34-race-') as directory:
    os.environ['SQLITE_PATH'] = str(Path(directory) / 'module.sqlite')
    os.environ['GAMEPLAY_VERSION'] = 'v3.4'
    from fastapi.testclient import TestClient
    from backend.app.main import create_app
    from backend.app.ai.types import TurnResult, Version

    class RacingRuntime:
        async def run(self, start, callbacks):
            current = start.visible_state
            # A real manual inspect commits while this hint is in flight.
            status, _ = app.state.store.action(session_id, token, {
                'request_id': uuid4().hex, 'revision': current['revision'], 'generation': current['generation'],
                'tool': 'inspect', 'arguments': {'object_id': 'r1_plaque'}})
            assert status == 200
            return TurnResult({'answer': 'PRIVATE_RACE_SENTINEL 4217', 'clue_refs': ['r1_record_clue', 'r1_clock_clue'],
                'status': 'no_suggestion', 'stop_reason': None,
                'usage': {'provider': 'mock', 'model': None, 'input_tokens': None, 'output_tokens': None, 'model_calls': 0, 'read_tool_calls': 0}},
                None, (), Version.from_state(current))

    app = create_app(db_path=Path(directory) / 'race.sqlite', gameplay_version='v3.4', runtime=RacingRuntime())
    with TestClient(app) as client:
        created = client.post('/api/sessions', json={}).json()['data']
        session_id, token, state = created['session_id'], created['token'], created['visible_state']
        headers = {'X-Session-Token': token}
        for object_id in ('r1_clock', 'r1_record'):
            response = client.post(f'/api/sessions/{session_id}/actions', headers=headers, json={
                'request_id': uuid4().hex, 'revision': state['revision'], 'generation': state['generation'],
                'tool': 'inspect', 'arguments': {'object_id': object_id}})
            assert response.status_code == 200
            state = response.json()['data']['visible_state']
        raw = {'request_id': uuid4().hex, 'revision': state['revision'], 'generation': state['generation'], 'message': 'hint', 'hint_level': 3}
        response = client.post(f'/api/sessions/{session_id}/ai/turns', headers=headers, json=raw)
        assert response.status_code == 200
        data = response.json()['data']
        assert data['status'] == 'stopped' and data['stop_reason'] == 'STALE_STATE'
        assert data['visible_state']['statistics']['hint_count'] == 0 and data['proposal'] is None
        assert 'PRIVATE_RACE_SENTINEL' not in data['answer'] and '4217' not in data['answer']
        replay = client.post(f'/api/sessions/{session_id}/ai/turns', headers=headers, json=raw)
        assert replay.status_code == 200 and replay.json()['data']['visible_state']['statistics']['hint_count'] == 0
report_path = ROOT / 'evidence/upgrade/v3.4/backend.json'
report = json.loads(report_path.read_text(encoding='utf-8'))
name = 'evidence/upgrade/v3.4/backend-stale-selfcheck.py'
if name not in report['files']:
    report['files'].append(name)
report['raw_sha256'][name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
report['commands'].append({'command': 'C:/Users/liyh/.conda/envs/1/python.exe evidence/upgrade/v3.4/backend-stale-selfcheck.py', 'exit': 0})
report['checks'].append({'operation': 'hint-race-and-replay', 'http': 200, 'stop_reason': 'STALE_STATE', 'hint_count': 0})
report['summary'].append('manual state change during hint invalidates reply; stale completion/replay never count hints')
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': 'PASS', 'target': 'hint-race-and-replay', 'hint_count': 0}))
