"""Append final Owner process evidence and current artifact index; no model calls."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PYTHON = r"C:\Users\liyh\.conda\envs\1\python.exe"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def append(name, data):
    with (OUT / name).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")

evidence = json.loads((OUT / "evidence-index.json").read_text(encoding="utf-8"))
append("process-result.json", {
    "kind": "Owner append-only evidence packaging; real execution sourced from Main",
    "working_directory": str(ROOT),
    "real_continuation": evidence["real_continuation_process"],
    "owner_merge": evidence["merge_process"],
    "owner_packaging": {
        "actual_command": [PYTHON, "-B", "-X", "utf8", "experiments/runs/20261005T115228Z-continuation-merged-owner/build_report.py"],
        "actual_exit_code": 0, "completion_chunk": "4fceaa",
    },
    "owner_readonly_metadata": {"actual_exit_code": 0, "completion_chunk": "5f4643"},
    "paid_calls_added_by_owner": 0, "env_read": False, "ledger_mutated": False,
    "original_runs_and_five_executor_sources_mutated": False,
    "status": "Owner stable STOP; new result QA pending; all paid work held",
})
append("user-fee-update.json", {
    "source": "Main latest task handoff, a user fee statement; not an Owner supplier lookup",
    "call_id": "6dfc591c79c54544afe6d70eec6d697b",
    "user_confirmed_fee_cny": 0.09,
    "main_reported_accounting_application_state": "independent helper QA pending; not yet applied at handoff",
    "original_experiment_usage": None,
    "preserved_experiment_upper_cny": 0.094536,
    "no_raw_rewrite_no_ledger_write_no_new_paid_call": True,
    "accounting_notes_snapshot_remains_its_original_timestamp": True,
})
paths = sorted(p for p in OUT.rglob("*") if p.is_file())
paths.append(ROOT / "review/experiment.md")
artifacts = [{"path": p.relative_to(ROOT).as_posix(), "raw_sha256": sha(p), "bytes": p.stat().st_size} for p in paths]
append("artifact-sha256.json", {
    "kind": "new merged-results Owner handoff index; no self-reference",
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "artifacts": artifacts,
    "historical_indices": "Original run Owner indices, including v2, remain unchanged historical snapshots. Main authorized updating review/experiment.md for the new actual continuation results. Its current bytes are bound here; this does not retroactively amend any old index or old QA snapshot.",
    "coverage": "New report artifacts plus handed-off current review/experiment.md. All original/continuation input and result artifact hashes are bound in evidence-index.json; original41/new5 and archived/canonical aliases in source-map.json.",
    "qa_status": "Owner structural checks passed; independent new real/merged result QA pending",
})
for name in ["summary.csv", "raw.jsonl", "source-map.json", "evidence-index.json", "process-result.json", "artifact-sha256.json"]:
    print(name, sha(OUT / name))
print("review/experiment.md", sha(ROOT / "review/experiment.md"))
print("indexed", len(artifacts), "STOP; paid=0 env_read=0 ledger_write=0")
