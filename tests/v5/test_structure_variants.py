"""Independent SD3 synthetic structure checks; run only on Main frozen GO.

No real replies, live ledger, entered Key or player database are test inputs.
"""
from __future__ import annotations
import asyncio
import copy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from tests.v5.conftest import Actor, CANARY, FixtureGenerator, private_game_hash, rid
import httpx
import pytest
from jsonschema import Draft202012Validator
from backend.app.ai.budget import BudgetLedger, cost_units
from backend.app.ai import provider as provider_module
from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider, GenerationLimits, ProviderError
from backend.app.ai.v5 import GenerationService, ServiceError
from backend.app.domain import blueprints as legacy
from backend.app.domain import generation_content_v2 as content
from backend.app.domain import structure_variants as structures
from backend.app.domain.generated import Draft, GeneratedRules, compile_level
from tests.v5.test_blueprint_generation import SHAPES, synthetic_content, synthetic_model_content
from tests.v5.test_generation import wire_body

ROOT = Path(__file__).resolve().parents[2]
EPOCH = ROOT / 'evidence/upgrade/v5.0/structure-diversity'
CELLS = [(n, d, seed) for n, d, *_ in SHAPES for seed in range(4)]
COUNTS = {(1, 'easy'): ([2], [5], [5]), (1, 'normal'): ([3], [7], [7]),
    (1, 'hard'): ([4], [8], [8]), (2, 'easy'): ([1, 2], [5, 2], [4, 3]),
    (2, 'normal'): ([2, 2], [6, 2], [5, 3]), (2, 'hard'): ([2, 3], [6, 5], [7, 4]),
    (3, 'easy'): ([1, 1, 2], [5, 1, 2], [4, 1, 3]),
    (3, 'normal'): ([1, 2, 2], [5, 2, 4], [4, 4, 3]),
    (3, 'hard'): ([2, 2, 2], [6, 4, 4], [7, 4, 3])}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def observe(name, value):
    directory = os.environ.get('STRUCTURE_QA_OUTPUT')
    if not directory:
        return
    target = Path(directory).resolve()
    target.relative_to((EPOCH / 'qa').resolve())
    assert Path(name).name == name and name.endswith('.json')
    target.mkdir(parents=True, exist_ok=True)
    with (target / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def model_content(bp, alternate=False):
    raw = synthetic_model_content(bp)
    if alternate:
        # Independent controlled facts, no answer or private real artifact input.
        raw['title'] = '另一次合成校园记录'
        if bp.family == 'position_v1':
            raw['parameters']['digits'] = list('8264')
            raw['parameters']['positions'] = [2, 4, 1, 3]
        else:
            raw['parameters']['code_symbols'] = list('BDAC')
            raw['parameters']['digit_map'] = dict(zip('ABCD', '8264'))
    for index, obj in enumerate(bp.objects):
        raw['objects'][obj.object_id]['name'] = '合成' + {'item': '道具', 'clue': '资料', 'puzzle': '装置'}[obj.kind] + '甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳'[index]
    return raw


def play(compiled):
    rules = GeneratedRules(compiled)
    state = rules.initial_state()
    order = []
    for action in compiled.witness:
        before = set(state.solved_puzzle_ids)
        inventory = list(state.inventory)
        state, observation = rules.apply_action(state, action['tool'], action['arguments'])
        if action['tool'] == 'use_item':
            assert state.inventory == inventory and observation['consumed_item_ids'] == []
        newly = set(state.solved_puzzle_ids) - before
        assert len(newly) <= 1
        order.extend(rules.puzzles[pid].mechanism for pid in newly)
    assert state.status == 'won' and state.room_id == 'EXIT'
    return state, order


@pytest.fixture(scope='session')
def cells():
    return {}


def cell(cells, rooms, difficulty, seed):
    key = (rooms, difficulty, seed)
    if key not in cells:
        bp = content.select_blueprint(rooms, difficulty, seed=seed)
        raw = model_content(bp)
        started = time.monotonic()
        try:
            compiled = compile_level(content.assemble_draft(bp, raw), rooms, difficulty)
        except Exception as error:
            cells[key] = error
            raise
        state, order = play(compiled)
        cells[key] = (bp, raw, compiled, state, order, time.monotonic() - started)
    if isinstance(cells[key], Exception):
        raise cells[key]  # Retain failure; never retry the same matrix proof.
    return cells[key]


@pytest.mark.parametrize('rooms,difficulty,seed', CELLS)
def test_36_selected_contracts_original_proof_and_actual_mechanism_order(cells, rooms, difficulty, seed):
    bp, raw, compiled, state, order, elapsed = cell(cells, rooms, difficulty, seed)
    count = min(6, rooms + {'easy': 1, 'normal': 2, 'hard': 3}[difficulty])
    expected = list(('code', 'sequence', 'circuit', 'code', 'sequence')[:count - 1]) + ['item']
    if seed >= 2:
        expected.reverse()
    assert order == expected
    assert bp.content_version == raw['content_version'] == '2.0.0'
    Draft202012Validator(content.content_schema(bp)).validate(raw)
    assert bp.family == ('position_v1' if seed % 2 == 0 else 'mapping_v1')
    old = legacy.select_blueprint(rooms, difficulty, seed=seed % 2)
    if seed < 2:
        assert bp == replace(old, content_version='2.0.0')
    else:
        assert bp.blueprint_id == old.blueprint_id + '-sv1-reverse'
        assert next(p for p in bp.puzzles if not p.prerequisite_ids).mechanism == 'item'
        key = next(o for o in bp.objects if o.kind == 'item')
        relation = next(o for o in bp.objects if o.role in ('reading_positions', 'symbol_mapping'))
        assert key.room_id == relation.room_id == bp.room_ids[0] and not key.locked_by
        assert relation.locked_by == (bp.puzzles[0].puzzle_id,)
    assert all(sorted(o.slot for o in bp.objects if o.room_id == room) == list(range(sum(o.room_id == room for o in bp.objects))) for room in bp.room_ids)
    assert max(sum(o.room_id == room for o in bp.objects) for room in bp.room_ids) <= 8
    puzzle_counts, forward_counts, reverse_counts = COUNTS[(rooms, difficulty)]
    assert [sum(p.room_id == room for p in bp.puzzles) for room in bp.room_ids] == puzzle_counts
    assert [sum(o.room_id == room for o in bp.objects) for room in bp.room_ids] == (reverse_counts if seed >= 2 else forward_counts)
    if seed >= 2:
        for obj in bp.objects:
            if obj.kind == 'puzzle':
                p = next(p for p in bp.puzzles if p.puzzle_id == obj.reference_id)
                assert (obj.room_id, obj.locked_by) == (p.room_id, p.prerequisite_ids)
            elif obj.role == 'code_source' or obj.role.startswith(('extra_code_', 'extra_devices_')):
                users = [p for p in bp.puzzles if obj.reference_id in p.clue_ids]
                assert len(users) == 1 and obj.room_id == users[0].room_id
            elif obj.role in ('reading_positions', 'symbol_mapping', 'device_source'):
                assert obj.room_id == bp.room_ids[0]
        room_index = {rid: i for i, rid in enumerate(bp.room_ids)}
        for puzzle in bp.puzzles:
            for cid in puzzle.clue_ids:
                obj = next(o for o in bp.objects if o.kind == 'clue' and o.reference_id == cid)
                assert room_index[obj.room_id] <= room_index[puzzle.room_id]
    item_puzzle = next(p for p in compiled.draft.puzzles if p.mechanism == 'item')
    flat = [o for room in compiled.draft.rooms for o in room.objects]
    item_object = next(o for o in flat if o.item_id == item_puzzle.required_item_id)
    target = next(o for o in flat if o.puzzle_id == item_puzzle.puzzle_id)
    assert item_object.name in target.description and item_object.item_id in state.inventory
    assert len(state.solved_puzzle_ids) == count
    observe(f'cell-{rooms}-{difficulty}-{seed}.json', {'blueprint_id': bp.blueprint_id,
        'proof_and_domain_EXIT': True, 'mechanism_order': order, 'definition_hash': compiled.definition_hash,
        'witness_actions': len(compiled.witness), 'seconds_including_domain_replay': elapsed,
        'signatures': structures.structure_signatures(bp), 'real_paid_calls': 0})
    fixture_dir = os.environ.get('STRUCTURE_BROWSER_FIXTURES')
    if fixture_dir and difficulty == 'hard' and rooms in (1, 3) and seed == 3:
        target = Path(fixture_dir).resolve()
        import tempfile
        target.relative_to(Path(tempfile.gettempdir()).resolve())
        # Explicit controlled synthetic cache, never a real private definition.
        with (target / f'R{rooms}.json').open('x', encoding='utf-8') as stream:
            json.dump({'synthetic_only': True, 'draft': compiled.draft.model_dump(),
                       'witness': compiled.witness, 'definition_hash': compiled.definition_hash}, stream)


@pytest.mark.parametrize('rooms,difficulty', [(n, d) for n, d, *_ in SHAPES])
def test_two_signatures_and_actual_order_change_not_family_or_hash_only(cells, rooms, difficulty):
    variants = [cell(cells, rooms, difficulty, s) for s in range(4)]
    signatures = [structures.structure_signatures(x[0]) for x in variants]
    assert signatures[0] == signatures[1] and signatures[2] == signatures[3]
    assert set(signatures[0]) == {'dependency', 'placement', 'full'}
    assert all(signatures[0][key] != signatures[2][key] for key in signatures[0])
    assert variants[0][4] != variants[2][4]


def renamed(bp):
    rooms = {rid: f'new_room_{i}' for i, rid in enumerate(bp.room_ids)}
    puzzles = {p.puzzle_id: f'new_puzzle_{i}' for i, p in enumerate(bp.puzzles)}
    references = {o.reference_id: f'new_fact_or_item_{i}' for i, o in enumerate(bp.objects) if o.kind != 'puzzle'}
    references.update(puzzles)
    return replace(bp, blueprint_id='renamed_catalog_entry', room_ids=tuple(rooms[x] for x in bp.room_ids),
        objects=tuple(replace(o, object_id=f'new_object_{i}', room_id=rooms[o.room_id],
            reference_id=references[o.reference_id], locked_by=tuple(puzzles[x] for x in o.locked_by)) for i, o in enumerate(reversed(bp.objects))),
        puzzles=tuple(replace(p, puzzle_id=puzzles[p.puzzle_id], room_id=rooms[p.room_id],
            prerequisite_ids=tuple(puzzles[x] for x in p.prerequisite_ids),
            clue_ids=tuple(references[x] for x in p.clue_ids),
            required_item_id=references[p.required_item_id] if p.required_item_id else None) for p in reversed(bp.puzzles)))


@pytest.mark.parametrize('seed', range(4))
def test_canonical_all_ID_rename_display_order_and_text_value_invariance(seed):
    bp = content.select_blueprint(3, 'hard', seed=seed)
    before = copy.deepcopy(bp)
    sig = structures.structure_signatures(bp)
    assert structures.canonical_structure(renamed(bp)) == structures.canonical_structure(bp)
    assert structures.structure_signatures(replace(bp, objects=tuple(reversed(bp.objects)))) == sig
    a = content.assemble_draft(bp, model_content(bp))
    b = content.assemble_draft(bp, model_content(bp, True))
    assert a['clues'] != b['clues'] and a['title'] != b['title']
    assert bp == before and structures.structure_signatures(bp) == sig


@pytest.mark.parametrize('kind', ['clue', 'item'])
def test_unused_identical_material_rows_keep_decoy_multiplicity(kind):
    bp = content.select_blueprint(2, 'easy', seed=2)
    template = next(o for o in bp.objects if o.kind == kind)
    room = bp.room_ids[-1]
    start = sum(o.room_id == room for o in bp.objects)
    one = replace(template, object_id='unused_object_a', reference_id='unused_ref_a', room_id=room, slot=start, locked_by=())
    two = replace(one, object_id='unused_object_b', reference_id='unused_ref_b', slot=start + 1)
    original = structures.canonical_structure(bp)
    added = replace(bp, objects=bp.objects + (one, two))
    value = structures.canonical_structure(added)
    row = {'kind': kind, 'uses': [], 'locked_by': []}
    assert value['dependency']['materials'].count(row) == original['dependency']['materials'].count(row) + 2
    assert len(value['dependency']['materials']) == len(original['dependency']['materials']) + 2
    assert structures.structure_signatures(added) == structures.structure_signatures(renamed(added))
    assert structures.structure_signatures(added) != structures.structure_signatures(replace(bp, objects=bp.objects + (one,)))


def test_signature_nonunique_topology_is_unsupported_not_a_claim_of_unsolvability():
    bp = content.select_blueprint(1, 'hard', seed=2)
    branch = replace(bp, puzzles=tuple(replace(p, prerequisite_ids=()) for p in bp.puzzles))
    with pytest.raises(ValueError, match='^STRUCTURE_SIGNATURE_UNSUPPORTED$'):
        structures.canonical_structure(branch)


def test_manifest_custom_renamed_references_and_unused_item_do_not_depend_on_catalog_ID():
    bp = renamed(content.select_blueprint(2, 'normal', seed=3))
    item = next(o for o in bp.objects if o.kind == 'item')
    room = bp.room_ids[-1]
    decoy = replace(item, object_id='unused_decoy_object', reference_id='unused_decoy_item', room_id=room,
                    slot=sum(o.room_id == room for o in bp.objects), locked_by=())
    bp = replace(bp, objects=bp.objects + (decoy,))
    manifest = content.request_manifest(bp)
    puzzle_objects = {o.reference_id: o.object_id for o in bp.objects if o.kind == 'puzzle'}
    item_objects = {o.reference_id: o.object_id for o in bp.objects if o.kind == 'item'}
    assert manifest['structure_catalog_version'] == '1.0.0'
    for puzzle, row in zip(bp.puzzles, manifest['puzzles']):
        assert row['object_slot'] == puzzle_objects[puzzle.puzzle_id]
        assert row['prerequisite_object_slots'] == [puzzle_objects[x] for x in puzzle.prerequisite_ids]
        if puzzle.mechanism == 'item':
            assert row['item_use'] == {'item_object_slot': item_objects[puzzle.required_item_id], 'tool': 'use_item', 'consumed': False}
            assert row['item_use']['item_object_slot'] != decoy.object_id
        else:
            assert 'item_use' not in row


@pytest.mark.parametrize('rooms', [1, 3])
def test_reverse_unobserved_partial_complete_discovery_and_retained_item(cells, rooms):
    bp, _, compiled, *_ = cell(cells, rooms, 'hard', 3)
    rules = GeneratedRules(compiled); state = rules.initial_state()
    puzzle = next(p for p in bp.puzzles if p.mechanism in ('code', 'sequence'))
    target = next(o for o in bp.objects if o.kind == 'puzzle' and o.reference_id == puzzle.puzzle_id)
    for action in compiled.witness:
        if set(puzzle.prerequisite_ids) <= set(state.solved_puzzle_ids):
            break
        if action['tool'] == 'inspect' and next(o for o in bp.objects if o.object_id == action['arguments']['object_id']).kind == 'clue':
            continue
        state, _ = rules.apply_action(state, action['tool'], action['arguments'])
    assert not state.discovered_clue_ids and set(puzzle.prerequisite_ids) <= set(state.solved_puzzle_ids)
    def view(): return rules.visible_state('synthetic_session', state)
    def target_description(): return next(o['description'] for o in view()['objects'] if o['object_id'] == target.object_id)
    assert '资料组合次序：' not in target_description()
    state, _ = rules.apply_action(state, 'inspect', {'object_id': target.object_id})
    for index, cid in enumerate(puzzle.clue_ids):
        obj = next(o for o in bp.objects if o.kind == 'clue' and o.reference_id == cid)
        state, _ = rules.apply_action(state, 'inspect', {'object_id': obj.object_id})
        description = target_description()
        complete = index == len(puzzle.clue_ids) - 1
        assert ('资料组合次序：' in description) == complete
        assert {c['clue_id'] for c in view()['clues']} == set(state.discovered_clue_ids)
        if not complete: assert all(x not in description for x in puzzle.clue_ids)
    item = next(o for o in bp.objects if o.kind == 'item')
    assert item.reference_id in state.inventory
    observe(f'partial-R{rooms}.json', {'unobserved_partial_complete_via_legal_actions': True,
        'actual_synthetic_partial_context': True, 'item_retained': True, 'real_model_sample': False})


@pytest.mark.parametrize('bad_seed', [True, -1, 1.0, '2'])
def test_seed_strictness(bad_seed):
    with pytest.raises(ValueError, match='^BLUEPRINT_SEED$'):
        content.select_blueprint(1, 'easy', seed=bad_seed)


def test_default_exactly_one_host_random_choice_and_explicit_legacy_family_seed(monkeypatch):
    original = legacy.select_blueprint
    calls = []; random = []
    def choose(n):
        random.append(n)
        return 3
    def old(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)
    monkeypatch.setattr(structures.secrets, 'randbelow', choose)
    monkeypatch.setattr(legacy, 'select_blueprint', old)
    bp = content.select_blueprint(3, 'hard')
    assert random == [4] and calls == [((3, 'hard'), {'seed': 1})]
    assert bp.family == 'mapping_v1' and bp.blueprint_id.endswith('-sv1-reverse')


def test_new36_and_retained18_catalog_builders_reproduce_without_migration():
    from contracts.v2.build_structure_variants_v1 import build
    from contracts.v2.build_generation_content_v2 import build as old2
    from contracts.v2.build_generation_content import build as old1
    artifact = json.loads((ROOT / 'contracts/v2/generation-structures-v1.schema.json').read_text(encoding='utf-8'))
    assert artifact == build() and len(artifact['oneOf']) == 36
    Draft202012Validator.check_schema(artifact)
    assert artifact['structure_catalog_version'] == '1.0.0' and artifact['content_contract_version'] == '2.0.0'
    assert old2() == json.loads((ROOT / 'contracts/v2/generation-content-v2.schema.json').read_text(encoding='utf-8'))
    assert old1() == json.loads((ROOT / 'contracts/v2/generation-content.schema.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('kind', ['cycle', 'key-self-lock', 'future-material', 'duplicate-slot', 'slot8', 'room9', 'combination', 'depth'])
def test_original_admission_refuses_invalid_or_unproven_candidates(cells, kind):
    rooms, difficulty, seed = (1, 'hard', 0) if kind in {'combination', 'depth', 'room9'} else (3, 'hard', 0)
    _, _, compiled, *_ = cell(cells, rooms, difficulty, seed)
    draft = compiled.draft.model_dump()
    objects = [o for room in draft['rooms'] for o in room['objects']]
    if kind == 'cycle':
        draft['puzzles'][0]['prerequisite_ids'] = [draft['puzzles'][-1]['puzzle_id']]
    elif kind == 'key-self-lock':
        key = next(o for o in objects if o['kind'] == 'item')
        key['locked_by'] = [next(p['puzzle_id'] for p in draft['puzzles'] if p['mechanism'] == 'item')]
    elif kind == 'future-material':
        source = next(o for o in draft['rooms'][0]['objects'] if o.get('clue_id') == 'fact_relation')
        draft['rooms'][0]['objects'].remove(source)
        source['slot'] = len(draft['rooms'][-1]['objects']); draft['rooms'][-1]['objects'].append(source)
    elif kind == 'duplicate-slot': draft['rooms'][0]['objects'][1]['slot'] = draft['rooms'][0]['objects'][0]['slot']
    elif kind == 'slot8': objects[0]['slot'] = 8
    elif kind == 'room9':
        extra = copy.deepcopy(objects[0]); extra.update(object_id='extra_ninth_object', item_id='extra_ninth_item', slot=0)
        draft['rooms'][0]['objects'].append(extra)
    elif kind == 'combination':
        for puzzle in draft['puzzles']:
            if puzzle['mechanism'] in ('code', 'sequence'):
                puzzle['clue_ids'] = puzzle['clue_ids'][:1]; puzzle['recipe'] = 'concat'
    else:
        for puzzle in draft['puzzles']: puzzle['prerequisite_ids'] = []
    with pytest.raises(ValueError):
        compile_level(draft, rooms, difficulty)


@pytest.mark.parametrize('rooms,seed', [(1, 2), (3, 3)])
def test_production_same_instance_API_multimoment_restore_and_process_reopen(cells, tmp_path, monkeypatch, rooms, seed):
    from backend.app.main import create_v5_app
    bp, raw, compiled, *_ = cell(cells, rooms, 'hard', seed)
    original_schema, original_manifest, original_assemble = content.content_schema, content.request_manifest, content.assemble_draft
    selected = []; stages = []
    def choose(*args, **kwargs): selected.append((args, kwargs)); return bp
    def bound(operation, name):
        def invoke(given, *args, **kwargs):
            assert given is bp; stages.append(name); return operation(given, *args, **kwargs)
        return invoke
    monkeypatch.setattr(content, 'select_blueprint', choose)
    monkeypatch.setattr(content, 'content_schema', bound(original_schema, 'schema'))
    monkeypatch.setattr(content, 'request_manifest', bound(original_manifest, 'manifest'))
    monkeypatch.setattr(content, 'assemble_draft', bound(original_assemble, 'assemble'))
    sends = []; ledger = BudgetLedger(tmp_path / 'synthetic-budget.sqlite')
    def handler(request):
        sends.append(request)
        assert request.headers['authorization'] == 'Bearer ' + CANARY and CANARY.encode() not in request.content
        payload = json.loads(request.content)
        user = json.loads(payload['messages'][1]['content'])
        assert user['schema'] == original_schema(bp) and user['blueprint'] == original_manifest(bp)
        assert payload['max_tokens'] == 6000 and payload['response_format'] == {'type': 'json_object'}
        return httpx.Response(200, json=wire_body(json.dumps(raw)))
    provider = DeepSeekProvider(DeepSeekConfig(CANARY), ledger, transport=httpx.MockTransport(handler))
    service = GenerationService(lambda key: provider)
    app = create_v5_app(tmp_path / 'game-v5.sqlite', generation_service=service)
    actor = Actor(app).authenticate('structure_owner')
    job = actor.generate(rooms, 'hard'); state = actor.session('generated', job['level_id']); sid = state['session_id']
    assert state['definition_hash'] == compiled.definition_hash
    assert len(sends) == len(selected) == 1 and {'schema', 'manifest', 'assemble'} <= set(stages)
    saves = []
    db = app.state.v5_database; principal = db.authenticate(actor.client.cookies.get('campus_v5_session'))
    fields = db.owned(principal, sid).rules.game_fields
    for index in range(len(compiled.witness) + 1):
        if index in {0, len(compiled.witness) // 2, len(compiled.witness)}:
            saved = actor.post(f'/sessions/{sid}/saves', actor.versioned(state, name=f'时刻{index}'))
            assert saved.status_code == 201
            saves.append((saved.json()['data']['slot']['save_id'], private_game_hash(db, sid, fields)))
            state = actor.state(sid)
        if index < len(compiled.witness):
            action = compiled.witness[index]
            response = actor.action(state, action['tool'], action['arguments']); assert response.status_code == 200
            state = response.json()['data']['visible_state']
    assert state['status'] == 'won' and len(saves) == 3
    def forbidden(*args, **kwargs): pytest.fail('Restore/reload tried new selection or generation')
    monkeypatch.setattr(content, 'select_blueprint', forbidden)
    monkeypatch.setattr(service, 'generate', forbidden)
    for save_id, game_hash in reversed(saves):
        response = actor.post(f'/sessions/{sid}/saves/{save_id}/restore', actor.versioned(state)); assert response.status_code == 200
        state = response.json()['data']['visible_state']
        assert private_game_hash(db, sid, fields) == game_hash
        assert actor.state(sid)['definition_hash'] == compiled.definition_hash
    probe = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(EPOCH / 'qa/reopen_probe.py'),
        '--db', db.path, '--owner', principal['user_id'], '--session', sid], capture_output=True, timeout=30)
    assert probe.returncode == 0
    reopened = json.loads(probe.stdout)
    assert reopened['definition_hash'] == compiled.definition_hash and reopened['game_hash'] == saves[0][1]
    assert len(sends) == len(selected) == 1 and ledger.snapshot()['calls'] == 1
    observe(f'api-save-R{rooms}.json', {'production_MockTransport_once': True, 'same_instance': True,
        'three_moments_selected_restore': True, 'actual_child_process_reload_hash': True,
        'definition_hash': compiled.definition_hash, 'paid_calls': 0})


@pytest.mark.parametrize('version', ['v1', 'v2'])
def test_old_complete_definitions_preserve_bytes_text_and_hash_without_selection(tmp_path, monkeypatch, version):
    from backend.app.main import create_v5_app
    bp = legacy.select_blueprint(1, 'easy', seed=0)
    if version == 'v1':
        draft = legacy.assemble_draft(bp, synthetic_content(bp))
    else:
        bp = replace(bp, content_version='2.0.0')
        draft = content.assemble_draft(bp, model_content(bp))
    draft['rooms'][0]['objects'][0]['description'] = '历史完整定义的特定说明保持原样。'
    generator = FixtureGenerator(); generator.output = draft
    app = create_v5_app(tmp_path / 'game-v5.sqlite', generation_service=generator)
    actor = Actor(app).authenticate('legacy_structure_owner')
    job = actor.generate(1, 'easy'); state = actor.session('generated', job['level_id']); sid = state['session_id']
    db = app.state.v5_database; principal = db.authenticate(actor.client.cookies.get('campus_v5_session'))
    fields = db.owned(principal, sid).rules.game_fields; original_game_hash = private_game_hash(db, sid, fields)
    with db.transaction() as c:
        definition_before = c.execute('SELECT definition_json FROM generated_levels WHERE level_id=?', (job['level_id'],)).fetchone()[0]
    saved = actor.post(f'/sessions/{sid}/saves', actor.versioned(state, name='历史完整定义'))
    assert saved.status_code == 201; save_id = saved.json()['data']['slot']['save_id']
    def forbidden(*args, **kwargs): pytest.fail('Complete old definition attempted structure selection/LLM')
    monkeypatch.setattr(content, 'select_blueprint', forbidden)
    monkeypatch.setattr(legacy, 'select_blueprint', forbidden)
    monkeypatch.setattr(structures, 'select_blueprint', forbidden)
    monkeypatch.setattr(generator, 'generate', forbidden)
    reopened = create_v5_app(db.path, generation_service=generator)
    owner = Actor(reopened).authenticate('legacy_structure_owner', False)
    current = owner.state(sid)
    restored = owner.post(f'/sessions/{sid}/saves/{save_id}/restore', owner.versioned(current)); assert restored.status_code == 200
    current = restored.json()['data']['visible_state']
    assert current['definition_hash'] == state['definition_hash'] and private_game_hash(reopened.state.v5_database, sid, fields) == original_game_hash
    assert current['objects'][0]['description'] == draft['rooms'][0]['objects'][0]['description']
    with db.transaction() as c:
        assert c.execute('SELECT definition_json FROM generated_levels WHERE level_id=?', (job['level_id'],)).fetchone()[0] == definition_before
    probe = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(EPOCH / 'qa/reopen_probe.py'),
        '--db', db.path, '--owner', principal['user_id'], '--session', sid], capture_output=True, timeout=30)
    assert probe.returncode == 0
    value = json.loads(probe.stdout)
    assert value['definition_hash'] == state['definition_hash'] and value['game_hash'] == original_game_hash
    assert len(generator.calls) == 1


