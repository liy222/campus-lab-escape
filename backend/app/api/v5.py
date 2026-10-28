"""Version-two authenticated local API; no anonymous gameplay routes."""
from __future__ import annotations
import asyncio
import hmac
import inspect
import json
import os
from pathlib import Path
from typing import Annotated, Literal
from fastapi import APIRouter, FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import Field, ValidationError, field_validator
from ..domain.models import StrictModel, Identifier
from ..domain.graybox_models import HintRequest
from ..domain.generated import Draft, compile_level
from ..domain.generation_observability import draft_counts, text_counts
from ..storage.sqlite import new_id
from ..storage.v5 import V5Database, digest

COOKIE='campus_v5_session'
ANON_COOKIE='campus_v5_csrf'
PREFIX='/api/v2'

class Credentials(StrictModel):
    username: Annotated[str,Field(min_length=3,max_length=24,pattern=r'^[A-Za-z0-9_]+$')]
    password: Annotated[str,Field(min_length=12,max_length=128)]
    @field_validator('username')
    @classmethod
    def lower(cls,value): return value.lower()
class SessionRequest(StrictModel):
    request_id: Identifier
    mode: Literal['classic','generated']
    level_id: Identifier | None = None
class GenerationRequest(StrictModel):
    request_id: Identifier
    theme: Annotated[str,Field(min_length=1,max_length=2000)]
    room_count: Annotated[int,Field(ge=1,le=3)]
    difficulty: Literal['easy','normal','hard']
class LogoutRequest(StrictModel):
    pass

class APIError(Exception):
    def __init__(self,status,code,message): self.status,self.code,self.message=status,code,message

def success(data,status=200): return JSONResponse({'ok':True,'event_id':new_id(),'data':data},status_code=status)
def failure(status,code,message): return JSONResponse({'ok':False,'event_id':new_id(),'error':{'code':code,'message':message}},status_code=status)
def result_response(result):
    status,body=result
    # Authorization has already occurred before touching private receipts.
    if isinstance(body,dict) and 'ok' not in body:
        return failure(status,body.get('code','BAD_ARGUMENT'),body.get('message','请求未完成。'))
    return JSONResponse(body,status_code=status)

def set_cookie(response,name,value,*,max_age):
    response.set_cookie(name,value,max_age=max_age,httponly=True,samesite='strict',path=PREFIX,secure=False)

def principal(request,mutate=False):
    db=request.app.state.v5_database
    p=db.authenticate(request.cookies.get(COOKIE))
    if not p: raise APIError(401,'AUTH_REQUIRED','请先登录。')
    if mutate:
        csrf=request.headers.get('X-CSRF-Token',''); context=request.headers.get('X-Auth-Context','')
        if len(request.headers.getlist('X-CSRF-Token'))!=1 or len(request.headers.getlist('X-Auth-Context'))!=1 or not hmac.compare_digest(p['csrf_hash'],digest(csrf)) or not hmac.compare_digest(p['auth_context'],context):
            raise APIError(403,'CSRF_FAILED','页面身份已改变，请重新登录或刷新。')
    return p

def bound(request,sid,mutate=False):
    p=principal(request,mutate)
    try: store=request.app.state.v5_database.owned(p,sid)
    except (ValueError,ValidationError,KeyError,TypeError): raise APIError(409,'DEFINITION_MISMATCH','关卡定义校验失败，当前进度已保留。') from None
    if store is None: raise APIError(404,'NOT_FOUND','未找到该资源。')
    return store

async def raw_body(request,model=None):
    def pairs(entries):
        value={}
        for k,v in entries:
            if k in value: raise ValueError('duplicate')
            value[k]=v
        return value
    try:
        raw=json.loads(await request.body(),object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))
        if not isinstance(raw,dict): raise ValueError('object')
        def check(v,n=0):
            if n>32: raise ValueError('depth')
            if isinstance(v,dict):
                for item in v.values(): check(item,n+1)
            if isinstance(v,list):
                for item in v: check(item,n+1)
        check(raw)
        return model.model_validate(raw) if model else raw
    except (ValueError,ValidationError,TypeError,RecursionError): raise APIError(422,'BAD_ARGUMENT','请求字段不符合契约。') from None

