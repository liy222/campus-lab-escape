"""Local opt-in sharing and transaction-bound challenge accounting.

Definitions and snapshots remain in their original tables and formats. Only
authorised shared-session links grant access to an author's frozen definition.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .sqlite import canonical, new_id

LOG = logging.getLogger(__name__)
MIGRATION_KEY = 'sharing_schema_version'


def now_ms():
    return int(time.time() * 1000)


def timestamp(milliseconds):
    return datetime.fromtimestamp(milliseconds / 1000, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def audit(connection, operation, *, session_id=None, **fields):
    """Safe IDs and counters only; no definitions, answers, requests or auth data."""
    allowed = {'share_id', 'level_id', 'attempt_id', 'user_id', 'published', 'revision',
               'status', 'elapsed_ms', 'hint_count', 'companion_count', 'existing'}
    if not fields.keys() <= allowed:
        raise ValueError('UNSAFE_SHARING_EVENT_FIELD')
    connection.execute('''INSERT INTO events(event_id,session_id,created_at,operation,outcome,result_json)
        VALUES(?,?,?,?,?,?)''', (new_id(), session_id, timestamp(now_ms()), operation, 'committed', canonical({'ok': True, 'data': fields})))


def backup_before_upgrade(path):
    """Existing V5 only; SQLite backup includes WAL and precedes all migrations."""
    target = Path(path)
    if not target.exists() or not target.stat().st_size:
        return
    with closing(sqlite3.connect(target.resolve().as_uri() + '?mode=ro', uri=True)) as source:
        tables = {row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'v5_metadata' not in tables or source.execute("SELECT value FROM v5_metadata WHERE key='database_version'").fetchone() != ('5',):
            raise ValueError('Refusing existing non-v5 database')
        marker = source.execute('SELECT value FROM v5_metadata WHERE key=?', (MIGRATION_KEY,)).fetchone()
        if marker:
            if marker != ('1',):
                raise ValueError('Unsupported sharing database version')
            return
        directory = target.parent / 'backups'
        directory.mkdir(parents=True, exist_ok=True)
        backup = directory / (target.stem + '-sharing-v1-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + new_id() + '.sqlite')
        with closing(sqlite3.connect(backup)) as destination:
            source.backup(destination)
        LOG.info('V5_SHARING_BACKUP_CREATED')


def migrate(connection):
    marker = connection.execute('SELECT value FROM v5_metadata WHERE key=?', (MIGRATION_KEY,)).fetchone()
    if marker:
        if marker[0] != '1':
            raise ValueError('Unsupported sharing database version')
        return
    statements = [
        '''CREATE TABLE shared_levels (
            share_id TEXT PRIMARY KEY, level_id TEXT NOT NULL UNIQUE REFERENCES generated_levels(level_id),
            author_id TEXT NOT NULL REFERENCES users(user_id), definition_hash TEXT NOT NULL,
            published INTEGER NOT NULL CHECK(published IN (0,1)), revision INTEGER NOT NULL,
            published_at TEXT NOT NULL)''',
        '''CREATE TABLE shared_sessions (
            session_id TEXT PRIMARY KEY REFERENCES sessions(session_id),
            share_id TEXT NOT NULL REFERENCES shared_levels(share_id),
            user_id TEXT NOT NULL REFERENCES users(user_id), current_attempt_id TEXT NOT NULL,
            UNIQUE(share_id,user_id))''',
        '''CREATE TABLE challenge_attempts (
            attempt_id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES shared_sessions(session_id),
            share_id TEXT NOT NULL REFERENCES shared_levels(share_id), user_id TEXT NOT NULL REFERENCES users(user_id),
            status TEXT NOT NULL CHECK(status IN ('active','practice','finished')),
            started_ms INTEGER NOT NULL, started_at TEXT NOT NULL, finished_at TEXT,
            elapsed_ms INTEGER CHECK(elapsed_ms>=0), hint_count INTEGER NOT NULL DEFAULT 0,
            companion_count INTEGER NOT NULL DEFAULT 0)''',
        '''CREATE TABLE shared_save_origins (
            session_id TEXT NOT NULL REFERENCES shared_sessions(session_id), save_id TEXT NOT NULL,
            attempt_id TEXT NOT NULL REFERENCES challenge_attempts(attempt_id),
            PRIMARY KEY(session_id,save_id))''',
        'CREATE INDEX challenge_ranking ON challenge_attempts(share_id,status,elapsed_ms,finished_at,attempt_id)',
        'CREATE INDEX shared_joined ON shared_sessions(user_id,share_id)',
    ]
    for statement in statements:
        connection.execute(statement)
    connection.execute('INSERT INTO v5_metadata VALUES(?,?)', (MIGRATION_KEY, '1'))
    LOG.info('V5_SHARING_MIGRATION_COMPLETED')


def sharing_state(connection, level_id):
    row = connection.execute('SELECT * FROM shared_levels WHERE level_id=?', (level_id,)).fetchone()
    return ({'share_id': row['share_id'], 'published': bool(row['published']), 'revision': row['revision'], 'published_at': row['published_at']}
            if row else {'share_id': None, 'published': False, 'revision': 0, 'published_at': None})


def current_attempt(connection, session_id):
    return connection.execute('''SELECT a.*,l.author_id FROM shared_sessions s
        JOIN challenge_attempts a ON a.attempt_id=s.current_attempt_id AND a.session_id=s.session_id
        JOIN shared_levels l ON l.share_id=s.share_id WHERE s.session_id=?''', (session_id,)).fetchone()


def challenge_projection(connection, session_id):
    row = current_attempt(connection, session_id)
    if row is None:
        return None
    return {key: row[key] for key in ('attempt_id', 'status', 'started_at', 'finished_at', 'elapsed_ms', 'hint_count', 'companion_count')} | {'is_author': row['user_id'] == row['author_id']}


def new_attempt(connection, session_id, *, status='active'):
    link = connection.execute('SELECT * FROM shared_sessions WHERE session_id=?', (session_id,)).fetchone()
    instant, attempt_id = now_ms(), new_id()
    connection.execute('''INSERT INTO challenge_attempts
        (attempt_id,session_id,share_id,user_id,status,started_ms,started_at)
        VALUES(?,?,?,?,?,?,?)''', (attempt_id, session_id, link['share_id'], link['user_id'], status, instant, timestamp(instant)))
    connection.execute('UPDATE shared_sessions SET current_attempt_id=? WHERE session_id=?', (attempt_id, session_id))
    audit(connection, 'challenge_start', session_id=session_id, share_id=link['share_id'], user_id=link['user_id'], attempt_id=attempt_id, status=status, hint_count=0, companion_count=0)
    return attempt_id


def after_mutation(connection, session_id, operation, before, after, save_id=None):
    row = current_attempt(connection, session_id)
    if row is None:
        raise ValueError('SHARED_ATTEMPT_MISSING')
    aid = row['attempt_id']
    if operation in {'archive_create', 'save'}:
        connection.execute('''INSERT INTO shared_save_origins VALUES(?,?,?)
            ON CONFLICT(session_id,save_id) DO UPDATE SET attempt_id=excluded.attempt_id''',
            (session_id, save_id or 'legacy', aid))
    elif operation == 'archive_delete':
        connection.execute('DELETE FROM shared_save_origins WHERE session_id=? AND save_id=?', (session_id, save_id))
    elif operation in {'archive_restore', 'restore'}:
        origin = connection.execute('SELECT attempt_id FROM shared_save_origins WHERE session_id=? AND save_id=?', (session_id, save_id or 'legacy')).fetchone()
        eligible = row['status'] == 'active' and origin and origin['attempt_id'] == aid and after.status == 'playing'
        if not eligible:
            if row['status'] == 'finished':
                new_attempt(connection, session_id, status='practice')
            else:
                connection.execute("UPDATE challenge_attempts SET status='practice' WHERE attempt_id=?", (aid,))
            current = current_attempt(connection, session_id)
            audit(connection, 'challenge_practice', session_id=session_id, share_id=row['share_id'], attempt_id=current['attempt_id'], status='practice', hint_count=current['hint_count'], companion_count=current['companion_count'])
    elif operation == 'reset':
        if row['status'] != 'finished':
            connection.execute("UPDATE challenge_attempts SET status='practice',finished_at=? WHERE attempt_id=?", (timestamp(now_ms()), aid))
            audit(connection, 'challenge_practice', session_id=session_id, share_id=row['share_id'], attempt_id=aid, status='practice', hint_count=row['hint_count'], companion_count=row['companion_count'])
        new_attempt(connection, session_id)
    elif operation == 'action' and before.status == 'playing' and after.status == 'won' and row['status'] == 'active':
        instant = now_ms()
        connection.execute("UPDATE challenge_attempts SET status='finished',finished_at=?,elapsed_ms=? WHERE attempt_id=? AND status='active'",
                           (timestamp(instant), max(0, instant-row['started_ms']), aid))
        audit(connection, 'challenge_finish', session_id=session_id, share_id=row['share_id'], attempt_id=aid, status='finished', elapsed_ms=max(0,instant-row['started_ms']), hint_count=row['hint_count'], companion_count=row['companion_count'])
        LOG.info('V5_SHARED_CHALLENGE_FINISHED')


def count_assistance(connection, session_id, *, hint=False, companion=False):
    row = current_attempt(connection, session_id)
    if row is not None and row['status'] != 'finished':
        connection.execute('UPDATE challenge_attempts SET hint_count=hint_count+?,companion_count=companion_count+? WHERE attempt_id=?',
                           (int(hint), int(companion), row['attempt_id']))
        if hint or companion:
            audit(connection, 'challenge_assistance', session_id=session_id, share_id=row['share_id'], attempt_id=row['attempt_id'], status=row['status'], hint_count=row['hint_count']+int(hint), companion_count=row['companion_count']+int(companion))


class SharingDatabaseMixin:
    def set_sharing(self, uid, level_id, published, revision):
        with self.transaction() as c:
            level = c.execute('SELECT * FROM generated_levels WHERE level_id=? AND user_id=?', (level_id, uid)).fetchone()
            if level is None:
                return 404, {'code': 'NOT_FOUND', 'message': '未找到该关卡。'}
            existing = sharing_state(c, level_id)
            if existing['revision'] != revision:
                return 409, {'code': 'STALE_SHARING', 'message': '共享状态已变化，请刷新后操作。'}
            self.load_compiled(level)
            if existing['share_id']:
                c.execute('UPDATE shared_levels SET published=?,revision=revision+1 WHERE level_id=?', (int(published), level_id))
            elif published:
                c.execute('INSERT INTO shared_levels VALUES(?,?,?,?,?,1,?)', (new_id(), level_id, uid, level['definition_hash'], 1, timestamp(now_ms())))
            # Cancelling an unpublished level is a stable no-op with revision 0.
            LOG.info('V5_SHARING_PUBLISHED' if published else 'V5_SHARING_CANCELLED')
            result = sharing_state(c, level_id)
            audit(c, 'sharing_publish' if published else 'sharing_unpublish', share_id=result['share_id'], level_id=level_id, user_id=uid, published=published, revision=result['revision'])
            return 200, {'sharing': result}

    def _accessible_share(self, c, uid, share_id):
        return c.execute('''SELECT l.*,u.username AS author_username,g.metadata_json,j.theme
            FROM shared_levels l JOIN users u ON u.user_id=l.author_id
            JOIN generated_levels g ON g.level_id=l.level_id AND g.user_id=l.author_id
            LEFT JOIN level_generations j ON j.job_id=g.job_id AND j.user_id=g.user_id AND j.level_id=g.level_id
            WHERE l.share_id=? AND (l.published=1 OR l.author_id=? OR EXISTS(
                SELECT 1 FROM shared_sessions s WHERE s.share_id=l.share_id AND s.user_id=?))''', (share_id, uid, uid)).fetchone()

    def _shared_public(self, c, uid, row):
        result = json.loads(row['metadata_json'])
        if row['theme'] is not None:
            result['theme'] = row['theme']
        link = c.execute('''SELECT s.session_id,g.state_json,a.status AS challenge_status
            FROM shared_sessions s JOIN sessions g ON g.session_id=s.session_id
            JOIN challenge_attempts a ON a.attempt_id=s.current_attempt_id
            WHERE s.share_id=? AND s.user_id=?''', (row['share_id'], uid)).fetchone()
        result.update(share_id=row['share_id'], author_username=row['author_username'], is_author=uid == row['author_id'],
                      published=bool(row['published']), sharing_revision=row['revision'], published_at=row['published_at'],
                      session_id=link['session_id'] if link else None,
                      status=json.loads(link['state_json'])['status'] if link else None,
                      challenge_status=link['challenge_status'] if link else None)
        return result

    def shared_detail(self, uid, share_id):
        with self.transaction() as c:
            row = self._accessible_share(c, uid, share_id)
            return self._shared_public(c, uid, row) if row else None

    def shared_levels(self, uid, view='hall', page=1):
        with self.transaction() as c:
            predicate = 'l.published=1' if view == 'hall' else 'EXISTS(SELECT 1 FROM shared_sessions s WHERE s.share_id=l.share_id AND s.user_id=?)'
            args = () if view == 'hall' else (uid,)
            total = c.execute('SELECT COUNT(*) FROM shared_levels l WHERE ' + predicate, args).fetchone()[0]
            rows = c.execute('SELECT l.share_id FROM shared_levels l WHERE ' + predicate + ' ORDER BY l.published_at DESC,l.share_id ASC LIMIT 20 OFFSET ?', (*args, (page-1)*20)).fetchall()
            return {'shared_levels': [self._shared_public(c, uid, self._accessible_share(c, uid, row['share_id'])) for row in rows], 'page': page, 'page_size': 20, 'total': total}

    def join_shared(self, principal, share_id, request):
        from ..domain.generated import GeneratedRules
        uid = principal['user_id']
        hashed = hashlib.sha256(canonical({'operation': 'join_shared', 'share_id': share_id, **request.model_dump()}).encode()).hexdigest()
        with self.transaction() as c:
            share = self._accessible_share(c, uid, share_id)
            if share is None:
                return 404, {'code': 'NOT_FOUND', 'message': '未找到该共享关卡。'}
            existing = c.execute('SELECT session_id FROM shared_sessions WHERE share_id=? AND user_id=?', (share_id, uid)).fetchone()
            if not share['published'] and not existing:
                return 404, {'code': 'NOT_FOUND', 'message': '该关卡已取消共享，无法新加入。'}
            prior = c.execute('SELECT * FROM session_requests WHERE user_id=? AND request_id=?', (uid, request.request_id)).fetchone()
            if prior:
                if prior['request_hash'] != hashed:
                    return 409, {'code': 'REQUEST_ID_CONFLICT', 'message': '同一请求标识不能更改内容。'}
                return 200, {'session_id': prior['session_id'], 'existing': True, 'share_id': share_id}
            level = c.execute('SELECT * FROM generated_levels WHERE level_id=? AND user_id=?', (share['level_id'], share['author_id'])).fetchone()
            if level['definition_hash'] != share['definition_hash']:
                raise ValueError('DEFINITION_HASH')
            compiled = self.load_compiled(level)
            if existing:
                sid, exists = existing['session_id'], True
            else:
                sid, exists = new_id(), False
                state = GeneratedRules(compiled, owner_id=uid, level_id=share['level_id']).initial_state()
                created = timestamp(now_ms())
                c.execute('INSERT INTO sessions VALUES(?,?,?,?)', (sid, new_id(), canonical(state.model_dump()), created))
                c.execute('INSERT INTO session_owners VALUES(?,?,?,?,?)', (sid, uid, 'shared', share['level_id'], created))
                c.execute('INSERT INTO shared_sessions VALUES(?,?,?,?)', (sid, share_id, uid, ''))
                new_attempt(c, sid)
            c.execute('INSERT INTO session_requests VALUES(?,?,?,?)', (uid, request.request_id, hashed, sid))
            audit(c, 'sharing_join', session_id=sid, share_id=share_id, user_id=uid, existing=exists)
            return 200 if exists else 201, {'session_id': sid, 'existing': exists, 'share_id': share_id}

    def leaderboard(self, uid, share_id):
        with self.transaction() as c:
            share = self._accessible_share(c, uid, share_id)
            if share is None:
                return None
            rows = c.execute('''WITH best AS (
                SELECT a.*,ROW_NUMBER() OVER(PARTITION BY a.user_id ORDER BY a.elapsed_ms,a.finished_at,a.attempt_id) AS choice
                FROM challenge_attempts a WHERE a.share_id=? AND a.status='finished' AND a.elapsed_ms IS NOT NULL
            ), ranked AS (
                SELECT *,ROW_NUMBER() OVER(ORDER BY elapsed_ms,finished_at,attempt_id) AS rank FROM best WHERE choice=1
            ) SELECT r.*,u.username FROM ranked r JOIN users u ON u.user_id=r.user_id ORDER BY r.rank''', (share_id,)).fetchall()
            def public(row):
                return {key: row[key] for key in ('rank', 'attempt_id', 'username', 'elapsed_ms', 'finished_at', 'hint_count', 'companion_count')} | {'is_author': row['user_id'] == share['author_id']}
            return {'share_id': share_id, 'entries': [public(row) for row in rows[:50]],
                    'own_entry': next((public(row) for row in rows if row['user_id'] == uid), None), 'total_players': len(rows)}
