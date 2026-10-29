"""Finite synthetic Owner checks; no provider, network or database constructor."""
from __future__ import annotations

import asyncio
import copy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from backend.app.domain import generation_content_v2 as content
from backend.app.domain.puzzle_purpose import puzzle_effects, validate_puzzle_names
from backend.app.domain.generated import GeneratedRules, compile_level
from backend.app.ai.v5 import GenerationService, ServiceError

OUT = Path(__file__).with_name('backend-development-result.json')


def synthetic(bp):
    params = ({'digits': list('9317'), 'positions': [2, 4, 1, 3]} if bp.family == 'position_v1'
              else {'code_symbols': list('BDAC'), 'digit_map': dict(zip('ABCD', '9317'))})
    if len(bp.puzzles) >= 3:
        devices = ['device_d', 'device_b', 'device_a', 'device_c']
        if bp.family == 'position_v1':
            params['devices'] = devices
        else:
            params.update(sequence_symbols=list('FHEG'), device_map=dict(zip('EFGH', devices)))
    if len(bp.puzzles) >= 5:
        params['extra_digits'] = list('2648')
    if len(bp.puzzles) >= 6:
        params['extra_devices'] = ['device_b', 'device_c', 'device_d', 'device_a']
    effects = puzzle_effects(bp)
    value = {'content_version': '2.0.0', 'blueprint_id': bp.blueprint_id, 'title': '合成通行资料室',
             'story': '细雨映着窗边安静的书架。',
             'rooms': {rid: {'name': '资料区' + str(i + 1), 'description': '灯光落在桌面与墙上。'}
                       for i, rid in enumerate(bp.room_ids)},
             'objects': {obj.object_id: {'name': '铜钥匙' if obj.kind == 'item' else '资料页'} for obj in bp.objects},
             'parameters': params}
    for obj in bp.objects:
        if obj.kind == 'puzzle':
            effect = effects[obj.object_id]
            value['objects'][obj.object_id]['name'] = (
                ('门禁' if effect['purpose'] == 'passage_control' else '校验') +
                ('供电箱' if effect['carrier'] == 'circuit' else '终端'))
    return value


