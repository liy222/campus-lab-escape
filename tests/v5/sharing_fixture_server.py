"""Owned-TEMP synthetic sharing UI server; never a player database or model."""
import copy
import json
import os
from pathlib import Path
import tempfile

reuse = os.environ.get('SHARING_REUSE_TEMP') == '1'
root = Path(os.environ['SHARING_FIXTURE_TEMP']).resolve()
db = Path(os.environ['SQLITE_PATH']).resolve()
if (not root.is_relative_to(Path(tempfile.gettempdir()).resolve())
        or not root.name.startswith('campus-sharing-browser-')
        or db != root / 'game-v5.sqlite' or (db.exists() and not reuse) or (reuse and not db.is_file())):
    raise RuntimeError('Fresh explicitly owned sharing TEMP required')
os.environ.update(SQLITE_PATH=str(db), GAMEPLAY_VERSION='v5', AI_PROVIDER='mock')
from backend.app.domain.generated import make_fixture, compile_level
from backend.app.main import create_v5_app

if not reuse:
    draft = make_fixture(1, 'easy')
    draft['title'] = 'Synthetic · 图书馆共享挑战'
    draft['story'] = 'Synthetic：雨后的校园图书馆留着一份待查阅的记录。'
    draft['rooms'][0]['name'] = '图书馆前厅'
    for obj in draft['rooms'][0]['objects']:
        if obj['kind'] == 'puzzle': obj['name'] = '门禁终端' if obj.get('puzzle_id') == draft['puzzles'][-1]['puzzle_id'] else '资料校验终端'
    compiled = compile_level(draft, 1, 'easy')
    with (root / 'synthetic-witness.json').open('x', encoding='utf-8') as stream:
        json.dump({'definition_hash': compiled.definition_hash, 'witness': compiled.witness}, stream)

class Generator:
    async def generate(self, *, room_count, difficulty, **kwargs):
        if reuse: raise RuntimeError('Read-only cover continuation cannot generate')
        if room_count != 1 or difficulty != 'easy': raise ValueError('One-room synthetic scope only')
        return copy.deepcopy(draft)

class Companion:
    async def turn(self, **kwargs):
        return {'answer': '可以先查看眼前物件。', 'clue_refs': [], 'count_hint': True,
                'status': 'completed', 'stop_reason': None,
                'usage': {'provider': 'deepseek', 'model': 'deepseek-flash', 'model_calls': 1,
                          'input_tokens': 1, 'output_tokens': 1, 'read_tool_calls': 0}}

app = create_v5_app(db, generation_service=Generator(), companion_service=Companion())
