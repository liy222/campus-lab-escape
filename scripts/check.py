"""Build the frontend and run the actual deterministic test suite."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import uuid

from scripts.dev import ROOT, npm_command


def source_hashes() -> dict[str, str]:
    result = {}
    excluded = {"node_modules", "dist", "__pycache__", ".pytest_cache", "data"}
    for directory in ("backend", "frontend", "scripts", "tests", "contracts"):
        base = ROOT / directory
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or excluded.intersection(path.relative_to(base).parts):
                continue
            if path.suffix.lower() not in {".py", ".ts", ".tsx", ".css", ".html", ".json", ".txt", ".in"}:
                continue
            result[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main() -> int:
    # Windows may default to GBK; build tools emit UTF-8 symbols.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=["deterministic"], default="deterministic")
    parser.add_argument("--output", type=Path, default=Path("evidence/runs/check"))
    parser.add_argument("--release-id", default="unreleased-working-tree")
    args = parser.parse_args()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid.uuid4().hex[:8]
    directory = args.output.resolve() / run_id
    directory.mkdir(parents=True, exist_ok=False)
    hashes_before = source_hashes()
    summary = {"run_id": run_id, "release_id": args.release_id, "suite": args.suite,
               "python": sys.version, "python_executable": sys.executable,
               "platform": platform.platform(), "provider": "mock", "steps": [],
               "source_hashes": hashes_before}
    environment = os.environ.copy()
    environment["AI_PROVIDER"] = "mock"
    environment["PYTHONUTF8"] = "1"
    result = 0
    try:
        commands = [("frontend-build", npm_command("--prefix", "frontend", "run", "build")),
                    ("deterministic-tests", [sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"])]
        for name, command in commands:
            log = directory / f"{name}.txt"
            started = datetime.now(timezone.utc).isoformat()
            print(f"Running {name}…", flush=True)
            with log.open("w", encoding="utf-8") as output:
                process = subprocess.run(command, cwd=ROOT, env=environment, stdout=output,
                                         stderr=subprocess.STDOUT, check=False)
            summary["steps"].append({"name": name, "command": command, "exit_code": process.returncode,
                                     "started_at": started, "completed_at": datetime.now(timezone.utc).isoformat(),
                                     "log": log.name, "sha256": hashlib.sha256(log.read_bytes()).hexdigest()})
            print(log.read_text(encoding="utf-8", errors="replace"), end="")
            if process.returncode and result == 0:
                result = process.returncode
    except Exception as error:
        summary["error"] = str(error)
        print(f"Check failed: {error}", file=sys.stderr)
        result = 1
    except KeyboardInterrupt:
        summary["error"] = "interrupted"
        result = 130
    finally:
        summary["source_unchanged"] = hashes_before == source_hashes()
        if not summary["source_unchanged"] and result == 0:
            result = 1
            summary["error"] = "source changed while checking; rerun on a stable candidate"
        summary["exit_code"] = result
        summary["status"] = "PASS" if result == 0 else "FAIL"
        (directory / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Evidence: {directory}\nExit code: {result}", flush=True)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
