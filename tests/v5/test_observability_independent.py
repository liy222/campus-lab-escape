"""One independent input-variation check; only synthetic TEMP fixture data."""
import json
import os
from pathlib import Path

from scripts.generation_trace import read_trace


def test_two_actual_request_scales_have_distinct_counts_without_rewriting_prior_records(actor, system):
    app, generator = system
    db = app.state.v5_database
    first_theme = 'Synthetic variation A'
    second_theme = '合成输入规模不同🌧'
    first = actor.generate(1, 'easy', theme=first_theme)
    assert first['status'] == 'ready'
    first_trace = read_trace(db.path, first['job_id'])
    with db.transaction() as connection:
        prior_events = [tuple(row) for row in connection.execute(
            'SELECT * FROM generation_job_events WHERE job_id=? ORDER BY event_id', (first['job_id'],))]
        prior_definition = tuple(connection.execute(
            'SELECT definition_json,metadata_json FROM generated_levels WHERE level_id=?', (first['level_id'],)).fetchone())
    second = actor.generate(2, 'normal', theme=second_theme)
    assert second['status'] == 'ready' and first['job_id'] != second['job_id']
    second_trace = read_trace(db.path, second['job_id'])
    for trace, theme, rooms, rank, puzzles in [
            (first_trace, first_theme, 1, 1, 2),
            (second_trace, second_theme, 2, 2, 4)]:
        assert [event['stage'] for event in trace['events']] == ['pending', 'generating', 'validating', 'ready']
        actual = trace['events'][0]['counts']
        assert actual == {'theme_characters': len(theme), 'theme_utf8_bytes': len(theme.encode('utf-8')),
                          'requested_rooms': rooms, 'difficulty_rank': rank}
        assert trace['events'][-1]['counts']['rooms'] == rooms
        assert trace['events'][-1]['counts']['puzzles'] == puzzles
        assert trace['events'][-1]['counts']['witness_steps'] > 0
        rendered = json.dumps(trace, ensure_ascii=False)
        assert theme not in rendered
        assert actor.client.cookies.get('campus_v5_session') not in rendered
    assert first_trace['events'][0]['counts'] != second_trace['events'][0]['counts']
    assert first_trace['events'][-1]['counts'] != second_trace['events'][-1]['counts']
    assert {event['event_id'] for event in first_trace['events']}.isdisjoint(
        event['event_id'] for event in second_trace['events'])
    assert read_trace(db.path, first['job_id']) == first_trace
    with db.transaction() as connection:
        assert [tuple(row) for row in connection.execute(
            'SELECT * FROM generation_job_events WHERE job_id=? ORDER BY event_id', (first['job_id'],))] == prior_events
        assert tuple(connection.execute(
            'SELECT definition_json,metadata_json FROM generated_levels WHERE level_id=?', (first['level_id'],)).fetchone()) == prior_definition
    assert len(generator.calls) == 2
    output = os.environ.get('EVALUATION_OBSERVABILITY_QA_OUTPUT')
    if output:
        directory = Path(output).resolve()
        directory.relative_to(Path(__file__).resolve().parents[2] / 'evidence/upgrade/v5.0/evaluation-observability-20261028')
        directory.mkdir(parents=True, exist_ok=True)
        observations = []
        for trace, theme, rooms, rank, puzzles in [
                (first_trace, first_theme, 1, 1, 2),
                (second_trace, second_theme, 2, 2, 4)]:
            observations.append({
                'run_id': trace['run_id'],
                'input': {'theme_text_recorded': False, 'theme_characters': len(theme),
                          'theme_utf8_bytes': len(theme.encode('utf-8')),
                          'requested_rooms': rooms, 'difficulty_rank': rank},
                'expected': {'stages': ['pending', 'generating', 'validating', 'ready'],
                             'final_rooms': rooms, 'final_puzzles': puzzles},
                'actual': {'current_status': trace['current_status'], 'recorded': trace['recorded'],
                           'source': trace['events'][0]['source'],
                           'events': [{key: event[key] for key in ('event_id', 'recorded_at', 'stage', 'reason', 'counts')}
                                      for event in trace['events']]},
            })
        with (directory / 'two-input-generation-traces.json').open('x', encoding='utf-8') as handle:
            json.dump({'kind': 'Actual API stages using two Synthetic TEMP inputs',
                       'synthetic_generator': True, 'paid_calls': 0, 'observations': observations},
                      handle, ensure_ascii=False, indent=2)
            handle.write('\n')