async def invoke(service,method,**kwargs):
    call=getattr(service,method)
    if inspect.iscoroutinefunction(call): return await call(**kwargs)
    value=await asyncio.to_thread(call,**kwargs)
    return await value if inspect.isawaitable(value) else value

async def generate(request_app,uid,job_id,request,key):
    db=request_app.state.v5_database
    try:
        db.job_phase(job_id,'generating',reason='started')
        service=request_app.state.generation_service
        if service is None:
            db.job_phase(job_id,'failed','MODEL_UNAVAILABLE',reason='provider_unavailable'); return
        raw=await asyncio.wait_for(invoke(service,'generate',theme=request.theme,room_count=request.room_count,difficulty=request.difficulty,api_key=key,draft_schema=Draft.model_json_schema()),timeout=90)
        # A provider cannot cause a credential to become immutable level content.
        rendered=json.dumps(raw,ensure_ascii=False) if not isinstance(raw,str) else raw
        if key and key in rendered: db.job_phase(job_id,'rejected','MODEL_INVALID_OUTPUT',reason='credential'); return
        db.job_phase(job_id,'validating',reason='generated',counts={**text_counts('draft_response',rendered),**draft_counts(raw)})
        try: compiled=await asyncio.to_thread(compile_level,raw,request.room_count,request.difficulty)
        except (ValueError,ValidationError,KeyError,TypeError) as error:
            proof=str(error) in {'PROOF_UNKNOWN','UNSOLVABLE','CIRCUIT_UNPROVEN','WITNESS_REPLAY'}
            db.job_phase(job_id,'rejected','PROOF_UNKNOWN' if str(error)=='PROOF_UNKNOWN' else 'ADMISSION_REJECTED',reason='proof' if proof else 'admission'); return
        db.commit_level(job_id,compiled)
    except asyncio.CancelledError:
        db.job_phase(job_id,'unknown','MODEL_OUTCOME_UNKNOWN',reason='cancelled'); raise
    except (TimeoutError,asyncio.TimeoutError): db.job_phase(job_id,'unknown','MODEL_OUTCOME_UNKNOWN',reason='timeout')
    except Exception as error:
        code=getattr(error,'code','MODEL_UNAVAILABLE')
        if code not in {'MODEL_TIMEOUT','MODEL_INVALID_OUTPUT','MODEL_UNAVAILABLE','AI_LIMIT_REACHED','MODEL_OUTCOME_UNKNOWN'}: code='MODEL_UNAVAILABLE'
        db.job_phase(job_id,'unknown' if code=='MODEL_OUTCOME_UNKNOWN' else ('rejected' if code=='MODEL_INVALID_OUTPUT' else 'failed'),code,
                     reason=getattr(error,'generation_diagnostic',None) or ('provider_unknown' if code=='MODEL_OUTCOME_UNKNOWN' else 'provider' if getattr(error,'code',None) else 'internal'),
                     counts=getattr(error,'generation_counts',None))
    finally:
        key=None

router=APIRouter(prefix=PREFIX)
@router.get('/auth/csrf')
def csrf(request:Request):
    db=request.app.state.v5_database
    p=db.authenticate(request.cookies.get(COOKIE))
    if p:
        token=db.csrf_for(p,request.cookies.get(COOKIE))
        return success({'csrf_token':token,'auth_context':p['auth_context'],'user':{'user_id':p['user_id'],'username':p['username']}})
    existing_nonce=request.cookies.get(ANON_COOKIE)
    nonce,token=db.anonymous(existing_nonce); response=success({'csrf_token':token,'auth_context':None,'user':None})
    if nonce!=existing_nonce: set_cookie(response,ANON_COOKIE,nonce,max_age=600)
    return response

