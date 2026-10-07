"""Small v3.3 adapter over v3.2 devices, inventory, clues and room rules."""
from copy import deepcopy

from . import circuit, puzzle_rules as base
from .mini_models import MiniState, TOOL_MODELS_MINI
from .models import RuleError

SCHEMA_VERSION, LEVEL_VERSION = '1.3.0', '3.3.0'
state_model, tool_models = MiniState, TOOL_MODELS_MINI
game_fields = set(MiniState.model_fields) - {'revision', 'generation'}
DEVICES = (
    {'device_id': 'cooling', 'label': '冷却', 'symbol': '▲'},
    {'device_id': 'lighting', 'label': '照明', 'symbol': '★'},
    {'device_id': 'safety', 'label': '安全', 'symbol': '●'},
    {'device_id': 'ventilation', 'label': '通风', 'symbol': '■'},
)
LEGEND = {**base.CLUES['r3_legend_clue'],
          'text': '■ 对应通风；▲ 对应冷却；★ 对应照明；● 对应安全。终检按纸条指定位置读取批次源序，再依次操作对应设备。'}
# Trusted sequence is inferred using the same clue network, never projected.
SOURCE_SYMBOLS = ('▲', '●', '■', '★')
READ_INDICES = (3, 1, 4, 2)
SYMBOL_DEVICES = {device['symbol']: device['device_id'] for device in DEVICES}


def legacy_state(state):
    values = state.model_dump(exclude={'circuit_rotations'})
    values['level_version'] = base.LEVEL_VERSION
    return base.state_model.model_validate(values)


def initial_state(revision=0):
    return MiniState.model_validate({**base.initial_state(revision).model_dump(),
                                     'level_version': LEVEL_VERSION,
                                     'circuit_rotations': list(circuit.INITIAL_ROTATIONS)})


def visible_state(session_id, state, save=None):
    result = base.visible_state(session_id, legacy_state(state), save)
    result.update(schema_version=SCHEMA_VERSION, level_version=LEVEL_VERSION)
    result['minigames'] = {'circuit': None, 'sequence': None}
    d = state.device_states
    exposed_circuit = (state.room_id == 'R2' and 'r2_powerbox' in state.observed_object_ids
                       and d.powerbox in {'FUSE_INSTALLED', 'CIRCUIT_READY', 'POWER_ON'})
    exposed_sequence = (state.room_id == 'R3' and 'r3_panel' in state.observed_object_ids
                        and state.puzzle_states.panel == 'STRIP_INSERTED'
                        and d.exit in {'FINAL_CHECK', 'UNLOCKED', 'OPEN'})
    if exposed_circuit:
        result['minigames']['circuit'] = circuit.board(state.circuit_rotations, d.powerbox != 'FUSE_INSTALLED')
    if exposed_sequence:
        result['minigames']['sequence'] = {'target_id': 'r3_panel', 'devices': deepcopy(list(DEVICES)),
                                            'length': 4, 'status': 'completed' if state.flags['check_done'] else 'editing'}
    for clue in result['clues']:
        if clue['clue_id'] == 'r3_legend_clue':
            clue.update(LEGEND)
    for obj in result['objects']:
        if obj['object_id'] == 'r2_powerbox' and d.powerbox == 'FUSE_INSTALLED':
            obj['description'] = '保险丝已经安装，箱内露出可以旋转的线路模块，总闸仍抬着。'
            obj['actions'] = [action for action in obj['actions'] if action['tool'] != 'interact']
            if exposed_circuit and state.status == 'playing':
                obj['actions'].append(base.affordance('submit_circuit', '检查线路', target_id='r2_powerbox'))
        if obj['object_id'] == 'r3_panel':
            if not state.flags['check_done']:
                obj['description'] = ('窄纸已经插好，四个设备操作钮等待读取顺序。' if state.puzzle_states.panel == 'STRIP_INSERTED'
                                      else '控制台旁有一条带定位齿的窄纸槽，设备操作钮仍暗着。')
            obj['actions'] = [action for action in obj['actions'] if action['tool'] != 'submit_code']
            if exposed_sequence and not state.flags['check_done'] and state.status == 'playing':
                obj['actions'].append(base.affordance('submit_sequence', '确认设备顺序', target_id='r3_panel'))
    return result


