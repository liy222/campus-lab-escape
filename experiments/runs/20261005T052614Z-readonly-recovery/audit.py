"""Append-only recovery inventory; no credentials, Provider or network."""
from pathlib import Path
from datetime import datetime, timezone
import json
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[3]
DEST = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from experiments.common import load, sha, encoded, experiment_hashes, baseline_binding
from experiments.plan import make_plan

before = experiment_hashes()
binding = baseline_binding()
plans = {phase: make_plan(phase) for phase in ("pilot", "formal")}
now = datetime.now(timezone.utc)
inventory, journals, real, orphan_journals = [], [], [], []
for directory in sorted((ROOT / "experiments/runs").iterdir()):
    if not directory.is_dir():
        continue
    run_path, journal_path = directory / "run.json", directory / "journal.jsonl"
    if run_path.exists():
        run = load(run_path)
        raw_path = directory / "raw.jsonl"
        rows = [json.loads(line) for line in raw_path.read_text(encoding="utf8").splitlines() if line.strip()] if raw_path.exists() else []
        item = {"directory": directory.name, "mode": run["mode"], "phase": run["phase"],
                "run_raw_sha256": sha(run_path.read_bytes()), "raw_rows": len(rows),
                "raw_sha256": sha(raw_path.read_bytes()) if raw_path.exists() else None,
                "completion_exists": (directory / "completion.json").exists(),
                "journal_exists": journal_path.exists(), "authorization_id": run.get("authorization_id"),
                "paid_attempts_confirmed_in_rows": sum(row.get("actually_called") is True for row in rows),
                "paid_attempts_uncertain_in_rows": sum(row.get("actually_called") is None for row in rows)}
        inventory.append(item)
        if run["mode"] == "real":
            real.append(item)
    if journal_path.exists():
        events = [json.loads(line) for line in journal_path.read_text(encoding="utf8").splitlines() if line.strip()]
        journals.append({"path": str(journal_path.relative_to(ROOT)).replace("\\", "/"),
                         "raw_sha256": sha(journal_path.read_bytes()), "events": len(events),
                         "modes": sorted({event["mode"] for event in events if "mode" in event}),
                         "run_exists": run_path.exists()})
        if not run_path.exists():
            orphan_journals.append(str(journal_path.relative_to(ROOT)).replace("\\", "/"))

# Original database opened strictly read-only. Aggregate stats only; no key/token data.
ledger_path = ROOT / "data/ai-budget.sqlite"
with sqlite3.connect(ledger_path.resolve().as_uri() + "?mode=ro", uri=True) as db:
    cap, is_frozen = db.execute("SELECT cap,frozen FROM budget_config WHERE id=1").fetchone()
    count, charged = db.execute("SELECT COUNT(*),COALESCE(SUM(charged),0) FROM budget_calls").fetchone()
    states = dict(db.execute("SELECT state,COUNT(*) FROM budget_calls GROUP BY state"))
    experiment_count = db.execute("SELECT COUNT(*) FROM budget_calls WHERE scope='experiments'").fetchone()[0]
    pending = db.execute("SELECT COUNT(*) FROM budget_calls WHERE state IN ('reserved','unknown')").fetchone()[0]
ledger = {"path": "data/ai-budget.sqlite", "mode": "ro", "total_calls": count,
          "cap_units": cap, "charged_units": charged, "remaining_units": max(0, cap-charged),
          "state_counts": states, "experiment_scope_calls": experiment_count,
          "pending_or_unknown": pending, "frozen": bool(is_frozen)}

