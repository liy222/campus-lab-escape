"""Server-only bounded hints from discovered references/current public geometry.

This module never imports private game answers. Provider prose, actions and free
claims cannot become a displayed hint, even at the highest level.
"""
import asyncio
import json

from .provider import CallLimits, ProviderError, strict_json
from .types import CheckResult, ReadResult, RuntimeBoundaryError, TurnResult, Version

NO_HINT = '当前没有合适的预设提示。可以查看当前环境和装置提供的操作，或回顾已经发现的线索。'
TEMPLATES = {
    'sample_time': (
        '已发现的记录和时间信息之间可能存在联系。',
        '可以对照已读过的样本编号规则和实验开始时间。',
        '记录把编号末两位指向开始时间的分钟数。先确定这一部分，另一部分仍需从样本信息推理。'),
    'sample_mark': (
        '样本上的标记也许能补充记录中的编号规则。',
        '可以对照已发现的样本标记和样本编号规则。',
        '记录说明编号前两位来自样本编号。先处理这部分，再用已发现的时间信息补足余下部分。'),
    'login_identity': (
        '先前记录的环境编号可能对当前终端有帮助。',
        '可以把已发现的实验室铭牌与终端维护说明放在一起读。',
        '维护说明要求完整实验室编号，铭牌的字母前缀也属于编号的一部分。这里仍需自行输入。'),
    'login_time': (
        '维护要求中的时间格式可以与已经读过的钟面对照。',
        '可以对照已发现的维护说明和实验开始时间。',
        '维护说明要求HHMM格式且不含冒号，可以从已经读过的钟面分别取小时和分钟。'),
    'sequence': (
        '先前保存的源序与现在的转录规则可以组合使用。',
        '可以对照已发现的批次源序、纸条读取位置和设备对应表。',
        '纸条要求先读取源序的第3位，再在对应表找同一符号的设备。其余位置请继续自行转录。'),
    'circuit': (
        '可以先关注当前线路盘起点与终点附近的接口方向。',
        '只看目前暴露的线路盘，检查相邻两格的端口是否朝向彼此。',
        '相邻格两端同时朝向彼此才算接通。先检查公开起点的西侧端口，再逐格核对连接。'),
}


