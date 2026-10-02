"""Narrow T16 recovery check: a durable reserved claim survives Store replacement."""
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

os.environ['AI_PROVIDER'] = 'mock'
from fastapi.testclient import TestClient
from backend.app.ai.types import RuntimeBoundaryError, Version
from backend.app.main import create_app
from backend.app.storage.ai import public_validator
from backend.app.storage.sqlite import Store
from evidence.backend.t16_local import CountingMock

ROOT = Path(__file__).resolve().parents[2]
CHECKS = []

def run():
    with tempfile.TemporaryDirectory(prefix='backend-t16-crash-owner-') as temp:
        db = Path(temp) / 'game.sqlite'
        first = Store(db)
        _, created = first.create({})
        sid, token = created['data']['session_id'], created['data']['token']
        state = created['data']['visible_state']
        raw = {'request_id': 'reserved_process_crash', 'revision': 0, 'generation': state['generation'], 'message': '查询当前状态。'}
        start, _ = first.begin_ai(sid, token, raw)
        with first.transaction() as connection:
            assert connection.execute('SELECT phase FROM action_receipts WHERE request_id=?', (raw['request_id'],)).fetchone()['phase'] == 'reserved'
        # No abandon/finish occurs: reconstruction stands for interruption after
        # the durable reservation and before an outcome has been persisted.
        fake = CountingMock()
        with TestClient(create_app(db, provider=fake)) as client:
            result = client.post(f'/api/sessions/{sid}/ai/turns', headers={'X-Session-Token': token}, json=raw)
            assert result.status_code == 503 and result.json()['error']['code'] == 'MODEL_UNAVAILABLE'
            public_validator('error_response').validate(result.json())
            assert fake.calls == 0
            replacement = client.app.state.store
            try:
                replacement.ai_snapshot(sid, start.turn_id, Version(0, state['generation']))
            except RuntimeBoundaryError as error:
                assert error.code == 'STALE_STATE'
            else:
                raise AssertionError('replacement adopted abandoned owner')
            with replacement.transaction() as connection:
                assert connection.execute('SELECT phase FROM action_receipts WHERE request_id=?', (raw['request_id'],)).fetchone()['phase'] == 'reserved'
                assert connection.execute('SELECT COUNT(*) AS n FROM proposals').fetchone()['n'] == 0
            CHECKS.append({'check': 'unabandoned reserved claim survives Store replacement; duplicate returns 503; injected fake provider calls=0; no proposal; old owner callbacks refused', 'passed': True})
        for definition in ('visible_state', 'proposal', 'ai_turn_data'):
            assert set(public_validator(definition).schema) == {'$defs', '$ref'}
        CHECKS.append({'check': 'public subschema validator contains only $defs and $ref, with no inherited root oneOf', 'passed': True})

if __name__ == '__main__':
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = ROOT / 'evidence/backend' / ('t16-recovery-' + stamp + '.json')
    record = {'scope': 'Backend owner narrow recovery mock checks; not formal T18 QA', 'command': r'C:\Users\liyh\.conda\envs\1\python.exe -m evidence.backend.t16_recovery', 'started_at': stamp, 'paid_model_calls': 0, 'explicit_local_provider': True, 'checks': CHECKS}
    try:
        run()
    except Exception as error:
        record.update(exit_code=1, failure_type=type(error).__name__)
        output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        raise
    else:
        paths = sorted((ROOT / 'backend/app').rglob('*.py')) + sorted((ROOT / 'contracts').glob('*.json')) + [Path(__file__)]
        record.update(exit_code=0, source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths})
        output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'PASS {len(CHECKS)} narrow Backend recovery checks; evidence {output.name}; no paid calls')
