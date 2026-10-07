"""Append-only, authenticated manual archives over the existing snapshot format.

Old single-slot rows/endpoints and public game projections remain untouched.
Only these new routes replay completed receipts before checking generation.
"""
import hashlib
import json

from pydantic import ValidationError

from ..domain.models import RuleError, VersionRequest, validate_generation
from ..domain.save_models import CreateSaveRequest, SelectedSave


class SaveStoreMixin:
    def migrate_saves(self, connection):
        connection.execute('''CREATE TABLE IF NOT EXISTS save_slots (
            save_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES sessions(session_id),
            created_at TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        )''')
        connection.execute('CREATE INDEX IF NOT EXISTS save_slots_by_session ON save_slots(session_id,created_at)')

    def legacy_slot(self, connection, session_id):
        row = connection.execute('SELECT summary_json FROM saves WHERE session_id=?', (session_id,)).fetchone()
        if row is None:
            return None
        # Listing never reads private old snapshot content or rewrites old rows.
        summary = json.loads(row['summary_json'])
        metadata = {key: summary[key] for key in ('schema_version', 'level_version', 'saved_at', 'source_revision', 'source_generation')}
        return {**metadata, 'save_id': 'legacy', 'name': '旧版单槽存档', 'room_id': None,
                'status': None, 'clues_found': None, 'kind': 'legacy'}

    def list_saves(self, session_id, token):
        from .sqlite import new_id
        event_id = new_id()
        with self.transaction() as connection:
            state = self.authenticate(connection, session_id, token)
            if state is None:
                return self.failure(connection, event_id, None, 'list_saves', 'FORBIDDEN_SESSION', '无权访问该会话。', expose=False)
            rows = connection.execute('SELECT metadata_json FROM save_slots WHERE session_id=? ORDER BY created_at DESC,rowid DESC', (session_id,)).fetchall()
            slots = [json.loads(row['metadata_json']) for row in rows]
            legacy = self.legacy_slot(connection, session_id)
            if legacy is not None:
                slots.append(legacy)
            return 200, {'ok': True, 'event_id': event_id,
                         'data': {'slots': slots, 'visible_state': self.projection(connection, session_id, state)}}

    def create_save(self, session_id, token, raw, parsed=True):
        return self.execute_save(session_id, token, 'archive_create', raw, parsed)

    def restore_save(self, session_id, token, save_id, raw, parsed=True):
        return self.execute_save(session_id, token, 'archive_restore', raw, parsed, save_id=save_id)

    def execute_save(self, session_id, token, operation, raw, parsed=True, save_id=None):
        from .sqlite import canonical, checksum, new_id, utc_now, validate_snapshot
        event_id = new_id()
        with self.transaction() as connection:
            state = self.authenticate(connection, session_id, token)
            if state is None:
                return self.failure(connection, event_id, None, operation, 'FORBIDDEN_SESSION', '无权访问该会话。', expose=False)
            try:
                if not parsed:
                    raise ValueError('Invalid JSON')
                request = (CreateSaveRequest if operation == 'archive_create' else VersionRequest).model_validate(raw)
                validate_generation(request.generation)
                if operation == 'archive_restore':
                    save_id = SelectedSave.model_validate({'save_id': save_id}).save_id
            except (ValidationError, ValueError, TypeError):
                return self.failure(connection, event_id, session_id, operation, 'BAD_ARGUMENT', '存档请求字段不符合契约。', state, expose=False)
            normalized = {'operation': operation, **request.model_dump()}
            if operation == 'archive_restore':
                normalized['save_id'] = save_id
            digest = hashlib.sha256(canonical(normalized).encode('utf-8')).hexdigest()
            prior = connection.execute('SELECT request_hash,response_json,http_status,phase FROM action_receipts WHERE session_id=? AND request_id=?', (session_id, request.request_id)).fetchone()
            if prior:
                if prior['request_hash'] != digest:
                    return self.failure(connection, event_id, session_id, operation, 'REQUEST_ID_CONFLICT', '同一请求标识不能替换请求内容。', state, normalized)
                if prior['phase'] != 'completed':
                    return self.failure(connection, event_id, session_id, operation, 'MODEL_UNAVAILABLE', '该请求正在处理或结果未知，不会重复执行。', state)
                body = json.loads(prior['response_json'])
                if body['ok']:
                    body['data'].update(replayed=True, visible_state=self.projection(connection, session_id, state))
                else:
                    body['visible_state'] = self.projection(connection, session_id, state)
                return prior['http_status'], body
            if request.generation != state.generation:
                return self.failure(connection, event_id, session_id, operation, 'STALE_GENERATION', '游戏已重置或恢复，请刷新状态。', state, normalized)
            revision_before = state.revision
            try:
                if request.revision != state.revision:
                    raise RuleError('STALE_STATE', '状态已变化，请刷新后操作存档。')
                if operation == 'archive_create':
                    self.rules.validate_invariants(state)
                    saved_at, archive_id = utc_now(), new_id()
                    snapshot = {'schema_version': self.rules.SCHEMA_VERSION, 'level_version': self.rules.LEVEL_VERSION,
                                'session_id': session_id, 'game_fields': {key: value for key, value in state.model_dump().items() if key in self.rules.game_fields},
                                'saved_at': saved_at}
                    snapshot['checksum'] = checksum(snapshot)
                    slot = {'save_id': archive_id, 'name': request.name or '存档 ' + saved_at[:19].replace('T', ' ') + ' UTC',
                            'saved_at': saved_at, 'schema_version': self.rules.SCHEMA_VERSION, 'level_version': self.rules.LEVEL_VERSION,
                            'source_revision': state.revision, 'source_generation': state.generation,
                            'room_id': state.room_id, 'status': state.status,
                            'clues_found': len(state.discovered_clue_ids), 'kind': 'archive'}
                    connection.execute('INSERT INTO save_slots (save_id,session_id,created_at,snapshot_json,metadata_json) VALUES (?,?,?,?,?)',
                                       (archive_id, session_id, saved_at, canonical(snapshot), canonical(slot)))
                    updated, status, message = state, 201, '已创建独立存档。'
                else:
                    if save_id == 'legacy':
                        row = connection.execute('SELECT snapshot_json FROM saves WHERE session_id=?', (session_id,)).fetchone()
                        slot = self.legacy_slot(connection, session_id)
                    else:
                        row = connection.execute('SELECT snapshot_json,metadata_json FROM save_slots WHERE session_id=? AND save_id=?', (session_id, save_id)).fetchone()
                        slot = json.loads(row['metadata_json']) if row is not None else None
                    if row is None:
                        raise RuleError('SAVE_NOT_FOUND', '没有找到该会话的指定存档。')
                    updated = validate_snapshot(row['snapshot_json'], session_id, state, self.rules)
                    status, message = 200, '已恢复所选存档。'
            except RuleError as error:
                status, body = self.failure(connection, event_id, session_id, operation, error.code, error.message, state, normalized, revision_before=revision_before)
            else:
                if operation == 'archive_restore':
                    connection.execute('UPDATE sessions SET state_json=? WHERE session_id=?', (canonical(updated.model_dump()), session_id))
                    self.invalidate_pending(connection, session_id)
                data = {'request_id': request.request_id, 'replayed': False, 'slot': slot, 'message': message,
                        'visible_state': self.projection(connection, session_id, updated)}
                body = {'ok': True, 'event_id': event_id, 'data': data}
                self.event(connection, event_id, session_id, operation, 'committed', body, updated, normalized, revision_before)
            connection.execute('INSERT INTO action_receipts (session_id,request_id,request_hash,generation,response_json,http_status) VALUES (?,?,?,?,?,?)',
                               (session_id, request.request_id, digest, state.generation, canonical(body), status))
            return status, body
