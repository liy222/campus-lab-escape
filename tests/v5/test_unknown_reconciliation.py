"""Isolated QA for conservative closure of the three historic unknown rows.

All database work here is against a fresh in-memory SQLite connection. These
tests do not open the project ledger or authorize a real accounting apply.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3

import pytest

from scripts import reconcile_v5_unknowns as reconcile


def _memory_ledger():
    db = sqlite3.connect(":memory:", isolation_level=None)
    db.executescript(
        """
        CREATE TABLE budget_config(id INTEGER PRIMARY KEY, cap INTEGER NOT NULL, frozen INTEGER NOT NULL);
        INSERT INTO budget_config VALUES(1, 10000000000, 0);
        CREATE TABLE budget_calls(
          id TEXT PRIMARY KEY, scope TEXT NOT NULL, created_at TEXT NOT NULL,
          reserved INTEGER NOT NULL, charged INTEGER NOT NULL, state TEXT NOT NULL,
          reason TEXT, prompt_tokens INTEGER, completion_tokens INTEGER, cache_hit_tokens INTEGER
        );
        CREATE TABLE qa_metadata(k TEXT PRIMARY KEY, v TEXT NOT NULL);
        INSERT INTO qa_metadata VALUES('fixture', 'synthetic');
        """
    )
    db.executemany(
        "INSERT INTO budget_calls VALUES(?,?,?,?,?,?,?,?,?,?)",
        [*reconcile.TARGETS,
         ("qa-settled", "evaluation", "2026-11-02T00:00:00+00:00", 1000, 750,
          "settled", None, 2, 1, 0)],
    )
    return db


def _snapshot(db):
    return reconcile._snapshot(db)


def test_dryrun_is_read_only_and_proposes_only_three_state_reason_changes():
    db = _memory_ledger()
    before = _snapshot(db)

    result = reconcile.reconcile(db)

    assert result["mode"] == "dryrun"
    assert result["applied"] is False
    assert result["proposal_status"] == "PROPOSED_NOT_APPLIED"
    assert result["retained_upper_units"] == 110_616_000
    assert result["provider_usage_known"] is False
    assert result["provider_invoice_verified"] is False
    assert _snapshot(db) == before
    assert result["before"] == [list(row) for row in reconcile.TARGETS]
    assert result["proposed_after"] == [list(row) for row in reconcile.CLOSED]
    assert all(row[7:] == (None, None, None) for row in reconcile.CLOSED)
    assert result["after"] == result["before"]


def test_apply_changes_only_target_state_and_reason_and_keeps_other_data():
    db = _memory_ledger()
    before = _snapshot(db)
    before_config = db.execute("SELECT * FROM budget_config").fetchall()
    before_other = db.execute("SELECT * FROM qa_metadata").fetchall()

    result = reconcile.reconcile(db, apply=True)

    assert result["applied"] is True
    assert result["after"] == [list(row) for row in reconcile.CLOSED]
    after = _snapshot(db)
    assert after["schema"] == before["schema"]
    assert after["tables"]["budget_config"] == before["tables"]["budget_config"]
    assert after["tables"]["qa_metadata"] == before["tables"]["qa_metadata"]
    assert db.execute("SELECT * FROM budget_config").fetchall() == before_config
    assert db.execute("SELECT * FROM qa_metadata").fetchall() == before_other
    assert sum(row[4] for row in after["tables"]["budget_calls"]["rows"]) == sum(
        row[4] for row in before["tables"]["budget_calls"]["rows"]
    )
    for old, new in zip(reconcile.TARGETS, reconcile.CLOSED):
        assert new[:5] == old[:5]
        assert new[5] == "settled"
        assert new[6] == reconcile.REASON
        assert new[7:] == old[7:] == (None, None, None)


def test_closed_replay_is_idempotent_and_issues_no_update():
    db = _memory_ledger()
    reconcile.reconcile(db, apply=True)
    statements = []
    db.set_trace_callback(statements.append)

    result = reconcile.reconcile(db, apply=True)

    db.set_trace_callback(None)
    assert result["already_closed"] is True
    assert result["applied"] is False
    assert not any(statement.lstrip().upper().startswith("UPDATE ") for statement in statements)


def test_reviewed_snapshot_binding_accepts_exact_pair_and_rejects_unrelated_drift():
    db = _memory_ledger()
    reviewed = reconcile.reconcile(db)
    bound = reconcile.reconcile(
        db, apply=True,
        expected_before=reviewed["before_fingerprint"],
        expected_after=reviewed["proposed_after_fingerprint"],
    )
    assert bound["applied"] is True

    drifted = _memory_ledger()
    drifted.execute("UPDATE qa_metadata SET v='changed' WHERE k='fixture'")
    before = _snapshot(drifted)
    with pytest.raises(reconcile.ReconciliationError, match="APPROVED_SNAPSHOT_DRIFT"):
        reconcile.reconcile(
            drifted, apply=True,
            expected_before=reviewed["before_fingerprint"],
            expected_after=reviewed["proposed_after_fingerprint"],
        )
    assert _snapshot(drifted) == before


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("extra_unknown", "OTHER_UNRESOLVED_CALLS"),
        ("extra_reserved", "OTHER_UNRESOLVED_CALLS"),
        ("frozen", "CAP_OR_FROZEN_DRIFT"),
        ("cap_drift", "CAP_OR_FROZEN_DRIFT"),
        ("over_cap", "EXISTING_TOTAL_OVER_CAP"),
        ("target_scope_drift", "TARGET_DRIFT_OR_PARTIAL_CLOSURE"),
        ("target_partially_closed", "TARGET_DRIFT_OR_PARTIAL_CLOSURE"),
    ],
)
def test_unsafe_or_drifted_ledgers_are_rejected_without_mutation(mutation, expected_code):
    db = _memory_ledger()
    if mutation == "extra_unknown":
        db.execute(
            "INSERT INTO budget_calls VALUES(?,?,?,?,?,?,?,?,?,?)",
            ("unexpected-unknown", "game", "2026-11-01T00:00:00Z", 10, 10,
             "unknown", "UNRESOLVED", None, None, None),
        )
    elif mutation == "extra_reserved":
        db.execute(
            "INSERT INTO budget_calls VALUES(?,?,?,?,?,?,?,?,?,?)",
            ("unexpected-reserved", "experiment", "2026-11-01T00:00:00Z", 10, 10,
             "reserved", None, None, None, None),
        )
    elif mutation == "frozen":
        db.execute("UPDATE budget_config SET frozen=1 WHERE id=1")
    elif mutation == "cap_drift":
        db.execute("UPDATE budget_config SET cap=9999999999 WHERE id=1")
    elif mutation == "over_cap":
        db.execute("UPDATE budget_calls SET reserved=10000000000, charged=10000000000 WHERE id='qa-settled'")
    elif mutation == "target_scope_drift":
        db.execute("UPDATE budget_calls SET scope='evaluation' WHERE id=?", (reconcile.TARGETS[0][0],))
    elif mutation == "target_partially_closed":
        db.execute("UPDATE budget_calls SET state='settled', reason=? WHERE id=?",
                   (reconcile.REASON, reconcile.TARGETS[0][0]))
    before = _snapshot(db)

    with pytest.raises(reconcile.ReconciliationError, match=expected_code):
        reconcile.reconcile(db, apply=True)

    assert _snapshot(db) == before


def test_mid_update_failure_rolls_back_every_target():
    db = _memory_ledger()
    db.executescript(
        """
        CREATE TRIGGER reject_second_target BEFORE UPDATE ON budget_calls
        WHEN OLD.id='d717f047d96542f0b391c7a50f47f994'
        BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END;
        CREATE TRIGGER mutate_unrelated_row AFTER UPDATE ON budget_calls
        WHEN OLD.id='e0ed1e09d56c43fe99cf554ee98cb8d3'
        BEGIN UPDATE qa_metadata SET v='trigger side effect' WHERE k='fixture'; END;
        """
    )
    before = _snapshot(db)

    with pytest.raises(sqlite3.IntegrityError):
        reconcile.reconcile(db, apply=True)

    assert _snapshot(db) == before


def _approval_fixture(now):
    helper_sha = "a" * 64
    before = {"full_sha256": "b" * 64}
    after = {"full_sha256": "c" * 64}
    dryrun = {
        "status": "ok", "mode": "dryrun", "applied": False,
        "purpose": reconcile.PURPOSE, "helper_raw_sha256": helper_sha,
        "ledger_relative_path": "data/ai-budget.sqlite",
        "targets": [list(row) for row in reconcile.TARGETS],
        "retained_upper_units": reconcile.RETAINED_UNITS,
        "before_fingerprint": before, "proposed_after_fingerprint": after,
    }
    raw = json.dumps(dryrun, sort_keys=True, separators=(",", ":")).encode()
    approval = {
        "approved": True, "approved_by": "liy222", "human_reply": "synthetic fixture only",
        "purpose": reconcile.PURPOSE, "reason": reconcile.REASON,
        "helper_raw_sha256": helper_sha,
        "dryrun_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "targets": [list(row) for row in reconcile.TARGETS],
        "retained_upper_units": reconcile.RETAINED_UNITS,
        "issued_at_utc": "2026-11-02T00:00:00+00:00",
        "expires_at_utc": "2026-11-02T01:00:00+00:00",
        "before_fingerprint": before, "proposed_after_fingerprint": after,
    }
    return approval, raw, helper_sha


def test_approval_validation_binds_exact_source_dryrun_targets_and_expiry():
    from datetime import datetime, timezone

    now = datetime(2026, 11, 2, 0, 30, tzinfo=timezone.utc)
    approval, raw, helper_sha = _approval_fixture(now)
    assert reconcile.validate_approval(approval, raw, helper_sha, now=now) == (
        approval["before_fingerprint"], approval["proposed_after_fingerprint"]
    )

    for changed_approval, changed_raw, changed_sha, expected in [
        ({**approval, "helper_raw_sha256": "d" * 64}, raw, helper_sha, "APPROVAL_SOURCE_MISMATCH"),
        (approval, raw + b" ", helper_sha, "APPROVAL_DRYRUN_MISMATCH"),
        ({**approval, "targets": []}, raw, helper_sha, "APPROVAL_TARGET_MISMATCH"),
    ]:
        with pytest.raises(reconcile.ReconciliationError, match=expected):
            reconcile.validate_approval(changed_approval, changed_raw, changed_sha, now=now)

    with pytest.raises(reconcile.ReconciliationError, match="APPROVAL_EXPIRED_OR_INVALID_WINDOW"):
        reconcile.validate_approval(approval, raw, helper_sha, now=now.replace(hour=2))


def test_apply_cli_without_fixed_approval_rejects_before_rw_open(tmp_path, monkeypatch):
    db_path = tmp_path / "data" / "ai-budget.sqlite"
    db_path.parent.mkdir()
    db_path.touch()
    stage = tmp_path / "evidence" / "project" / "stages" / "v5-conservative-recovery"
    stage.mkdir(parents=True)
    monkeypatch.setattr(reconcile, "ROOT", tmp_path)
    monkeypatch.setattr(reconcile, "CANONICAL_ROOT", tmp_path)
    monkeypatch.setattr(reconcile, "LEDGER", db_path)
    monkeypatch.setattr(reconcile, "STAGE", stage)
    monkeypatch.setattr(reconcile, "APPROVAL", stage / "reconciliation-approval.json")
    original_connect = sqlite3.connect
    opened_modes = []

    def observe_connect(database, *args, **kwargs):
        uri = str(database)
        if "mode=rw" in uri:
            opened_modes.append("rw")
        return original_connect(database, *args, **kwargs)

    monkeypatch.setattr(reconcile.sqlite3, "connect", observe_connect)

    assert reconcile.main(["--apply", "--operator", "synthetic QA fixture"]) == 1

    assert opened_modes == []
    outputs = list((stage / "runs").glob("*/result.json"))
    assert len(outputs) == 1
    public = json.loads(outputs[0].read_text(encoding="utf-8"))
    assert public["error_code"] == "FIXED_APPROVAL_MISSING"
    assert public["database_opened"] is False
    assert public["network_calls"] == 0
