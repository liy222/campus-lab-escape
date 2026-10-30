"""Synthetic, TEMP-only generation metadata checks; no provider/ledger/network."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import subprocess
import sys
from types import SimpleNamespace

import pytest
from tests.v5.conftest import Actor, CANARY, rid
from tests.v5.test_blueprint_generation import synthetic_model_content
from backend.app.ai.provider import ProviderError
from backend.app.ai.v5 import GenerationService, ServiceError
from backend.app.domain import generation_content_v2 as content
from backend.app.domain.generation_observability import SOURCE_FILES
from backend.app.main import create_v5_app
from scripts.generation_trace import ROOT, read_trace

PRIVATE_TEXT = 'SYNTHETIC_PRIVATE_MODEL_TEXT_ONLY_4d2c'


class FakeProvider:
    def __init__(self, raw=None, error=None):
        self.raw, self.error, self.calls = raw, error, 0
    async def complete(self, messages, tools, limits, **kwargs):
        self.calls += 1
        if self.error: raise self.error
        return SimpleNamespace(content=self.raw, tool_calls=[], usage={'prompt_tokens': 10, 'completion_tokens': 10})


def prepared(tmp_path, monkeypatch, raw=None, provider_error=None):
    bp = content.select_blueprint(1, 'easy', seed=0)
    monkeypatch.setattr(content, 'select_blueprint', lambda *args, **kwargs: bp)
    good = synthetic_model_content(bp)
    effects = content.puzzle_effects(bp)
    for obj in bp.objects:
        if obj.kind != 'puzzle':
            continue
        requirements = content.name_requirements(effects[obj.object_id])
        prefix = '门禁甲' if requirements['require_access_word'] else '主题甲'
        good['objects'][obj.object_id]['name'] = prefix + requirements['allowed_suffixes'][0]
    provider = FakeProvider(json.dumps(good, ensure_ascii=False) if raw is None else raw, provider_error)
    app = create_v5_app(tmp_path / 'temp-only.sqlite', generation_service=GenerationService(lambda key: provider))
    actor = Actor(app).authenticate('trace_actor')
    return app, actor, provider, good


def run_job(actor, theme):
    response = actor.post('/level-generations', {'request_id': rid(), 'theme': theme,
        'room_count': 1, 'difficulty': 'easy'}, headers={'X-AI-Api-Key': CANARY})
    assert response.status_code == 202
    job_id = response.json()['data']['job']['job_id']
    return actor.get('/level-generations/' + job_id).json()['data']['job']


def assert_safe(trace, *secrets):
    rendered = json.dumps(trace, ensure_ascii=False)
    for secret in (PRIVATE_TEXT, CANARY, *secrets): assert secret not in rendered
    assert trace['run_id']
    for event in trace['events']:
        assert datetime.fromisoformat(event['recorded_at'].replace('Z', '+00:00')).tzinfo == timezone.utc
        assert all(type(value) is int and value >= 0 for value in event['counts'].values())
        source = event['source']
        assert source['source_version'] == 'generation-observability-v1'
        assert set(source['file_fingerprints']) == set(SOURCE_FILES)
        for name, digest in source['file_fingerprints'].items():
            assert digest == hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


@pytest.mark.parametrize('branch', ['parse', 'schema', 'narrative', 'assembly'])
def test_actual_content_failure_branches_have_safe_distinct_reasons(tmp_path, monkeypatch, branch):
    app, actor, provider, good = prepared(tmp_path, monkeypatch)
    if branch == 'parse': provider.raw = '{' + PRIVATE_TEXT
    elif branch == 'schema': provider.raw = json.dumps({'title': PRIVATE_TEXT})
    elif branch == 'narrative':
        good['story'] = '离开前必须归还所有资料。'
        provider.raw = json.dumps(good, ensure_ascii=False)
    else:
        def fail_assembly(*args): raise ValueError(PRIVATE_TEXT)
        monkeypatch.setattr(content.v1, 'assemble_draft', fail_assembly)
    theme = '仅供隔离测试的主题' + branch
    job = run_job(actor, theme)
    assert job['status'] == 'rejected' and job['error_code'] == 'MODEL_INVALID_OUTPUT'
    trace = read_trace(app.state.v5_database.path, job['job_id'])
    assert [event['stage'] for event in trace['events']] == ['pending', 'generating', 'rejected']
    terminal = trace['events'][-1]
    assert terminal['reason'] == branch
    assert terminal['counts']['model_response_utf8_bytes'] == len(provider.raw.encode())
    assert terminal['counts']['model_response_characters'] == len(provider.raw)
    assert trace['events'][0]['counts']['theme_characters'] == len(theme)
    assert provider.calls == 1
    assert_safe(trace, theme, actor.client.cookies.get('campus_v5_session'))


def test_success_admission_and_proof_have_real_phase_paths_and_cli_is_read_only(tmp_path, monkeypatch):
    app, actor, provider, _ = prepared(tmp_path, monkeypatch)
    job = run_job(actor, '成功合成主题')
    assert job['status'] == 'ready' and job['error_code'] is None
    database = Path(app.state.v5_database.path)
    trace = read_trace(database, job['job_id'])
    assert [event['stage'] for event in trace['events']] == ['pending', 'generating', 'validating', 'ready']
    assert trace['events'][-1]['reason'] == 'completed'
    assert trace['events'][2]['counts']['rooms'] == 1
    assert trace['events'][-1]['counts']['witness_steps'] > 0
    assert_safe(trace, '成功合成主题')
    before = database.read_bytes()
    result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-m', 'scripts.generation_trace',
        '--job-id', job['job_id'], '--database', str(database)], cwd=ROOT,
        capture_output=True, encoding='utf-8')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == trace
    assert database.read_bytes() == before
    from backend.app.api import v5 as api
    for message, expected_reason, expected_code in [
            ('PRIVATE invalid draft ' + PRIVATE_TEXT, 'admission', 'ADMISSION_REJECTED'),
            ('PROOF_UNKNOWN', 'proof', 'PROOF_UNKNOWN')]:
        def fail_compile(*args, _message=message, **kwargs): raise ValueError(_message)
        monkeypatch.setattr(api, 'compile_level', fail_compile)
        failed = run_job(actor, expected_reason + '合成主题')
        assert failed['status'] == 'rejected' and failed['error_code'] == expected_code
        failed_trace = read_trace(database, failed['job_id'])
        assert [event['stage'] for event in failed_trace['events']] == ['pending', 'generating', 'validating', 'rejected']
        assert failed_trace['events'][-1]['reason'] == expected_reason
        assert_safe(failed_trace, expected_reason + '合成主题')
    assert provider.calls == 3


def test_provider_and_untrusted_diagnostic_are_controlled(tmp_path, monkeypatch):
    app, actor, provider, _ = prepared(tmp_path, monkeypatch, provider_error=ProviderError('MODEL_TIMEOUT'))
    job = run_job(actor, '提供方超时合成主题')
    assert (job['status'], job['error_code']) == ('failed', 'MODEL_TIMEOUT')
    trace = read_trace(app.state.v5_database.path, job['job_id'])
    assert [event['stage'] for event in trace['events']] == ['pending', 'generating', 'failed']
    assert trace['events'][-1]['reason'] == 'timeout'
    assert 'model_response_characters' not in trace['events'][-1]['counts']
    assert trace['events'][-1]['counts']['messages_utf8_bytes'] > 0
    assert_safe(trace, '提供方超时合成主题')
    class UnsafeDiagnostic:
        async def generate(self, **kwargs):
            raise ServiceError('MODEL_INVALID_OUTPUT', diagnostic=PRIVATE_TEXT,
                counts={'model_response_characters': 19, 'private_text': PRIVATE_TEXT, 'rooms': True})
    app.state.generation_service = UnsafeDiagnostic()
    job = run_job(actor, '不可信诊断合成主题')
    trace = read_trace(app.state.v5_database.path, job['job_id'])
    assert trace['events'][-1]['reason'] == 'unspecified'
    assert trace['events'][-1]['counts'] == {'model_response_characters': 19}
    assert_safe(trace, '不可信诊断合成主题')


def test_old_job_without_events_is_explicit_and_cli_does_not_import_main(tmp_path):
    database = tmp_path / 'old-temp.sqlite'
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE level_generations(job_id TEXT,status TEXT,theme TEXT)')
        connection.execute('INSERT INTO level_generations VALUES(?,?,?)', ('old_job', 'ready', PRIVATE_TEXT))
        connection.execute('CREATE TABLE generated_levels(definition_json TEXT)')
        connection.execute('INSERT INTO generated_levels VALUES(?)', (PRIVATE_TEXT,))
    before = database.read_bytes()
    # Fresh interpreter proves the delivery tool does not import/start main.
    code = "import scripts.generation_trace as trace,sys; assert 'backend.app.main' not in sys.modules; raise SystemExit(trace.main())"
    result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', code,
        '--job-id', 'old_job', '--database', str(database)], cwd=ROOT,
        capture_output=True, encoding='utf-8')
    assert result.returncode == 0, result.stderr
    trace = json.loads(result.stdout)
    assert trace['recorded'] is False and trace['events'] == []
    assert '未记录' in trace['message'] and PRIVATE_TEXT not in result.stdout
    assert database.read_bytes() == before
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='generation_job_events'").fetchall() == []


def test_restart_records_only_observed_jobs_without_backfilling_old_jobs(system, actor):
    from backend.app.storage.v5 import V5Database
    app, _ = system
    new_job = actor.generate(theme='新观测合成任务')
    old_job = actor.generate(theme='模拟旧任务没有阶段记录')
    db = app.state.v5_database
    with db.transaction() as connection:
        definitions = [tuple(row) for row in connection.execute('SELECT level_id,definition_json,metadata_json FROM generated_levels ORDER BY level_id')]
        connection.execute('DELETE FROM generation_job_events WHERE job_id=?', (old_job['job_id'],))
        connection.execute("UPDATE level_generations SET status='generating' WHERE job_id IN (?,?)", (new_job['job_id'], old_job['job_id']))
    V5Database(db.path)  # Actual existing restart branch, isolated TEMP store.
    trace = read_trace(db.path, new_job['job_id'])
    assert trace['current_status'] == 'unknown'
    assert trace['events'][-1]['stage'] == 'unknown'
    assert trace['events'][-1]['reason'] == 'process_restart'
    legacy = read_trace(db.path, old_job['job_id'])
    assert legacy['current_status'] == 'unknown' and not legacy['recorded'] and legacy['events'] == []
    with db.transaction() as connection:
        assert [tuple(row) for row in connection.execute('SELECT level_id,definition_json,metadata_json FROM generated_levels ORDER BY level_id')] == definitions
        assert connection.execute("SELECT value FROM v5_metadata WHERE key='database_version'").fetchone()[0] == '5'
