"""Owner local deterministic checks. No .env, paid provider or network."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import asyncio
import uuid

from jsonschema import Draft202012Validator, FormatChecker

from .common import HOME, ROOT, baseline_binding, encoded, experiment_hashes, load, sha, write_new
from .context import build, facts, pack, unpack
from .judger import judge
from .plan import input_for, make_plan
from .runner import append, approve, execute, exclusive, mock_content, new_run, reconcile
from .summarize import calculate, read_rows, summarize


def receipt_checks(check):
    """Exercise execute's real branch with explicit local-only injected I/O."""
    import sqlite3
    from unittest.mock import patch
    import httpx
    import backend.app.ai.provider as adapter
    from backend.app.ai.budget import BudgetLedger
    from . import runner
    plan = make_plan("pilot")
    original = adapter.DeepSeekProvider
    records = []
    for name in ("401", "403", "429", "503", "connect_error", "timeout", "malformed_200", "success", "preflight"):
        ledger = BudgetLedger(HOME / ".runtime" / ("fake-receipt-" + uuid.uuid4().hex) / "fake-budget.sqlite")
        calls = []
        def fake_http(request):
            calls.append(sha(request.content))
            if name == "connect_error":
                raise httpx.ConnectError("synthetic", request=request)
            if name == "timeout":
                raise httpx.ReadTimeout("synthetic", request=request)
            if name.isdigit():
                return httpx.Response(int(name), json={"error": "synthetic"})
            if name == "malformed_200":
                return httpx.Response(200, content=b"{broken")
            return httpx.Response(200, json={"model": "deepseek-flash", "choices": [{"finish_reason": "stop", "message": {
                "role": "assistant", "content": mock_content("C02")}}], "usage": {
                    "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "prompt_cache_hit_tokens": 0}})
        config = adapter.DeepSeekConfig("" if name == "preflight" else "synthetic-not-a-real-key")
        def factory(_):
            return original(config, ledger, transport=httpx.MockTransport(fake_http))
        def snapshot():
            with sqlite3.connect(ledger.path.resolve().as_uri() + "?mode=ro", uri=True) as db:
                db.row_factory = sqlite3.Row
                cap, frozen = db.execute("SELECT cap,frozen FROM budget_config WHERE id=1").fetchone()
                rows = [dict(row) for row in db.execute("SELECT id,scope,created_at,reserved,charged,state,reason,prompt_tokens,completion_tokens,cache_hit_tokens FROM budget_calls")]
            charged = sum(row["charged"] for row in rows)
            return {"cap_units": cap, "charged_units": charged, "remaining_units": cap - charged,
                    "frozen": bool(frozen), "calls": rows}
        directory = new_run(plan, "synthetic-transport")
        with patch.object(adapter.DeepSeekConfig, "from_environment", return_value=config), \
                patch.object(adapter, "DeepSeekProvider", factory), patch.object(runner, "ledger_read", side_effect=snapshot):
            rows = asyncio.run(execute(plan, directory, "real", {"additional_upper_cap_units": 1_000_000_000}))
        summary = summarize(directory)
        first = rows[0]
        if name in {"401", "403", "429", "503", "malformed_200", "success"}:
            check(name + "_http_receipt_and_delivery_confirmed", first["response_received"] is True and first["upstream_delivery_known"] is True)
            check(name + "_status_only_observed", first["http_status_code"] == (int(name) if name.isdigit() else 200))
        elif name in {"connect_error", "timeout"}:
            check(name + "_receipt_delivery_unknown", first["response_received"] is None and first["upstream_delivery_known"] is None)
            check(name + "_no_invented_http_status", first["http_status_code"] is None)
        else:
            check("preflight_explicitly_not_attempted", first["status"] == "not_called" and first["response_received"] is False and first["upstream_delivery_known"] is False and not calls)
        if name != "success":
            check(name + "_no_resend_and_remaining_rows_not_called", len(calls) == (0 if name == "preflight" else 1) and all(row["status"] == "not_called" for row in rows[1:]))
        else:
            check("success_normalized_response_separate", all(row["normalized_response_received"] is True for row in rows))
        for variant, group in summary["by_variant"].items():
            check(name + "_" + variant + "_response_tristate_partition", group["responses_received"] + group["responses_unknown"] + group["responses_not_received"] == group["planned"])
            check(name + "_" + variant + "_delivery_tristate_partition", group["delivery_confirmed"] + group["delivery_unknown"] + group["delivery_not_attempted"] == group["planned"])
        check(name + "_wire_hash_unchanged", not calls or calls[0] == plan["rows"][0]["input_hash"])
        records.append({"case": name, "run": str(directory), "synthetic_only": True,
                        "network_calls": 0, "paid_calls": 0, "transport_invocations": len(calls)})
    # Observer rejects noncanonical production ledgers before making a request.
    from .transport import observe, ReceiptObserver
    class Unapproved:
        transport = None
        ledger = type("Ledger", (), {"path": HOME / ".runtime/fake-noncanonical.sqlite"})()
    try:
        observe(Unapproved())
    except ValueError:
        check("observer_cannot_change_production_ledger", True)
    else:
        check("observer_cannot_change_production_ledger", False)
    async def bad_endpoint():
        observer = ReceiptObserver(httpx.MockTransport(lambda _: httpx.Response(200)))
        try:
            await observer.handle_async_request(httpx.Request("POST", "https://example.invalid/chat/completions"))
        finally:
            await observer.aclose()
    try:
        asyncio.run(bad_endpoint())
    except ValueError:
        check("observer_rejects_arbitrary_endpoint", True)
    else:
        check("observer_rejects_arbitrary_endpoint", False)
    return records


def main():
    results = []
    def check(name, condition):
        if not condition:
            raise ValueError("LOCAL_CHECK_FAILED:" + name)
        results.append({"name": name, "passed": True})
    initial = experiment_hashes()
    binding = baseline_binding()
    check("baseline_all_sources_bound", len(binding["sources"]) == 60)
    check("baseline_evidence_bound", len(binding["artifacts"]) == 14)
    check("historical_unbound_qa_not_silently_dropped", len(binding["unbound_prior_source_records"]) == 6)
    from .samples import build_samples
    public, private = build_samples()
    api = load(ROOT / "contracts/api.schema.json")
    state_schema = {"$ref": "#/$defs/visible_state", "$defs": api["$defs"]}
    for sample_id, rebuilt in public.items():
        stored = load(HOME / "fixtures" / (sample_id + ".json"))
        check(sample_id + "_public_reproducible", stored == rebuilt)
        check(sample_id + "_private_reproducible", load(HOME / "ground_truth" / (sample_id + ".json")) == private[sample_id])
        Draft202012Validator(state_schema, format_checker=FormatChecker()).validate(stored["visible_state"])
        check(sample_id + "_roundtrip", unpack(pack(stored["visible_history"])) == stored["visible_history"])
        a, b = build(stored, "full_history"), build(stored, "structured_summary")
        check(sample_id + "_same_visible_facts", facts(a) == facts(b))
        am, at, ah = input_for(stored, "full_history")
        bm, bt, bh = input_for(stored, "structured_summary")
        check(sample_id + "_same_prompt_schema_question", am[0] == bm[0] and at == bt and a["message"] == b["message"])
        check(sample_id + "_no_ground_truth_in_request", all("ground_truth" not in msg["content"] and "acceptable_actions" not in msg["content"] for msg in am + bm))
        check(sample_id + "_payload_bound", ah["input_token_bound"] <= 1_000_000 and bh["input_token_bound"] <= 1_000_000)
        golden = judge(mock_content(sample_id), stored)
        check(sample_id + "_golden_legal_correct_refs", golden["legal"] and golden["correct"] and golden["reference_valid"] and golden["reference_sufficient"])
        from backend.app.domain.models import GameState
        from backend.app.domain.rules import apply_action
        state = GameState.model_validate(deepcopy(private[sample_id]["state"]))
        before = state.model_dump()
        for action in private[sample_id]["acceptable_actions"]:
            apply_action(state.model_copy(deep=True), action["tool"], action["arguments"])
        check(sample_id + "_all_reference_actions_legal_without_mutation", state.model_dump() == before)
        # Chronology and knowledge are proven by legal-prefix rebuild, plus refs.
        known = {clue["clue_id"] for clue in stored["visible_state"]["clues"]}
        check(sample_id + "_history_discovered_refs", all(set(entry["new_clue_ids"]) <= known for entry in stored["visible_history"]))
    odd = [{"kind": "action", "tool": "inspect", "observation": None}, {"kind": "ai_turn", "answer": "值"},
           {"kind": "action", "tool": "inspect", "observation": ""}, {"kind": "action", "tool": "inspect", "observation": None}]
    check("lossless_missing_null_empty_repetition_order", unpack(pack(odd)) == odd)
    literal = [{"kind": "action", "arguments": {"encoding": "e1-columns-v1", "groups": [None], "indices": [0]}, "observation": None},
               {"kind": "ai_turn", "answer": "null"},
               {"kind": "action", "arguments": {"encoding": "e1-columns-v1", "groups": [None], "indices": [0]}, "observation": None}]
    expected_packed = {"encoding": "e1-columns-v1", "record_count": 3, "groups": [
        {"fields": ["kind", "arguments", "observation"], "indices": [0, 2], "rows": [
            ["action", {"encoding": "e1-columns-v1", "groups": [None], "indices": [0]}, None],
            ["action", {"encoding": "e1-columns-v1", "groups": [None], "indices": [0]}, None]]},
        {"fields": ["kind", "answer"], "indices": [1], "rows": [["ai_turn", "null"]]}]}
    check("independent_literal_column_representation", pack(literal) == expected_packed)
    check("independent_literal_decode_and_reserved_word_collision", unpack(expected_packed) == literal)
    malformed = pack(odd)
    malformed["groups"][0]["indices"][0] = True
    try:
        unpack(malformed)
    except ValueError:
        check("summary_rejects_boolean_index", True)
    else:
        check("summary_rejects_boolean_index", False)
    for name, change in [("duplicate_chronological_index", lambda item: item["groups"][0]["indices"].__setitem__(1, 0)),
                         ("duplicate_field_names", lambda item: item["groups"][0]["fields"].__setitem__(1, "kind")),
                         ("missing_chronological_record", lambda item: item.__setitem__("record_count", 4))]:
        corrupt = deepcopy(expected_packed)
        change(corrupt)
        try:
            unpack(corrupt)
        except ValueError:
            check(name + "_rejected", True)
        else:
            check(name + "_rejected", False)
    formal, pilot = make_plan("formal"), make_plan("pilot")
    check("formal_72_unique_rows", len(formal["rows"]) == 72 and len({r["row_id"] for r in formal["rows"]}) == 72)
    check("pilot_6_separate_rows", len(pilot["rows"]) == 6 and not {r["row_id"] for r in pilot["rows"]} & {r["row_id"] for r in formal["rows"]})
    first_variants = [formal["rows"][index]["variant"] for index in range(0, 72, 2)]
    check("balanced_18_AB_18_BA", first_variants.count("full_history") == first_variants.count("structured_summary") == 18)
    sample = public["C01"]
    check("parse_duplicate_keys_rejected", not judge('{"answer":"a","answer":"b","clue_refs":[],"next_action":null}', sample)["parse_valid"])
    wrong = {"answer": "wrong", "clue_refs": ["not_discovered"], "next_action": {"tool": "move", "arguments": {"destination_id": "R2"}, "clue_refs": [], "summary": "wrong"}}
    verdict = judge(encoded(wrong).decode(), sample)
    check("wrong_move_and_unknown_refs_preserved", verdict["parse_valid"] and verdict["legal"] is False and verdict["correct"] is False and verdict["reference_valid"] is False)
    inventory = {"answer": "legal but not useful", "clue_refs": [], "next_action": {"tool": "get_inventory", "arguments": {}, "clue_refs": [], "summary": "mock"}}
    verdict = judge(encoded(inventory).decode(), sample)
    check("legal_is_not_correct", verdict["legal"] is True and verdict["correct"] is False)
    insufficient = load(HOME / "ground_truth/C03.json")["acceptable_actions"][0]
    insufficient = {"answer": "code without citations", "clue_refs": [], "next_action": {**insufficient, "clue_refs": [], "summary": "mock"}}
    verdict = judge(encoded(insufficient).decode(), public["C03"])
    check("correct_action_separate_reference_sufficiency", verdict["correct"] and verdict["reference_valid"] and not verdict["reference_sufficient"])
    try:
        approve(None, None, pilot)
    except ValueError:
        check("no_go_blocks_before_paid_construction", True)
    else:
        check("no_go_blocks_before_paid_construction", False)
    from backend.app.ai.provider import MockProvider, ProviderResult, CallLimits
    async def provider_mock():
        provider = MockProvider([ProviderResult(mock_content("C01"), (), None, "mock", "mock", "mock", "stop")])
        messages, tools, _ = input_for(sample, "full_history")
        return await provider.complete(messages, tools, CallLimits(), scope="experiments", tool_choice="none")
    reply = asyncio.run(provider_mock())
    check("generic_six_tool_mock_provider", reply.usage is None and judge(reply.content, sample)["correct"])
    # Synthetic HTTP transport binds input_hash to actual frozen Provider wire.
    # No credentials are read; the fake ledger is ignored .runtime, never production.
    import httpx
    from backend.app.ai.budget import BudgetLedger
    from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider
    captured = []
    def fake_http(request):
        captured.append(sha(request.content))
        return httpx.Response(200, json={"model": "deepseek-flash", "choices": [{"finish_reason": "stop", "message": {
            "role": "assistant", "content": mock_content("C01")}}], "usage": {
                "prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3, "prompt_cache_hit_tokens": 0}})
    async def wire_check():
        ledger = BudgetLedger(HOME / ".runtime" / ("fake-wire-" + uuid.uuid4().hex) / "fake-budget.sqlite")
        provider = DeepSeekProvider(DeepSeekConfig("synthetic-not-a-real-key", "deepseek-flash", "https://api.deepseek.com"),
                                    ledger, transport=httpx.MockTransport(fake_http))
        messages, tools, hashes = input_for(sample, "structured_summary")
        response = await provider.complete(messages, tools, CallLimits(), scope="experiments", tool_choice="none")
        return hashes, response
    hashes, response = asyncio.run(wire_check())
    check("fake_transport_actual_wire_hash_matches_plan", captured == [hashes["input_hash"]])
    check("fake_transport_shared_adapter_output_shape", judge(response.content, sample)["correct"])
    with exclusive():
        local = new_run(pilot, "mock")
        rows = asyncio.run(execute(pilot, local, "mock", scenario="mixed"))
        summary = summarize(local)
        check("mixed_raw_preserves_all_planned_rows", len(read_rows(local / "raw.jsonl")) == 6)
        check("mixed_parse_timeout_ref_failure_retained", rows[0]["status"] == "parse_invalid" and rows[1]["status"] == "timeout" and rows[2]["reference_valid"] is False)
        check("mock_never_implies_paid_usage", all(r["actually_called"] is False and r["usage"] is None and r["charged_upper_cny"] is None for r in rows))
        interrupted = new_run(pilot, "mock")
        append(interrupted / "journal.jsonl", {"event": "invocation_started", "at": interrupted.name, "row_id": pilot["rows"][0]["row_id"], "mode": "mock", "experiment_ids_before": []})
        suffix = reconcile(interrupted)
        recovered = read_rows(interrupted / (suffix + ".jsonl"))
        check("crash_mock_no_resend_all_rows", len(recovered) == 6 and recovered[0]["error"] == "INTERRUPTED_NO_RETRY" and recovered[1]["status"] == "not_called")
        # Synthetic crash fixture marked explicitly; it does not touch real ledger.
        fake = new_run(pilot, "synthetic-real-recovery")
        started = "2026-10-02T00:00:00+00:00"
        append(fake / "journal.jsonl", {"event": "invocation_started", "at": started, "row_id": pilot["rows"][0]["row_id"], "mode": "real", "experiment_ids_before": []})
        call = {"id": "synthetic-call", "scope": "experiments", "created_at": "2026-10-02T00:00:01+00:00", "reserved": 100, "charged": 100, "state": "unknown", "reason": "SYNTHETIC_CRASH", "prompt_tokens": None, "completion_tokens": None, "cache_hit_tokens": None}
        snapshot = {"calls": [call], "cap_units": 1000, "charged_units": 100, "remaining_units": 900, "frozen": False}
        suffix = reconcile(fake, snapshot)
        recovered = read_rows(fake / (suffix + ".jsonl"))
        check("unique_reservation_attempt_delivery_unknown", recovered[0]["actually_called"] is True and recovered[0]["response_received"] is None and recovered[0]["upstream_delivery_known"] is None and recovered[0]["usage"] is None)
        ambiguous = {**snapshot, "calls": [call, {**call, "id": "synthetic-second"}]}
        suffix = reconcile(fake, ambiguous)
        recovered = read_rows(fake / (suffix + ".jsonl"))
        check("ambiguous_reservation_retains_null", recovered[0]["actually_called"] is None and recovered[0]["call_id"] is None)
        check("interrupted_response_delivery_unknown", recovered[0]["response_received"] is None and recovered[0]["upstream_delivery_known"] is None)
        receipt_evidence = receipt_checks(check)
    check("experiment_sources_unchanged_during_checks", initial == experiment_hashes())
    check("baseline_unchanged_after_checks", binding == baseline_binding())
    result = {"kind": "owner-local-deterministic-not-formal-QA", "passed": True, "checks": results,
              "count": len(results), "real_provider_constructed": False, "fake_transport_provider_constructed": True,
              "fake_transport_calls": 1 + sum(case["transport_invocations"] for case in receipt_evidence),
              "network_calls": 0, "paid_calls": 0,
              "source_hashes": initial, "baseline": binding, "mock_run": str(local), "synthetic_recovery_run": str(fake),
              "receipt_checks": receipt_evidence,
              "limitations": ["Crash checks inject journal/reservation fixtures; they are not a killed real process or real ledger transaction.",
                             "The mock output is scripted; no empirical E1 model quality result.",
                             "Independent QA and separate T23 Main GO remain required."]}
    out = HOME / "runs" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-owner-check-" + uuid.uuid4().hex[:8])
    write_new(out / "checks.json", result)
    print(str(out / "checks.json"))


if __name__ == "__main__":
    main()