def _next_step(state, *, as_goal=False):
    """One bounded observation/action, derived only from the public projection.

    The four item/target pairs describe public uses, never puzzle answers.
    usable_targets is empty in this level, so visible/observed targets, carried
    items and their public stages jointly gate these suggestions. No action is
    executed and no undiscovered clue text or hidden object is consulted.
    """
    objects = {obj['object_id']: obj for obj in state['objects']}
    known = {clue['clue_id'] for clue in state['clues']}
    observed = set(state['observed_object_ids'])
    inventory = {item['item_id']: item for item in state['inventory']}
    devices, puzzles = state['device_states'], state['puzzle_states']
    room = state['room']['room_id']
    done = state['progress']['check_done']

    def emit(texts, kind, **focus):
        if as_goal:
            return {'kind': kind, 'focus': focus, 'teaching_goal': {
                'observe': '先观察当前可见对象，不预报观察结果',
                'take': '提醒收起当前已观察物品',
                'use': '讨论背包物品与已观察装置的一次公开用途',
                'interact': '解释当前装置的一次公开可用操作',
                'move': '讨论当前开放通路，可回溯补充观察',
            }[kind]}
        return texts

    def action(object_id, tool):
        obj = objects.get(object_id)
        return next((entry for entry in obj['actions'] if entry['tool'] == tool), None) if obj else None

    def look(object_id, *, again=False):
        if action(object_id, 'inspect') and (again or object_id not in observed):
            name = objects[object_id]['name']
            return emit(('先留意当前环境中还可以细看的地方。',
                    f'可以把注意力放在{name}上。',
                    f'可以再次观察{name}，确认当前可见的信息。' if again else f'可以先观察{name}，取得它当前可见的信息。'), 'observe', object_id=object_id)

    def take(item_id, object_id):
        result = look(object_id)
        if result:
            return result
        if item_id not in inventory and action(object_id, 'take'):
            name = objects[object_id]['name']
            return emit(('留意已经看见、尚未收起的物品。',
                    f'{name}还在当前环境中，可以关注它的操作。',
                    f'可以对{name}选择“拿起物品”。'), 'take', object_id=object_id, item_id=item_id)

    def interact(object_id):
        result = look(object_id)
        if result:
            return result
        entry = action(object_id, 'interact')
        if entry:
            name = objects[object_id]['name']
            return emit(('留意当前装置还提供了什么操作。',
                    f'{name}的当前阶段还有可用操作。',
                    f'可以在{name}选择“{entry["label"]}”。'), 'interact', object_id=object_id, label=entry['label'])

    def use(item_id, object_id):
        result = look(object_id)
        if result:
            return result
        if item_id in inventory and object_id in objects and object_id in observed:
            item, target = inventory[item_id]['name'], objects[object_id]['name']
            return emit(('留意背包物件与当前装置的配合。',
                    f'可以对照背包里的{item}与{target}。',
                    f'可以将背包中的{item}用于{target}。'), 'use', object_id=object_id, item_id=item_id)

    def travel(destination, *, back=False):
        passage = next((entry for entry in state['exits'] if entry['destination_id'] == destination and entry['unlocked']), None)
        if passage:
            name = passage['name']
            return emit(('可以回顾先前房间，补看环境或尚未收起的物品。' if back else '可以留意当前已经开放的通路。',
                    f'当前有一条通往{name}的开放通路。',
                    f'可以沿当前开放通路前往{name}，继续查看环境。'), 'move', destination_id=destination, backtrack=back)
        door = {('R1', 'R2'): 'r1_door', ('R2', 'R3'): 'r2_door'}.get((room, destination))
        return interact(door) if door else None

    if room == 'R1':
        if devices['cabinet'] == 'LOCKED':
            for clue, target in (('r1_record_clue', 'r1_record'), ('r1_clock_clue', 'r1_clock')):
                if clue not in known:
                    return look(target)
            if 'r1_sample_clue' not in known:
                result = look('r1_microscope')
                if result:
                    return result
                if puzzles['microscope'] == 'SLIDE_PLACED':
                    return look('r1_microscope', again=True)
                if 'sample_slide' in inventory:
                    return use('sample_slide', 'r1_microscope')
                return take('sample_slide', 'sample_slide')
            # All cabinet materials are known: retain only the original topics.
            return None
        if devices['cabinet'] == 'CODE_ACCEPTED':
            return interact('r1_cabinet')
        if 'r1_fuse' in objects:
            return take('fuse', 'r1_fuse')
        if not done and 'r1_symbols_clue' not in known:
            return look('r1_symbols')
        if devices['computer'] not in {'UNLOCKED', 'DATA_READ'}:
            for clue, target in (('r1_plaque_clue', 'r1_plaque'), ('r1_clock_clue', 'r1_clock')):
                if clue not in known:
                    return look(target)
        return travel('R2')

    if room == 'R2':
        power = devices['powerbox']
        if power in {'CLOSED', 'OPEN', 'CIRCUIT_READY'}:
            return interact('r2_powerbox')
        if power == 'MISSING_FUSE':
            if 'fuse' in inventory:
                return use('fuse', 'r2_powerbox')
            return travel('R1', back=True)
        if power == 'FUSE_INSTALLED':
            # Current public circuit geometry has its own sole empty-ref topic.
            return None
        computer = devices['computer']
        if computer in {'OFF', 'BOOTING', 'UNLOCKED'}:
            return interact('r2_monitor')
        if computer == 'LOGIN_LOCKED':
            if 'r2_maintenance_clue' not in known:
                return look('r2_maintenance')
            if not {'r1_plaque_clue', 'r1_clock_clue'} <= known:
                return travel('R1', back=True)
            return None
        if computer == 'DATA_READ':
            for item in ('research_strip', 'access_card'):
                if item in objects:
                    return take(item, item)
            if not done and puzzles['panel'] == 'STRIP_INSERTED' and devices['exit'] == 'FINAL_CHECK' and 'r1_symbols_clue' not in known:
                return travel('R1', back=True)
            return travel('R3')

    if room == 'R3':
        if done:
            if devices['exit'] == 'OPEN':
                return travel('EXIT')
            return interact('exit_door')
        if puzzles['panel'] == 'EMPTY':
            if 'research_strip' in inventory:
                return use('research_strip', 'r3_panel')
            return travel('R2', back=True)
        if devices['exit'] == 'LOCKED':
            if 'access_card' in inventory:
                return use('access_card', 'exit_door')
            return travel('R2', back=True)
        if devices['exit'] == 'CARD_ACCEPTED':
            return interact('exit_door')
        if devices['exit'] == 'FINAL_CHECK':
            if 'r3_legend_clue' not in known:
                return look('r3_legend')
            if not {'r1_symbols_clue', 'r2_indices_clue'} <= known:
                return travel('R2', back=True)
            return None
    return None


