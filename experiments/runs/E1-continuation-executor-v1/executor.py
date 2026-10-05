"""Explicit 49-unit continuation envelope; immutable original v1 evidence."""
from __future__ import annotations
import argparse
import asyncio
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time
import uuid

HOME = Path(__file__).resolve().parent
ROOT = HOME.parents[2]
RUNS = ROOT / "experiments/runs"
ARCHIVE = ROOT / "release/archives/baseline_v1"
ORIGIN = RUNS / "20261005T053334004502Z-formal-real-48d972eb"
ARCHIVE_INDEX = ROOT / "evidence/integration/E1-source-archive-20261005.json"
ARCHIVE_SHA = "0dab9b9e213a3631a7630eb59cd0a27d8e44c74321891463ed7d71d599d285a6"
MANIFEST = ROOT / "evidence/integration/baseline_v1-manifest.json"
MANIFEST_SHA = "9c36943cbb6e4fe08b6e176445ba91835fafa79a2077c2155bbf8d613f8b07c1"
FREEZE_SHA = "f4436d0b4d9009788993092246b278e44c03021558bddb8b87337372b3eb1066"
PLAN_SHA = "bb9d603d75d16dcf9473e534a38687ce7a90d548035a6ad76ad682a16b459539"
ORIGIN_HASHES = {"run.json": "5f3042b1513bd191d241c3699e6519dafcae48b51e9727b4ff4b2e8e13689d3d",
 "plan.json": "c7a407bf1cb43232cf2a864d1bb26b64485a6ca788d7d32b7054adab9ee9746f",
 "raw.jsonl": "74c20c72ac39e236bd3e5c48062f71e2c98a92b9368269c3e67a95c841db2e28",
 "journal.jsonl": "f3db42fc64211c36be4420d9f3d2db4aa8e883b79ef35fc9f06413fb0fbc80d9",
 "completion.json": "ad2602b8aaed4c5d82b3fd6804617983f025ad5b6f31fc81932ebc49ecf09706",
 "summary.json": "83870be5f56b8f53a4c5be6a42fe049aee78c8159dac872f20ef04c74a4ecb11"}
SOURCE_FILES = ["executor.py", "v1_judge_worker.py", "schema.json", "README.md", "owner_tests.py"]
KIND = "E1-first-attempt-continuation-v1"
LEDGER = ROOT / "data/ai-budget.sqlite"
sys.path.insert(0, str(ROOT))
from experiments.common import encoded, load, sha, strict_load, experiment_hashes
from experiments.summarize import calculate


def now():
    return datetime.now(timezone.utc).isoformat()


def rawhash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lines(path):
    return [strict_load(line) for line in Path(path).read_text(encoding="utf8").splitlines() if line.strip()]


def output_path(path):
    path = Path(path).resolve()
    if not path.is_relative_to(RUNS.resolve()) or "continuation-" not in path.relative_to(RUNS).parts[0]:
        raise ValueError("NEW_CONTINUATION_OUTPUT_REQUIRED")
    return path


def write(path, value):
    path = output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(encoded(value) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())


def append(path, value):
    with output_path(path).open("ab") as handle:
        handle.write(encoded(value) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())


@contextmanager
def exclusive():
    path = HOME / "runtime/continuation.lock"
    path.parent.mkdir(exist_ok=True)
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


def source_manifest():
    return {"method": "new explicit raw source identity, separate from original f443", "files":
            {str((HOME / name).relative_to(ROOT)).replace("\\", "/"): rawhash(HOME / name) for name in SOURCE_FILES}}


