"""Isolated QA for V5 paid-recovery gates and the free wire preview.

Every paid-path dispatch in this module is a local fake. The real production
ledger, credential environment, PaidProvider transport, and network are never
used. Registered V5 evidence is read-only input for the evaluator context.
"""
from __future__ import annotations

import asyncio
import copy
import json
import sqlite3
from types import SimpleNamespace

import pytest

from evaluation import v5
from evaluation import provider as provider_module
from evaluation.common import EvaluationError
from evaluation.provider import CAP, Suggestion, cost_units
from scripts import preview_v5_evaluation as preview


APPROVAL_ID = "synthetic-qa-gate"
INPUT_HASH = "a" * 64
GATE_HASH = "b" * 64


@pytest.fixture(scope="module")
def registered_v5():
    """Load only the registered evaluator inputs; never opens the budget DB."""
    return v5.load_v5()


class _ForbiddenEnvironment:
    def __init__(self):
        self.reads = 0

    def get(self, *args, **kwargs):
        self.reads += 1
        raise AssertionError("QA fake path must not read credentials")

    def __getitem__(self, _key):
        self.reads += 1
        raise AssertionError("QA fake path must not read credentials")


def _guard_credentials(monkeypatch, env):
    # Isolate only the evaluator/provider module globals. Never replace the
    # process-wide os.environ used by pytest, Python, or unrelated libraries.
    monkeypatch.setattr(v5, "os", SimpleNamespace(environ=env), raising=False)
    monkeypatch.setattr(provider_module, "os", SimpleNamespace(environ=env))


class _FakeLedger:
    def __init__(self, *, ready_error=None, remaining=10_000_000_000, rows=(),
                 frozen=False, cap=CAP):
        self.ready_error = ready_error
        self.remaining = remaining
        self.rows = list(rows)
        self.frozen = frozen
        self.cap = cap
        self.assert_ready_calls = 0
        self.connect_calls = 0

    def assert_ready(self):
        self.assert_ready_calls += 1
        if self.ready_error:
            raise EvaluationError(self.ready_error)
        if self.frozen or self.cap != CAP or self.remaining <= 0:
            raise EvaluationError("AI_BUDGET_EXHAUSTED")
        if any(state in {"unknown", "reserved"} for _scope, _id, _charged, state in self.rows):
            raise EvaluationError("PRIOR_CALL_UNKNOWN_STOP")
        return {"remaining_units": self.remaining}

    def _connect(self):
        self.connect_calls += 1
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE budget_calls(scope TEXT, id TEXT, charged INTEGER, state TEXT)")
        db.executemany("INSERT INTO budget_calls VALUES(?,?,?,?)", self.rows)
        return db


class _FakePaidProvider:
    """Scripted local transport facade; it never reads env or opens HTTP."""

    scripts = []
    instances = []

    def __init__(self, gate, input_hash):
        self.gate = copy.deepcopy(gate)
        self.input_hash = input_hash
        self.calls = 0
        self.last_metadata = None
        self.instances.append(self)

    async def complete(self, messages):
        self.calls += 1
        action = self.scripts.pop(0) if self.scripts else "pass"
        claim = json.loads(messages[1]["content"])["TARGET_DATA"]["claim"]
        if action == "raise":
            raise RuntimeError("synthetic provider failure")
        status = action if action in {"PASS", "FAIL", "INSUFFICIENT_EVIDENCE"} else "PASS"
        refs = copy.deepcopy(claim["evidence_refs"])
        if action == "invalid_reference":
            refs = [{"evidence_id": "synthetic:unread", "snippet": "summary"}]
        suggestion = {
            "claim_id": claim["claim_id"], "release_id": claim["release_id"],
            "status": status, "evidence_refs": refs,
            "reason": "Synthetic QA response only; no model judgement was requested.",
            "missing_check": ["Synthetic missing item"] if status == "INSUFFICIENT_EVIDENCE" else [],
        }
        self.last_metadata = {
            "mode": "fake", "actual_network_call": False, "call_id": None,
            "usage": None, "requested_model": "synthetic", "cost_upper_units": None,
        }
        return Suggestion(json.dumps(suggestion, ensure_ascii=False), copy.deepcopy(self.last_metadata))


