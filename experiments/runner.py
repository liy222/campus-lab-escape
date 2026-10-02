"""Finite single-request runner. Real admission is separate from local modes."""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager

from .common import HOME, ROOT, baseline_binding, encoded, inside, load, now, sha, write_new
from .plan import frozen, input_for, make_plan


@contextmanager
def exclusive():
    path = inside(HOME / ".runtime/experiment.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if path.stat().st_size == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def append(path, value):
    with inside(path).open("ab") as handle:
        handle.write(encoded(value) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())


def ledger_read():
    """Read original shared ledger in mode=ro; never initialize/reset it here."""
    path = ROOT / "data/ai-budget.sqlite"
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        cap, frozen = db.execute("SELECT cap,frozen FROM budget_config WHERE id=1").fetchone()
        all_calls = [dict(row) for row in db.execute("SELECT id,scope,created_at,reserved,charged,state,reason,prompt_tokens,completion_tokens,cache_hit_tokens FROM budget_calls")]
    charged = sum(row["charged"] for row in all_calls)
    return {"cap_units": cap, "charged_units": charged, "remaining_units": max(0, cap - charged),
            "frozen": bool(frozen), "calls": all_calls}


def safe_ledger(snapshot):
    # Only experiment IDs are written, never non-experiment call details.
    return {"cap_units": snapshot["cap_units"], "charged_units": snapshot["charged_units"],
            "remaining_units": snapshot["remaining_units"], "frozen": snapshot["frozen"],
            "experiment_calls": [row for row in snapshot["calls"] if row["scope"] == "experiments"]}


def approve(path, expected_hash, plan):
    """A future Main-issued finite gate binds every reviewed input/source hash."""
    if path is None or expected_hash is None:
        raise ValueError("REAL_REQUIRES_SEPARATE_MAIN_GO")
    path = inside(path)
    if not path.is_relative_to((HOME / "authorizations").resolve()):
        raise ValueError("AUTHORIZATION_PATH_REQUIRED")
    if sha(path.read_bytes()) != expected_hash:
        raise ValueError("AUTHORIZATION_HASH_MISMATCH")
    gate = load(path)
    if gate.get("approved_by") != "Main" or gate.get("approved") is not True or gate.get("phase") != plan["phase"]:
        raise ValueError("INVALID_MAIN_PHASE_GO")
    if gate.get("freeze_hash") != sha(plan["freeze"]) or gate.get("plan_hash") != sha(plan):
        raise ValueError("GO_INPUTS_CHANGED")
    if type(gate.get("max_calls")) is not int or gate["max_calls"] != plan["planned"]:
        raise ValueError("GO_CALL_LIMIT_MISMATCH")
    if type(gate.get("additional_upper_cap_units")) is not int or not 0 < gate["additional_upper_cap_units"] <= 10_000_000_000:
        raise ValueError("INVALID_FINITE_PHASE_CAP")
    if not isinstance(gate.get("id"), str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", gate["id"]):
        raise ValueError("INVALID_GO_ID")
    expires = datetime.fromisoformat(gate["expires_at"].replace("Z", "+00:00"))
    if expires.tzinfo is None or datetime.now(timezone.utc) >= expires:
        raise ValueError("GO_EXPIRED")
    pricing_path = (ROOT / gate["pricing_evidence"]).resolve()
    if not pricing_path.is_relative_to(ROOT.resolve()) or sha(pricing_path.read_bytes()) != gate["pricing_sha256"]:
        raise ValueError("PRICING_EVIDENCE_MISMATCH")
    pricing = load(pricing_path)
    checked = datetime.fromisoformat(pricing["checked_at_utc"].replace("Z", "+00:00"))
    age = (datetime.now(timezone.utc) - checked).total_seconds()
    if checked.tzinfo is None or not 0 <= age <= 86400 or pricing["peak_cny_per_million"] != {"input_miss": 2, "input_hit": .04, "output": 8}:
        raise ValueError("FRESH_APPROVED_PRICING_REQUIRED")
    for old in (HOME / "runs").glob("*/run.json"):
        old_run = load(old)
        if old_run.get("authorization_id") == gate["id"]:
            raise ValueError("GO_ALREADY_CONSUMED_NO_REPLAY")
        if old_run["mode"] == "real" and not (old.parent / "completion.json").exists():
            audits = list(old.parent.glob("reconciled-*-audit.json"))
            if not audits or any(load(audit)["uncertain_paid_attempts"] for audit in audits):
                raise ValueError("PRIOR_INTERRUPTION_REQUIRES_READONLY_RECONCILIATION")
    if plan["phase"] == "formal":
        pilot = inside(HOME / "runs" / gate["pilot_run_id"])
        pilot_run, summary = load(pilot / "run.json"), load(pilot / "summary.json")
        if pilot_run["mode"] != "real" or pilot_run["phase"] != "pilot" or sha((pilot / "summary.json").read_bytes()) != gate["pilot_summary_sha256"]:
            raise ValueError("REAL_PILOT_ACCEPTANCE_REQUIRED")
        if any(group["completed"] != group["planned"] or group["usage_known_rows"] != group["planned"] or group["paid_attempts_uncertain"] for group in summary["by_variant"].values()):
            raise ValueError("PILOT_NOT_COMPLETE_WITH_KNOWN_USAGE")
        if gate.get("pilot_review_accepted") is not True:
            raise ValueError("MAIN_PILOT_REVIEW_REQUIRED")
    current = ledger_read()
    if current["frozen"] or any(call["state"] in {"reserved", "unknown"} for call in current["calls"]):
        raise ValueError("SHARED_PENDING_OR_UNKNOWN_BLOCKS_PHASE_START")
    return gate


def new_run(plan, mode, gate=None):
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + plan["phase"] + "-" + mode + "-" + uuid.uuid4().hex[:8]
    directory = inside(HOME / "runs" / run_id)
    directory.mkdir(parents=True, exist_ok=False)
    run = {"run_id": run_id, "created_at": now(), "phase": plan["phase"], "mode": mode,
           "plan_hash": sha(plan), "baseline": baseline_binding(), "authorization_id": gate["id"] if gate else None,
           "authorization": gate, "real_calls_allowed": mode == "real", "planned": plan["planned"],
           "synthetic_recovery_fixture": mode == "synthetic-real-recovery",
           "command": __import__("sys").argv, "python": __import__("sys").executable,
           "limitations": ["Owner local verification is not independent QA or paid E1 evidence."]}
    write_new(directory / "run.json", run)
    write_new(directory / "plan.json", plan)
    for row in plan["rows"]:
        sample = load(HOME / "fixtures" / (row["sample_id"] + ".json"))
        if frozen() != plan["freeze"]:
            raise ValueError("EXPERIMENT_SOURCE_CHANGED")
        messages, tools, hashes = input_for(sample, row["variant"])
        if hashes["input_hash"] != row["input_hash"]:
            raise ValueError("INPUT_CHANGED")
        write_new(directory / "inputs" / (row["row_id"] + ".json"), {"messages": messages, "tools": tools, **hashes})
    return directory


def mock_content(sample_id):
    # Deliberately scripted output, not a model and not part of request inputs.
    truth = load(HOME / "ground_truth" / (sample_id + ".json"))
    return encoded({"answer": "本地注入的参考建议，不是模型观察。", "clue_refs": truth["required_code_refs"],
                    "next_action": {**deepcopy(truth["acceptable_actions"][0]), "clue_refs": truth["required_code_refs"],
                                    "summary": "本地脚本建议"}}).decode("utf-8")


def billed(row, snapshot):
    matching = [call for call in snapshot["calls"] if call["id"] == row["call_id"] and call["scope"] == "experiments"]
    if not matching:
        raise ValueError("PROVIDER_CALL_NOT_IN_ORIGINAL_SHARED_LEDGER")
    call = matching[0]
    row.update(actually_called=True, charged_upper_cny=call["charged"] / 1e9)
    if call["state"] == "settled":
        row["usage"] = {"prompt_tokens": call["prompt_tokens"], "completion_tokens": call["completion_tokens"],
                        "prompt_cache_hit_tokens": call["cache_hit_tokens"], "total_tokens": call["prompt_tokens"] + call["completion_tokens"]}
        row["usage_known"] = True


async def execute(plan, directory, mode, gate=None, scenario="success"):
    from .judger import judge
    provider = None
    if mode == "real":
        # This is the sole credential-reading/provider-construction branch.
        from backend.app.ai.provider import DeepSeekProvider, DeepSeekConfig, CallLimits, ProviderError
        provider = DeepSeekProvider(DeepSeekConfig.from_environment())
    stopped, consecutive = None, 0
    phase_charged_units = 0
    rows = deepcopy(plan["rows"])
    for index, row in enumerate(rows):
        if stopped:
            row["error"] = stopped
            append(directory / "raw.jsonl", row)
            continue
        if frozen() != plan["freeze"]:
            stopped = "EXPERIMENT_SOURCE_CHANGED"
            row["error"] = stopped
            append(directory / "raw.jsonl", row)
            continue
        sample = load(HOME / "fixtures" / (row["sample_id"] + ".json"))
        messages, tools, hashes = input_for(sample, row["variant"])
        if hashes["input_hash"] != row["input_hash"]:
            stopped = "INPUT_CHANGED"
            row["error"] = stopped
            append(directory / "raw.jsonl", row)
            continue
        before_ids = []
        if mode == "real":
            baseline_binding()
            snapshot = ledger_read()
            if snapshot["frozen"] or snapshot["remaining_units"] < row["reservation_units"]:
                stopped = "SHARED_BUDGET_STOP"
            elif phase_charged_units + row["reservation_units"] > gate["additional_upper_cap_units"]:
                stopped = "PHASE_UPPER_CAP_STOP"
            if stopped:
                row["error"] = stopped
                append(directory / "raw.jsonl", row)
                continue
            before_ids = [call["id"] for call in snapshot["calls"] if call["scope"] == "experiments"]
        row["start_time"] = now()
        append(directory / "journal.jsonl", {"event": "invocation_started", "at": row["start_time"], "row_id": row["row_id"],
                                             "mode": mode, "experiment_ids_before": before_ids})
        start = time.monotonic()
        content = None
        if mode == "mock":
            row["local_attempted"] = True
            content = mock_content(row["sample_id"])
            if scenario == "mixed" and index == 0:
                content = "{broken"
            elif scenario == "mixed" and index == 1:
                row.update(status="timeout", error="LOCAL_SCRIPTED_TIMEOUT")
            elif scenario == "mixed" and index == 2:
                content = encoded({"answer": "mock invalid reference", "clue_refs": ["undiscovered_mock"],
                                   "next_action": None}).decode("utf-8")
        else:
            row["provider_invoked"] = True
            from .transport import observe
            original_transport, observer = observe(provider)
            try:
                reply = await provider.complete(messages, tools, CallLimits(max_tokens=1000, timeout_seconds=20), scope="experiments", tool_choice="none")
                row.update(call_id=reply.call_id, reported_model=reply.reported_model, usage=reply.usage,
                           normalized_response_received=True)
                if reply.tool_calls:
                    row.update(status="parse_invalid", error="UNEXPECTED_TOOL_CALL_WITH_CHOICE_NONE")
                else:
                    content = reply.content
            except ProviderError as error:
                metadata = provider.last_response_metadata or {}
                row.update(call_id=error.call_id, status="timeout" if error.code == "MODEL_TIMEOUT" else "failed", error=error.code,
                           reported_model=metadata.get("reported_model"), usage=metadata.get("usage"))
            finally:
                # Tri-state HTTP evidence comes from transport, never metadata.
                row.update(observer.fields())
                provider.transport = original_transport
            if row["call_id"]:
                current = ledger_read()
                billed(row, current)
                phase_charged_units += round(row["charged_upper_cny"] * 1e9)
            if row["call_id"] and not row["usage_known"] or row["error"] in {"MODEL_TIMEOUT", "UNAPPROVED_REPORTED_MODEL", "TOKEN_BOUND_EXCEEDED", "COST_BOUND_EXCEEDED", "MODEL_AUTH_ERROR", "MODEL_RATE_LIMIT"}:
                stopped = "STOP_AFTER_UNKNOWN_TIMEOUT_OR_PROVIDER_ABNORMALITY"
            if not row["call_id"]:
                row["status"] = "not_called"
                stopped = "PROVIDER_PREFLIGHT_STOP"
        if content is not None and row["status"] not in {"timeout", "failed", "parse_invalid"}:
            result = judge(content, sample)
            row.update(response=content, tool_proposal=result["next_action"], legal=result["legal"], correct=result["correct"],
                       reference_valid=result["reference_valid"], reference_sufficient=result["reference_sufficient"],
                       status="completed" if result["parse_valid"] else "parse_invalid", error=result["reason"])
        row["end_time"] = now()
        row["latency_seconds"] = time.monotonic() - start
        consecutive = consecutive + 1 if row["status"] in {"failed", "timeout", "parse_invalid"} else 0
        if mode == "real" and consecutive >= plan["freeze"]["config"]["max_consecutive_failures"]:
            stopped = "CONSECUTIVE_FAILURE_STOP"
        append(directory / "raw.jsonl", row)
        append(directory / "journal.jsonl", {"event": "row_finalized", "at": now(), "row_id": row["row_id"], "row_hash": sha(row)})
    write_new(directory / "completion.json", {"completed_at": now(), "stop_reason": stopped,
                                               "phase_charged_upper_cny": phase_charged_units / 1e9 if mode == "real" else None,
                                               "rows_hash": sha(rows), "real": mode == "real"})
    return rows


def reconcile(directory, snapshot=None):
    """Never resend. A unique new reservation proves attempt, not delivery."""
    from .summarize import read_rows
    directory = inside(directory)
    run, plan = load(directory / "run.json"), load(directory / "plan.json")
    final = read_rows(directory / "raw.jsonl") if (directory / "raw.jsonl").exists() else []
    if [r["row_id"] for r in final] != [r["row_id"] for r in plan["rows"][:len(final)]]:
        raise ValueError("CORRUPTED_FINAL_ROW_PREFIX")
    events = read_rows(directory / "journal.jsonl") if (directory / "journal.jsonl").exists() else []
    starts = {event["row_id"]: event for event in events if event["event"] == "invocation_started"}
    final_by_id = {row["row_id"]: row for row in final}
    rows = []
    paid_recovery = run["mode"] in {"real", "synthetic-real-recovery"}
    if run["mode"] == "synthetic-real-recovery" and snapshot is None:
        raise ValueError("SYNTHETIC_RECOVERY_REQUIRES_INJECTED_SNAPSHOT")
    if paid_recovery and snapshot is None:
        snapshot = ledger_read()
    for planned in plan["rows"]:
        row = deepcopy(final_by_id.get(planned["row_id"], planned))
        start = starts.get(row["row_id"])
        if row["row_id"] not in final_by_id:
            row["error"] = "NOT_CALLED_AFTER_INTERRUPTION"
            if start:
                row.update(status="failed", error="INTERRUPTED_NO_RETRY", start_time=start["at"],
                           actually_called=None if paid_recovery else False,
                           local_attempted=run["mode"] == "mock", provider_invoked=None if paid_recovery else False,
                           response_received=None if paid_recovery else False,
                           upstream_delivery_known=None if paid_recovery else False)
                if paid_recovery:
                    candidates = [call for call in snapshot["calls"] if call["scope"] == "experiments"
                                  and call["id"] not in start["experiment_ids_before"]]
                    # New later runs make temporal association ambiguous: do not infer.
                    if len(candidates) == 1 and candidates[0]["created_at"] >= start["at"]:
                        row["call_id"] = candidates[0]["id"]
                        billed(row, snapshot)
        rows.append(row)
    suffix = "reconciled-" + uuid.uuid4().hex[:8]
    for row in rows:
        append(directory / (suffix + ".jsonl"), row)
    write_new(directory / (suffix + "-audit.json"), {"at": now(), "source_raw_hash": sha(final), "no_resend": True,
                                                    "ledger": safe_ledger(snapshot) if snapshot else None,
                                                    "rows_hash": sha(rows), "known_paid_attempts": sum(r["actually_called"] is True for r in rows),
                                                    "uncertain_paid_attempts": sum(r["actually_called"] is None for r in rows)})
    return suffix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "check", "mock", "pilot", "run", "summarize", "reconcile"])
    parser.add_argument("--phase", choices=["pilot", "formal"], default="formal")
    parser.add_argument("--mode", choices=["mock", "real"], default="mock")
    parser.add_argument("--scenario", choices=["success", "mixed"], default="success")
    parser.add_argument("--authorization")
    parser.add_argument("--authorization-sha")
    parser.add_argument("--run-dir")
    args = parser.parse_args()
    if args.command == "check":
        from .check import main as check
        return check()
    if args.command in {"summarize", "reconcile"}:
        if not args.run_dir:
            raise ValueError("RUN_DIR_REQUIRED")
        if args.command == "summarize":
            from .summarize import summarize
            result = summarize(Path(args.run_dir))
            print(encoded(result).decode("utf-8"))
        else:
            with exclusive():
                print(reconcile(Path(args.run_dir)))
        return
    phase = "pilot" if args.command == "pilot" else args.phase
    mode = "plan" if args.command == "plan" else "mock" if args.command == "mock" else args.mode
    baseline_binding()
    plan = make_plan(phase)
    with exclusive():
        gate = approve(args.authorization, args.authorization_sha, plan) if mode == "real" else None
        directory = new_run(plan, mode, gate)
        if mode == "plan":
            for row in plan["rows"]:
                append(directory / "raw.jsonl", row)
        else:
            asyncio.run(execute(plan, directory, mode, gate, args.scenario))
        from .summarize import summarize
        summarize(directory)
    print(str(directory))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # No arbitrary upstream exception text, headers, credentials or bodies.
        print("EXPERIMENT_STOP:" + (str(error) if isinstance(error, ValueError) else type(error).__name__))
        raise SystemExit(1)
