"""Conservative accounting closure, never a claim of recovered provider usage.

CLI is fixed to the existing canonical ledger. Default: read-only dry-run.
Only Main's fresh, source/dry-run-bound approval can unlock the CLI write path.
reconcile() accepts an existing connection for isolated independent QA; it does
not load approvals, initialize a database, read credentials, or make requests.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sqlite3
import sys
import uuid
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = Path("D:/深度能力")
LEDGER = ROOT / "data/ai-budget.sqlite"
STAGE = ROOT / "evidence/project/stages/v5-conservative-recovery"
APPROVAL = STAGE / "reconciliation-approval.json"
PURPOSE = "v5_conservative_unknown_accounting_closure"
REASON = "HUMAN_ACCEPTED_UPPER_RETAINED"
CAP_UNITS = 10_000_000_000
RETAINED_UNITS = 110_616_000
COLUMNS = ("id", "scope", "created_at", "reserved", "charged", "state",
           "reason", "prompt_tokens", "completion_tokens", "cache_hit_tokens")
TARGETS = (
    ("e0ed1e09d56c43fe99cf554ee98cb8d3", "game", "2026-10-07T07:24:24.341639+00:00",
     27_760_000, 27_760_000, "unknown", "INTERRUPTED_OR_INTERNAL", None, None, None),
    ("d717f047d96542f0b391c7a50f47f994", "game", "2026-10-07T07:34:15.860291+00:00",
     27_760_000, 27_760_000, "unknown", "MODEL_AUTH_ERROR", None, None, None),
    ("d6b0528c32c048efa845e5ae813001b2", "game", "2026-10-18T15:07:18.189412+00:00",
     55_096_000, 55_096_000, "unknown", "MODEL_AUTH_ERROR", None, None, None),
)
TARGET_IDS = frozenset(row[0] for row in TARGETS)
CLOSED = tuple(row[:5] + ("settled", REASON) + row[7:] for row in TARGETS)


class ReconciliationError(ValueError):
    """Safe fixed error code; raw SQLite errors are not published."""


def _require(condition, code):
    if not condition:
        raise ReconciliationError(code)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _digest(value):
    return _sha(_json(value).encode("utf-8"))


def _value(value):
    # Preserve SQLite value types and NULLs, including hypothetical BLOB fields.
    if isinstance(value, bytes):
        return ["blob", value.hex()]
    return [type(value).__name__, value]


def _quote(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def _snapshot(db):
    schema = [tuple(row) for row in db.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name,tbl_name,sql")]
    tables = {}
    for kind, name, _, _ in schema:
        if kind == "table":
            columns = tuple(row[1] for row in db.execute("PRAGMA table_info(" + _quote(name) + ")"))
            rows = [tuple(row) for row in db.execute("SELECT * FROM " + _quote(name))]
            tables[name] = {"columns": columns, "rows": rows}
    return {"schema": schema, "tables": tables}


def _fingerprint(snapshot):
    tables = {}
    for name, data in sorted(snapshot["tables"].items()):
        rows = sorted((_json([_value(v) for v in row]) for row in data["rows"]))
        tables[name] = {"columns": list(data["columns"]), "rows": len(rows),
                        "sha256": _digest(rows)}
    return {"schema_sha256": _digest(snapshot["schema"]), "tables": tables,
            "full_sha256": _digest({"schema": snapshot["schema"], "tables": tables})}


def _same(left, right):
    if left["schema"] != right["schema"] or left["tables"].keys() != right["tables"].keys():
        return False
    for name, data in left["tables"].items():
        other = right["tables"][name]
        encode = lambda rows: sorted(_json([_value(v) for v in row]) for row in rows)
        if data["columns"] != other["columns"] or encode(data["rows"]) != encode(other["rows"]):
            return False
    return True


def _validate(snapshot):
    tables = snapshot["tables"]
    _require("budget_config" in tables and "budget_calls" in tables, "MISSING_LEDGER_TABLES")
    _require(tables["budget_config"]["columns"] == ("id", "cap", "frozen"), "CONFIG_SCHEMA_DRIFT")
    _require(tables["budget_config"]["rows"] == [(1, CAP_UNITS, 0)], "CAP_OR_FROZEN_DRIFT")
    calls = tables["budget_calls"]
    _require(calls["columns"] == COLUMNS, "CALL_SCHEMA_DRIFT")
    rows = calls["rows"]
    by_id = {row[0]: row for row in rows}
    _require(len(by_id) == len(rows), "DUPLICATE_CALL_ID")
    selected = tuple(by_id.get(row[0]) for row in TARGETS)
    _require(selected == TARGETS or selected == CLOSED, "TARGET_DRIFT_OR_PARTIAL_CLOSURE")
    _require(not any(row[0] not in TARGET_IDS and row[5] in ("unknown", "reserved")
                     for row in rows), "OTHER_UNRESOLVED_CALLS")
    _require(all(type(row[3]) is int and type(row[4]) is int and
                 0 <= row[4] <= row[3] for row in rows), "INVALID_EXISTING_AMOUNTS")
    _require(sum(row[4] for row in rows) <= CAP_UNITS, "EXISTING_TOTAL_OVER_CAP")
    _require(sum(row[4] for row in TARGETS) == RETAINED_UNITS, "RETAINED_BOUND_DRIFT")
    return selected == CLOSED


def _proposed(snapshot):
    result = copy.deepcopy(snapshot)
    replacements = {row[0]: row for row in CLOSED}
    result["tables"]["budget_calls"]["rows"] = [
        replacements.get(row[0], row) for row in snapshot["tables"]["budget_calls"]["rows"]]
    return result


def reconcile(connection, apply=False, *, expected_before=None, expected_after=None):
    """Own one transaction; apply=True is intended for QA fixtures or gated CLI.

    Optional fingerprints bind a reviewed dry-run. An exact approved after-state
    is accepted as idempotent; any mixed state or unrelated drift is rejected.
    No filesystem/network access occurs here. Existing outer transactions fail.
    """
    db = connection
    _require(type(apply) is bool, "INVALID_APPLY_FLAG")
    _require(not db.in_transaction, "OUTER_TRANSACTION_FORBIDDEN")
    try:
        db.execute("BEGIN IMMEDIATE" if apply else "BEGIN")
        before = _snapshot(db)
        already_closed = _validate(before)
        proposed = _proposed(before)
        before_fp, proposed_fp = _fingerprint(before), _fingerprint(proposed)
        if expected_before is not None or expected_after is not None:
            _require(expected_before is not None and expected_after is not None,
                     "INCOMPLETE_SNAPSHOT_BINDING")
            _require(before_fp == (expected_after if already_closed else expected_before)
                     and proposed_fp == expected_after, "APPROVED_SNAPSHOT_DRIFT")
        if apply and not already_closed:
            for original in TARGETS:
                cursor = db.execute(
                    "UPDATE budget_calls SET state='settled',reason=? "
                    "WHERE id=? AND scope=? AND created_at=? AND reserved=? AND charged=? "
                    "AND state=? AND reason=? AND prompt_tokens IS NULL "
                    "AND completion_tokens IS NULL AND cache_hit_tokens IS NULL",
                    (REASON, *original[:7]))
                _require(cursor.rowcount == 1, "ATOMIC_TARGET_UPDATE_FAILED")
        after = _snapshot(db)
        _require(_same(after, proposed if apply else before), "UNAPPROVED_LEDGER_CHANGE")
        calls = before["tables"]["budget_calls"]["rows"]
        by_id = {row[0]: row for row in calls}
        after_by_id = {row[0]: row for row in after["tables"]["budget_calls"]["rows"]}
        others = sorted((_json([_value(v) for v in row]) for row in calls
                         if row[0] not in TARGET_IDS))
        result = {
            "purpose": PURPOSE, "mode": "apply" if apply else "dryrun",
            "applied": bool(apply and not already_closed), "already_closed": already_closed,
            "columns": list(COLUMNS), "targets": [list(row) for row in TARGETS],
            "before": [list(by_id[row[0]]) for row in TARGETS],
            "after": [list(after_by_id[row[0]]) for row in TARGETS],
            "proposed_after": [list(row) for row in CLOSED],
            "proposal_status": "ACTUAL_AFTER" if apply else "PROPOSED_NOT_APPLIED",
            "allowed_changes": [] if already_closed else [
                {"id": row[0], "state": {"before": "unknown", "proposed": "settled"},
                 "reason": {"before": row[6], "proposed": REASON}} for row in TARGETS],
            "before_fingerprint": before_fp, "proposed_after_fingerprint": proposed_fp,
            "actual_after_fingerprint": _fingerprint(after), "other_rows_sha256": _digest(others),
            "calls": len(calls), "charged_upper_units": sum(row[4] for row in calls),
            "reserved_units_total": sum(row[3] for row in calls),
            "retained_upper_units": RETAINED_UNITS, "retained_upper_cny": "0.110616",
            "cap_units": CAP_UNITS, "frozen": False,
            "provider_usage_known": False, "provider_invoice_verified": False,
            "accounting_closure_only": True, "network_calls": 0,
        }
        # A closed replay deliberately issues no UPDATE and ends by rollback.
        if apply and not already_closed:
            db.commit()
        else:
            db.rollback()
        return result
    except BaseException:
        db.rollback()
        raise


def _strict_json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            _require(key not in value, "DUPLICATE_JSON_FIELD")
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(
                          ReconciliationError("INVALID_JSON_CONSTANT")))


def _time(value):
    _require(isinstance(value, str), "INVALID_APPROVAL_TIME")
    result = datetime.fromisoformat(value)
    _require(result.tzinfo is not None, "TIMEZONE_REQUIRED")
    return result.astimezone(timezone.utc)


def validate_approval(approval, dryrun_raw, helper_sha, *, now=None):
    """Pure approval validation; returns approved snapshot bindings for the CLI."""
    now = now or datetime.now(timezone.utc)
    _require(approval.get("approved") is True and approval.get("approved_by") == "liy222",
             "EXPLICIT_OWNER_APPROVAL_REQUIRED")
    _require(isinstance(approval.get("human_reply"), str) and approval["human_reply"].strip(),
             "ACTUAL_HUMAN_REPLY_REQUIRED")
    _require(approval.get("purpose") == PURPOSE and approval.get("reason") == REASON,
             "APPROVAL_PURPOSE_MISMATCH")
    _require(approval.get("helper_raw_sha256") == helper_sha, "APPROVAL_SOURCE_MISMATCH")
    _require(approval.get("dryrun_raw_sha256") == _sha(dryrun_raw), "APPROVAL_DRYRUN_MISMATCH")
    _require(approval.get("targets") == [list(row) for row in TARGETS]
             and type(approval.get("retained_upper_units")) is int
             and approval["retained_upper_units"] == RETAINED_UNITS, "APPROVAL_TARGET_MISMATCH")
    issued, expires = _time(approval.get("issued_at_utc")), _time(approval.get("expires_at_utc"))
    _require(issued <= now < expires and expires - issued <= timedelta(hours=24),
             "APPROVAL_EXPIRED_OR_INVALID_WINDOW")
    dryrun = _strict_json(dryrun_raw)
    _require(dryrun.get("status") == "ok" and dryrun.get("mode") == "dryrun"
             and dryrun.get("applied") is False and dryrun.get("purpose") == PURPOSE
             and dryrun.get("helper_raw_sha256") == helper_sha
             and dryrun.get("ledger_relative_path") == "data/ai-budget.sqlite"
             and dryrun.get("targets") == [list(row) for row in TARGETS]
             and dryrun.get("retained_upper_units") == RETAINED_UNITS,
             "INVALID_REVIEWED_DRYRUN")
    _require(approval.get("before_fingerprint") == dryrun.get("before_fingerprint")
             and approval.get("proposed_after_fingerprint") == dryrun.get("proposed_after_fingerprint")
             and isinstance(dryrun.get("before_fingerprint"), dict)
             and isinstance(dryrun.get("proposed_after_fingerprint"), dict),
             "APPROVAL_FINGERPRINT_MISMATCH")
    return dryrun["before_fingerprint"], dryrun["proposed_after_fingerprint"]


def _no_reparse(path):
    for current in (path, *path.parents):
        _require(not current.is_symlink()
                 and not (getattr(current.lstat(), "st_file_attributes", 0) & 0x400),
                 "REPARSE_PATH_FORBIDDEN")


def _load_approval(helper_sha):
    _require(APPROVAL.is_file(), "FIXED_APPROVAL_MISSING")
    _no_reparse(APPROVAL)
    raw = APPROVAL.read_bytes()
    approval = _strict_json(raw)
    relative = approval.get("dryrun_relative_path")
    _require(isinstance(relative, str), "DRYRUN_PATH_REQUIRED")
    dryrun_path = (ROOT / relative).resolve()
    _require(dryrun_path.is_relative_to((STAGE / "runs").resolve())
             and dryrun_path.name == "result.json" and dryrun_path.is_file(),
             "FIXED_STAGE_DRYRUN_REQUIRED")
    _no_reparse(ROOT / relative)
    binding = validate_approval(approval, dryrun_path.read_bytes(), helper_sha)
    return binding, _sha(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Requires fixed Main approval before rw open")
    parser.add_argument("--operator", required=True, help="Actual operator, recorded verbatim; no credentials")
    args = parser.parse_args(argv)
    _require(args.operator.strip() and len(args.operator) <= 80, "OPERATOR_REQUIRED")
    helper_sha = _sha(Path(__file__).read_bytes())
    report = {"recorded_at_utc": datetime.now(timezone.utc).isoformat(),
              "operator": args.operator, "actual_command": [sys.executable, *sys.argv],
              "helper_raw_sha256": helper_sha, "ledger_relative_path": "data/ai-budget.sqlite",
              "network_calls": 0, "database_opened": False, "status": "rejected"}
    output = None
    try:
        _require(ROOT == CANONICAL_ROOT.resolve(), "CANONICAL_ROOT_REQUIRED")
        _require(LEDGER.is_file(), "EXISTING_CANONICAL_LEDGER_REQUIRED")
        _no_reparse(LEDGER)
        # Do all authorization checks before opening a read/write connection.
        binding, approval_sha = _load_approval(helper_sha) if args.apply else ((None, None), None)
        report["approval_raw_sha256"] = approval_sha
        _require(_sha(Path(__file__).read_bytes()) == helper_sha, "SOURCE_CHANGED")
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:12]
        output = STAGE / "runs" / run_id / "result.json"
        output.parent.mkdir(parents=True, exist_ok=False)
        _no_reparse(output.parent)
        mode = "rw" if args.apply else "ro"
        with closing(sqlite3.connect(LEDGER.as_uri() + "?mode=" + mode,
                                    uri=True, isolation_level=None, timeout=15)) as db:
            report["database_opened"] = True
            report["sqlite_open_mode"] = mode
            if not args.apply:
                db.execute("PRAGMA query_only=ON")
            report.update(reconcile(db, args.apply, expected_before=binding[0], expected_after=binding[1]))
        report["status"] = "ok"
    except BaseException as error:
        # Neither SQL exception text nor arbitrary file contents reach evidence/stdout.
        report["error_code"] = str(error) if isinstance(error, ReconciliationError) else "RECONCILIATION_STOP"
        report["error_type"] = type(error).__name__
    if output is None:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:12]
        output = STAGE / "runs" / run_id / "result.json"
        output.parent.mkdir(parents=True, exist_ok=False)
        _no_reparse(output.parent)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(_json({"status": report["status"], "error_code": report.get("error_code"),
                 "output": str(output.relative_to(ROOT)), "applied": report.get("applied", False)}))
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