def test_key_before_selection_and_wrong_structure_reply_no_repair(tmp_path, monkeypatch):
    bp = content.select_blueprint(1, 'hard', seed=2)
    wrong = model_content(content.select_blueprint(1, 'hard', seed=0))
    calls = []; sends = []
    monkeypatch.setattr(content, 'select_blueprint', lambda *a, **k: calls.append(True) or bp)
    ledger = BudgetLedger(tmp_path / 'synthetic-invalid.sqlite')
    def handler(request): sends.append(True); return httpx.Response(200, json=wire_body(json.dumps(wrong)))
    provider = DeepSeekProvider(DeepSeekConfig(CANARY), ledger, transport=httpx.MockTransport(handler))
    service = GenerationService(lambda key: provider)
    for key in ('', '非法密钥'):
        with pytest.raises(ServiceError, match='AI_KEY_REQUIRED'):
            asyncio.run(service.generate(theme='合成', room_count=1, difficulty='hard', api_key=key, draft_schema={}))
    assert not calls and not sends and ledger.snapshot()['calls'] == 0
    with pytest.raises(ServiceError, match='MODEL_INVALID_OUTPUT'):
        asyncio.run(service.generate(theme='合成', room_count=1, difficulty='hard', api_key=CANARY, draft_schema={}))
    assert len(calls) == len(sends) == 1 and ledger.snapshot()['calls'] == 1