def archive_precheck():
    if rawhash(ARCHIVE_INDEX) != ARCHIVE_SHA or rawhash(MANIFEST) != MANIFEST_SHA:
        raise ValueError("TRUSTED_ALIAS_OR_MANIFEST_CHANGED")
    registry, manifest = load(ARCHIVE_INDEX), load(MANIFEST)
    if registry["approved_by"] != "Main" or registry["count"] != 101 or len(registry["sources"]) != 101:
        raise ValueError("ARCHIVE_REGISTRATION_INVALID")
    aliases = {}
    for rel, record in registry["sources"].items():
        path = (ROOT / record["archive_path"]).resolve()
        if path != (ARCHIVE / rel).resolve() or not path.is_relative_to(ARCHIVE.resolve()) or rawhash(path) != record["raw_sha256"]:
            raise ValueError("ARCHIVE_RAW_CHANGED")
        aliases[rel] = {"archive_path": record["archive_path"], "raw_sha256": record["raw_sha256"]}
    for rel, record in manifest["sources"].items():
        data = (ROOT / aliases[rel]["archive_path"]).read_bytes()
        canonical = data.decode("utf8").replace("\r\n", "\n").encode("utf8")
        if sha(canonical) != record["utf8_lf_v1_sha256"]:
            raise ValueError("ARCHIVE_PRODUCT_CANONICAL_CHANGED")
    evidence = {}
    for record in manifest["evidence"]:
        data = (ROOT / record["path"]).read_bytes()
        if sha(data.decode("utf8").replace("\r\n", "\n").encode("utf8")) != record["artifact_utf8_lf_v1_sha256"]:
            raise ValueError("ORIGINAL_BASELINE_EVIDENCE_CHANGED")
        evidence[record["path"]] = sha(data)
    canonical_client = {}
    for rel in ["backend/__init__.py", "backend/app/__init__.py", "backend/app/ai/__init__.py", "backend/app/ai/provider.py", "backend/app/ai/budget.py"]:
        if rawhash(ROOT / rel) != aliases[rel]["raw_sha256"]:
            raise ValueError("CANONICAL_CLIENT_SOURCE_CHANGED")
        canonical_client[rel] = {"loaded_from": str(ROOT / rel), "raw_sha256": rawhash(ROOT / rel)}
    return {"archive_index_raw_sha256": ARCHIVE_SHA, "manifest_raw_sha256": MANIFEST_SHA,
            "logical_v1_aliases": aliases, "original_evidence_raw_sha256": evidence,
            "canonical_paid_client": canonical_client, "canonical_ledger": str(LEDGER),
            "v1_judge_only_in_child": True}


def request_parts(saved):
    # Original input artifacts use sorted JSON keys. Restore only the original
    # serializer insertion order, using exact registered v1 tool bytes; values
    # and message text must be equal to the saved artifact.
    tools = load(ARCHIVE / "contracts/tools.json")
    if saved["tools"] != tools or len(saved["messages"]) != 2:
        raise ValueError("SAVED_REQUEST_STRUCTURE_CHANGED")
    messages = []
    for item, role in zip(saved["messages"], ["system", "user"]):
        if set(item) != {"role", "content"} or item["role"] != role or not isinstance(item["content"], str):
            raise ValueError("SAVED_MESSAGES_CHANGED")
        messages.append({"role": item["role"], "content": item["content"]})
    return messages, deepcopy(tools)


def wire_bytes(saved):
    messages, tools = request_parts(saved)
    for tool in tools:
        tool["function"].pop("strict", None)
    payload = {"model": "deepseek-flash", "messages": messages, "max_tokens": 1000,
               "thinking": {"type": "disabled"}, "stream": False}
    payload.update(tools=tools, tool_choice="none")
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf8")


def prepare():
    dependencies = archive_precheck()
    for filename, expected in ORIGIN_HASHES.items():
        if rawhash(ORIGIN / filename) != expected:
            raise ValueError("ORIGIN_RAW_CHANGED")
    original, results, events = load(ORIGIN / "plan.json"), lines(ORIGIN / "raw.jsonl"), lines(ORIGIN / "journal.jsonl")
    if sha(original) != PLAN_SHA or sha(original["freeze"]) != FREEZE_SHA or experiment_hashes() != original["freeze"]["source_hashes"]:
        raise ValueError("ORIGINAL_EXPERIMENT_FREEZE_CHANGED")
    if len(results) != 72 or [r["row_id"] for r in results] != [r["row_id"] for r in original["rows"]]:
        raise ValueError("ORIGIN_ROW_IDENTITY_CHANGED")
    starts = {event["row_id"] for event in events if event["event"] == "invocation_started"}
    rows, identity = [], []
    for planned, result in zip(original["rows"], results):
        if result["status"] != "not_called":
            continue
        if result["actually_called"] is not False or result["provider_invoked"] is not False or result["call_id"] is not None or result["start_time"] is not None or result["row_id"] in starts:
            raise ValueError("UNCERTAIN_ORIGIN_UNIT_INELIGIBLE")
        path = ORIGIN / "inputs" / (planned["row_id"] + ".json")
        saved = load(path)
        payload = wire_bytes(saved)
        bound = len(payload) * 4 + 8192
        if sha(payload) != planned["input_hash"] or saved["input_hash"] != planned["input_hash"] or bound != planned["input_token_bound"] or len(payload) != planned["payload_utf8_bytes"] or bound * 2000 + 1000 * 8000 != planned["reservation_units"]:
            raise ValueError("ORIGINAL_INPUT_CHANGED")
        rows.append(deepcopy(planned))
        identity.append({"row_id": planned["row_id"], "sample_id": planned["sample_id"], "variant": planned["variant"],
                         "repeat": planned["repeat"], "original_order": planned["order"], "input_hash": planned["input_hash"],
                         "input_artifact_raw_sha256": rawhash(path)})
    if len(rows) != 49 or [r["order"] for r in rows] != list(range(24, 73)):
        raise ValueError("EXACT_49_UNIT_WHITELIST_REQUIRED")
    return {"kind": KIND, "phase": "continuation", "planned": 49, "rows": rows, "original_freeze": original["freeze"],
            "original_plan_hash": PLAN_SHA, "origin_run_id": ORIGIN.name, "origin_artifact_hashes": ORIGIN_HASHES,
            "selected_identity": identity, "selected_identity_hash": sha(identity), "execution_sources": source_manifest(),
            "dependencies": dependencies, "controls": original["controls"], "retry": False,
            "reservation_sum_units": sum(r["reservation_units"] for r in rows), "max_calls": 49,
            "origin_timeout_remains_null": True, "one_continuation_per_origin": True}


