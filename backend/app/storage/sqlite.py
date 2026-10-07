import hashlib
import hmac
import json
import secrets
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from pydantic import ValidationError

from .ai import AIStoreMixin
from ..domain.models import ActionRequest, EmptyRequest, GameState, RuleError, TOOL_MODELS, VersionRequest, validate_generation
from ..domain.rules import LEVEL_VERSION, SCHEMA_VERSION, apply_action, validate_invariants, visible_state

ERROR_STATUS = {"BAD_ARGUMENT": 422, "INVALID_TOOL": 422, "FORBIDDEN_SESSION": 403, "SAVE_NOT_FOUND": 404, "INTERNAL_ERROR": 500, "PROPOSAL_NOT_FOUND": 404, "MODEL_UNAVAILABLE": 503, "MODEL_TIMEOUT": 504, "MODEL_INVALID_OUTPUT": 502, "AI_LIMIT_REACHED": 429}
GAME_FIELDS = {"room_id", "inventory", "discovered_clue_ids", "flags", "opened_containers", "status"}
SNAPSHOT_FIELDS = {"schema_version", "level_version", "session_id", "game_fields", "saved_at", "checksum"}
LEGACY_RULES = SimpleNamespace(state_model=GameState, initial_state=GameState,
                              SCHEMA_VERSION=SCHEMA_VERSION, LEVEL_VERSION=LEVEL_VERSION,
                              apply_action=apply_action, validate_invariants=validate_invariants,
                              visible_state=visible_state, tool_models=TOOL_MODELS, game_fields=GAME_FIELDS)


def select_rules(gameplay_version="legacy"):
    if gameplay_version == "legacy":
        return LEGACY_RULES
    if gameplay_version in {"3.1", "3.1.0", "v3.1"}:
        from ..domain import upgrade_rules
        return upgrade_rules
    if gameplay_version in {"3.2", "3.2.0", "v3.2"}:
        from ..domain import puzzle_rules
        return puzzle_rules
    if gameplay_version in {"3.3", "3.3.0", "v3.3"}:
        from ..domain import mini_rules
        return mini_rules
    if gameplay_version in {"upgrade", "3.4", "3.4.0", "v3.4"}:
        from ..domain import graybox_rules
        return graybox_rules
    raise ValueError("Unsupported gameplay version")


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_id() -> str:
    return uuid4().hex


def checksum(snapshot: dict) -> str:
    return hashlib.sha256(canonical({key: value for key, value in snapshot.items() if key != "checksum"}).encode("utf-8")).hexdigest()


def error_body(event_id: str, code: str, message: str, state=None) -> dict:
    return {"ok": False, "event_id": event_id, "error": {"code": code, "message": message}, "visible_state": state}


