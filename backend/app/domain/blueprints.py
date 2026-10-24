"""Versioned Host-owned structures and strict AI content assembly.

The model supplies text and typed facts, never references, layout or solutions.
Assembly is a declared transformation, not admission: the existing compiler and
real-action proof remain the only authority for accepting the returned Draft.
This module has no provider, database, credential or fixture dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass
import copy
import secrets

from jsonschema import Draft202012Validator, validators

from .generated import strict_json

CONTENT_VERSION = '1.0.0'
FAMILIES = ('position_v1', 'mapping_v1')
DEVICES = ('device_a', 'device_b', 'device_c', 'device_d')
_IntegerValidator = validators.extend(
    Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER.redefine(
        'integer', lambda checker, value: type(value) is int),
)


@dataclass(frozen=True, slots=True)
class ObjectSlot:
    object_id: str
    room_id: str
    kind: str
    role: str
    reference_id: str
    art_id: str
    slot: int
    locked_by: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PuzzleSlot:
    puzzle_id: str
    room_id: str
    mechanism: str
    prerequisite_ids: tuple[str, ...]
    clue_ids: tuple[str, ...] = ()
    recipe: str = 'concat'
    required_item_id: str | None = None


@dataclass(frozen=True, slots=True)
class Blueprint:
    blueprint_id: str
    family: str
    room_count: int
    difficulty: str
    room_ids: tuple[str, ...]
    objects: tuple[ObjectSlot, ...]
    puzzles: tuple[PuzzleSlot, ...]
    content_version: str = CONTENT_VERSION


def select_blueprint(room_count, difficulty, *, seed=None) -> Blueprint:
    """Select once per generation; a nonnegative integer seed controls the family.

    Production selection uses fresh local randomness, without a model call.
    A caller must keep this exact immutable instance for messages and assembly.
    """
    if type(room_count) is not int or room_count not in (1, 2, 3):
        raise ValueError('BLUEPRINT_ROOM_COUNT')
    if type(difficulty) is not str or difficulty not in ('easy', 'normal', 'hard'):
        raise ValueError('BLUEPRINT_DIFFICULTY')
    if seed is not None and (type(seed) is not int or seed < 0):
        raise ValueError('BLUEPRINT_SEED')
    family = FAMILIES[secrets.randbelow(len(FAMILIES)) if seed is None else seed % len(FAMILIES)]
    count = min(6, room_count + {'easy': 1, 'normal': 2, 'hard': 3}[difficulty])
    room_ids = tuple(f'G{i + 1}' for i in range(room_count))
    # Extra puzzles go in later rooms, leaving space for the initial materials.
    quotient, remainder = divmod(count, room_count)
    puzzle_rooms = tuple(rid for i, rid in enumerate(room_ids)
                         for _ in range(quotient + (i >= room_count - remainder)))
    mechanisms = ('code', 'sequence', 'circuit', 'code', 'sequence')[:count - 1] + ('item',)
    objects = []
    puzzles = []

    def add(rid, oid, kind, role, reference, art, locked_by=()):
        slot = sum(obj.room_id == rid for obj in objects)
        if slot >= 8:
            raise ValueError('BLUEPRINT_OBJECT_LIMIT')
        objects.append(ObjectSlot(oid, rid, kind, role, reference, art, slot, locked_by))

    add('G1', 'obj_key', 'item', 'reusable_key', 'shared_key', 'key')
    add('G1', 'obj_code_source', 'clue', 'code_source', 'fact_code', 'note')
    add('G1', 'obj_relation', 'clue', 'reading_positions' if family == 'position_v1' else 'symbol_mapping',
        'fact_relation', 'note')
    if count >= 3:
        add('G1', 'obj_device_source', 'clue', 'device_source', 'fact_devices', 'note')
    for index, (rid, mechanism) in enumerate(zip(puzzle_rooms, mechanisms)):
        pid = f'puzzle_{index + 1}'
        previous = (f'puzzle_{index}',) if index else ()
        clues = ()
        recipe = 'concat'
        if mechanism in ('code', 'sequence'):
            if index < 2:
                clues = ('fact_code' if mechanism == 'code' else 'fact_devices', 'fact_relation')
                recipe = 'index' if family == 'position_v1' else 'symbol_map'
            else:
                prefix = 'extra_code' if mechanism == 'code' else 'extra_devices'
                clues = (f'fact_{prefix}_a', f'fact_{prefix}_b')
                for suffix, cid in zip(('a', 'b'), clues):
                    add(rid, f'obj_{prefix}_{suffix}', 'clue', f'{prefix}_{suffix}', cid, 'note')
        puzzles.append(PuzzleSlot(pid, rid, mechanism, previous, clues, recipe,
                                  'shared_key' if mechanism == 'item' else None))
        add(rid, f'obj_puzzle_{index + 1}', 'puzzle', mechanism, pid,
            'circuit' if mechanism == 'circuit' else 'terminal', previous)
    return Blueprint(f'{family}-r{room_count}-{difficulty}', family, room_count, difficulty,
                     room_ids, tuple(objects), tuple(puzzles))


def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False}


def _permutation(values):
    return {'type': 'array', 'items': {'enum': list(values)},
            'minItems': len(values), 'maxItems': len(values), 'uniqueItems': True}


def _digits():
    return {'type': 'array', 'items': {'type': 'string', 'pattern': '^[0-9]$', 'minLength': 1, 'maxLength': 1},
            'minItems': 4, 'maxItems': 4}


def content_schema(blueprint: Blueprint) -> dict:
    """Return a fresh exact-slot schema for only the already selected structure."""
    count = len(blueprint.puzzles)
    text = _object({'name': {'type': 'string', 'minLength': 1, 'maxLength': 40},
                    'description': {'type': 'string', 'minLength': 1, 'maxLength': 240}})
    if blueprint.family == 'position_v1':
        parameters = {'digits': _digits(), 'positions': _permutation((1, 2, 3, 4))}
        parameters['positions']['items']['type'] = 'integer'
        if count >= 3:
            parameters['devices'] = _permutation(DEVICES)
    elif blueprint.family == 'mapping_v1':
        parameters = {'code_symbols': _permutation(('A', 'B', 'C', 'D')),
                      'digit_map': _object({key: {'type': 'string', 'pattern': '^[0-9]$',
                                                 'minLength': 1, 'maxLength': 1} for key in 'ABCD'})}
        if count >= 3:
            parameters['sequence_symbols'] = _permutation(('E', 'F', 'G', 'H'))
            parameters['device_map'] = _object({key: {'enum': list(DEVICES)} for key in 'EFGH'})
            # Four unique values in a fixed four-key mapping: pairwise inequality.
            parameters['device_map']['allOf'] = [
                {'not': {'properties': {left: {'const': device}, right: {'const': device}}}}
                for i, left in enumerate('EFGH') for right in 'EFGH'[i + 1:] for device in DEVICES]
    else:
        raise ValueError('BLUEPRINT_FAMILY')
    if count >= 5:
        parameters['extra_digits'] = _digits()
    if count >= 6:
        parameters['extra_devices'] = _permutation(DEVICES)
    schema = _object({
        'content_version': {'const': CONTENT_VERSION},
        'blueprint_id': {'const': blueprint.blueprint_id},
        'title': {'type': 'string', 'minLength': 1, 'maxLength': 40},
        'story': {'type': 'string', 'minLength': 1, 'maxLength': 240},
        'rooms': _object({rid: {'$ref': '#/$defs/slot_text'} for rid in blueprint.room_ids}),
        'objects': _object({obj.object_id: {'$ref': '#/$defs/slot_text'} for obj in blueprint.objects}),
        'parameters': _object(parameters),
    })
    schema['$defs'] = {'slot_text': text}
    # A caller may annotate its private schema without changing later requests.
    return copy.deepcopy(schema)


def request_manifest(blueprint: Blueprint) -> dict:
    """Public-to-generator outline, containing no answers or execution authority."""
    clue_objects = {obj.reference_id: obj.object_id for obj in blueprint.objects if obj.kind == 'clue'}
    item_objects = {obj.reference_id: obj.object_id for obj in blueprint.objects if obj.kind == 'item'}
    return {
        'content_version': CONTENT_VERSION, 'blueprint_id': blueprint.blueprint_id,
        'family': blueprint.family, 'room_count': blueprint.room_count,
        'difficulty': blueprint.difficulty, 'puzzle_count': len(blueprint.puzzles),
        'room_slots': list(blueprint.room_ids),
        'object_slots': {obj.object_id: {'room_slot': obj.room_id, 'kind': obj.kind, 'role': obj.role}
                         for obj in blueprint.objects},
        'puzzles': [{'object_slot': next(obj.object_id for obj in blueprint.objects
                                        if obj.kind == 'puzzle' and obj.reference_id == puzzle.puzzle_id),
                     'room_slot': puzzle.room_id, 'mechanism': puzzle.mechanism,
                     'recipe': puzzle.recipe if puzzle.clue_ids else None,
                     'material_slots': [clue_objects[cid] for cid in puzzle.clue_ids],
                     **({'item_use': {'item_object_slot': item_objects[puzzle.required_item_id],
                                      'tool': 'use_item', 'consumed': False}}
                        if puzzle.mechanism == 'item' else {})}
                    for puzzle in blueprint.puzzles],
        'parameter_meaning': {
            'position_v1': 'digits是四个单数字，devices是四个设备的排列；共享positions从一开始读取各自源序。',
            'mapping_v1': 'code_symbols是A到D的排列，digit_map给各符号一个数字；sequence_symbols是E到H的排列，device_map为其提供互不相同的设备。',
        }[blueprint.family],
        'extra_parameter_meaning': '若schema要求extra_digits或extra_devices，它们是独立谜题的四项源序，程序按前两项和后两项分为两份拼接资料。',
        'text_rule': '只为exact槽位写主题名称与短叙述，不写完整密码、设备答案或另一套操作规则。',
    }


def assemble_draft(blueprint: Blueprint, raw_model_content) -> dict:
    """Strictly validate once, then construct the original Draft data format.

    No value is corrected, dropped or substituted. Exceptions abort generation;
    callers still run the original compile/proof before storing a playable level.
    """
    try:
        content = strict_json(raw_model_content)
    except (TypeError, RecursionError) as error:
        raise ValueError('GENERATION_CONTENT_INVALID') from error
    if not _IntegerValidator(content_schema(blueprint)).is_valid(content):
        raise ValueError('GENERATION_CONTENT_INVALID')
    params = content['parameters']
    has_sequence = len(blueprint.puzzles) >= 3
    if blueprint.family == 'position_v1':
        clues = [{'clue_id': 'fact_code', 'tokens': list(params['digits'])},
                 {'clue_id': 'fact_relation', 'indices': list(params['positions'])}]
        if has_sequence:
            clues.append({'clue_id': 'fact_devices', 'tokens': list(params['devices'])})
    else:
        mapping = dict(params['digit_map'])
        if has_sequence:
            mapping.update(params['device_map'])
        clues = [{'clue_id': 'fact_code', 'tokens': list(params['code_symbols'])},
                 {'clue_id': 'fact_relation', 'symbol_map': mapping}]
        if has_sequence:
            clues.append({'clue_id': 'fact_devices', 'tokens': list(params['sequence_symbols'])})
    for name, key in (('extra_code', 'extra_digits'), ('extra_devices', 'extra_devices')):
        if key in params:
            clues.extend({'clue_id': f'fact_{name}_{suffix}', 'tokens': list(params[key][start:start + 2])}
                         for suffix, start in (('a', 0), ('b', 2)))
    rooms = []
    for index, rid in enumerate(blueprint.room_ids):
        objects = []
        for obj in blueprint.objects:
            if obj.room_id == rid:
                value = {'object_id': obj.object_id, **content['objects'][obj.object_id],
                         'slot': obj.slot, 'art_id': obj.art_id, 'kind': obj.kind,
                         'locked_by': list(obj.locked_by)}
                value[{'clue': 'clue_id', 'item': 'item_id', 'puzzle': 'puzzle_id'}[obj.kind]] = obj.reference_id
                objects.append(value)
        rooms.append({'room_id': rid, **content['rooms'][rid],
                      'background_id': ('neutral_lab', 'neutral_archive', 'neutral_control')[index],
                      'objects': objects})
    puzzles = [{'puzzle_id': p.puzzle_id, 'room_id': p.room_id, 'mechanism': p.mechanism,
                'prerequisite_ids': list(p.prerequisite_ids), 'clue_ids': list(p.clue_ids),
                'recipe': p.recipe, 'required_item_id': p.required_item_id} for p in blueprint.puzzles]
    return {'title': content['title'], 'story': content['story'], 'rooms': rooms,
            'clues': clues, 'puzzles': puzzles}