def validate_invariants(state):
    if state.level_version != LEVEL_VERSION:
        raise ValueError('Invalid minigame version')
    base.validate_invariants(legacy_state(state))
    rotations = state.circuit_rotations
    if len(rotations) != 9 or any(type(value) is not int or not 0 <= value <= 3 for value in rotations):
        raise ValueError('Invalid rotations')
    stage = state.device_states.powerbox
    if stage in {'CLOSED', 'OPEN', 'MISSING_FUSE'} and rotations != list(circuit.INITIAL_ROTATIONS):
        raise ValueError('Rotation requires installed fuse')
    if stage in {'CIRCUIT_READY', 'POWER_ON'} and not circuit.connected(rotations):
        raise ValueError('Committed circuit requires reciprocal connectivity')


def apply_action(original, tool, arguments):
    if tool == 'interact' and arguments['target_id'] == 'r2_powerbox' and original.device_states.powerbox == 'FUSE_INSTALLED':
        raise RuleError('PRECONDITION_FAILED', '线路尚未通过检查，总闸保持原位。')
    if tool == 'submit_code' and arguments['target_id'] == 'r3_panel':
        raise RuleError('PRECONDITION_FAILED', '终检装置等待设备操作顺序。')
    if tool not in {'rotate_circuit', 'submit_circuit', 'submit_sequence'}:
        updated, result = base.apply_action(legacy_state(original), tool, arguments)
        state = MiniState.model_validate({**updated.model_dump(), 'level_version': LEVEL_VERSION,
                                         'circuit_rotations': list(original.circuit_rotations)})
        # Keep old-version clue text unchanged while this epoch uses operation rules.
        if tool == 'inspect' and arguments['object_id'] == 'r3_legend':
            result['observation'] = LEGEND['text']
        elif tool == 'inspect' and arguments['object_id'] in {'r2_powerbox', 'r3_panel'}:
            target = next(obj for obj in visible_state('', state)['objects'] if obj['object_id'] == arguments['object_id'])
            result['observation'] = target['description']
        elif tool == 'use_item' and arguments['target_id'] == 'r3_panel':
            result['message'] = '窄纸已经沿定位齿插好，控制台等待设备操作顺序。'
        validate_invariants(state)
        return state, result
    state = original.model_copy(deep=True)
    target = arguments['target_id']
    if state.status == 'won':
        raise RuleError('GAME_FINISHED', '游戏已通关，请重新开始。')
    if target not in {obj['object_id'] for obj in base.visible_objects(legacy_state(state))}:
        raise RuleError('NOT_VISIBLE', '当前无法操作该对象。')
    if target not in state.observed_object_ids:
        raise RuleError('PRECONDITION_FAILED', '还没有仔细观察这件装置。')
    if tool in {'rotate_circuit', 'submit_circuit'}:
        if state.device_states.powerbox != 'FUSE_INSTALLED':
            raise RuleError('PRECONDITION_FAILED', '线路模块当前无法操作。')
        if tool == 'rotate_circuit':
            index = circuit.MODULE_IDS.index(arguments['module_id'])
            state.circuit_rotations[index] = (state.circuit_rotations[index] + 1) % 4
            message = '线路模块已旋转。'
        else:
            if not circuit.connected(state.circuit_rotations):
                raise RuleError('WRONG_CODE', '线路尚未接通，请检查模块的连接。')
            state.device_states.powerbox = 'CIRCUIT_READY'
            message = '线路检查通过，总闸仍抬着。'
    else:
        if state.puzzle_states.panel != 'STRIP_INSERTED' or state.device_states.exit != 'FINAL_CHECK' or state.flags['check_done']:
            raise RuleError('PRECONDITION_FAILED', '终检装置当前没有等待设备操作。')
        expected = [SYMBOL_DEVICES[SOURCE_SYMBOLS[index - 1]] for index in READ_INDICES]
        if arguments['device_ids'] != expected:
            raise RuleError('WRONG_CODE', '终检没有接受这组操作顺序，请核对已发现资料。')
        state.flags['check_done'] = True
        message = '终检已完成，出口仍等待释放门锁。'
    state.revision += 1
    validate_invariants(state)
    return state, {'changed': True, 'message': message, 'observation': None,
                   'new_clue_ids': [], 'consumed_item_ids': []}
