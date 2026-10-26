"""Strict model content2: AI names/facts and Host object descriptions.

Only a successfully validated v2 reply becomes a separate Host helper input
for the frozen v1 pure assembler. Invalid v2 never reaches a v1 fallback.
"""
from __future__ import annotations

import copy
import re
import unicodedata
from dataclasses import replace

from . import blueprints as v1
from .generated import strict_json

CONTENT_VERSION = '2.0.0'
NARRATIVE_GUARD_REVISION = '1'
Blueprint = v1.Blueprint
FAMILIES = v1.FAMILIES

_MATERIAL_TERMS = ('材料', '物品', '道具', '钥匙', '资料', '记录卡', '器材', '标本', '样本', '文件', '卡片')
_RETURN_ACTION = re.compile(r'归位|归还|交回|放回|挂回|返还')
_DIRECTIVE = re.compile(r'必须|务必|请|须|需|要求|一律|都要|(?:你|玩家)要')
_NEGATION_TAIL = re.compile(
    r'(?:无需|无须|不必|不用|不需要|不要求|不要|禁止|不得)'
    r'(?:再|先|立即|把|将|让|使|所有|全部|这些|其他|任何|的|你|玩家|都|也){0,8}$')
_NEGATION_BRIDGE = re.compile(r'(?:都|也|再|先|立即|重新|必须|要|须|被|的){0,6}')
_INVALIDATED_OLD_QUOTE = re.compile(
    r'(?:旧标语|旧规|往年)[^“”「」『"\r\n。;；]{0,16}[“「『"]'
    r'[^”」』"\r\n。;；]{0,120}[”」』"]'
    r'[,，]?(?:这条旧规|该旧规|这条规定|这项规定|该规定|该标语|标语)?'
    r'(?:现已|已经|已)?作废')


def _has_return_instruction(text: str, material_pattern: re.Pattern) -> bool:
    """Recognize a finite short-clause subset, not general narrative semantics."""
    compared = re.sub(r'\s+', '', unicodedata.normalize('NFKC', text))
    # Mask only the explicitly invalidated old quotation, never later demands.
    compared = _INVALIDATED_OLD_QUOTE.sub(' ', compared)
    for clause in re.split(r'[。！？!?;；\r\n,，]|但是|但|不过|然而', compared):
        materials = list(material_pattern.finditer(clause))
        previous_action_end = 0
        for action in _RETURN_ACTION.finditer(clause):
            if any(material.start() <= action.start() and action.end() <= material.end()
                   for material in materials):
                continue
            local_start = previous_action_end
            previous_action_end = action.end()
            prefix = clause[local_start:action.start()]
            directive = _DIRECTIVE.search(prefix)
            history = re.search(r'去年|往年|以前|当年|过去|曾经', prefix)
            current = re.search(r'现在|如今|目前', prefix)
            if (history and (not directive or history.start() < directive.start())
                    and not (current and current.start() > history.start())):
                continue
            for material in materials:
                if material.start() < local_start or material.start() <= action.start() < material.end():
                    continue
                start = min(material.start(), action.start())
                end = max(material.end(), action.end())
                if end - start > 80:
                    continue
                if _NEGATION_TAIL.search(prefix):
                    continue
                if (material.end() <= action.start()
                        and _NEGATION_TAIL.search(clause[local_start:material.start()])
                        and _NEGATION_BRIDGE.fullmatch(clause[material.end():action.start()])):
                    continue
                before = clause[max(local_start, start - 24):action.start()]
                after = clause[action.end():action.end() + 24]
                if (_DIRECTIVE.search(before)
                        or re.search(r'(?:离开|离楼|出门|出去)前', before)
                        or re.search(r'后?才能(?:离开|离楼|出门|出去)', after)):
                    return True
    return False


def _guard_narrative(blueprint: Blueprint, content: dict) -> None:
    """Check only schema-valid story/room atmosphere; names are target literals."""
    targets = set(_MATERIAL_TERMS)
    generic_material_pattern = re.compile('|'.join(re.escape(name) for name in _MATERIAL_TERMS))
    for obj in blueprint.objects:
        if obj.kind in ('item', 'clue'):
            name = content['objects'][obj.object_id]['name']
            compared_name = re.sub(r'\s+', '', unicodedata.normalize('NFKC', name))
            if compared_name and not _has_return_instruction(compared_name, generic_material_pattern):
                targets.add(compared_name)
    material_pattern = re.compile('|'.join(re.escape(name) for name in sorted(targets, key=lambda value: (-len(value), value))))
    fields = [content['story']] + [content['rooms'][rid]['description'] for rid in blueprint.room_ids]
    if any(_has_return_instruction(text, material_pattern) for text in fields):
        raise ValueError('UNSUPPORTED_NARRATIVE_OPERATION')


def _require_v2(blueprint: Blueprint) -> None:
    if not isinstance(blueprint, Blueprint) or blueprint.content_version != CONTENT_VERSION:
        raise ValueError('BLUEPRINT_CONTENT_VERSION')


