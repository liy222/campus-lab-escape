"""Read saved real responses only. Never import the executor, main, or a provider."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError
from backend.app.domain.generated import Draft, compile_level, derive, strict_json

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'evidence/upgrade/v5.0/real-samples'
OUT = Path(__file__).with_name('real-samples-independent-review.json')


def read(name):
    return json.loads((BASE / name).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rejection(call):
    try:
        call()
        return {'status': 'admitted'}
    except ValidationError as error:
        return {'status': 'rejected', 'category': 'DRAFT_SCHEMA',
                'errors': [{'location': list(item['loc']), 'type': item['type']}
                           for item in error.errors()]}
    except ValueError as error:
        return {'status': 'rejected', 'category': str(error)}


def main():
    sealed = json.loads((ROOT / 'evidence/upgrade/v5.0/qa/final-offline-result.json').read_text(encoding='utf-8-sig'))
    before = {name: sha(ROOT / name) for name in sealed['source_sha256']}
    cases = []
    for cid, count, difficulty in [('G1', 1, 'easy'), ('G2', 2, 'normal'), ('G3', 3, 'hard')]:
        saved = read(f'{cid}-provider-result.json')
        raw = strict_json(saved['content_redacted'])
        entry = {'case_id': cid, 'room_count': count, 'difficulty': difficulty,
                 'expected_puzzles': min(6, count + {'easy': 1, 'normal': 2, 'hard': 3}[difficulty]),
                 'actual_puzzles': len(raw['puzzles']),
                 'original_compile': rejection(lambda: compile_level(raw, count, difficulty)),
                 'requested_model': saved['requested_model'], 'reported_model': saved['reported_model'],
                 'finish_reason': saved['finish_reason'], 'usage': saved['usage'],
                 'cost_upper_cny': saved['cost_upper_cny'], 'secret_detected': saved['secret_detected'],
                 'content_hash_matches_saved': hashlib.sha256(saved['content_redacted'].encode()).hexdigest() == saved['content_raw_sha256']}
        # Inspect independent downstream violations. G2's forbidden ROOM field is
        # removed in this diagnostic copy only; original rejection stays intact.
        diagnostic = json.loads(json.dumps(raw))
        removed = []
        for index, room in enumerate(diagnostic['rooms']):
            for key in list(room):
                if key not in Draft.model_fields['rooms'].annotation.__args__[0].model_fields:
                    removed.append(['rooms', index, key])
                    del room[key]
        entry['diagnostic_only_removed_fields'] = removed
        draft = Draft.model_validate(diagnostic)
        rooms = {room.room_id: index for index, room in enumerate(draft.rooms)}
        clue_rooms = {obj.clue_id: index for index, room in enumerate(draft.rooms)
                      for obj in room.objects if obj.kind == 'clue'}
        item_rooms = {obj.item_id: index for index, room in enumerate(draft.rooms)
                      for obj in room.objects if obj.kind == 'item'}
        clues = {clue.clue_id: clue for clue in draft.clues}
        entry['recipe_checks'] = []
        entry['later_room_dependencies'] = []
        entry['reserved_exit_id_used'] = any(p.puzzle_id == 'EXIT' for p in draft.puzzles)
        for puzzle in draft.puzzles:
            if puzzle.mechanism in {'code', 'sequence'}:
                entry['recipe_checks'].append({'puzzle_id': puzzle.puzzle_id,
                    'mechanism': puzzle.mechanism, 'recipe': puzzle.recipe,
                    'result': rejection(lambda: derive(puzzle, clues))})
            elif puzzle.clue_ids:
                entry['recipe_checks'].append({'puzzle_id': puzzle.puzzle_id,
                    'mechanism': puzzle.mechanism,
                    'result': {'status': 'rejected', 'category': 'UNEXPECTED_FACTS'}})
            current = rooms[puzzle.room_id]
            later_clues = [cid for cid in puzzle.clue_ids if clue_rooms.get(cid, -1) > current]
            later_item = puzzle.required_item_id if item_rooms.get(puzzle.required_item_id, -1) > current else None
            if later_clues or later_item:
                entry['later_room_dependencies'].append({'puzzle_id': puzzle.puzzle_id,
                    'clue_ids': later_clues, 'item_id': later_item,
                    'classification': 'current room puzzle gates forward passage to required material'})
        entry['surface_theme_review'] = 'campus-specific fictional title/story/objects present; no playable acceptance'
        entry['surface_assets_review'] = 'only existing neutral backgrounds and object-art whitelist; no generated art claim'
        cases.append(entry)
    ledger_before, ledger_after = read('ledger-before.json'), read('ledger-after.json')
    result = read('result.json')
    after = {name: sha(ROOT / name) for name in before}
    artifacts = [f'{cid}-{kind}.json' for cid in ('G1', 'G2', 'G3')
                 for kind in ('provider-result', 'api-result', 'exact-payload')]
    artifacts += ['result.json', 'ledger-before.json', 'ledger-after.json',
                  'dispatch-journal.jsonl', 'execute-started.json']
    report = {'kind': 'independent_read_only_real_V5_sample_diagnosis',
        'utc': datetime.now(timezone.utc).isoformat(),
        'review_command': "PYTHONPATH=. C:\\Users\\liyh\\.conda\\envs\\1\\python.exe evidence/upgrade/v5.0/qa/review_real_samples.py",
        'review_exit_code': 0, 'original_execute_exit_code': result['exit_code'],
        'qa_provider_calls': 0, 'qa_network_calls': 0, 'qa_database_access': False,
        'actual_main_attempted_case_ids': result['attempted_case_ids'],
        'actual_main_generation_admitted': 0, 'companion_A1_A2': 'SKIPPED_NO_SUCCESSFUL_GENERATED_STAGE',
        'GEN01_acceptance': False, 'overall_release_acceptance': False,
        'automatic_retries': result['automatic_retries'], 'evaluation_invoked': result['evaluation_invoked'],
        'charged_upper_increment_cny': (ledger_after['charged_upper_units'] - ledger_before['charged_upper_units']) / 1_000_000_000,
        'ledger_call_increment': ledger_after['calls'] - ledger_before['calls'],
        'unknown_count_before_after': [ledger_before['unknown_calls'], ledger_after['unknown_calls']],
        'unknown_identity_unchanged': ledger_before['unknown_identity_sha256'] == ledger_after['unknown_identity_sha256'],
        'pending_after': ledger_after['pending_calls'], 'frozen_after': ledger_after['frozen'],
        'source_count': len(before), 'source_before': before, 'source_after': after,
        'source_unchanged': before == after,
        'source_matches_sealed_offline': before == sealed['source_sha256'],
        'current_vs_sealed_source_differences': [name for name in before if before[name] != sealed['source_sha256'][name]],
        'executed_generation_source_hash': result['source_after']['backend/app/ai/v5.py'],
        'domain_matches_actual_real_run': before['backend/app/domain/generated.py'] == result['source_after']['backend/app/domain/generated.py'],
        'raw_artifact_sha256': {str((BASE / name).relative_to(ROOT)).replace('\\', '/'): sha(BASE / name) for name in artifacts},
        'cases': cases,
        'root_cause': 'Actual model drafts violate declared DSL and semantic admission constraints before solver proof. Existing schema teaches shapes but does not encode request-specific count or recipe semantics; the system prompt gives insufficient precise recipe/forward-access constraints.',
        'minimum_recommendations': [
            'Add computed expected_puzzle_count to the request and explicit exactly-N instruction, retaining strict admission.',
            'Teach exact concat/index/symbol_map operations and compatible clue fields; code must derive 1-16 ASCII digits; sequence four distinct ASCII IDs.',
            'Specify no room locked_by field, no reserved EXIT identifiers, no clue_ids for item/circuit, and all necessary materials in same or earlier accessible room.',
            'Use saved failures for offline generator-message/semantic regression; never mutate these real outputs into successful samples and never relax validators.',
            'Any later real dispatch needs Main authorization and new concrete source-bound preview; no automatic retry.'],
        'limits': ['Three finite real generation samples only; all rejected; no real playable route, public stage or companion-history evaluation.',
                   'Raw provider text is already redacted by executor. QA records shapes, IDs and errors only, not private solution values.',
                   'First preliminary diagnostic command exited 1 after uncaught G2 Draft ValidationError; robust second inline classification exited 0. Neither changed source or original evidence.',
                   'Initial saved-report command exited1 on full-source assertion: Main AI source changed after the real run. This diagnosis binds unchanged compiler and saved exact real payloads, not the new AI source. Offline sealed evidence is untouched.',
                   'Read-only diagnosis completion exit0 is not generation acceptance. Offline joint evidence remains its separate historical scope.']}
    assert before == after
    assert report['domain_matches_actual_real_run']
    assert all(case['original_compile']['status'] == 'rejected' for case in cases)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'review_completed': True, 'original_execute_exit_code': result['exit_code'],
        'generation_admitted': 0, 'cases': [{k: c[k] for k in ('case_id', 'original_compile', 'later_room_dependencies')} for c in cases],
        'source_unchanged': True, 'output': str(OUT.relative_to(ROOT))}, ensure_ascii=True))


if __name__ == '__main__':
    main()
