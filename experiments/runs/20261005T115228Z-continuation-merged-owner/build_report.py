"""Append-only Owner packaging. Reads results/source hashes and ledger mode=ro."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import csv
import json
import math
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
EXECUTOR = ROOT / "experiments/runs/E1-continuation-executor-v1"
sys.path.insert(0, str(EXECUTOR))
import executor as e


def dump(name, value):
    with (OUT / name).open("xb") as handle:
        handle.write(e.encoded(value) + b"\n")


def csv_file(name, rows):
    with (OUT / name).open("x", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    original = e.ORIGIN
    continued = ROOT / "experiments/runs/20261005T114740304313Z-continuation-real-b584e838"
    origin_rows, continuation_rows = e.lines(original / "raw.jsonl"), e.lines(continued / "raw.jsonl")
    rows, summary = e.lines(OUT / "merged.jsonl"), e.load(OUT / "summary.json")
    recorded = e.load(continued / "run.json")
    plan = e.load(continued / "plan.json")
    # Actual assertions here are Owner packaging checks, not independent QA.
    assert len(rows) == 72 and len(continuation_rows) == 49
    assert [r["row_id"] for r in rows] == [r["row_id"] for r in origin_rows]
    assert Counter(r["status"] for r in rows) == {"completed": 69, "timeout": 1, "failed": 1, "not_called": 1}
    protected = []
    for old, merged in zip(origin_rows, rows):
        if old["status"] != "not_called":
            assert old == merged
            protected.append({"row_id": old["row_id"], "original_row_hash": e.sha(old), "merged_row_hash": e.sha(merged),
                              "response_utf8_sha256": e.sha(old["response"].encode("utf8")) if old["response"] is not None else None,
                              "object_equal": True})
    assert len(protected) == 23
    assert rows[22]["usage"] is None and rows[22]["charged_upper_cny"] == .16292
    assert rows[70]["call_id"] == "6dfc591c79c54544afe6d70eec6d697b" and rows[70]["usage"] is None
    assert rows[71]["actually_called"] is False and rows[71]["call_id"] is None
    pairs = []
    for repeat in (1, 2, 3):
        for sample in (f"C{n:02d}" for n in range(1, 13)):
            pair = [r for r in rows if r["sample_id"] == sample and r["repeat"] == repeat]
            pairs.append({"sample_id": sample, "repeat": repeat,
                          "complete_response_pair": len(pair) == 2 and all(r["status"] == "completed" for r in pair),
                          "paid_pair": len(pair) == 2 and all(r["actually_called"] is True for r in pair)})
    assert sum(p["complete_response_pair"] for p in pairs) == 34
    table = []
    for variant, group in summary["by_variant"].items():
        selected = [r for r in rows if r["variant"] == variant]
        known = [r for r in selected if r["usage_known"]]
        unknown = [r for r in selected if r["actually_called"] is True and not r["usage_known"]]
        table.append({"variant": variant, **{key: value for key, value in group.items() if key != "status_counts"},
                      "timeout": sum(r["status"] == "timeout" for r in selected),
                      "failed": sum(r["status"] == "failed" for r in selected),
                      "not_called": sum(r["status"] == "not_called" for r in selected),
                      "known_usage_settled_charge_cny": sum(r["charged_upper_cny"] for r in known),
                      "unknown_usage_retained_upper_cny": sum(r["charged_upper_cny"] for r in unknown),
                      "cost_basis": "retained ledger upper is not provider invoice; unknown usage is not zero"})
    csv_file("summary.csv", table)
    with (OUT / "raw.jsonl").open("xb") as handle:
        handle.write((OUT / "merged.jsonl").read_bytes())
    assert e.rawhash(OUT / "raw.jsonl") == e.rawhash(OUT / "merged.jsonl")
    latency, usage = [], []
    for batch, batch_rows in [(original.name, origin_rows), (continued.name, continuation_rows)]:
        for variant in ("full_history", "structured_summary"):
            selected = [r for r in batch_rows if r["variant"] == variant]
            for metric in ["latency_seconds"] + (["provider_latency_seconds"] if batch == continued.name else []):
                values = sorted(r[metric] for r in selected if r.get(metric) is not None)
                latency.append({"batch": batch, "variant": variant, "metric": metric, "known_attempt_rows": len(values),
                                "median_seconds": statistics.median(values) if values else None,
                                "p95_nearest_rank_seconds": values[math.ceil(.95*len(values))-1] if values else None,
                                "boundary": "new provider call only" if metric == "provider_latency_seconds" else "old in-process end-to-end" if batch == original.name else "new end-to-end including isolated judge; repeat-equivalent results may use offline judge cache",
                                "includes_failed_attempt_latency": True})
            known = [r for r in selected if r["usage_known"]]
            prompts = sum(r["usage"]["prompt_tokens"] for r in known)
            hits = sum(r["usage"]["prompt_cache_hit_tokens"] for r in known)
            usage.append({"batch": batch, "variant": variant, "planned_in_batch": len(selected), "usage_known_rows": len(known),
                          "prompt_tokens_known": prompts, "completion_tokens_known": sum(r["usage"]["completion_tokens"] for r in known),
                          "cache_hit_tokens_known": hits, "cache_hit_fraction_known_input": hits/prompts if prompts else None,
                          "known_charge_cny": sum(r["charged_upper_cny"] for r in known),
                          "unknown_usage_retained_upper_cny": sum(r["charged_upper_cny"] for r in selected if r["actually_called"] is True and not r["usage_known"]),
                          "scope": "batch only; no cache/time-controlled superiority claim"})
    csv_file("latency-by-phase.csv", latency)
    csv_file("usage-cache-by-phase.csv", usage)
    dump("phase-metrics.json", {"latency": latency, "usage_cache": usage,
                               "warning": "Mixed merged latency distributions are not equivalent measurement boundaries; phases/time/cache must be reported separately."})
    old_source = e.load(original / "plan.json")["freeze"]["source_hashes"]
    new_source = recorded["execution_sources"]["files"]
    source_map = {"original41": {rel: {"before_sha256": expected, "before_method": "recorded original plan.freeze.source_hashes, not reconstructed pre-run snapshot", "after_sha256": e.rawhash(ROOT/rel)} for rel, expected in old_source.items()},
                  "new5": {rel: {"before_sha256": expected, "before_method": "recorded continuation run.execution_sources", "after_sha256": e.rawhash(ROOT/rel)} for rel, expected in new_source.items()},
                  "logical_v1_archive_aliases": plan["dependencies"]["logical_v1_aliases"],
                  "canonical_paid_client": plan["dependencies"]["canonical_paid_client"],
                  "v1_worker_actual_imports_by_completed_row": [{"row_id": r["row_id"], "modules": r["v1_judge_dependencies"]} for r in continuation_rows if r["status"] == "completed"],
                  "archive_precheck_actual": e.archive_precheck(), "source_map_at_utc": e.now()}
    assert all(record["before_sha256"] == record["after_sha256"] for group in [source_map["original41"], source_map["new5"]] for record in group.values())
    dump("source-map.json", source_map)
    ledger = e.read_ledger()  # Original shared ledger mode=ro only.
    failed_call = next(c for c in ledger["calls"] if c["id"] == rows[70]["call_id"])
    old_call = next(c for c in ledger["calls"] if c["id"] == rows[22]["call_id"])
    dump("accounting-notes.json", {"at_utc": e.now(), "ledger_method": "original data/ai-budget.sqlite mode=ro; no mutation",
                                  "ledger_snapshot": e.safe_snapshot(ledger), "original_timeout_current_ledger_safe": old_call,
                                  "continuation_failure_current_ledger_safe": failed_call,
                                  "formal_known_usage_charge_cny": sum(r["charged_upper_cny"] for r in rows if r["usage_known"]),
                                  "formal_unknown_usage_retained_upper_cny": sum(r["charged_upper_cny"] for r in rows if r["actually_called"] is True and not r["usage_known"]),
                                  "formal_charged_upper_sum_cny": sum(r["charged_upper_cny"] or 0 for r in rows),
                                  "separate_prior_user_fee_fact": {"source": "Main dispatch/historical accounting closure", "original_timeout_user_confirmed_fee_cny": .05, "independent_invoice_retrieved_by_owner": False},
                                  "warning": "Ledger closure does not rewrite model response/token unknowns; maximum upper is not an invoice. All paid work remains held by Main."})
    failed_attempts = [{key: r.get(key) for key in ["row_id", "order", "status", "error", "start_time", "end_time", "call_id", "input_hash", "payload_utf8_bytes", "input_token_bound", "reservation_units", "charged_upper_cny", "actually_called", "response_received", "upstream_delivery_known", "http_status_code", "reported_model", "usage", "usage_known"]} for r in rows if r["status"] != "completed"]
    all_bindings = []
    for row in rows:
        original_input = original/"inputs"/(row["row_id"]+".json")
        continued_input = continued/"inputs"/(row["row_id"]+".json")
        all_bindings.append({"row_id": row["row_id"], "original_order": row["order"], "input_hash": row["input_hash"],
                             "original_input_path": str(original_input.relative_to(ROOT)).replace("\\", "/"), "original_input_raw_sha256": e.rawhash(original_input),
                             "continuation_input_path": str(continued_input.relative_to(ROOT)).replace("\\", "/") if continued_input.exists() else None,
                             "continuation_input_raw_sha256": e.rawhash(continued_input) if continued_input.exists() else None})
    dump("evidence-index.json", {"kind": "Owner append-only packaging, independent QA pending", "original_run": original.name,
                                "continuation_run": continued.name, "original_artifact_raw_sha256": {name: e.rawhash(original/name) for name in e.ORIGIN_HASHES},
                                "continuation_artifact_raw_sha256": {str(p.relative_to(continued)).replace("\\", "/"): e.rawhash(p) for p in sorted(continued.rglob("*")) if p.is_file() and p.suffix not in {".sqlite", ".db"}},
                                "original23_object_preservation": protected, "unit_input_bindings": all_bindings, "pair_coverage": pairs,
                                "noncompleted_original_units": failed_attempts,
                                "real_continuation_process": {"actual_command": [recorded["python"], "-B", "-X", "utf8"]+recorded["command"], "actual_exit_code": 0, "session_id": 61932, "completion_chunk": "d2b527", "evidence_source": "Main actual execution dispatch, not an Owner replay"},
                                "merge_process": {"actual_command": "C:\\Users\\liyh\\.conda\\envs\\1\\python.exe -B -X utf8 experiments/runs/E1-continuation-executor-v1/executor.py merge --run-dir experiments/runs/20261005T114740304313Z-continuation-real-b584e838 --output experiments/runs/20261005T115228Z-continuation-merged-owner", "actual_exit_code": 0, "completion_chunk": "936bb4"},
                                "paid_calls_added_by_owner_packaging": 0, "env_read": False, "ledger_mutated": False})
    note = """# E1 追加续跑结果说明（Owner整理，待独立QA）

