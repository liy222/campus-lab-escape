"""Backend authority for AI reservations, public callbacks and proposals.

The runtime receives public projections only. Provider/network work is never
performed in these transactions. Durable pending/unknown claims cannot restart
model work, including after process or Store replacement.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError

from ..ai.types import CheckResult, ProposalCandidate, ReadResult, RuntimeBoundaryError, Snapshot, TurnResult, TurnStart, Version
from ..domain.models import AITurnRequest, EmptyRequest, RuleError, TOOL_MODELS, validate_generation

SCHEMA = json.loads((Path(__file__).resolve().parents[3] / 'contracts' / 'api.schema.json').read_text(encoding='utf-8'))
PROGRESS_TOOLS = {'take', 'use_item', 'submit_code', 'move'}
STOP_REASONS = {'MODEL_TIMEOUT', 'MODEL_UNAVAILABLE', 'MODEL_INVALID_OUTPUT', 'AI_LIMIT_REACHED', 'STALE_STATE'}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def public_validator(definition):
    return Draft202012Validator({'$defs': SCHEMA['$defs'], '$ref': '#/$defs/' + definition}, format_checker=FormatChecker())


class BoundCallbacks:
    def __init__(self, store, session_id, turn_id):
        self.store, self.session_id, self.turn_id = store, session_id, turn_id

    async def snapshot(self, expected):
        return self.store.ai_snapshot(self.session_id, self.turn_id, expected)

    async def read_tool(self, expected, tool, arguments):
        return self.store.ai_read(self.session_id, self.turn_id, expected, tool, arguments)

    async def precheck_proposal(self, expected, candidate):
        return self.store.ai_precheck(self.session_id, self.turn_id, expected, candidate)


class AIStoreMixin:
    def migrate_ai(self, connection):
        columns = {row['name'] for row in connection.execute('PRAGMA table_info(action_receipts)')}
        if 'phase' not in columns:
            connection.execute("ALTER TABLE action_receipts ADD COLUMN phase TEXT NOT NULL DEFAULT 'completed'")
        connection.executescript('''
            CREATE TABLE IF NOT EXISTS ai_turns (
                turn_id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(session_id),
                request_id TEXT NOT NULL, event_id TEXT NOT NULL, generation TEXT NOT NULL,
                cursor_revision INTEGER NOT NULL, owner TEXT NOT NULL, phase TEXT NOT NULL,
                created_at TEXT NOT NULL, read_calls INTEGER NOT NULL DEFAULT 0,
                trace_json TEXT NOT NULL DEFAULT '[]', UNIQUE(session_id,request_id)
            );
            CREATE TABLE IF NOT EXISTS proposals (
                proposal_id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(session_id),
                turn_id TEXT NOT NULL UNIQUE REFERENCES ai_turns(turn_id), proposal_json TEXT NOT NULL,
                receipt_json TEXT, receipt_event_id TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_pending_proposal_per_session
                ON proposals(session_id) WHERE json_extract(proposal_json,'$.status')='pending';
        ''')

    def invalidate_pending(self, connection, session_id, except_id=None):
        rows = connection.execute('SELECT proposal_id,proposal_json FROM proposals WHERE session_id=?', (session_id,)).fetchall()
        for row in rows:
            proposal = json.loads(row['proposal_json'])
            if proposal['status'] == 'pending' and row['proposal_id'] != except_id:
                proposal['status'] = 'invalidated'
                connection.execute('UPDATE proposals SET proposal_json=? WHERE proposal_id=?', (encoded(proposal), row['proposal_id']))

    def safe_history(self, connection, session_id, state):
        # Full legal public history for this generation, never raw events/requests.
        history = []
        rows = connection.execute("SELECT operation,outcome,result_json FROM events WHERE session_id=? AND generation=? ORDER BY sequence", (session_id, state.generation)).fetchall()
        for row in rows:
            result = json.loads(row['result_json'])
            data = result.get('data', {})
            if row['operation'] in {'action', 'ai_read', 'confirm'} and row['outcome'] == 'committed':
                receipt = data.get('receipt', {})
                if receipt.get('tool') in TOOL_MODELS:
                    history.append({'kind': 'action', 'tool': receipt['tool'], 'arguments': deepcopy(receipt['arguments']),
                                    'observation': receipt['observation'], 'new_clue_ids': deepcopy(receipt['new_clue_ids']),
                                    'revision': receipt['revision_after'], 'generation': receipt['generation'],
                                    'outcome': 'committed', 'message': receipt['message']})
            elif row['operation'] == 'ai_turn' and isinstance(data.get('answer'), str):
                history.append({'kind': 'ai_turn', 'answer': data['answer'], 'clue_refs': deepcopy(data['clue_refs']),
                                'revision': data['visible_state']['revision'], 'generation': data['visible_state']['generation'], 'outcome': data['status']})
        return tuple(history)

    def begin_ai(self, session_id, token, raw, parsed=True):
        from .sqlite import new_id, utc_now
        event_id = new_id()
        with self.transaction() as connection:
            state = self.authenticate(connection, session_id, token)
            if state is None:
                return self.failure(connection, event_id, None, 'ai_turn', 'FORBIDDEN_SESSION', '无权访问该会话。', expose=False)
            try:
                if not parsed:
                    raise ValueError()
                request = getattr(self.rules, 'ai_request_model', AITurnRequest).model_validate(raw)
                validate_generation(request.generation)
            except (ValidationError, ValueError, TypeError):
                return self.failure(connection, event_id, session_id, 'ai_turn', 'BAD_ARGUMENT', 'AI 请求字段不符合契约。', state, expose=False)
            normalized = {'operation': 'ai_turn', **request.model_dump()}
            digest = hashlib.sha256(encoded(normalized).encode('utf-8')).hexdigest()
            # Never persist or send the current session capability if pasted into
            # a chat message. Hash original content for conflict detection only.
            safe_request = {**normalized, 'message': request.message.replace(token, '[REDACTED]')}
            if request.generation != state.generation:
                return self.failure(connection, event_id, session_id, 'ai_turn', 'STALE_GENERATION', '游戏已重置或恢复，请刷新状态。', state, safe_request)
            prior = connection.execute('SELECT request_hash,response_json,http_status,phase FROM action_receipts WHERE session_id=? AND request_id=?', (session_id, request.request_id)).fetchone()
            if prior:
                if prior['request_hash'] != digest:
                    return self.failure(connection, event_id, session_id, 'ai_turn', 'REQUEST_ID_CONFLICT', '同一请求标识不能替换请求内容。', state, safe_request)
                if prior['phase'] != 'completed':
                    return self.failure(connection, event_id, session_id, 'ai_turn', 'MODEL_UNAVAILABLE', '该轮次正在处理或结果未知；使用相同请求标识查询，不会重复调用模型。', state)
                body = json.loads(prior['response_json'])
                projection = self.projection(connection, session_id, state)
                if body['ok']:
                    body['data']['visible_state'] = projection
                    proposal = body['data'].get('proposal')
                    if proposal:
                        proposal_row = connection.execute('SELECT proposal_json FROM proposals WHERE proposal_id=?', (proposal['proposal_id'],)).fetchone()
                        if proposal_row:
                            body['data']['proposal'] = json.loads(proposal_row['proposal_json'])
                else:
                    body['visible_state'] = projection
                return prior['http_status'], body
            if request.revision != state.revision:
                status, body = self.failure(connection, event_id, session_id, 'ai_turn', 'STALE_STATE', '状态已变化，请刷新后重新提问。', state, safe_request)
                connection.execute('INSERT INTO action_receipts (session_id,request_id,request_hash,generation,response_json,http_status) VALUES (?,?,?,?,?,?)', (session_id, request.request_id, digest, state.generation, encoded(body), status))
                return status, body
            hint_mode = self.rules.LEVEL_VERSION == '3.4.0'
            hint_topics = []
            if hint_mode:
                from ..ai.hints import available_topics
                hint_topics = available_topics(self.projection(connection, session_id, state))
                if hint_topics and state.statistics.current_hint_level != request.hint_level:
                    state.statistics.current_hint_level = request.hint_level
                    state.revision += 1
                    self.rules.validate_invariants(state)
                    connection.execute('UPDATE sessions SET state_json=? WHERE session_id=?', (encoded(state.model_dump()), session_id))
                    self.invalidate_pending(connection, session_id)
            turn_id = new_id()
            connection.execute("INSERT INTO action_receipts (session_id,request_id,request_hash,generation,response_json,http_status,phase) VALUES (?,?,?,?,?,0,'reserved')", (session_id, request.request_id, digest, state.generation, '{}'))
            connection.execute("INSERT INTO ai_turns (turn_id,session_id,request_id,event_id,generation,cursor_revision,owner,phase,created_at) VALUES (?,?,?,?,?,?,?,'reserved',?)", (turn_id, session_id, request.request_id, event_id, state.generation, state.revision, self.runtime_owner, utc_now()))
            if hint_mode and not hint_topics:
                from ..ai.hints import NO_HINT
                data = {'turn_id': turn_id, 'answer': NO_HINT, 'clue_refs': [], 'proposal': None, 'status': 'no_suggestion', 'stop_reason': None,
                        'usage': {'provider': 'unavailable', 'model': None, 'input_tokens': None, 'output_tokens': None, 'model_calls': 0, 'read_tool_calls': 0},
                        'visible_state': self.projection(connection, session_id, state)}
                public_validator('ai_turn_data').validate(data)
                body = {'ok': True, 'event_id': event_id, 'data': data}
                connection.execute("UPDATE ai_turns SET phase='completed' WHERE turn_id=?", (turn_id,))
                connection.execute("UPDATE action_receipts SET phase='completed',response_json=?,http_status=200 WHERE session_id=? AND request_id=?", (encoded(body), session_id, request.request_id))
                self.event(connection, event_id, session_id, 'ai_turn', 'no_suggestion', body, state, {'turn_id': turn_id}, state.revision)
                return 200, body
            start = TurnStart(turn_id, safe_request['message'], self.projection(connection, session_id, state), self.safe_history(connection, session_id, state))
            self.event(connection, new_id(), session_id, 'ai_begin', 'reserved', {'turn_id': turn_id, 'revision': state.revision, 'generation': state.generation}, state, safe_request, state.revision)
            callbacks = BoundCallbacks(self, session_id, turn_id)
            if hint_mode:
                from ..ai.hints import HintCallbacks
                callbacks = HintCallbacks(callbacks)
            return start, callbacks

    def ai_cursor(self, connection, session_id, turn_id, expected):
        turn = connection.execute('SELECT * FROM ai_turns WHERE session_id=? AND turn_id=?', (session_id, turn_id)).fetchone()
        if not turn or turn['phase'] != 'reserved' or turn['owner'] != self.runtime_owner:
            raise RuntimeBoundaryError('STALE_STATE')
        row = connection.execute('SELECT state_json FROM sessions WHERE session_id=?', (session_id,)).fetchone()
        state = self.parse_state(row['state_json'])
        if not isinstance(expected, Version) or expected.generation != turn['generation'] or expected.revision != turn['cursor_revision'] or state.generation != turn['generation'] or state.revision != turn['cursor_revision']:
            raise RuntimeBoundaryError('STALE_STATE')
        return turn, state

    def ai_snapshot(self, session_id, turn_id, expected):
        with self.transaction() as connection:
            _, state = self.ai_cursor(connection, session_id, turn_id, expected)
            return Snapshot(self.projection(connection, session_id, state))

    def ai_read(self, session_id, turn_id, expected, tool, arguments):
        from .sqlite import new_id
        with self.transaction() as connection:
            turn, state = self.ai_cursor(connection, session_id, turn_id, expected)
            if tool not in {'inspect', 'get_inventory'}:
                return ReadResult(False, self.projection(connection, session_id, state), error_code='INVALID_TOOL')
            try:
                args = self.rules.tool_models[tool].model_validate(arguments).model_dump()
            except (ValidationError, TypeError, ValueError):
                return ReadResult(False, self.projection(connection, session_id, state), error_code='BAD_ARGUMENT')
            # A second, server-side cap prevents a faulty runtime bypassing limits.
            if turn['read_calls'] >= 5:
                return ReadResult(False, self.projection(connection, session_id, state), error_code='AI_LIMIT_REACHED')
            connection.execute('UPDATE ai_turns SET read_calls=read_calls+1 WHERE turn_id=?', (turn_id,))
            event_id = new_id()
            try:
                updated, result = self.rules.apply_action(state, tool, args)
            except RuleError as error:
                self.failure(connection, event_id, session_id, 'ai_read', error.code, error.message, state, {'turn_id': turn_id, 'tool': tool, 'arguments': args})
                return ReadResult(False, self.projection(connection, session_id, state), error_code=error.code)
            connection.execute('UPDATE sessions SET state_json=? WHERE session_id=?', (encoded(updated.model_dump()), session_id))
            connection.execute('UPDATE ai_turns SET cursor_revision=? WHERE turn_id=?', (updated.revision, turn_id))
            if updated.revision != state.revision:
                self.invalidate_pending(connection, session_id)
            receipt = {'request_id': turn_id, 'event_id': event_id, 'tool': tool, 'arguments': args, 'generation': state.generation,
                       'revision_before': state.revision, 'revision_after': updated.revision, **result}
            self.event(connection, event_id, session_id, 'ai_read', 'committed', {'ok': True, 'data': {'receipt': receipt}}, updated, {'turn_id': turn_id, 'tool': tool, 'arguments': args}, state.revision)
            return ReadResult(True, self.projection(connection, session_id, updated), result['observation'], tuple(result['new_clue_ids']))

    def candidate_arguments(self, state, candidate):
        if not isinstance(candidate, ProposalCandidate) or candidate.tool not in PROGRESS_TOOLS:
            raise RuleError('PROPOSAL_REJECTED', '提案工具不符合允许范围。')
        try:
            args = self.rules.tool_models[candidate.tool].model_validate(candidate.arguments).model_dump()
            known = set(state.discovered_clue_ids)
            refs = candidate.clue_refs
            if not isinstance(refs, tuple) or any(not isinstance(ref, str) or ref not in known for ref in refs) or len(refs) != len(set(refs)):
                raise ValueError()
            if not isinstance(candidate.summary, str) or not 1 <= len(candidate.summary) <= 4000:
                raise ValueError()
        except (ValidationError, ValueError, TypeError):
            raise RuleError('PROPOSAL_REJECTED', '提案参数或线索引用不符合契约。') from None
        self.rules.apply_action(state, candidate.tool, args)  # Copy-only dynamic precheck.
        return args

    def ai_precheck(self, session_id, turn_id, expected, candidate):
        with self.transaction() as connection:
            _, state = self.ai_cursor(connection, session_id, turn_id, expected)
            try:
                self.candidate_arguments(state, candidate)
            except RuleError as error:
                return CheckResult(False, error.code)
            return CheckResult(True)

    def sanitize_trace(self, trace, state):
        # Typed allowlist: keep actual versions, limits, public tool facts and
        # measured usage, never prompts/configuration/raw upstream payloads.
        result = []
        if not isinstance(trace, tuple):
            return result
        kinds = {'turn_started', 'read_tool', 'proposed', 'proposal_rejected', 'provider_result', 'provider_error', 'answer', 'turn_finished', 'runtime_error'}
        known = set(state.discovered_clue_ids)
        for entry in trace[:30]:
            if not isinstance(entry, dict) or entry.get('kind') not in kinds:
                continue
            safe = {'kind': entry['kind']}
            for key in ('attempt', 'model_calls', 'read_tool_calls', 'revision', 'revision_before', 'revision_after', 'message_length'):
                value = entry.get(key)
                if type(value) is int and 0 <= value <= 10**9:
                    safe[key] = value
            generation = entry.get('generation')
            try:
                if isinstance(generation, str):
                    validate_generation(generation)
                    safe['generation'] = generation
            except ValueError:
                pass
            visible = entry.get('visible_state')
            if isinstance(visible, dict) and public_validator('visible_state').is_valid(visible):
                safe['revision'], safe['generation'] = visible['revision'], visible['generation']
            for key in ('tool', 'status', 'stop_reason', 'outcome', 'error_code', 'code'):
                value = entry.get(key)
                allowed = set(TOOL_MODELS) | STOP_REASONS | {'completed', 'stopped', 'no_suggestion', 'proposed', 'committed', 'cancelled', 'rejected', 'WRONG_CODE', 'PRECONDITION_FAILED', 'NOT_VISIBLE', 'BAD_ARGUMENT', 'INVALID_TOOL', 'PROPOSAL_REJECTED', 'UNEXECUTED_ACTION_CLAIM'}
                if isinstance(value, str) and value in allowed:
                    safe[key] = value
            tool = safe.get('tool')
            if tool and isinstance(entry.get('arguments'), dict):
                try:
                    safe['arguments'] = TOOL_MODELS[tool].model_validate(entry['arguments']).model_dump()
                except (ValidationError, ValueError, TypeError):
                    pass
            for key in ('new_clue_ids', 'clue_refs'):
                refs = entry.get(key)
                if isinstance(refs, list) and len(refs) == len(set(ref for ref in refs if isinstance(ref, str))) and all(isinstance(ref, str) and ref in known for ref in refs):
                    safe[key] = deepcopy(refs)
            if entry['kind'] == 'read_tool':
                if type(entry.get('ok')) is bool:
                    safe['ok'] = entry['ok']
                if entry.get('observation') is None or isinstance(entry.get('observation'), str) and len(entry['observation']) <= 4000:
                    safe['observation'] = entry.get('observation')
            if entry.get('context_mode') in {'full_history', 'structured_summary'}:
                safe['context_mode'] = entry['context_mode']
            if isinstance(entry.get('message_sha256'), str) and re.fullmatch(r'[0-9a-f]{64}', entry['message_sha256']):
                safe['message_sha256'] = entry['message_sha256']
            limits = entry.get('limits')
            expected_limits = {'model_calls', 'read_tool_calls', 'progress_proposals', 'call_seconds', 'total_seconds', 'output_tokens', 'format_retries'}
            if isinstance(limits, dict) and set(limits) == expected_limits:
                maxima = {'model_calls': 3, 'read_tool_calls': 5, 'progress_proposals': 1, 'output_tokens': 1000, 'format_retries': 1}
                integers = all(type(limits[key]) is int and (0 if key == 'format_retries' else 1) <= limits[key] <= maximum for key, maximum in maxima.items())
                seconds = all(type(limits[key]) in {int, float} and 0 < limits[key] <= maximum for key, maximum in (('call_seconds', 20), ('total_seconds', 45)))
                if integers and seconds:
                    safe['limits'] = deepcopy(limits)
            if entry.get('provider') in {'mock', 'deepseek', 'unavailable'}:
                safe['provider'] = entry['provider']
            for key in ('requested_model', 'reported_model', 'call_id'):
                value = entry.get(key)
                if value is None:
                    safe[key] = None
                elif isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.:/-]{1,100}', value):
                    safe[key] = value
            usage = entry.get('usage')
            if usage is None:
                safe['usage'] = None
            elif isinstance(usage, (tuple, list)) and len(usage) == 2 and all(type(value) is int and value >= 0 for value in usage):
                safe['usage'] = {'input_tokens': usage[0], 'output_tokens': usage[1]}
            elif isinstance(usage, dict):
                if Draft202012Validator(SCHEMA['$defs']['ai_turn_data']['properties']['usage']).is_valid(usage):
                    safe['usage'] = deepcopy(usage)
                else:
                    token_keys = {'prompt_tokens', 'completion_tokens', 'total_tokens', 'prompt_cache_hit_tokens', 'prompt_cache_miss_tokens'}
                    cleaned = {key: value for key, value in usage.items() if key in token_keys and type(value) is int and value >= 0}
                    if cleaned:
                        safe['usage'] = cleaned
            cost = entry.get('cost_upper_cny')
            if cost is None:
                safe['cost_upper_cny'] = None
            elif type(cost) in {int, float} and math.isfinite(cost) and 0 <= cost <= 10:
                safe['cost_upper_cny'] = cost
            if entry.get('finish_reason') in {'stop', 'tool_calls', 'length', 'content_filter', 'unknown'}:
                safe['finish_reason'] = entry['finish_reason']
            result.append(safe)
        return result

    def finish_ai(self, session_id, turn_id, result):
        from .sqlite import new_id, utc_now
        with self.transaction() as connection:
            turn = connection.execute('SELECT * FROM ai_turns WHERE session_id=? AND turn_id=?', (session_id, turn_id)).fetchone()
            if not turn or turn['owner'] != self.runtime_owner or turn['phase'] != 'reserved':
                raise RuntimeBoundaryError('STALE_STATE')
            row = connection.execute('SELECT state_json FROM sessions WHERE session_id=?', (session_id,)).fetchone()
            state = self.parse_state(row['state_json'])
            projection = self.projection(connection, session_id, state)
            revision_before_finish = state.revision
            expected = Version(turn['cursor_revision'], turn['generation'])
            valid_result = isinstance(result, TurnResult)
            data = deepcopy(result.data) if valid_result and isinstance(result.data, dict) else {}
            candidate = result.candidate if valid_result else None
            # Preserve valid measured usage even if a faulty runtime returns bad
            # prose or a state race; no fake zero token counts.
            usage = data.get('usage')
            usage_schema = SCHEMA['$defs']['ai_turn_data']['properties']['usage']
            if not Draft202012Validator(usage_schema).is_valid(usage):
                status, body = self.failure(connection, turn['event_id'], session_id, 'ai_turn', 'MODEL_INVALID_OUTPUT', '无法取得符合要求的轮次结果，游戏进度已保留。', state, {'turn_id': turn_id})
                connection.execute("UPDATE ai_turns SET phase='completed' WHERE turn_id=?", (turn_id,))
                connection.execute("UPDATE action_receipts SET phase='completed',response_json=?,http_status=? WHERE session_id=? AND request_id=? AND phase='reserved'", (encoded(body), status, session_id, turn['request_id']))
                return status, body
            else:
                usage = {**usage, 'read_tool_calls': turn['read_calls']}
            malformed = set(data) != {'answer', 'clue_refs', 'status', 'stop_reason', 'usage'}
            if not malformed:
                sample = {'turn_id': turn_id, **data, 'proposal': None, 'visible_state': projection}
                malformed = not public_validator('ai_turn_data').is_valid(sample) or any(ref not in state.discovered_clue_ids for ref in data['clue_refs'])
                malformed = malformed or (data['status'] == 'stopped' and data['stop_reason'] is None) or (data['status'] != 'stopped' and data['stop_reason'] is not None)
            stale = not valid_result or result.expected_version != expected or state.revision != expected.revision or state.generation != expected.generation
            if stale or malformed:
                data = {'answer': '游戏状态已变化，请根据当前状态重新询问。' if stale else '本轮模型输出不符合要求，游戏进度已保留。', 'clue_refs': [], 'status': 'stopped', 'stop_reason': 'STALE_STATE' if stale else 'MODEL_INVALID_OUTPUT', 'usage': usage}
                candidate = None
            else:
                data['usage'] = usage
            if self.rules.LEVEL_VERSION == '3.4.0':
                from ..ai.hints import bounded_render
                if data['status'] == 'stopped':
                    # Even failure text from an injected runtime is untrusted.
                    data.update(answer='本轮提示没有完成，已发现线索与游戏进度仍保留。', clue_refs=[])
                if data['status'] != 'stopped':
                    try:
                        if candidate is not None or turn['read_calls'] != 0:
                            raise ValueError('Progress is forbidden in hint mode')
                        answer, refs = bounded_render(projection, data['clue_refs'])
                    except (ValueError, KeyError, TypeError):
                        data.update(answer='提示选择不符合已发现信息，本轮已停止。', clue_refs=[], status='stopped', stop_reason='MODEL_INVALID_OUTPUT')
                    else:
                        # The final authority renders again and ignores runtime prose.
                        data.update(answer=answer, clue_refs=refs, status='no_suggestion', stop_reason=None)
                        state.statistics.hint_count += 1
                        state.revision += 1
                        self.rules.validate_invariants(state)
                        connection.execute('UPDATE sessions SET state_json=? WHERE session_id=?', (encoded(state.model_dump()), session_id))
                        self.invalidate_pending(connection, session_id)
                        projection = self.projection(connection, session_id, state)
                candidate = None
            proposal = None
            if data['status'] == 'stopped':
                candidate = None
            if candidate is not None:
                try:
                    args = self.candidate_arguments(state, candidate)
                except RuleError:
                    data.update(answer='本轮建议未通过游戏规则检查，请核对已发现线索。', clue_refs=[], status='stopped', stop_reason='MODEL_INVALID_OUTPUT')
                else:
                    self.invalidate_pending(connection, session_id)
                    proposal = {'proposal_id': new_id(), 'tool': candidate.tool, 'arguments': args, 'revision': state.revision, 'generation': state.generation,
                                'expires_at': (datetime.now(timezone.utc) + timedelta(seconds=120)).isoformat().replace('+00:00', 'Z'), 'status': 'pending', 'clue_refs': list(candidate.clue_refs), 'summary': candidate.summary}
                    public_validator('proposal').validate(proposal)
                    connection.execute('INSERT INTO proposals (proposal_id,session_id,turn_id,proposal_json) VALUES (?,?,?,?)', (proposal['proposal_id'], session_id, turn_id, encoded(proposal)))
            data.update(turn_id=turn_id, proposal=proposal, visible_state=projection)
            public_validator('ai_turn_data').validate(data)
            body = {'ok': True, 'event_id': turn['event_id'], 'data': data}
            trace = self.sanitize_trace(result.trace, state) if valid_result else []
            connection.execute("UPDATE ai_turns SET phase='completed',trace_json=? WHERE turn_id=? AND phase='reserved'", (encoded(trace), turn_id))
            connection.execute("UPDATE action_receipts SET phase='completed',response_json=?,http_status=200 WHERE session_id=? AND request_id=? AND phase='reserved'", (encoded(body), session_id, turn['request_id']))
            self.event(connection, turn['event_id'], session_id, 'ai_turn', 'proposed' if proposal else data['status'], body, state, {'turn_id': turn_id}, revision_before_finish)
            return 200, body

    def abandon_ai(self, session_id, turn_id):
        # Unknown network outcome stays charged/tombstoned; no automatic retry.
        with self.transaction() as connection:
            turn = connection.execute('SELECT request_id FROM ai_turns WHERE session_id=? AND turn_id=? AND owner=? AND phase=\'reserved\'', (session_id, turn_id, self.runtime_owner)).fetchone()
            if turn:
                connection.execute("UPDATE ai_turns SET phase='unknown' WHERE turn_id=?", (turn_id,))
                connection.execute("UPDATE action_receipts SET phase='unknown' WHERE session_id=? AND request_id=? AND phase='reserved'", (session_id, turn['request_id']))

    def proposal_operation(self, session_id, token, proposal_id, operation, raw, parsed=True):
        from .sqlite import new_id
        event_id = new_id()
        with self.transaction() as connection:
            state = self.authenticate(connection, session_id, token)
            if state is None:
                return self.failure(connection, event_id, None, operation, 'FORBIDDEN_SESSION', '无权访问该会话。', expose=False)
            try:
                if not parsed:
                    raise ValueError()
                EmptyRequest.model_validate(raw)
            except (ValidationError, ValueError, TypeError):
                return self.failure(connection, event_id, session_id, operation, 'BAD_ARGUMENT', '确认或取消请求必须为空 JSON 对象。', state, expose=False)
            row = connection.execute('SELECT * FROM proposals WHERE proposal_id=? AND session_id=?', (proposal_id, session_id)).fetchone()
            if row is None:
                return self.failure(connection, event_id, session_id, operation, 'PROPOSAL_NOT_FOUND', '未找到该提案。', state)
            proposal = json.loads(row['proposal_json'])

            def reject(code, message, status=None):
                if status is not None:
                    proposal['status'] = status
                    connection.execute('UPDATE proposals SET proposal_json=? WHERE proposal_id=?', (encoded(proposal), proposal_id))
                return self.failure(connection, event_id, session_id, operation, code, message, state, {'proposal_id': proposal_id})

            if proposal['generation'] != state.generation:
                return reject('PROPOSAL_INVALIDATED', '游戏已重置或恢复，该提案已失效。', 'invalidated')
            if proposal['status'] == 'committed':
                if operation == 'cancel':
                    return reject('PROPOSAL_REJECTED', '已执行的提案不能取消。')
                receipt = json.loads(row['receipt_json'])
                return 200, {'ok': True, 'event_id': row['receipt_event_id'], 'data': {'receipt': receipt, 'replayed': True, 'proposal': proposal, 'visible_state': self.projection(connection, session_id, state)}}
            if proposal['status'] == 'cancelled':
                if operation == 'cancel':
                    return 200, {'ok': True, 'event_id': event_id, 'data': {'proposal': proposal, 'visible_state': self.projection(connection, session_id, state)}}
                return reject('PROPOSAL_CANCELLED', '该提案已取消。')
            if proposal['status'] == 'expired':
                return reject('PROPOSAL_EXPIRED', '该提案已过期。')
            if proposal['status'] == 'invalidated':
                return reject('PROPOSAL_INVALIDATED', '游戏状态已变化，该提案已失效。')
            if proposal['status'] == 'rejected':
                return reject('PROPOSAL_REJECTED', '该提案未通过游戏规则检查。')
            if datetime.fromisoformat(proposal['expires_at'].replace('Z', '+00:00')) <= datetime.now(timezone.utc):
                return reject('PROPOSAL_EXPIRED', '该提案已过期。', 'expired')
            if proposal['revision'] != state.revision:
                return reject('PROPOSAL_INVALIDATED', '游戏状态已变化，该提案已失效。', 'invalidated')
            if operation == 'cancel':
                proposal['status'] = 'cancelled'
                connection.execute('UPDATE proposals SET proposal_json=? WHERE proposal_id=?', (encoded(proposal), proposal_id))
                body = {'ok': True, 'event_id': event_id, 'data': {'proposal': proposal, 'visible_state': self.projection(connection, session_id, state)}}
                self.event(connection, event_id, session_id, 'cancel', 'cancelled', body, state, {'proposal_id': proposal_id}, state.revision)
                return 200, body
            try:
                candidate = ProposalCandidate(proposal['tool'], proposal['arguments'], tuple(proposal['clue_refs']), proposal['summary'])
                args = self.candidate_arguments(state, candidate)
                updated, result = self.rules.apply_action(state, proposal['tool'], args)
            except RuleError:
                return reject('PROPOSAL_REJECTED', '当前条件不允许执行该提案。', 'rejected')
            proposal['status'] = 'committed'
            receipt = {'request_id': proposal_id, 'event_id': event_id, 'tool': proposal['tool'], 'arguments': args, 'generation': state.generation,
                       'revision_before': state.revision, 'revision_after': updated.revision, **result}
            connection.execute('UPDATE sessions SET state_json=? WHERE session_id=?', (encoded(updated.model_dump()), session_id))
            connection.execute('UPDATE proposals SET proposal_json=?,receipt_json=?,receipt_event_id=? WHERE proposal_id=?', (encoded(proposal), encoded(receipt), event_id, proposal_id))
            if updated.revision != state.revision:
                self.invalidate_pending(connection, session_id, except_id=proposal_id)
            body = {'ok': True, 'event_id': event_id, 'data': {'receipt': receipt, 'replayed': False, 'proposal': proposal, 'visible_state': self.projection(connection, session_id, updated)}}
            self.event(connection, event_id, session_id, 'confirm', 'committed', body, updated, {'proposal_id': proposal_id}, state.revision)
            return 200, body





