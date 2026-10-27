"""Finite pure Owner canonical/selection/frozen-source checks, not formal QA."""
from __future__ import annotations

import ast
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from backend.app.domain import generation_content_v2 as content
from backend.app.domain import structure_variants as structures
from backend.app.domain.blueprints import ObjectSlot


def main():
    checks = []
    bp = content.select_blueprint(3, 'hard', seed=3)
    expected = structures.structure_signatures(bp)
    identifiers = set(bp.room_ids)
    for obj in bp.objects:
        identifiers.update((obj.object_id, obj.reference_id))
    identifiers.update(p.puzzle_id for p in bp.puzzles)
    names = {value: 'renamed_' + str(100 - index) for index, value in enumerate(sorted(identifiers))}
    renamed = replace(bp, blueprint_id='unregistered-custom-id', family='unregistered-family',
                      room_ids=tuple(names[rid] for rid in bp.room_ids),
                      objects=tuple(replace(obj, object_id=names[obj.object_id], room_id=names[obj.room_id],
                                            reference_id=names[obj.reference_id],
                                            locked_by=tuple(names[pid] for pid in obj.locked_by))
                                    for obj in reversed(bp.objects)),
                      puzzles=tuple(replace(p, puzzle_id=names[p.puzzle_id], room_id=names[p.room_id],
                                            prerequisite_ids=tuple(names[pid] for pid in p.prerequisite_ids),
                                            clue_ids=tuple(names[cid] for cid in p.clue_ids),
                                            required_item_id=names[p.required_item_id] if p.required_item_id else None,
                                            recipe='excluded-recipe-label') for p in reversed(bp.puzzles)))
    assert structures.structure_signatures(renamed) == expected
    checks.append('all-ID rename/object+puzzle reorder/family+recipe label excluded')
    first = ObjectSlot('decoyA', bp.room_ids[-1], 'item', 'unused', 'unusedA', 'key', 6)
    second = replace(first, object_id='decoyB', reference_id='unusedB', slot=7)
    one = replace(bp, objects=bp.objects + (first,))
    two = replace(bp, objects=bp.objects + (first, second))
    one_rows = structures.canonical_structure(one)['dependency']['materials']
    two_rows = structures.canonical_structure(two)['dependency']['materials']
    unused = {'kind': 'item', 'uses': [], 'locked_by': []}
    assert one_rows.count(unused) == 1 and two_rows.count(unused) == 2
    assert structures.structure_signatures(one)['dependency'] != structures.structure_signatures(two)['dependency']
    checks.append('unused material duplicate canonical rows retained')
    # Signature-domain rejection is deliberately separate from compiler admission.
    branch = replace(bp, puzzles=tuple(replace(p, prerequisite_ids=()) if i == 1 else p
                                       for i, p in enumerate(bp.puzzles)))
    try:
        structures.canonical_structure(branch)
        raise AssertionError('branch accepted for signature')
    except ValueError as error:
        assert str(error) == 'STRUCTURE_SIGNATURE_UNSUPPORTED'
    checks.append('nonunique-chain signature domain error only')
    changed_position = replace(bp, puzzles=tuple(replace(p, clue_ids=tuple(reversed(p.clue_ids)))
                                                if len(p.clue_ids) > 1 else p for p in bp.puzzles))
    assert structures.structure_signatures(changed_position)['dependency'] != expected['dependency']
    checks.append('real clue use positions retained')
    with patch.object(structures.secrets, 'randbelow', return_value=3) as random:
        selected = content.select_blueprint(3, 'hard')
    random.assert_called_once_with(4)
    assert selected == bp
    checks.append('one random selection and immutable selected result')
    for invalid in (True, -1, 1.0, '2'):
        try:
            content.select_blueprint(3, 'hard', seed=invalid)
            raise AssertionError('invalid seed accepted')
        except ValueError as error:
            assert str(error) == 'BLUEPRINT_SEED'
    checks.append('strict seed types retained')
    # A renamed supported-family Blueprint exercises manifest actual refs, not IDs.
    manifest_bp = replace(renamed, family=bp.family)
    manifest = content.request_manifest(manifest_bp)
    object_by_puzzle = {obj.reference_id: obj.object_id for obj in manifest_bp.objects if obj.kind == 'puzzle'}
    assert [row['prerequisite_object_slots'] for row in manifest['puzzles']] == [
        [object_by_puzzle[pid] for pid in p.prerequisite_ids] for p in manifest_bp.puzzles]
    checks.append('manifest custom IDs and actual prerequisites')

    path = 'backend/app/domain/generation_content_v2.py'
    previous = subprocess.run(['git', 'show', 'HEAD:' + path], cwd=ROOT, check=True,
                              capture_output=True).stdout.decode('utf-8-sig')
    current = (ROOT / path).read_text(encoding='utf-8-sig')
    before_tree, after_tree = ast.parse(previous), ast.parse(current)
    allowed = {'select_blueprint', 'request_manifest'}
    before_nodes = [n for n in before_tree.body if not (isinstance(n, ast.FunctionDef) and n.name in allowed)]
    after_nodes = [n for n in after_tree.body if not (
        isinstance(n, ast.FunctionDef) and n.name in allowed or
        isinstance(n, ast.ImportFrom) and n.module is None and
        [a.name for a in n.names] == ['structure_variants'])]
    assert [ast.dump(n, include_attributes=False) for n in before_nodes] == [
        ast.dump(n, include_attributes=False) for n in after_nodes]
    old_functions = {n.name: n for n in before_tree.body if isinstance(n, ast.FunctionDef)}
    new_functions = {n.name: n for n in after_tree.body if isinstance(n, ast.FunctionDef)}
    for name in old_functions.keys() - allowed:
        assert ast.get_source_segment(previous, old_functions[name]) == ast.get_source_segment(current, new_functions[name])
    checks.append('v2 only one import + select/manifest AST and other functions byte unchanged')
    hashes = json.loads(Path(__file__).with_name('before.json').read_text(encoding='utf-8'))['paths']
    for frozen, expected_hash in hashes.items():
        if frozen != path:
            assert hashlib.sha256((ROOT / frozen).read_bytes()).hexdigest() == expected_hash, frozen
    checks.append('all nine recorded historical sources except allowed v2 unchanged')
    paths = ['backend/app/domain/structure_variants.py', path, 'contracts/v2/build_structure_variants_v1.py']
    for source in paths:
        ast.parse((ROOT / source).read_text(encoding='utf-8-sig'))
    checks.append('new and changed Python syntax')
    result = {'kind': 'Owner pure finite development boundaries; not independent QA',
              'status': 'PASS', 'checks': checks, 'compile_or_proof_invocations': 0,
              'provider_calls': 0}
    Path(__file__).with_name('development-boundaries.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
