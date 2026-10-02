import hashlib
import hmac
import json
import secrets
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from ..domain.models import ActionRequest, EmptyRequest, GameState, RuleError, TOOL_MODELS, validate_generation
from ..domain.rules import apply_action, validate_invariants, visible_state

ERROR_STATUS = {"BAD_ARGUMENT": 422, "INVALID_TOOL": 422, "FORBIDDEN_SESSION": 403, "INTERNAL_ERROR": 500}


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_id() -> str:
    return uuid4().hex


def error_body(event_id: str, code: str, message: str, state=None) -> dict:
    return {"ok": False, "event_id": event_id, "error": {"code": code, "message": message}, "visible_state": state}


class Store:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path == ":memory:":
            raise ValueError("Use a file-backed SQLite path so requests share state")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY, token_hash TEXT NOT NULL,
                    state_json TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE,
                    session_id TEXT, created_at TEXT NOT NULL, operation TEXT NOT NULL,
                    outcome TEXT NOT NULL, request_json TEXT, result_json TEXT NOT NULL,
                    revision_before INTEGER, revision_after INTEGER, generation TEXT
                );
                CREATE TABLE IF NOT EXISTS action_receipts (
                    session_id TEXT NOT NULL, request_id TEXT NOT NULL,
                    request_hash TEXT NOT NULL, generation TEXT NOT NULL,
                    response_json TEXT NOT NULL, http_status INTEGER NOT NULL,
                    PRIMARY KEY (session_id, request_id)
                );
            """)

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    @contextmanager
    def transaction(self):
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def event(self, connection, event_id, session_id, operation, outcome, result, state=None, request=None, revision_before=None):
        connection.execute("""INSERT INTO events
            (event_id,session_id,created_at,operation,outcome,request_json,result_json,revision_before,revision_after,generation)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", (
                event_id, session_id, utc_now(), operation, outcome,
                canonical(request) if request is not None else None, canonical(result),
                revision_before, state.revision if state else None, state.generation if state else None,
            ))

    def failure(self, connection, event_id, session_id, operation, code, message, state=None, request=None, expose=True):
        body = error_body(event_id, code, message, visible_state(session_id, state) if state and expose else None)
        self.event(connection, event_id, session_id, operation, "rejected", body, state, request, state.revision if state else None)
        return ERROR_STATUS.get(code, 409), body

    def authenticate(self, connection, session_id, token):
        row = connection.execute("SELECT token_hash,state_json FROM sessions WHERE session_id=?", (session_id,)).fetchone()
        supplied_hash = hashlib.sha256((token or "").encode()).hexdigest()
        # A hash is compared even for missing sessions; never log the supplied token.
        expected_hash = row["token_hash"] if row else "0" * 64
        matches = hmac.compare_digest(expected_hash, supplied_hash)
        if not row or not token or not matches:
            return None
        state = GameState.model_validate(json.loads(row["state_json"]))
        validate_invariants(state)
        return state

    def create(self, raw, parsed=True):
        event_id = new_id()
        with self.transaction() as connection:
            try:
                if not parsed:
                    raise ValueError("Invalid JSON")
                EmptyRequest.model_validate(raw)
            except (ValidationError, ValueError, TypeError):
                return self.failure(connection, event_id, None, "create", "BAD_ARGUMENT", "请求必须是空 JSON 对象。", expose=False)
            session_id, token, state = new_id(), secrets.token_urlsafe(32), GameState()
            connection.execute("INSERT INTO sessions VALUES (?,?,?,?)", (session_id, hashlib.sha256(token.encode()).hexdigest(), canonical(state.model_dump()), utc_now()))
            projection = visible_state(session_id, state)
            body = {"ok": True, "event_id": event_id, "data": {"session_id": session_id, "token": token, "visible_state": projection}}
            # The capability is returned exactly once and never copied into persisted events.
            self.event(connection, event_id, session_id, "create", "committed", {"visible_state": projection}, state)
            return 201, body

    def read(self, session_id, token):
        event_id = new_id()
        with self.transaction() as connection:
            state = self.authenticate(connection, session_id, token)
            if state is None:
                return self.failure(connection, event_id, None, "state", "FORBIDDEN_SESSION", "无权访问该会话。", expose=False)
            return 200, {"ok": True, "event_id": event_id, "data": {"visible_state": visible_state(session_id, state)}}

    def action(self, session_id, token, raw, parsed=True):
        event_id = new_id()
        with self.transaction() as connection:
            state = self.authenticate(connection, session_id, token)
            if state is None:
                return self.failure(connection, event_id, None, "action", "FORBIDDEN_SESSION", "无权访问该会话。", expose=False)
            try:
                if not parsed:
                    raise ValueError("Invalid JSON")
                request = ActionRequest.model_validate(raw)
                validate_generation(request.generation)
                if request.tool not in TOOL_MODELS:
                    return self.failure(connection, event_id, session_id, "action", "INVALID_TOOL", "工具不在允许列表中。", state)
                arguments = TOOL_MODELS[request.tool].model_validate(request.arguments).model_dump()
            except (ValidationError, ValueError, TypeError):
                # Do not persist raw invalid values: they might contain secrets or arbitrary payloads.
                return self.failure(connection, event_id, session_id, "action", "BAD_ARGUMENT", "请求字段或工具参数不符合契约。", state, expose=False)
            normalized = {"operation": "action", **request.model_dump(), "arguments": arguments}
            if request.generation != state.generation:
                return self.failure(connection, event_id, session_id, "action", "STALE_GENERATION", "游戏已重置或恢复，请刷新状态。", state, normalized)
            digest = hashlib.sha256(canonical(normalized).encode()).hexdigest()
            prior = connection.execute("SELECT request_hash,response_json,http_status FROM action_receipts WHERE session_id=? AND request_id=?", (session_id, request.request_id)).fetchone()
            if prior:
                if prior["request_hash"] != digest:
                    return self.failure(connection, event_id, session_id, "action", "REQUEST_ID_CONFLICT", "同一请求标识不能替换请求内容。", state, normalized)
                body = json.loads(prior["response_json"])
                if body["ok"]:
                    body["data"]["replayed"] = True
                    body["data"]["visible_state"] = visible_state(session_id, state)
                else:
                    body["visible_state"] = visible_state(session_id, state)
                return prior["http_status"], body
            revision_before = state.revision
            try:
                if request.revision != state.revision:
                    raise RuleError("STALE_STATE", "状态已变化，请刷新后重新操作。")
                updated, result = apply_action(state, request.tool, arguments)
            except RuleError as error:
                status, body = self.failure(connection, event_id, session_id, "action", error.code, error.message, state, normalized)
            else:
                receipt = {"request_id": request.request_id, "event_id": event_id, "tool": request.tool,
                           "arguments": arguments, "generation": state.generation, "revision_before": revision_before,
                           "revision_after": updated.revision, **result}
                body = {"ok": True, "event_id": event_id, "data": {"receipt": receipt, "replayed": False, "proposal": None, "visible_state": visible_state(session_id, updated)}}
                status = 200
                connection.execute("UPDATE sessions SET state_json=? WHERE session_id=?", (canonical(updated.model_dump()), session_id))
                self.event(connection, event_id, session_id, "action", "committed", body, updated, normalized, revision_before)
            connection.execute("INSERT INTO action_receipts VALUES (?,?,?,?,?,?)", (session_id, request.request_id, digest, state.generation, canonical(body), status))
            return status, body
