"""Delivery entry-point probes; synthetic fixtures, not formal product QA."""
from __future__ import annotations

import _thread
import contextlib
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import urllib.request
from unittest.mock import patch

from scripts import check, dev, reset

OUTPUT = Path(__file__).parent / "credential-isolation-recheck"
OUTPUT.mkdir(exist_ok=True)
records = []


def record(name, **details):
    records.append({"name": name, "time_utc": datetime.now(timezone.utc).isoformat(), **details})


def available_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def run():
    with tempfile.TemporaryDirectory(prefix="campus-delivery-") as temporary:
        base = Path(temporary)
        env_file = base / ".env"
        env_file.write_text("# synthetic fixture only\nAI_PROVIDER=deepseek\nMODEL_API_KEY='synthetic-key-only'\nSHELL_LITERAL=$(never-run); still-literal\n", encoding="utf-8")
        values = {"AI_PROVIDER": "existing-environment"}
        dev.load_env_file(env_file, values)
        assert values["AI_PROVIDER"] == "existing-environment"
        assert values["MODEL_API_KEY"] == "synthetic-key-only"
        assert values["SHELL_LITERAL"] == "$(never-run); still-literal"
        record("env-existing-priority-and-literal-data", passed=True, secret_values_logged=False)
        for invalid in ["export KEY=value", "KEY=one\nKEY=two", "KEY='unclosed", "missing-separator"]:
            env_file.write_text(invalid, encoding="utf-8")
            try:
                dev.load_env_file(env_file, {})
            except RuntimeError as error:
                assert invalid not in str(error)
            else:
                raise AssertionError("invalid env entry accepted")
        record("env-invalid-format-rejected", passed=True, cases=4)
        inherited = {"PATH": os.environ["PATH"], "MODEL_API_KEY": "synthetic-model-only",
                     "DEEPSEEK_API_KEY": "synthetic-deepseek-only", "OPENAI_ACCESS_TOKEN": "synthetic-token-only",
                     "VITE_MODEL_API_KEY": "synthetic-vite-only", "AI_PROVIDER": "deepseek"}
        frontend = dev.make_frontend_environment(inherited, "http://127.0.0.1:12345")
        assert frontend == {"PATH": os.environ["PATH"], "CAMPUS_BACKEND_URL": "http://127.0.0.1:12345"}
        record("frontend-inherited-credentials-stripped", passed=True, credential_values_logged=False)
        env_file.write_text("AI_PROVIDER=deepseek\nMODEL_API_KEY=synthetic-key-only\n", encoding="utf-8")
        child_environments = []
        original_popen = dev.subprocess.Popen
        loader = dev.load_env_file

        def capture_child(*args, **kwargs):
            if "env" in kwargs:
                child_environments.append(dict(kwargs["env"]))
            return original_popen(*args, **kwargs)

        for provider_option, expected in [([], "deepseek"), (["--provider", "mock"], "mock")]:
            # Force a pre-launch npm lookup failure after env parsing, so no service or API runs.
            # Exercise provider selection via a harmless fake Popen that exits immediately.
            class ExitedChild:
                returncode = 17

                def poll(self):
                    return self.returncode

            captured = []

            def fake_child(*args, **kwargs):
                captured.append(kwargs["env"])
                return ExitedChild()

            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.object(dev, "load_env_file", side_effect=lambda path, environment: loader(env_file, environment)), \
                 patch.object(dev, "ensure_port_available"), patch.object(dev.subprocess, "Popen", side_effect=fake_child), \
                 patch.dict(os.environ, {"AI_PROVIDER": ""}), \
                 patch.object(sys, "argv", ["scripts.dev", *provider_option]), \
                 contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                # Remove only this probe's artificial empty variable to allow file fallback.
                os.environ.pop("AI_PROVIDER", None)
                result = dev.main()
            assert result == 1 and captured and captured[0]["AI_PROVIDER"] == expected
            assert "synthetic-key-only" not in stdout.getvalue() + stderr.getvalue()
            record("provider-selection-" + expected, passed=True, exit_code=result, synthetic_key_not_logged=True)

        # Real services use ephemeral ports and isolated SQLite, never the root .env.
        backend_port, frontend_port = available_port(), available_port()
        while backend_port == frontend_port:
            frontend_port = available_port()
        readiness = []

        def watcher():
            deadline = time.monotonic() + 20
            urls = [f"http://127.0.0.1:{backend_port}/api/health", f"http://127.0.0.1:{frontend_port}/api/health"]
            try:
                while time.monotonic() < deadline:
                    try:
                        responses = []
                        for url in urls:
                            with urllib.request.urlopen(url, timeout=1) as response:
                                responses.append({"url": url, "status": response.status, "body": json.loads(response.read())})
                        readiness.extend(responses)
                        # Allow scripts.dev to finish its own readiness messages.
                        time.sleep(0.5)
                        break
                    except OSError:
                        time.sleep(0.1)
            finally:
                _thread.interrupt_main()

        watcher_thread = threading.Thread(target=watcher, daemon=True)
        with patch.object(dev, "load_env_file", side_effect=lambda path, environment: loader(env_file, environment)), \
             patch.object(dev.subprocess, "Popen", side_effect=capture_child), \
             patch.dict(os.environ, {"SQLITE_PATH": str(base / "runtime/game.sqlite"),
                                     "DEEPSEEK_API_KEY": "synthetic-deepseek-only",
                                     "VITE_MODEL_API_KEY": "synthetic-vite-only"}), \
             patch.object(sys, "argv", ["scripts.dev", "--provider", "mock", "--backend-port", str(backend_port), "--frontend-port", str(frontend_port)]):
            watcher_thread.start()
            result = dev.main()
        watcher_thread.join(timeout=2)
        assert result == 0 and len(readiness) == 2 and all(row["status"] == 200 for row in readiness)
        for port in (backend_port, frontend_port):
            with socket.socket() as client:
                client.settimeout(1)
                assert client.connect_ex(("127.0.0.1", port)) != 0
        assert len(child_environments) == 2
        assert child_environments[0]["AI_PROVIDER"] == "mock"
        assert child_environments[0]["MODEL_API_KEY"] == "synthetic-key-only"
        assert not any("API_KEY" in key or key.startswith(("AI_", "MODEL_", "DEEPSEEK_"))
                       for key in child_environments[1])
        record("ephemeral-real-start-stop", passed=True, exit_code=result, responses=readiness,
               ports_released=True, actual_root_env_read=False, provider_api_calls=0)

        with socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen()
            port = occupied.getsockname()[1]
            try:
                dev.ensure_port_available(port)
            except RuntimeError:
                pass
            else:
                raise AssertionError("occupied port accepted")
        record("occupied-port-rejection", passed=True)

        for name, fixture, expected in [("missing", None, 4), ("empty", "", 5), ("failing", "def test_probe():\n    assert False\n", 1), ("passing", "def test_probe():\n    assert True\n", 0)]:
            root = base / ("harness-" + name)
            root.mkdir()
            if fixture is not None:
                (root / "tests").mkdir()
                if fixture:
                    (root / "tests/test_probe.py").write_text(fixture, encoding="utf-8")
            stream = io.StringIO()
            with patch.object(check, "ROOT", root), \
                 patch.object(check, "npm_command", return_value=[sys.executable, "-c", "raise SystemExit(0)"]), \
                 patch.object(sys, "argv", ["scripts.check", "--output", str(OUTPUT / ("harness-" + name))]), \
                 contextlib.redirect_stdout(stream):
                result = check.main()
            assert result == expected, (name, result)
            summaries = list((OUTPUT / ("harness-" + name)).glob("*/summary.json"))
            summary = json.loads(summaries[0].read_text(encoding="utf-8"))
            assert summary["exit_code"] == expected
            assert summary["status"] == ("PASS" if expected == 0 else "FAIL")
            record("synthetic-harness-" + name, passed=True, observed_exit=result,
                   expected_exit=expected, build_is_synthetic=True,
                   evidence=summaries[0].relative_to(OUTPUT).as_posix())

        root = base / "reset-project"
        root.mkdir()
        data = root / "data"
        data.mkdir()
        database = data / "game.sqlite"
        database.write_bytes(b"Synthetic fixture only")
        def reset_call(arguments):
            with patch.object(reset, "ROOT", root), patch.object(sys, "argv", ["scripts.reset", *arguments]), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return reset.main()
        assert reset_call(["--data-dir", str(data)]) == 0 and database.exists()
        assert reset_call(["--data-dir", str(root), "--confirm"]) == 1 and database.exists()
        assert reset_call(["--data-dir", str(data), "--confirm"]) == 0 and not database.exists()
        record("reset-explicit-target-preview-and-boundary", passed=True, exits=[0, 1, 0], existing_user_data_touched=False)
    (OUTPUT / "results.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Delivery probes passed: {len(records)}; no paid calls or formal product QA.")


if __name__ == "__main__":
    run()
