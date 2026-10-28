"""TEMP-only archive/review/trace-export checks; no real evidence or player data."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest
from scripts import evidence_hub as hub
from scripts import generation_trace


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = tmp_path / 'archive'
    monkeypatch.setattr(hub, 'HUB_ROOT', root)
    return tmp_path, root


def metadata(root, stage='sample'):
    return json.loads((root / 'stages' / stage / 'stage.json').read_text(encoding='utf-8'))


def test_init_has_no_acceptance_and_refuses_existing_stage(workspace, capsys):
    _, root = workspace
    assert hub.main(['init', '--stage', 'sample', '--title', '合成测试阶段', '--activate']) == 0
    created = json.loads(capsys.readouterr().out)
    assert created['technical_status'] == 'not_recorded'
    assert created['human_review_status'] == created['owner_review_status'] == created['peer_review_status'] == 'not_reviewed'
    assert created['collections'] == []
    for category in hub.CATEGORIES: assert (root / 'stages/sample' / category).is_dir()
    human = root / 'human-reviews/sample/round-01'
    assert (human / 'screenshots').is_dir()
    assert '未核验' in (human / 'review.md').read_text(encoding='utf-8')
    assert not (human / 'events.jsonl').exists()
    index_before = (root / 'index.json').read_bytes()
    stage_before = (root / 'stages/sample/stage.json').read_bytes()
    with pytest.raises(FileExistsError): hub.init_stage('sample', '不得覆盖')
    assert (root / 'index.json').read_bytes() == index_before
    assert (root / 'stages/sample/stage.json').read_bytes() == stage_before
    hub.init_stage('second', '下一合成阶段')
    assert json.loads((root / 'index.json').read_text(encoding='utf-8'))['active_stage'] == 'sample'
    for unsafe in ('../escape', '/absolute', 'C:\\escape', 'not a slug'):
        with pytest.raises(ValueError): hub.init_stage(unsafe, '拒绝越界')


def test_collect_copies_bytes_and_records_import_without_execution(workspace):
    tmp, root = workspace
    hub.init_stage('sample', '合成归档')
    source = tmp / 'result.json'
    payload = b'{"result":"passed","count":2}\n'
    source.write_bytes(payload)
    item = hub.collect('sample', 'automated', source, name='run-01/result.json')
    target = root / item['archive_path']
    assert source.read_bytes() == target.read_bytes() == payload
    assert item['sha256'] == hashlib.sha256(payload).hexdigest()
    assert item['source_path'] == str(source.resolve())
    assert item['new_execution'] is False and item['collected_at'].endswith('Z')
    stage_before = (root / 'stages/sample/stage.json').read_bytes()
    with pytest.raises(FileExistsError): hub.collect('sample', 'automated', source, name='run-01/result.json')
    assert target.read_bytes() == payload
    assert (root / 'stages/sample/stage.json').read_bytes() == stage_before
    for name in ('../escape.json', '/escape.json', 'C:\\escape.json', 'a/../../escape.json', 'a\\..\\escape.json', 'NUL.json', 'bad:stream.json'):
        with pytest.raises(ValueError): hub.collect('sample', 'logs', source, name=name)
    outside = tmp / 'outside'
    outside.mkdir()
    link = root / 'stages/sample/logs/linked'
    try: link.symlink_to(outside, target_is_directory=True)
    except OSError: pass  # Windows can disallow creating test symlinks.
    else:
        with pytest.raises(ValueError): hub.collect('sample', 'logs', source, name='linked/result.json')
        assert list(outside.iterdir()) == []
    state = metadata(root)
    assert len(state['collections']) == 1 and state['human_review_status'] == 'not_reviewed'


def test_sensitive_and_database_sources_are_rejected(workspace):
    tmp, _ = workspace
    hub.init_stage('sample', '合成安全边界')
    samples = {
        'store.sqlite': b'synthetic-not-a-real-database',
        'disguised.txt': b'SQLite format 3\x00' + b'synthetic',
        '.env.example': b'SYNTHETIC_ONLY=1',
        'raw-sensitive/report.txt': b'synthetic',
        'G3-provider-result.json': b'{}',
        'sample-definition.json': b'{}',
        'sample-witness.json': b'{}',
        'unsafe-shape.json': b'{"parameters":{"synthetic":1}}',
        'credential.log': b'Authorization: Bearer SYNTHETIC_ONLY_CREDENTIAL_12345',
    }
    for name, payload in samples.items():
        source = tmp / name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(payload)
        with pytest.raises(ValueError): hub.collect('sample', 'logs', source)


def test_human_feedback_is_append_only_and_owner_peer_are_separate(workspace):
    tmp, root = workspace
    hub.init_stage('sample', '合成人工反馈')
    image = tmp / 'user-inputs' / '屏幕截图 2026-10-28 141203.png'
    image.parent.mkdir()
    image.write_bytes(b'\x89PNG\r\n\x1a\nSYNTHETIC_IMAGE_BYTES')
    automated = hub.collect('sample', 'screenshots', image)
    with pytest.raises(ValueError):
        hub.record_review('sample', reviewer='owner', mode='executed', decision='accepted',
                          text='合成测试：此图实际是自动化归档', reference='test-only source',
                          screenshots=[root / automated['archive_path']])
    assert metadata(root)['human_review_status'] == 'not_reviewed'
    with pytest.raises(ValueError):
        hub.record_review('sample', reviewer='owner', mode='executed', decision='accepted', text='反馈', reference=' ')
    first = hub.record_review('sample', reviewer='owner', mode='executed', decision='changes-requested',
        text='合成测试反馈：文字遮挡按钮，需要修正。', reference='Synthetic user message #1 (test only)', screenshots=[image])
    screenshot = first['screenshots'][0]
    assert (root / screenshot['archive_path']).read_bytes() == image.read_bytes()
    assert screenshot['sha256'] == hashlib.sha256(image.read_bytes()).hexdigest()
    assert screenshot['origin'] == 'user-provided' and screenshot['source_path'] == str(image.resolve())
    copied_name = Path(screenshot['archive_path']).name
    assert f'(<screenshots/{copied_name}>)' in (root / 'human-reviews/sample/round-01/review.md').read_text(encoding='utf-8')
    assert first['reviewed_at'] is None and first['imported_at'].endswith('Z')
    human = root / 'human-reviews/sample/round-01'
    first_bytes = (human / 'events.jsonl').read_bytes()
    hub.record_review('sample', reviewer='peer', mode='read-existing', decision='accepted',
        text='合成同伴反馈：已检查现有图。', reference='Synthetic peer message #2 (test only)')
    assert metadata(root)['human_review_status'] == 'changes-requested'
    assert metadata(root)['peer_review_status'] == 'accepted'
    hub.record_review('sample', reviewer='owner', mode='executed', decision='accepted',
        text='合成本人结论：修复后可接受。', reference='Synthetic owner message #3 (test only)')
    assert (human / 'events.jsonl').read_bytes().startswith(first_bytes)
    events = [json.loads(line) for line in (human / 'events.jsonl').read_text(encoding='utf-8').splitlines()]
    assert [event['decision'] for event in events] == ['changes-requested', 'accepted', 'accepted']
    assert metadata(root)['human_review_status'] == 'accepted'
    assert metadata(root)['technical_status'] == 'not_recorded'
    old_summary = (human / 'review.md').read_bytes()
    hub.record_review('sample', reviewer='peer', mode='executed', decision='accepted', round_number=2,
        text='新一轮只有同伴核验。', reference='Synthetic peer round 2 (test only)')
    assert metadata(root)['human_review_status'] == 'not_reviewed'
    assert (human / 'review.md').read_bytes() == old_summary
    index = json.loads((root / 'index.json').read_text(encoding='utf-8'))
    assert index['stages'][0]['human_review'].endswith('round-02/review.md')


def test_trace_export_is_new_safe_json_and_database_stays_read_only(workspace):
    tmp, root = workspace
    hub.init_stage('sample', '合成trace导出')
    database = tmp / 'temp-only.sqlite'
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE level_generations(job_id TEXT,status TEXT,theme TEXT)')
        connection.execute('INSERT INTO level_generations VALUES(?,?,?)', ('synthetic_job', 'ready', 'SYNTHETIC_THEME_NOT_EXPORTED'))
        connection.execute('CREATE TABLE generated_levels(definition_json TEXT)')
        connection.execute('INSERT INTO generated_levels VALUES(?)', ('SYNTHETIC_DEFINITION_NOT_READ',))
    before = database.read_bytes()
    export = tmp / 'trace.json'
    args = ['--job-id', 'synthetic_job', '--database', str(database), '--export', str(export)]
    result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-m', 'scripts.generation_trace', *args],
                            cwd=hub.PROJECT_ROOT, capture_output=True, encoding='utf-8')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == json.loads(export.read_text(encoding='utf-8')) == generation_trace.read_trace(database, 'synthetic_job')
    assert 'SYNTHETIC_THEME_NOT_EXPORTED' not in export.read_text(encoding='utf-8')
    assert database.read_bytes() == before
    exported_before = export.read_bytes()
    repeat = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-m', 'scripts.generation_trace', *args],
                            cwd=hub.PROJECT_ROOT, capture_output=True, encoding='utf-8')
    assert repeat.returncode == 1 and export.read_bytes() == exported_before
    assert database.read_bytes() == before
    invalid_export = tmp / 'not-json.txt'
    assert generation_trace.main(['--job-id', 'synthetic_job', '--database', str(database),
                                  '--export', str(invalid_export)]) == 1
    assert not invalid_export.exists() and database.read_bytes() == before
    copied = hub.collect('sample', 'logs', export)
    assert (root / copied['archive_path']).read_bytes() == exported_before