async def login_or_register(request,register):
    db=request.app.state.v5_database; old=request.cookies.get(COOKIE)
    p=db.authenticate(old)
    if p: principal(request,True)
    elif len(request.headers.getlist('X-CSRF-Token'))!=1 or not db.check_anonymous(request.cookies.get(ANON_COOKIE),request.headers.get('X-CSRF-Token')):
        raise APIError(403,'CSRF_FAILED','请刷新登录页面后重试。')
    credentials=await raw_body(request,Credentials)
    status,uid=await asyncio.to_thread(db.credentials,credentials.username,credentials.password,request.client.host if request.client else 'local',register)
    if uid is None:
        codes={401:('INVALID_CREDENTIALS','用户名或密码不正确。'),409:('USERNAME_UNAVAILABLE','用户名不可用。'),429:('AUTH_LIMIT_REACHED','尝试较频繁，请稍后重试。')}
        code,message=codes.get(status,('AUTH_FAILED','认证未完成。')); return failure(status,code,message)
    token,csrf,data=db.rotate(uid,old); response=success(data,status)
    set_cookie(response,COOKIE,token,max_age=28800)
    response.delete_cookie(ANON_COOKIE,path=PREFIX)
    return response
@router.post('/auth/register')
async def register(request:Request): return await login_or_register(request,True)
@router.post('/auth/login')
async def login(request:Request): return await login_or_register(request,False)
@router.get('/auth/me')
def me(request:Request):
    p=principal(request); csrf=request.app.state.v5_database.csrf_for(p,request.cookies.get(COOKIE))
    return success({'user':{'user_id':p['user_id'],'username':p['username']},'auth_context':p['auth_context'],'csrf_token':csrf})
@router.post('/auth/logout')
async def logout(request:Request):
    p=principal(request,True); await raw_body(request,LogoutRequest)
    with request.app.state.v5_database.transaction() as c: c.execute('UPDATE auth_sessions SET revoked=1 WHERE auth_id=?',(p['auth_id'],))
    nonce,_=request.app.state.v5_database.anonymous()
    response=success({'logged_out':True}); response.delete_cookie(COOKIE,path=PREFIX)
    set_cookie(response,ANON_COOKIE,nonce,max_age=600)
    return response
@router.get('/sessions')
def sessions(request:Request): return success({'sessions':request.app.state.v5_database.sessions(principal(request)['user_id'])})
@router.post('/sessions')
async def create_session(request:Request):
    p=principal(request,True); raw=await raw_body(request,SessionRequest)
    try: status,data=request.app.state.v5_database.create_session(p,raw)
    except (ValueError,ValidationError,KeyError,TypeError): raise APIError(409,'DEFINITION_MISMATCH','关卡定义校验失败，当前进度已保留。') from None
    if status not in {200,201}: return result_response((status,data))
    store=request.app.state.v5_database.owned(p,data['session_id']); _,body=store.read(data['session_id'],None)
    data.update(mode=store.metadata['mode'],level_id=store.metadata['level_id'] or None,visible_state=body['data']['visible_state'])
    return success(data,status)
@router.get('/sessions/{sid}/state')
def state(sid:str,request:Request): return result_response(bound(request,sid).read(sid,None))
@router.post('/sessions/{sid}/actions')
async def action(sid:str,request:Request):
    store=bound(request,sid,True); raw=await raw_body(request)
    return result_response(store.action(sid,None,raw))
@router.post('/sessions/{sid}/reset')
async def reset(sid:str,request:Request):
    store=bound(request,sid,True); raw=await raw_body(request)
    return result_response(store.control(sid,None,'reset',raw))
@router.get('/sessions/{sid}/saves')
def saves(sid:str,request:Request): return result_response(bound(request,sid).list_saves(sid,None))
@router.post('/sessions/{sid}/saves')
async def save(sid:str,request:Request):
    store=bound(request,sid,True); raw=await raw_body(request)
    return result_response(store.create_save(sid,None,raw))
@router.post('/sessions/{sid}/saves/{save_id}/restore')
async def restore(sid:str,save_id:str,request:Request):
    store=bound(request,sid,True); raw=await raw_body(request)
    return result_response(store.restore_save(sid,None,save_id,raw))
@router.post('/sessions/{sid}/saves/{save_id}/delete')
async def delete(sid:str,save_id:str,request:Request):
    store=bound(request,sid,True); raw=await raw_body(request)
    return result_response(store.delete_save(sid,None,save_id,raw))
@router.get('/level-generations')
def jobs(request:Request): return success({'jobs':request.app.state.v5_database.jobs(principal(request)['user_id'])})
@router.get('/level-generations/{job_id}')
def job(job_id:str,request:Request):
    item=request.app.state.v5_database.jobs(principal(request)['user_id'],job_id)
    if item is None: raise APIError(404,'NOT_FOUND','未找到该任务。')
    return success({'job':item})
