"""Post-run read-only owner accounting, not independent QA."""
from pathlib import Path
from collections import Counter
import sys
sys.path.insert(0, str(Path.cwd()))
from experiments.common import load, sha, encoded, experiment_hashes, baseline_binding, now
from experiments.runner import ledger_read, safe_ledger
from experiments.summarize import read_rows

ROOT = Path.cwd()
DEST = ROOT / "experiments/runs/20261005T053334004502Z-formal-real-48d972eb"
run = load(DEST / "run.json")
plan = load(DEST / "plan.json")
rows = read_rows(DEST / "raw.jsonl")
summary = load(DEST / "summary.json")
completion = load(DEST / "completion.json")
before = load(ROOT / "experiments/runs/20261005T053300Z-formal-control/before.json")["shared_ledger"]
snapshot = ledger_read()
after = safe_ledger(snapshot)
after.update(total_calls=len(snapshot["calls"]), state_counts=dict(Counter(row["state"] for row in snapshot["calls"])),
             pending_or_unknown=sum(row["state"] in {"reserved", "unknown"} for row in snapshot["calls"]))
fields = ["row_id", "sample_id", "variant", "repeat", "status", "error", "actually_called", "call_id", "reported_model",
          "response_received", "http_status_code", "normalized_response_received", "usage_known", "usage", "charged_upper_cny",
          "latency_seconds", "legal", "correct", "reference_valid", "reference_sufficient", "tool_proposal", "input_hash"]
known = [row for row in rows if row["usage"] is not None]
report = {"at_utc": now(), "owner_accounting_only": True, "phase": run["phase"], "mode": run["mode"], "run_id": run["run_id"],
          "authorization_id": run["authorization_id"], "planned": plan["planned"], "rows": [{key: row.get(key) for key in fields} for row in rows],
          "completion": completion, "summary": summary, "shared_ledger_before": before, "shared_ledger_after": after,
          "shared_delta_charged_units": after["charged_units"] - before["charged_units"],
          "all_planned_rows_in_original_order": [row["row_id"] for row in rows] == [row["row_id"] for row in plan["rows"]],
          "usage_totals_known": {key: sum(row["usage"][key] for row in known) for key in ["prompt_tokens", "completion_tokens", "prompt_cache_hit_tokens", "total_tokens"]},
          "baseline": baseline_binding(),
          "experiment_sources_unchanged": experiment_hashes() == load(ROOT / "experiments/runs/20261005T052614Z-readonly-recovery/recovery-audit.json")["source_hashes_before"],
          "artifact_hashes": {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path.read_bytes()) for path in sorted(DEST.rglob("*")) if path.is_file()},
          "limitations": ["Owner accounting is not independent QA or Main acceptance.", "Real provider usage and ledger charges are not an independent invoice.",
                          "Action correctness does not certify all free-text claims.", "Fixed checkpoints and three repetitions do not establish general intelligence or autonomous completion.",
                          "Cache effects and unsent temperature/seed mean measured cost and latency are scoped to this run."]}
with (DEST / "owner-formal-report.json").open("xb") as handle:
    handle.write(encoded(report) + b"\n")
print(encoded({"run": run["run_id"], "rows": len(rows), "order_matches_plan": report["all_planned_rows_in_original_order"],
               "status_counts": dict(Counter(row["status"] for row in rows)), "error_counts": dict(Counter(row["error"] for row in rows if row["error"])),
               "usage_totals": report["usage_totals_known"], "charged_units_delta": report["shared_delta_charged_units"],
               "after": {key: val for key, val in after.items() if key != "experiment_calls"}, "completion": completion,
               "summary": {"by_variant": summary["by_variant"], "rows_hash": summary["rows_hash"]},
               "report_sha256": sha((DEST / "owner-formal-report.json").read_bytes()),
               "summary_sha256": sha((DEST / "summary.json").read_bytes()), "raw_sha256": sha((DEST / "raw.jsonl").read_bytes()),
               "sources_unchanged": report["experiment_sources_unchanged"]}).decode("utf8"))
