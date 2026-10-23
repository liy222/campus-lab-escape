"""Saved real-round2 diagnosis only; no executor/provider/database import."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

from jsonschema import Draft202012Validator
from pydantic import ValidationError
from backend.app.ai.companion import looks_like_solution
from backend.app.ai.v5 import validate_reply
from backend.app.domain.generated import Draft, GeneratedRules, canonical, compile_level, derive, strict_json

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'evidence/upgrade/v5.0/real-samples-round2'


def read(name):
    return json.loads((BASE / name).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify(call):
    try:
        return 'ADMITTED', call()
    except ValidationError as error:
        return [{'location': list(item['loc']), 'type': item['type']} for item in error.errors()], None
    except ValueError as error:
        return str(error), None


def static_observations(draft, difficulty):
    clues = {clue.clue_id: clue for clue in draft.clues}
    puzzles = {puzzle.puzzle_id: puzzle for puzzle in draft.puzzles}
    rooms = {room.room_id: index for index, room in enumerate(draft.rooms)}
    clue_rooms = {obj.clue_id: rooms[room.room_id] for room in draft.rooms for obj in room.objects if obj.kind == 'clue'}
    item_rooms = {obj.item_id: rooms[room.room_id] for room in draft.rooms for obj in room.objects if obj.kind == 'item'}
    violations = []
    recipes = []
    for room in draft.rooms:
        for obj in room.objects:
            if set(obj.locked_by) - set(puzzles):
                violations.append({'category': 'UNKNOWN_REFERENCE', 'object_id': obj.object_id,
                    'invalid_locked_by_ids': sorted(set(obj.locked_by) - set(puzzles)),
                    'reason': 'locked_by must reference puzzle IDs, not an item ID'})
    cross = False
    combos = 0
    for puzzle in draft.puzzles:
        current = rooms[puzzle.room_id]
        cross |= any(clue_rooms[cid] != current for cid in puzzle.clue_ids)
        cross |= puzzle.required_item_id in item_rooms and item_rooms[puzzle.required_item_id] != current
        if puzzle.mechanism in {'code', 'sequence'}:
            combos += len(puzzle.clue_ids) >= 2
            result, answer = classify(lambda: derive(puzzle, clues))
            selected = [clues[cid] for cid in puzzle.clue_ids]
            tokens = [token for clue in selected for token in clue.tokens]
            mapping = {symbol: value for clue in selected for symbol, value in clue.symbol_map.items()}
            recipes.append({'puzzle_id': puzzle.puzzle_id, 'mechanism': puzzle.mechanism,
                'recipe': puzzle.recipe, 'result': result, 'flattened_token_count': len(tokens),
                'unmapped_token_count': sum(token not in mapping for token in tokens) if puzzle.recipe == 'symbol_map' else None})
            if result != 'ADMITTED':
                violations.append({'category': result, 'puzzle_id': puzzle.puzzle_id,
                    'reason': 'selected symbol sources are missing or unmapped' if result == 'INSUFFICIENT_FACTS' else 'recipe fails admission'})
            if puzzle.mechanism == 'sequence' and puzzle.recipe == 'symbol_map' and len(tokens) != 4:
                violations.append({'category': 'INVALID_SEQUENCE_SHAPE', 'puzzle_id': puzzle.puzzle_id,
                    'flattened_token_count': len(tokens), 'required_count': 4,
                    'reason': 'Even supplying missing mappings would preserve this token count; no modified real draft was tested or accepted'})
    minimum = {'easy': 0, 'normal': 1, 'hard': 2}[difficulty]
    if combos < minimum:
        violations.append({'category': 'COMBINATION_COUNT', 'observed': combos, 'minimum': minimum})
    if len(draft.rooms) > 1 and not cross:
        violations.append({'category': 'CROSS_ROOM_REQUIRED', 'reason': 'All selected materials/items serve only same-room puzzles'})
    return {'recipe_checks': recipes, 'independent_observed_violations': violations,
        'two_material_puzzles': combos, 'cross_room_material_dependency': cross}


def main():
    result = read('result.json')
    source_before = {name: sha(ROOT / name) for name in result['source_after']}
    assert source_before == result['source_after'], 'Source changed since the actual paid run'
    cases = []
    compiled_g1 = None
    for cid, rooms, difficulty in [('G1', 1, 'easy'), ('G2', 2, 'normal'), ('G3', 3, 'hard')]:
        saved = read(cid + '-provider-result.json')
        raw = strict_json(saved['content_redacted'])
        draft = Draft.model_validate(raw)
        Draft202012Validator(Draft.model_json_schema()).validate(raw)
        category, compiled = classify(lambda: compile_level(raw, rooms, difficulty))
        row = {'case_id': cid, 'draft_schema_valid': True,
            'requested_shape_matches': len(draft.rooms) == rooms and len(draft.puzzles) == min(6, rooms + {'easy': 1, 'normal': 2, 'hard': 3}[difficulty]),
            'actual_first_compile_result': category, **static_observations(draft, difficulty),
            'campus_surface_theme': 'Library closing patrol' if cid == 'G1' else 'Astronomy club records handover' if cid == 'G2' else 'Ecology laboratory specimen handover',
            'art_scope': 'Fixed neutral catalog backgrounds and existing object sprites; no new AI art'}
        if compiled:
            rules = GeneratedRules(compiled)
            state = rules.initial_state()
            for action in compiled.witness:
                state, _ = rules.apply_action(state, action['tool'], action['arguments'])
            record = read(cid + '-api-result.json')
            row.update(independent_memory_replay_won=state.status == 'won',
                replay_room_id=state.room_id, witness_actions=len(compiled.witness),
                definition_hash=compiled.definition_hash,
                witness_sha256=hashlib.sha256(canonical(compiled.witness).encode()).hexdigest(),
                main_actual_HTTP_replay_record_matches=(record['definition_hash'] == compiled.definition_hash
                    and record['witness_sha256'] == hashlib.sha256(canonical(compiled.witness).encode()).hexdigest()
                    and record['witness_actions'] == len(compiled.witness) == 8
                    and record['settlement']['puzzles_solved'] == record['settlement']['puzzles_total'] == 2))
            compiled_g1 = compiled
        cases.append(row)
    stage = read('companion-actual-stage.json')['visible_state']
    a1_saved = read('A1-provider-result.json')
    a1 = strict_json(a1_saved['content_redacted'])
    context = json.loads(read('A1-exact-payload.json')['payload']['messages'][-1]['content'])
    traced = []

    def trace(frame, event, arg):
        if frame.f_code is validate_reply.__code__ and event == 'exception':
            traced.append({'line': frame.f_lineno, 'exception': str(arg[1])})
        return trace

    previous_trace = sys.gettrace()
    try:
        sys.settrace(trace)
        a1_category, _ = classify(lambda: validate_reply(stage, a1, context['question'], context['recent_history']))
    finally:
        sys.settrace(previous_trace)
    known = {clue['clue_id'] for clue in stage['clues']}
    ids = {obj['object_id'] for obj in stage['objects']} | known
    offending = sorted(ident for ident in ids if len(ident) > 3 and ident in a1['answer'])
    names = {obj.clue_id: obj.name for room in compiled_g1.draft.rooms for obj in room.objects if obj.kind == 'clue'}
    changed = copy.deepcopy(a1)
    for ident in offending:
        changed['answer'] = changed['answer'].replace(ident, names.get(ident, '已发现材料'))
    counterfactual, _ = classify(lambda: validate_reply(stage, changed, context['question'], context['recent_history']))
    before_ai = read('companion-actual-stage.json')['visible_state']
    after_ai = read('A1-api-result.json')['response']['visible_state']
    preserved_fields = ['definition_hash', 'room_id', 'inventory', 'objects', 'clues', 'observed_object_ids', 'exits', 'minigames', 'status']
    no_full_answer = all(answer not in a1['answer'] if isinstance(answer, str) else
        all(separator.join(answer) not in a1['answer'] for separator in ['', '、', ',', ' → '])
        for answer in compiled_g1.answers.values())
    a1_review = {'actual_http_status': read('A1-api-result.json')['api_status'],
        'actual_error': 'MODEL_INVALID_OUTPUT', 'pure_memory_guard': a1_category,
        'traced_exception': traced, 'offending_public_clue_ids': offending,
        'clue_refs_allowed': set(a1['clue_refs']) <= set(context['allowed_clue_refs']) <= known,
        'known_titles_contain_ids': all(any(ident in clue.get('title', '') for clue in context['known_evidence']) for ident in offending),
        'looks_like_solution': looks_like_solution(a1['answer']), 'complete_compiled_answer_absent': no_full_answer,
        'history_kind_counts': {kind: sum(item.get('kind') == kind for item in context['recent_history']) for kind in {'action', 'dialogue'}},
        'gameplay_projection_preserved_after_failure': all(before_ai[field] == after_ai[field] for field in preserved_fields),
        'in_memory_public_name_substitution_only': counterfactual,
        'raw_not_modified_or_delivered': True,
        'independent_public_fact_review': 'The index relation matches the observed puzzle rule and both discovered clue materials; no unsupported object/state/action claim was found. Reply is concise natural Chinese but includes machine IDs copied from public labels.',
        'minimum_fix_recommendation': 'Use the discovered clue object names in public clue titles and ordered-material description. Keep IDs only for machine clue_refs and retain existing no-full-answer/internal-ID-prose validation.'}
    preview = read('offline-preview-v1.json')
    payload_checks = []
    usage_sum_units = 0
    for cid in result['attempted_case_ids']:
        exact = read(cid + '-exact-payload.json')
        body = exact['payload']
        encoded = json.dumps(body, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
        upper_units = (len(encoded) * 4 + 8192) * 2000 + body['max_tokens'] * 8000
        assert exact['bound']['payload_sha256'] == hashlib.sha256(encoded).hexdigest()
        assert exact['bound']['cost_upper_units'] == upper_units <= (50_000_000 if cid == 'A1' else 200_000_000)
        if cid != 'A1':
            assert body == next(case['payload'] for case in preview['generation_cases'] if case['case_id'] == cid)
        saved = read(cid + '-provider-result.json')
        usage = saved['usage']
        assert usage['total_tokens'] == usage['prompt_tokens'] + usage['completion_tokens']
        units = (usage['prompt_tokens'] - usage.get('prompt_cache_hit_tokens', 0)) * 2000 + usage.get('prompt_cache_hit_tokens', 0) * 40 + usage['completion_tokens'] * 8000
        usage_sum_units += units
        assert units / 1e9 == saved['cost_upper_cny'] and saved['secret_detected'] is False
        assert hashlib.sha256(saved['content_redacted'].encode()).hexdigest() == saved['content_raw_sha256']
        payload_checks.append({'case_id': cid, 'full_payload_bytes': len(encoded),
            'reserved_upper_units': upper_units, 'actual_usage_upper_units': units,
            'requested_model': saved['requested_model'], 'reported_model': saved['reported_model'],
            'finish_reason': saved['finish_reason'], 'secret_detected_by_controller': saved['secret_detected']})
    ledger_before, ledger_after = read('ledger-before.json'), read('ledger-after.json')
    assert usage_sum_units == ledger_after['charged_upper_units'] - ledger_before['charged_upper_units']
    assert ledger_after['calls'] - ledger_before['calls'] == 4
    sensitive_pattern = re.compile(r'''(?:<Cookie\s+\S+=\S+|Bearer\s+[A-Za-z0-9_.~-]{20,}|["'](?:csrf_token|auth_context|password|api_key|session_token)["']\s*:\s*["'][A-Za-z0-9_.~-]{16,}["'])''', re.I)
    sensitive_hits = []
    artifact_paths = sorted(BASE.glob('*.json')) + sorted(BASE.glob('*.jsonl'))
    for path in artifact_paths:
        if sensitive_pattern.search(path.read_text(encoding='utf-8-sig')):
            sensitive_hits.append(path.name)
    source_after = {name: sha(ROOT / name) for name in source_before}
    report = {'kind': 'independent_read_only_real_round2_review', 'utc': datetime.now(timezone.utc).isoformat(),
        'review_command': 'PYTHONPATH=. python -B -X utf8 evidence/upgrade/v5.0/qa/review_real_round2.py',
        'review_exit_code': 0, 'original_actual_execute_exit_code': result['exit_code'],
        'source_before': source_before, 'source_after': source_after,
        'source_matches_actual_execute': source_before == result['source_after'], 'source_unchanged': source_before == source_after,
        'cases': cases, 'A1': a1_review, 'A2': 'SKIPPED_A1_NOT_SUCCESSFUL_NO_PAID_RETRY',
        'actual_main_calls': result['attempted_case_ids'], 'actual_main_admitted_generation_samples': 1,
        'payload_usage_checks': payload_checks,
        'sum_reserved_upper_cny': sum(item['reserved_upper_units'] for item in payload_checks) / 1e9,
        'actual_usage_upper_increment_cny': usage_sum_units / 1e9,
        'old_unknown_identity_unchanged': ledger_before['unknown_identity_sha256'] == ledger_after['unknown_identity_sha256'],
        'unknown_count_before_after': [ledger_before['unknown_calls'], ledger_after['unknown_calls']],
        'pending_after': ledger_after['pending_calls'], 'frozen_after': ledger_after['frozen'],
        'saved_artifact_secret_pattern_hits_without_values': sensitive_hits,
        'qa_provider_calls': 0, 'qa_network_calls': 0, 'qa_credential_reads': 0, 'qa_database_access': False,
        'artifact_sha256': {str(path.relative_to(ROOT)).replace('\\', '/'): sha(path) for path in artifact_paths},
        'limits': ['One real 1/easy sample admitted and actual Main HTTP-replayed; independent QA replay is in memory only, not another HTTP run.',
            'G2/G3 remain rejected; no solver-limit classification or repair of stored real drafts. Listed downstream violations are independent structural/recipe observations, not accepted edited samples.',
            'A1 was blocked and never delivered; A2 skipped, so no successful real companion/history-continuity claim.',
            'QA did not read the credential: no-value secret-pattern review plus executor secret checks do not constitute a universal credential audit.',
            'First combined inline diagnosis cffb95 exited1 on a QA Pydantic-object .get typo after G2/G3 classification; corrected A1 guard diagnosis 0cd8e0 exited0. No source/raw change.',
            'Original round1 0/3 and earlier sealed evidence remain unchanged. This round is not a whole-suite rerun or overall release acceptance.']}
    assert source_before == source_after == result['source_after']
    assert cases[0]['main_actual_HTTP_replay_record_matches'] and a1_category == 'COMPANION_CONTENT'
    assert counterfactual == 'ADMITTED' and not sensitive_hits
    out = Path(__file__).with_name('real-round2-independent-review.json')
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'review_exit_code': 0, 'main_execute_exit_code': result['exit_code'],
        'actual_main_calls': result['attempted_case_ids'], 'admitted_generations': 1,
        'A1_guard': a1_category, 'actual_usage_upper_increment_cny': usage_sum_units / 1e9,
        'source_unchanged': True, 'output': str(out.relative_to(ROOT)), 'sha256': sha(out)}))


if __name__ == '__main__':
    main()