72个冻结计划单元的首个实际尝试已追加合并，终态为 **69 completed、1 timeout、1 failed、1 not_called**。也就是71次确证付费尝试、69次确证响应、2次响应/用量未知、1条未调用；不是72次回复。原run72行、原summary和续run49行均未改。

| 方案 | planned | 付费确证 | 完成 | 正确/完成 | 正确/planned | usage覆盖 | 服务失败 | 未调用 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A完整历史 | 36 | 36 | 34 | 26/34 | 26/36 | 34/36 | 1原timeout+1续failed | 0 |
| B结构摘要 | 36 | 35 | 35 | 29/35 | 29/36 | 35/36 | 0 | 1 |

两方案已完成动作均合法且引用有效/充分（A34/34、B35/35）；动作正确性不等于自由文本全部无幻觉。69条完成中有14条合法但不在冻结正确下一步集合内，这些偏差未被替换。36个计划配对只有34个双响应完整；C12 repeat1的A原超时保留，C04 repeat3的A失败/B未调用。原23条付费尝试的完整行对象及22条响应UTF8内容逐条相等，详情在evidence-index.json。

原第23行formal-C12-full_history-1超时的HTTP/model/usage仍null，账本上界0.16292元保留；用户曾向Main确认费用0.05元是独立的人工费用事实，不能补出模型token或改写raw。续跑第71行formal-C04-full_history-3发生MODEL_UNAVAILABLE，call_id=6dfc591c79c54544afe6d70eec6d697b，HTTP/model/usage/投递仍未知，fullupper0.094536元；第72行B未调用。新失败不能推定上游没收到请求。所有付费操作暂停，由Main另行核清。