def run():
    checks = []
    result = {'kind': 'Owner finite synthetic development, not independent QA', 'checks': checks,
              'real_provider_calls': 0, 'database_constructors': 0, 'first_failure': None}
    start = time.perf_counter()
    try:
        gate_mechanisms = set()
        metadata_count = 0
        for rooms in (1, 2, 3):
            for difficulty in ('easy', 'normal', 'hard'):
                for seed in range(4):
                    bp = content.select_blueprint(rooms, difficulty, seed=seed)
                    effects = puzzle_effects(bp)
                    by_pid = {p.puzzle_id: p for p in bp.puzzles}
                    assert sum(e['purpose'] == 'passage_control' for e in effects.values()) == rooms
                    for index, rid in enumerate(bp.room_ids):
                        gates = [obj for obj in bp.objects if obj.kind == 'puzzle' and obj.room_id == rid
                                 and effects[obj.object_id]['purpose'] == 'passage_control']
                        assert len(gates) == 1
                        gate = gates[0]
                        gate_mechanisms.add(by_pid[gate.reference_id].mechanism)
                        assert effects[gate.object_id]['destination_room_slot'] == (
                            bp.room_ids[index + 1] if index + 1 < rooms else 'EXIT')
                    assert puzzle_effects(replace(bp, objects=tuple(reversed(bp.objects)),
                                                  puzzles=tuple(reversed(bp.puzzles)))) == effects
                    manifest = content.request_manifest(bp)
                    assert all(row['effect'] == effects[row['object_slot']] for row in manifest['puzzles'])
                    value = synthetic(bp)
                    names = {key: row['name'] for key, row in value['objects'].items()}
                    validate_puzzle_names(bp, names, effects)
                    metadata_count += 1
        assert gate_mechanisms == {'code', 'sequence', 'circuit', 'item'}
        checks.append({'metadata_variants': metadata_count, 'gate_mechanisms': sorted(gate_mechanisms),
                       'proof_calls': 0, 'tuple_order_invariant': True})
        bp = content.select_blueprint(3, 'hard', seed=3)
        effects = puzzle_effects(bp)
        value = synthetic(bp)
        names = {key: row['name'] for key, row in value['objects'].items()}
        terminal_gate = next(oid for oid, effect in effects.items()
                             if effect['purpose'] == 'passage_control' and effect['carrier'] == 'terminal')
        name_cases = []
        for name, accepted in [('柜旁门禁终端', True), ('储物柜门旁的门禁终端', True),
                               ('前厅门锁控制台', True), ('前厅储物柜锁', False),
                               ('储物柜锁控制台', False), ('储物柜门禁终端', False),
                               ('校验终端', False), ('门禁供电箱', False)]:
            candidate = {**names, terminal_gate: name}
            try:
                validate_puzzle_names(bp, candidate, effects)
                actual = True
            except ValueError as error:
                assert str(error) == 'GENERATION_PUZZLE_NAME_INVALID'
                actual = False
            assert actual == accepted, name
            name_cases.append({'name': name, 'accepted': actual})
        ordinary = next(oid for oid, effect in effects.items()
                        if effect['purpose'] == 'puzzle_control' and effect['carrier'] == 'terminal')
        try:
            validate_puzzle_names(bp, {**names, ordinary: '资料柜密码终端'}, effects)
            raise AssertionError('fake container accepted')
        except ValueError as error:
            assert str(error) == 'GENERATION_PUZZLE_NAME_INVALID'
        checks.append({'finite_name_cases': name_cases, 'ordinary_fake_container_rejected': True})

        # Consistent renaming: the dependency edges and actual references win.
        ids = set(bp.room_ids) | {p.puzzle_id for p in bp.puzzles}
        ids.update(obj.object_id for obj in bp.objects)
        ids.update(obj.reference_id for obj in bp.objects)
        renamed = {old: 'renamed_' + str(i) for i, old in enumerate(sorted(ids))}
        custom = replace(bp, room_ids=tuple(renamed[rid] for rid in bp.room_ids),
                         objects=tuple(replace(obj, object_id=renamed[obj.object_id], room_id=renamed[obj.room_id],
                                               reference_id=renamed[obj.reference_id],
                                               locked_by=tuple(renamed[pid] for pid in obj.locked_by))
                                       for obj in reversed(bp.objects)),
                         puzzles=tuple(replace(p, puzzle_id=renamed[p.puzzle_id], room_id=renamed[p.room_id],
                                               prerequisite_ids=tuple(renamed[pid] for pid in p.prerequisite_ids),
                                               clue_ids=tuple(renamed[cid] for cid in p.clue_ids),
                                               required_item_id=renamed[p.required_item_id] if p.required_item_id else None)
                                       for p in reversed(bp.puzzles)))
        custom_effects = puzzle_effects(custom)
        for oid, effect in effects.items():
            expected = copy.deepcopy(effect)
            expected['unlocks_material_slots'] = [renamed[key] for key in effect['unlocks_material_slots']]
            if 'destination_room_slot' in effect:
                expected['destination_room_slot'] = renamed.get(effect['destination_room_slot'], 'EXIT')
            assert custom_effects[renamed[oid]] == expected
        checks.append({'actual_reference_rename': True})
        for malformed in ('{"title":"a","title":"b"}', json.dumps({**value, 'extra': True})):
            with patch.object(content, 'validate_puzzle_names') as guard:
                try:
                    content.assemble_draft(bp, malformed)
                    raise AssertionError('malformed accepted')
                except ValueError:
                    pass
                guard.assert_not_called()
        bad = copy.deepcopy(value)
        bad['objects'][terminal_gate]['name'] = '前厅储物柜锁'
        before = copy.deepcopy(bad)
        with patch.object(content.v1, 'assemble_draft') as helper:
            try:
                content.assemble_draft(bp, bad)
                raise AssertionError('bad name accepted')
            except ValueError as error:
                assert str(error) == 'GENERATION_PUZZLE_NAME_INVALID'
                assert error.generation_diagnostic == 'narrative'
            helper.assert_not_called()
        assert bad == before
        checks.append({'strict_schema_before_name_guard': True, 'bad_raw_unchanged': True,
                       'bad_name_helper_calls': 0})

        representative = []
        for seed in (0, 3):
            chosen = content.select_blueprint(3, 'hard', seed=seed)
            raw = synthetic(chosen)
            compiled = compile_level(content.assemble_draft(chosen, raw), 3, 'hard')
            rules = GeneratedRules(compiled)
            state = rules.initial_state()
            chosen_effects = puzzle_effects(chosen)
            gate_pids = {obj.reference_id: chosen_effects[obj.object_id] for obj in chosen.objects
                         if obj.kind == 'puzzle' and chosen_effects[obj.object_id]['purpose'] == 'passage_control'}
            transitions = []
            for action in compiled.witness:
                pid = action['arguments'].get('target_id')
                if pid in gate_pids and action['tool'] in ('use_item', 'submit_code', 'submit_sequence', 'submit_circuit'):
                    target = gate_pids[pid]['destination_room_slot']
                    assert next(e for e in rules.exits(state) if e['destination_id'] == target)['unlocked'] is False
                    state, _ = rules.apply_action(state, action['tool'], action['arguments'])
                    assert next(e for e in rules.exits(state) if e['destination_id'] == target)['unlocked'] is True
                    transitions.append({'target': target, 'before': False, 'after': True})
                else:
                    state, _ = rules.apply_action(state, action['tool'], action['arguments'])
            assert state.status == 'won' and state.room_id == 'EXIT' and len(transitions) == 3
            representative.append({'seed': seed, 'witness_steps': len(compiled.witness), 'status': 'won',
                                   'passage_transitions': transitions})
        checks.append({'representative_original_proof_replay': representative, 'limits': 'unchanged 25000/5s'})

        # Execute the actual old loader on an in-memory row/cache, no DB __init__.
        from backend.app.storage.v5 import V5Database
        old_draft = copy.deepcopy(compiled.private_dump()['draft'])
        for room in old_draft['rooms']:
            for obj in room['objects']:
                if obj['kind'] == 'puzzle':
                    obj['name'] = '旧储物柜锁'
        old = compile_level(old_draft, 3, 'hard', prove=False)
        row = {'definition_json': json.dumps(old.private_dump(), ensure_ascii=False),
               'definition_hash': old.definition_hash, 'definition_version': '1.0.0',
               'metadata_json': json.dumps({'definition_hash': old.definition_hash, 'room_count': 3, 'difficulty': 'hard'})}
        cache_only = object.__new__(V5Database)
        cache_only._compiled_cache = {}
        with patch.object(content, 'validate_puzzle_names', side_effect=AssertionError('old definition guarded')):
            restored = cache_only.load_compiled(row)
        assert restored.definition_hash == old.definition_hash and restored.private_dump() == old.private_dump()
        checks.append({'actual_old_definition_loader': 'unchanged with legacy cabinet names', 'database_constructor_calls': 0})

        class FakeProvider:
            def __init__(self): self.calls = 0
            async def complete(self, messages, tools, limits, **kwargs):
                self.calls += 1
                assert json.loads(messages[1]['content'])['blueprint']['puzzles'][0]['effect']
                return SimpleNamespace(content=json.dumps(bad), tool_calls=(), usage={'prompt_tokens': 1, 'completion_tokens': 1})

        provider = FakeProvider()
        with patch.object(content, 'select_blueprint', return_value=bp) as select:
            try:
                asyncio.run(GenerationService(lambda _: provider).generate(
                    theme='合成资料室', room_count=3, difficulty='hard', api_key='offline-synthetic-only', draft_schema={}))
                raise AssertionError('production service accepted fake cabinet')
            except ServiceError as error:
                assert error.code == 'MODEL_INVALID_OUTPUT' and error.generation_diagnostic == 'narrative'
            select.assert_called_once()
        assert provider.calls == 1
        checks.append({'fake_provider_service_invalid_name': 'MODEL_INVALID_OUTPUT', 'fake_provider_calls': 1, 'retries': 0})
        for builder in ('build_generation_content.py', 'build_generation_content_v2.py', 'build_structure_variants_v1.py'):
            completed = subprocess.run([sys.executable, str(ROOT / 'contracts/v2' / builder), '--check'], cwd=ROOT,
                                       check=True, capture_output=True, text=True)
            checks.append({'builder': builder, 'exit': completed.returncode, 'stdout': completed.stdout.strip()})
        result['status'] = 'PASS'
    except Exception as error:
        result.update(status='FAIL', first_failure={'type': type(error).__name__, 'code': str(error)})
        raise
    finally:
        result['seconds'] = round(time.perf_counter() - start, 6)
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    run()
