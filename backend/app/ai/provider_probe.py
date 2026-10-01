"""Isolated, offline provider boundary probe using only the Python standard library.

This module does not connect to a provider or import game state/storage. Its
synthetic messages and tools demonstrate a bounded provider conversation only.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import platform
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProbeLimits:
    max_model_calls: int = 3
    max_read_tools: int = 5
    request_timeout_seconds: float = 0.02
    turn_timeout_seconds: float = 0.2


class MockFailure(Exception):
    """Fixed, sanitized synthetic error; never includes raw upstream content."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class MockProvider:
    """Scripted fixtures, not a model or real API adapter."""

    def __init__(self, scenario: str):
        self.scenario = scenario
        self.calls = 0

    async def complete(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        self.calls += 1
        if self.scenario == "timeout":
            await asyncio.sleep(1)
        if self.scenario in {"auth", "service"}:
            raise MockFailure("AUTH_ERROR" if self.scenario == "auth" else "SERVICE_ERROR")
        if self.scenario == "malformed":
            return {"answer": 42, "unexpected": "fixture"}
        if self.scenario == "loop":
            return {"answer": "", "tools": ["get_inventory", "get_inventory"]}
        if self.scenario == "model_limit":
            return {"answer": "", "tools": ["get_inventory"]}
        if self.scenario == "illegal_tool":
            return {"answer": "", "tools": ["shell"]}
        if self.calls == 1:
            return {"answer": "", "tools": ["get_inventory"]}
        return {"answer": "Mock inventory is empty; inspect visible objects next.", "tools": []}


def validate_response(response: Any) -> tuple[str, list[str]]:
    if not isinstance(response, dict) or set(response) != {"answer", "tools"}:
        raise MockFailure("MALFORMED_RESPONSE")
    answer, tool_names = response["answer"], response["tools"]
    if not isinstance(answer, str) or len(answer) > 4096:
        raise MockFailure("MALFORMED_RESPONSE")
    if not isinstance(tool_names, list) or not all(isinstance(name, str) for name in tool_names):
        raise MockFailure("MALFORMED_RESPONSE")
    if any(name != "get_inventory" for name in tool_names):
        raise MockFailure("ILLEGAL_TOOL")
    return answer, tool_names


async def run_scenario(scenario: str, limits: ProbeLimits) -> dict[str, Any]:
    provider = MockProvider(scenario)
    messages: list[dict[str, Any]] = [{"role": "user", "content": "Synthetic offline probe"}]
    read_count = 0
    events: list[dict[str, Any]] = []
    started = time.monotonic()
    status = "MODEL_CALL_LIMIT"
    answer = ""
    while provider.calls < limits.max_model_calls:
        remaining = limits.turn_timeout_seconds - (time.monotonic() - started)
        if remaining <= 0:
            status = "TURN_TIMEOUT"
            break
        try:
            response = await asyncio.wait_for(
                provider.complete(messages), timeout=min(limits.request_timeout_seconds, remaining)
            )
            answer, tool_names = validate_response(response)
        except TimeoutError:
            status = "TURN_TIMEOUT" if remaining < limits.request_timeout_seconds else "REQUEST_TIMEOUT"
            events.append({"kind": "stopped", "reason": status})
            break
        except MockFailure as error:
            status = error.code
            events.append({"kind": "stopped", "reason": status})
            break
        events.append({"kind": "mock_response", "call": provider.calls, "response": response})
        if not tool_names:
            status = "COMPLETED"
            break
        for name in tool_names:
            if read_count >= limits.max_read_tools:
                status = "READ_TOOL_LIMIT"
                break
            read_count += 1
            tool_result = {"tool": name, "inventory": [], "source": "synthetic_fixture"}
            messages.append({"role": "tool", "content": tool_result})
            events.append({"kind": "mock_read", "ordinal": read_count, "result": tool_result})
        if status == "READ_TOOL_LIMIT":
            break
    return {
        "scenario": scenario,
        "status": status,
        "model_calls": provider.calls,
        "read_tools": read_count,
        "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
        "answer": answer,
        "usage": None,
        "usage_reason": "No real model call; synthetic fixtures do not have measured token usage.",
        "events": events,
    }


async def run_probe() -> dict[str, Any]:
    limits = ProbeLimits()
    expected = {
        "normal": ("COMPLETED", 2, 1),
        "timeout": ("REQUEST_TIMEOUT", 1, 0),
        "malformed": ("MALFORMED_RESPONSE", 1, 0),
        "auth": ("AUTH_ERROR", 1, 0),
        "service": ("SERVICE_ERROR", 1, 0),
        "loop": ("READ_TOOL_LIMIT", 3, 5),
        "model_limit": ("MODEL_CALL_LIMIT", 3, 3),
        "illegal_tool": ("ILLEGAL_TOOL", 1, 0),
    }
    results = []
    for scenario, expected_tuple in expected.items():
        result = await run_scenario(scenario, limits)
        actual = (result["status"], result["model_calls"], result["read_tools"])
        result["expected"] = {"status": expected_tuple[0], "model_calls": expected_tuple[1], "read_tools": expected_tuple[2]}
        result["passed"] = actual == expected_tuple
        results.append(result)
    return {
        "task": "T04", "scope": "isolated offline mock provider probe",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "executable": sys.executable,
        "real_api_called": False, "provider_model_id": None, "provider_model_version": None,
        "cost": None, "cost_reason": "No provider/model/budget approved; no paid call was performed.",
        "limits": asdict(limits), "results": results,
        "passed": all(result["passed"] for result in results),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("evidence/provider"))
    args = parser.parse_args()
    report = asyncio.run(run_probe())
    run_dir = args.output / datetime.now(timezone.utc).strftime("probe-%Y%m%dT%H%M%S%fZ")
    run_dir.mkdir(parents=True, exist_ok=False)
    report_path = run_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [f"{item['scenario']}: {item['status']} calls={item['model_calls']} reads={item['read_tools']} passed={item['passed']}" for item in report["results"]]
    exit_code = 0 if report["passed"] else 1
    lines.extend([f"real_api_called=False", f"exit_code={exit_code}", f"evidence={report_path}"])
    output = "\n".join(lines) + "\n"
    (run_dir / "output.txt").write_text(output, encoding="utf-8")
    print(output, end="")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
