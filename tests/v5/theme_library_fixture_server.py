"""Theme-specific names for synthetic visual coverage only.

Reuses the existing isolated V5 production app and SyntheticGenerator. It only
changes room/story/object display text; puzzles, parameters, dependencies,
answers, art IDs, and affordances remain those from the existing fixture.
"""
from __future__ import annotations

from tests.v5 import visual_ui_fixture_server as base
from backend.app.main import create_v5_app

THEMES = (
    (('图书馆', '档案', '阅览室', 'library', 'archive'), {
        'rooms': ('图书馆阅览室', '馆藏档案整理室', '校史资料室'),
        'descriptions': ('合成图书馆主题样例：借阅记录与书架索引。', '合成馆藏主题样例：待整理的资料与分类目录。', '合成校史主题样例：资料查询设备与旧档案。'),
        'story': '合成图书馆主题视觉夹具，仅用于场景素材显示检查。',
        'notes': ('借阅日志册', '封存馆藏资料'),
        'terminal': '档案检索终端',
    }),
    (('化学实验室', '化学实验', '化学', 'chemistry'), {
        'rooms': ('化学实验准备室', '实验记录整理室', '化学仪器控制室'),
        'descriptions': ('合成化学主题样例：实验准备台与安全记录。', '合成实验主题样例：资料和样品整理区域。', '合成化学主题样例：仪器与信息终端。'),
        'story': '合成化学实验室主题视觉夹具，仅用于场景素材显示检查。',
        'notes': ('实验记录册', '封存实验资料'),
        'terminal': '实验记录终端',
    }),
    (('计算机机房', '电脑室', '微机室', 'computer', 'computing'), {
        'rooms': ('计算机机房', '设备资料整理室', '信息控制室'),
        'descriptions': ('合成机房主题样例：计算机桌面与维护记录。', '合成机房主题样例：设备资料与登记索引。', '合成机房主题样例：设备控制终端。'),
        'story': '合成计算机机房主题视觉夹具，仅用于场景素材显示检查。',
        'notes': ('设备维护日志', '封存机房资料'),
        'terminal': '机房管理终端',
    }),
    (('校园广播室', '广播室', '广播站', '广播台', 'broadcast', 'radio'), {
        'rooms': ('校园广播室', '节目资料整理室', '广播控制室'),
        'descriptions': ('合成广播主题样例：播音台与节目记录。', '合成广播主题样例：节目资料与播出目录。', '合成广播主题样例：播控设备与操作终端。'),
        'story': '合成校园广播主题视觉夹具，仅用于场景素材显示检查。',
        'notes': ('节目播出日志', '封存节目资料'),
        'terminal': '播控管理终端',
    }),
)


def theme_for(text: str) -> dict[str, object]:
    lowered = (text or '').lower()
    choices = [(lowered.find(token.lower()), data) for tokens, data in THEMES for token in tokens if lowered.find(token.lower()) >= 0]
    if not choices:
        return THEMES[0][1]
    return min(choices, key=lambda item: item[0])[1]


class ThemeLibrarySyntheticGenerator(base.SyntheticGenerator):
    async def generate(self, *, theme, room_count, difficulty, **kwargs):
        draft = await super().generate(theme=theme, room_count=room_count, difficulty=difficulty, **kwargs)
        selected = theme_for(theme)
        draft['story'] = selected['story']
        for index, room in enumerate(draft['rooms']):
            room['name'] = selected['rooms'][min(index, 2)]
            room['description'] = selected['descriptions'][min(index, 2)]
            for obj in room['objects']:
                if obj.get('object_id') == 'obj_source' and obj.get('art_id') == 'note':
                    obj['name'] = selected['notes'][0]
                elif obj.get('object_id') == 'obj_order' and obj.get('art_id') == 'note':
                    obj['name'] = selected['notes'][1]
                elif obj.get('art_id') == 'terminal':
                    obj['name'] = selected['terminal']
        return draft


app = create_v5_app(base.db, generation_service=ThemeLibrarySyntheticGenerator())