def available_topics(state):
    """Eligibility uses public facts only; no reads, hidden facts or discovery."""
    if state.get('level_version') != '3.4.0' or state.get('status') != 'playing':
        return []
    known = {clue['clue_id'] for clue in state['clues']}
    topics = []

    def add(topic, refs):
        if set(refs) <= known:
            topics.append({'topic': topic, 'clue_refs': list(refs)})

    room = state['room']['room_id']
    devices = state['device_states']
    if room == 'R1' and devices['cabinet'] == 'LOCKED':
        add('sample_time', ('r1_record_clue', 'r1_clock_clue'))
        add('sample_mark', ('r1_record_clue', 'r1_sample_clue'))
    if room == 'R2' and devices['computer'] == 'LOGIN_LOCKED':
        add('login_identity', ('r1_plaque_clue', 'r2_maintenance_clue'))
        add('login_time', ('r1_clock_clue', 'r2_maintenance_clue'))
    if room == 'R3' and state['puzzle_states']['panel'] == 'STRIP_INSERTED' and devices['exit'] == 'FINAL_CHECK' and not state['progress']['check_done']:
        add('sequence', ('r1_symbols_clue', 'r2_indices_clue', 'r3_legend_clue'))
    board = state.get('minigames', {}).get('circuit')
    if room == 'R2' and isinstance(board, dict) and board['status'] == 'editing':
        add('circuit', ())
    elif _next_step(state) is not None:
        # Unique empty refs preserve finish_ai's final refs-only re-render.
        add('next_step', ())
    return topics


def bounded_render(state, refs, topic=None):
    """Also used inside finish_ai; supplied free answer text is never consulted."""
    if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs) or len(refs) != len(set(refs)):
        raise ValueError('Invalid hint references')
    for allowed in available_topics(state):
        if set(refs) == set(allowed['clue_refs']) and (topic is None or topic == allowed['topic']):
            level = state['statistics']['current_hint_level']
            texts = _next_step(state) if allowed['topic'] == 'next_step' else TEMPLATES[allowed['topic']]
            return texts[level - 1], list(allowed['clue_refs'])
    raise ValueError('No eligible known topic')


class HintCallbacks:
    """Give new-mode runtimes only snapshot access, even if injected/faulty."""
    def __init__(self, callbacks):
        self._snapshot = callbacks.snapshot

    async def snapshot(self, expected):
        return await self._snapshot(expected)

    async def read_tool(self, expected, tool, arguments):
        snapshot = await self.snapshot(expected)
        return ReadResult(False, snapshot.visible_state, error_code='INVALID_TOOL')

    async def precheck_proposal(self, expected, candidate):
        await self.snapshot(expected)
        return CheckResult(False, 'PROPOSAL_REJECTED')