@router.post('/level-generations')
async def new_job(request:Request,background_tasks:BackgroundTasks):
    p=principal(request,True); raw=await raw_body(request,GenerationRequest)
    keys=request.headers.getlist('X-AI-Api-Key')
    if len(keys)!=1 or not keys[0].strip() or len(keys[0])>256 or any(ord(c)<33 or ord(c)>126 for c in keys[0]): raise APIError(422,'AI_KEY_REQUIRED','生成关卡需要临时 API Key。')
    key=keys[0]; raw=raw.model_copy(update={'theme':raw.theme.replace(key,'[REDACTED]').replace(request.cookies.get(COOKIE) or '\0','[REDACTED]')})
    status,item,dispatch=request.app.state.v5_database.reserve_job(p['user_id'],raw)
    if item is None: return failure(status,'REQUEST_ID_CONFLICT' if status==409 else 'GENERATION_LIMIT_REACHED','同一请求标识不能更改内容。' if status==409 else '生成名额或频率已达上限，请稍后重试。')
    if dispatch: background_tasks.add_task(generate,request.app,p['user_id'],item['job_id'],raw,key)
    return success({'job':item},status)
@router.get('/levels')
def levels(request:Request): return success({'levels':request.app.state.v5_database.levels(principal(request)['user_id'])})
@router.get('/levels/{lid}')
def level(lid:str,request:Request):
    item=request.app.state.v5_database.levels(principal(request)['user_id'],lid)
    if item is None: raise APIError(404,'NOT_FOUND','未找到该关卡。')
    return success({'level':item})
@router.post('/sessions/{sid}/ai/turns')
async def ai_turn(sid:str,request:Request):
    store=bound(request,sid,True); raw=await raw_body(request,HintRequest)
    providers=request.headers.getlist('X-AI-Provider'); keys=request.headers.getlist('X-AI-Api-Key')
    provider=providers[0] if providers else 'mock'; key=keys[0] if keys else None
    if len(providers)>1 or len(keys)>1 or provider not in {'mock','deepseek'} or provider=='deepseek' and (not key or len(key)>256 or any(ord(c)<33 or ord(c)>126 for c in key)):
        raise APIError(422,'BAD_ARGUMENT','AI 设置不符合要求。')
    secrets_to_redact=[v for v in (key,request.cookies.get(COOKIE)) if v]
    message=raw.message
    for value in secrets_to_redact: message=message.replace(value,'[REDACTED]')
    raw=raw.model_copy(update={'message':message})
    try: status,started=store.begin_v5_ai(sid,raw,provider)
    except (ValueError,ValidationError): raise APIError(422,'BAD_ARGUMENT','AI 请求字段不符合契约。') from None
    if status is not None: return result_response((status,started or {'code':'AUTH_REQUIRED','message':'请重新登录。'}))
    try:
        service=request.app.state.companion_service
        if service is None: return result_response(store.fail_v5_ai(sid,raw,started))
        result=await asyncio.wait_for(invoke(service,'turn',public_state=started['state'],message=raw.message,history=started['history'],api_key=key,provider=provider,hint_level=raw.hint_level),timeout=25)
        if result.get('status')=='stopped' and result.get('stop_reason'): return result_response(store.fail_v5_ai(sid,raw,started,result.get('stop_reason') or 'MODEL_UNAVAILABLE'))
        return result_response(store.finish_v5_ai(sid,raw,started,result,secret_values=secrets_to_redact))
    except (TimeoutError,asyncio.TimeoutError):
        return result_response(store.fail_v5_ai(sid,raw,started,'MODEL_TIMEOUT',unknown=True))
    except asyncio.CancelledError:
        store.fail_v5_ai(sid,raw,started,unknown=True); raise
    except Exception as error:
        code=getattr(error,'code','MODEL_UNAVAILABLE')
        if code not in {'MODEL_TIMEOUT','MODEL_INVALID_OUTPUT','MODEL_UNAVAILABLE','AI_LIMIT_REACHED','MODEL_OUTCOME_UNKNOWN'}: code='MODEL_UNAVAILABLE'
        return result_response(store.fail_v5_ai(sid,raw,started,'MODEL_UNAVAILABLE' if code=='MODEL_OUTCOME_UNKNOWN' else code,unknown=code=='MODEL_OUTCOME_UNKNOWN'))


