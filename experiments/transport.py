"""Safe experiment-only HTTP receipt observer; no headers/body/request retained."""
from pathlib import Path

import httpx

from .common import ROOT

OFFICIAL_ENDPOINT = httpx.URL("https://api.deepseek.com/chat/completions")


class ReceiptObserver(httpx.AsyncBaseTransport):
    def __init__(self, inner):
        self.inner = inner
        self.invoked = False
        self.received = None
        self.status_code = None

    async def handle_async_request(self, request):
        if request.url != OFFICIAL_ENDPOINT:
            raise ValueError("UNAPPROVED_EXPERIMENT_ENDPOINT")
        self.invoked = True
        response = await self.inner.handle_async_request(request)
        # A returned HTTP response is evidence even when parsing/auth fails.
        self.received = True
        self.status_code = response.status_code
        return response

    async def aclose(self):
        await self.inner.aclose()

    def fields(self):
        received = self.received if self.invoked else False
        return {"response_received": received, "upstream_delivery_known": received,
                "http_status_code": self.status_code}


def observe(provider):
    """Wrap after approved Provider construction; keep production ledger fixed.

    Only MockTransport may use a synthetic ledger. There is no CLI transport,
    URL or ledger override. The production constructor already validated its
    canonical ledger before this observer is installed, and we check it again.
    """
    original = provider.transport
    if original is None:
        if Path(provider.ledger.path).resolve() != (ROOT / "data/ai-budget.sqlite").resolve():
            raise ValueError("UNAPPROVED_PRODUCTION_LEDGER")
        inner = httpx.AsyncHTTPTransport(trust_env=False, retries=0)
    elif isinstance(original, httpx.MockTransport):
        inner = original
    else:
        raise ValueError("UNAPPROVED_EXPERIMENT_TRANSPORT")
    observer = ReceiptObserver(inner)
    provider.transport = observer
    return original, observer
