"""Owned TEMP browser service; injected controlled matrix cache, no model IO."""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[5]
db = Path(os.environ['SQLITE_PATH']).resolve()
db.relative_to(Path(tempfile.gettempdir()).resolve())
assert db.name == 'game-v5.sqlite'
index_path = Path(os.environ['STRUCTURE_FIXTURE_INDEX']).resolve()
index_path.relative_to(ROOT / 'evidence/upgrade/v5.0/structure-diversity/qa')
index = json.loads(index_path.read_text(encoding='utf-8'))
cache = Path(index['directory']).resolve(); cache.relative_to(Path(tempfile.gettempdir()).resolve())
assert index['synthetic_only'] is True
receipt = Path(os.environ['STRUCTURE_BROWSER_SERVER_RECEIPT']).resolve()
receipt.relative_to(ROOT / 'evidence/upgrade/v5.0/structure-diversity/qa')
facts = {'synthetic_generation_calls': 0, 'network_config_ledger_nonTEMP_denied_attempts': 0,
         'stdlib_socketpair_local_IPC_connects': 0, 'real_paid_calls': 0}
receipt_lock = threading.RLock()


def save_receipt():
    with receipt_lock:
        temp = receipt.with_suffix('.tmp')
        temp.write_text(json.dumps(facts, indent=2) + '\n', encoding='utf-8')
        temp.replace(receipt)


def deny(*args, **kwargs):
    facts['network_config_ledger_nonTEMP_denied_attempts'] += 1
    save_receipt()
    raise RuntimeError('BROWSER_SERVICE_FORBIDDEN_RUNTIME_BOUNDARY')


original_socketpair = socket.socketpair
original_socket_connect = socket.socket.connect
original_socket_connect_ex = socket.socket.connect_ex
original_db_connect = sqlite3.connect
socketpair_context = threading.local()


def inside_original_socketpair(address):
    return (getattr(socketpair_context, 'active', False)
            and isinstance(address, tuple) and len(address) in (2, 4)
            and address[0] in {'127.0.0.1', '::1'}
            and type(address[1]) is int and 0 < address[1] <= 65535)


def guarded_socket_connect(connection, address):
    if inside_original_socketpair(address):
        facts['stdlib_socketpair_local_IPC_connects'] += 1
        save_receipt()
        return original_socket_connect(connection, address)
    return deny()


def guarded_socket_connect_ex(connection, address):
    if inside_original_socketpair(address):
        facts['stdlib_socketpair_local_IPC_connects'] += 1
        save_receipt()
        return original_socket_connect_ex(connection, address)
    return deny()


def guarded_socketpair(*args, **kwargs):
    previous = getattr(socketpair_context, 'active', False)
    socketpair_context.active = True
    try:
        return original_socketpair(*args, **kwargs)
    finally:
        socketpair_context.active = previous


def temp_connect(database, *args, **kwargs):
    if str(database) != ':memory:' and Path(database).resolve() != db:
        return deny()
    return original_db_connect(database, *args, **kwargs)


socket.socketpair = guarded_socketpair
socket.socket.connect = guarded_socket_connect
socket.socket.connect_ex = guarded_socket_connect_ex
socket.create_connection = deny
sqlite3.connect = temp_connect
import httpx
from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider
from backend.app.ai.budget import BudgetLedger
DeepSeekConfig.from_environment = deny
DeepSeekProvider.__init__ = deny
BudgetLedger.__init__ = deny
httpx.HTTPTransport.handle_request = deny
httpx.AsyncHTTPTransport.handle_async_request = deny
os.environ['GAMEPLAY_VERSION'] = 'v5'; os.environ['AI_PROVIDER'] = 'mock'
fixtures = {}
for rooms in (1, 3):
    name = f'R{rooms}.json'; data = (cache / name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == index['files_sha256'][name]
    value = json.loads(data); assert value['synthetic_only'] is True
    fixtures[rooms] = value['draft']


class SyntheticGenerator:
    async def generate(self, *, theme, room_count, difficulty, api_key, draft_schema):
        assert room_count in (1, 3) and difficulty == 'hard'
        assert theme == '独立合成结构路线' and api_key == 'SYNTHETIC-STRUCTURE-BROWSER-ONLY'
        facts['synthetic_generation_calls'] += 1
        save_receipt()
        return copy.deepcopy(fixtures[room_count])


class NoCompanion:
    async def turn(self, *args, **kwargs):
        return deny()


from backend.app.main import create_v5_app
app = create_v5_app(db, generation_service=SyntheticGenerator(), companion_service=NoCompanion())


@app.middleware('http')
async def identify_owned_health(request, call_next):
    response = await call_next(request)
    if request.url.path == '/health':
        response.headers['X-Synthetic-QA-Instance'] = os.environ['STRUCTURE_BROWSER_SERVICE_MARKER']
    return response


save_receipt()
