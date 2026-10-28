"""Read local generation metadata only; does not import main or migrate stores."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sqlite3
from contextlib import closing

from backend.app.domain.generation_observability import (
    ROOT, SOURCE_FILES, STAGES, safe_counts, safe_reason,
)


def _object(value):
    try:
        result = json.loads(value)
        return result if isinstance(result, dict) else {}
    except (TypeError, ValueError): return {}


def _source(value):
    value = _object(value)
    result = {'source_version': 'generation-observability-v1'}
    revision = value.get('git_revision')
    result['git_revision'] = revision if isinstance(revision, str) and re.fullmatch(r'[a-f0-9]{40,64}', revision) else None
    fingerprints = value.get('file_fingerprints', {})
    if not isinstance(fingerprints, dict): fingerprints = {}
    result['file_fingerprints'] = {
        name: item if isinstance(item, str) and re.fullmatch(r'[a-f0-9]{64}', item) else None
        for name in SOURCE_FILES for item in [fingerprints.get(name)]}
    return result


def read_trace(database, job_id):
    if not isinstance(job_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', job_id):
        raise ValueError('INVALID_JOB_ID')
    path = Path(database).resolve(strict=True)
    # mode=ro refuses creation/writes. Query only named non-sensitive columns;
    # generated definitions, themes, credentials and receipts are never selected.
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        job = connection.execute('SELECT job_id,status FROM level_generations WHERE job_id=?', (job_id,)).fetchone() if 'level_generations' in tables else None
        result = {'run_id': job_id, 'recorded': False, 'events': []}
        if job:
            result['current_status'] = job['status'] if job['status'] in STAGES else 'unknown'
        rows = connection.execute('SELECT event_id,stage,recorded_at,reason,counts_json,source_json FROM generation_job_events WHERE job_id=? ORDER BY event_id', (job_id,)).fetchall() if 'generation_job_events' in tables else []
        for row in rows:
            stamp = row['recorded_at']
            result['events'].append({
                'event_id': row['event_id'], 'stage': row['stage'] if row['stage'] in STAGES else 'unknown',
                'recorded_at': stamp if isinstance(stamp, str) and re.fullmatch(r'[0-9T:.+-]+Z', stamp) else None,
                'reason': safe_reason(row['reason']), 'counts': safe_counts(_object(row['counts_json'])),
                'source': _source(row['source_json']),
            })
        result['recorded'] = bool(result['events'])
        if not result['recorded']:
            result['message'] = '此任务未记录生成观测；历史任务不会补写阶段。' if job else '未找到此任务的生成观测记录。'
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='只读本地生成任务的阶段与安全计数，不读取主题、模型正文或私有定义。')
    parser.add_argument('--job-id', required=True)
    parser.add_argument('--database', type=Path, default=ROOT / 'data/game-v5.sqlite')
    parser.add_argument('--export', type=Path,
                        help='将已读取的安全元数据写入新JSON文件，不覆盖；建议随后collect至固定阶段logs目录。')
    args = parser.parse_args(argv)
    try:
        result = read_trace(args.database, args.job_id)
    except (OSError, sqlite3.Error, ValueError):
        print(json.dumps({'recorded': False, 'error': 'TRACE_UNAVAILABLE', 'message': '无法读取观测，请检查本地数据库与任务标识。'}, ensure_ascii=False))
        return 1
    if args.export is not None:
        try:
            if args.export.suffix.lower() != '.json':
                raise ValueError('export requires a JSON path')
            # Exclusive create: never overwrite a prior trace or the database.
            with args.export.open('x', encoding='utf-8', newline='\n') as stream:
                stream.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        except (OSError, ValueError):
            print(json.dumps({'recorded': False, 'error': 'TRACE_EXPORT_UNAVAILABLE',
                              'message': '无法导出；请使用已存在目录中的新JSON路径，已有文件不会覆盖。'}, ensure_ascii=False))
            return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
