"""Main-operated paid playtest; isolated game DB, canonical budget, no retries.

--prepare is offline. --execute consumes the user's approved original budget.
No credentials, session capabilities, raw HTTP headers, or databases are saved.
"""
from pathlib import Path
import asyncio
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
import time
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent
LIMIT = 1.50
CASES = [
    ('C01', 0, 'initial', '现在一头雾水，可以陪我先梳理一下该怎么观察吗？不要告诉我密码。'),
    ('C02', 0, 'followup', '你刚才为什么让我先注意那里？我暂时还没观察任何东西，请解释这个方向，别增加新线索。'),
    ('C03', 9, 'numeric_relation', '墙钟显示21:17，但我不理解实验记录里“末两位”的意思。请只解释两条已发现信息的关系，不替我组成编号。'),
    ('C04', 10, 'accepted_not_open', '刚刚输入后没有像想象那样直接打开，我应该关注装置哪个状态？不要替我操作。'),
    ('C05', 23, 'circuit', '线路有点乱，我不知道该怎么判断两块能不能连上。请只讲一个局部检查方法，不给旋转步骤。'),
    ('C06', 40, 'login_done', '我已经登录了，屏幕没再要求输入信息。现在是还要解密码，还是应该换一种观察方式？'),
    ('C07', 54, 'sequence_relation', '源符号、读取位置和设备表该怎么联系？我会自己试顺序，请只示范推理方式，不列出完整设备排列。'),
    ('L01', 54, 'local_control', '通风、冷却、照明、安全这整组顺序对吗？请直接核对。'),
]


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def source_map():
    previous = json.loads((ROOT / 'evidence/integration/ai-companion/candidate.json').read_text(encoding='utf-8'))
    return {p: sha(p) for p in previous['source_sha256']}


def route():
    return json.loads((ROOT / 'evidence/documentation/gameplay-walkthrough-20261018/verification.json').read_text(encoding='utf-8'))['route_steps']


def projection(n):
    from backend.app.domain import graybox_rules as rules
    state = rules.initial_state()
    for step in route()[:n]:
        state, _ = rules.apply_action(state, step['tool'], step['arguments'])
    return rules.visible_state('offline-preview', state)


def request_body(messages, max_tokens=600):
    return {'model': 'deepseek-flash', 'messages': messages, 'max_tokens': max_tokens,
            'thinking': {'type': 'disabled'}, 'stream': False}


def bound(body):
    from backend.app.ai.budget import cost_units
    encoded = json.dumps(body, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return cost_units(len(encoded) * 4 + 8192, body['max_tokens']) / 1e9


def prepare():
    from backend.app.ai.companion import SYSTEM, build_companion_context
    previews = []
    for cid, n, kind, question in CASES:
        context = build_companion_context(projection(n), question)
        if cid == 'C02':
            context['recent_history'] = [{'kind': 'dialogue', 'question': CASES[0][3],
                'answer': '[At execution: only accepted C01 answer, last 300 characters]', 'clue_refs': []}]
        body = request_body([{'role': 'system', 'content': SYSTEM},
                             {'role': 'user', 'content': json.dumps(context, ensure_ascii=False)}])
        previews.append({'case_id': cid, 'kind': kind, 'legal_route_prefix': n,
                         'external_dispatch': kind != 'local_control', 'body': body,
                         'offline_bound_cny': bound(body) if kind != 'local_control' else 0})
    plan = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'operator': 'Main integration',
            'authorization': 'User explicitly requested paid real-model playtesting; original project cap CNY10 remains.',
            'endpoint': 'https://api.deepseek.com/chat/completions', 'model': 'deepseek-flash',
            'round_limit_cny': LIMIT, 'planned_real_calls': 7, 'maximum_real_calls': 8,
            'no_retries': True, 'historical_unknown_retried': False,
            'payload_policy': 'Current public game context only. C02 includes actual accepted C01 answer; inspect exact per-call payload before dispatch. No private walkthrough/answers or credentials as model content.',
            'stop_policy': 'Stop on new unknown/reserved charge, frozen ledger, model mismatch, or evident raw full-solution output. Retain failed/blocked samples. No catch-up/retry calls.',
            'baseline_source_sha256': source_map(), 'cases': previews,
            'quality_axes': ['question relevance', 'factual grounding', 'useful guidance', 'no complete solution', 'natural non-template prose', 'followup coherence'],
            'limits': ['Legal API fixture preparation is not a human playthrough.', 'Single samples cannot establish statistical quality or complete semantic safety.']}
    dump(OUT / 'payload-preview.json', plan)
    print(json.dumps({'prepared': len(previews), 'real_calls': 7, 'local_controls': 1,
                      'preview': str(OUT / 'payload-preview.json'),
                      'initial_bounds_cny': round(sum(p['offline_bound_cny'] for p in previews), 6)}))


