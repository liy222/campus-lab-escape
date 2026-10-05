"""Reproduce a committed, Main-pinned source ZIP in a new local directory.

The existing Conda interpreter is checked, never installed into or reset. The
only installation is npm ci inside the new directory. No credentials, player
databases, original budget ledger, Git operations or paid modes are used.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import zipfile


SECRET_PREFIXES = ("MODEL_", "EVALUATION_", "EVAL_", "OPENAI_", "ANTHROPIC_", "DEEPSEEK_", "AI_")
SECRET_FRAGMENTS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
FORBIDDEN_PARTS = {".git", ".conda", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}
FORBIDDEN_SUFFIXES = {".sqlite", ".sqlite3", ".db", ".pyc", ".pyo"}
LEGACY_SHA = "21d992feb895ce5535c6b0b3d731887be9619171351a551935e1d10fc2bfae22"
LEGACY_COMMIT = "165a961c9d6694ceb44c88ef86c1ea28de2eae71"
ROUTE = [
    ("inspect", {"object_id": "r1_note"}), ("inspect", {"object_id": "r1_cabinet"}),
    ("submit_code", {"target_id": "r1_cabinet", "code": "382"}), ("take", {"item_id": "access_card"}),
    ("use_item", {"item_id": "access_card", "target_id": "r1_door"}), ("move", {"destination_id": "R2"}),
    ("take", {"item_id": "fuse"}), ("use_item", {"item_id": "fuse", "target_id": "r2_powerbox"}),
    ("inspect", {"object_id": "r2_monitor"}), ("inspect", {"object_id": "r2_drawer"}),
    ("submit_code", {"target_id": "r2_drawer", "code": "724"}), ("take", {"item_id": "emergency_key"}),
    ("use_item", {"item_id": "emergency_key", "target_id": "r2_door"}), ("move", {"destination_id": "R3"}),
    ("inspect", {"object_id": "r3_checklist"}), ("inspect", {"object_id": "r3_panel"}),
    ("submit_code", {"target_id": "r3_panel", "code": "231"}), ("move", {"destination_id": "EXIT"}),
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean_environment(root: Path, database: Path) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith(SECRET_PREFIXES)
           and not any(fragment in key.upper() for fragment in SECRET_FRAGMENTS)
           and key.upper() not in {"PYTHONPATH", "PYTHONHOME", "SQLITE_PATH", "CAMPUS_BACKEND_URL"}}
    env.update(AI_PROVIDER="mock", SQLITE_PATH=str(database), PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    # Child imports resolve only from its explicit cwd, not from the original tree.
    return env


def safe_relative(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if "\\" in name or path.is_absolute() or any(p in {"", ".", ".."} for p in path.parts) or ":" in name:
        raise ValueError("unsafe archive path")
    if any(p.lower() in FORBIDDEN_PARTS for p in path.parts):
        raise ValueError("forbidden generated/environment archive member")
    if path.name.lower() == ".env" or path.name.lower().startswith(".env.") and path.name.lower() != ".env.example":
        raise ValueError("configuration secrets are forbidden in source archive")
    if path.suffix.lower() in FORBIDDEN_SUFFIXES or path.name.lower().endswith(("-wal", "-shm")):
        raise ValueError("runtime database/cache is forbidden in source archive")
    return path


def materialize(archive: Path, digest: str, root: Path, pins: dict) -> dict:
    if sha(archive.read_bytes()) != digest or pins["archive_sha256"] != digest:
        raise ValueError("source archive hash mismatch")
    records = pins["files"]
    if not isinstance(records, dict) or not records:
        raise ValueError("Main source-member pins required")
    members = {}
    with zipfile.ZipFile(archive) as source:
        for item in source.infolist():
            if item.is_dir():
                continue
            name = safe_relative(item.filename).as_posix()
            if name in members or stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError("duplicate or symlink archive member")
            members[name] = source.read(item)
    if set(members) != set(records):
        raise ValueError("source archive members differ from Main pins")
    audit = {}
    for name, raw in members.items():
        record = records[name]
        if sha(raw) != record["git_blob_sha256"]:
            raise ValueError("Git blob SHA256 mismatch: " + name)
        mode = record.get("materialization", "raw_equal")
        if mode == "raw_equal":
            output = raw
        elif mode == "main_pinned_lf_to_crlf":
            # A Main-supplied path-by-path record chooses this mode; target data
            # cannot select normalization. Original runtime bytes must match.
            if b"\r" in raw or b"\n" not in raw:
                raise ValueError("not a canonical LF source: " + name)
            output = raw.replace(b"\n", b"\r\n")
        elif mode == "main_pinned_line_endings":
            # Main records original CRLF positions after proving canonical
            # Git/runtime equality. Keep UTF-8 BOM, lone CRs and EOF bytes.
            canonical = raw.decode("utf-8", errors="strict").replace("\r\n", "\n").encode("utf-8")
            indices = record.get("crlf_newline_indices")
            count = canonical.count(b"\n")
            if (not isinstance(indices, list)
                    or any(type(index) is not int or index < 0 or index >= count for index in indices)
                    or indices != sorted(set(indices))):
                raise ValueError("invalid Main CRLF newline indices: " + name)
            selected = set(indices)
            parts = canonical.split(b"\n")
            output = b"".join(part + (b"\r\n" if index in selected else b"\n")
                              for index, part in enumerate(parts[:-1])) + parts[-1]
        else:
            raise ValueError("unknown Main materialization mode")
        if sha(output) != record["runtime_raw_sha256"]:
            raise ValueError("Main runtime raw SHA256 mismatch: " + name)
        path = root.joinpath(*PurePosixPath(name).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(output)
        audit[name] = {"git_blob_sha256": sha(raw), "runtime_raw_sha256": sha(output), "materialization": mode}
        if mode == "main_pinned_line_endings":
            audit[name]["crlf_newline_indices"] = indices
    return audit


class Run:
    def __init__(self, root: Path, output: Path):
        self.root, self.output, self.steps = root, output, []
        self.environment = clean_environment(root, root / "data/runtime/game-v2.sqlite")

    def command(self, name: str, arguments: list[str], *, cwd: Path | None = None, environment=None) -> int:
        log = self.output / (name + ".txt")
        start = datetime.now(timezone.utc).isoformat()
        with log.open("w", encoding="utf-8") as stream:
            result = subprocess.run(arguments, cwd=cwd or self.root, env=environment or self.environment,
                                    stdout=stream, stderr=subprocess.STDOUT, check=False)
        self.steps.append({"name": name, "command": arguments, "cwd": str(cwd or self.root),
                           "started": start, "ended": datetime.now(timezone.utc).isoformat(),
                           "exit_code": result.returncode, "log": log.name, "log_sha256": sha(log.read_bytes())})
        print(f"{name}: exit {result.returncode}", flush=True)
        return result.returncode


def npm(*args: str) -> list[str]:
    executable = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if executable is None:
        raise ValueError("npm not found")
    return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", executable, *args] if os.name == "nt" else [executable, *args]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def http(url: str, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Session-Token"] = token
    request = urllib.request.Request(url, data=None if data is None else json.dumps(data).encode(), headers=headers)
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read())


def stop(process: subprocess.Popen, ledger: list) -> None:
    if process.poll() is None:
        if os.name == "nt":
            killer = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
            killer_exit = killer.returncode
        else:
            process.terminate()
            killer_exit = None
        process.wait(timeout=10)
    else:
        killer_exit = None
    ledger.append({"event": "stop", "pid": process.pid, "exit_code": process.returncode, "taskkill_exit_code": killer_exit})


def service_smoke(run: Run, root: Path, database: Path, *, version: str, frontend: bool) -> dict:
    backend_port, frontend_port = free_port(), free_port()
    while frontend_port == backend_port:
        frontend_port = free_port()
    base = f"http://127.0.0.1:{backend_port}/api"
    env = clean_environment(root, database)
    children, streams, ledger = [], [], []
    def start_backend():
        command = [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1",
                   "--port", str(backend_port), "--no-access-log"]
        stream = (run.output / f"v{version[0]}-backend-{len(ledger)}.txt").open("w", encoding="utf-8")
        streams.append(stream)
        child = subprocess.Popen(command, cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT)
        children.append(child)
        ledger.append({"event": "start", "pid": child.pid, "command": command, "cwd": str(root)})
        await_health(base + "/health", child)
        return child
    try:
        backend = start_backend()
        if frontend:
            front_env = dict(env)
            front_env["CAMPUS_BACKEND_URL"] = f"http://127.0.0.1:{backend_port}"
            command = npm("--prefix", "frontend", "run", "dev", "--", "--host", "127.0.0.1",
                          "--port", str(frontend_port), "--strictPort")
            stream = (run.output / "v2-frontend.txt").open("w", encoding="utf-8")
            streams.append(stream)
            child = subprocess.Popen(command, cwd=root, env=front_env, stdout=stream, stderr=subprocess.STDOUT)
            children.append(child)
            ledger.append({"event": "start", "pid": child.pid, "command": command, "cwd": str(root)})
            await_health(f"http://127.0.0.1:{frontend_port}/", child, json_response=False)
            status, health = http(f"http://127.0.0.1:{frontend_port}/api/health")
            assert status == 200 and health["status"] == "ok"
        _, session = http(base + "/sessions", {})
        session = session["data"]
        token, session_id, state = session["token"], session["session_id"], session["visible_state"]
        assert state["level_version"] == version
        receipts = []
        def operate(operation, extra=None):
            nonlocal state
            request = {"request_id": uuid.uuid4().hex, "revision": state["revision"], "generation": state["generation"]}
            request.update(extra or {})
            _, body = http(base + "/sessions/" + session_id + "/" + operation, request, token)
            assert body["ok"]
            state = body["data"]["visible_state"]
            return body["data"]
        for tool, arguments in ROUTE[:13]:
            receipts.append(operate("actions", {"tool": tool, "arguments": arguments})["receipt"])
        inventory = [item["item_id"] for item in state["inventory"]]
        assert ("emergency_key" in inventory) == (version == "1.0.0")
        assert receipts[-1]["consumed_item_ids"] == ([] if version == "1.0.0" else ["emergency_key"])
        saved = operate("save")["visible_state"]
        if version == "2.0.0":
            for tool, arguments in ROUTE[13:]:
                operate("actions", {"tool": tool, "arguments": arguments})
            assert state["status"] == "won" and [i["item_id"] for i in state["inventory"]] == ["access_card"]
        won = state
        stop(backend, ledger)
        backend = start_backend()
        _, persisted = http(base + "/sessions/" + session_id + "/state", token=token)
        assert persisted["data"]["visible_state"] == won
        restored = operate("restore")["visible_state"]
        fields = ["status", "room", "objects", "inventory", "clues", "exits", "progress"]
        assert {k: restored[k] for k in fields} == {k: saved[k] for k in fields}
        assert restored["generation"] != saved["generation"]
        return {"status": "PASS", "version": version, "provider": "mock", "service_ledger": ledger,
                "saved_state": saved, "state_before_restart": won, "restored_state": restored,
                "unlock_receipt": receipts[-1], "actual_paid_calls": 0}
    finally:
        for child in reversed(children):
            if child.poll() is None:
                stop(child, ledger)
        for stream in streams:
            stream.close()


def await_health(url: str, process: subprocess.Popen, *, json_response=True) -> None:
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("service exited during startup")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    if json_response:
                        assert json.loads(response.read())["status"] == "ok"
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(.2)
    raise RuntimeError("service startup timeout")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--main-pins", type=Path, required=True)
    parser.add_argument("--main-pins-sha256", required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--legacy-fixture", type=Path, required=True)
    parser.add_argument("--evaluator-release", action="append", default=[])
    args = parser.parse_args()
    root, output = args.workspace.resolve(), args.output.resolve()
    if root.exists() or output.exists():
        parser.error("workspace and evidence output must both be new paths")
    if not re.fullmatch(r"[0-9a-f]{40}", args.commit):
        parser.error("full committed source SHA required")
    pin_bytes = args.main_pins.read_bytes()
    if sha(pin_bytes) != args.main_pins_sha256:
        parser.error("Main pins hash mismatch")
    pins = json.loads(pin_bytes)
    if pins["commit"] != args.commit:
        parser.error("Main commit pin mismatch")
    output.mkdir(parents=True, exist_ok=False)
    root.mkdir(parents=True, exist_ok=False)
    run = Run(root, output)
    report = {"commit": args.commit, "archive_sha256": args.archive_sha256,
              "main_pins_sha256": args.main_pins_sha256, "python_executable": sys.executable,
              "python_version": sys.version, "workspace": str(root), "provider": "mock",
              "actual_paid_calls": 0, "environment_mutated": False, "steps": run.steps,
              "limitations": ["Uses the existing designated Conda environment; no new Python environment or pip install.",
                              "Service HTTP checks are automated local coverage, not human gameplay."]}
    code = 1
    hashes = {}
    try:
        hashes = materialize(args.source_archive, args.archive_sha256, root, pins)
        write_json(output / "materialization.json", hashes)
        fixture = args.legacy_fixture.read_bytes()
        if sha(fixture) != LEGACY_SHA:
            raise ValueError("historical M2 fixture raw SHA256 mismatch")
        fixture_path = root / "data/integration/m2-legacy-sqlite-165a961.py"
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_bytes(fixture)
        report["legacy_fixture"] = {"commit": LEGACY_COMMIT, "source_path": "backend/app/storage/sqlite.py",
                                    "runtime_path": "data/integration/m2-legacy-sqlite-165a961.py", "sha256": LEGACY_SHA}
        versions = {}
        for line in (root / "backend/requirements.lock.txt").read_text().splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            package, expected = line.split("==")
            actual = importlib.metadata.version(package)
            versions[package] = {"expected": expected, "actual": actual}
            if actual != expected:
                raise ValueError("installed lock mismatch: " + package)
        report["locked_python_dependencies"] = versions
        for name, command in [("pip-check", [sys.executable, "-m", "pip", "check"]),
                              ("node-version", [shutil.which("node") or "node", "--version"]),
                              ("npm-version", npm("--version")),
                              ("npm-ci", npm("--prefix", "frontend", "ci")),
                              ("unified-check", [sys.executable, "-m", "scripts.check", "--suite", "deterministic",
                                "--output", str(output / "check"), "--release-id", "clean-" + args.commit])]:
            result = run.command(name, command)
            if result:
                raise RuntimeError(f"{name} exited {result}")
        for release in args.evaluator_release:
            result = run.command("evaluator-" + release, [sys.executable, "-m", "evaluation.cli", "precheck", "--release", release])
            if result:
                raise RuntimeError(f"evaluator identity precheck exited {result}; Main pins must be corrected, never relaxed")
        v2 = service_smoke(run, root, root / "data/runtime/game-v2.sqlite", version="2.0.0", frontend=True)
        write_json(output / "v2-services.json", v2)
        v1_root = root / "release/archives/baseline_v1"
        if not (v1_root / "backend/app/main.py").is_file():
            raise ValueError("separate archived v1 source required")
        v1 = service_smoke(run, v1_root, root / "data/rollback/game-v1.sqlite", version="1.0.0", frontend=False)
        write_json(output / "v1-rollback.json", v1)
        report["v2_service_result"] = "v2-services.json"
        report["v1_rollback_result"] = "v1-rollback.json"
        code = 0
    except Exception as error:
        report["error"] = str(error)
        print("Reproduction stopped:", type(error).__name__, str(error), flush=True)
    finally:
        after = {name: sha(root.joinpath(*PurePosixPath(name).parts).read_bytes()) for name in hashes}
        before = {name: value["runtime_raw_sha256"] for name, value in hashes.items()}
        report["source_hashes_before"], report["source_hashes_after"] = before, after
        report["source_unchanged"] = before == after
        if not report["source_unchanged"]:
            code = 1
        report["exit_code"], report["status"] = code, "PASS" if code == 0 else "FAIL"
        report["completed_at"] = datetime.now(timezone.utc).isoformat()
        write_json(output / "report.json", report)
        print("Evidence:", output, "Exit:", code, flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
