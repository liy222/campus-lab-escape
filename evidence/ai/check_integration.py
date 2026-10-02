"""Owner mock checks over real Backend callbacks; never uses hidden rules."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
OUT.mkdir(parents=True, exist_ok=False)


def main():
    from fastapi.testclient import TestClient
    from backend.app.ai.mock import DeterministicMockProvider
    from backend.app.ai.provider import DeepSeekConfig, MockProvider, ProviderResult
    from backend.app.ai.runtime import Runtime

    results = []
    with tempfile.TemporaryDirectory(prefix="owner_mock_", dir=OUT) as task_tmp:
        task_dir = Path(task_tmp).resolve()
        assert task_dir.is_relative_to(OUT.resolve())
        # Import-time app also writes only the owned disposable evidence directory.
        with patch.dict(os.environ, {"SQLITE_PATH": str(task_dir / "import.sqlite"), "AI_PROVIDER": "mock"}):
            from backend.app.main import create_app

        def create(client):
            response = client.post('/api/sessions', json={})
            assert response.status_code == 201
            data = response.json()['data']
            return data['session_id'], {'X-Session-Token': data['token']}, data['visible_state']

        def action(client, session_id, headers, state, tool, arguments, request_id):
            response = client.post(f'/api/sessions/{session_id}/actions', headers=headers, json={"request_id": request_id, "revision": state['revision'], "generation": state['generation'], "tool": tool, "arguments": arguments})
            assert response.status_code == 200, response.json().get('error', {}).get('code')
            return response.json()['data']['visible_state']

        def ask(client, session_id, headers, state, request_id):
            response = client.post(f'/api/sessions/{session_id}/ai/turns', headers=headers, json={"request_id": request_id, "revision": state['revision'], "generation": state['generation'], "message": "下一步可以做什么？"})
            assert response.status_code == 200, response.json().get('error', {}).get('code')
            return response.json()['data']

        # Both runtime layouts receive the exact same real backend start/history.
        scripted = ProviderResult(json.dumps({"answer": "请依据公开线索继续。", "clue_refs": [], "proposal": None}, ensure_ascii=False), (), None, "mock", "owner_script", "owner_script", "stop")
        seed_path = task_dir / 'seed.sqlite'
        seed_app = create_app(db_path=seed_path, provider=MockProvider([scripted]))
        with TestClient(seed_app) as client:
            session_id, headers, visible = create(client)
            for ordinal, obj in enumerate(visible['objects'][:2]):
                visible = action(client, session_id, headers, visible, 'inspect', {'object_id': obj['object_id']}, f'inspect_{ordinal}')
            for ordinal in range(13):
                visible = action(client, session_id, headers, visible, 'get_inventory', {}, f'inventory_{ordinal}')
            data = ask(client, session_id, headers, visible, 'history_seed')
            assert data['status'] == 'no_suggestion'
            visible = data['visible_state']

        class RecordingMock(DeterministicMockProvider):
            def __init__(self):
                self.contexts = []
            async def complete(self, messages, *args, **kwargs):
                self.contexts.append(json.loads(next(m['content'] for m in messages if m['role'] == 'user')))
                return await super().complete(messages, *args, **kwargs)

        contexts = {}
        for mode in ('full_history', 'structured_summary'):
            destination = task_dir / (mode + '.sqlite')
            with closing(sqlite3.connect(seed_path)) as source, closing(sqlite3.connect(destination)) as target:
                source.backup(target)
            provider = RecordingMock()
            app = create_app(db_path=destination, runtime=Runtime(provider, context_mode=mode))
            with TestClient(app) as client:
                data = ask(client, session_id, headers, visible, 'layout_comparison')
                assert data['status'] == 'completed' and data['proposal']['status'] == 'pending'
                assert data['usage']['provider'] == 'mock' and data['usage']['input_tokens'] is None
                contexts[mode] = provider.contexts[0]
                results.append({'name': 'backend_runtime_' + mode, 'passed': True, 'status': data['status'], 'model_calls': data['usage']['model_calls']})
        full, summary = contexts['full_history'], contexts['structured_summary']
        recovered = [entry for group in summary['visible_history_summary']['records_by_tool'].values() for entry in group]
        recovered.sort(key=lambda e: e['history_index'])
        recovered = [{k: v for k, v in e.items() if k != 'history_index'} for e in recovered]
        assert len(full['visible_history']) == 16 and recovered == full['visible_history']
        assert any(e['kind'] == 'ai_turn' for e in recovered)
        assert full['visible_state'] == summary['visible_state'] and full['message'] == summary['message']
        results.append({'name': 'two_real_backend_contexts_same_16_history_records', 'passed': True, 'history_records': 16})
        (OUT / 'context_comparison.json').write_text(json.dumps(contexts, ensure_ascii=False, indent=2), encoding='utf-8')

        app = create_app(db_path=task_dir / 'progress.sqlite', provider=DeterministicMockProvider())
        path = []
        with TestClient(app) as client:
            sid, auth, current = create(client)
            for ordinal in range(30):
                data = ask(client, sid, auth, current, f'turn_{ordinal}')
                assert data['status'] == 'completed', data['stop_reason']
                proposal = data['proposal']
                assert proposal and proposal['status'] == 'pending'
                assert proposal['tool'] in {'take', 'use_item', 'submit_code', 'move'}
                assert '尚未执行' in data['answer']
                assert all(r in {c['clue_id'] for c in data['visible_state']['clues']} for r in proposal['clue_refs'])
                # Harness plays the explicit player-confirmation role for mock only.
                confirmed = client.post(f'/api/sessions/{sid}/proposals/{proposal["proposal_id"]}/confirm', headers=auth, json={})
                assert confirmed.status_code == 200, confirmed.json().get('error', {}).get('code')
                committed = confirmed.json()['data']
                assert committed['proposal']['status'] == 'committed'
                current = committed['visible_state']
                path.append({'turn': ordinal, 'tool': proposal['tool'], 'room_after_confirmation': current['room']['room_id'], 'revision': current['revision'], 'clue_refs': proposal['clue_refs'], 'usage': data['usage']})
                if current['status'] == 'won':
                    break
            assert current['status'] == 'won' and current['room']['room_id'] == 'EXIT'
        results.append({'name': 'mock_three_rooms_explicit_confirmation_chain', 'passed': True, 'confirmed_proposals': len(path), 'status': current['status']})
        (OUT / 'mock_confirmed_path.json').write_text(json.dumps(path, ensure_ascii=False, indent=2), encoding='utf-8')

        cases = [('unknown_provider', {'AI_PROVIDER': 'not_approved'}, None),
                 ('missing_credentials', {'AI_PROVIDER': 'deepseek'}, DeepSeekConfig('')),
                 ('bad_model', {'AI_PROVIDER': 'deepseek'}, DeepSeekConfig('synthetic_unused_key', model='unapproved')),
                 ('bad_url', {'AI_PROVIDER': 'deepseek'}, DeepSeekConfig('synthetic_unused_key', base_url='https://invalid.test'))]
        for name, environment, config in cases:
            with patch.dict(os.environ, environment):
                config_patch = patch('backend.app.ai.runtime.DeepSeekConfig.from_environment', return_value=config) if config else patch('backend.app.ai.runtime.DeepSeekConfig.from_environment', side_effect=AssertionError('must not read environment file'))
                with config_patch:
                    badapp = create_app(db_path=task_dir / (name + '.sqlite'))
            with TestClient(badapp) as client:
                assert client.get('/api/health').status_code == 200
                sid, auth, current = create(client)
                current = action(client, sid, auth, current, 'inspect', {'object_id': current['objects'][0]['object_id']}, 'manual_still_works')
                data = ask(client, sid, auth, current, 'unavailable_ai')
                assert data['status'] == 'stopped' and data['stop_reason'] == 'MODEL_UNAVAILABLE'
                assert data['usage']['provider'] == ('unavailable' if name == 'unknown_provider' else 'deepseek')
                assert data['usage']['input_tokens'] is data['usage']['output_tokens'] is None
                results.append({'name': 'manual_available_' + name, 'passed': True, 'ai_status': data['status'], 'provider': data['usage']['provider']})

    hashes = {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for base in ('backend/app/ai', 'backend/app/storage', 'backend/app/api') for p in sorted((ROOT / base).glob('*.py'))}
    hashes['backend/app/main.py'] = hashlib.sha256((ROOT / 'backend/app/main.py').read_bytes()).hexdigest()
    report = {'kind': 'owner_mock_backend_integration', 'real_network_calls': 0, 'paid_calls': 0, 'checks': results, 'source_sha256': hashes,
              'limitations': ['Owner checks, not independent QA.', 'No real provider acceptance.', 'Current-generation full history excludes previous reset/restore generations and rejected actions.', 'Player confirmations were simulated by this mock-only harness.']}
    (OUT / 'integration_checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'checks_passed': len(results), 'confirmed_mock_proposals': len(path), 'evidence': str(OUT)}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        hashes = {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / 'backend/app/ai').glob('*.py'))}
        (OUT / 'failure.json').write_text(json.dumps({'kind': 'owner_mock_integration_failure', 'exception_type': type(error).__name__, 'message': str(error), 'paid_calls': 0, 'source_sha256': hashes}), encoding='utf-8')
        raise
