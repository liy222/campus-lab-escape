"""Synthetic display names for the v5 theme variation browser check only.

Reuses the isolated V5 production app and existing SyntheticGenerator. This
wrapper changes visible story, room, note, and terminal labels only; puzzle
rules, dependencies, answers, actions, and object art IDs stay untouched.
"""
from __future__ import annotations

from tests.v5 import visual_ui_fixture_server as base
from backend.app.main import create_v5_app

THEMES = (
    (('天文社', '天文', '星图', 'astronomy'), {
        'room': ('天文社活动室', '封存观测资料室', '观测设备间'),
        'story': '合成天文主题样例，仅用于主题变体画面检查。',
        'notes': ('星图观测记录本', '封存观测资料'),
        'terminal': '观测资料终端',
    }),
    (('图书馆', '档案', '阅览室', 'library', 'archive'), {
        'room': ('图书馆阅览室', '馆藏档案整理室', '校史资料室'),
        'story': '合成图书馆主题样例，仅用于主题变体画面检查。',
        'notes': ('借阅日志册', '封存馆藏资料'),
        'terminal': '档案检索终端',
    }),
    (('化学实验室', '化学实验', 'chemistry'), {
        'room': ('化学实验准备室', '实验记录整理室', '化学仪器控制室'),
        'story': '合成化学主题样例，仅用于主题变体画面检查。',
        'notes': ('实验记录册', '封存实验资料'),
        'terminal': '实验记录终端',
    }),
    (('计算机机房', '电脑室', '微机室', 'computer', 'computing'), {
        'room': ('计算机机房', '设备资料整理室', '信息控制室'),
        'story': '合成计算机主题样例，仅用于主题变体画面检查。',
        'notes': ('设备维护日志', '封存机房资料'),
        'terminal': '机房管理终端',
    }),
    (('校园广播室', '广播站', '广播台', '广播室', 'broadcast', 'radio'), {
        'room': ('校园广播室', '节目资料整理室', '广播控制室'),
        'story': '合成广播主题样例，仅用于主题变体画面检查。',
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


class ThemeVariationSyntheticGenerator(base.SyntheticGenerator):
    async def generate(self, *, theme, room_count, difficulty, **kwargs):
        draft = await super().generate(theme=theme, room_count=room_count, difficulty=difficulty, **kwargs)
        selected = theme_for(theme)
        draft['story'] = selected['story']
        for index, room in enumerate(draft['rooms']):
            room['name'] = selected['room'][min(index, 2)]
            room['description'] = f"{selected['story']} 房间 {index + 1}。"
            for obj in room['objects']:
                if obj.get('object_id') == 'obj_source' and obj.get('art_id') == 'note':
                    obj['name'] = selected['notes'][0]
                elif obj.get('object_id') == 'obj_order' and obj.get('art_id') == 'note':
                    obj['name'] = selected['notes'][1]
                elif obj.get('art_id') == 'terminal':
                    obj['name'] = selected['terminal']
        return draft


app = create_v5_app(base.db, generation_service=ThemeVariationSyntheticGenerator())
