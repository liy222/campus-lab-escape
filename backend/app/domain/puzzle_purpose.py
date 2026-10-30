"""Host-owned purpose for newly generated puzzle names and descriptions.

This module never changes the Blueprint or a saved definition. Its finite
name policy is admission for new content, not general language understanding.
"""
from __future__ import annotations

import re
import unicodedata

from .blueprints import Blueprint

PURPOSE_POLICY_REVISION = '1'
_UNSUPPORTED = 'BLUEPRINT_PURPOSE_UNSUPPORTED'
_NAME_INVALID = 'GENERATION_PUZZLE_NAME_INVALID'
_HEADS = {
    'terminal': ('终端', '控制台', '控制器', '控制面板', '验证面板', '操作面板', '读卡器'),
    'circuit': ('供电箱', '配电箱', '电源箱', '线路箱', '电路箱', '控制箱'),
}
_ACCESS_WORDS = ('门禁', '门锁', '通行', '出入口')
_ACCESS = re.compile('|'.join(re.escape(word) for word in _ACCESS_WORDS))
_CONTAINER = r'(?:储物柜|器材柜|档案柜|文件柜|橱柜|柜子|抽屉|保险箱|储物箱|柜)'
_CONTAINER_LOCATION = re.compile(
    _CONTAINER + r'(?:的)?(?:门|锁)?(?:旁边|旁|侧面|侧|边上|边|附近|上方|下方)(?:的)?')
_CONTAINER_IDENTITY = re.compile(
    _CONTAINER + r'(?:的)?(?:锁|门|密码|控制|终端|开关|验证|解锁)|' + _CONTAINER + r'$')


def puzzle_effects(blueprint: Blueprint) -> dict[str, dict]:
    """Derive each room's unique final task from real prerequisite ancestry.

    A passage task must imply completion of every other task in that room.
    Tuple order and literal IDs do not establish that implication. Only real
    same-room material releases are listed; no new container action is made.
    """
    puzzles = {p.puzzle_id: p for p in blueprint.puzzles}
    objects = {obj.reference_id: obj for obj in blueprint.objects if obj.kind == 'puzzle'}
    rooms = blueprint.room_ids
    if (not rooms or len(set(rooms)) != len(rooms) or not puzzles
            or len(puzzles) != len(blueprint.puzzles)
            or len(objects) != sum(obj.kind == 'puzzle' for obj in blueprint.objects)
            or set(objects) != set(puzzles)):
        raise ValueError(_UNSUPPORTED)
    ancestors = {}

    def predecessors(pid, visiting):
        if pid not in puzzles or pid in visiting:
            raise ValueError(_UNSUPPORTED)
        if pid not in ancestors:
            result = set()
            for parent in puzzles[pid].prerequisite_ids:
                result.add(parent)
                result.update(predecessors(parent, visiting | {pid}))
            ancestors[pid] = result
        return ancestors[pid]

    for p in puzzles.values():
        obj = objects[p.puzzle_id]
        if (p.room_id not in rooms or obj.room_id != p.room_id
                or obj.art_id != ('circuit' if p.mechanism == 'circuit' else 'terminal')
                or any(pid not in puzzles for pid in obj.locked_by)):
            raise ValueError(_UNSUPPORTED)
        predecessors(p.puzzle_id, set())
    final = {}
    for index, rid in enumerate(rooms):
        local = {p.puzzle_id for p in puzzles.values() if p.room_id == rid}
        candidates = [pid for pid in local if local - {pid} <= ancestors[pid]]
        if len(candidates) != 1:
            raise ValueError(_UNSUPPORTED)
        final[candidates[0]] = rooms[index + 1] if index + 1 < len(rooms) else 'EXIT'
    effects = {}
    for p in blueprint.puzzles:
        obj = objects[p.puzzle_id]
        effect = {
            'purpose': 'passage_control' if p.puzzle_id in final else 'puzzle_control',
            'carrier': obj.art_id,
            'unlocks_material_slots': [material.object_id for material in blueprint.objects
                                       if material.kind in ('item', 'clue')
                                       and material.room_id == p.room_id
                                       and p.puzzle_id in material.locked_by
                                       and set(material.locked_by) - {p.puzzle_id} <= ancestors[p.puzzle_id]],
        }
        if p.puzzle_id in final:
            effect['destination_room_slot'] = final[p.puzzle_id]
        effects[obj.object_id] = effect
    return effects


def name_requirements(effect: dict) -> dict:
    """Fresh model-facing requirements from the exact finite admission vocabulary."""
    suffixes = list(_HEADS[effect['carrier']])
    access_required = effect['purpose'] == 'passage_control'
    prefix = _ACCESS_WORDS[0] if access_required else '校内'
    return {
        'allowed_suffixes': suffixes,
        'must_end_with': True,
        'require_access_word': access_required,
        'allowed_access_words': list(_ACCESS_WORDS),
        'examples': [prefix + suffix for suffix in suffixes[:2]],
    }


def _invalid_name(reason: str) -> ValueError:
    error = ValueError(_NAME_INVALID)
    error.generation_name_reason = reason
    return error


def validate_puzzle_names(blueprint: Blueprint, names: dict[str, str], effects: dict[str, dict]) -> None:
    """Reject incompatible new names; accepted original names remain untouched.

    A clear container location is distinct from claiming a cabinet lock as the
    device. Required noun heads keep the stated carrier explicit. This finite
    vocabulary does not claim to resolve arbitrary prose or every compound.
    """
    for obj in blueprint.objects:
        if obj.kind != 'puzzle':
            continue
        effect = effects[obj.object_id]
        compared = re.sub(r'\s+', '', unicodedata.normalize('NFKC', names[obj.object_id]))
        identity = _CONTAINER_LOCATION.sub('', compared)
        if _CONTAINER_IDENTITY.search(identity):
            raise _invalid_name('name_container')
        if not identity.endswith(_HEADS[effect['carrier']]):
            raise _invalid_name('name_suffix')
        if effect['purpose'] == 'passage_control' and not _ACCESS.search(identity):
            raise _invalid_name('name_access')


def describe_effect(effect: dict, room_names: dict[str, str]) -> str:
    """Describe known rule effects without parameters, answers or clue IDs."""
    if effect['purpose'] == 'passage_control':
        target = effect['destination_room_slot']
        destination = '出口' if target == 'EXIT' else '「' + room_names[target] + '」'
        return '此装置控制通往' + destination + '的通道；完成本房前置任务并通过此装置后，通道开放。'
    if effect['unlocks_material_slots']:
        return '完成后可发现本房后续资料或物品；本装置不直接开放通道。'
    return '用于完成本房前置任务；通行由本房门禁控制。'