authorizations = []
for path in sorted((ROOT / "experiments/authorizations").glob("*.json")):
    gate = load(path)
    expiry = datetime.fromisoformat(gate["expires_at"].replace("Z", "+00:00"))
    pricing_path = ROOT / gate["pricing_evidence"]
    price = load(pricing_path)
    checked = datetime.fromisoformat(price["checked_at_utc"].replace("Z", "+00:00"))
    authorizations.append({"path": str(path.relative_to(ROOT)).replace("\\", "/"),
                           "raw_sha256": sha(path.read_bytes()), "id": gate["id"], "phase": gate["phase"],
                           "expires_at": gate["expires_at"], "expired": now >= expiry,
                           "consumed_by_real_run": any(item["authorization_id"] == gate["id"] for item in real),
                           "pricing_path": gate["pricing_evidence"], "pricing_age_seconds": (now-checked).total_seconds(),
                           "pricing_fresh": 0 <= (now-checked).total_seconds() <= 86400,
                           "pricing_hash_matches": sha(pricing_path.read_bytes()) == gate["pricing_sha256"]})

plan_checks = {}
stored_paths = {"pilot": "20261002T125617836186Z-pilot-plan-07a086ba", "formal": "20261002T125600594673Z-formal-plan-949ddff0"}
for phase, plan in plans.items():
    stored_path = ROOT / "experiments/runs" / stored_paths[phase] / "plan.json"
    stored = load(stored_path)
    plan_checks[phase] = {"planned": plan["planned"], "plan_hash": sha(plan), "freeze_hash": sha(plan["freeze"]),
                          "matches_stored_plan": plan == stored, "source_plan": str(stored_path.relative_to(ROOT)).replace("\\", "/"),
                          "sum_reservation_units": sum(row["reservation_units"] for row in plan["rows"]),
                          "max_reservation_units": max(row["reservation_units"] for row in plan["rows"])}

after = experiment_hashes()
report = {"kind": "read-only-recovery-not-model-evidence-not-authorization", "at_utc": now.isoformat(),
          "actual_command": sys.argv, "python": sys.executable, "ledger": ledger,
          "inventory": inventory, "journals": journals, "real_runs": real, "orphan_journals": orphan_journals,
          "authorizations": authorizations, "plans": plan_checks, "source_hashes_before": before,
          "source_hashes_after": after, "experiment_sources_unchanged": before == after,
          "baseline": {"commit": binding["commit"], "manifest_raw_sha256": binding["manifest_raw_sha256"],
                       "bound_source_count": len(binding["sources"]), "bound_evidence_count": len(binding["artifacts"]),
                       "unbound_prior_source_records": binding["unbound_prior_source_records"],
                       "generated_runtime_only": binding["generated_runtime_only"], "limitations": binding["limitations"]},
          "baseline_binding_unchanged": binding == baseline_binding(),
          "reconcile_required": bool(orphan_journals or any(not item["completion_exists"] for item in real)),
          "env_read": False, "provider_constructed": False, "network_calls": 0, "paid_calls": 0,
          "limitations": ["Read-only recovery inventory is not independent QA or experimental outcome.",
                          "Aggregate original ledger and absent real-run artifacts establish no recorded experiment attempt; they do not certify unrelated external activity.",
                          "A new Main-issued finite gate and explicit GO remain required; old authorization is expired.",
                          "Formal execution remains blocked until real pilot known-usage results and separate Main review/GO."]}
if not report["experiment_sources_unchanged"] or not report["baseline_binding_unchanged"] or not all(item["matches_stored_plan"] for item in plan_checks.values()):
    raise ValueError("FROZEN_INPUT_CHANGED")
with (DEST / "recovery-audit.json").open("xb") as handle:
    handle.write(encoded(report) + b"\n")
print(json.dumps({"output": str(DEST / "recovery-audit.json"), "real_run_count": len(real),
                  "orphan_journals": orphan_journals, "journal_modes": [item["modes"] for item in journals],
                  "run_modes": {mode: sum(item["mode"] == mode for item in inventory) for mode in sorted({item["mode"] for item in inventory})},
                  "ledger": ledger, "plans": plan_checks, "source_unchanged": before == after,
                  "reconcile_required": report["reconcile_required"], "expired_authorizations": [item["id"] for item in authorizations if item["expired"]]}, ensure_ascii=False))
