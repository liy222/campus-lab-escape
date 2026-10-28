"""Rebuild additive V2 data contracts; never writes the classic contracts."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.api.v5 import Credentials, SessionRequest, GenerationRequest, LogoutRequest, router
from backend.app.domain.models import ActionRequest, VersionRequest
from backend.app.domain.graybox_models import HintRequest
from backend.app.domain.save_models import CreateSaveRequest
from backend.app.domain.generated import Draft, TOOL_MODELS

HERE = Path(__file__).parent
DIALECT = 'https://json-schema.org/draft/2020-12/schema'
def obj(properties, required=None):
    return {'type':'object','properties':properties,'required':list(properties) if required is None else required,'additionalProperties':False}
def ref(name): return {'$ref':'#/$defs/'+name}
def arr(items): return {'type':'array','items':items}
def nullable(value): return {'anyOf':[value,{'type':'null'}]}
def string(limit=4000): return {'type':'string','maxLength':limit}
def enum(*values): return {'enum':list(values)}
def const(value): return {'const':value}

def build():
    definitions = copy.deepcopy(json.loads((HERE.parent/'api.schema.json').read_text(encoding='utf-8'))['$defs'])
    sid = {'type':'string','minLength':1,'maxLength':100,'pattern':'^[A-Za-z0-9_-]+$'}
    n = {'type':'integer','minimum':0}; boolean={'type':'boolean'}
    status=enum('playing','won'); stamp={'type':'string','format':'date-time'}
    def model(name, cls):
        schema=cls.model_json_schema(); definitions.update(schema.pop('$defs',{})); definitions[name]=schema
    for name,cls in [('credentials',Credentials),('session_request',SessionRequest),('generation_request',GenerationRequest),('logout_request',LogoutRequest),('action_request',ActionRequest),('version_request',VersionRequest),('hint_request',HintRequest),('create_save_request',CreateSaveRequest)]: model(name,cls)
    classic=copy.deepcopy(definitions['graybox_visible_state'])
    classic['properties'].update(mode=const('classic'),level_id={'type':'null'})
    classic['required']+=['mode','level_id']; definitions['classic_visible_state']=classic
    saved=copy.deepcopy(definitions['graybox_save_metadata']); saved['properties']['schema_version']=const('2.0.0'); saved['properties']['level_version']=const('5.0.0')
    definitions['generated_save_metadata']=saved
    classic_game=classic['properties']['minigames']['properties']
    board=copy.deepcopy(classic_game['circuit']['anyOf'][0]); board['properties']['target_id']=sid
    sequence=obj({'target_id':sid,'length':const(4),'status':enum('editing','completed'),'devices':arr(obj({'device_id':string(40),'label':string(40),'symbol':string(40)}))})
    definitions['generated_circuit']=board; definitions['generated_sequence']=sequence
    stats=obj({'started_at':stamp,'finished_at':nullable(stamp),'current_hint_level':enum(1,2,3),**{k:n for k in ('clues_found','clues_total','puzzles_solved','puzzles_total','hint_count','mistake_count')},'hidden_found':const(0),'hidden_total':const(0)})
    settlement=copy.deepcopy(stats); settlement['properties'].update(elapsed_seconds=n,rating=enum('S','A','B','C')); settlement['required']+=['elapsed_seconds','rating']
    definitions['generated_visible_state']=obj({
        'schema_version':const('2.0.0'),'level_version':const('5.0.0'),'mode':const('generated'),'level_id':nullable(sid),
        'definition_hash':{'type':'string','pattern':'^[a-f0-9]{64}$'},'session_id':sid,'room_id':sid,
        'room':obj({'room_id':sid,'name':string(40),'description':string(240),'background_id':enum('neutral_lab','neutral_archive','neutral_control'),'background_art_id':enum('neutral_lab','neutral_archive','neutral_control')}),
        'inventory':arr(obj({'item_id':sid,'name':string(40),'art_id':const('key')})),
        'objects':arr(obj({'object_id':sid,'name':string(40),'kind':enum('clue','item','puzzle'),'description':string(), 'art_id':enum('note','key','terminal','cabinet','circuit','panel'),'slot':{'type':'integer','minimum':0,'maximum':7},'target_id':nullable(sid),'mechanism':nullable(enum('item','code','sequence','circuit')),'completed':boolean,'actions':arr(obj({'tool':sid,'label':string(),'arguments':{'type':'object','additionalProperties':string()}}))})),
        'clues':arr(obj({'clue_id':sid,'object_id':sid,'title':string(),'text':string()})),
        'observed_object_ids':arr(sid),'exits':arr(obj({'destination_id':sid,'name':string(40),'unlocked':boolean})),
        'minigames':obj({'circuits':arr(ref('generated_circuit')),'sequences':arr(ref('generated_sequence')),'circuit':nullable(ref('generated_circuit')),'sequence':nullable(ref('generated_sequence'))}),
        'statistics':stats,'settlement':nullable(settlement),'status':status,'revision':n,'generation':{'type':'string','format':'uuid'},'save':nullable(ref('generated_save_metadata')),'flags':obj({})})
    definitions['visible_state']={'oneOf':[ref('classic_visible_state'),ref('generated_visible_state')]}
    generated_slot=copy.deepcopy(definitions['save_slot']['oneOf'][-2]); generated_slot['properties'].update(schema_version=const('2.0.0'),level_version=const('5.0.0'),room_id=sid)
    definitions['save_slot']['oneOf'].append(generated_slot)
    # Generic generated actions carry strings/arrays; old receipt enum was classic-only.
    for variant in definitions['receipt']['oneOf']:
        tool=variant['properties']['tool'].get('const')
        if tool in TOOL_MODELS: variant['properties']['arguments']=TOOL_MODELS[tool].model_json_schema()
    definitions['ai_turn_data']['properties']['answer']=string(360)
    definitions['ai_turn_data']['properties']['proposal']={'type':'null'}
    definitions['auth_data']=obj({'user':nullable(obj({'user_id':sid,'username':string(24)})),'auth_context':nullable(sid),'csrf_token':string(256)})
    definitions['job']=obj({'job_id':sid,'status':enum('pending','generating','validating','ready','rejected','failed','unknown'),'room_count':enum(1,2,3),'difficulty':enum('easy','normal','hard'),'created_at':{'type':'number'},'updated_at':{'type':'number'},'level_id':nullable(sid),'error_code':nullable(sid)})
    definitions['level']=obj({'level_id':sid,'title':string(40),'story':string(240),'room_count':enum(1,2,3),'difficulty':enum('easy','normal','hard'),'definition_hash':string(64),'definition_version':const('1.0.0'),'rules_version':const('1.0.0'),'policy_version':enum('0.9.0','1.0.0'),'created_at':stamp})
    # Optional read projection: redaction can expand a 2000-character theme 10x.
    definitions['level']['properties']['theme']=string(20000)
    definitions['session_summary']=obj({'session_id':sid,'mode':enum('classic','generated'),'level_id':string(100),'created_at':stamp,'status':status,'room_id':sid,'revision':n,'clues_found':n,'puzzles_solved':n})
    def response(name, data): definitions[name]=obj({'ok':const(True),'event_id':sid,'data':data})
    response('auth_response',ref('auth_data')); response('logout_response',obj({'logged_out':const(True)}))
    response('sessions_response',obj({'sessions':arr(ref('session_summary'))}))
    response('session_response',obj({'session_id':sid,'existing':boolean,'mode':enum('classic','generated'),'level_id':nullable(sid),'visible_state':ref('visible_state')}))
    for singular,plural in [('job','jobs'),('level','levels')]:
        response(singular+'_response',obj({singular:ref(singular)})); response(plural+'_response',obj({plural:arr(ref(singular))}))
    definitions['error_response']=obj({'ok':const(False),'event_id':sid,'error':obj({'code':sid,'message':string()}),'visible_state':ref('visible_state')},['ok','event_id','error'])
    api={'$schema':DIALECT,'title':'Campus escape authenticated API V2','contract_version':'2.0.0','$defs':definitions}
    pairs={
        ('GET','/auth/csrf'):(None,'auth_response'),('POST','/auth/register'):('credentials','auth_response'),('POST','/auth/login'):('credentials','auth_response'),('GET','/auth/me'):(None,'auth_response'),('POST','/auth/logout'):('logout_request','logout_response'),
        ('GET','/sessions'):(None,'sessions_response'),('POST','/sessions'):('session_request','session_response'),('GET','/sessions/{sid}/state'):(None,'state_response'),('POST','/sessions/{sid}/actions'):('action_request','action_response'),('POST','/sessions/{sid}/reset'):('version_request','control_response'),
        ('GET','/sessions/{sid}/saves'):(None,'list_saves_response'),('POST','/sessions/{sid}/saves'):('create_save_request','save_slot_response'),('POST','/sessions/{sid}/saves/{save_id}/restore'):('version_request','save_slot_response'),('POST','/sessions/{sid}/saves/{save_id}/delete'):('version_request','delete_save_response'),('POST','/sessions/{sid}/ai/turns'):('hint_request','ai_turn_response'),
        ('GET','/level-generations'):(None,'jobs_response'),('POST','/level-generations'):('generation_request','job_response'),('GET','/level-generations/{job_id}'):(None,'job_response'),('GET','/levels'):(None,'levels_response'),('GET','/levels/{lid}'):(None,'level_response')}
    routes=[]
    for (method,path),(request,response_name) in pairs.items():
        routes.append({'method':method,'path':'/api/v2'+path,'request':request,'response':response_name,'authenticated':path not in {'/auth/csrf','/auth/register','/auth/login'},'csrf_required':method=='POST','success_statuses':[200,201] if path in {'/sessions','/auth/register'} else [201] if path=='/sessions/{sid}/saves' and method=='POST' else [200,202] if path=='/level-generations' and method=='POST' else [200]})
    draft=Draft.model_json_schema(); draft['$schema']=DIALECT
    return {'api.schema.json':api,'level-draft.schema.json':draft,'routes.json':{'contract_version':'2.0.0','schema':'api.schema.json','routes':routes,'health_paths':['/health','/api/v2/health'],'headers':{'mutations':['Origin','Content-Type: application/json','X-CSRF-Token','X-Auth-Context'],'generation':['X-AI-Api-Key'],'partner':['X-AI-Provider','X-AI-Api-Key']}}}

if __name__=='__main__':
    for name,value in build().items(): (HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
