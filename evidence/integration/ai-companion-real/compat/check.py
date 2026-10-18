from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from backend.app.ai.budget import BudgetLedger
from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider, ProviderError

ACCEPTED = (
    "deepseek-flash",
    "deepseek-v4.1-flash",
    "DeepSeek-V4.1-Flash",
    "deepseek-v4.1-flash-1017",
    "DeepSeek-V4.1-Flash-1017",
)
REJECTED = "deepseek-unrelated-model"


def response_for(model: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": model,
            "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3, "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 2},
        },
    )


async def exercise(model: str, ledger_path: Path, expected_ok: bool) -> dict:
    seen = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append({"url": str(request.url), "auth": request.headers.get("authorization"), "body": json.loads(request.content)})
        return response_for(model)

    ledger = BudgetLedger(path=ledger_path)
    provider = DeepSeekProvider(DeepSeekConfig("temporary-test-key"), ledger, transport=httpx.MockTransport(handler))
    try:
        result = await provider.complete([{"role": "user", "content": "hello"}], [], scope="compat-test")
        assert expected_ok, f"unexpectedly accepted {model}"
        assert result.reported_model == model
        assert result.requested_model == "deepseek-flash"
        assert not ledger.snapshot()["frozen"]
        outcome = "accepted"
    except ProviderError as error:
        assert not expected_ok, f"unexpected rejection {model}: {error.code}"
        assert error.code == "UNAPPROVED_REPORTED_MODEL", error.code
        assert ledger.snapshot()["frozen"], "unapproved model did not freeze the temporary ledger"
        outcome = "rejected_and_frozen"
    assert len(seen) == 1, "expected exactly one intercepted request"
    assert seen[0]["url"] == "https://api.deepseek.com/chat/completions"
    assert seen[0]["auth"] == "Bearer temporary-test-key"
    assert seen[0]["body"]["model"] == "deepseek-flash"
    return {"reported_model": model, "outcome": outcome, "requested_model": seen[0]["body"]["model"], "url": seen[0]["url"], "external_network": False}


def main() -> None:
    results = []
    with tempfile.TemporaryDirectory(prefix="ai-companion-model-compat-") as temp:
        tempdir = Path(temp)
        for index, model in enumerate(ACCEPTED):
            results.append(asyncio.run(exercise(model, tempdir / f"accepted-{index}.sqlite", True)))
        results.append(asyncio.run(exercise(REJECTED, tempdir / "rejected.sqlite", False)))
    print(json.dumps({"checks": results, "passed": len(results)}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