def assert_plan(plan):
    if prepare() != plan:
        raise ValueError("CONTINUATION_SOURCE_OR_INPUT_CHANGED")


def read_ledger(path=LEDGER):
    with sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        cap, frozen = db.execute("SELECT cap,frozen FROM budget_config WHERE id=1").fetchone()
        calls = [dict(row) for row in db.execute("SELECT id,scope,created_at,reserved,charged,state,reason,prompt_tokens,completion_tokens,cache_hit_tokens FROM budget_calls")]
    charged = sum(row["charged"] for row in calls)
    return {"cap_units": cap, "charged_units": charged, "remaining_units": max(0, cap-charged), "frozen": bool(frozen), "calls": calls}


def safe_snapshot(snapshot):
    return {key: value for key, value in snapshot.items() if key != "calls"} | {
        "total_calls": len(snapshot["calls"]), "pending_or_unknown": sum(r["state"] in {"reserved", "unknown"} for r in snapshot["calls"]),
        "experiment_calls": [r for r in snapshot["calls"] if r["scope"] == "experiments"]}


def verify_evidence(rel, expected, area):
    path = (ROOT / rel).resolve()
    if not path.is_relative_to((ROOT / area).resolve()) or rawhash(path) != expected:
        raise ValueError("GATE_REVIEW_EVIDENCE_CHANGED")


def validate_gate(gate, plan, snapshot, at=None):
    from jsonschema import Draft202012Validator
    Draft202012Validator(load(HOME / "schema.json")).validate(gate)
    if gate["approved_by"] != "Main" or gate["approved"] is not True or gate["phase"] != "continuation" or gate["kind"] != KIND:
        raise ValueError("NEW_MAIN_CONTINUATION_GO_REQUIRED")
    for key, expected in {"plan_hash": sha(plan), "original_freeze_hash": FREEZE_SHA, "original_plan_hash": PLAN_SHA,
                          "origin_run_id": ORIGIN.name, "selected_identity_hash": plan["selected_identity_hash"],
                          "execution_sources_hash": sha(plan["execution_sources"]), "archive_index_sha256": ARCHIVE_SHA,
                          "baseline_manifest_sha256": MANIFEST_SHA, "dependencies_hash": sha(plan["dependencies"])}.items():
        if gate[key] != expected:
            raise ValueError("GATE_BOUND_IDENTITY_MISMATCH")
    current = at or datetime.now(timezone.utc)
    expiry = datetime.fromisoformat(gate["expires_at"].replace("Z", "+00:00"))
    if expiry.tzinfo is None or current >= expiry:
        raise ValueError("GO_EXPIRED")
    verify_evidence(gate["pricing_evidence"], gate["pricing_sha256"], "evidence/integration")
    pricing = load(ROOT / gate["pricing_evidence"])
    checked = datetime.fromisoformat(pricing["checked_at_utc"].replace("Z", "+00:00"))
    if checked.tzinfo is None or not 0 <= (current-checked).total_seconds() <= 86400 or pricing["peak_cny_per_million"] != {"input_miss": 2, "input_hit": .04, "output": 8}:
        raise ValueError("FRESH_PRICING_REQUIRED")
    pilot = RUNS / gate["pilot_run_id"]
    if pilot.resolve().parent != RUNS.resolve() or gate["pilot_run_id"] != "20261005T052822923700Z-pilot-real-0378672e" or rawhash(pilot / "summary.json") != gate["pilot_summary_sha256"]:
        raise ValueError("PILOT_IDENTITY_REQUIRED")
    pilot_summary = load(pilot / "summary.json")
    if load(pilot / "run.json")["mode"] != "real" or gate["pilot_review_accepted"] is not True or any(g["completed"] != 3 or g["usage_known_rows"] != 3 for g in pilot_summary["by_variant"].values()):
        raise ValueError("PILOT_REVIEW_REQUIRED")
    verify_evidence(gate["candidate_qa_evidence"], gate["candidate_qa_sha256"], "evidence/qa")
    verify_evidence(gate["accounting_closure_evidence"], gate["accounting_closure_sha256"], "evidence/integration")
    if gate["candidate_qa_accepted"] is not True or gate["accounting_closure_accepted"] is not True:
        raise ValueError("INDEPENDENT_REVIEW_REQUIRED")
    if snapshot["cap_units"] != 10_000_000_000 or snapshot["frozen"] or any(c["state"] in {"reserved", "unknown"} for c in snapshot["calls"]):
        raise ValueError("CANONICAL_SHARED_BUDGET_BLOCKED")
    if gate["additional_upper_cap_units"] > snapshot["remaining_units"]:
        raise ValueError("PHASE_CAP_EXCEEDS_SHARED_REMAINDER")
    return gate


