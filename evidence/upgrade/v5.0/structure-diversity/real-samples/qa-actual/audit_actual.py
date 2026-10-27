"""Closed-allowlist local audit of this one admitted content2 sample.

Never print model raw, parameters, facts, answers, actions or state dictionaries.
Only this OUT's four local originals may be read. No application/provider/DB,
network, compiler or solver is imported or called. Player prose is explicitly
constructed only after admission/raw/schema/definition gates have succeeded.
"""
from __future__ import annotations

import ast
import hashlib
import json
import importlib.abc
import socket
import sqlite3
import subprocess
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parents[1]
QA = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def write(name, value):
    with (QA / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


class NoServices(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if (fullname.startswith('backend.app.ai') or fullname.startswith('backend.app.storage')
                or fullname.startswith('backend.app.api') or fullname == 'backend.app.main'):
            raise RuntimeError('LOCAL_AUDIT_FORBIDDEN_IMPORT')
        return None


def denied(*args, **kwargs):
    raise RuntimeError('LOCAL_AUDIT_FORBIDDEN_RUNTIME')


def audit():
    stage = 'admission_and_source_gate'
    try:
        sys.meta_path.insert(0, NoServices())
        socket.socket.connect = denied
        socket.socket.connect_ex = denied
        socket.create_connection = denied
        sqlite3.connect = denied
        preview = load(OUT / 'offline-preview-v1.json')
        result = load(OUT / 'result.json')
        api = load(OUT / 'G3-api-result.json')
        exact = load(OUT / 'G3-exact-payload.json')
        assert result['exit_code'] == 0 and result['cases'] == [api]
        assert api['status'] == 'ready_and_replayed' and api['job']['status'] == 'ready'
        assert result['attempted_case_ids'] == ['G3'] and result['scope'] == ['G3']
        assert len(preview['source']) == 455 and result['source_after'] == preview['source']
        assert all(digest((ROOT / name).read_bytes()) == value for name, value in preview['source'].items())
        assert digest(canonical(preview['source']).encode()) == preview['candidate_sha256']
        assert exact['payload'] == preview['generation_cases'][0]['payload']
        assert exact['bound'] == preview['generation_cases'][0]['bound']

        stage = 'raw_hash_and_schema2_gate'
        provider_path = OUT / 'G3-provider-result.json'
        provider_original_sha256 = digest(provider_path.read_bytes())
        ignored = subprocess.run(['git', 'check-ignore', '--', provider_path.relative_to(ROOT).as_posix()], capture_output=True, text=True, encoding='utf-8')
        assert ignored.returncode == 0
        assert ignored.stdout.strip() == provider_path.relative_to(ROOT).as_posix()
        provider = load(provider_path)
        raw = provider['content_redacted']
        assert not provider['secret_detected']
        assert digest(raw.encode()) == provider['content_raw_sha256']
        from backend.app.domain import generated as generated
        from backend.app.domain import blueprints as v1
        from backend.app.domain import generation_content_v2 as v2
        assert not any(name in sys.modules for name in ('backend.app.ai.provider', 'backend.app.main', 'backend.app.storage.v5'))
        generated.compile_level = denied
        generated.solve = denied
        content = generated.strict_json(raw)
        blueprint = v2.select_blueprint(3, 'hard', seed=3)
        assert blueprint.blueprint_id == 'mapping_v1-r3-hard-sv1-reverse'
        assert [p.mechanism for p in blueprint.puzzles] == ['item', 'sequence', 'code', 'circuit', 'sequence', 'code']
        schema = v2.content_schema(blueprint)
        assert not list(v1._IntegerValidator(schema).iter_errors(content))
        assert content['content_version'] == '2.0.0'
        assert len(content['objects']) == 14
        assert all(set(row) == {'name'} for row in content['objects'].values())
        extra = {'obj_extra_code_a', 'obj_extra_code_b', 'obj_extra_devices_a', 'obj_extra_devices_b'}
        assert extra <= set(content['objects'])

        stage = 'saved_definition_gate'
        definition_path = OUT / 'raw-sensitive/G3-private-definition-local.json'
        witness_path = OUT / 'raw-sensitive/G3-witness-local.json'
        trace_path = OUT / 'raw-sensitive/G3-api-replay-local.json'
        saved = load(definition_path)['definition']
        witness = load(witness_path)['witness']
        trace = load(trace_path)
        assert v2.NARRATIVE_GUARD_REVISION == '1'
        assembled = v2.assemble_draft(blueprint, raw)
        definition = generated.Draft.model_validate(assembled)
        assert definition.model_dump() == saved['draft']
        clues = {clue.clue_id: clue for clue in definition.clues}
        answers = {p.puzzle_id: generated.derive(p, clues) for p in definition.puzzles
                   if p.mechanism in {'code', 'sequence'}}
        compiled = generated.CompiledLevel(definition, answers, witness, saved['policy_version'])
        assert compiled.private_dump() == saved
        assert compiled.definition_hash == trace['definition_hash'] == api['definition_hash']
        assert digest(canonical(witness).encode()) == api['witness_sha256']
        assert len(witness) == len(trace['steps']) == api['witness_actions'] == 33
        assert compiled.definition_hash == '5371808d6549df60336bff859b89556649822465a902716427bff7ff3a33e948'
        model_names = {key: value['name'] for key, value in content['objects'].items()}
        objects = {obj.object_id: obj for room in definition.rooms for obj in room.objects}
        assert all(objects[key].name == name for key, name in model_names.items())
        item_puzzle = next(p for p in definition.puzzles if p.mechanism == 'item')
        key_object = next(obj for obj in objects.values() if obj.kind == 'item' and obj.item_id == item_puzzle.required_item_id)
        item_target = next(obj for obj in objects.values() if obj.puzzle_id == item_puzzle.puzzle_id)
        assert key_object.name in item_target.description

        stage = 'saved_rule_state_chain'
        end = trace['final_visible_state']
        rules = generated.GeneratedRules(compiled, level_id=end['level_id'])
        state = rules.initial_state()
        # Recorded metadata is reused only to explain saved observable hashes.
        state.generation = end['generation']
        state.started_at = end['statistics']['started_at']
        def visible():
            value = rules.visible_state(end['session_id'], state, save=end['save'])
            value['level_id'] = end['level_id']
            return value
        assert digest(canonical(visible()).encode()) == trace['initial_visible_state_sha256']
        gate_checks = {'unobserved': 0, 'observed_partial': 0, 'observed_complete': 0}
        relation = next(obj for obj in blueprint.objects if obj.role == 'symbol_mapping')
        first_item = blueprint.puzzles[0]
        assert first_item.mechanism == 'item' and not first_item.prerequisite_ids
        assert relation.locked_by == (first_item.puzzle_id,)
        relation_gate_checks = []
        actual_mechanism_order = []
        def check_discovery():
            value = visible()
            assert {row['clue_id'] for row in value['clues']} == set(state.discovered_clue_ids)
            if state.room_id == blueprint.room_ids[0]:
                expected_visible = first_item.puzzle_id in state.solved_puzzle_ids
                assert (relation.object_id in {row['object_id'] for row in value['objects']}) == expected_visible
                relation_gate_checks.append(expected_visible)
            for row in value['objects']:
                assert rules.objects[row['object_id']][0] == state.room_id
                obj = objects[row['object_id']]
                if obj.kind != 'puzzle':
                    continue
                puzzle = rules.puzzles[obj.puzzle_id]
                if puzzle.mechanism not in {'code', 'sequence'}:
                    continue
                observed = obj.object_id in state.observed_object_ids
                complete = set(puzzle.clue_ids) <= set(state.discovered_clue_ids)
                key = 'unobserved' if not observed else 'observed_complete' if complete else 'observed_partial'
                gate_checks[key] += 1
                assert ('资料组合次序：' in row['description']) == (observed and complete)
                if not (observed and complete):
                    assert all(cid not in row['description'] for cid in puzzle.clue_ids)
        check_discovery()
        matched = 0
        uses = []
        with patch.object(generated, 'now', return_value=end['statistics']['finished_at']):
            for index, (action, saved_step) in enumerate(zip(witness, trace['steps'])):
                assert saved_step['index'] == index and saved_step['http_status'] == 200
                assert saved_step['tool'] == action['tool']
                before_inventory = list(state.inventory)
                before_solved = set(state.solved_puzzle_ids)
                state, observation = rules.apply_action(state, action['tool'], action['arguments'])
                assert digest(canonical(visible()).encode()) == saved_step['visible_state_sha256']
                matched += 1
                newly_solved = set(state.solved_puzzle_ids) - before_solved
                assert len(newly_solved) <= 1
                actual_mechanism_order.extend(rules.puzzles[pid].mechanism for pid in newly_solved)
                check_discovery()
                if action['tool'] == 'use_item':
                    uses.append(action['arguments']['item_id'] in before_inventory
                        and state.inventory == before_inventory and observation['consumed_item_ids'] == [])
        assert visible() == end and trace['complete'] and state.status == 'won' and state.room_id == 'EXIT'
        assert uses == [True] and key_object.item_id in state.inventory
        assert actual_mechanism_order == ['item', 'sequence', 'code', 'circuit', 'sequence', 'code']
        assert False in relation_gate_checks and True in relation_gate_checks

        stage = 'authorization_and_saved_accounting'
        auth = load(OUT / 'user-authorization.json')
        binding = load(OUT / 'authorization-binding.json')
        marker = load(OUT / 'execute-started.json')
        journal = [json.loads(line) for line in (OUT / 'dispatch-journal.jsonl').read_text('utf-8').splitlines()]
        before = load(OUT / 'ledger-before.json')
        after = load(OUT / 'ledger-after.json')
        assert auth['approved'] is True and auth['scope'] == ['G3']
        assert type(auth['max_calls']) is int and auth['max_calls'] == 1
        assert type(auth['max_reserved_units']) is int and auth['max_reserved_units'] == 200000000
        assert 'call_94350e33f3094a8abf7c84b2cf5549b1 item0' in auth['actual_user_approval_reference']
        assert auth['preview_file_sha256'] == digest((OUT / 'offline-preview-v1.json').read_bytes())
        assert auth['candidate_sha256'] == marker['candidate_sha256'] == result['candidate_sha256'] == preview['candidate_sha256']
        assert binding['authorization_sha256'] == marker['authorization_sha256'] == digest((OUT / 'user-authorization.json').read_bytes())
        assert len(journal) == 2 and [row['phase'] for row in journal] == ['before_dispatch', 'after_dispatch']
        assert all(row['case_id'] == 'G3' for row in journal)
        assert journal[0]['attempt_number'] == 1 and journal[0]['bound'] == exact['bound']
        assert journal[1]['usage'] == provider['usage'] and journal[1]['ledger_after'] == after
        assert before == exact['ledger_before']
        assert before['calls'] == 149 and after['calls'] == 150
        for value in (before, after):
            assert value['cap_units'] == 10000000000 and value['unknown_calls'] == 3
            assert value['pending_calls'] == 0 and value['frozen'] is False
            assert value['unknown_identity_sha256'] == 'b7490c5f157e75f973533e518a1e245c1ea0a3818318065c9c7ddf5e5b59085e'
        usage = provider['usage']
        assert usage['total_tokens'] == usage['prompt_tokens'] + usage['completion_tokens']
        assert 0 <= usage['prompt_cache_hit_tokens'] <= usage['prompt_tokens']
        assert before['charged_upper_units'] == 1142225520 and after['charged_upper_units'] == 1151630880
        budget_tree = ast.parse((ROOT / 'backend/app/ai/budget.py').read_text('utf-8'))
        constants = {node.targets[0].id: ast.literal_eval(node.value) for node in budget_tree.body
                     if isinstance(node, ast.Assign) and len(node.targets) == 1
                     and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Constant)}
        measured = ((usage['prompt_tokens'] - usage['prompt_cache_hit_tokens']) * constants['INPUT_MISS_UNITS']
                    + usage['prompt_cache_hit_tokens'] * constants['INPUT_HIT_UNITS']
                    + usage['completion_tokens'] * constants['OUTPUT_UNITS'])
        assert after['charged_upper_units'] - before['charged_upper_units'] == measured == 9405360
        assert provider['cost_upper_cny'] == measured / 1e9
        assert provider['requested_model'] == 'deepseek-flash'
        assert provider['reported_model'] in {'deepseek-flash', 'deepseek-v4.1-flash', 'DeepSeek-V4.1-Flash', 'deepseek-v4.1-flash-1017', 'DeepSeek-V4.1-Flash-1017'}
        assert provider['finish_reason'] == 'stop'
        assert result['sum_reserved_upper_cny'] == .162584 and result['maximum_reserved_upper_cny'] == .20
        assert result['automatic_retries'] == 0 and result['finalization_failures'] == [] and result['stopped_reason'] is None
        assert not result['companion_invoked'] and not result['evaluation_invoked'] and not result['real_api_save_restore_tested']
        assert auth['recorded_utc'] < marker['utc'] < journal[0]['utc'] < journal[1]['utc'] < result['end_utc']

        stage = 'closed_player_public_prose_derivation'
        slot_by_id = {slot.object_id: slot for slot in blueprint.objects}
        puzzle_by_id = {p.puzzle_id: p for p in blueprint.puzzles}
        # Do not merge source dicts or serialize the private definition. These
        # literal field selections are the entire prose publication allowlist.
        prose_rooms = []
        for room in definition.rooms:
            public_objects = []
            for obj in room.objects:
                slot = slot_by_id[obj.object_id]
                assert obj.kind in {'item', 'clue', 'puzzle'}
                mechanism = puzzle_by_id[slot.reference_id].mechanism if obj.kind == 'puzzle' else None
                assert mechanism in {None, 'code', 'sequence', 'circuit', 'item'}
                public_objects.append({'AI_name': obj.name, 'Host_base_description': obj.description,
                    'trusted_kind': obj.kind, 'trusted_role': slot.role, 'trusted_mechanism': mechanism})
            prose_rooms.append({'AI_name': room.name, 'AI_atmosphere_description': room.description,
                                'objects': public_objects})
        prose = {'kind': 'DERIVED_PLAYER_PUBLIC_PROSE_ALLOWLIST_NOT_RAW_MODEL_REPLY',
            'original_model_content_raw_sha256': provider['content_raw_sha256'],
            'gates': {'admitted': True, 'raw_hash_matches': True, 'strict_schema2_valid': True,
                      'saved_definition_matches_declared_assembly': True},
            'AI_title': content['title'], 'AI_story': content['story'], 'rooms': prose_rooms,
            'scope': 'Fictional player prose in its proper room context, not a current-stage all-rooms model input; no facts/parameters/answers/actions/state.'}
        local_paths = [provider_path, definition_path, witness_path, trace_path]
        raw_name_fields_match = all(objects[key].name == value['name'] for key, value in content['objects'].items())
        item_fact = next(p for p in blueprint.puzzles if p.mechanism == 'item')
        device_source = next(obj for obj in blueprint.objects if obj.role == 'device_source')
        source_symbols = content['parameters']['sequence_symbols']
        mapped_devices = [content['parameters']['device_map'][symbol] for symbol in source_symbols]
        summary = {'kind': 'Independent AI QA local audit; counts/bools/hashes only', 'exit_code': 0,
            'source_count': 455, 'source_bundle_sha256': preview['candidate_sha256'],
            'sources_before_after_match': True, 'raw_content_sha256': provider['content_raw_sha256'],
            'schema2_valid': True, 'local_finite_guard_revision1_passed': True, 'reverse_blueprint_id': blueprint.blueprint_id,
            'actual_solved_mechanism_order': actual_mechanism_order,
            'relation_hidden_before_and_visible_after_first_item_in_G1': True,
            'observed_relation_gate_state_checks': len(relation_gate_checks),
            'saved_room_object_counts': [len(room.objects) for room in definition.rooms], 'exact_objects': 14, 'required_extra_objects_present': 4,
            'accepted_model_names_preserved_exactly': raw_name_fields_match,
            'Host_descriptions_equal_declared_assembly': True, 'definition_hash': compiled.definition_hash,
            'saved_witness_actions': 33, 'memory_state_hashes_matched': matched,
            'initial_state_hash_matches': True, 'final_full_projection_matches': True,
            'recorded_metadata_reused_only_for_hash_comparison': ['session/level identifiers', 'generation', 'started_at/finished_at', 'save projection'],
            'final_status': 'won', 'final_room': 'EXIT', 'puzzles_solved': len(state.solved_puzzle_ids),
            'clues_discovered': len(state.discovered_clue_ids), 'discovery_gate_context_counts': gate_checks,
            'required_item_resolved_by_actual_reference': item_fact.required_item_id == key_object.item_id,
            'item_target_contains_exact_generated_item_name': key_object.name in item_target.description,
            'use_item_inventory_unchanged_and_consumed_empty': uses == [True],
            'required_item_retained_at_EXIT': key_object.item_id in state.inventory,
            'no_return_action_in_original_tools': 'return' not in generated.TOOL_MODELS,
            'device_source_description_names_symbol_source': '符号源序' in objects[device_source.object_id].description,
            'Host_description_has_no_alphabetical_order_instruction': not any('按字母' in obj.description or '字母序' in obj.description for obj in objects.values()),
            'source_symbols_are_alphabetical': source_symbols == sorted(source_symbols),
            'mapped_devices_are_alphabetical': mapped_devices == sorted(mapped_devices),
            'usage': {key: usage[key] for key in ('prompt_tokens', 'completion_tokens', 'total_tokens', 'prompt_cache_hit_tokens')},
            'usage_upper_cny': measured / 1e9, 'reserved_upper_cny': .162584,
            'saved_calls_before_after': [before['calls'], after['calls']],
            'saved_charged_upper_units_before_after': [before['charged_upper_units'], after['charged_upper_units']],
            'old_unknown_identity_unchanged': True, 'pending': 0, 'frozen': False, 'finalization_failures': [],
            'actual_payload_equals_approved_preview': True, 'authorization_marker_journal_binding': True,
            'attempts': 1, 'remaining_paid_authorization': 0,
            'automatic_settlement': {'elapsed_seconds': end['settlement']['elapsed_seconds'], 'rating': end['settlement']['rating'], 'human_timing_or_difficulty_evidence': False},
            'opaque_api_body_hash_limitation': 'Full event-id-bearing HTTP response bodies were not retained; per-step opaque body hashes not independently reconstructed. Saved status/state hash chain checked.',
            'new_HTTP_compile_solve_prove_provider_network_DB_config_or_Key_access': 0,
            'pure_typed_derive_for_saved_replay_only': True,
            'local_private_sha256': {path.relative_to(ROOT).as_posix(): digest(path.read_bytes()) for path in local_paths},
            'local_private_originals_not_publication_artifacts': True,
            'closed_prose_allowlist_only_no_parameters_clues_answers_witness_projection_output': True}
        assert all(digest((ROOT / name).read_bytes()) == value for name, value in preview['source'].items())
        assert digest(provider_path.read_bytes()) == provider_original_sha256
        private_ignore = subprocess.run(['git', 'check-ignore', '--', *[path.relative_to(ROOT).as_posix() for path in local_paths]], capture_output=True, text=True, encoding='utf-8')
        assert private_ignore.returncode == 0 and set(private_ignore.stdout.splitlines()) == {path.relative_to(ROOT).as_posix() for path in local_paths}
        write('player-public-prose-derived.json', prose)
        write('local-audit.json', summary)
        print(json.dumps({'exit_code': 0, 'objects': 14, 'memory_state_hashes_matched': matched,
            'usage_upper_cny': measured / 1e9, 'local_private_originals': 4,
            'prose_derivative_sha256': digest((QA / 'player-public-prose-derived.json').read_bytes()),
            'local_audit_sha256': digest((QA / 'local-audit.json').read_bytes())}))
        return 0
    except BaseException as error:
        # No traceback, exception payload or private local variables are emitted.
        print(json.dumps({'exit_code': 1, 'stage': stage, 'error_type': type(error).__name__}))
        return 1


if __name__ == '__main__':
    raise SystemExit(audit())
