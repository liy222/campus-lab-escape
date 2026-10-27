"""Finish only accounting/prose after the preserved successful replay checkpoint.

No GeneratedRules replay, derive, compile, solve, HTTP or model dispatch here.
Only this sample's four local originals may be machine-read, never printed.
"""
from __future__ import annotations
import ast
import hashlib
import importlib.abc
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parents[1]
QA = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def load(path): return json.loads(path.read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
def deny(*args, **kwargs): raise RuntimeError('FINISH_ONLY_FORBIDDEN_RUNTIME')
def write(name, value):
    with (QA / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


class NoServices(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('backend.app.ai', 'backend.app.storage', 'backend.app.api')) or fullname == 'backend.app.main':
            return deny()
        return None


def main():
    sys.meta_path.insert(0, NoServices())
    socket.socket.connect = socket.socket.connect_ex = socket.create_connection = deny
    sqlite3.connect = deny
    checkpoint = load(QA / 'first-local-audit-attempt.json')
    assert checkpoint['local_helper_exit_code'] == 1
    assert sha(QA / 'audit_actual.py') == checkpoint['executed_helper_sha256']
    preview = load(OUT / 'offline-preview-v1.json')
    result = load(OUT / 'result.json'); api = load(OUT / 'G3-api-result.json')
    exact = load(OUT / 'G3-exact-payload.json')
    assert result['exit_code'] == 0 and result['cases'] == [api] and api['status'] == 'ready_and_replayed'
    assert len(preview['source']) == 455 and result['source_after'] == preview['source']
    assert all(sha(ROOT / p) == d for p, d in preview['source'].items())
    assert exact['payload'] == preview['generation_cases'][0]['payload'] and exact['bound'] == preview['generation_cases'][0]['bound']
    auth = load(OUT / 'user-authorization.json'); marker = load(OUT / 'execute-started.json'); binding = load(OUT / 'authorization-binding.json')
    journal = [json.loads(line) for line in (OUT / 'dispatch-journal.jsonl').read_text(encoding='utf-8').splitlines()]
    assert auth['approved'] is True and auth['scope'] == ['G3'] and type(auth['max_calls']) is int and auth['max_calls'] == 1
    assert auth['max_reserved_units'] == 200000000 and 'call_94350e33f3094a8abf7c84b2cf5549b1 item0' in auth['actual_user_approval_reference']
    assert auth['preview_file_sha256'] == sha(OUT / 'offline-preview-v1.json')
    assert auth['candidate_sha256'] == marker['candidate_sha256'] == preview['candidate_sha256']
    assert binding['authorization_sha256'] == marker['authorization_sha256'] == sha(OUT / 'user-authorization.json')
    assert len(journal) == 2 and [j['phase'] for j in journal] == ['before_dispatch', 'after_dispatch']
    assert auth['approved_utc'] < marker['utc'] < journal[0]['utc'] < journal[1]['utc'] < result['end_utc']
    assert journal[0]['attempt_number'] == 1 and journal[0]['bound'] == exact['bound']
    provider_path = OUT / 'G3-provider-result.json'
    definition_path = OUT / 'raw-sensitive/G3-private-definition-local.json'
    witness_path = OUT / 'raw-sensitive/G3-witness-local.json'
    trace_path = OUT / 'raw-sensitive/G3-api-replay-local.json'
    private = [provider_path, definition_path, witness_path, trace_path]
    ignored = subprocess.run(['git', 'check-ignore', '--', *[p.relative_to(ROOT).as_posix() for p in private]], capture_output=True, text=True, encoding='utf-8')
    assert ignored.returncode == 0 and set(ignored.stdout.splitlines()) == {p.relative_to(ROOT).as_posix() for p in private}
    provider = load(provider_path); raw = provider['content_redacted']
    assert not provider['secret_detected'] and hashlib.sha256(raw.encode()).hexdigest() == provider['content_raw_sha256']
    from backend.app.domain import generated, generation_content_v2 as v2
    generated.derive = generated.compile_level = generated.solve = generated.GeneratedRules.apply_action = deny
    bp = v2.select_blueprint(3, 'hard', seed=3)
    content = generated.strict_json(raw)
    assert v2.v1._IntegerValidator(v2.content_schema(bp)).is_valid(content)
    normalized = generated.Draft.model_validate(v2.assemble_draft(bp, raw)).model_dump()
    saved = load(definition_path)['definition']
    assert normalized == saved['draft'] and saved['definition_hash'] == api['definition_hash'] == '5371808d6549df60336bff859b89556649822465a902716427bff7ff3a33e948'
    witness = load(witness_path)['witness']; trace = load(trace_path)
    assert len(witness) == len(trace['steps']) == api['witness_actions'] == 33
    assert hashlib.sha256(canonical(witness).encode()).hexdigest() == api['witness_sha256']
    assert all(step['http_status'] == 200 and step['index'] == i and step['tool'] == action['tool'] for i, (action, step) in enumerate(zip(witness, trace['steps'])))
    # Extract coverage from the already accepted witness's finite reference
    # chronology. This does not apply a domain action or compare states again.
    observed = set(); discovered = set(); solved = set(); room = bp.room_ids[0]
    by_object = {o.object_id: o for o in bp.objects}; puzzles = {p.puzzle_id: p for p in bp.puzzles}
    coverage = {'unobserved': 0, 'observed_partial': 0, 'observed_complete': 0}
    order = []
    def count_context():
        for obj in bp.objects:
            if obj.kind != 'puzzle' or obj.room_id != room or not set(obj.locked_by) <= solved:
                continue
            p = puzzles[obj.reference_id]
            if p.mechanism not in ('code', 'sequence'): continue
            key = 'unobserved' if obj.object_id not in observed else 'observed_complete' if set(p.clue_ids) <= discovered else 'observed_partial'
            coverage[key] += 1
    count_context()
    for action in witness:
        args = action['arguments']; tool = action['tool']
        if tool == 'inspect':
            obj = by_object[args['object_id']]; observed.add(obj.object_id)
            if obj.kind == 'clue': discovered.add(obj.reference_id)
        elif tool == 'move': room = args['destination_id']
        elif tool in ('use_item', 'submit_code', 'submit_sequence', 'submit_circuit'):
            pid = args['target_id']; solved.add(pid); order.append(puzzles[pid].mechanism)
        count_context()
    assert order == ['item', 'sequence', 'code', 'circuit', 'sequence', 'code']
    end = trace['final_visible_state']
    assert end['status'] == 'won' and end['room_id'] == room == 'EXIT' and trace['complete']
    before = load(OUT / 'ledger-before.json'); after = load(OUT / 'ledger-after.json'); usage = provider['usage']
    assert before == exact['ledger_before'] and after == journal[1]['ledger_after'] and usage == journal[1]['usage']
    assert before['calls'] == 149 and after['calls'] == 150
    for snapshot in (before, after):
        assert snapshot['cap_units'] == 10000000000 and snapshot['unknown_calls'] == 3 and snapshot['pending_calls'] == 0 and snapshot['frozen'] is False
        assert snapshot['unknown_identity_sha256'] == 'b7490c5f157e75f973533e518a1e245c1ea0a3818318065c9c7ddf5e5b59085e'
    tree = ast.parse((ROOT / 'backend/app/ai/budget.py').read_text(encoding='utf-8'))
    rates = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and isinstance(n.value, ast.Constant)}
    measured = (usage['prompt_tokens'] - usage['prompt_cache_hit_tokens']) * rates['INPUT_MISS_UNITS'] + usage['prompt_cache_hit_tokens'] * rates['INPUT_HIT_UNITS'] + usage['completion_tokens'] * rates['OUTPUT_UNITS']
    assert measured == 9405360 == after['charged_upper_units'] - before['charged_upper_units']
    assert provider['cost_upper_cny'] == measured / 1e9 and result['sum_reserved_upper_cny'] == .162584
    assert result['automatic_retries'] == 0 and result['finalization_failures'] == [] and result['stopped_reason'] is None
    assert not result['real_api_save_restore_tested'] and not result['companion_invoked'] and not result['evaluation_invoked']
    assert provider['requested_model'] == 'deepseek-flash' and provider['reported_model'] in {'deepseek-flash', 'deepseek-v4.1-flash', 'DeepSeek-V4.1-Flash', 'deepseek-v4.1-flash-1017', 'DeepSeek-V4.1-Flash-1017'} and provider['finish_reason'] == 'stop'
    slot_by_id = {o.object_id: o for o in bp.objects}
    prose_rooms = []
    for row in normalized['rooms']:
        prose_objects = []
        for obj in row['objects']:
            slot = slot_by_id[obj['object_id']]
            mechanism = puzzles[slot.reference_id].mechanism if obj['kind'] == 'puzzle' else None
            assert obj['kind'] in {'item', 'clue', 'puzzle'} and mechanism in {None, 'code', 'sequence', 'circuit', 'item'}
            prose_objects.append({'AI_name': obj['name'], 'Host_base_description': obj['description'], 'trusted_kind': obj['kind'], 'trusted_role': slot.role, 'trusted_mechanism': mechanism})
        prose_rooms.append({'AI_name': row['name'], 'AI_atmosphere_description': row['description'], 'objects': prose_objects})
    prose = {'kind': 'DERIVED_PLAYER_PUBLIC_PROSE_ALLOWLIST_NOT_RAW_MODEL_REPLY',
        'original_model_content_raw_sha256': provider['content_raw_sha256'],
        'gates': {'admitted': True, 'raw_hash_matches': True, 'strict_schema2_valid': True, 'saved_definition_matches_declared_assembly': True},
        'AI_title': content['title'], 'AI_story': content['story'], 'rooms': prose_rooms,
        'scope': 'Fictional player-public prose only; not a stage-visible all-rooms model input, no facts/parameters/answers/witness/private projection.'}
    summary = {'kind': 'Local joint audit finish-only; first replay not repeated', 'exit_code': 0,
        'source_count': 455, 'source_bundle_sha256': preview['candidate_sha256'], 'current455_match': True,
        'definition_hash': api['definition_hash'], 'objects': 14, 'extra_clue_objects': 4,
        'first_local_attempt_exit_code': 1, 'first_attempt_checkpoint_sha256': sha(QA / 'first-local-audit-attempt.json'),
        'initial_33_step_final_hash_assertions_completed_in_first_attempt': True,
        'GeneratedRules_replay_or_derive_repeated_in_finish_helper': False,
        'actual_solved_mechanism_order': order, 'discovery_context_counts_from_saved_reference_chronology': coverage,
        'coverage_method': 'Counted from existing successful witness inspection/solve/room references, not a second GeneratedRules replay.',
        'authorization_time_field': 'approved_utc', 'chronology_and_preview_scope_binding_valid': True,
        'usage': {k: usage[k] for k in ('prompt_tokens', 'completion_tokens', 'total_tokens', 'prompt_cache_hit_tokens')},
        'usage_upper_cny': measured / 1e9, 'reserved_upper_cny': .162584,
        'calls_before_after': [149, 150], 'charged_upper_units_before_after': [before['charged_upper_units'], after['charged_upper_units']],
        'old_unknown_identity_unchanged': True, 'pending': 0, 'frozen': False, 'finalization_failures': [],
        'used_authorized_slots': 1, 'remaining_authorized_calls': 0,
        'automatic_settlement': {'elapsed_seconds': end['settlement']['elapsed_seconds'], 'rating': end['settlement']['rating'], 'human_difficulty_evidence': False},
        'opaque_full_HTTP_bodyhash_limitation': 'Original per-step full response bodies with event metadata were not saved, so those opaque hashes cannot be reconstructed. Initial/33state/final assertions completed in the first attempt.',
        'local_private_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in private},
        'private_originals_never_publication_artifacts': True, 'new_HTTP_model_compile_solve_proof_tests_build_UI_paid': 0}
    assert all(sha(ROOT / p) == d for p, d in preview['source'].items())
    write('player-public-prose-derived.json', prose)
    write('finish-audit-v1.json', summary)
    print(json.dumps({'exit_code': 0, 'first_attempt_exit_code': 1, 'new_state_replays': 0,
        'definition_hash': api['definition_hash'], 'actual_mechanism_order': order,
        'partial_contexts': coverage['observed_partial'], 'usage_upper_cny': measured / 1e9,
        'public_prose_sha256': sha(QA / 'player-public-prose-derived.json'), 'finish_audit_sha256': sha(QA / 'finish-audit-v1.json')}))


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        print(json.dumps({'exit_code': 1, 'error_class': type(error).__name__, 'raw_details_suppressed': True}))
        raise SystemExit(1)