def started_guard(plan, gate):
    started_guard_records(plan, gate, [load(path) for path in RUNS.rglob("admission.json")])
    for path in RUNS.glob("*/run.json"):
        run = load(path)
        if run.get("authorization_id") == gate["id"]:
            raise ValueError("GO_ALREADY_CONSUMED")
        if run.get("mode") == "real" and not (path.parent / "completion.json").exists():
            audits = list(path.parent.glob("reconciled-*-audit.json"))
            if not audits or any(load(a)["uncertain_paid_attempts"] for a in audits):
                raise ValueError("PRIOR_CRASH_REQUIRES_READONLY_RECONCILIATION")


def started_guard_records(plan, gate, admissions):
    for item in admissions:
        if item.get("mode") == "real" and (item.get("origin_run_id") == plan["origin_run_id"] or item.get("authorization_id") == gate["id"]):
            raise ValueError("ORIGIN_CONTINUATION_ALREADY_ADMITTED_NO_REPLAY")


def admit(path, expected_hash, plan):
    if path is None or expected_hash is None:
        raise ValueError("REAL_REQUIRES_NEW_MAIN_GO")
    path = Path(path).resolve()
    if not path.is_relative_to((ROOT / "experiments/authorizations").resolve()) or rawhash(path) != expected_hash:
        raise ValueError("AUTHORIZATION_RAW_OR_PATH_MISMATCH")
    assert_plan(plan)
    gate = load(path)
    started_guard(plan, gate)
    return validate_gate(gate, plan, read_ledger())


def judge_batch(items):
    worker = HOME / "v1_judge_worker.py"
    env = {key: value for key, value in os.environ.items() if key.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "USERPROFILE", "LOCALAPPDATA", "APPDATA"}}
    result = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", str(worker)],
                            input=encoded({"requests": items}).decode("utf8"), text=True, encoding="utf8",
                            capture_output=True, cwd=HOME, env=env, timeout=90)
    if result.returncode != 0 or len(result.stdout.encode("utf8")) > 2_000_000:
        raise ValueError("ISOLATED_V1_JUDGE_FAILED")
    reply = strict_load(result.stdout)
    if reply["level_version"] != "1.0.0" or reply["provider_imported"] or reply["canonical_product_imported"] or reply["ledger_accessed"] or len(reply["results"]) != len(items):
        raise ValueError("ISOLATED_JUDGE_EVIDENCE_INVALID")
    for rel, record in reply["dependencies"].items():
        expected = load(ARCHIVE_INDEX)["sources"][rel]
        if record["path"] != str((ROOT / expected["archive_path"]).resolve()) or record["raw_sha256"] != expected["raw_sha256"]:
            raise ValueError("ISOLATED_JUDGE_SOURCE_MISMATCH")
    return reply


def local_content(sample_id):
    truth = load(ARCHIVE / "experiments/ground_truth" / (sample_id + ".json"))
    return encoded({"answer": "本地注入参考动作；不是模型观察。", "clue_refs": truth["required_code_refs"],
                    "next_action": {**truth["acceptable_actions"][0], "clue_refs": truth["required_code_refs"], "summary": "本地脚本建议"}}).decode("utf8")