def test_full36_short_and_four_maximal_four_byte_requests_and_overcap_before_reserve(tmp_path, monkeypatch):
    observations = []; over = []
    requests = [(n, d, s, '合成校园') for n, d, s in CELLS] + [(3, 'hard', s, '\U0001f9ea' * 2000) for s in range(4)]
    for rooms, difficulty, seed, theme in requests:
        bp = content.select_blueprint(rooms, difficulty, seed=seed)
        messages = GenerationService.messages(theme=theme, room_count=rooms, difficulty=difficulty, blueprint=bp)
        body = {'model': 'deepseek-flash', 'messages': messages, 'max_tokens': 6000, 'thinking': {'type': 'disabled'}, 'stream': False, 'response_format': {'type': 'json_object'}}
        dumps = json.dumps
        encoded = dumps(body, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
        size = len(encoded); bound = cost_units(size * 4 + 8192, 6000)
        captured = []; reserve_calls = []
        class StopBeforeReserve(RuntimeError): pass
        class PureLedger:
            path = tmp_path / 'never-created-pure-ledger.sqlite'
            def reserve(self, scope, amount):
                reserve_calls.append((scope, amount))
                raise StopBeforeReserve()
        def capture(value, *args, **kwargs):
            result = dumps(value, *args, **kwargs)
            if isinstance(value, dict) and set(value) == set(body) and value.get('model') == 'deepseek-flash':
                captured.append(result.encode())
            return result
        def no_transport(request): raise AssertionError('Pure accounting unexpectedly sent')
        provider = DeepSeekProvider(DeepSeekConfig(CANARY), PureLedger(), transport=httpx.MockTransport(no_transport))
        with monkeypatch.context() as local:
            local.setattr(provider_module.json, 'dumps', capture)
            expected_error = ProviderError if bound > 200_000_000 else StopBeforeReserve
            with pytest.raises(expected_error) as error:
                asyncio.run(provider.complete(messages, [], GenerationLimits(), scope='v5_generation', tool_choice='none'))
        assert captured == [encoded]  # Real production complete() serialized these exact bytes.
        if bound > 200_000_000:
            assert error.value.code == 'AI_LIMIT_REACHED' and reserve_calls == []
        else:
            assert reserve_calls == [('v5_generation', bound)]
        assert not PureLedger.path.exists()
        if len(theme) < 2000: assert bound <= 200_000_000
        elif bound > 200_000_000: over.append((bp, theme))
        observations.append({'rooms': rooms, 'difficulty': difficulty, 'seed': seed, 'theme_characters': len(theme), 'bytes': size, 'upper_cny': bound / 1e9})
    assert over
    bp, theme = over[-1]; monkeypatch.setattr(content, 'select_blueprint', lambda *a, **k: bp)
    ledger = BudgetLedger(tmp_path / 'synthetic-overcap.sqlite'); before = ledger.snapshot(); sends = []
    def handler(request): sends.append(True); raise AssertionError('Overcap sent')
    provider = DeepSeekProvider(DeepSeekConfig(CANARY), ledger, transport=httpx.MockTransport(handler))
    with pytest.raises(ServiceError, match='AI_LIMIT_REACHED'):
        asyncio.run(GenerationService(lambda key: provider).generate(theme=theme, room_count=3, difficulty='hard', api_key=CANARY, draft_schema={}))
    assert not sends and ledger.snapshot() == before
    observe('whole-request-budgets.json', {'measurements': observations, 'overcap_synthetic_before_reserve': True, 'cap_cny': .20, 'max_tokens': 6000, 'paid_calls': 0})
