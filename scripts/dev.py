"""Start and supervise the local backend and frontend together."""
from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


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
    parser.add_argument("--provider", default="mock")
    parser.add_argument("--backend-port", type=port_number, default=8000)
    parser.add_argument("--frontend-port", type=port_number, default=5173)
    parser.add_argument("--startup-timeout", type=float, default=30.0)
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
        environment = os.environ.copy()
        environment.update(AI_PROVIDER=args.provider,
                           CAMPUS_BACKEND_URL=f"http://127.0.0.1:{args.backend_port}")
        process_options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
        children.append(subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.app.main:app",
                                          "--host", "127.0.0.1", "--port", str(args.backend_port)],
                                         cwd=ROOT, env=environment, **process_options))
        children.append(subprocess.Popen(frontend_command, cwd=ROOT, env=environment, **process_options))
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
        print(f"\nGame: {urls[1]}\nBackend: {urls[0]}\nProvider: {args.provider}\nPress Ctrl+C to stop both services.", flush=True)
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
