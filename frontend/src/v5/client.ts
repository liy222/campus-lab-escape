import { ApiError, type VisibleState, type Session, api as classicApi } from '../api';
export type Identity = { user_id: string; username: string };
export type Auth = { user: Identity | null; auth_context: string | null; csrf_token: string };
export type Level = { level_id: string; title?: string; theme?: string; room_count: number; difficulty: string; created_at?: string };
export type Run = { session_id: string; mode: 'classic' | 'generated'; level_id: string | null; status?: string; room_id?: string; revision?: number };
export type Job = { job_id: string; status: 'pending'|'generating'|'validating'|'ready'|'rejected'|'failed'|'unknown'; level_id?: string; error_code?: string; error?: {code?:string;message?:string}|string; message?: string };
export function sanitize(value: string, key = '') { return (key ? value.split(key).join('[已隐藏]') : value).replace(/sk-[A-Za-z0-9_-]{8,}/g, '[已隐藏]'); }
export class V5Client {
  auth: Auth = { user: null, auth_context: null, csrf_token: '' };
  epoch = 0;
  onInvalid: (() => void) | null = null;
  async request<T>(path: string, body?: object, extra: Record<string,string> = {}, timeoutMs=20000): Promise<{ok:true;event_id:string;data:T}> {
    const stamp = this.epoch;
    const headers: Record<string,string> = {...extra};
    if (body !== undefined) {
      headers['Content-Type']='application/json'; headers['X-CSRF-Token']=this.auth.csrf_token;
      if(this.auth.auth_context) headers['X-Auth-Context']=this.auth.auth_context;
    }
    const controller = new AbortController(); const timer = window.setTimeout(()=>controller.abort(),timeoutMs);
    try {
      const res = await fetch(`/api/v2/${path}`,{method:body===undefined?'GET':'POST',credentials:'same-origin',cache:'no-store',headers,body:body===undefined?undefined:JSON.stringify(body),signal:controller.signal});
      const value = await res.json();
      if(stamp !== this.epoch) throw new ApiError('STALE_AUTH','账号已更换，旧响应已忽略。');
      if(!res.ok || value?.ok!==true) {
        const code = value?.error?.code || 'SERVICE_UNAVAILABLE';
        if(['AUTH_CONTEXT_MISMATCH','AUTH_REQUIRED','UNAUTHENTICATED','CSRF_INVALID','INVALID_CSRF','CSRF_FAILED','CSRF_REJECTED','AUTH_CONTEXT_CHANGED'].includes(code)||res.status===401) { this.epoch++; this.auth={user:null,auth_context:null,csrf_token:''}; this.onInvalid?.(); }
        throw new ApiError(code,sanitize(value?.error?.message || '请求未完成，请同步后重试。'),value?.visible_state||null,value?.event_id||null);
      }
      return value;
    } catch(e) { if(e instanceof ApiError)throw e; throw new ApiError('NETWORK_ERROR','连接中断或请求超时；结果未知。请查询当前状态，勿重复提交。'); }
    finally {window.clearTimeout(timer);}
  }
  async refresh() { const r=await this.request<Auth>('auth/me'); if(this.auth.auth_context && this.auth.auth_context!==r.data.auth_context) this.epoch++; this.auth=r.data; return r.data; }
  async csrf() { const r=await this.request<Auth>('auth/csrf');this.auth=r.data;return r.data; }
  async authenticate(operation:'login'|'register',username:string,password:string) {const r=await this.request<Auth>(`auth/${operation}`,{username,password});this.epoch++;this.auth=r.data;return r.data;}
  async logout(){await this.request('auth/logout',{});this.epoch++;this.auth={user:null,auth_context:null,csrf_token:''};}
  version(state:VisibleState){return {request_id:crypto.randomUUID(),revision:state.revision,generation:state.generation};}
  classic(sessionId: string): typeof classicApi {
    const p=`sessions/${encodeURIComponent(sessionId)}`;
    const boundOwner=this.auth.user?.user_id,boundContext=this.auth.auth_context,boundEpoch=this.epoch;
    const assertBound=()=>{if(boundOwner!==this.auth.user?.user_id||boundContext!==this.auth.auth_context||boundEpoch!==this.epoch)throw new ApiError('STALE_AUTH','账号状态已改变，临时密钥已失效，请重新登录。');};
    const req=<T,>(suffix:string,body?:object,headers?:Record<string,string>,timeout?:number)=>{assertBound();return this.request<T>(`${p}${suffix}`,body,headers,timeout);};
    return {
      create:async()=>{assertBound();const r=await this.request<{session_id:string;visible_state:VisibleState}>('sessions',{request_id:crypto.randomUUID(),mode:'classic'});return {...r,data:{...r.data,token:''}};},
      state:()=>req('/state'),saveSlots:()=>req('/saves'),
      createSaveSlot:(_s,state,name)=>req('/saves',{...this.version(state),...(name?{name}:{})}),
      restoreSaveSlot:(_s,state,id)=>req(`/saves/${encodeURIComponent(id)}/restore`,this.version(state)),
      deleteSaveSlot:(_s,state,id)=>req(`/saves/${encodeURIComponent(id)}/delete`,this.version(state)),
      action:(_s,state,tool,args)=>req('/actions',{...this.version(state),tool,arguments:args}),
      control:(_s,state)=>req('/reset',this.version(state)),
      ai:(_s,state,message,settings={provider:'mock'},hintLevel)=>req('/ai/turns',{...this.version(state),message:sanitize(message,settings.provider==='deepseek'?settings.apiKey:''),...(hintLevel?{hint_level:hintLevel}:{})},{'X-AI-Provider':settings.provider,...(settings.provider==='deepseek'?{'X-AI-Api-Key':settings.apiKey.trim()}:{})},55000),
      confirm:()=>Promise.reject(new ApiError('UNSUPPORTED','伙伴不会代替你执行行动。')),cancel:()=>Promise.reject(new ApiError('UNSUPPORTED','没有待执行的建议。')),
    } as typeof classicApi;
  }
}
export const localSession = (session_id:string):Session=>({session_id,token:''});
