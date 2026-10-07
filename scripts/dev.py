"""Start and supervise the local backend and frontend together."""
from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parents[1]


def load_env_file(path: Path, environment: dict[str, str]) -> None:
    """Read strict single-line KEY=VALUE data without shell expansion or logging."""
    if not path.exists():
        return
    values: dict[str, str] = {}
    for line_number, original in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = original.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) or key in values:
            raise RuntimeError(f"Invalid .env entry on line {line_number}; expected unique KEY=VALUE")
        if value.startswith(("'", '"')):
            if len(value) < 2 or value[-1] != value[0]:
                raise RuntimeError(f"Invalid .env quoting on line {line_number}")
            value = value[1:-1]
        values[key] = value
    for key, value in values.items():
        environment.setdefault(key, value)


def make_frontend_environment(inherited: dict[str, str], backend_url: str,
                              gameplay_version: str = "upgrade") -> dict[str, str]:
    """Pass only explicit public settings to Vite, never inherited VITE secrets."""
    if gameplay_version not in {"legacy", "v3.1", "v3.2", "v3.3", "v3.4", "upgrade"}:
        raise ValueError("gameplay_version must be 'legacy', 'v3.1', 'v3.2', 'v3.3', 'v3.4' or 'upgrade'")
    server_prefixes = ("MODEL_", "DEEPSEEK_", "OPENAI_", "ANTHROPIC_", "AI_",
                       "GOOGLE_", "GEMINI_", "MISTRAL_", "COHERE_", "OLLAMA_",
                       "HUGGINGFACE_", "HF_", "AZURE_OPENAI_")
    secret_fragments = ("API_KEY", "APIKEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
    environment = {key: value for key, value in inherited.items()
                   if not key.upper().startswith(server_prefixes)
                   and not key.upper().startswith("VITE_")
                   and key.upper() != "SQLITE_PATH"
                   and not any(fragment in key.upper() for fragment in secret_fragments)}
    environment["CAMPUS_BACKEND_URL"] = backend_url
    environment["VITE_GAMEPLAY_VERSION"] = "v3.4" if gameplay_version == "upgrade" else gameplay_version
    return environment


def port_number(value: str) -> int:
    port = int(value)
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def npm_command(*arguments: str) -> list[str]:
    executable = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not executable:
        raise RuntimeError("npm is unavailable; install Node.js and ensure npm is on PATH")
    if os.name == "nt":
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", executable, *arguments]
    return [executable, *arguments]


def ensure_port_available(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if os.name == "nt":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as error:
            raise RuntimeError(f"127.0.0.1:{port} is occupied or unavailable; choose another port") from error


def terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        # npm creates a child Node process. Stop only this supervised process tree.
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        import signal
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", default=None, help="override AI_PROVIDER from environment or root .env")
    parser.add_argument("--backend-port", type=port_number, default=8000)
    parser.add_argument("--frontend-port", type=port_number, default=5173)
    parser.add_argument("--startup-timeout", type=float, default=30.0)
    parser.add_argument("--open-browser", action="store_true",
                        help="open the game page after both services pass their health checks")
    args = parser.parse_args()
    children: list[subprocess.Popen[bytes]] = []
    try:
        if args.backend_port == args.frontend_port:
            raise RuntimeError("backend and frontend ports must differ")
        if args.startup_timeout <= 0:
            raise RuntimeError("startup timeout must be positive")
        if not importlib.util.find_spec("uvicorn") or not importlib.util.find_spec("fastapi"):
            raise RuntimeError("backend dependencies are missing; install backend/requirements.lock.txt")
        if not (ROOT / "frontend/node_modules/vite/bin/vite.js").is_file():
            raise RuntimeError("frontend dependencies are missing; run npm --prefix frontend ci")
        for port in (args.backend_port, args.frontend_port):
            ensure_port_available(port)
        frontend_command = npm_command("--prefix", "frontend", "run", "dev", "--",
                                       "--host", "127.0.0.1", "--port", str(args.frontend_port), "--strictPort")
        backend_environment = os.environ.copy()
        load_env_file(ROOT / ".env", backend_environment)
        gameplay_version = (backend_environment.get("GAMEPLAY_VERSION") or "upgrade").strip().lower()
        if gameplay_version not in {"legacy", "v3.1", "v3.2", "v3.3", "v3.4", "upgrade"}:
            raise RuntimeError("GAMEPLAY_VERSION must be 'legacy', 'v3.1', 'v3.2', 'v3.3', 'v3.4' or 'upgrade'")
        backend_environment["GAMEPLAY_VERSION"] = gameplay_version
        provider = args.provider if args.provider is not None else (backend_environment.get("AI_PROVIDER") or "mock")
        backend_environment["AI_PROVIDER"] = provider
        frontend_environment = make_frontend_environment(
            os.environ.copy(), f"http://127.0.0.1:{args.backend_port}", gameplay_version)
        process_options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
        children.append(subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.app.main:app",
                                          "--host", "127.0.0.1", "--port", str(args.backend_port)],
                                         cwd=ROOT, env=backend_environment, **process_options))
        children.append(subprocess.Popen(frontend_command, cwd=ROOT, env=frontend_environment, **process_options))
        urls = [f"http://127.0.0.1:{args.backend_port}/api/health", f"http://127.0.0.1:{args.frontend_port}/"]
        pending = set(urls)
        deadline = time.monotonic() + args.startup_timeout
        while pending and time.monotonic() < deadline:
            if any(child.poll() is not None for child in children):
                raise RuntimeError("a service exited during startup; inspect its output above")
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
            raise RuntimeError("startup timed out: " + ", ".join(sorted(pending)))
        print(f"\nGame: {urls[1]}\nBackend: {urls[0]}\nPress Ctrl+C to stop both services.", flush=True)
        if args.open_browser:
            try:
                if not webbrowser.open(urls[1]):
                    print(f"Browser did not open automatically; visit {urls[1]}.", flush=True)
            except Exception as error:
                print(f"Could not open a browser ({error}); visit {urls[1]} manually.", flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(0.3)
        print("A service exited; stopping the other service.", file=sys.stderr)
        return next((child.returncode for child in children if child.returncode), 1)
    except KeyboardInterrupt:
        print("\nStopping both services.", flush=True)
        return 0
    except (OSError, RuntimeError) as error:
        print(f"Startup failed: {error}", file=sys.stderr)
        return 1
    finally:
        for child in reversed(children):
            terminate(child)


if __name__ == "__main__":
    raise SystemExit(main())