def new_run(plan, mode, directory=None, gate=None, before=None):
    directory = output_path(directory or RUNS / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-continuation-" + mode + "-" + uuid.uuid4().hex[:8]))
    directory.mkdir(parents=True, exist_ok=False)
    if mode == "real":
        write(directory / "admission.json", {"kind": KIND, "mode": mode, "origin_run_id": plan["origin_run_id"], "authorization_id": gate["id"], "at": now()})
    write(directory / "run.json", {"kind": KIND, "phase": "continuation", "mode": mode, "run_id": directory.name,
                                  "origin_run_id": plan["origin_run_id"], "planned": 49, "plan_hash": sha(plan), "created_at": now(),
                                  "authorization_id": gate["id"] if gate else None, "authorization": gate,
                                  "execution_sources": plan["execution_sources"], "dependencies": plan["dependencies"],
                                  "shared_ledger_before": safe_snapshot(before) if before else None,
                                  "command": sys.argv, "python": sys.executable, "real_calls_allowed": mode == "real"})
    write(directory / "plan.json", plan)
    for row in plan["rows"]:
        saved = load(ORIGIN / "inputs" / (row["row_id"] + ".json"))
        write(directory / "inputs" / (row["row_id"] + ".json"), saved)
    return directory


class IntentionalSyntheticCrash(BaseException):
    pass


async def execute(plan, directory, mode, *, provider=None, cap_units=5_300_000_000, ledger_path=None, scenario="success", crash_after_call=False):
    from backend.app.ai.provider import CallLimits, ProviderError
    import httpx
    if mode not in {"real", "mock", "synthetic-transport"}:
        raise ValueError("EXECUTION_MODE_REQUIRED")
    if mode == "real":
        if crash_after_call or scenario != "success" or ledger_path not in {None, LEDGER} or provider is None or provider.ledger.path != LEDGER.resolve() or provider.transport is not None:
            raise ValueError("CANONICAL_REAL_CLIENT_REQUIRED")
    elif mode == "synthetic-transport":
        if provider is None or not isinstance(provider.transport, httpx.MockTransport) or not provider.ledger.path.is_relative_to(RUNS.resolve()) or provider.ledger.path == LEDGER.resolve():
            raise ValueError("ISOLATED_MOCK_TRANSPORT_REQUIRED")
        ledger_path = provider.ledger.path
    elif provider is not None:
        raise ValueError("PURE_MOCK_PROVIDER_FORBIDDEN")
    rows, stopped, consecutive, charge, judged_cache = deepcopy(plan["rows"]), None, 0, 0, {}
    for index, row in enumerate(rows):
        if stopped:
            row["error"] = stopped
            append(directory / "raw.jsonl", row)
            continue
        try:
            assert_plan(plan)
        except ValueError:
            stopped = "CONTINUATION_SOURCE_OR_INPUT_CHANGED"
            row["error"] = stopped
            append(directory / "raw.jsonl", row)
            continue
        saved = load(ORIGIN / "inputs" / (row["row_id"] + ".json"))
        before_ids = []
        if mode != "mock":
            snapshot = read_ledger(ledger_path or LEDGER)
            if snapshot["frozen"] or snapshot["remaining_units"] < row["reservation_units"] or any(r["state"] in {"reserved", "unknown"} for r in snapshot["calls"]):
                stopped = "SHARED_BUDGET_STOP"
            elif charge + row["reservation_units"] > cap_units:
                stopped = "PHASE_UPPER_CAP_STOP"
            if stopped:
                row["error"] = stopped
                append(directory / "raw.jsonl", row)
                continue
            before_ids = [r["id"] for r in snapshot["calls"] if r["scope"] == "experiments"]
        row["start_time"] = now()
        append(directory / "journal.jsonl", {"event": "invocation_started", "at": row["start_time"], "row_id": row["row_id"],
                                              "mode": mode, "experiment_ids_before": before_ids, "input_hash": row["input_hash"]})
        start, content = time.monotonic(), None
        if mode == "mock":
            row["local_attempted"] = True
            content = local_content(row["sample_id"])
            if scenario == "mixed" and index == 0:
                content = "{broken"
            elif scenario == "mixed" and index == 1:
                row.update(status="timeout", error="LOCAL_SCRIPTED_TIMEOUT")
                content = None
        else:
            row["provider_invoked"] = True
            original = provider.transport
            inner = original if mode == "synthetic-transport" else httpx.AsyncHTTPTransport(trust_env=False, retries=0)

            class WireReceipt(httpx.AsyncBaseTransport):
                invoked, received, code = False, None, None
                async def handle_async_request(self, request):
                    if request.url != httpx.URL("https://api.deepseek.com/chat/completions") or sha(request.content) != row["input_hash"] or len(request.content) != row["payload_utf8_bytes"]:
                        raise ValueError("WIRE_INPUT_IDENTITY_MISMATCH")
                    self.invoked = True
                    response = await inner.handle_async_request(request)
                    self.received, self.code = True, response.status_code
                    return response
                async def aclose(self):
                    await inner.aclose()
            observer = WireReceipt()
            provider.transport = observer
            try:
                messages, tools = request_parts(saved)
                reply = await provider.complete(messages, tools, CallLimits(max_tokens=1000, timeout_seconds=20), scope="experiments", tool_choice="none")
                row.update(call_id=reply.call_id, reported_model=reply.reported_model, usage=reply.usage, normalized_response_received=True)
                if reply.tool_calls:
                    row.update(status="parse_invalid", error="UNEXPECTED_TOOL_CALL_WITH_CHOICE_NONE")
                else:
                    content = reply.content
            except ProviderError as error:
                metadata = provider.last_response_metadata or {}
                row.update(call_id=error.call_id, status="timeout" if error.code == "MODEL_TIMEOUT" else "failed", error=error.code,
                           reported_model=metadata.get("reported_model"), usage=metadata.get("usage"))
            finally:
                received = observer.received if observer.invoked else False
                row.update(response_received=received, upstream_delivery_known=received, http_status_code=observer.code)
                provider.transport = original
            if crash_after_call:
                raise IntentionalSyntheticCrash()
            if row["call_id"]:
                snapshot = read_ledger(ledger_path or LEDGER)
                billed = next((r for r in snapshot["calls"] if r["id"] == row["call_id"] and r["scope"] == "experiments"), None)
                if billed is None:
                    raise ValueError("CALL_NOT_IN_CANONICAL_LEDGER")
                row.update(actually_called=mode == "real", local_attempted=mode != "real", synthetic_reservation=mode != "real",
                           charged_upper_cny=billed["charged"] / 1e9)
                charge += billed["charged"]
                p, c, h = billed["prompt_tokens"], billed["completion_tokens"], billed["cache_hit_tokens"]
                if billed["state"] == "settled" and all(type(n) is int and n >= 0 for n in (p, c, h)) and h <= p:
                    row.update(usage_known=True, usage={"prompt_tokens": p, "completion_tokens": c, "prompt_cache_hit_tokens": h, "total_tokens": p+c})
                else:
                    row.update(usage_known=False, usage=None)
            if row["call_id"] and not row["usage_known"] or row["error"] in {"MODEL_TIMEOUT", "UNAPPROVED_REPORTED_MODEL", "TOKEN_BOUND_EXCEEDED", "COST_BOUND_EXCEEDED", "MODEL_AUTH_ERROR", "MODEL_RATE_LIMIT"}:
                stopped = "STOP_AFTER_UNKNOWN_TIMEOUT_OR_PROVIDER_ABNORMALITY"
            if not row["call_id"]:
                row["status"] = "not_called"
                stopped = "PROVIDER_PREFLIGHT_STOP"
        row["provider_latency_seconds"] = time.monotonic()-start if mode != "mock" else None
        if content is not None and row["status"] not in {"timeout", "failed", "parse_invalid"}:
            try:
                cache_key = (row["sample_id"], content)
                if cache_key not in judged_cache:
                    judged_cache[cache_key] = judge_batch([{"sample_id": row["sample_id"], "content": content}])
                judged = judged_cache[cache_key]
                result = judged["results"][0]
                row.update(response=content, tool_proposal=result["next_action"], legal=result["legal"], correct=result["correct"],
                           reference_valid=result["reference_valid"], reference_sufficient=result["reference_sufficient"],
                           status="completed" if result["parse_valid"] else "parse_invalid", error=result["reason"],
                           v1_judge_dependencies=judged["modules"])
            except ValueError:
                row.update(status="failed", error="ISOLATED_V1_JUDGE_FAILED")
                stopped = "STOP_AFTER_JUDGER_FAILURE"
        row["end_time"], row["latency_seconds"] = now(), time.monotonic()-start
        consecutive = consecutive+1 if row["status"] in {"failed", "timeout", "parse_invalid"} else 0
        if mode != "mock" and consecutive >= 2:
            stopped = stopped or "CONSECUTIVE_FAILURE_STOP"
        append(directory / "raw.jsonl", row)
        append(directory / "journal.jsonl", {"event": "row_finalized", "at": now(), "row_id": row["row_id"], "row_hash": sha(row)})
    write(directory / "completion.json", {"at": now(), "stop_reason": stopped, "rows_hash": sha(rows),
                                          "phase_charged_upper_cny": charge/1e9 if mode != "mock" else None,
                                          "real": mode == "real", "planned": 49})
    write(directory / "summary.json", {**calculate(rows), "phase": "continuation", "mode": mode,
                                       "origin_run_id": ORIGIN.name, "plan_hash": sha(plan), "new_sources": source_manifest(),
                                       "limitations": ["Separated continuation batch; changed time/cache/order continuity.", "Synthetic transport is not paid model evidence.", "latency_seconds includes isolated judgement; provider_latency_seconds separates the call boundary. Original batch did not record this separate metric."]})
    return rows


def reconcile(directory, *, synthetic_snapshot=None):
    directory = output_path(directory)
    run, plan = load(directory / "run.json"), load(directory / "plan.json")
    if run["kind"] != KIND:
        raise ValueError("CONTINUATION_RUN_REQUIRED")
    if plan != prepare() or run["plan_hash"] != sha(plan):
        raise ValueError("RECOVERY_PLAN_BINDING_CHANGED")
    if run["mode"] != "real" and synthetic_snapshot is None:
        raise ValueError("SYNTHETIC_SNAPSHOT_REQUIRED")
    snapshot = read_ledger() if run["mode"] == "real" else synthetic_snapshot
    final = lines(directory / "raw.jsonl") if (directory / "raw.jsonl").exists() else []
    if [r["row_id"] for r in final] != [r["row_id"] for r in plan["rows"][:len(final)]]:
        raise ValueError("CORRUPTED_FINAL_PREFIX")
    for row, original in zip(final, plan["rows"]):
        if any(row[key] != original[key] for key in ["row_id", "sample_id", "variant", "repeat", "order", "phase", "input_hash", "commit"]):
            raise ValueError("RECOVERY_ROW_IDENTITY_CHANGED")
    events = lines(directory / "journal.jsonl") if (directory / "journal.jsonl").exists() else []
    starts = {e["row_id"]: e for e in events if e["event"] == "invocation_started"}
    finals = {r["row_id"]: r for r in final}
    rows = []
    for planned in plan["rows"]:
        row = deepcopy(finals.get(planned["row_id"], planned))
        if row["row_id"] not in finals:
            row["error"] = "NOT_CALLED_AFTER_INTERRUPTION"
            if row["row_id"] in starts:
                event = starts[row["row_id"]]
                row.update(status="failed", error="INTERRUPTED_NO_RETRY", start_time=event["at"], provider_invoked=None,
                           actually_called=None, response_received=None, upstream_delivery_known=None)
                candidates = [c for c in snapshot["calls"] if c["scope"] == "experiments" and c["id"] not in event["experiment_ids_before"] and c["created_at"] >= event["at"]]
                if len(candidates) == 1:
                    call = candidates[0]
                    row.update(call_id=call["id"], actually_called=run["mode"] == "real", synthetic_reservation=run["mode"] != "real", charged_upper_cny=call["charged"]/1e9)
                    p, c, h = call["prompt_tokens"], call["completion_tokens"], call["cache_hit_tokens"]
                    if call["state"] == "settled" and all(type(n) is int and n >= 0 for n in (p, c, h)) and h <= p:
                        row.update(usage_known=True, usage={"prompt_tokens": p, "completion_tokens": c, "prompt_cache_hit_tokens": h, "total_tokens": p+c})
        rows.append(row)
    stem = "reconciled-" + uuid.uuid4().hex[:8]
    for row in rows:
        append(directory / (stem + ".jsonl"), row)
    write(directory / (stem + "-audit.json"), {"at": now(), "no_resend": True, "uncertain_paid_attempts": sum(r["actually_called"] is None for r in rows),
                                              "rows_hash": sha(rows), "ledger": safe_snapshot(snapshot), "original_raw_unchanged": rawhash(ORIGIN / "raw.jsonl") == ORIGIN_HASHES["raw.jsonl"]})
    return stem


def merge(directory, output, *, filename="raw.jsonl", allow_synthetic=False):
    directory = output_path(directory)
    run, plan = load(directory / "run.json"), load(directory / "plan.json")
    if run["kind"] != KIND or run["mode"] != "real" and not allow_synthetic:
        raise ValueError("REAL_CONTINUATION_REQUIRED")
    if plan != prepare() or run["plan_hash"] != sha(plan):
        raise ValueError("MERGE_PLAN_BINDING_CHANGED")
    if filename != "raw.jsonl" and not re.fullmatch(r"reconciled-[0-9a-f]{8}\.jsonl", filename):
        raise ValueError("REGISTERED_RECONCILED_FILE_REQUIRED")
    new = lines(directory / filename)
    if [r["row_id"] for r in new] != [r["row_id"] for r in plan["rows"]]:
        raise ValueError("MERGE_DUPLICATE_OR_INCOMPLETE_UNITS")
    original = lines(ORIGIN / "raw.jsonl")
    new_by_id, rows, lineage = {r["row_id"]: r for r in new}, [], []
    original_plan = load(ORIGIN / "plan.json")
    for old, planned in zip(original, original_plan["rows"]):
        current = new_by_id.get(old["row_id"])
        if current:
            if old["status"] != "not_called" or old["actually_called"] is not False or old["start_time"] is not None:
                raise ValueError("ORIGINAL_ATTEMPT_REPLACEMENT_FORBIDDEN")
            for field in ["row_id", "sample_id", "variant", "repeat", "order", "phase", "input_hash", "commit"]:
                if current[field] != planned[field]:
                    raise ValueError("MERGE_INPUT_IDENTITY_CHANGED")
            selected, source = deepcopy(current), directory.name
        else:
            selected, source = deepcopy(old), ORIGIN.name
        item = {"row_id": old["row_id"], "original_status": old["status"], "original_row_hash": sha(old),
                "selected_result_run_id": source, "selected_result_row_hash": sha(selected),
                "transition": "not_called_to_first_attempt" if current and (current["actually_called"] is not False or current.get("synthetic_reservation")) else "not_called_retained" if current else "original_first_attempt_retained",
                "actual_attempt_count": 1 if selected["actually_called"] is True else None if selected["actually_called"] is None else 0}
        rows.append(selected)
        lineage.append(item)
    output = output_path(output)
    output.mkdir(parents=True, exist_ok=False)
    for row in rows:
        append(output / "merged.jsonl", row)
    write(output / "lineage.json", {"kind": KIND, "origin": ORIGIN.name, "continuation": directory.name, "units": lineage,
                                     "original_artifacts": ORIGIN_HASHES, "continuation_raw_sha256": rawhash(directory / filename), "synthetic": run["mode"] != "real"})
    write(output / "summary.json", {**calculate(rows), "planned": 72, "source_batches": [ORIGIN.name, directory.name],
                                    "original_timeout_not_rebilled_or_rejudged": True, "synthetic": run["mode"] != "real",
                                    "phase_costs": {"original_charged_upper_cny": sum(r["charged_upper_cny"] or 0 for r in original), "continuation_charged_upper_cny": sum(r["charged_upper_cny"] or 0 for r in new)},
                                    "limitations": ["First attempts across separated batches; pause/cache/load/order continuity changed.", "Old timeout response/token usage remain unknown despite accounting closure.", "Merged latency_seconds mixes old in-process and new isolated-judge overhead; compare phase-specific provider_latency separately, not as identical measurements.", "No superiority or autonomous completion claim; failures remain."]})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["plan", "mock", "real", "reconcile", "merge"])
    parser.add_argument("--authorization")
    parser.add_argument("--authorization-sha")
    parser.add_argument("--run-dir")
    parser.add_argument("--output")
    parser.add_argument("--filename", default="raw.jsonl")
    args = parser.parse_args()
    with exclusive():
        if args.command == "reconcile":
            print(reconcile(args.run_dir))
            return
        if args.command == "merge":
            print(len(merge(args.run_dir, args.output, filename=args.filename)))
            return
        plan = prepare()
        if args.command == "plan":
            directory = new_run(plan, "plan", args.output)
        elif args.command == "mock":
            directory = new_run(plan, "mock", args.output)
            asyncio.run(execute(plan, directory, "mock"))
        else:
            gate = admit(args.authorization, args.authorization_sha, plan)
            before = read_ledger()
            directory = new_run(plan, "real", args.output, gate, before)
            # Sole credential loader/production Provider construction branch.
            from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider
            from backend.app.ai.budget import PROJECT_ROOT
            if PROJECT_ROOT.resolve() != ROOT.resolve():
                raise ValueError("CANONICAL_PROVIDER_ROOT_REQUIRED")
            provider = DeepSeekProvider(DeepSeekConfig.from_environment())
            asyncio.run(execute(plan, directory, "real", provider=provider, cap_units=gate["additional_upper_cap_units"]))
            write(directory / "shared-ledger-after.json", safe_snapshot(read_ledger()))
        print(str(directory))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("CONTINUATION_STOP:" + (str(error) if isinstance(error, ValueError) else type(error).__name__))
        raise SystemExit(1)