async def run_hint(runtime, start, callbacks):
    state = start.visible_state
    expected = Version.from_state(state)
    provider = runtime.provider
    name = getattr(provider, 'provider_name', 'mock')
    model = getattr(provider, 'model_name', None) or getattr(getattr(provider, 'config', None), 'model', None)
    usage = {'provider': name, 'model': model, 'input_tokens': None, 'output_tokens': None,
             'model_calls': 0, 'read_tool_calls': 0}
    trace = []

    def result(answer, refs, reason=None):
        return TurnResult({'answer': answer, 'clue_refs': refs, 'status': 'stopped' if reason else 'no_suggestion',
                           'stop_reason': reason, 'usage': dict(usage)}, None, tuple(trace), expected)

    try:
        async with asyncio.timeout(runtime.limits.total_seconds):
            snapshot = await callbacks.snapshot(expected)
            runtime._validate_state(snapshot.visible_state)
            if Version.from_state(snapshot.visible_state) != expected:
                raise RuntimeBoundaryError('STALE_STATE')
            state = snapshot.visible_state
            topics = available_topics(state)
            if not topics:
                return result(NO_HINT, [])
            from .mock import DeterministicMockProvider
            if isinstance(provider, DeterministicMockProvider):
                selected = topics[state['statistics']['hint_count'] % len(topics)]
                # This is local template selection: no fabricated model/token call.
            else:
                messages = [
                    {'role': 'system', 'content': 'Select one supplied known hint topic. Return ONLY JSON with exactly topic and clue_refs matching one supplied option. No prose, actions, tools or extra fields.'},
                    {'role': 'user', 'content': json.dumps({'topics': topics}, ensure_ascii=False)},
                ]
                usage['model_calls'] = 1
                if hasattr(provider, 'last_response_metadata'):
                    provider.last_response_metadata = None
                async with asyncio.timeout(runtime.limits.call_seconds):
                    reply = await provider.complete(messages, [], CallLimits(runtime.limits.output_tokens, runtime.limits.call_seconds), tool_choice='none')
                tokens = reply.usage
                if isinstance(tokens, dict) and all(type(tokens.get(key)) is int and tokens[key] >= 0 for key in ('prompt_tokens', 'completion_tokens')):
                    usage.update(input_tokens=tokens['prompt_tokens'], output_tokens=tokens['completion_tokens'])
                trace.append({'kind': 'provider_result', 'provider': name, 'requested_model': model,
                              'reported_model': reply.reported_model, 'usage': reply.usage, 'call_id': reply.call_id,
                              'finish_reason': reply.finish_reason, 'cost_upper_cny': reply.cost_upper_cny})
                selected = strict_json(reply.content or '')
                if reply.tool_calls or not isinstance(selected, dict) or set(selected) != {'topic', 'clue_refs'} or selected not in topics:
                    raise ValueError('Invalid topic selection')
            answer, refs = bounded_render(state, selected['clue_refs'], selected['topic'])
            trace.append({'kind': 'answer', 'clue_refs': refs})
            return result(answer, refs)
    except RuntimeBoundaryError as error:
        return result('游戏状态已变化，请根据当前状态重新询问。', [], 'STALE_STATE' if error.code in {'STALE_STATE', 'STALE_GENERATION'} else 'MODEL_INVALID_OUTPUT')
    except TimeoutError:
        return result('本轮提示超时，已发现线索仍保留。', [], 'MODEL_TIMEOUT')
    except ProviderError as error:
        metadata = getattr(provider, 'last_response_metadata', None)
        if isinstance(metadata, dict) and error.call_id is not None and metadata.get('call_id') == error.call_id:
            tokens = metadata.get('usage')
            if isinstance(tokens, dict) and all(type(tokens.get(key)) is int and tokens[key] >= 0 for key in ('prompt_tokens', 'completion_tokens')):
                usage.update(input_tokens=tokens['prompt_tokens'], output_tokens=tokens['completion_tokens'])
        trace.append({'kind': 'provider_error', 'code': error.code, 'call_id': error.call_id,
                      'usage': {'prompt_tokens': usage['input_tokens'], 'completion_tokens': usage['output_tokens']} if usage['input_tokens'] is not None else None})
        reason = error.code if error.code in {'MODEL_TIMEOUT', 'MODEL_INVALID_OUTPUT', 'AI_LIMIT_REACHED'} else 'MODEL_UNAVAILABLE'
        return result('本轮提示暂时不可用，已发现线索仍保留。', [], reason)
    except Exception:
        return result('提示选择不符合要求，本轮已停止。', [], 'MODEL_INVALID_OUTPUT')
