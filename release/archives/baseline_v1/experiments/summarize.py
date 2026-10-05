"""Summaries derive from every planned row, including failures and unknowns."""
import csv
import math
import statistics

from .common import inside, load, sha, strict_load, write_new


def read_rows(path):
    return [strict_load(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def calculate(rows):
    groups = {}
    for variant in ("full_history", "structured_summary"):
        selected = [row for row in rows if row["variant"] == variant]
        n = len(selected)
        called = sum(row["actually_called"] is True for row in selected)
        uncertain = sum(row["actually_called"] is None for row in selected)
        completed = sum(row["status"] == "completed" for row in selected)
        legal = sum(row["legal"] is True for row in selected)
        correct = sum(row["correct"] is True for row in selected)
        refvalid = sum(row["reference_valid"] is True for row in selected)
        known = [row for row in selected if row["usage"] is not None]
        latencies = sorted(row["latency_seconds"] for row in selected if row["latency_seconds"] is not None)
        costs = [row["charged_upper_cny"] for row in selected if row["charged_upper_cny"] is not None]
        def ratio(num, den):
            return num / den if den else None
        groups[variant] = {"planned": n, "paid_attempts_confirmed": called, "paid_attempts_uncertain": uncertain,
                           "local_attempts": sum(row["local_attempted"] is True for row in selected),
                           "responses_received": sum(row["response_received"] is True for row in selected),
                           "responses_unknown": sum(row["response_received"] is None for row in selected),
                           "responses_not_received": sum(row["response_received"] is False for row in selected),
                           "delivery_confirmed": sum(row["upstream_delivery_known"] is True for row in selected),
                           "delivery_unknown": sum(row["upstream_delivery_known"] is None for row in selected),
                           "delivery_not_attempted": sum(row["upstream_delivery_known"] is False for row in selected),
                           "normalized_responses_received": sum(row.get("normalized_response_received") is True for row in selected),
                           "completed": completed, "legal": legal, "correct": correct, "reference_valid": refvalid,
                           "reference_sufficient": sum(row["reference_sufficient"] is True for row in selected),
                           "completed_per_planned": ratio(completed, n), "completed_per_paid_attempt": ratio(completed, called),
                           "legal_per_completed": ratio(legal, completed), "correct_per_completed": ratio(correct, completed),
                           "correct_per_planned": ratio(correct, n), "reference_valid_per_completed": ratio(refvalid, completed),
                           "usage_known_rows": len(known), "usage_coverage_per_planned": ratio(len(known), n),
                           "prompt_tokens_mean_known": statistics.mean(row["usage"]["prompt_tokens"] for row in known) if known else None,
                           "completion_tokens_mean_known": statistics.mean(row["usage"]["completion_tokens"] for row in known) if known else None,
                           "latency_known_rows": len(latencies), "latency_median_seconds": statistics.median(latencies) if latencies else None,
                           "latency_p95_nearest_rank_seconds": latencies[math.ceil(.95 * len(latencies)) - 1] if latencies else None,
                           "cost_known_rows": len(costs), "charged_upper_sum_known_cny": sum(costs) if costs else None,
                           "status_counts": {status: sum(row["status"] == status for row in selected) for status in sorted({r["status"] for r in selected})}}
    return {"by_variant": groups, "row_count": len(rows), "rows_hash": sha(rows),
            "limits": ["Fixed level/checkpoints only; no autonomous completion or general statistical superiority claim.",
                       "Mock outputs are injected fixtures, not model observations; tokens/cost remain null.",
                       "Action correctness excludes free-text hallucination certification.",
                       "Unknown costs and paid attempts are reported, not replaced by zero."]}


def summarize(run_dir, filename="raw.jsonl", output_name="summary"):
    run_dir = inside(run_dir)
    manifest = load(run_dir / "run.json")
    rows = read_rows(run_dir / filename)
    planned = load(run_dir / "plan.json")["rows"]
    if [row["row_id"] for row in rows] != [row["row_id"] for row in planned]:
        raise ValueError("INCOMPLETE_OR_REORDERED_PLANNED_ROWS")
    for row, source in zip(rows, planned):
        for field in ("sample_id", "variant", "repeat", "input_hash", "commit", "phase"):
            if row[field] != source[field]:
                raise ValueError("SUMMARY_ROW_IDENTITY_CHANGED")
    result = calculate(rows)
    result.update(phase=manifest["phase"], mode=manifest["mode"], run_id=manifest["run_id"],
                  plan_hash=manifest["plan_hash"], baseline_unbound_prior_records=manifest["baseline"]["unbound_prior_source_records"])
    write_new(run_dir / (output_name + ".json"), result)
    target = inside(run_dir / (output_name + ".csv"))
    with target.open("x", encoding="utf-8", newline="") as handle:
        fields = [key for key in next(iter(result["by_variant"].values())) if key != "status_counts"]
        writer = csv.DictWriter(handle, fieldnames=["variant"] + fields)
        writer.writeheader()
        for variant, values in result["by_variant"].items():
            writer.writerow({"variant": variant, **{key: values[key] for key in fields}})
    return result
