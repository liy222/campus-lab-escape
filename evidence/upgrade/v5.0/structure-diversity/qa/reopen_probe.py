"""Fresh-process reload of an explicitly synthetic, owned TEMP database only."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import socket
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))


def deny(*args, **kwargs):
    raise RuntimeError('REOPEN_PROBE_FORBIDDEN_ACCESS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--session', required=True)
    args = parser.parse_args()
    dbpath = args.db.resolve(); dbpath.relative_to(Path(tempfile.gettempdir()).resolve())
    assert dbpath.is_file() and dbpath.name == 'game-v5.sqlite'
    original_connect = sqlite3.connect
    def connect(path, *values, **kwargs):
        assert Path(path).resolve() == dbpath
        return original_connect(path, *values, **kwargs)
    sqlite3.connect = connect
    socket.socket.connect = socket.socket.connect_ex = socket.create_connection = deny
    from backend.app.domain import blueprints, generation_content_v2, structure_variants
    blueprints.select_blueprint = generation_content_v2.select_blueprint = structure_variants.select_blueprint = deny
    from backend.app.storage.v5 import V5Database
    db = V5Database(dbpath)
    store = db.owned({'user_id': args.owner}, args.session)
    assert store is not None
    with db.transaction() as c:
        state = json.loads(c.execute('SELECT state_json FROM sessions WHERE session_id=?', (args.session,)).fetchone()[0])
    fields = set(store.rules.game_fields) - {'revision', 'generation'}
    encoded = json.dumps({key: state[key] for key in fields}, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
    print(json.dumps({'definition_hash': store.rules.compiled.definition_hash,
        'game_hash': hashlib.sha256(encoded).hexdigest(), 'new_process': True,
        'selection_or_LLM_calls': 0, 'owned_TEMP_only': True}))


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        print(json.dumps({'exit_code': 1, 'error_class': type(error).__name__, 'raw_details_suppressed': True}))
        raise SystemExit(1)
