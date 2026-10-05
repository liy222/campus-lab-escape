"""Finite paid-game QA. DO NOT execute before separate Main real-provider GO.

Exactly one AI turn, <=3 dispatched calls (below authorized <=2 turns/6 calls),
<=CNY0.50 additional conservative ledger charge. No automatic retry after error.
Uses existing canonical root ledger. First model call is forced get_inventory;
the next sees the actual tool result and may propose the known R1 cabinet action.
Credentials only read inside main after explicit CLI gate, never logged.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = (ROOT / 'data/ai-budget.sqlite').resolve()
SEGMENT_CAP = 500_000_000


def ledger_view():
    # Read existing ledger only; no replacement or independent cap.
    with closing(sqlite3.connect(CANONICAL)) as db:
        cap, frozen = db.execute('SELECT cap,frozen FROM budget_config WHERE id=1').fetchone()
        rows = [dict(zip(('call_id','scope','reserved','charged','state','reason','prompt_tokens','completion_tokens','cache_hit_tokens'), row))
                for row in db.execute('SELECT id,scope,reserved,charged,state,reason,prompt_tokens,completion_tokens,cache_hit_tokens FROM budget_calls ORDER BY created_at,id')]
    return {'canonical_ledger':str(CANONICAL),'cap_units':cap,'frozen':frozen,'calls':rows,
            'charged_units':sum(row['charged'] for row in rows)}


class FiniteProvider:
    provider_name = 'deepseek'
    model_name = 'deepseek-flash'
    def __init__(self, provider, start):
        self.provider, self.start, self.attempts = provider, start, 0
        self.last_response_metadata = None
    async def complete(self, messages, tools, limits, **kwargs):
        from backend.app.ai.provider import ProviderError
        self.last_response_metadata = None
        if self.attempts >= 3:
            raise ProviderError('AI_LIMIT_REACHED')
        choice = {'type':'function','function':{'name':'get_inventory'}} if self.attempts == 0 else 'auto'
        wire = json.loads(json.dumps(tools))
        for tool in wire:
            tool['function'].pop('strict', None)
        outgoing = {'model':self.model_name,'messages':messages,'max_tokens':limits.max_tokens,
                    'thinking':{'type':'disabled'},'stream':False,'tools':wire,'tool_choice':choice}
        encoded = json.dumps(outgoing,ensure_ascii=False,separators=(',', ':'),allow_nan=False).encode('utf-8')
        maximum = (len(encoded) * 4 + 8192) * 2000 + limits.max_tokens * 8000
        current = ledger_view()
        if current['frozen'] or current['charged_units']-self.start['charged_units']+maximum > SEGMENT_CAP:
            raise ProviderError('AI_BUDGET_EXHAUSTED')
        self.attempts += 1
        try:
            result = await self.provider.complete(messages,tools,limits,scope='game',tool_choice=choice)
        finally:
            self.last_response_metadata = self.provider.last_response_metadata
        if result.usage is None:
            raise ProviderError('MODEL_UNAVAILABLE',call_id=result.call_id)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',required=True)
    parser.add_argument('--main-real-go',required=True,help='Human-readable identifier of Main separate paid GO; not budget creation')
    args = parser.parse_args()
    if not CANONICAL.exists():
        raise SystemExit('Canonical existing ledger missing; no paid call attempted')
    folder = ROOT / 'evidence/qa' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-m3-real')
    folder.mkdir(parents=True,exist_ok=False)
    from tests.qa_runner import sources, git_read
    before = sources(True)
    started = datetime.now(timezone.utc).isoformat()
    exchanges, checks = [], []
    initial, outcome, actual = ledger_view(), 'NOT_EXECUTED', None
    secrets = []
    def sanitized(value):
        if isinstance(value,dict):
            return {k:('[REDACTED]' if k.lower() in {'token','authorization','x-session-token','api_key'} else sanitized(v)) for k,v in value.items()}
        if isinstance(value,list):
            return [sanitized(v) for v in value]
        if isinstance(value,str):
            for secret in secrets:
                if secret:value=value.replace(secret,'[REDACTED]')
        return value
    try:
        assert initial['cap_units'] == 10_000_000_000 and not initial['frozen']
        assert not any(row['state'] in {'reserved','unknown'} for row in initial['calls']), 'UNRESOLVED_LEDGER_NO_PAID_CALL'
        with tempfile.TemporaryDirectory(prefix='campus-qa-m3-real-') as temp:
            owned = Path(temp).resolve()
            assert owned.parent == Path(tempfile.gettempdir()).resolve() and owned.name.startswith('campus-qa-m3-real-')
            # Avoid import-time app opening user gameplay DB. No config fallback.
            os.environ['AI_PROVIDER']='mock'
            os.environ['SQLITE_PATH']=str(owned/'import-only.sqlite')
            from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider
            from backend.app.ai.budget import BudgetLedger
            from backend.app.ai.runtime import Runtime, RuntimeLimits
            from backend.app.main import create_app
            from fastapi.testclient import TestClient
            from jsonschema import Draft202012Validator, FormatChecker
            config=DeepSeekConfig.from_environment()
            secrets.append(config.api_key)
            assert config.api_key.strip(), 'MISSING_CREDENTIALS'
            ledger=BudgetLedger(CANONICAL)
            actual=FiniteProvider(DeepSeekProvider(config,ledger),initial)
            runtime=Runtime(actual,RuntimeLimits(format_retries=0))
            app=create_app(sqlite_path=owned/'game.sqlite',runtime=runtime)
            schema=json.loads((ROOT/'contracts/api.schema.json').read_text(encoding='utf-8'))
            with TestClient(app,raise_server_exceptions=False) as client:
                creation=client.post('/api/sessions',json={})
                assert creation.status_code == 201
                session=creation.json()['data']
                secrets.append(session['token'])
                sid=session['session_id'];headers={'X-Session-Token':session['token']};state=session['visible_state']
                def exchange(path,request,definition):
                    response=client.post(f'/api/sessions/{sid}/{path}',headers=headers,json=request)
                    body=response.json()
                    Draft202012Validator({'$defs':schema['$defs'],'$ref':'#/$defs/'+(definition if body.get('ok') else 'error_response')},format_checker=FormatChecker()).validate(body)
                    exchanges.append(sanitized({'path':path,'request':request,'http_status':response.status_code,'response':body}))
                    assert response.status_code == 200, 'GAME_HTTP_FAILURE'
                    return body
                for obj in ('r1_note','r1_cabinet'):
                    request={'request_id':uuid.uuid4().hex,'revision':state['revision'],'generation':state['generation'],'tool':'inspect','arguments':{'object_id':obj}}
                    state=exchange('actions',request,'action_response')['data']['visible_state']
                assert state['revision'] == 2 and len(state['clues']) == 2
                request={'request_id':uuid.uuid4().hex,'revision':state['revision'],'generation':state['generation'],
                         'message':'请先调用 get_inventory 查看当前背包，等待工具真实结果，然后仅依据已发现的值班便签及柜门顺序提出 submit_code 值班柜建议。不要执行进度动作，等待我确认。最终只返回要求的 JSON。'}
                body=exchange('ai/turns',request,'ai_turn_response');data=body['data']
                assert data['status'] == 'completed' and data['stop_reason'] is None, 'REAL_TURN_STOPPED_NO_RETRY'
                proposal=data['proposal']
                assert proposal and proposal['tool']=='submit_code' and proposal['arguments']=={'target_id':'r1_cabinet','code':'382'}, 'REAL_PROPOSAL_MISSING_OR_UNEXPECTED_NO_RETRY'
                assert set(proposal['clue_refs']) <= {'r1_note_clue','r1_cabinet_clue'} and proposal['clue_refs'], 'REAL_CLUE_REFS_MISSING'
                assert data['visible_state']['revision'] == 2
                with closing(sqlite3.connect(owned/'game.sqlite')) as db:
                    trace=json.loads(db.execute('SELECT trace_json FROM ai_turns WHERE turn_id=?',(data['turn_id'],)).fetchone()[0])
                assert any(e.get('kind')=='read_tool' and e.get('tool')=='get_inventory' and e.get('ok') for e in trace), 'REAL_TOOL_RETURN_MISSING'
                attempts=actual.attempts
                replay=exchange('ai/turns',request,'ai_turn_response')
                assert replay['data']['turn_id']==data['turn_id'] and actual.attempts==attempts
                confirmed=exchange(f"proposals/{proposal['proposal_id']}/confirm",{},'action_response')
                receipt=confirmed['data']['receipt']
                assert receipt['revision_before']==2 and receipt['revision_after']==3 and confirmed['data']['proposal']['status']=='committed'
                assert confirmed['data']['visible_state']['inventory']==[]
                again=exchange(f"proposals/{proposal['proposal_id']}/confirm",{},'action_response')
                assert again['data']['replayed'] and again['data']['receipt']==receipt and actual.attempts==attempts
                (folder/'public-runtime-trace.json').write_text(json.dumps(sanitized(trace),ensure_ascii=False,indent=2),encoding='utf-8')
                checks.append({'AI_turns':1,'provider_attempts':attempts,'tool':'get_inventory','proposal':proposal,'confirm_receipt':receipt,'replays_no_new_provider':True})
                outcome='PASS'
    except Exception as error:
        # Fixed category only, no raw exception/provider body/header/token.
        outcome='FAIL'
        checks.append({'stopped':True,'failure_type':type(error).__name__,'retry':False})
    final=ledger_view();after=sources(True)
    newrows=[row for row in final['calls'] if row['call_id'] not in {old['call_id'] for old in initial['calls']}]
    delta=final['charged_units']-initial['charged_units']
    if delta > SEGMENT_CAP or len(newrows)>3 or before!=after:outcome='FAIL'
    (folder/'http-exchanges.json').write_text(json.dumps(sanitized(exchanges),ensure_ascii=False,indent=2),encoding='utf-8')
    (folder/'checks.json').write_text(json.dumps(sanitized(checks),ensure_ascii=False,indent=2),encoding='utf-8')
    result={'candidate':args.candidate,'separate_main_real_go':args.main_real_go,'command':[sys.executable,'-m','tests.real_m3_runner',*sys.argv[1:]],
      'head':git_read('rev-parse','HEAD'),'start':started,'end':datetime.now(timezone.utc).isoformat(),'status':outcome,'exit_code':0 if outcome=='PASS' else 1,
      'AI_turns_max':1,'provider_attempts_max':3,'additional_cap_cny':.5,'canonical_ledger':str(CANONICAL),'ledger_before':initial,'ledger_after':final,
      'actual_new_ledger_rows':newrows,'additional_conservative_charge_cny':delta/1e9,'actual_provider_attempts':actual.attempts if actual else 0,
      'source_sha256_before':before,'source_sha256_after':after,'privacy':'No key/token/headers/raw provider body/prompt copied; only public game results and typed sanitized runtime trace.'}
    result['evidence_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}
    (folder/'run.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'evidence':str(folder),'status':outcome,'exit_code':result['exit_code'],'actual_provider_attempts':result['actual_provider_attempts'],'additional_conservative_charge_cny':delta/1e9},ensure_ascii=False))
    return result['exit_code']


if __name__=='__main__':
    raise SystemExit(main())
