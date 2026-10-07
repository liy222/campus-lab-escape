"""Server-only bounded hints from discovered references/current public geometry.

This module never imports private game answers. Provider prose, actions and free
claims cannot become a displayed hint, even at the highest level.
"""
import asyncio
import json

from .provider import CallLimits, ProviderError, strict_json
from .types import CheckResult, ReadResult, RuntimeBoundaryError, TurnResult, Version

NO_HINT = '目前已发现的信息还不足以形成提示。可以先观察当前可见环境，取得更多线索后再询问。'
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
    return topics


def bounded_render(state, refs, topic=None):
    """Also used inside finish_ai; supplied free answer text is never consulted."""
    if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs) or len(refs) != len(set(refs)):
        raise ValueError('Invalid hint references')
    for allowed in available_topics(state):
        if set(refs) == set(allowed['clue_refs']) and (topic is None or topic == allowed['topic']):
            level = state['statistics']['current_hint_level']
            return TEMPLATES[allowed['topic']][level - 1], list(allowed['clue_refs'])
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
                selected = topics[0]
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
