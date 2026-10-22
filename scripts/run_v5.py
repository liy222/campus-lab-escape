"""Run the isolated V5 app in production-preview or frontend development mode."""
from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import sqlite3
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

from scripts.dev import ROOT, npm_command, port_number

DEFAULT_BACKEND_PORT = 8001
DEFAULT_FRONTEND_PORT = 5174
OLD_DATABASE_NAMES = {"game.sqlite", "game-v3.1.sqlite", "game-v3.2.sqlite",
                      "game-v3.3.sqlite", "game-v3.4.sqlite"}


def ensure_port_available(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if os.name == "nt":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as error:
            raise RuntimeError(f"127.0.0.1:{port} is occupied or unavailable; no existing process was stopped") from error


def frontend_environment(inherited: dict[str, str], backend_url: str) -> dict[str, str]:
    prefixes = ("MODEL_", "DEEPSEEK_", "OPENAI_", "ANTHROPIC_", "AI_", "GOOGLE_",
                "GEMINI_", "MISTRAL_", "COHERE_", "OLLAMA_", "HUGGINGFACE_", "HF_", "AZURE_OPENAI_")
    secret_parts = ("API_KEY", "APIKEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
    env = {k: v for k, v in inherited.items()
           if not k.upper().startswith(prefixes) and not k.upper().startswith("VITE_")
           and k.upper() != "SQLITE_PATH" and not any(p in k.upper() for p in secret_parts)}
    env["VITE_GAMEPLAY_VERSION"] = "v5"
    env["CAMPUS_BACKEND_URL"] = backend_url
    return env


def backend_environment(inherited: dict[str, str], *, dev: bool, database: Path) -> dict[str, str]:
    prefixes = ("MODEL_", "DEEPSEEK_", "OPENAI_", "ANTHROPIC_", "AI_", "GOOGLE_",
                "GEMINI_", "MISTRAL_", "COHERE_", "OLLAMA_", "HUGGINGFACE_", "HF_", "AZURE_OPENAI_")
    secret_parts = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
    env = {k: v for k, v in inherited.items()
           if not k.upper().startswith(prefixes)
           and not any(part in k.upper() for part in secret_parts)
           and not k.upper().startswith("VITE_")
           and k.upper() not in {"SQLITE_PATH", "GAMEPLAY_VERSION", "V5_DEV", "AI_PROVIDER"}}
    env.update({"GAMEPLAY_VERSION": "v5", "SQLITE_PATH": str(database),
                "AI_PROVIDER": "mock", "PYTHONUTF8": "1"})
    if dev:
        env["V5_DEV"] = "1"
    return env


def database_path(value: str | None, *, dev: bool) -> Path:
    if value and not dev:
        raise RuntimeError("--database is a development-only option; use it with --dev")
    path = Path(value) if value else Path("data/game-v5.sqlite")
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    if path.name.casefold() in {name.casefold() for name in OLD_DATABASE_NAMES}:
        raise RuntimeError("refusing a known legacy database path; V5 must use game-v5.sqlite")
    if path.name.casefold() != "game-v5.sqlite":
        raise RuntimeError("V5 database filename must be game-v5.sqlite")
    if path.exists():
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError("refusing an existing empty or non-file database path")
        try:
            with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as connection:
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if "v5_metadata" not in tables:
                    raise RuntimeError("refusing an existing database without the V5 identity marker")
                marker = connection.execute(
                    "SELECT value FROM v5_metadata WHERE key='database_version'"
                ).fetchone()
                if marker != ("5",):
                    raise RuntimeError("refusing an existing database without the V5 version marker")
        except sqlite3.DatabaseError as error:
            raise RuntimeError("refusing an unreadable or non-V5 database") from error
    return path


def stop_child(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        import signal
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def wait_healthy(processes: list[subprocess.Popen[bytes]], urls: list[str], timeout: float) -> None:
    pending = set(urls)
    deadline = time.monotonic() + timeout
    while pending and time.monotonic() < deadline:
        if any(p.poll() is not None for p in processes):
            raise RuntimeError("a V5 service exited during startup; inspect its output above")
        for url in list(pending):
            try:
                with urllib.request.urlopen(url, timeout=1) as response:
                    if response.status == 200:
                        pending.remove(url)
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
        if pending:
            time.sleep(0.2)
    if pending:
        raise RuntimeError("startup timed out waiting for: " + ", ".join(sorted(pending)))


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev", action="store_true", help="run Vite at :5174 with backend at :8001")
    parser.add_argument("--open-browser", action="store_true", help="open only after health checks pass")
    parser.add_argument("--backend-port", type=port_number, default=8001)
    parser.add_argument("--frontend-port", type=port_number, default=5174)
    parser.add_argument("--database", help="development only: isolated database path named game-v5.sqlite")
    parser.add_argument("--startup-timeout", type=float, default=40.0)
    args = parser.parse_args()
    children: list[subprocess.Popen[bytes]] = []
    try:
        if args.backend_port != DEFAULT_BACKEND_PORT or args.frontend_port != DEFAULT_FRONTEND_PORT:
            raise RuntimeError("V5 host configuration is fixed: backend 127.0.0.1:8001 and frontend 127.0.0.1:5174")
        if args.startup_timeout <= 0:
            raise RuntimeError("startup timeout must be positive")
        selected_database = database_path(args.database, dev=args.dev)
        if not importlib.util.find_spec("uvicorn") or not importlib.util.find_spec("fastapi"):
            raise RuntimeError("backend dependencies are missing; install backend/requirements.lock.txt")
        if args.dev and not (ROOT / "frontend/node_modules/vite/bin/vite.js").is_file():
            raise RuntimeError("frontend dependencies are missing; run npm --prefix frontend ci")
        ports = [args.backend_port] + ([args.frontend_port] if args.dev else [])
        for port in ports:
            ensure_port_available(port)
        backend_env = backend_environment(os.environ.copy(), dev=args.dev, database=selected_database)
        backend_url = f"http://127.0.0.1:{args.backend_port}"
        options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
        command = [sys.executable, "-B", "-X", "utf8", "-m", "uvicorn", "backend.app.main:app",
                   "--host", "127.0.0.1", "--port", str(args.backend_port), "--no-proxy-headers"]
        if not args.dev:
            build = ROOT / "frontend/dist-v5/index.html"
            if not build.is_file():
                raise RuntimeError("V5 production build is missing at frontend/dist-v5; build it with VITE_GAMEPLAY_VERSION=v5 npm --prefix frontend run build")
        children.append(subprocess.Popen(command, cwd=ROOT, env=backend_env, **options))
        urls = [backend_url + "/health"]
        page = backend_url + "/" if not args.dev else f"http://127.0.0.1:{args.frontend_port}/"
        if args.dev:
            vite_command = npm_command("--prefix", "frontend", "run", "dev", "--", "--host", "127.0.0.1",
                                       "--port", str(args.frontend_port), "--strictPort")
            vite_env = frontend_environment(os.environ.copy(), backend_url)
            children.append(subprocess.Popen(vite_command, cwd=ROOT, env=vite_env, **options))
            urls.append(page)
        wait_healthy(children, urls, args.startup_timeout)
        print(f"V5 ready: {page}\nBackend health: {urls[0]}\nPress Ctrl+C to stop services started by this launcher.", flush=True)
        if args.open_browser:
            try:
                if not webbrowser.open(page):
                    print(f"Browser did not open automatically; visit {page}.", flush=True)
            except Exception:
                print(f"Browser could not be opened automatically; visit {page}.", flush=True)
        while all(p.poll() is None for p in children):
            time.sleep(0.25)
        return next((p.returncode for p in children if p.returncode), 1)
    except KeyboardInterrupt:
        print("\nStopping V5 services started by this launcher.", flush=True)
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"V5 startup failed: {error}", file=sys.stderr)
        return 1
    finally:
        for child in reversed(children):
            stop_child(child)


if __name__ == "__main__":
    raise SystemExit(main())