@pytest.fixture
def paid_fakes(monkeypatch):
    counts = {"binding": 0, "gate": 0, "ledger_init": 0, "provider_init": 0}
    binding = {
        "binding_version": "v5-paid-input-v1", "registration_raw_sha256": "c" * 64,
        "evaluator_sources": {"synthetic-source.py": "d" * 64}, "input_sha256": INPUT_HASH,
    }
    gate = {
        "approval_id": APPROVAL_ID, "input_sha256": INPUT_HASH, "max_calls": 3,
        "max_cost_units": 9_000_000_000, "max_tokens": 1000, "timeout_seconds": 20,
        "expires_at": "2099-01-01T00:00:00+00:00",
    }
    ledger = _FakeLedger()
    env = _ForbiddenEnvironment()

    def read_binding():
        counts["binding"] += 1
        return copy.deepcopy(binding)

    def read_gate(approval_id, input_hash):
        counts["gate"] += 1
        assert approval_id == APPROVAL_ID
        assert input_hash == INPUT_HASH
        return copy.deepcopy(gate), GATE_HASH

    def new_ledger():
        counts["ledger_init"] += 1
        return ledger

    class FakeProvider(_FakePaidProvider):
        scripts = []
        instances = []

        def __init__(self, provider_gate, input_hash):
            counts["provider_init"] += 1
            super().__init__(provider_gate, input_hash)

    FakeProvider.scripts = []
    FakeProvider.instances = []
    monkeypatch.setattr(v5, "paid_input_binding", read_binding)
    monkeypatch.setattr(v5, "fixed_paid_gate", read_gate)
    monkeypatch.setattr(v5, "ExistingLedger", new_ledger)
    monkeypatch.setattr(v5, "PaidProvider", FakeProvider)
    _guard_credentials(monkeypatch, env)
    return {"counts": counts, "binding": binding, "gate": gate, "ledger": ledger,
            "env": env, "provider": FakeProvider}


def _report():
    return {"paid_attempts": [], "credentials_accessed": False,
            "credential_access_attempted": False, "ledger_opened": False,
            "ledger_access_attempted": False}


def _messages(claim="V5-C1"):
    return [{"role": "system", "content": "synthetic system"},
            {"role": "user", "content": json.dumps({"TARGET_DATA": {"claim": {
                "claim_id": claim, "release_id": "synthetic", "evidence_refs": []}}})}]


def test_paid_input_binding_is_pure_and_covers_registered_sources(monkeypatch):
    env = _ForbiddenEnvironment()
    _guard_credentials(monkeypatch, env)
    monkeypatch.setattr(v5, "ExistingLedger", lambda: pytest.fail("ledger must not open"))
    monkeypatch.setattr(v5, "PaidProvider", lambda *a, **k: pytest.fail("provider must not initialize"))

    binding = v5.paid_input_binding()

    assert binding["binding_version"] == "v5-paid-input-v1"
    assert binding["registration_raw_sha256"] == v5.REGISTRATION_RAW_SHA256
    assert len(binding["evaluator_sources"]) == 20
    assert "scripts/preview_v5_evaluation.py" in binding["evaluator_sources"]
    assert len(binding["input_sha256"]) == 64
    assert env.reads == 0


