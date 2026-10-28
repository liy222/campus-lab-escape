"""Synthetic visual-UI fixture. Never a production generator or player store.

One room of the draft is always a plain code + item chain so an isolated browser
run can reach the real exit and capture the settlement screen; larger rooms keep
the circuit and sequence mechanisms for panel checks.
"""
import os
from pathlib import Path
import tempfile

db = Path(os.environ['SQLITE_PATH']).resolve()
if db.name != 'game-v5.sqlite' or not db.is_relative_to(Path(tempfile.gettempdir()).resolve()) or not db.parent.name.startswith('campus-visual-') or (db.exists() and os.environ.get('VISUAL_REUSE_TEMP') != '1'):
    raise RuntimeError('Fresh owned TEMP database required')
os.environ.update(GAMEPLAY_VERSION='v5', AI_PROVIDER='mock')

from backend.app.domain.generated import make_fixture
from backend.app.main import create_v5_app

ROOMS = [
    ('天文社旧活动室', '雨水顺着旧窗往下走，观测记录摊在桌边，社团的东西还没收走。'),
    ('封存观测资料室', '成排的资料箱与索引柜，许多年份的观测记录在这里等着被重新翻出来。'),
    ('观测设备间', '望远镜和配电设备都还在，屋顶的观测缝漏进一线夜雨。'),
]
RENAMES = {
    'key': ('黄铜钥匙', '一枚带皮革标签的黄铜钥匙。'),
    'note': ('观测记录册', '记录着社团当年的观测数据与读取方式。'),
    'terminal': ('资料终端', '天文社的旧资料终端，屏幕上留着待查的索引。'),
    'cabinet': ('封存资料柜', '存放观测记录的玻璃门资料柜。'),
    'circuit': ('配电箱', '为观测设备供电的配电箱，接点需要按线路接好。'),
    'panel': ('设备顺序盘', '刻着观测设备编号的黄铜顺序盘。'),
}


class SyntheticGenerator:
    async def generate(self, *, theme, room_count, difficulty, **kwargs):
        draft = make_fixture(room_count, difficulty)
        label = (theme or '校园').strip()[:10]
        draft['title'] = f'Synthetic · {label}'
        draft['story'] = f'Synthetic：{label}。雨夜的天文社旧活动室里，封存的观测记录等待查阅。'
        for index, room in enumerate(draft['rooms']):
            name, description = ROOMS[min(index, len(ROOMS) - 1)]
            room['name'] = name
            room['description'] = description
            for obj in room['objects']:
                if obj.get('puzzle_id') == 'puzzle_1':
                    obj['art_id'] = 'cabinet'
                if obj.get('puzzle_id') == 'puzzle_3':
                    obj['art_id'] = 'panel'
                art = obj.get('art_id')
                if art in RENAMES:
                    obj['name'], obj['description'] = RENAMES[art]
                if obj.get('object_id') == 'obj_source':
                    obj['name'], obj['description'] = '观测记录册', '记录着社团当年的观测数据。'
                if obj.get('object_id') == 'obj_order':
                    obj['name'], obj['description'] = '星图资料页', '记录着读取观测数据的方式。'

        for room in draft['rooms']:
            seen = {}
            for obj in room['objects']:
                name = obj['name']
                seen[name] = seen.get(name, 0) + 1
                if seen[name] > 1:
                    obj['name'] = f'{name}·{seen[name]}'
        return draft


app = create_v5_app(db, generation_service=SyntheticGenerator())


@app.middleware('http')
async def fixture_identity(request, call_next):
    response = await call_next(request)
    response.headers['X-QA-Synthetic-Visual'] = 'owned-temp-only'
    return response