正式两个批次合计费用保守上界0.40885584元，其中已知usage结算0.15139984元、两条unknown usage预留上界0.257456元；不含独立pilot和此前游戏/探针费用。续跑单批上界0.17135888元，已知结算0.07682288元、未知预留0.094536元。原总项目账本交接事实为83条调用、总上界0.44896184元，Owner只读当前快照另存accounting-notes.json；账本状态核清与实验未知状态分别记录，不回收/猜测费用。

summary.csv为T24附件，沿原summary分母补列timeout/failed/not_called及known settled/unknown retained upper费用。raw.jsonl等于merged.jsonl完整72行；lineage.json逐单元说明原not_called→首次实际尝试或仍未调用。原23条结果保持原样，没有选择最好结果、补打旧失败或把pilot并入正式。

延迟和缓存按批次分列于latency-by-phase.csv、usage-cache-by-phase.csv。原批记录的是旧进程内判定结束前后的latency_seconds，续批端到端包含独立v1判定子进程，另有provider_latency_seconds；不能把混合延迟当同一测量边界。续跑相隔约六小时，vendor时间/负载、缓存命中和顺序连续性改变；仅请求值、字节指纹、原相对顺序及v1判定保持一致。原温度/seed未发送。原v1的6条未绑定旧QA源记录/3项runtime-only构建局限仍适用。不能声称B优越、成本优势、总体智能、自主通关、人测或课程签署。

