"""Run one explicitly named V5 QA suite into a fresh, isolated evidence directory."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import uuid

from scripts.dev import ROOT

SUITES = {
    "auth": ["tests/v5/test_auth.py"],
    "kernel": ["tests/v5/test_kernel.py"],
    "generation": ["tests/v5/test_generation.py"],
    "integration": ["tests/v5/test_integration.py"],
    "security": ["tests/v5/test_security.py"],
    "legacy": ["tests/v5/test_legacy.py"],
}
SECRET_TEXT = re.compile(
    r"(?i)(authorization\s*[:=]\s*(?:bearer\s+)?|(?:x-api-key|api[_-]?key|token|secret|password)\s*[:=]\s*)[^\s,;]+"
)


def source_hashes() -> dict[str, str]:
    result: dict[str, str] = {}
    excluded = {"node_modules", "dist", "dist-v5", "__pycache__", ".pytest_cache", "data", "owner-evidence"}
    for dirname in ("backend", "frontend", "scripts", "tests", "contracts"):
        base = ROOT / dirname
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and not excluded.intersection(path.relative_to(base).parts):
                result[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    # Only new executable/contract inputs, never historical experiment/evaluation runs.
    for base in (ROOT / "experiments/v5", ROOT / "evaluation/v5"):
        if base.exists():
            for path in sorted(base.rglob("*")):
                if path.is_file() and not excluded.intersection(path.relative_to(base).parts):
                    result[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ("evaluation/v5.py", "evaluation/cli.py", "evaluation/engine.py", "evaluation/reader.py", "evaluation/common.py", "evaluation/provider.py", "evaluation/trust.py"):
        path = ROOT / name
        if path.is_file(): result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def safe_text(value: str) -> str:
    return SECRET_TEXT.sub(lambda match: match.group(0).split(":", 1)[0].split("=", 1)[0] + "=[REDACTED]", value)


def prohibited_staged_paths() -> list[str]:
    proc = subprocess.run(["git", "diff", "--cached", "--name-only", "--"], cwd=ROOT,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if proc.returncode:
        raise RuntimeError("could not inspect staged paths for evidence audit")
    blocked_parts = {"data", "node_modules", ".venv", "venv", "env", "envs", ".conda", "raw-sensitive", "logs"}
    blocked_suffixes = {".sqlite", ".sqlite3", ".db", ".pem", ".key", ".log"}
    findings = []
    for item in proc.stdout.splitlines():
        path = Path(item)
        lowered = [part.casefold() for part in path.parts]
        if blocked_parts.intersection(lowered) or path.suffix.casefold() in blocked_suffixes:
            findings.append(item)
        elif path.name.casefold() in {".env", ".env.local"} or path.name.casefold().startswith("credentials"):
            findings.append(item)
    return findings


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=["contracts", "auth", "kernel", "generation", "integration", "security", "legacy", "browser", "evidence"], required=True)
    parser.add_argument("--output", type=Path, required=True, help="parent directory for a new run-id folder")
    parser.add_argument("--scope", action="append", default=[], help="optional pytest -k scope; repeat to combine with OR")
    parser.add_argument("--candidate", type=Path, help="candidate/source reference JSON to bind into evidence")
    args = parser.parse_args()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid.uuid4().hex[:8]
    directory = args.output.resolve() / run_id
    directory.mkdir(parents=True, exist_ok=False)
    before = source_hashes()
    summary: dict[str, object] = {
        "run_id": run_id, "suite": args.suite, "started_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version, "python_executable": sys.executable, "platform": platform.platform(),
        "provider": "mock", "source_hashes_before": before, "steps": [],
        "candidate_reference": str(args.candidate.resolve()) if args.candidate else None,
        "limitations": ["This scoped runner is not a complete privacy/security audit.", "No paid model calls are made."],
    }
    environment = os.environ.copy()
    environment.update({"AI_PROVIDER": "mock", "PYTHONUTF8": "1",
                        "SQLITE_PATH": str(directory / "isolated-data" / "game-v5.sqlite")})
    result = 0
    try:
        if args.suite == "evidence":
            if not args.candidate or not args.candidate.is_file():
                result = 2
                summary["status"] = "NOT_READY"
                summary["error"] = "evidence suite requires an existing --candidate JSON reference"
            else:
                candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
                staged = prohibited_staged_paths()
                referenced = candidate.get("source_sha256") if isinstance(candidate, dict) else None
                if not isinstance(referenced, dict):
                    referenced = candidate.get("source_hashes") if isinstance(candidate, dict) else None
                if not isinstance(referenced, dict) or not referenced:
                    raise ValueError("candidate JSON must contain a nonempty source_sha256 or source_hashes map")
                current = source_hashes()
                invalid_refs = []
                mismatches = []
                for name, digest in referenced.items():
                    if not isinstance(name, str) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
                        invalid_refs.append(str(name))
                    elif name not in current:
                        invalid_refs.append(name)
                    elif current[name].lower() != digest.lower():
                        mismatches.append(name)
                summary["candidate_reference_sha256"] = hashlib.sha256(args.candidate.read_bytes()).hexdigest()
                summary["candidate_source_count"] = len(referenced)
                summary["candidate_source_invalid_references"] = invalid_refs
                summary["candidate_source_mismatches"] = mismatches
                summary["prohibited_staged_paths"] = staged
                result = 1 if staged or invalid_refs or mismatches else 0
                summary["status"] = "PASS" if result == 0 else "FAIL"
        else:
            if args.suite == "contracts":
                old_checker = ROOT / "contracts/check_contracts.py"
                v2_checker = ROOT / "contracts/v2/check_contracts.py"
                if not v2_checker.is_file():
                    legacy_result = 0
                    if old_checker.is_file():
                        legacy_result = _run([sys.executable, str(old_checker), "--output",
                                              str(directory / "legacy-contracts-report.json")], directory, environment, summary)
                    if legacy_result:
                        result = legacy_result
                        summary["status"] = "FAIL"
                        summary["error"] = "legacy contract checker failed; V5 contract checker is also absent"
                    else:
                        result = 2
                        summary["status"] = "NOT_READY"
                        summary["error"] = "V5 contracts/v2/check_contracts.py is absent; only the legacy checker, if present, was run"
                else:
                    result = 0
                    if old_checker.is_file():
                        result = _run([sys.executable, str(old_checker), "--output",
                                       str(directory / "legacy-contracts-report.json")], directory, environment, summary)
                    if result == 0:
                        result = _run([sys.executable, str(v2_checker), "--output",
                                       str(directory / "contracts-report.json")], directory, environment, summary)
            elif args.suite == "browser":
                browser_script = ROOT / "tests/v5/run_browser.mjs"
                if not browser_script.is_file():
                    result = 2
                    summary["status"] = "NOT_READY"
                    summary["error"] = "tests/v5/run_browser.mjs is absent; no browser suite was run"
                else:
                    command = [shutil_which_node(), str(browser_script), "--output", str(directory)]
                    result = _run(command, directory, environment, summary)
            else:
                files = [ROOT / path for path in SUITES[args.suite] if (ROOT / path).is_file()]
                if not files:
                    result = 2
                    summary["status"] = "NOT_READY"
                    summary["error"] = f"No QA-owned test file is present for suite {args.suite}; no tests were run"
                else:
                    command = [sys.executable, "-m", "pytest", *[str(p) for p in files], "-q", "-p", "no:cacheprovider"]
                    if args.scope:
                        command.extend(["-k", " or ".join(f"({scope})" for scope in args.scope)])
                    result = _run(command, directory, environment, summary)
            summary.setdefault("status", "PASS" if result == 0 else ("NOT_READY" if result == 2 else "FAIL"))
    except KeyboardInterrupt:
        result = 130
        summary["status"] = "INTERRUPTED"
        summary["error"] = "interrupted by operator"
    except Exception as error:
        result = 1
        summary["status"] = "FAIL"
        summary["error"] = f"{type(error).__name__}: {error}"
    finally:
        after = source_hashes()
        summary["source_hashes_after"] = after
        summary["source_unchanged"] = before == after
        if before != after and result == 0:
            result = 1
            summary["status"] = "FAIL"
            summary["error"] = "source changed during the run"
        summary["completed_at"] = datetime.now(timezone.utc).isoformat()
        summary["exit_code"] = result
        (directory / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"V5 suite status: {summary.get('status')}\nEvidence: {directory}\nExit code: {result}", flush=True)
    return result


def _run(command: list[str], directory: Path, environment: dict[str, str], summary: dict[str, object]) -> int:
    is_build = "vite" in " ".join(command).lower() or "npm" in " ".join(command).lower()
    timeout = 120 if is_build else 300
    log = directory / f"step-{len(summary['steps']) + 1}.txt"
    started = datetime.now(timezone.utc).isoformat()
    try:
        proc = subprocess.run(command, cwd=ROOT, env=environment, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout, check=False)
        output = safe_text(proc.stdout.decode("utf-8", errors="replace"))
        code = proc.returncode
    except subprocess.TimeoutExpired as error:
        output = safe_text((error.stdout or b"").decode("utf-8", errors="replace")) + "\n[timeout]\n"
        code = 124
    log.write_text(output, encoding="utf-8")
    summary["steps"].append({"command": command, "exit_code": code, "started_at": started,
                             "completed_at": datetime.now(timezone.utc).isoformat(), "log": log.name,
                             "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest()})
    print(f"Ran {Path(command[0]).name} step; exit code {code}; log {log.name}", flush=True)
    return code


def shutil_which_node() -> str:
    import shutil
    node = shutil.which("node") or shutil.which("node.exe")
    if not node:
        raise RuntimeError("Node.js is unavailable; V5 browser suite was not run")
    return node


if __name__ == "__main__":
    raise SystemExit(main())
