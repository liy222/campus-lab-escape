"""Shared, fail-closed CNY budget; no prompts, credentials or raw errors stored."""
from __future__ import annotations

import re
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROJECT_LEDGER = PROJECT_ROOT / "data" / "ai-budget.sqlite"
CAP_UNITS = 10_000_000_000  # One unit = 1e-9 CNY; approved project total = CNY 10.
INPUT_MISS_UNITS = 2_000
INPUT_HIT_UNITS = 40
OUTPUT_UNITS = 8_000


class BudgetError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def cost_units(prompt_tokens: int, completion_tokens: int, cache_hit_tokens: int = 0) -> int:
    if any(type(n) is not int or n < 0 for n in (prompt_tokens, completion_tokens, cache_hit_tokens)) or cache_hit_tokens > prompt_tokens:
        raise BudgetError("INVALID_USAGE")
    return (prompt_tokens - cache_hit_tokens) * INPUT_MISS_UNITS + cache_hit_tokens * INPUT_HIT_UNITS + completion_tokens * OUTPUT_UNITS


class BudgetLedger:
    """All processes must use the same path. Pending/crashed calls stay charged."""

    def __init__(self, path: Path = PROJECT_LEDGER, *, cap_units: int = CAP_UNITS):
        if type(cap_units) is not int or not 0 < cap_units <= CAP_UNITS:
            raise BudgetError("INVALID_BUDGET_CAP")
        self.path = Path(path).resolve()
        self.cap_units = cap_units
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS budget_config (id INTEGER PRIMARY KEY CHECK(id=1), cap INTEGER NOT NULL, frozen INTEGER NOT NULL DEFAULT 0)")
            db.execute("CREATE TABLE IF NOT EXISTS budget_calls (id TEXT PRIMARY KEY, scope TEXT NOT NULL, created_at TEXT NOT NULL, reserved INTEGER NOT NULL, charged INTEGER NOT NULL, state TEXT NOT NULL, reason TEXT, prompt_tokens INTEGER, completion_tokens INTEGER, cache_hit_tokens INTEGER)")
            db.execute("INSERT OR IGNORE INTO budget_config(id,cap) VALUES(1,?)", (cap_units,))
            if db.execute("SELECT cap FROM budget_config WHERE id=1").fetchone()[0] != cap_units:
                raise BudgetError("BUDGET_CONFIG_MISMATCH")
            db.commit()

    def _connect(self):
        return sqlite3.connect(self.path, timeout=15, isolation_level=None)

    def reserve(self, scope: str, maximum_units: int, *, call_id: str | None = None) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", scope) or type(maximum_units) is not int or maximum_units <= 0:
            raise BudgetError("INVALID_RESERVATION")
        call_id = call_id or uuid.uuid4().hex
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", call_id):
            raise BudgetError("INVALID_CALL_ID")
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            cap, frozen = db.execute("SELECT cap,frozen FROM budget_config WHERE id=1").fetchone()
            charged = db.execute("SELECT COALESCE(SUM(charged),0) FROM budget_calls").fetchone()[0]
            if frozen or charged + maximum_units > cap:
                raise BudgetError("AI_BUDGET_EXHAUSTED")
            if scope == "probe":
                probe_charged = db.execute("SELECT COALESCE(SUM(charged),0) FROM budget_calls WHERE scope='probe'").fetchone()[0]
                if maximum_units > 100_000_000 or probe_charged + maximum_units > 200_000_000:
                    raise BudgetError("PROBE_BUDGET_EXHAUSTED")
            try:
                db.execute("INSERT INTO budget_calls(id,scope,created_at,reserved,charged,state) VALUES(?,?,?,?,?,'reserved')", (call_id, scope, datetime.now(timezone.utc).isoformat(), maximum_units, maximum_units))
            except sqlite3.IntegrityError:
                raise BudgetError("DUPLICATE_CALL_ID") from None
            db.commit()
        return call_id

    def settle(self, call_id: str, *, prompt_tokens: int, completion_tokens: int, cache_hit_tokens: int = 0) -> int:
        measured = cost_units(prompt_tokens, completion_tokens, cache_hit_tokens)
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT reserved,state,charged,prompt_tokens,completion_tokens,cache_hit_tokens FROM budget_calls WHERE id=?", (call_id,)).fetchone()
            if row is None:
                raise BudgetError("UNKNOWN_CALL_ID")
            reserved, state, charged, *previous = row
            if state == "settled":
                if previous != [prompt_tokens, completion_tokens, cache_hit_tokens]:
                    raise BudgetError("SETTLEMENT_CONFLICT")
                return charged
            if state != "reserved":
                raise BudgetError("SETTLEMENT_CONFLICT")
            overrun = measured > reserved
            db.execute("UPDATE budget_calls SET charged=?,state='settled',reason=?,prompt_tokens=?,completion_tokens=?,cache_hit_tokens=? WHERE id=?", (measured, "BOUND_EXCEEDED" if overrun else None, prompt_tokens, completion_tokens, cache_hit_tokens, call_id))
            if overrun:
                db.execute("UPDATE budget_config SET frozen=1 WHERE id=1")
            db.commit()
        if overrun:
            raise BudgetError("COST_BOUND_EXCEEDED")
        return measured

    def retain(self, call_id: str, reason: str) -> None:
        if not re.fullmatch(r"[A-Z_]{1,64}", reason):
            raise BudgetError("INVALID_REASON")
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE budget_calls SET state='unknown',reason=? WHERE id=? AND state='reserved'", (reason, call_id))
            db.commit()

    def snapshot(self) -> dict:
        with closing(self._connect()) as db:
            cap, frozen = db.execute("SELECT cap,frozen FROM budget_config WHERE id=1").fetchone()
            charged, calls = db.execute("SELECT COALESCE(SUM(charged),0),COUNT(*) FROM budget_calls").fetchone()
            pending = db.execute("SELECT COUNT(*) FROM budget_calls WHERE state IN ('reserved','unknown')").fetchone()[0]
        return {"cap_cny": cap / 1e9, "charged_upper_cny": charged / 1e9, "remaining_cny": max(0, cap-charged) / 1e9, "calls": calls, "unknown_or_pending_calls": pending, "frozen": bool(frozen)}

    def freeze(self) -> None:
        """Fail closed if provider usage/model violates the approved estimate."""
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE budget_config SET frozen=1 WHERE id=1")
            db.commit()