def test_paid_wire_encoding_is_exact_and_bounded():
    messages = _messages()
    actual = v5.paid_wire_bytes(messages, max_tokens=733)
    expected = json.dumps(
        {"model": v5.MODEL, "messages": messages, "max_tokens": 733,
         "thinking": {"type": "disabled"}, "stream": False},
        ensure_ascii=False, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    assert actual == expected
    with pytest.raises(EvaluationError, match="INVALID_GATE_LIMITS"):
        v5.paid_wire_bytes(messages, max_tokens=1001)
    with pytest.raises(EvaluationError, match="INVALID_MESSAGES"):
        v5.paid_wire_bytes([{"role": "assistant", "content": "bad role"}])


@pytest.mark.parametrize(
    ("approval_id", "mutations", "expected"),
    [
        (None, {}, "MAIN_FINITE_PAID_GO_REQUIRED"),
        (APPROVAL_ID, {"input_sha256": "f" * 64}, "GATE_INPUT_MISMATCH"),
        (APPROVAL_ID, {"expires_at": "2020-01-01T00:00:00+00:00"}, "GATE_EXPIRED"),
        (APPROVAL_ID, {"max_calls": 4}, "INVALID_GATE_LIMITS"),
        ("missing-approval", {}, "MAIN_FINITE_PAID_GO_REQUIRED"),
    ],
)
def test_fixed_gate_rejects_missing_expired_wrong_binding_and_overlimit(
    monkeypatch, approval_id, mutations, expected
):
    from evaluation.provider import MODEL, OFFICIAL_BASE

    gate = {
        "approval_id": APPROVAL_ID, "approved_by": "Main", "purpose": "claims",
        "input_sha256": INPUT_HASH, "max_calls": 3, "max_cost_units": 1_000_000_000,
        "max_tokens": 1000, "timeout_seconds": 20,
        "expires_at": "2099-01-01T00:00:00+00:00",
        "credential_env": "EVALUATION_MODEL_API_KEY", "base_url": OFFICIAL_BASE, "model": MODEL,
    }
    gate.update(mutations)
    raw = json.dumps({"approvals": [gate]}, sort_keys=True).encode("utf-8")
    monkeypatch.setattr(v5, "safe_read", lambda _root, path: raw if path == "evaluation/trusted/paid-gates.json" else pytest.fail("unexpected file read"))

    with pytest.raises(EvaluationError, match=expected):
        v5.fixed_paid_gate(approval_id, INPUT_HASH)


def test_paid_evidence_gate_rejects_before_binding_and_provider(registered_v5, paid_fakes, monkeypatch):
    _files, tools, context = registered_v5
    monkeypatch.setattr(context, "ready", False)
    paid_fakes["counts"]["binding"] = 0
    report = _report()

    with pytest.raises(EvaluationError, match="V5_PAID_EVIDENCE_NOT_READY"):
        v5.prepare_paid_provider(tools, context, APPROVAL_ID, report)

    assert paid_fakes["counts"]["binding"] == 0
    assert paid_fakes["counts"]["gate"] == 0
    assert paid_fakes["counts"]["ledger_init"] == 0
    assert paid_fakes["counts"]["provider_init"] == 0
    assert paid_fakes["env"].reads == 0


def test_missing_fixed_approval_stops_before_ledger_or_provider(registered_v5, paid_fakes, monkeypatch):
    _files, tools, context = registered_v5
    monkeypatch.setattr(v5, "fixed_paid_gate", lambda *a: (_ for _ in ()).throw(
        EvaluationError("MAIN_FINITE_PAID_GO_REQUIRED")))
    report = _report()

    with pytest.raises(EvaluationError, match="MAIN_FINITE_PAID_GO_REQUIRED"):
        v5.prepare_paid_provider(tools, context, None, report)

    assert paid_fakes["counts"]["ledger_init"] == 0
    assert paid_fakes["counts"]["provider_init"] == 0
    assert report["ledger_opened"] is False
    assert report["credentials_accessed"] is False
    assert paid_fakes["env"].reads == 0


@pytest.mark.parametrize(
    ("ledger_error", "remaining", "rows", "gate_calls", "gate_cost", "expected"),
    [
        ("PRIOR_CALL_UNKNOWN_STOP", 9_000_000_000, (), 3, 9_000_000_000, "PRIOR_CALL_UNKNOWN_STOP"),
        ("AI_BUDGET_EXHAUSTED", 9_000_000_000, (), 3, 9_000_000_000, "AI_BUDGET_EXHAUSTED"),
        (None, 0, (), 3, 9_000_000_000, "AI_BUDGET_EXHAUSTED"),
        (None, 9_000_000_000, [("game", "another-scope-unknown", 1, "unknown")],
         3, 9_000_000_000, "PRIOR_CALL_UNKNOWN_STOP"),
        (None, 9_000_000_000, [("experiment", "another-scope-reserved", 1, "reserved")],
         3, 9_000_000_000, "PRIOR_CALL_UNKNOWN_STOP"),
        (None, 9_000_000_000, [("evaluation", f"eval_{APPROVAL_ID}_1", 1, "settled")],
         1, 9_000_000_000, "EVALUATION_GATE_EXHAUSTED"),
        (None, 9_000_000_000, [("evaluation", f"eval_{APPROVAL_ID}_1", 8_999_999_999, "settled")],
         3, 9_000_000_000, "EVALUATION_GATE_EXHAUSTED"),
        (None, 9_000_000_000, (), 3, 1, "AI_BUDGET_EXHAUSTED"),
        (None, 9_000_000_000, [("evaluation", f"eval_{APPROVAL_ID}_1", 1, "unknown")],
         3, 9_000_000_000, "PRIOR_CALL_UNKNOWN_STOP"),
    ],
)
def test_global_ledger_and_used_gate_allowance_reject_before_fake_provider(
    registered_v5, paid_fakes, ledger_error, remaining, rows, gate_calls, gate_cost, expected
):
    _files, tools, context = registered_v5
    paid_fakes["ledger"].ready_error = ledger_error
    paid_fakes["ledger"].remaining = remaining
    paid_fakes["ledger"].rows = list(rows)
    paid_fakes["gate"]["max_calls"] = gate_calls
    paid_fakes["gate"]["max_cost_units"] = gate_cost
    provider = None
    prepare_blocked = (ledger_error is not None or remaining <= 0 or
                       any(state in {"unknown", "reserved"} for _scope, _id, _charged, state in rows))
    if prepare_blocked:
        with pytest.raises(EvaluationError, match=expected):
            v5.prepare_paid_provider(tools, context, APPROVAL_ID, _report())
    else:
        provider = v5.prepare_paid_provider(tools, context, APPROVAL_ID, _report())
        with pytest.raises(EvaluationError, match=expected):
            asyncio.run(provider.complete(_messages()))

    assert paid_fakes["counts"]["provider_init"] == 0
    assert paid_fakes["env"].reads == 0
    if provider is not None:
        assert provider.last_metadata is None
    paid_fakes["ledger"].ready_error = None
    paid_fakes["ledger"].remaining = 10_000_000_000
    paid_fakes["ledger"].rows = []
    paid_fakes["gate"]["max_calls"] = 3
    paid_fakes["gate"]["max_cost_units"] = 9_000_000_000


@pytest.mark.parametrize("condition", ["frozen", "cap_drift"])
def test_frozen_or_changed_global_cap_blocks_before_fake_provider(
    registered_v5, paid_fakes, condition
):
    _files, tools, context = registered_v5
    if condition == "frozen":
        paid_fakes["ledger"].frozen = True
    else:
        paid_fakes["ledger"].cap = CAP - 1
    with pytest.raises(EvaluationError, match="AI_BUDGET_EXHAUSTED"):
        v5.prepare_paid_provider(tools, context, APPROVAL_ID, _report())

    assert paid_fakes["counts"]["provider_init"] == 0
    assert paid_fakes["env"].reads == 0
    paid_fakes["ledger"].frozen = False
    paid_fakes["ledger"].cap = CAP


def test_identity_change_after_prepare_stops_before_provider(registered_v5, paid_fakes, monkeypatch):
    _files, tools, context = registered_v5
    provider = v5.prepare_paid_provider(tools, context, APPROVAL_ID, _report())
    changed = {**paid_fakes["binding"], "input_sha256": "e" * 64}
    monkeypatch.setattr(v5, "paid_input_binding", lambda: changed)

    with pytest.raises(EvaluationError, match="V5_PAID_INPUT_CHANGED"):
        asyncio.run(provider.complete(_messages()))

    assert paid_fakes["counts"]["provider_init"] == 0
    assert paid_fakes["env"].reads == 0
    assert provider.last_metadata is None


def test_identity_change_after_fake_dispatch_stops_remaining_claims(
    registered_v5, paid_fakes, monkeypatch
):
    files, tools, context = registered_v5
    paid_fakes["provider"].scripts = ["PASS", "PASS", "PASS"]
    binding = copy.deepcopy(paid_fakes["binding"])
    changed = {**binding, "input_sha256": "f" * 64}
    observed = []

    def change_after_first_judgement():
        observed.append(None)
        # prepare + pre-dispatch see the reviewed bytes; post-dispatch sees drift.
        return copy.deepcopy(changed if len(observed) >= 3 else binding)

    monkeypatch.setattr(v5, "paid_input_binding", change_after_first_judgement)
    report = _report()

    code = asyncio.run(v5.evaluate_paid_claims(files, tools, context, APPROVAL_ID, report))

    assert code == 2
    assert len(report["paid_attempts"]) == 1
    assert report["paid_attempts"][0]["provider_invoked"] is True
    assert report["paid_attempts"][0]["actual_network_call"] is False
    assert report["paid_attempts"][0]["error_code"] == "V5_PAID_INPUT_CHANGED"
    assert all(row["status"] == "INSUFFICIENT_EVIDENCE" for row in report["results"])
    assert paid_fakes["provider"].scripts == ["PASS", "PASS"]
    assert paid_fakes["env"].reads == 0


def test_gate_change_stops_after_prior_fake_call_and_clears_old_metadata(
    registered_v5, paid_fakes, monkeypatch
):
    _files, tools, context = registered_v5
    paid_fakes["provider"].scripts = ["pass"]
    report = _report()
    provider = v5.prepare_paid_provider(tools, context, APPROVAL_ID, report)
    reply = asyncio.run(provider.complete(_messages()))
    assert reply.content
    assert provider.last_metadata["actual_network_call"] is False
    assert provider.last_metadata["call_id"] is None

    monkeypatch.setattr(v5, "fixed_paid_gate", lambda _approval, _input: (
        {**paid_fakes["gate"], "max_calls": 2}, GATE_HASH))
    with pytest.raises(EvaluationError, match="V5_PAID_GATE_CHANGED"):
        asyncio.run(provider.complete(_messages("V5-C2")))

    assert provider.last_metadata is None
    assert report["paid_attempts"][-1]["provider_invoked"] is False
    assert report["paid_attempts"][-1]["reserved_call_delta"] == 0
    assert report["paid_attempts"][-1]["error_code"] == "V5_PAID_GATE_CHANGED"
    assert paid_fakes["env"].reads == 0


@pytest.mark.parametrize("first_action", ["INSUFFICIENT_EVIDENCE", "invalid_reference", "raise"])
def test_insufficient_invalid_or_exception_stops_remaining_claims_without_retry(
    registered_v5, paid_fakes, first_action
):
    files, tools, context = registered_v5
    paid_fakes["provider"].scripts = [first_action, "pass", "pass"]
    report = _report()

    code = asyncio.run(v5.evaluate_paid_claims(files, tools, context, APPROVAL_ID, report))

    assert code == 2
    assert len(report["paid_attempts"]) == 1
    assert report["paid_attempts"][0]["provider_invoked"] is True
    assert report["paid_attempts"][0]["reserved_call_delta"] == 1
    assert report["paid_attempts"][0]["actual_network_call"] is False
    assert len(report["results"]) == len(v5.CLAIMS)
    assert report["results"][0]["status"] == "INSUFFICIENT_EVIDENCE"
    assert all(row["status"] == "INSUFFICIENT_EVIDENCE" for row in report["results"][1:])
    if first_action == "raise":
        assert report["paid_attempts"][0]["error_code"] == "PAID_ATTEMPT_INTERRUPTED_OR_INTERNAL"
    else:
        assert report["paid_attempts"][0]["error_code"] is None
    assert paid_fakes["provider"].scripts == ["pass", "pass"]
    assert paid_fakes["env"].reads == 0


def test_valid_fail_is_retained_and_later_fake_claims_complete(registered_v5, paid_fakes):
    files, tools, context = registered_v5
    paid_fakes["provider"].scripts = ["FAIL", "PASS", "PASS"]
    report = _report()

    code = asyncio.run(v5.evaluate_paid_claims(files, tools, context, APPROVAL_ID, report))

    assert code == 1
    assert [row["status"] for row in report["results"]] == ["FAIL", "PASS", "PASS"]
    assert [row["claim_id"] for row in report["paid_attempts"]] == list(v5.CLAIMS)
    assert all(row["provider_invoked"] and row["actual_network_call"] is False
               for row in report["paid_attempts"])
    assert all(row["call_id"] is None and row["usage"] is None for row in report["paid_attempts"])
    assert paid_fakes["env"].reads == 0


def test_free_preview_matches_fake_engine_messages_and_never_touches_paid_surfaces(
    monkeypatch
):
    captured = []
    original_complete = preview.CaptureProvider.complete

    async def capture_messages(self, messages):
        captured.append(copy.deepcopy(messages))
        return await original_complete(self, messages)

    def forbidden(*_args, **_kwargs):
        pytest.fail("free preview must not touch paid provider, ledger, or fixed gate")

    monkeypatch.setattr(preview.CaptureProvider, "complete", capture_messages)
    monkeypatch.setattr(v5, "ExistingLedger", forbidden)
    monkeypatch.setattr(v5, "PaidProvider", forbidden)
    monkeypatch.setattr(v5, "fixed_paid_gate", forbidden)
    env = _ForbiddenEnvironment()
    _guard_credentials(monkeypatch, env)

    result = asyncio.run(preview.build_preview())

    assert result["status"] == "PREVIEW_ONLY"
    assert result["synthetic_capture_only"] is True
    assert result["capture_dispatches"] == len(v5.CLAIMS) == len(captured)
    assert [row["claim_id"] for row in result["claims"]] == list(v5.CLAIMS)
    assert result["credentials_accessed"] is False
    assert result["ledger_opened"] is False
    assert result["real_model_calls"] == result["actual_paid_calls"] == result["actual_network_calls"] == 0
    assert result["total_cost_upper_units"] == sum(row["cost_upper_units"] for row in result["claims"])
    for messages, row in zip(captured, result["claims"]):
        wire = v5.paid_wire_bytes(messages, max_tokens=1000)
        bound = len(wire) * 4 + 8192
        assert row["wire_sha256"] == v5.sha256(wire)
        assert row["wire_bytes"] == len(wire)
        assert row["input_token_bound"] == bound
        assert row["cost_upper_units"] == cost_units(bound, 1000)
    assert env.reads == 0