def select_blueprint(room_count, difficulty, *, seed=None) -> Blueprint:
    """Select the original structure once; change only the content-contract tag."""
    return replace(v1.select_blueprint(room_count, difficulty, seed=seed),
                   content_version=CONTENT_VERSION)


def content_schema(blueprint: Blueprint) -> dict:
    """Fresh exact v2 schema; room and typed parameter constraints stay intact."""
    _require_v2(blueprint)
    schema = v1.content_schema(blueprint)
    schema['properties']['content_version'] = {'const': CONTENT_VERSION}
    schema['$defs']['object_name'] = {
        'type': 'object', 'properties': {'name': {'type': 'string', 'minLength': 1, 'maxLength': 40}},
        'required': ['name'], 'additionalProperties': False,
    }
    schema['properties']['objects']['properties'] = {
        obj.object_id: {'$ref': '#/$defs/object_name'} for obj in blueprint.objects}
    return schema


def request_manifest(blueprint: Blueprint) -> dict:
    """Retain the factual outline; request names rather than AI object prose."""
    _require_v2(blueprint)
    manifest = v1.request_manifest(blueprint)
    manifest['content_version'] = CONTENT_VERSION
    manifest['text_rule'] = ('物件槽位只填写name，物件说明由程序按真实角色和规则产生；'
                             'rooms的description只写氛围，不编造操作、完整答案或另一套规则。')
    return manifest


def _describe(blueprint: Blueprint, obj: v1.ObjectSlot, names: dict[str, str]) -> str:
    """Base facts only: no parameters, answers, witness or solver input."""
    if obj.kind == 'item':
        return '可拿入背包并用于对应装置；使用后仍保留在背包中。'
    if obj.kind == 'clue':
        if obj.role == 'code_source':
            return ('这份资料记录用于数字映射的符号源序。按资料展示的先后读取。'
                    if blueprint.family == 'mapping_v1' else
                    '这份资料记录数字源序。按资料展示的先后读取。')
        if obj.role == 'device_source':
            return ('这份资料记录用于设备映射的符号源序。按资料展示的先后读取。'
                    if blueprint.family == 'mapping_v1' else
                    '这份资料记录设备源序。按资料展示的先后读取。')
        descriptions = {
            'reading_positions': '这份资料记录从一开始计数的读取位置。',
            'symbol_mapping': '这份资料记录符号的对应关系。',
            'extra_code_a': '这是一份数字源序资料片段。组合次序在资料齐备后由装置说明。',
            'extra_code_b': '这是一份数字源序资料片段。组合次序在资料齐备后由装置说明。',
            'extra_devices_a': '这是一份设备源序资料片段。组合次序在资料齐备后由装置说明。',
            'extra_devices_b': '这是一份设备源序资料片段。组合次序在资料齐备后由装置说明。',
        }
        if obj.role not in descriptions:
            raise ValueError('BLUEPRINT_DESCRIPTION_ROLE')
        return descriptions[obj.role]
    if obj.kind == 'puzzle':
        selected = [p for p in blueprint.puzzles if p.puzzle_id == obj.reference_id]
        if len(selected) != 1:
            raise ValueError('BLUEPRINT_DESCRIPTION_REFERENCE')
        puzzle = selected[0]
        if puzzle.mechanism == 'item':
            items = [item for item in blueprint.objects
                     if item.kind == 'item' and item.reference_id == puzzle.required_item_id]
            if len(items) != 1:
                raise ValueError('BLUEPRINT_DESCRIPTION_REFERENCE')
            return '这是与背包中的「' + names[items[0].object_id] + '」配合使用的装置。'
        descriptions = {
            'code': '这是根据资料推理结果填写数字的装置。',
            'sequence': '这是填写四个设备操作顺序的装置。',
            'circuit': '这是需要接通入口与出口的线路装置。',
        }
        if puzzle.mechanism not in descriptions:
            raise ValueError('BLUEPRINT_DESCRIPTION_ROLE')
        return descriptions[puzzle.mechanism]
    raise ValueError('BLUEPRINT_DESCRIPTION_ROLE')


def assemble_draft(blueprint: Blueprint, raw_model_content) -> dict:
    """Strict v2 validation precedes declared construction of the original Draft.

    The helper is a new Host representation, not repaired model output. Raw
    reply and accepted values remain untouched; original compile/proof belongs
    to the caller and is never invoked here.
    """
    _require_v2(blueprint)
    try:
        content = strict_json(raw_model_content)
    except (TypeError, RecursionError) as error:
        raise ValueError('GENERATION_CONTENT_INVALID') from error
    if not v1._IntegerValidator(content_schema(blueprint)).is_valid(content):
        raise ValueError('GENERATION_CONTENT_INVALID')
    _guard_narrative(blueprint, content)
    names = {oid: value['name'] for oid, value in content['objects'].items()}
    helper = copy.deepcopy(content)
    helper['content_version'] = v1.CONTENT_VERSION
    helper['objects'] = {obj.object_id: {'name': names[obj.object_id],
                                       'description': _describe(blueprint, obj, names)}
                         for obj in blueprint.objects}
    return v1.assemble_draft(blueprint, helper)
