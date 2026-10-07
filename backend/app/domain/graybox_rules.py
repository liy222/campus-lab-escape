"""Run statistics and two optional story observations over the v3.3 adapter."""
from datetime import datetime, timezone

from . import mini_rules as base
from .graybox_models import GrayboxState, HintRequest, RunStatistics
from .models import RuleError

SCHEMA_VERSION, LEVEL_VERSION = '1.4.0', '3.4.0'
state_model, tool_models, ai_request_model = GrayboxState, base.tool_models, HintRequest
game_fields = set(GrayboxState.model_fields) - {'revision', 'generation'}
OPTIONAL = {
    'r1_photo': {'clue_id': 'r1_photo_clue', 'object_id': 'r1_photo', 'title': '柜内旧相片',
                 'text': '凹槽里压着一张旧合照。照片背面写着：“最后离开的人，请记得让实验室恢复安静。”'},
    'r2_service_label': {'clue_id': 'r2_service_clue', 'object_id': 'r2_service_label', 'title': '箱背维护标签',
                         'text': '箱背的维护签上留着几代人的日期和签字，末行写着：“交接前，请检查设备并关闭出口。”'},
}
HIDDEN_IDS = {clue['clue_id'] for clue in OPTIONAL.values()}


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def utc_date(value):
    if not isinstance(value, str) or not value.endswith('Z'):
        raise ValueError('Timestamp must be UTC')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.utcoffset().total_seconds() != 0:
        raise ValueError('Timestamp must be UTC')
    return parsed


def mini_state(state):
    values = state.model_dump(exclude={'statistics'})
    values['level_version'] = base.LEVEL_VERSION
    hidden_objects = set(OPTIONAL)
    values['observed_object_ids'] = [oid for oid in values['observed_object_ids'] if oid not in hidden_objects]
    values['discovered_clue_ids'] = [cid for cid in values['discovered_clue_ids'] if cid not in HIDDEN_IDS]
    return base.state_model.model_validate(values)


def initial_state(revision=0):
    return GrayboxState.model_validate({**base.initial_state(revision).model_dump(), 'level_version': LEVEL_VERSION,
        'statistics': RunStatistics(started_at=utc_now(), finished_at=None, current_hint_level=1, hint_count=0, mistake_count=0).model_dump()})


def optional_objects(state):
    result = []
    if state.room_id == 'R1' and state.device_states.cabinet == 'ITEM_TAKEN':
        result.append(('r1_photo', '柜内凹槽', '取空的玻璃管下方露出一道浅浅的凹槽。'))
    if state.room_id == 'R2' and state.device_states.powerbox == 'POWER_ON':
        result.append(('r2_service_label', '箱背维护签', '通电指示灯照亮了箱背一张泛黄的维护签。'))
    return result


def rating(clues, hints, mistakes):
    if clues >= 9 and hints <= 1 and mistakes <= 2:
        return 'S'
    if clues >= 7 and hints <= 3 and mistakes <= 5:
        return 'A'
    if hints <= 8:
        return 'B'
    return 'C'


def visible_state(session_id, state, save=None):
    result = base.visible_state(session_id, mini_state(state), save)
    result.update(schema_version=SCHEMA_VERSION, level_version=LEVEL_VERSION,
                  observed_object_ids=list(state.observed_object_ids))
    by_id = {clue['clue_id']: clue for clue in result['clues']}
    by_id.update({clue['clue_id']: dict(clue) for clue in OPTIONAL.values() if clue['clue_id'] in state.discovered_clue_ids})
    result['clues'] = [by_id[cid] for cid in state.discovered_clue_ids]
    for object_id, name, description in optional_objects(state):
        result['objects'].append({'object_id': object_id, 'name': name, 'kind': 'clue', 'description': description,
                                  'actions': [base.base.affordance('inspect', '观察', object_id=object_id)]})
    stats = state.statistics.model_dump()
    stats.update(clues_found=len(state.discovered_clue_ids), clues_total=10,
                 hidden_found=len(set(state.discovered_clue_ids) & HIDDEN_IDS), hidden_total=2)
    result['statistics'] = stats
    result['settlement'] = None
    if state.status == 'won':
        result['settlement'] = {key: stats[key] for key in ('clues_found', 'clues_total', 'hint_count', 'mistake_count', 'hidden_found', 'hidden_total')}
        result['settlement']['elapsed_seconds'] = max(0, int((utc_date(stats['finished_at']) - utc_date(stats['started_at'])).total_seconds()))
        result['settlement']['rating'] = rating(stats['clues_found'], stats['hint_count'], stats['mistake_count'])
    return result