source-map.json分别注明original41 before来自原plan.freeze源图、new5 before来自真实续run记录，after为本次实际raw哈希读取；不是事后制造前快照。归档v1 aliases和canonical付费client明确分开，currentv2规则没有进入续跑判定。稳定executor和原始数据均未修改。当前报告仅Owner整理；Main交接和独立QA复核尚待进行。
"""
    with (OUT/"result-note.md").open("x", encoding="utf8", newline="\n") as handle:
        handle.write(note)
    dump("packaging-checks.json", {"kind": "Owner structural preservation check, not formal QA", "planned": 72,
                                    "statuses": dict(Counter(r["status"] for r in rows)), "original23_rows_object_equal": True,
                                    "original22_response_utf8_preserved": True, "source_before_after_match": True,
                                    "complete_response_pairs": 34, "paid_attempt_pairs": sum(p["paid_pair"] for p in pairs),
                                    "raw_copy_equal": True, "actual_command": sys.argv, "python": sys.executable,
                                    "paid_calls_added": 0, "env_read": False, "ledger_mutated": False})
    print(json.dumps({"directory": str(OUT), "statuses": dict(Counter(r["status"] for r in rows)),
                      "by_variant": {variant: {key: group[key] for key in ["planned", "paid_attempts_confirmed", "completed", "correct", "usage_known_rows", "responses_unknown"]} for variant, group in summary["by_variant"].items()},
                      "ledger_actual_ro": {key: value for key, value in e.safe_snapshot(ledger).items() if key != "experiment_calls"},
                      "original23_preserved": True, "original41_new5_hashes_match": True,
                      "summary_csv_sha256": e.rawhash(OUT/"summary.csv"), "raw_sha256": e.rawhash(OUT/"raw.jsonl"),
                      "result_note_sha256": e.rawhash(OUT/"result-note.md")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
