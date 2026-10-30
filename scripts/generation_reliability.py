"""Finite reliability sampling. Preparation never opens credentials or a ledger.

Execute is Main-only after actual new user approval of the concrete preview.
Each of the six cases has one attempt; provider/usage/budget anomalies stop.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'evidence/project/stages/v5-generation-reliability'
ACTIVE_RUN = None
MAX_CALLS = 6
MAX_TOTAL_UNITS = 1_000_000_000
SOURCES = (
    'scripts/generation_reliability.py', 'backend/app/ai/v5.py',
    'backend/app/ai/provider.py', 'backend/app/ai/budget.py',
    'backend/app/domain/generation_content_v2.py', 'backend/app/domain/puzzle_purpose.py',
    'backend/app/domain/generation_observability.py', 'backend/app/domain/blueprints.py',
    'backend/app/domain/structure_variants.py', 'backend/app/domain/generated.py',
    'frontend/src/assets/generated-catalog.json',
)
CASES = (
    ('A1', '雨夜天文社', 2, 'normal', 0),
    ('A2', '图书馆档案', 2, 'normal', 1),
    ('A3', '化学实验室', 2, 'normal', 2),
    ('A4', '计算机机房', 2, 'normal', 3),
    ('A5', '校园广播室', 2, 'normal', 0),
    ('A6', '雨夜天文社', 3, 'hard', 3),
)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def source_map():
    return {name: sha((ROOT / name).read_bytes()) for name in SOURCES}


def cases_and_payloads():
    from backend.app.ai.v5 import GenerationService
    from backend.app.ai.budget import cost_units
    from backend.app.domain.generation_content_v2 import select_blueprint
    result = []
    for case_id, theme, rooms, difficulty, seed in CASES:
        bp = select_blueprint(rooms, difficulty, seed=seed)
        messages = GenerationService.messages(theme=theme, room_count=rooms, difficulty=difficulty, blueprint=bp)
        payload = {'model': 'deepseek-flash', 'messages': messages, 'max_tokens': 6000,
                   'thinking': {'type': 'disabled'}, 'stream': False,
                   'response_format': {'type': 'json_object'}}
        body = encoded(payload)
        units = cost_units(len(body) * 4 + 8192, 6000)
        if units > 200_000_000:
            raise ValueError('CASE_COST_BOUND_EXCEEDED')
        result.append({'case_id': case_id, 'theme': theme, 'room_count': rooms,
            'difficulty': difficulty, 'controlled_host_seed': seed, 'blueprint_id': bp.blueprint_id,
            'payload': payload, 'payload_sha256': sha(body), 'payload_utf8_bytes': len(body),
            'input_token_upper': len(body) * 4 + 8192, 'output_token_upper': 6000,
            'cost_upper_units': units, 'cost_upper_cny': units / 1e9})
    if sum(x['cost_upper_units'] for x in result) > MAX_TOTAL_UNITS:
        raise ValueError('BATCH_COST_BOUND_EXCEEDED')
    return result


def prepare():
    before = source_map()
    cases = cases_and_payloads()
    if source_map() != before:
        raise ValueError('SOURCE_CHANGED_DURING_PREPARE')
    out = STAGE / 'automated' / ('preflight-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid4().hex[:8])
    preview = {'kind': 'offline_preflight_not_paid_execution', 'prepared_at_utc': stamp(),
        'sources': before, 'cases': cases, 'max_calls': MAX_CALLS,
        'max_total_units': MAX_TOTAL_UNITS, 'sum_cost_upper_cny': sum(x['cost_upper_units'] for x in cases) / 1e9,
        'automatic_retries': 0, 'provider': 'existing fixed official DeepSeek configuration',
        'scope': 'Five existing themes at 2/normal plus astronomy 3/hard; controlled existing Host choices, each once',
        'not_in_scope': ['old/new paired comparison', 'companion', 'evaluator', 'player database', 'browser'],
        'credentials_loaded': False, 'ledger_opened': False, 'network_calls': 0,
        'approval_required': True}
    path = out / 'preview.json'
    write(path, preview)
    print(json.dumps({'preview': str(path.relative_to(ROOT)), 'calls': MAX_CALLS,
        'cost_upper_cny': preview['sum_cost_upper_cny'], 'case_upper_cny': [x['cost_upper_cny'] for x in cases],
        'paid_calls': 0, 'credentials_loaded': False, 'ledger_opened': False}, ensure_ascii=False))


def approved_preview(preview_path, approval_path):
    # No credential/provider/ledger operation precedes these exact scope checks.
    preview_path = Path(preview_path).resolve()
    approval_path = Path(approval_path).resolve()
    if not preview_path.is_relative_to(STAGE.resolve()) or not approval_path.is_relative_to(STAGE.resolve()):
        raise ValueError('APPROVAL_PATH_OUTSIDE_STAGE')
    preview = json.loads(preview_path.read_text(encoding='utf-8'))
    approval = json.loads(approval_path.read_text(encoding='utf-8'))
    if (approval.get('approved') is not True
            or approval.get('preview_sha256') != sha(preview_path.read_bytes())
            or approval.get('max_calls') != MAX_CALLS
            or approval.get('max_total_units') != MAX_TOTAL_UNITS
            or not isinstance(approval.get('actual_user_approval_reference'), str)
            or not approval['actual_user_approval_reference'].strip()
            or preview.get('sources') != source_map()
            or preview.get('cases') != cases_and_payloads()
            or preview.get('max_calls') != MAX_CALLS
            or preview.get('max_total_units') != MAX_TOTAL_UNITS):
        raise ValueError('APPROVAL_OR_PREVIEW_MISMATCH')
    return preview


def pending_ids(ledger):
    with sqlite3.connect(ledger.path.as_uri() + '?mode=ro', uri=True) as connection:
        return {(row[0], row[1]) for row in connection.execute("SELECT id,state FROM budget_calls WHERE state IN ('reserved','unknown')")}


async def execute(preview_path, approval_path):
    global ACTIVE_RUN
    preview = approved_preview(preview_path, approval_path)
    run = STAGE / 'automated' / ('real-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid4().hex[:8])
    run.mkdir(parents=True, exist_ok=False)
    ACTIVE_RUN = run
    # One approval/preview can only be consumed once, including interrupted runs.
    marker = Path(preview_path).resolve().parent / 'execute-started.json'
    write(marker, {'started_at_utc': stamp(), 'run': str(run.relative_to(ROOT)), 'operator': 'Main'})
    from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider
    from backend.app.ai.budget import BudgetLedger
    from backend.app.ai.v5 import GenerationService, ServiceError
    from backend.app.domain import generation_content_v2 as content
    from backend.app.domain.generated import compile_level, GeneratedRules
    from backend.app.domain.generation_observability import safe_reason
    config = DeepSeekConfig.from_environment()
    if not config.api_key:
        raise ValueError('LOCAL_CREDENTIALS_NOT_CONFIGURED')
    ledger = BudgetLedger()
    before = ledger.snapshot()
    old_pending = pending_ids(ledger)
    if before['frozen'] or any(state == 'reserved' for _, state in old_pending) or before['remaining_cny'] * 1e9 < sum(x['cost_upper_units'] for x in preview['cases']):
        raise ValueError('BUDGET_OR_ACTIVE_CALL_BLOCKED')
    private = ROOT / 'data' / 'generation-reliability' / run.name
    records = []
    stop = None
    for case in preview['cases']:
        if source_map() != preview['sources'] or pending_ids(ledger) != old_pending:
            stop = 'SOURCE_OR_PENDING_CALL_CHANGED'
            break
        bp = content.select_blueprint(case['room_count'], case['difficulty'], seed=case['controlled_host_seed'])
        provider = DeepSeekProvider(config, ledger)
        row = {k: case[k] for k in ('case_id', 'theme', 'room_count', 'difficulty', 'controlled_host_seed', 'blueprint_id', 'cost_upper_cny')}
        row.update(attempted_at_utc=stamp(), admitted=False, reason=None, provider_call_id=None)
        with (run / 'attempts.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'case_id': case['case_id'], 'started_at_utc': row['attempted_at_utc']}) + '\n')

        class Capture:
            @property
            def last_response_metadata(self):
                return provider.last_response_metadata

            async def complete(self, messages, tools, limits, **kwargs):
                # Recheck the actual production payload against the reviewed preview.
                actual = {'model': config.model, 'messages': messages, 'max_tokens': limits.max_tokens,
                    'thinking': {'type': 'disabled'}, 'stream': False, 'response_format': {'type': 'json_object'}}
                if sha(encoded(actual)) != case['payload_sha256']:
                    raise ValueError('RUNTIME_PAYLOAD_MISMATCH')
                try:
                    reply = await provider.complete(messages, tools, limits, **kwargs)
                finally:
                    meta = provider.last_response_metadata or {}
                    if isinstance(meta.get('call_id'), str) and re.fullmatch(r'[A-Za-z0-9_-]{1,100}', meta['call_id']):
                        row['provider_call_id'] = meta['call_id']
                    if isinstance(meta.get('usage'), dict):
                        row['usage'] = {k: v for k, v in meta['usage'].items() if k in {'prompt_tokens', 'completion_tokens', 'prompt_cache_hit_tokens', 'total_tokens'} and type(v) is int}
                row['provider_call_id'] = reply.call_id
                row['usage'] = {k: v for k, v in (reply.usage or {}).items() if k in {'prompt_tokens', 'completion_tokens', 'prompt_cache_hit_tokens', 'total_tokens'} and type(v) is int}
                row['charged_upper_cny'] = reply.cost_upper_cny
                if config.api_key in (reply.content or ''):
                    raise ValueError('CREDENTIAL_IN_MODEL_OUTPUT')
                # Private diagnostic material is ignored under data/, never public evidence.
                write(private / (case['case_id'] + '-model-local.json'), {'content': reply.content})
                return reply

        try:
            with patch.object(content, 'select_blueprint', lambda *args, **kwargs: bp):
                draft = await GenerationService(lambda key: Capture()).generate(theme=case['theme'], room_count=case['room_count'], difficulty=case['difficulty'], api_key=config.api_key, draft_schema=None)
            compiled = compile_level(draft, case['room_count'], case['difficulty'])
            rules = GeneratedRules(compiled)
            state = rules.initial_state()
            for action in compiled.witness:
                state, _ = rules.apply_action(state, action['tool'], action['arguments'])
            if state.status != 'won':
                raise ValueError('WITNESS_DID_NOT_EXIT')
            row.update(admitted=True, reason='completed', witness_steps=len(compiled.witness), definition_hash=compiled.definition_hash)
            write(private / (case['case_id'] + '-definition-local.json'), compiled.private_dump())
        except ServiceError as error:
            row.update(error_code=error.code, reason=safe_reason(error.generation_diagnostic))
            if error.code != 'MODEL_INVALID_OUTPUT':
                stop = 'PROVIDER_OR_BUDGET_STOP'
        except Exception as error:
            row.update(error_code='LOCAL_VALIDATION_FAILED', reason='admission')
            code = str(error)
            if type(error) is ValueError and re.fullmatch(r'[A-Z_]{1,64}', code):
                row['validation_code'] = code
            # A measured compile rejection is a sample result; a pre-response or
            # local runtime anomaly stops instead of silently consuming more calls.
            if row['provider_call_id'] is None or code in {'CREDENTIAL_IN_MODEL_OUTPUT', 'RUNTIME_PAYLOAD_MISMATCH'}:
                stop = 'LOCAL_OR_CREDENTIAL_STOP'
        records.append(row)
        write(run / (case['case_id'] + '-result.json'), row)
        if pending_ids(ledger) != old_pending or ledger.snapshot()['frozen']:
            stop = 'NEW_UNKNOWN_OR_FROZEN_LEDGER'
        if stop:
            break
    result = {'finished_at_utc': stamp(), 'operator': 'Main', 'preview_sha256': sha(Path(preview_path).read_bytes()),
        'attempted_cases': len(records), 'admitted_cases': sum(x['admitted'] for x in records),
        'sample_admission_rate': sum(x['admitted'] for x in records) / len(records) if records else None,
        'cases': records, 'not_called_case_ids': [c['case_id'] for c in preview['cases'][len(records):]],
        'stop_reason': stop, 'ledger_before': before, 'ledger_after': ledger.snapshot(),
        'retries': 0, 'companion_calls': 0, 'evaluation_calls': 0, 'player_database_access': False,
        'limits': 'Small controlled after-only sample; no general success-rate, story-quality or human acceptance claim'}
    write(run / 'result.json', result)
    print(json.dumps({'result': str((run / 'result.json').relative_to(ROOT)), 'attempted': len(records), 'admitted': result['admitted_cases'], 'stop_reason': stop}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--execute', action='store_true')
    parser.add_argument('--preview')
    parser.add_argument('--approval')
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.preview and args.approval:
        asyncio.run(execute(args.preview, args.approval))
    else:
        parser.error('--execute requires a preview and actual new approval record')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Do not print arbitrary provider exceptions, local configuration or text.
        if ACTIVE_RUN is not None:
            write(ACTIVE_RUN / 'failure.json', {'stopped_at_utc': stamp(),
                'reason': 'PRECONDITION_OR_EXECUTION_FAILURE',
                'calls_not_inferred_from_exit': True, 'retry_allowed': False})
        print(json.dumps({'status': 'stopped', 'reason': 'PRECONDITION_OR_EXECUTION_FAILURE'}))
        raise SystemExit(1)