def install_security(app,*,dev=False):
    allowed={'http://127.0.0.1:8001'}|({'http://127.0.0.1:5174'} if dev else set())
    @app.middleware('http')
    async def security(request:Request,call_next):
        if request.url.path.startswith('/api/') and not request.url.path.startswith(PREFIX+'/'): response=failure(404,'NOT_FOUND','未找到该资源。')
        elif len(request.headers.getlist('host'))!=1 or request.headers.get('host','')!='127.0.0.1:8001': response=failure(400,'INVALID_HOST','仅支持指定本机地址。')
        elif any(name.lower()=='forwarded' or name.lower().startswith('x-forwarded-') for name in request.headers): response=failure(400,'FORWARDED_HEADERS_REJECTED','不支持转发访问。')
        elif request.headers.get('origin') is not None and (len(request.headers.getlist('origin'))!=1 or request.headers.get('origin') not in allowed): response=failure(403,'INVALID_ORIGIN','请求来源不合法。')
        elif request.method not in {'GET','HEAD','OPTIONS'} and request.headers.get('origin') not in allowed: response=failure(403,'INVALID_ORIGIN','请求来源不合法。')
        elif request.method not in {'GET','HEAD','OPTIONS'} and request.headers.get('content-type','').split(';')[0].strip().lower()!='application/json': response=failure(415,'UNSUPPORTED_MEDIA_TYPE','请求必须使用 JSON。')
        elif request.method=='OPTIONS': response=failure(403,'CORS_DISABLED','不支持跨站调用。')
        else:
            try:
                length=request.headers.get('content-length')
                if length and (not length.isdigit() or int(length)>16384): response=failure(413,'REQUEST_TOO_LARGE','请求过大。')
                else:
                    chunks=[]; total=0
                    async for chunk in request.stream():
                        total+=len(chunk)
                        if total>16384: break
                        chunks.append(chunk)
                    if total>16384: response=failure(413,'REQUEST_TOO_LARGE','请求过大。')
                    else:
                        request._body=b''.join(chunks)
                        response=await call_next(request)
            except Exception: response=failure(500,'INTERNAL_ERROR','服务暂时无法完成请求。')
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; media-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='no-referrer'
        if request.url.path.startswith(PREFIX): response.headers['Cache-Control']='no-store'
        return response
    @app.exception_handler(APIError)
    async def api_error(request,error): return failure(error.status,error.code,error.message)
    @app.exception_handler(Exception)
    async def internal_error(request,error): return failure(500,'INTERNAL_ERROR','服务暂时无法完成请求。')


def create_v5_application(db_path,*,generation_service=None,companion_service=None,runtime=None,provider=None,dev=False):
    app=FastAPI(title='逃离校园实验室 v5',version='2.0.0',docs_url=None,redoc_url=None,openapi_url=None)
    app.state.v5_database=V5Database(db_path)
    if generation_service is None or companion_service is None:
        from ..ai.v5 import GenerationService,CompanionService
        if generation_service is None: generation_service=GenerationService()
        if companion_service is None: companion_service=CompanionService()
    app.state.generation_service=generation_service
    app.state.companion_service=companion_service or runtime
    app.state.ai_provider=provider
    install_security(app,dev=dev)
    app.include_router(router)
    @app.get('/health')
    @app.get(PREFIX+'/health')
    def health(): return {'status':'ok','service':'campus-lab-escape-v5','gameplay_version':'v5','api_version':'2.0.0'}
    dist=Path(__file__).resolve().parents[3]/'frontend'/'dist-v5'
    @app.get('/{asset_path:path}')
    def static(asset_path:str):
        if asset_path.startswith('api/') or any(part.startswith('.') for part in asset_path.replace('\\','/').split('/')): return failure(404,'NOT_FOUND','未找到该资源。')
        target=(dist/asset_path).resolve()
        if not target.is_relative_to(dist.resolve()): return failure(404,'NOT_FOUND','未找到该资源。')
        if target.is_file(): return FileResponse(target)
        if not asset_path and (dist/'index.html').is_file(): return FileResponse(dist/'index.html')
        return failure(404,'NOT_FOUND','未找到该资源。')
    return app
