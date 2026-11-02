"""Run four current-evidence nodes once and archive only observed outputs.

This entry point is deliberately inert without the explicit --execute flag.
Synthetic inputs run through the current product compiler/API/storage fixtures;
they are not evidence of real-AI content quality.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[2]
FIXED_AUTOMATED = ROOT / "evidence/project/stages/v5-current-evaluation/automated"
LEGACY_QA_ROOT = ROOT / "evidence/upgrade/v5.0/qa"
INPUTS = ROOT / "evidence/upgrade/v5.0/experiments-owner/run1/inputs.json"
EXPECTED_INPUTS_SHA256 = "7609c5b66fcaaf662c04a5783d3ffac6e3d00c89cda0ed7ba1a804e1fe111cef"
SYNTHETIC_CANARY = "QA-SYNTHETIC-CREDENTIAL-ONLY-9c584e"

TESTS = [
    "tests/v5/test_planner_fixed.py::test_affected_nine_and_twenty_original_inputs",
    "tests/v5/test_security.py::test_all_private_ids_read_write_denied_without_owner_change",
    "tests/v5/test_integration.py::test_three_archives_restore_delete_reset_relogin_reopen",
    "tests/v5/test_integration.py::test_bad_definition_or_archive_does_not_overwrite[checksum]",
]

PRODUCT_SOURCES = [
    "backend/requirements.in",
    "backend/requirements.lock.txt",
]
TEST_SOURCES = [
    "backend/__init__.py",
    "backend/app/__init__.py",
    "tests/v5/test_planner_fixed.py",
    "tests/v5/test_security.py",
    "tests/v5/test_integration.py",
    "tests/__init__.py",
    "tests/v5/__init__.py",
    "tests/v5/conftest.py",
    "tests/v5/run_current_evidence.py",
    "evidence/upgrade/v5.0/experiments-owner/run1/inputs.json",
    "frontend/src/assets/generated-catalog.json",
    "frontend/src/assets/manifest.ts",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def current_sources() -> list[Path]:
    paths = [ROOT / value for value in PRODUCT_SOURCES + TEST_SOURCES]
    paths.extend((ROOT / "backend/app").rglob("*.py"))
    paths.extend(path for path in (ROOT / "contracts/v2").rglob("*") if path.is_file() and path.suffix.lower() in {".json", ".py"})
    # Include all registered visual manifests as metadata dependencies, not the
    # full binary art tree (these four selected nodes do not render images).
    paths.extend(sorted((ROOT / "frontend/src/assets/themes").glob("*/manifest.json")))
    return sorted({path.resolve() for path in paths}, key=lambda path: path.as_posix().lower())


def source_map() -> list[dict]:
    result = []
    for path in current_sources():
        if not path.is_file():
            raise FileNotFoundError(f"required source missing: {relative(path)}")
        raw = path.read_bytes()
        result.append({"path": relative(path), "bytes": len(raw), "sha256": digest_bytes(raw)})
    return result


def safe_pytest_output(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    text = text.replace(SYNTHETIC_CANARY, "[SYNTHETIC-CANARY]")
    text = re.sub(r"(?im)((?:set-cookie|cookie|authorization|x-csrf-token|x-auth-context|x-ai-api-key)\s*:\s*)[^\r\n]+", r"\1[REDACTED]", text)
    text = re.sub(
        r'(?i)(["\']?(?:csrf_token|x-csrf-token|auth_context|x-auth-context|campus_v5_session|campus_v5_csrf|session[_-]?(?:token|id)|authorization|cookie|token|password|password_hash|api[_-]?key|x-ai-api-key)["\']?\s*[:=]\s*["\'])[^"\']*(["\'])',
        r"\1[REDACTED]\2",
        text,
    )
    return text


def copy_observed_outputs(legacy_output: Path, destination: Path) -> list[dict]:
    destination.mkdir(parents=True, exist_ok=False)
    copied = []
    for source in sorted(legacy_output.glob("*.json")):
        target = destination / source.name
        raw = source.read_bytes()
        target.write_bytes(raw)
        copied.append({
            "source": relative(source),
            "copy": relative(target),
            "bytes": len(raw),
            "sha256": digest_bytes(raw),
            "copied_byte_for_byte": source.read_bytes() == target.read_bytes(),
            "source_note": "written by the selected test's observed_output helper during this actual invocation; copied without modification",
        })
    return copied


def derive_observations(raw_dir: Path) -> dict:
    """Produce compact proof fields from actual helper JSON; never synthesize rows."""
    derived: dict = {"format": "observed-current-evidence-v1", "from_actual_raw_files": True}
    c1_path = raw_dir / "C1-admission-affected.json"
    if c1_path.is_file():
        c1 = json.loads(c1_path.read_text(encoding="utf-8"))
        admissions = c1.get("admissions", [])
        rejections = c1.get("rejections", [])
        derived["C1"] = {
            "frozen_input_file_sha256": c1.get("frozen_input_file_sha256"),
            "scope": c1.get("scope"),
            "admitted_count": len(admissions),
            "rejected_count": len(rejections),
            "all_admitted_have_witness_exit": bool(admissions) and all(row.get("admitted") is True and row.get("replay_won") is True and row.get("steps", 0) > 0 for row in admissions),
            "all_negative_cases_rejected": bool(rejections) and all(row.get("rejected") is True for row in rejections),
            "admissions": [
                {key: row.get(key) for key in ("case_id", "room_count", "difficulty", "steps", "replay_won", "definition_hash")}
                for row in admissions
            ],
            "rejections": [
                {key: row.get(key) for key in ("case_id", "category", "error_code", "rejected")}
                for row in rejections
            ],
        }
    else:
        derived["C1"] = {"observed_file": None, "complete": False}

    c2_path = raw_dir / "C2-observations.json"
    if c2_path.is_file():
        c2 = json.loads(c2_path.read_text(encoding="utf-8"))
        requests = c2.get("requests", [])
        derived["C2"] = {
            "request_count": len(requests),
            "all_http_404": bool(requests) and all(row.get("http_status") == 404 for row in requests),
            "all_target_state_hashes_unchanged": bool(requests) and all(row.get("target_before_sha256") == row.get("target_after_sha256") for row in requests),
            "request_kinds": {name: sum(row.get("operation") == name for row in requests) for name in sorted({row.get("operation") for row in requests})},
            "private_identifiers_copied_only_to_raw_artifact": True,
        }
    else:
        derived["C2"] = {"observed_file": None, "complete": False}

    c3_moments_path = raw_dir / "C3-moments.json"
    c3_checksum_path = raw_dir / "C3-bad-checksum.json"
    moments = json.loads(c3_moments_path.read_text(encoding="utf-8")) if c3_moments_path.is_file() else None
    checksum = json.loads(c3_checksum_path.read_text(encoding="utf-8")) if c3_checksum_path.is_file() else None
    restores = moments.get("restores", []) if moments else []
    derived["C3"] = {
        "three_moment_restores_observed": len(restores),
        "all_moment_hashes_match": len(restores) == 3 and all(row.get("http_status") == 200 and row.get("saved_state_sha256") == row.get("restored_state_sha256") for row in restores),
        "moment_definition_hashes_match": bool(restores) and all(row.get("restored_definition_sha256") == moments.get("original_definition_sha256") for row in restores),
        "checksum_bad_restore_observed": bool(checksum),
        "checksum_rejected_with_409": bool(checksum and checksum.get("rejected") is True and checksum.get("http_status") == 409),
        "checksum_failure_preserved_current_state": bool(checksum and checksum.get("current_before_sha256") == checksum.get("current_after_sha256")),
    }
    derived["complete_observed_artifacts"] = bool(c1_path.is_file() and c2_path.is_file() and c3_moments_path.is_file() and c3_checksum_path.is_file())
    c1_result, c2_result, c3_result = derived["C1"], derived["C2"], derived["C3"]
    derived["required_observations_match_actual_counts"] = bool(
        c1_result.get("admitted_count") == 9
        and c1_result.get("rejected_count") == 20
        and c1_result.get("all_admitted_have_witness_exit") is True
        and c1_result.get("all_negative_cases_rejected") is True
        and c2_result.get("request_count") == 11
        and c2_result.get("all_http_404") is True
        and c2_result.get("all_target_state_hashes_unchanged") is True
        and c3_result.get("three_moment_restores_observed") == 3
        and c3_result.get("all_moment_hashes_match") is True
        and c3_result.get("moment_definition_hashes_match") is True
        and c3_result.get("checksum_rejected_with_409") is True
        and c3_result.get("checksum_failure_preserved_current_state") is True
    )
    return derived


def execute() -> int:
    FIXED_AUTOMATED.mkdir(parents=True, exist_ok=True)
    run_id = f"current-evidence-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    output = FIXED_AUTOMATED / run_id
    output.mkdir(exist_ok=False)
    raw_copy = output / "observed"
    temp_root = Path(tempfile.mkdtemp(prefix="campus-current-evaluation-"))
    pytest_base = temp_root / "pytest-basetemp"
    legacy_output = LEGACY_QA_ROOT / "current-evaluation" / run_id
    legacy_output.mkdir(parents=True, exist_ok=False)
    (temp_root / "import").mkdir()
    isolated_import_db = temp_root / "import" / "game-v5.sqlite"

    started = utc_now()
    before = source_map()
    command = [
        sys.executable, "-B", "-X", "utf8", "-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider",
        "--basetemp", str(pytest_base), *TESTS,
    ]
    env = os.environ.copy()
    env.update({
        "PYTHONUTF8": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "GAMEPLAY_VERSION": "v5",
        "AI_PROVIDER": "mock",
        "SQLITE_PATH": str(isolated_import_db),
        "V5_QA_OUTPUT": str(legacy_output),
        "TERM": "dumb",
        "NO_COLOR": "1",
    })
    proc = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    finished = utc_now()
    after = source_map()
    copied = copy_observed_outputs(legacy_output, raw_copy)
    derived = derive_observations(raw_copy)
    derived_path = output / "derived-observations.json"
    derived_path.write_text(json.dumps(derived, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    raw_stdout_hash = digest_bytes(proc.stdout)
    local_raw_log = temp_root / "raw-pytest-sensitive.log"
    local_raw_log.write_bytes(proc.stdout)
    sanitized = safe_pytest_output(proc.stdout)
    log_path = output / "pytest-output-redacted.log"
    log_path.write_text(sanitized, encoding="utf-8")
    sources_equal = before == after
    outputs_byte_exact = all(row["copied_byte_for_byte"] for row in copied)
    complete = derived.get("complete_observed_artifacts") is True
    exit_code = proc.returncode if sources_equal and outputs_byte_exact else (proc.returncode or 1)
    observations_match = derived.get("required_observations_match_actual_counts") is True
    if proc.returncode == 0 and (not sources_equal or not outputs_byte_exact or not complete or not observations_match):
        exit_code = 1

    result = {
        "kind": "current V5 deterministic evidence refresh",
        "run_id": run_id,
        "started_at_utc": started,
        "finished_at_utc": finished,
        "operator_role": "Independent AI QA agent /root/passage_qa_exec_luna",
        "host_account": getpass.getuser(),
        "command": command,
        "pytest_exit_code": proc.returncode,
        "runner_exit_code": exit_code,
        "selected_nodes": TESTS,
        "synthetic_input": True,
        "current_product_code_executed": True,
        "real_ai_quality_tested": False,
        "real_model_calls": 0,
        "paid_calls": 0,
        "player_database_access": False,
        "database_isolation": {
            "SQLITE_PATH_seeded_from_owned_temp": isolated_import_db.is_relative_to(temp_root),
            "pytest_tmp_base_is_owned_temp": pytest_base.is_relative_to(temp_root),
            "existing_conftest_uses_its_own_temporary_import_home": True,
            "temp_root_name": temp_root.name,
        },
        "observed_output_helper_source_root": relative(LEGACY_QA_ROOT),
        "observed_output_helper_run_directory": relative(legacy_output),
        "fixed_stage_raw_copy_directory": relative(raw_copy),
        "raw_observed_files": copied,
        "derived_observations_file": relative(derived_path),
        "derived_observations": derived,
        "pytest_output_redacted_log": relative(log_path),
        "raw_pytest_stdout_sha256": raw_stdout_hash,
        "raw_pytest_sensitive_log_local_path": str(local_raw_log),
        "raw_pytest_sensitive_log_in_public_stage_or_git": False,
        "public_result_contains_credentials_or_session_tokens": False,
        "local_raw_log_may_contain_synthetic_credentials_or_tokens": True,
        "source_map": {"before": before, "after": after, "identical": sources_equal},
        "all_observed_output_copies_byte_exact": outputs_byte_exact,
        "required_observations_match_actual_counts": observations_match,
        "scope_note": "Actual current product compiler/rules/API/storage ran with offline Synthetic fixture inputs. This does not establish real-AI quality or full-suite status.",
    }
    (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "run_id": run_id,
        "output": relative(output),
        "pytest_exit_code": proc.returncode,
        "runner_exit_code": exit_code,
        "source_map_identical": sources_equal,
        "observed_files": len(copied),
        "observed_artifacts_complete": complete,
        "real_model_calls": 0,
        "paid_calls": 0,
    }, ensure_ascii=False))
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="run the four assigned pytest nodes once")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"status": "NOT_RUN", "reason": "Explicit --execute required; preparation mode performs no tests or writes."}, ensure_ascii=False))
        return 0
    return execute()


if __name__ == "__main__":
    raise SystemExit(main())
