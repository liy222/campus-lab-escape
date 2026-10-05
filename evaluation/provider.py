"""Owned evaluator adapter and existing-ledger client; target code is never imported."""
from __future__ import annotations

import asyncio
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3

from .common import EvaluationError, PROJECT_ROOT, exact_keys, strict_json

CAP = 10_000_000_000
MISS, HIT, OUTPUT = 2000, 40, 8000  # integer 1e-9 CNY units, approved peak rates
PRODUCTION_LEDGER = Path('D:/深度能力/data/ai-budget.sqlite')
OFFICIAL_BASE = 'https://api.deepseek.com'
MODEL = 'deepseek-flash'
REPORTED_MODELS = {'deepseek-flash', 'deepseek-v4.1-flash', 'DeepSeek-V4.1-Flash'}
CALL_COLUMNS = {'id', 'scope', 'created_at', 'reserved', 'charged', 'state', 'reason',
                'prompt_tokens', 'completion_tokens', 'cache_hit_tokens'}


def cost_units(prompt, completion, cache_hit=0):
    if any(type(x) is not int or x < 0 for x in (prompt, completion, cache_hit)) or cache_hit > prompt:
        raise EvaluationError('INVALID_USAGE')
    return (prompt - cache_hit) * MISS + cache_hit * HIT + completion * OUTPUT