def validate_invariants(state):
    if state.level_version != LEVEL_VERSION:
        raise ValueError('Invalid graybox version')
    base.validate_invariants(mini_state(state))
    stats = state.statistics
    start = utc_date(stats.started_at)
    if (state.status == 'won') != (stats.finished_at is not None):
        raise ValueError('Finish time must match win')
    if stats.finished_at is not None and utc_date(stats.finished_at) < start:
        raise ValueError('Finish before start')
    if stats.current_hint_level not in {1, 2, 3} or type(stats.current_hint_level) is not int:
        raise ValueError('Invalid hint level')
    if any(type(value) is not int or value < 0 for value in (stats.hint_count, stats.mistake_count)):
        raise ValueError('Invalid statistics')
    for oid, clue in OPTIONAL.items():
        if (oid in state.observed_object_ids) != (clue['clue_id'] in state.discovered_clue_ids):
            raise ValueError('Optional observation requires canonical clue')
    if 'r1_photo' in state.observed_object_ids and state.device_states.cabinet != 'ITEM_TAKEN':
        raise ValueError('Photo requires taken fuse')
    if 'r2_service_label' in state.observed_object_ids and state.device_states.powerbox != 'POWER_ON':
        raise ValueError('Service label requires power')
    if len(state.observed_object_ids) != len(set(state.observed_object_ids)) or len(state.discovered_clue_ids) != len(set(state.discovered_clue_ids)):
        raise ValueError('Duplicate observations')


def apply_action(original, tool, arguments):
    target = arguments.get('object_id')
    if tool == 'inspect' and target in OPTIONAL:
        if target not in {entry[0] for entry in optional_objects(original)}:
            raise RuleError('NOT_VISIBLE', '当前无法观察该对象。')
        state = original.model_copy(deep=True)
        clue = OPTIONAL[target]
        new = []
        if target not in state.observed_object_ids:
            state.observed_object_ids.append(target)
            state.discovered_clue_ids.append(clue['clue_id'])
            state.revision += 1
            new.append(clue['clue_id'])
        validate_invariants(state)
        return state, {'changed': bool(new), 'message': '已观察。', 'observation': clue['text'], 'new_clue_ids': new, 'consumed_item_ids': []}
    updated, result = base.apply_action(mini_state(original), tool, arguments)
    values = updated.model_dump()
    values['level_version'] = LEVEL_VERSION
    values['statistics'] = original.statistics.model_dump()
    values['observed_object_ids'] = list(original.observed_object_ids) + [oid for oid in values['observed_object_ids'] if oid not in original.observed_object_ids]
    values['discovered_clue_ids'] = list(original.discovered_clue_ids) + [cid for cid in values['discovered_clue_ids'] if cid not in original.discovered_clue_ids]
    state = GrayboxState.model_validate(values)
    if state.status == 'won' and original.status != 'won':
        state.statistics.finished_at = utc_now()
    validate_invariants(state)
    return state, result


def record_mistake(original, tool, arguments, error):
    """Only Store's actual rejected action calls this; never proposals/prechecks."""
    meaningful = original.status == 'playing' and error.code == 'WRONG_CODE' and tool in {'submit_code', 'submit_login', 'submit_circuit', 'submit_sequence'}
    if tool == 'use_item' and error.code == 'PRECONDITION_FAILED' and original.status == 'playing':
        pair = (arguments['item_id'], arguments['target_id'])
        pairs = {('sample_slide', 'r1_microscope'), ('fuse', 'r2_powerbox'), ('research_strip', 'r3_panel'), ('access_card', 'exit_door')}
        visible = {obj['object_id'] for obj in visible_state('', original)['objects']}
        meaningful = (pair not in pairs and pair[0] in original.inventory
                      and pair[1] in visible and pair[1] in original.observed_object_ids)
    if not meaningful:
        return original
    state = original.model_copy(deep=True)
    state.statistics.mistake_count += 1
    state.revision += 1
    validate_invariants(state)
    return state
