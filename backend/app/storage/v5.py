"""V5 account ownership over the existing Store transaction and receipt machinery."""
from __future__ import annotations
import hashlib
import hmac
import json
import secrets
import sqlite3
import threading
import time
from contextlib import closing
from pathlib import Path
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from .sqlite import Store, canonical, new_id, utc_now, select_rules
from ..domain.generated import compile_level, GeneratedRules
from ..domain.generation_observability import STAGES, safe_counts, safe_reason, source_snapshot, text_counts

PASSWORD_HASHER=PasswordHasher(time_cost=2,memory_cost=19456,parallelism=1,hash_len=32,salt_len=16)
HASH_SLOTS=threading.BoundedSemaphore(2)
ACTIVE_PHASES=('pending','generating','validating')

def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def public_user(row): return {'user_id':row['user_id'],'username':row['username']}

class V5Database:
    def __init__(self,path):
        self.path=str(path)
        if self.path==':memory:': raise ValueError('V5 requires isolated file-backed database')
        target=Path(self.path)
        target.parent.mkdir(parents=True,exist_ok=True)
        # Crucially, do this before Store's migrations or WAL writes.
        if target.exists() and target.stat().st_size:
            with closing(sqlite3.connect(self.path)) as c:
                tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if 'v5_metadata' not in tables or c.execute("SELECT value FROM v5_metadata WHERE key='database_version'").fetchone()!=('5',):
                    raise ValueError('Refusing existing non-v5 database')
        with closing(sqlite3.connect(self.path)) as c:
            c.execute('CREATE TABLE IF NOT EXISTS v5_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
            c.execute("INSERT OR IGNORE INTO v5_metadata VALUES('database_version','5')")
            c.commit()
        self.base=Store(self.path,rules=select_rules('3.4'))
        self._compiled_cache={}
        with self.base.transaction() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS users(user_id TEXT PRIMARY KEY,username TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,created_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS auth_sessions(auth_id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(user_id),token_hash TEXT NOT NULL UNIQUE,csrf_hash TEXT NOT NULL,auth_context TEXT NOT NULL UNIQUE,created_at REAL NOT NULL,last_seen REAL NOT NULL,revoked INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS anonymous_csrf(nonce_hash TEXT PRIMARY KEY,csrf_hash TEXT NOT NULL,created_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS auth_limits(kind TEXT NOT NULL,identity TEXT NOT NULL,at REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS auth_limits_lookup ON auth_limits(kind,identity,at);
            CREATE TABLE IF NOT EXISTS session_owners(session_id TEXT PRIMARY KEY REFERENCES sessions(session_id),user_id TEXT NOT NULL REFERENCES users(user_id),mode TEXT NOT NULL,level_id TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(user_id,mode,level_id));
            CREATE TABLE IF NOT EXISTS session_requests(user_id TEXT NOT NULL,request_id TEXT NOT NULL,request_hash TEXT NOT NULL,session_id TEXT NOT NULL,PRIMARY KEY(user_id,request_id));
            CREATE TABLE IF NOT EXISTS level_generations(job_id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(user_id),request_id TEXT NOT NULL,request_hash TEXT NOT NULL,theme TEXT NOT NULL,room_count INTEGER NOT NULL,difficulty TEXT NOT NULL,status TEXT NOT NULL,created_at REAL NOT NULL,updated_at REAL NOT NULL,level_id TEXT,error_code TEXT,UNIQUE(user_id,request_id));
            CREATE TABLE IF NOT EXISTS generated_levels(level_id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(user_id),job_id TEXT NOT NULL UNIQUE,definition_json TEXT NOT NULL,definition_hash TEXT NOT NULL,definition_version TEXT NOT NULL,metadata_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS generation_job_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT NOT NULL,stage TEXT NOT NULL,recorded_at TEXT NOT NULL,reason TEXT NOT NULL,counts_json TEXT NOT NULL,source_json TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS generation_job_events_job ON generation_job_events(job_id,event_id);
            ''')
            interrupted=c.execute("SELECT job_id,status FROM level_generations WHERE status IN ('pending','generating','validating') AND EXISTS(SELECT 1 FROM generation_job_events e WHERE e.job_id=level_generations.job_id)").fetchall()
            c.execute("UPDATE level_generations SET status=CASE status WHEN 'generating' THEN 'unknown' ELSE 'failed' END,error_code='PROCESS_RESTARTED',updated_at=? WHERE status IN ('pending','generating','validating')",(time.time(),))
            for row in interrupted:
                self.record_job_event(c,row['job_id'],'unknown' if row['status']=='generating' else 'failed',reason='process_restart')
    def transaction(self): return self.base.transaction()
    def anonymous(self,existing_nonce=None):
        now=time.time()
        with self.transaction() as c:
            c.execute('DELETE FROM anonymous_csrf WHERE created_at<?',(now-600,))
            if existing_nonce:
                row=c.execute('SELECT csrf_hash,created_at FROM anonymous_csrf WHERE nonce_hash=?',(digest(existing_nonce),)).fetchone()
                csrf=hmac.new(existing_nonce.encode(),b'campus-v5-anonymous-csrf',hashlib.sha256).hexdigest()
                if row and now-row['created_at']<600 and hmac.compare_digest(row['csrf_hash'],digest(csrf)):
                    return existing_nonce,csrf
                # A legacy random-CSRF row cannot be reconstructed; rotate once.
                c.execute('DELETE FROM anonymous_csrf WHERE nonce_hash=?',(digest(existing_nonce),))
            nonce=secrets.token_urlsafe(32)
            csrf=hmac.new(nonce.encode(),b'campus-v5-anonymous-csrf',hashlib.sha256).hexdigest()
            c.execute('INSERT INTO anonymous_csrf VALUES(?,?,?)',(digest(nonce),digest(csrf),now))
        return nonce,csrf
    def check_anonymous(self,nonce,csrf):
        with self.transaction() as c:
            row=c.execute('SELECT * FROM anonymous_csrf WHERE nonce_hash=?',(digest(nonce or ''),)).fetchone()
            return bool(row and time.time()-row['created_at']<600 and hmac.compare_digest(row['csrf_hash'],digest(csrf or '')))
    def authenticate(self,token,*,touch=True):
        now=time.time()
        with self.transaction() as c:
            row=c.execute('SELECT a.*,u.username FROM auth_sessions a JOIN users u ON u.user_id=a.user_id WHERE token_hash=?',(digest(token or ''),)).fetchone()
            if not row or row['revoked'] or now-row['created_at']>=28800 or now-row['last_seen']>=1800: return None
            if touch: c.execute('UPDATE auth_sessions SET last_seen=? WHERE auth_id=?',(now,row['auth_id']))
            return dict(row)
    def rotate(self,user_id,old_token=None):
        token=secrets.token_urlsafe(32); csrf=hmac.new(token.encode(),b'campus-v5-csrf',hashlib.sha256).hexdigest(); context=new_id()
        with self.transaction() as c:
            if old_token: c.execute('UPDATE auth_sessions SET revoked=1 WHERE token_hash=?',(digest(old_token),))
            c.execute('INSERT INTO auth_sessions VALUES(?,?,?,?,?,?,?,0)',(new_id(),user_id,digest(token),digest(csrf),context,time.time(),time.time()))
            user=c.execute('SELECT * FROM users WHERE user_id=?',(user_id,)).fetchone()
        return token,csrf,{'user':public_user(user),'auth_context':context,'csrf_token':csrf}
    def csrf_for(self,principal,token):
        # Stable for the lifetime of this rotated authentication context.
        if not hmac.compare_digest(principal['token_hash'],digest(token or '')): raise ValueError('AUTH_CONTEXT')
        return hmac.new(token.encode(),b'campus-v5-csrf',hashlib.sha256).hexdigest()
    def rate_allowed(self,kind,identity,limit,window=600,cooldown=0):
        now=time.time()
        with self.transaction() as c:
            rows=c.execute('SELECT at FROM auth_limits WHERE kind=? AND identity=? AND at>? ORDER BY at DESC',(kind,identity,now-window)).fetchall()
            if len(rows)>=limit and (not cooldown or now-rows[0]['at']<cooldown): return False
        return True
    def rate_record(self,kind,identity):
        with self.transaction() as c:
            c.execute('DELETE FROM auth_limits WHERE at<?',(time.time()-86400,))
            c.execute('INSERT INTO auth_limits VALUES(?,?,?)',(kind,identity,time.time()))
    def credentials(self,username,password,source,register):
        identity=digest(username); source=digest(source)
        if not self.rate_allowed('source',source,30,cooldown=60) or not self.rate_allowed('account',identity,5,cooldown=60): return 429,None
        if register and not self.rate_allowed('register',source,10): return 429,None
        if register: self.rate_record('register',source)
        with self.transaction() as c: user=c.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
        if not HASH_SLOTS.acquire(blocking=False): return 429,None
        try:
            if register:
                if user: return 409,None
                hashed=PASSWORD_HASHER.hash(password)
                with self.transaction() as c:
                    uid=new_id()
                    try: c.execute('INSERT INTO users VALUES(?,?,?,?)',(uid,username,hashed,time.time()))
                    except sqlite3.IntegrityError: return 409,None
                return 201,uid
            try:
                # Equal-cost absent-user verification, without storing the password.
                if user: PASSWORD_HASHER.verify(user['password_hash'],password)
                else: PASSWORD_HASHER.hash(password); raise VerificationError('invalid')
            except VerificationError:
                self.rate_record('account',identity); self.rate_record('source',source); return 401,None
            with self.transaction() as c: c.execute("DELETE FROM auth_limits WHERE kind='account' AND identity=?",(identity,))
            return 200,user['user_id']
        finally: HASH_SLOTS.release()
    def owned(self,principal,session_id):
        with self.transaction() as c:
            row=c.execute('SELECT * FROM session_owners WHERE session_id=? AND user_id=?',(session_id,principal['user_id'])).fetchone()
            if not row: return None
            row=dict(row)
            if row['mode']=='classic': rules=select_rules('3.4')
            else:
                level=c.execute('SELECT * FROM generated_levels WHERE level_id=? AND user_id=?',(row['level_id'],principal['user_id'])).fetchone()
                if not level: raise ValueError('DEFINITION_MISSING')
                compiled=self.load_compiled(level)
                rules=GeneratedRules(compiled,owner_id=principal['user_id'],level_id=row['level_id'])
            return BoundStore(self,principal,rules,row)
    def load_compiled(self,level):
        private=json.loads(level['definition_json']); metadata=json.loads(level['metadata_json'])
        if private.get('version')!='1.0.0' or private.get('definition_version')!='1.0.0' or private.get('rules_version')!='1.0.0' or private.get('policy_version') not in {'1.0.0','0.9.0'} or level['definition_version']!='1.0.0': raise ValueError('DEFINITION_VERSION')
        actual=digest(canonical({key:private[key] for key in ('definition_version','rules_version','policy_version','draft')}))
        if actual!=level['definition_hash'] or private.get('definition_hash')!=actual or metadata.get('definition_hash')!=actual: raise ValueError('DEFINITION_HASH')
        key=(actual,metadata['room_count'],metadata['difficulty'],private['policy_version'])
        compiled=self._compiled_cache.get(key)
        if compiled is None:
            compiled=compile_level(private['draft'],metadata['room_count'],metadata['difficulty'],policy_version=private['policy_version'])
            self._compiled_cache[key]=compiled
        return compiled
    def sessions(self,user_id):
        with self.transaction() as c:
            rows=c.execute('SELECT o.*,s.state_json FROM session_owners o JOIN sessions s ON s.session_id=o.session_id WHERE o.user_id=? ORDER BY o.created_at DESC',(user_id,)).fetchall()
            result=[]
            for row in rows:
                state=json.loads(row['state_json'])
                result.append({key:row[key] for key in ('session_id','mode','level_id','created_at')} | {'status':state['status'],'room_id':state['room_id'],'revision':state['revision'],'clues_found':len(state['discovered_clue_ids']),'puzzles_solved':len(state.get('solved_puzzle_ids',[]))})
            return result
    def create_session(self,principal,request):
        normalized=request.model_dump(); hashed=digest(canonical(normalized)); uid=principal['user_id']
        with self.transaction() as c:
            prior=c.execute('SELECT * FROM session_requests WHERE user_id=? AND request_id=?',(uid,request.request_id)).fetchone()
            if prior:
                if prior['request_hash']!=hashed: return 409,{'code':'REQUEST_ID_CONFLICT','message':'同一请求标识不能更改内容。'}
                return 200,{'session_id':prior['session_id'],'existing':True}
            level_id=request.level_id or ''
            if request.mode=='classic':
                if level_id: return 422,{'code':'BAD_ARGUMENT','message':'经典关卡无需指定关卡。'}
                rules=select_rules('3.4')
            else:
                level=c.execute('SELECT * FROM generated_levels WHERE level_id=? AND user_id=?',(level_id,uid)).fetchone()
                if not level: return 404,{'code':'NOT_FOUND','message':'未找到关卡。'}
                compiled=self.load_compiled(level)
                rules=GeneratedRules(compiled,owner_id=uid,level_id=level_id)
            existing=c.execute('SELECT session_id FROM session_owners WHERE user_id=? AND mode=? AND level_id=?',(uid,request.mode,level_id)).fetchone()
            if existing: sid=existing['session_id']; exists=True
            else:
                sid=new_id(); exists=False; state=rules.initial_state()
                c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(sid,digest(secrets.token_urlsafe(32)),canonical(state.model_dump()),utc_now()))
                c.execute('INSERT INTO session_owners VALUES(?,?,?,?,?)',(sid,uid,request.mode,level_id,utc_now()))
            c.execute('INSERT INTO session_requests VALUES(?,?,?,?)',(uid,request.request_id,hashed,sid))
            return 200 if exists else 201,{'session_id':sid,'existing':exists}
    def job_public(self,row):
        return {key:row[key] for key in ('job_id','status','room_count','difficulty','created_at','updated_at','level_id','error_code')}
    def jobs(self,user_id,job_id=None):
        with self.transaction() as c:
            if job_id:
                row=c.execute('SELECT * FROM level_generations WHERE user_id=? AND job_id=?',(user_id,job_id)).fetchone()
                return self.job_public(row) if row else None
            return [self.job_public(r) for r in c.execute('SELECT * FROM level_generations WHERE user_id=? ORDER BY created_at DESC',(user_id,))]
    def reserve_job(self,uid,request):
        raw=request.model_dump(); hashed=digest(canonical(raw)); now=time.time()
        with self.transaction() as c:
            old=c.execute('SELECT * FROM level_generations WHERE user_id=? AND request_id=?',(uid,request.request_id)).fetchone()
            if old: return (200,self.job_public(old),False) if old['request_hash']==hashed else (409,None,False)
            pending=c.execute("SELECT user_id FROM level_generations WHERE status IN ('pending','generating','validating')").fetchall()
            if len(pending)>=2 or any(r['user_id']==uid for r in pending): return 429,None,False
            job_id=new_id()
            c.execute('INSERT INTO level_generations VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(job_id,uid,request.request_id,hashed,request.theme,request.room_count,request.difficulty,'pending',now,now,None,None))
            self.record_job_event(c,job_id,'pending',reason='requested',counts={
                **text_counts('theme',request.theme),'requested_rooms':request.room_count,
                'difficulty_rank':{'easy':1,'normal':2,'hard':3}[request.difficulty]})
            row=c.execute('SELECT * FROM level_generations WHERE job_id=?',(job_id,)).fetchone()
            return 202,self.job_public(row),True
    def record_job_event(self,c,job_id,stage,*,reason='unspecified',counts=None):
        if stage not in STAGES: return
        c.execute('INSERT INTO generation_job_events(job_id,stage,recorded_at,reason,counts_json,source_json) VALUES(?,?,?,?,?,?)',
                  (job_id,stage,utc_now(),safe_reason(reason),canonical(safe_counts(counts)),canonical(source_snapshot())))
    def job_phase(self,job_id,phase,error=None,*,reason='unspecified',counts=None):
        with self.transaction() as c:
            changed=c.execute('UPDATE level_generations SET status=?,error_code=?,updated_at=? WHERE job_id=?',(phase,error,time.time(),job_id))
            if changed.rowcount: self.record_job_event(c,job_id,phase,reason=reason,counts=counts)
    def commit_level(self,job_id,compiled):
        with self.transaction() as c:
            job=c.execute('SELECT * FROM level_generations WHERE job_id=?',(job_id,)).fetchone()
            if not job or job['status']!='validating': raise ValueError('JOB_STATE')
            lid=new_id(); d=compiled.draft
            metadata={'level_id':lid,'title':d.title,'story':d.story,'room_count':job['room_count'],'difficulty':job['difficulty'],'definition_hash':compiled.definition_hash,'definition_version':'1.0.0','rules_version':'1.0.0','policy_version':compiled.policy_version,'created_at':utc_now()}
            c.execute('INSERT INTO generated_levels VALUES(?,?,?,?,?,?,?)',(lid,job['user_id'],job_id,canonical(compiled.private_dump()),compiled.definition_hash,'1.0.0',canonical(metadata)))
            c.execute("UPDATE level_generations SET status='ready',level_id=?,updated_at=? WHERE job_id=?",(lid,time.time(),job_id))
            self.record_job_event(c,job_id,'ready',reason='completed',counts={
                'rooms':len(d.rooms),'objects':sum(len(room.objects) for room in d.rooms),
                'clues':len(d.clues),'puzzles':len(d.puzzles),'witness_steps':len(compiled.witness)})
    def levels(self,uid,lid=None):
        # Generation requests are Key/cookie-redacted by the sole HTTP creation
        # route before reservation. Project only the owning job's theme; never
        # open or rewrite the private definition or stored legacy metadata.
        query=('SELECT l.metadata_json,j.theme FROM generated_levels l '
               'LEFT JOIN level_generations j ON j.job_id=l.job_id '
               'AND j.user_id=l.user_id AND j.level_id=l.level_id '
               'WHERE l.user_id=?')
        def public(row):
            result=json.loads(row['metadata_json'])
            if row['theme'] is not None: result['theme']=row['theme']
            return result
        with self.transaction() as c:
            if lid:
                row=c.execute(query+' AND l.level_id=?',(uid,lid)).fetchone()
                return public(row) if row else None
            return [public(row) for row in c.execute(query+' ORDER BY l.rowid DESC',(uid,))]

class BoundStore(Store):
    """Per-request facade. No mutable global rules/principal switching."""
    def __init__(self,database,principal,rules,metadata):
        self.path=database.path; self.rules=rules; self.principal=dict(principal); self.metadata=metadata
        self.runtime_owner=database.base.runtime_owner
    def authenticate(self,c,session_id,token=None):
        row=c.execute('SELECT s.state_json FROM sessions s JOIN session_owners o ON o.session_id=s.session_id JOIN auth_sessions a ON a.user_id=o.user_id WHERE s.session_id=? AND o.user_id=? AND a.auth_id=? AND a.revoked=0 AND a.last_seen>? AND a.created_at>?',(session_id,self.principal['user_id'],self.principal['auth_id'],time.time()-1800,time.time()-28800)).fetchone()
        return self.parse_state(row['state_json']) if row else None
    def projection(self,c,session_id,state):
        result=super().projection(c,session_id,state)
        result.update(mode=self.metadata['mode'],level_id=self.metadata['level_id'] or None)
        return result

    def begin_v5_ai(self,session_id,request,provider):
        from ..domain.models import validate_generation
        validate_generation(request.generation)
        eid=new_id(); normalized={'operation':'v5_ai_turn',**request.model_dump(),'provider':provider}; hashed=digest(canonical(normalized))
        with self.transaction() as c:
            s=self.authenticate(c,session_id)
            if s is None: return 401,None
            if request.generation!=s.generation: return 409,{'code':'STALE_GENERATION','message':'进度已恢复或重置，请同步。'}
            prior=c.execute('SELECT * FROM action_receipts WHERE session_id=? AND request_id=?',(session_id,request.request_id)).fetchone()
            if prior:
                if prior['request_hash']!=hashed: return 409,{'code':'REQUEST_ID_CONFLICT','message':'同一请求标识不能更改内容。'}
                if prior['phase']!='completed': return 503,{'code':'MODEL_UNAVAILABLE','message':'本轮正在处理或结果未知，不会重复调用。'}
                body=json.loads(prior['response_json'])
                if body['ok']: body['data']['visible_state']=self.projection(c,session_id,s)
                return prior['http_status'],body
            if request.revision!=s.revision: return 409,{'code':'STALE_STATE','message':'进度已改变，请同步。'}
            c.execute("INSERT INTO action_receipts(session_id,request_id,request_hash,generation,response_json,http_status,phase) VALUES(?,?,?,?,?,0,'reserved')",(session_id,request.request_id,hashed,s.generation,'{}'))
            history=[]
            rows=c.execute("SELECT request_json,result_json FROM events WHERE session_id=? AND generation=? AND operation='v5_ai_turn' AND outcome='committed' AND json_extract(result_json,'$.data.usage.provider')='deepseek' AND json_extract(result_json,'$.data.usage.model_calls')=1 ORDER BY sequence DESC LIMIT 3",(session_id,s.generation)).fetchall()
            for row in reversed(rows):
                req=json.loads(row['request_json'] or '{}'); data=json.loads(row['result_json']).get('data',{})
                history.append({'kind':'dialogue','question':req.get('message','')[-300:],'answer':data.get('answer','')[-360:],'clue_refs':data.get('clue_refs',[])})
            rows=c.execute("SELECT result_json FROM events WHERE session_id=? AND generation=? AND operation='action' AND outcome='committed' ORDER BY sequence DESC LIMIT 3",(session_id,s.generation)).fetchall()
            for row in reversed(rows):
                receipt=json.loads(row['result_json']).get('data',{}).get('receipt',{})
                if receipt.get('tool') in self.rules.tool_models: history.append({'kind':'action','tool':receipt['tool']})
            return None,{'event_id':eid,'turn_id':new_id(),'state':self.projection(c,session_id,s),'history':history,'revision':s.revision,'generation':s.generation,'provider':provider}

    def finish_v5_ai(self,session_id,request,started,result,*,secret_values=()):
        import re
        with self.transaction() as c:
            s=self.authenticate(c,session_id)
            if s is None:
                c.execute("UPDATE action_receipts SET phase='unknown' WHERE session_id=? AND request_id=?",(session_id,request.request_id))
                return 401,{'ok':False,'event_id':new_id(),'error':{'code':'AUTH_REQUIRED','message':'请重新登录。'}}
            if s.generation!=started['generation'] or s.revision!=started['revision']:
                code='STALE_STATE'; message='进度已变化，请重新询问。'
            else:
                answer=result.get('answer') if isinstance(result,dict) else None
                refs=result.get('clue_refs') if isinstance(result,dict) else None
                code=None
                if started['provider']=='mock':
                    from ..ai.v5 import local_hint
                    current=local_hint(self.projection(c,session_id,s),request.hint_level)
                    result={**current,'usage':{'provider':'mock','model':None,'input_tokens':None,'output_tokens':None,'model_calls':0,'read_tool_calls':0}}
                    answer=result['answer']; refs=result['clue_refs']
                if not isinstance(answer,str) or not 1<=len(answer)<=360 or not isinstance(refs,list) or len(refs)!=len(set(refs)) or any(not isinstance(r,str) or r not in s.discovered_clue_ids for r in refs): code='MODEL_INVALID_OUTPUT'
                if isinstance(answer,str) and (any(secret and secret in answer for secret in secret_values) or re.search(r'https?://|<script|sk-[A-Za-z0-9_-]{12,}|(?:Bearer\s+)[A-Za-z0-9_-]+',answer,re.I)): code='MODEL_INVALID_OUTPUT'
                if not code and started['provider']=='deepseek':
                    try:
                        from ..ai.v5 import validate_reply
                        validate_reply(self.projection(c,session_id,s),{'answer':answer,'clue_refs':refs},request.message,started['history'])
                    except (ValueError,TypeError,KeyError): code='MODEL_INVALID_OUTPUT'
                if not code and hasattr(self.rules,'compiled'):
                    for value in self.rules.compiled.answers.values():
                        if isinstance(value,str) and len(value)>=3 and value in answer: code='MODEL_INVALID_OUTPUT'
                        if isinstance(value,list) and any(sep.join(value) in answer for sep in ('','、',',',' → ')): code='MODEL_INVALID_OUTPUT'
                message='伙伴回复未通过安全检查，进度已保留。'
            if code:
                status=409 if code=='STALE_STATE' else 502
                body={'ok':False,'event_id':started['event_id'],'error':{'code':code,'message':message},'visible_state':self.projection(c,session_id,s)}
                c.execute("UPDATE action_receipts SET phase='completed',response_json=?,http_status=? WHERE session_id=? AND request_id=?",(canonical(body),status,session_id,request.request_id))
                return status,body
            count=result.get('count_hint',True)
            if count and s.status=='playing':
                if hasattr(s,'statistics'): s.statistics.hint_count+=1; s.statistics.current_hint_level=request.hint_level
                else: s.hint_count+=1
                s.revision+=1; self.rules.validate_invariants(s)
                c.execute('UPDATE sessions SET state_json=? WHERE session_id=?',(canonical(s.model_dump()),session_id))
                self.invalidate_pending(c,session_id)
            usage=result.get('usage') or {'provider':'mock','model':None,'input_tokens':None,'output_tokens':None,'model_calls':0,'read_tool_calls':0}
            usage={key:usage.get(key) for key in ('provider','model','input_tokens','output_tokens','model_calls','read_tool_calls')}
            # Never trust provider metadata as a free-form output/logging channel.
            usage['provider']=started['provider']
            usage['model']='deepseek-flash' if started['provider']=='deepseek' and usage.get('model_calls')==1 else None
            for name in ('input_tokens','output_tokens'):
                if type(usage[name]) is not int or usage[name]<0: usage[name]=None
            usage['model_calls']=1 if usage.get('model_calls')==1 else 0
            usage['read_tool_calls']=0
            data={'turn_id':started['turn_id'],'answer':answer,'clue_refs':refs,'proposal':None,'status':'no_suggestion','stop_reason':None,'usage':usage,'visible_state':self.projection(c,session_id,s)}
            body={'ok':True,'event_id':started['event_id'],'data':data}
            self.event(c,started['event_id'],session_id,'v5_ai_turn','committed',body,s,{'message':request.message},started['revision'])
            c.execute("UPDATE action_receipts SET phase='completed',response_json=?,http_status=200 WHERE session_id=? AND request_id=?",(canonical(body),session_id,request.request_id))
            return 200,body
    def fail_v5_ai(self,session_id,request,started,code='MODEL_UNAVAILABLE',unknown=False):
        with self.transaction() as c:
            s=self.authenticate(c,session_id)
            body={'ok':False,'event_id':started['event_id'],'error':{'code':code,'message':'本轮未完成，游戏进度已保留；同一请求不会再次调用。'}}
            if s is not None: body['visible_state']=self.projection(c,session_id,s)
            status={'MODEL_TIMEOUT':504,'MODEL_INVALID_OUTPUT':502,'AI_LIMIT_REACHED':429}.get(code,503)
            c.execute('UPDATE action_receipts SET phase=?,response_json=?,http_status=? WHERE session_id=? AND request_id=?',('unknown' if unknown else 'completed',canonical(body),status,session_id,request.request_id))
            return status,body
