"""QA-only request runtime construction without any budget file access.

Route authentication/mode, Store and Runtime remain real. Provider.complete is
separately replaced by each caller. This deliberately does not test production
provider construction or budget accounting.
"""
from backend.app.ai.mock import DeterministicMockProvider
from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider
from backend.app.ai.runtime import Runtime


def create_test_runtime(base, provider_name, api_key):
    if provider_name == 'mock':
        provider = DeterministicMockProvider()
    else:
        provider = object.__new__(DeepSeekProvider)
        provider.config = DeepSeekConfig(api_key=api_key)
        provider.ledger = None
        provider.transport = None
        provider.last_response_metadata = None
    return Runtime(provider, base.limits, context_mode=base.context_mode)