class ExistingLedger:
    """Opens mode=rw; never CREATE, mkdir, initialize, reset, or change cap."""
    def __init__(self, *, _fake_path=None):
        self.fake = _fake_path is not None
        self.path = Path(_fake_path) if self.fake else PRODUCTION_LEDGER
        if not self.fake and PROJECT_ROOT.resolve() != Path('D:/深度能力').resolve():
            raise EvaluationError('UNAPPROVED_LEDGER_ROOT')
        if not self.path.is_file() or self.path.is_symlink() or getattr(self.path.lstat(), 'st_file_attributes', 0) & 0x400:
            raise EvaluationError('EXISTING_LEDGER_REQUIRED')
        # Check every ancestor, including data: no production junction redirection.
        for parent in self.path.parents:
            if parent.is_symlink() or getattr(parent.lstat(), 'st_file_attributes', 0) & 0x400:
                raise EvaluationError('LEDGER_REPARSE_POINT')
        with closing(self._connect()) as db:
            config = {r[1] for r in db.execute('PRAGMA table_info(budget_config)')}
            calls = {r[1] for r in db.execute('PRAGMA table_info(budget_calls)')}
            if config != {'id', 'cap', 'frozen'} or calls != CALL_COLUMNS:
                raise EvaluationError('LEDGER_SCHEMA_MISMATCH')
            rows = db.execute('SELECT id,cap,frozen FROM budget_config').fetchall()
            if len(rows) != 1 or rows[0][0] != 1 or rows[0][1] != CAP or rows[0][2] not in (0, 1):
                raise EvaluationError('BUDGET_CONFIG_MISMATCH')

    def _connect(self):
        # URI quoted by pathlib; mode=rw fails if someone removes the existing file.
        return sqlite3.connect(self.path.resolve().as_uri() + '?mode=rw', uri=True, timeout=15, isolation_level=None)

    def snapshot(self):
        with closing(self._connect()) as db:
            cap, frozen = db.execute('SELECT cap,frozen FROM budget_config WHERE id=1').fetchone()
            charged, calls = db.execute('SELECT COALESCE(SUM(charged),0),COUNT(*) FROM budget_calls').fetchone()
            pending = db.execute("SELECT COUNT(*) FROM budget_calls WHERE state IN ('reserved','unknown')").fetchone()[0]
        return {'cap_units': cap, 'charged_upper_units': charged, 'remaining_units': max(0, cap-charged),
                'calls': calls, 'unknown_or_pending_calls': pending, 'frozen': bool(frozen), 'fake_ledger': self.fake}

    def assert_ready(self):
        """Paid entry preflight only; reserve repeats the check under its write lock."""
        snapshot=self.snapshot()
        if snapshot['cap_units']!=CAP or snapshot['frozen']:
            raise EvaluationError('AI_BUDGET_EXHAUSTED')
        if snapshot['unknown_or_pending_calls']:
            raise EvaluationError('PRIOR_CALL_UNKNOWN_STOP')
        return snapshot

    def reserve(self, bound, gate):
        if type(bound) is not int or bound <= 0: raise EvaluationError('INVALID_RESERVATION')
        prefix = 'eval_' + gate['approval_id'] + '_'
        with closing(self._connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            # All scopes share the human-approved allowance. An unsettled call
            # from any gate/game/experiment/probe blocks before a new reservation.
            pending=db.execute("SELECT COUNT(*) FROM budget_calls WHERE state IN ('reserved','unknown')").fetchone()[0]
            if pending:raise EvaluationError('PRIOR_CALL_UNKNOWN_STOP')
            cap, frozen = db.execute('SELECT cap,frozen FROM budget_config WHERE id=1').fetchone()
            charged = db.execute('SELECT COALESCE(SUM(charged),0) FROM budget_calls').fetchone()[0]
            rows = db.execute("SELECT id,charged,state FROM budget_calls WHERE scope='evaluation' AND substr(id,1,?)=?", (len(prefix),prefix)).fetchall()
            if frozen or cap != CAP or charged + bound > cap: raise EvaluationError('AI_BUDGET_EXHAUSTED')
            if any(r[2] != 'settled' for r in rows): raise EvaluationError('PRIOR_CALL_UNKNOWN_STOP')
            if len(rows) >= gate['max_calls'] or sum(r[1] for r in rows) + bound > gate['max_cost_units']:
                raise EvaluationError('EVALUATION_GATE_EXHAUSTED')
            call_id = prefix + str(len(rows) + 1)
            try:
                db.execute("INSERT INTO budget_calls(id,scope,created_at,reserved,charged,state) VALUES(?,'evaluation',?,?,?,'reserved')",
                           (call_id, datetime.now(timezone.utc).isoformat(), bound, bound))
            except sqlite3.IntegrityError: raise EvaluationError('DUPLICATE_CALL_ID') from None
            db.commit()
        return call_id

    def settle(self, call_id, prompt, completion, hit):
        amount = cost_units(prompt, completion, hit)
        with closing(self._connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT reserved,state,charged,prompt_tokens,completion_tokens,cache_hit_tokens FROM budget_calls WHERE id=?', (call_id,)).fetchone()
            if row is None: raise EvaluationError('UNKNOWN_CALL_ID')
            if row[1] == 'settled':
                if list(row[3:]) != [prompt, completion, hit]: raise EvaluationError('SETTLEMENT_CONFLICT')
                return row[2]
            if row[1] != 'reserved': raise EvaluationError('SETTLEMENT_CONFLICT')
            overrun = amount > row[0]
            db.execute("UPDATE budget_calls SET charged=?,state='settled',reason=?,prompt_tokens=?,completion_tokens=?,cache_hit_tokens=? WHERE id=?",
                       (amount, 'BOUND_EXCEEDED' if overrun else None, prompt, completion, hit, call_id))
            if overrun: db.execute('UPDATE budget_config SET frozen=1 WHERE id=1')
            db.commit()
        if overrun: raise EvaluationError('COST_BOUND_EXCEEDED')
        return amount

    def retain(self, call_id, reason):
        if not re.fullmatch(r'[A-Z_]{1,64}',reason): raise EvaluationError('INVALID_REASON')
        with closing(self._connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute("UPDATE budget_calls SET state='unknown',reason=? WHERE id=? AND state='reserved'", (reason,call_id))
            db.commit()

    def freeze(self):
        with closing(self._connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE budget_config SET frozen=1 WHERE id=1')
            db.commit()


def validate_gate(gate, *, input_hash, fake=False):
    exact_keys(gate, ['approval_id','approved_by','purpose','input_sha256','max_calls','max_cost_units',
                      'max_tokens','timeout_seconds','expires_at','credential_env','base_url','model'])
    if not isinstance(gate['approval_id'],str) or not re.fullmatch(r'[A-Za-z0-9-]{1,40}',gate['approval_id']):
        raise EvaluationError('INVALID_APPROVAL_ID')
    if gate['approved_by'] != ('SYNTHETIC_TEST_ONLY' if fake else 'Main'):
        raise EvaluationError('MAIN_PAID_GO_REQUIRED')
    if gate['purpose'] not in {'calibration','claims'} or gate['input_sha256'] != input_hash:
        raise EvaluationError('GATE_INPUT_MISMATCH')
    for key,maximum in [('max_calls',100),('max_tokens',1000),('max_cost_units',CAP)]:
        if type(gate[key]) is not int or not 1 <= gate[key] <= maximum: raise EvaluationError('INVALID_GATE_LIMITS')
    if type(gate['timeout_seconds']) not in (int,float) or not 0 < gate['timeout_seconds'] <= 20:
        raise EvaluationError('INVALID_GATE_LIMITS')
    if gate['base_url'] != OFFICIAL_BASE or gate['model'] != MODEL or gate['credential_env'] != 'EVALUATION_MODEL_API_KEY':
        raise EvaluationError('UNAPPROVED_PROVIDER_CONFIG')
    try: expires = datetime.fromisoformat(gate['expires_at'].replace('Z','+00:00'))
    except (ValueError,TypeError): raise EvaluationError('INVALID_GATE_EXPIRY') from None
    if expires.tzinfo is None or datetime.now(timezone.utc) >= expires: raise EvaluationError('GATE_EXPIRED')


@dataclass(frozen=True)
class Suggestion:
    content: str
    metadata: dict


class MockProvider:
    """Explicit scripted suggestions, no real usage or paid calls."""
    mode = 'mock'
    def __init__(self, replies): self.replies, self.calls = list(replies), 0
    async def complete(self, messages):
        self.calls += 1
        if not self.replies: raise EvaluationError('MOCK_REPLIES_EXHAUSTED')
        value = self.replies.pop(0)
        if isinstance(value, Exception): raise value
        return Suggestion(json.dumps(value,ensure_ascii=False,allow_nan=False),
                          {'mode':'mock','actual_network_call':False,'usage':None,'call_id':None,'cost_upper_units':None})


class PaidProvider:
    mode = 'paid'
    def __init__(self, gate, input_hash):
        validate_gate(gate,input_hash=input_hash)
        self.gate, self.ledger, self.transport = gate, ExistingLedger(), None
        self.ledger.assert_ready()
        # Only trusted evaluator config may select this fixed credential variable.
        self.key = os.environ.get('EVALUATION_MODEL_API_KEY','')
        if not self.key.strip(): raise EvaluationError('MISSING_EVALUATOR_CREDENTIALS')
        self.calls = 0
        self.last_metadata = None

    async def complete(self,messages):
        import httpx
        self.last_metadata=None
        validate_gate(self.gate,input_hash=self.gate['input_sha256'],fake=self.mode=='fake')
        if not isinstance(messages,list) or not 1 <= len(messages) <= 3 or any(not isinstance(m,dict) or set(m)!={'role','content'} or m['role'] not in {'system','user'} or not isinstance(m['content'],str) for m in messages):
            raise EvaluationError('INVALID_MESSAGES')
        payload={'model':MODEL,'messages':messages,'max_tokens':self.gate['max_tokens'],
                 'thinking':{'type':'disabled'},'stream':False}
        encoded=json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
        input_bound=len(encoded)*4+8192
        if input_bound>1_000_000: raise EvaluationError('INPUT_TOO_LARGE')
        call_id=self.ledger.reserve(cost_units(input_bound,self.gate['max_tokens']),self.gate)
        self.calls+=1
        settled=False
        self.last_metadata={'mode':self.mode,'actual_network_call':self.mode=='paid','call_id':call_id,'usage':None,
                            'requested_model':MODEL,'cost_upper_units':cost_units(input_bound,self.gate['max_tokens'])}
        try:
            async with httpx.AsyncClient(transport=self.transport,trust_env=False,follow_redirects=False,timeout=self.gate['timeout_seconds']) as client:
                async with asyncio.timeout(self.gate['timeout_seconds']):
                    response=await client.post(OFFICIAL_BASE+'/chat/completions',content=encoded,
                                              headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'})
            if response.status_code!=200: raise EvaluationError('MODEL_AUTH_ERROR' if response.status_code in (401,403) else 'MODEL_UNAVAILABLE')
            if len(response.content)>1_000_000: raise EvaluationError('MODEL_INVALID_OUTPUT')
            body=strict_json(response.content)
            usage=body.get('usage') if isinstance(body,dict) else None
            if isinstance(usage,dict):
                p,c,h=usage.get('prompt_tokens'),usage.get('completion_tokens'),usage.get('prompt_cache_hit_tokens',0)
                if all(type(x) is int and x>=0 for x in (p,c,h)) and h<=p and type(usage.get('total_tokens')) is int and usage['total_tokens']==p+c and usage.get('prompt_cache_miss_tokens',p-h)==p-h:
                    normalized={'prompt_tokens':p,'completion_tokens':c,'total_tokens':p+c,'prompt_cache_hit_tokens':h}
                    self.last_metadata['usage']=normalized
                    amount=self.ledger.settle(call_id,p,c,h);settled=True
                    self.last_metadata['cost_upper_units']=amount
                    if p>input_bound or c>self.gate['max_tokens']:
                        self.ledger.freeze();raise EvaluationError('TOKEN_BOUND_EXCEEDED')
            if not isinstance(body,dict) or body.get('model') not in REPORTED_MODELS:
                self.ledger.freeze();raise EvaluationError('UNAPPROVED_REPORTED_MODEL')
            self.last_metadata['reported_model']=body['model']
            choices=body.get('choices')
            if not isinstance(choices,list) or len(choices)!=1 or not isinstance(choices[0],dict): raise EvaluationError('MODEL_INVALID_OUTPUT')
            choice=choices[0];message=choice.get('message')
            if choice.get('finish_reason')!='stop' or not isinstance(message,dict) or set(message)-{'role','content','reasoning_content'} or message.get('role')!='assistant' or message.get('reasoning_content') or not isinstance(message.get('content'),str) or not message['content']:
                raise EvaluationError('MODEL_INVALID_OUTPUT')
            self.last_metadata['finish_reason']='stop'
            if not settled: self.ledger.retain(call_id,'MISSING_USAGE')
            return Suggestion(message['content'],dict(self.last_metadata))
        except (TimeoutError,httpx.TimeoutException):
            self.ledger.retain(call_id,'MODEL_TIMEOUT');raise EvaluationError('MODEL_TIMEOUT') from None
        except httpx.HTTPError:
            self.ledger.retain(call_id,'MODEL_UNAVAILABLE');raise EvaluationError('MODEL_UNAVAILABLE') from None
        except EvaluationError as error:
            if not settled:self.ledger.retain(call_id,error.code)
            raise
        except BaseException:
            if not settled:self.ledger.retain(call_id,'INTERRUPTED_OR_INTERNAL')
            raise


class FakePaidProvider(PaidProvider):
    """Transport fake only, never reachable through CLI --mode paid."""
    mode='fake'
    def __init__(self,gate,input_hash,*,ledger_path,transport):
        validate_gate(gate,input_hash=input_hash,fake=True)
        if Path(ledger_path).resolve()==PRODUCTION_LEDGER.resolve(): raise EvaluationError('FAKE_CANNOT_USE_PRODUCTION_LEDGER')
        import httpx
        if not isinstance(transport,httpx.MockTransport): raise EvaluationError('EXPLICIT_FAKE_TRANSPORT_REQUIRED')
        self.gate,self.ledger,self.transport=gate,ExistingLedger(_fake_path=ledger_path),transport
        self.key='SYNTHETIC_TEST_KEY';self.calls=0;self.last_metadata=None
