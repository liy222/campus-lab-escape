"""One synthetic Owner development matrix, not independent QA or model output."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from jsonschema import Draft202012Validator
from backend.app.domain import blueprints as old
from backend.app.domain import generation_content_v2 as content
from backend.app.domain import structure_variants as structures
from backend.app.domain.generated import GeneratedRules, compile_level

OUT = Path(__file__).with_name('development-matrix.json')


def synthetic(bp):
    params = ({'digits': list('9317'), 'positions': [2, 4, 1, 3]}
              if bp.family == 'position_v1' else
              {'code_symbols': list('BDAC'), 'digit_map': dict(zip('ABCD', '9317'))})
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
    return {'content_version': '2.0.0', 'blueprint_id': bp.blueprint_id,
            'title': '合成资料室', 'story': '窗外的雨声映着整齐的书架。',
            'rooms': {rid: {'name': '静室', 'description': '灯光落在桌面与墙上。'} for rid in bp.room_ids},
            'objects': {obj.object_id: {'name': '资料物件'} for obj in bp.objects},
            'parameters': params}


def main():
    records = []
    result = {'kind': 'Owner synthetic development; not independent QA',
              'original_solver_limits': {'states': 25000, 'seconds': 5},
              'provider_calls': 0, 'records': records, 'first_failure': None}
    catalog = json.loads((ROOT / 'contracts/v2/generation-structures-v1.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(catalog)
    validator = Draft202012Validator(catalog)
    start = time.perf_counter()
    try:
        for rooms in (1, 2, 3):
            for difficulty in ('easy', 'normal', 'hard'):
                shape = []
                for seed in range(4):
                    case_start = time.perf_counter()
                    row = {'rooms': rooms, 'difficulty': difficulty, 'seed': seed}
                    records.append(row)
                    bp = content.select_blueprint(rooms, difficulty, seed=seed)
                    row['blueprint_id'] = bp.blueprint_id
                    if seed < 2:
                        assert replace(bp, content_version='1.0.0') == old.select_blueprint(rooms, difficulty, seed=seed)
                    value = synthetic(bp)
                    raw = json.dumps(value, ensure_ascii=False)
                    Draft202012Validator(content.content_schema(bp)).validate(value)
                    validator.validate(value)
                    manifest = content.request_manifest(bp)
                    assert manifest['structure_catalog_version'] == structures.CATALOG_VERSION
                    object_by_puzzle = {obj.reference_id: obj.object_id for obj in bp.objects if obj.kind == 'puzzle'}
                    assert [r['prerequisite_object_slots'] for r in manifest['puzzles']] == [
                        [object_by_puzzle[pid] for pid in p.prerequisite_ids] for p in bp.puzzles]
                    compiled = compile_level(content.assemble_draft(bp, raw), rooms, difficulty)
                    assert raw == json.dumps(value, ensure_ascii=False)
                    rules = GeneratedRules(compiled)
                    state = rules.initial_state()
                    solved_order = []
                    by_id = {p.puzzle_id: p for p in bp.puzzles}
                    for action in compiled.witness:
                        previous = set(state.solved_puzzle_ids)
                        state, _ = rules.apply_action(state, action['tool'], action['arguments'])
                        solved_order.extend(by_id[pid].mechanism for pid in state.solved_puzzle_ids if pid not in previous)
                    assert state.status == 'won' and state.room_id == 'EXIT'
                    assert solved_order == [p.mechanism for p in bp.puzzles]
                    signatures = structures.structure_signatures(bp)
                    row.update(status='PASS', object_counts=[len(r.objects) for r in compiled.draft.rooms],
                               solved_mechanisms=solved_order, witness_steps=len(compiled.witness),
                               definition_hash=compiled.definition_hash, signatures=signatures,
                               seconds=round(time.perf_counter() - case_start, 6))
                    shape.append(row)
                    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                    print(json.dumps({'shape': [rooms, difficulty], 'seed': seed, 'status': 'PASS',
                                      'seconds': row['seconds']}), flush=True)
                assert shape[0]['signatures'] == shape[1]['signatures']
                assert shape[2]['signatures'] == shape[3]['signatures']
                assert shape[0]['solved_mechanisms'] != shape[2]['solved_mechanisms']
                assert all(shape[0]['signatures'][key] != shape[2]['signatures'][key]
                           for key in ('dependency', 'placement', 'full'))
        result['status'] = 'PASS'
    except Exception as error:
        result['status'] = 'FAIL'
        result['first_failure'] = {'record': len(records), 'type': type(error).__name__, 'code': str(error)}
        raise
    finally:
        result['seconds'] = round(time.perf_counter() - start, 6)
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