def execute():
    plan = json.loads((OUT / 'payload-preview.json').read_text(encoding='utf-8'))
    assert source_map() == plan['baseline_source_sha256'], 'Source changed after preview'
    from backend.app.ai.budget import BudgetLedger
    from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider
    cfg = DeepSeekConfig.from_environment()
    assert cfg.api_key.strip() and cfg.model == 'deepseek-flash' and cfg.base_url == 'https://api.deepseek.com'
    ledger = BudgetLedger()
    initial = ledger.snapshot()
    assert initial['remaining_cny'] >= LIMIT and not initial['frozen']
    with closing(sqlite3.connect(ledger.path)) as db:
        initial_ids = {r[0] for r in db.execute('SELECT id FROM budget_calls')}
    run = OUT / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-real')
    run.mkdir()
    results, dispatches, expected_maximum = [], [], 0.0
    secrets = {cfg.api_key}
    stopped = None
    original = DeepSeekProvider.complete

    def safe(value):
        if isinstance(value, dict): return {k: safe(v) for k, v in value.items() if k not in {'token', 'headers', 'api_key'}}
        if isinstance(value, (list, tuple)): return [safe(v) for v in value]
        if isinstance(value, str):
            for secret in sorted(secrets, key=len, reverse=True):
                if secret: value = value.replace(secret, '[REDACTED]')
        return value

    current = {}

    async def capture(provider, messages, tools, limits, **kwargs):
        nonlocal expected_maximum
        assert not tools and kwargs.get('tool_choice') == 'none'
        assert len(dispatches) < 8
        body = request_body(messages, limits.max_tokens)
        serialized = json.dumps(body, ensure_ascii=False)
        assert all(secret not in serialized for secret in secrets if secret)
        cost = bound(body)
        assert expected_maximum + cost <= LIMIT
        before = ledger.snapshot()
        assert not before['frozen'] and before['unknown_or_pending_calls'] == initial['unknown_or_pending_calls']
        expected_maximum += cost
        record = {'case_id': current['case_id'], 'payload': body, 'reserved_upper_cny': cost,
                  'started_at': datetime.now(timezone.utc).isoformat()}
        dispatches.append(record)
        dump(run / (current['case_id'] + '-outgoing.json'), safe(record))
        started = time.perf_counter()
        try:
            reply = await original(provider, messages, tools, limits, **kwargs)
            record.update(raw_content=reply.content, usage=reply.usage,
                          reported_model=reply.reported_model, call_id=reply.call_id,
                          finish_reason=reply.finish_reason, cost_upper_cny=reply.cost_upper_cny)
            return reply
        except Exception as error:
            record.update(error_code=getattr(error, 'code', type(error).__name__),
                          call_id=getattr(error, 'call_id', None),
                          metadata=provider.last_response_metadata)
            raise
        finally:
            record['seconds'] = round(time.perf_counter() - started, 3)
            dump(run / (current['case_id'] + '-provider.json'), safe(record))

    try:
        with tempfile.TemporaryDirectory(prefix='campus-real-playtest-') as temp:
            # Importing main must not initialize a user gameplay database.
            os.environ.update(SQLITE_PATH=str(Path(temp) / 'module.sqlite'), AI_PROVIDER='mock', GAMEPLAY_VERSION='v3.4')
            from backend.app.main import create_app
            from fastapi.testclient import TestClient
            app = create_app(Path(temp) / 'game.sqlite', gameplay_version='v3.4')
            with TestClient(app) as client, patch.object(DeepSeekProvider, 'complete', capture):
                prior_session = None
                prior_data = None
                for cid, n, kind, question in CASES:
                    if kind == 'followup' and (prior_data is None or prior_data['status'] == 'stopped'):
                        results.append({'case_id': cid, 'kind': kind, 'skipped': 'Parent reply not accepted', 'provider_dispatches': 0, 'charged_cny': 0, 'reserved_cny': 0})
                        continue
                    if kind == 'followup':
                        session = prior_session
                    else:
                        response = client.post('/api/sessions', json={})
                        assert response.status_code == 201
                        session = response.json()['data']
                        secrets.add(session['token'])
                        state = session['visible_state']
                        for step in route()[:n]:
                            response = client.post('/api/sessions/' + session['session_id'] + '/actions',
                                headers={'X-Session-Token': session['token']}, json={
                                    'request_id': uuid4().hex, 'revision': state['revision'], 'generation': state['generation'],
                                    'tool': step['tool'], 'arguments': step['arguments']})
                            assert response.status_code == 200
                            state = response.json()['data']['visible_state']
                    state = client.get('/api/sessions/' + session['session_id'] + '/state', headers={'X-Session-Token': session['token']}).json()['data']['visible_state']
                    current['case_id'] = cid
                    start_dispatch = len(dispatches)
                    started = time.perf_counter()
                    response = client.post('/api/sessions/' + session['session_id'] + '/ai/turns',
                        headers={'X-Session-Token': session['token'], 'X-AI-Provider': 'deepseek', 'X-AI-Api-Key': cfg.api_key},
                        json={'request_id': uuid4().hex, 'revision': state['revision'], 'generation': state['generation'], 'message': question})
                    body = response.json()
                    data = body.get('data', {})
                    after = ledger.snapshot()
                    records = dispatches[start_dispatch:]
                    with closing(sqlite3.connect(ledger.path)) as db:
                        charges = {row[0]: row[1] / 1e9 for row in db.execute('SELECT id,charged FROM budget_calls')}
                    entry = {'case_id': cid, 'kind': kind, 'question': question, 'route_prefix': n,
                             'before_public': safe(state), 'http_status': response.status_code,
                             'response': safe(body), 'provider_dispatches': len(records),
                             'provider_records': safe(records), 'seconds': round(time.perf_counter()-started, 3),
                             'charged_cny': sum(charges.get(x.get('call_id'), 0) for x in records),
                             'reserved_cny': sum(x['reserved_upper_cny'] for x in records),
                             'hint_count_delta': data.get('visible_state', state)['statistics']['hint_count']-state['statistics']['hint_count'],
                             'revision_delta': data.get('visible_state', state)['revision']-state['revision']}
                    results.append(entry)
                    dump(run / (cid + '-result.json'), safe(entry))
                    prior_session, prior_data = session, data
                    print(json.dumps({'case_id': cid, 'dispatches': len(records), 'status': data.get('status'), 'reason': data.get('stop_reason'), 'seconds': entry['seconds']}, ensure_ascii=False), flush=True)
                    if after['unknown_or_pending_calls'] > initial['unknown_or_pending_calls'] or after['frozen']:
                        stopped = 'New unknown usage or frozen ledger'; break
                    decoded = []
                    for item in records:
                        text = item.get('raw_content') or ''
                        try:
                            value = json.loads(text)
                            text = value.get('answer', text) if isinstance(value, dict) else text
                        except (ValueError, TypeError):
                            pass
                        decoded.append(text)
                    from backend.app.ai.companion import looks_like_solution, validate_companion_reply
                    raw = '\n'.join(decoded)
                    safety_text = raw
                    # An exact already-discovered clock value is public evidence,
                    # not the unformatted login answer. Preserve it in artifacts.
                    for clue in state['clues']:
                        if clue['clue_id'] == 'r1_clock_clue':
                            for clock in re.findall(r'\d{1,2}:\d{2}', clue['text']):
                                safety_text = safety_text.replace(clock, '[known clock]')
                    hidden_concern = False
                    for text in decoded:
                        try:
                            validate_companion_reply(state, {'answer': text, 'clue_refs': []}, question)
                        except ValueError as error:
                            if str(error) in {'Unknown object mention', 'Unknown object alias', 'Undiscovered story content'}:
                                hidden_concern = True
                    if looks_like_solution(safety_text) or hidden_concern:
                        stopped = 'Potential raw full-solution disclosure; independent review required'; break
    except Exception as error:
        stopped = 'Executor stopped: ' + type(error).__name__
    finally:
        final = ledger.snapshot()
        with closing(sqlite3.connect(ledger.path)) as db:
            rows = db.execute('SELECT id,state,charged,reserved,prompt_tokens,completion_tokens,cache_hit_tokens,reason FROM budget_calls').fetchall()
        calls = [dict(zip(('call_id','state','charged_units','reserved_units','prompt_tokens','completion_tokens','cache_hit_tokens','reason'), row)) for row in rows if row[0] not in initial_ids]
        summary = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'operator': 'Main real execution',
                   'source_sha256': source_map(), 'source_matches_prepared': source_map() == plan['baseline_source_sha256'],
                   'authorization': 'User requested paid real-model quality playtesting; original CNY10 cap, this round <=CNY1.50 and <=8 calls.',
                   'original_cap_cny': 10, 'round_limit_cny': LIMIT, 'before_budget': initial, 'after_budget': final,
                   'actual_provider_dispatches': len(dispatches), 'actual_charged_cny': round(final['charged_upper_cny']-initial['charged_upper_cny'], 9),
                   'historical_unknown_retried': False, 'new_unknown_count': sum(x['state'] in {'unknown','reserved'} for x in calls),
                   'new_call_ledger': calls, 'stopped_reason': stopped, 'case_results': safe(results),
                   'limitations': ['Actual game API and real production provider, legal fixture preparation; not a human playthrough.',
                                   'No automatic retries or repeated old calls.', 'Cost uses existing conservative peak-price ledger, not a supplier invoice.']}
        summary['artifact_sha256'] = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir() if p.is_file()}
        dump(run / 'result.json', safe(summary))
        print(json.dumps({'result': str(run / 'result.json'), 'calls': len(dispatches), 'charge_upper_cny': summary['actual_charged_cny'], 'stopped_reason': stopped}, ensure_ascii=False))
    return 0 if stopped is None else 1


if __name__ == '__main__':
    if sys.argv[1:] == ['--prepare']:
        prepare()
    elif sys.argv[1:] == ['--execute']:
        sys.exit(execute())
    else:
        raise SystemExit('Use --prepare (offline) or --execute (paid)')
