"""Versioned Host structure selection and ID-independent chain signatures.

Signatures describe this catalog's single-chain topology, not playability.
Only the original compiler and its bounded real-action proof admit a level.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import secrets

from . import blueprints as v1

CATALOG_VERSION = '1.0.0'
VARIANTS = ('forward_v1', 'reverse_v1')
_UNSUPPORTED = 'STRUCTURE_SIGNATURE_UNSUPPORTED'


def _reverse_blueprint(blueprint: v1.Blueprint) -> v1.Blueprint:
    """Transform a trusted forward selection, preserving material identities."""
    ordered = tuple(reversed(blueprint.puzzles))
    counts = [sum(p.room_id == rid for p in blueprint.puzzles) for rid in blueprint.room_ids]
    rooms = [rid for rid, count in zip(blueprint.room_ids, counts) for _ in range(count)]
    puzzles = tuple(replace(p, room_id=rid,
                            prerequisite_ids=(ordered[index - 1].puzzle_id,) if index else ())
                    for index, (p, rid) in enumerate(zip(ordered, rooms)))
    by_id = {p.puzzle_id: p for p in puzzles}
    first_room = blueprint.room_ids[0]
    objects = []
    for obj in blueprint.objects:
        if obj.kind == 'puzzle':
            puzzle = by_id[obj.reference_id]
            obj = replace(obj, room_id=puzzle.room_id, locked_by=puzzle.prerequisite_ids)
        elif obj.kind == 'item':
            obj = replace(obj, room_id=first_room, locked_by=())
        elif obj.role in ('reading_positions', 'symbol_mapping'):
            obj = replace(obj, room_id=first_room, locked_by=(puzzles[0].puzzle_id,))
        elif obj.role == 'device_source':
            obj = replace(obj, room_id=first_room, locked_by=())
        elif obj.role == 'code_source' or obj.role.startswith(('extra_code_', 'extra_devices_')):
            owners = [p for p in puzzles if obj.reference_id in p.clue_ids]
            if len(owners) != 1:
                raise ValueError('BLUEPRINT_STRUCTURE_REFERENCE')
            obj = replace(obj, room_id=owners[0].room_id)
        else:
            raise ValueError('BLUEPRINT_STRUCTURE_ROLE')
        objects.append(obj)
    puzzle_objects = {obj.reference_id: obj for obj in objects if obj.kind == 'puzzle'}
    packed = []
    for rid in blueprint.room_ids:
        local = [obj for obj in objects if obj.room_id == rid and obj.kind != 'puzzle']
        local.extend(puzzle_objects[p.puzzle_id] for p in puzzles if p.room_id == rid)
        if len(local) > 8:
            raise ValueError('BLUEPRINT_OBJECT_LIMIT')
        packed.extend(replace(obj, slot=index) for index, obj in enumerate(local))
    return replace(blueprint, blueprint_id=blueprint.blueprint_id + '-sv1-reverse',
                   puzzles=puzzles, objects=tuple(packed))


def select_blueprint(room_count, difficulty, *, seed=None) -> v1.Blueprint:
    """Select once: F position/map at 0/1, R position/map at 2/3."""
    if type(room_count) is not int or room_count not in (1, 2, 3):
        raise ValueError('BLUEPRINT_ROOM_COUNT')
    if type(difficulty) is not str or difficulty not in ('easy', 'normal', 'hard'):
        raise ValueError('BLUEPRINT_DIFFICULTY')
    if seed is not None and (type(seed) is not int or seed < 0):
        raise ValueError('BLUEPRINT_SEED')
    index = secrets.randbelow(4) if seed is None else seed % 4
    blueprint = v1.select_blueprint(room_count, difficulty, seed=index % 2)
    return blueprint if index < 2 else _reverse_blueprint(blueprint)


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def canonical_structure(blueprint: v1.Blueprint) -> dict:
    """Normalize a unique dependency chain without using IDs as tie breakers.

    Object-list order, text, family and recipe values are excluded. Room order
    and actual slots are placement facts. Sorted material rows retain decoys
    and multiplicity. Unsupported graphs/references raise a signature error;
    they are not a claim that the compiler would reject or fail to solve them.
    """
    if not isinstance(blueprint, v1.Blueprint):
        raise ValueError(_UNSUPPORTED)
    puzzles = {p.puzzle_id: p for p in blueprint.puzzles}
    rooms = {rid: index for index, rid in enumerate(blueprint.room_ids)}
    if (not puzzles or len(puzzles) != len(blueprint.puzzles)
            or not rooms or len(rooms) != len(blueprint.room_ids)
            or len({o.object_id for o in blueprint.objects}) != len(blueprint.objects)):
        raise ValueError(_UNSUPPORTED)
    for p in puzzles.values():
        if (p.room_id not in rooms or len(set(p.prerequisite_ids)) != len(p.prerequisite_ids)
                or any(pid not in puzzles or pid == p.puzzle_id for pid in p.prerequisite_ids)):
            raise ValueError(_UNSUPPORTED)
    ranked = []
    rank = {}
    while len(ranked) < len(puzzles):
        ready = [p for p in puzzles.values() if p.puzzle_id not in rank
                 and all(pid in rank for pid in p.prerequisite_ids)]
        if len(ready) != 1:
            raise ValueError(_UNSUPPORTED)
        puzzle = ready[0]
        expected = (ranked[-1].puzzle_id,) if ranked else ()
        if puzzle.prerequisite_ids != expected:
            raise ValueError(_UNSUPPORTED)
        rank[puzzle.puzzle_id] = len(ranked)
        ranked.append(puzzle)

    def locks(obj):
        if (len(set(obj.locked_by)) != len(obj.locked_by)
                or any(pid not in rank for pid in obj.locked_by)):
            raise ValueError(_UNSUPPORTED)
        return sorted(rank[pid] for pid in obj.locked_by)

    references = {}
    for obj in blueprint.objects:
        key = (obj.kind, obj.reference_id)
        if (obj.kind not in ('puzzle', 'clue', 'item') or key in references
                or obj.room_id not in rooms):
            raise ValueError(_UNSUPPORTED)
        references[key] = obj
    if {obj.reference_id for obj in blueprint.objects if obj.kind == 'puzzle'} != set(puzzles):
        raise ValueError(_UNSUPPORTED)
    for p in ranked:
        if (len(set(p.clue_ids)) != len(p.clue_ids)
                or any(('clue', cid) not in references for cid in p.clue_ids)
                or (p.required_item_id is not None and ('item', p.required_item_id) not in references)
                or references[('puzzle', p.puzzle_id)].room_id != p.room_id):
            raise ValueError(_UNSUPPORTED)
    dependency_puzzles = []
    materials = []
    placement = []
    for obj in blueprint.objects:
        uses = []
        if obj.kind == 'clue':
            uses = [[rank[p.puzzle_id], index] for p in ranked
                    for index, cid in enumerate(p.clue_ids) if cid == obj.reference_id]
        elif obj.kind == 'item':
            uses = [rank[p.puzzle_id] for p in ranked if p.required_item_id == obj.reference_id]
        row = {'kind': obj.kind, 'uses': uses, 'locked_by': locks(obj)}
        if obj.kind != 'puzzle':
            materials.append(row)
        placed = {**row, 'room': rooms[obj.room_id], 'slot': obj.slot}
        if obj.kind == 'puzzle':
            placed['puzzle_rank'] = rank[obj.reference_id]
        placement.append(placed)
    for p in ranked:
        dependency_puzzles.append({'rank': rank[p.puzzle_id], 'mechanism': p.mechanism,
                                   'prerequisites': sorted(rank[pid] for pid in p.prerequisite_ids),
                                   'locked_by': locks(references[('puzzle', p.puzzle_id)])})
    return {'schema_version': CATALOG_VERSION,
            'dependency': {'puzzles': dependency_puzzles, 'materials': sorted(materials, key=_canonical)},
            'placement': {'room_count': len(rooms), 'objects': sorted(placement, key=_canonical)}}


def structure_signatures(blueprint: v1.Blueprint) -> dict[str, str]:
    """Return separate dependency/placement and combined structural SHA256s."""
    value = canonical_structure(blueprint)
    payloads = {key: {'schema_version': value['schema_version'], key: value[key]}
                for key in ('dependency', 'placement')}
    payloads['full'] = value
    return {key: hashlib.sha256(_canonical(payload).encode('utf-8')).hexdigest()
            for key, payload in payloads.items()}
