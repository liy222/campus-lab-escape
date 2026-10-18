"""Test-only local app for UI; production routes/Store/Runtime, fake provider.

No product feature flags or backdoors. Import only from the owned QA runner.
"""
import copy
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ['AI_PROVIDER'] = 'mock'
import httpx
from backend.app.ai.provider import DeepSeekProvider, ProviderResult
from backend.app.main import create_app
import backend.app.ai.runtime as runtime_module
from fake_runtime import create_test_runtime

CALLS = []


async def forbidden(*args, **kwargs):
    raise AssertionError('External provider transport forbidden in QA app')


async def complete(provider, messages, tools, limits, **kwargs):
    CALLS.append({'messages': copy.deepcopy(messages), 'tools': copy.deepcopy(tools), 'kwargs': copy.deepcopy(kwargs)})
    content = json.dumps({'answer': f'可以先说说你已经观察到的内容，再选择一个小问题继续讨论。交流{len(CALLS)}。', 'clue_refs': []}, ensure_ascii=False)
    return ProviderResult(content, (), {'prompt_tokens': 29, 'completion_tokens': 17}, 'deepseek', 'deepseek-flash', 'deepseek-flash', 'stop')


DeepSeekProvider.complete = complete
runtime_module.create_request_runtime = create_test_runtime
httpx.AsyncClient.send = forbidden
app = create_app(os.environ['SQLITE_PATH'], gameplay_version='v3.4')


@app.get('/qa/companion-observations')
def observations():
    return {'calls': copy.deepcopy(CALLS), 'test_only': True}