def validate_snapshot(raw: str, session_id: str, current: GameState, rules=LEGACY_RULES) -> GameState:
    """Validate the entire private snapshot before constructing replacement state."""
    try:
        snapshot = json.loads(raw)
        if not isinstance(snapshot, dict) or set(snapshot) != SNAPSHOT_FIELDS:
            raise ValueError("Invalid snapshot structure")
        if not isinstance(snapshot["schema_version"], str) or not isinstance(snapshot["level_version"], str):
            raise ValueError("Invalid snapshot version")
        # Version mismatches are explicit, never silently migrated.
        if snapshot["schema_version"] != rules.SCHEMA_VERSION or snapshot["level_version"] != rules.LEVEL_VERSION:
            raise RuleError("SNAPSHOT_VERSION_MISMATCH", "存档版本与当前游戏不一致。")
        if snapshot["session_id"] != session_id:
            raise ValueError("Invalid snapshot owner")
        if not isinstance(snapshot["checksum"], str) or not hmac.compare_digest(snapshot["checksum"], checksum(snapshot)):
            raise ValueError("Invalid snapshot checksum")
        saved_at = snapshot["saved_at"]
        if not isinstance(saved_at, str) or not saved_at.endswith("Z") or datetime.fromisoformat(saved_at.replace("Z", "+00:00")).utcoffset().total_seconds() != 0:
            raise ValueError("Invalid snapshot timestamp")
        fields = snapshot["game_fields"]
        if not isinstance(fields, dict) or set(fields) != rules.game_fields:
            raise ValueError("Invalid gameplay fields")
        restored = rules.state_model.model_validate({**fields, "revision": current.revision + 1, "generation": str(uuid4())})
        rules.validate_invariants(restored)
        return restored
    except RuleError:
        raise
    except (ValidationError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
        raise RuleError("INVALID_SNAPSHOT", "存档损坏或不符合游戏规则。") from None


class Store(AIStoreMixin):
    def __init__(self, path: str | Path, *, rules=LEGACY_RULES):
        self.rules = rules
        self.runtime_owner = new_id()
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
                CREATE TABLE IF NOT EXISTS saves (
                    session_id TEXT PRIMARY KEY REFERENCES sessions(session_id),
                    snapshot_json TEXT NOT NULL, summary_json TEXT NOT NULL
                );
            """)

            self.migrate_ai(connection)

    def parse_state(self, raw):
        state = self.rules.state_model.model_validate(json.loads(raw))
        self.rules.validate_invariants(state)
        return state

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

    def projection(self, connection, session_id, state):
        row = connection.execute("SELECT summary_json FROM saves WHERE session_id=?", (session_id,)).fetchone()
        return self.rules.visible_state(session_id, state, json.loads(row["summary_json"]) if row else None)

    def event(self, connection, event_id, session_id, operation, outcome, result, state=None, request=None, revision_before=None):
        connection.execute("""INSERT INTO events
            (event_id,session_id,created_at,operation,outcome,request_json,result_json,revision_before,revision_after,generation)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", (
                event_id, session_id, utc_now(), operation, outcome,
                canonical(request) if request is not None else None, canonical(result),
                revision_before, state.revision if state else None, state.generation if state else None,
            ))

    def failure(self, connection, event_id, session_id, operation, code, message, state=None, request=None, expose=True, revision_before=None):
        body = error_body(event_id, code, message, self.projection(connection, session_id, state) if state and expose else None)
        self.event(connection, event_id, session_id, operation, "rejected", body, state, request, revision_before if revision_before is not None else state.revision if state else None)
        return ERROR_STATUS.get(code, 409), body

    def authenticate(self, connection, session_id, token):
        row = connection.execute("SELECT token_hash,state_json FROM sessions WHERE session_id=?", (session_id,)).fetchone()
        supplied_hash = hashlib.sha256((token or "").encode()).hexdigest()
        expected_hash = row["token_hash"] if row else "0" * 64
        matches = hmac.compare_digest(expected_hash, supplied_hash)
        if not row or not token or not matches:
            return None
        return self.parse_state(row["state_json"])

    def create(self, raw, parsed=True):
        event_id = new_id()
        with self.transaction() as connection:
            try:
                if not parsed:
                    raise ValueError("Invalid JSON")
                EmptyRequest.model_validate(raw)
            except (ValidationError, ValueError, TypeError):
                return self.failure(connection, event_id, None, "create", "BAD_ARGUMENT", "请求必须是空 JSON 对象。", expose=False)
            session_id, token, state = new_id(), secrets.token_urlsafe(32), self.rules.initial_state()
            connection.execute("INSERT INTO sessions VALUES (?,?,?,?)", (session_id, hashlib.sha256(token.encode()).hexdigest(), canonical(state.model_dump()), utc_now()))
            projection = self.projection(connection, session_id, state)
            body = {"ok": True, "event_id": event_id, "data": {"session_id": session_id, "token": token, "visible_state": projection}}
            self.event(connection, event_id, session_id, "create", "committed", {"visible_state": projection}, state)
            return 201, body

    def read(self, session_id, token):
        event_id = new_id()
        with self.transaction() as connection:
            state = self.authenticate(connection, session_id, token)
            if state is None:
                return self.failure(connection, event_id, None, "state", "FORBIDDEN_SESSION", "无权访问该会话。", expose=False)
            return 200, {"ok": True, "event_id": event_id, "data": {"visible_state": self.projection(connection, session_id, state)}}

    def action(self, session_id, token, raw, parsed=True):
        return self.execute(session_id, token, "action", raw, parsed)

    def control(self, session_id, token, operation, raw, parsed=True):
        if operation not in {"save", "reset", "restore"}:
            raise ValueError("Unsupported control operation")
        return self.execute(session_id, token, operation, raw, parsed)

    def execute(self, session_id, token, operation, raw, parsed=True):
        """Shared session/request_id namespace for all versioned mutations.

        Future AI/proposal storage must use this transaction, projection and shared
        receipt namespace rather than introduce a second request_id authority.
        Reset/restore invalidates bound proposals by the new generation even when
        their historical proposal/receipt rows are retained. No T16 dispatcher is
        installed by this module.
        """
        event_id = new_id()
        with self.transaction() as connection:
            state = self.authenticate(connection, session_id, token)
            if state is None:
                return self.failure(connection, event_id, None, operation, "FORBIDDEN_SESSION", "无权访问该会话。", expose=False)
            try:
                if not parsed:
                    raise ValueError("Invalid JSON")
                request = (ActionRequest if operation == "action" else VersionRequest).model_validate(raw)
                validate_generation(request.generation)
                arguments = None
                if operation == "action":
                    if request.tool not in self.rules.tool_models:
                        return self.failure(connection, event_id, session_id, operation, "INVALID_TOOL", "工具不在允许列表中。", state)
                    arguments = self.rules.tool_models[request.tool].model_validate(request.arguments).model_dump()
            except (ValidationError, ValueError, TypeError):
                return self.failure(connection, event_id, session_id, operation, "BAD_ARGUMENT", "请求字段或工具参数不符合契约。", state, expose=False)
            normalized = {"operation": operation, **request.model_dump()}
            if arguments is not None:
                normalized["arguments"] = arguments
            if request.generation != state.generation:
                return self.failure(connection, event_id, session_id, operation, "STALE_GENERATION", "游戏已重置或恢复，请刷新状态。", state, normalized)
            digest = hashlib.sha256(canonical(normalized).encode("utf-8")).hexdigest()
            prior = connection.execute("SELECT request_hash,response_json,http_status FROM action_receipts WHERE session_id=? AND request_id=?", (session_id, request.request_id)).fetchone()
            if prior:
                if prior["request_hash"] != digest:
                    return self.failure(connection, event_id, session_id, operation, "REQUEST_ID_CONFLICT", "同一请求标识不能替换请求内容。", state, normalized)
                body = json.loads(prior["response_json"])
                if body["ok"]:
                    body["data"]["replayed"] = True
                    body["data"]["visible_state"] = self.projection(connection, session_id, state)
                else:
                    body["visible_state"] = self.projection(connection, session_id, state)
                return prior["http_status"], body
            revision_before = state.revision
            try:
                if request.revision != state.revision:
                    raise RuleError("STALE_STATE", "状态已变化，请刷新后重新操作。")
                if operation == "action":
                    updated, result = self.rules.apply_action(state, request.tool, arguments)
                    receipt = {"request_id": request.request_id, "event_id": event_id, "tool": request.tool,
                               "arguments": arguments, "generation": state.generation, "revision_before": revision_before,
                               "revision_after": updated.revision, **result}
                    data = {"receipt": receipt, "replayed": False, "proposal": None}
                else:
                    updated = self.apply_control(connection, session_id, state, operation)
                    data = {"request_id": request.request_id, "replayed": False,
                            "message": {"save": "已保存当前进度。", "reset": "已重新开始，原存档仍可恢复。", "restore": "已恢复存档。"}[operation]}
            except RuleError as error:
                if operation == 'action' and hasattr(self.rules, 'record_mistake'):
                    failed = self.rules.record_mistake(state, request.tool, arguments, error)
                    if failed.revision != state.revision:
                        connection.execute('UPDATE sessions SET state_json=? WHERE session_id=?', (canonical(failed.model_dump()), session_id))
                        self.invalidate_pending(connection, session_id)
                        state = failed
                status, body = self.failure(connection, event_id, session_id, operation, error.code, error.message, state, normalized, revision_before=revision_before)
            else:
                data["visible_state"] = self.projection(connection, session_id, updated)
                body = {"ok": True, "event_id": event_id, "data": data}
                status = 200
                connection.execute("UPDATE sessions SET state_json=? WHERE session_id=?", (canonical(updated.model_dump()), session_id))
                if updated.revision != revision_before or updated.generation != state.generation:
                    self.invalidate_pending(connection, session_id)
                self.event(connection, event_id, session_id, operation, "committed", body, updated, normalized, revision_before)
            connection.execute("INSERT INTO action_receipts (session_id,request_id,request_hash,generation,response_json,http_status) VALUES (?,?,?,?,?,?)", (session_id, request.request_id, digest, state.generation, canonical(body), status))
            return status, body

    def apply_control(self, connection, session_id, state, operation):
        if operation == "save":
            self.rules.validate_invariants(state)
            saved_at = utc_now()
            snapshot = {"schema_version": self.rules.SCHEMA_VERSION, "level_version": self.rules.LEVEL_VERSION,
                        "session_id": session_id, "game_fields": {key: value for key, value in state.model_dump().items() if key in self.rules.game_fields}, "saved_at": saved_at}
            snapshot["checksum"] = checksum(snapshot)
            summary = {"schema_version": self.rules.SCHEMA_VERSION, "level_version": self.rules.LEVEL_VERSION, "saved_at": saved_at,
                       "source_revision": state.revision, "source_generation": state.generation}
            connection.execute("INSERT INTO saves VALUES (?,?,?) ON CONFLICT(session_id) DO UPDATE SET snapshot_json=excluded.snapshot_json,summary_json=excluded.summary_json", (session_id, canonical(snapshot), canonical(summary)))
            return state
        if operation == "reset":
            return self.rules.initial_state(revision=state.revision + 1)
        row = connection.execute("SELECT snapshot_json FROM saves WHERE session_id=?", (session_id,)).fetchone()
        if row is None:
            raise RuleError("SAVE_NOT_FOUND", "尚未保存游戏进度。")
        return validate_snapshot(row["snapshot_json"], session_id, state, self.rules)

