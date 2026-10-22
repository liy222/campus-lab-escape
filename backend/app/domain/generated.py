"""Strict generated definitions, deterministic compilation and authoritative rules.

Drafts contain clue facts and recipes, never supplied answers or executable content.
The private compiler derives solutions and proves a real-action witness.
"""
from __future__ import annotations
import hashlib
import itertools
import json
import re
import time
from dataclasses import dataclass
from typing import ClassVar
from collections import deque
from pathlib import Path
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4
from pydantic import Field
from .models import StrictModel, Identifier, RuleError, InspectArgs, TakeArgs, UseArgs
from . import circuit

Text = Annotated[str, Field(min_length=1, max_length=240)]
Short = Annotated[str, Field(min_length=1, max_length=40)]
IdList = Annotated[list[Identifier], Field(max_length=8)]
Background = Literal['neutral_lab','neutral_archive','neutral_control']
Art = Literal['note','key','terminal','cabinet','circuit','panel']

class Clue(StrictModel):
    clue_id: Identifier
    tokens: Annotated[list[Short], Field(max_length=8)] = Field(default_factory=list)
    indices: Annotated[list[Annotated[int,Field(ge=1,le=8)]], Field(max_length=8)] = Field(default_factory=list)
    symbol_map: dict[Short, Short] = Field(default_factory=dict)

class Object(StrictModel):
    object_id: Identifier
    name: Short
    description: Text
    slot: Annotated[int,Field(ge=0,le=7)]
    art_id: Art
    kind: Literal['clue','item','puzzle']
    clue_id: Identifier | None = None
    item_id: Identifier | None = None
    puzzle_id: Identifier | None = None
    locked_by: IdList = Field(default_factory=list)

class Room(StrictModel):
    room_id: Identifier
    name: Short
    description: Text
    background_id: Background
    objects: Annotated[list[Object],Field(min_length=1,max_length=8)]

class Puzzle(StrictModel):
    puzzle_id: Identifier
    room_id: Identifier
    mechanism: Literal['item','code','sequence','circuit']
    prerequisite_ids: IdList = Field(default_factory=list)
    required_item_id: Identifier | None = None
    clue_ids: Annotated[list[Identifier],Field(max_length=4)] = Field(default_factory=list)
    recipe: Literal['concat','index','symbol_map'] = 'concat'

class Draft(StrictModel):
    title: Short
    story: Text
    rooms: Annotated[list[Room],Field(min_length=1,max_length=3)]
    clues: Annotated[list[Clue],Field(max_length=18)]
    puzzles: Annotated[list[Puzzle],Field(min_length=2,max_length=6)]

class GeneratedState(StrictModel):
    level_version: Literal['5.0.0'] = '5.0.0'
    definition_hash: str
    owner_id: str = 'private'
    level_id: str = 'private'
    definition_version: Literal['1.0.0'] = '1.0.0'
    rules_version: Literal['1.0.0'] = '1.0.0'
    policy_version: Literal['1.0.0','0.9.0'] = '1.0.0'
    room_id: str
    inventory: list[str] = Field(default_factory=list)
    discovered_clue_ids: list[str] = Field(default_factory=list)
    observed_object_ids: list[str] = Field(default_factory=list)
    solved_puzzle_ids: list[str] = Field(default_factory=list)
    circuit_rotations: dict[str,list[int]] = Field(default_factory=dict)
    status: Literal['playing','won'] = 'playing'
    revision: Annotated[int,Field(ge=0)] = 0
    generation: str = Field(default_factory=lambda:str(uuid4()))
    started_at: str
    finished_at: str | None = None
    hint_count: Annotated[int,Field(ge=0)] = 0
    mistake_count: Annotated[int,Field(ge=0)] = 0

class TargetArgs(StrictModel):
    target_id: Identifier
class CodeArgs(TargetArgs):
    code: Annotated[str,Field(min_length=1,max_length=64)]
class SequenceArgs(TargetArgs):
    device_ids: Annotated[list[Identifier],Field(min_length=4,max_length=4)]
class RotateArgs(TargetArgs):
    module_id: Literal['c00','c01','c02','c10','c11','c12','c20','c21','c22']
class MoveArgs(StrictModel):
    destination_id: Identifier
class InventoryArgs(StrictModel):
    pass
TOOL_MODELS = {'inspect':InspectArgs,'take':TakeArgs,'use_item':UseArgs,'submit_code':CodeArgs,
               'submit_sequence':SequenceArgs,'rotate_circuit':RotateArgs,'submit_circuit':TargetArgs,
               'move':MoveArgs,'get_inventory':InventoryArgs}

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def strict_json(value):
    if isinstance(value,str):
        if len(value.encode()) > 65536: raise ValueError('OUTPUT_SIZE')
        def pairs(entries):
            obj={}
            for key,item in entries:
                if key in obj: raise ValueError('DUPLICATE_KEY')
                obj[key]=item
            return obj
        value=json.loads(value,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE')))
    def visit(item,depth=0):
        if depth>32: raise ValueError('OUTPUT_DEPTH')
        if isinstance(item,dict):
            for k,v in item.items(): visit(k,depth+1); visit(v,depth+1)
        elif isinstance(item,list):
            for v in item: visit(v,depth+1)
        elif isinstance(item,str) and re.search(r'https?://|file:|(?:[A-Za-z]:[\\/])|[<>]|javascript:|(?:^|\s)(?:/[A-Za-z]|\\\\)|\b(?:DROP|ALTER|CREATE)\s+(?:TABLE|DATABASE)\b|\b(?:eval|exec|import|__import__)\s*\(',item,re.I):
            raise ValueError('UNSAFE_TEXT')
    visit(value)
    if len(canonical(value).encode()) > 65536: raise ValueError('OUTPUT_SIZE')
    return value

@dataclass(frozen=True,slots=True,init=False)
class CompiledLevel:
    """Immutable canonical definition; properties return independent parsed copies."""
    version: ClassVar[str]='1.0.0'
    _json: str
    _answers: str
    _witness: str
    definition_hash: str
    policy_version: str
    def __init__(self,draft,answers,witness,policy_version='1.0.0'):
        encoded=canonical(draft.model_dump())
        payload={'definition_version':'1.0.0','rules_version':'1.0.0','policy_version':policy_version,'draft':json.loads(encoded)}
        object.__setattr__(self,'_json',encoded)
        object.__setattr__(self,'definition_hash',hashlib.sha256(canonical(payload).encode()).hexdigest())
        object.__setattr__(self,'_answers',canonical(answers))
        object.__setattr__(self,'_witness',canonical(witness))
        object.__setattr__(self,'policy_version',policy_version)
    @property
    def draft(self): return Draft.model_validate(json.loads(self._json))
    @property
    def answers(self): return json.loads(self._answers)
    @property
    def witness(self): return json.loads(self._witness)
    def private_dump(self):
        return {'version':self.version,'definition_version':'1.0.0','rules_version':'1.0.0','policy_version':self.policy_version,'definition_hash':self.definition_hash,'draft':json.loads(self._json)}

def derive(p,clues):
    selected=[clues[x] for x in p.clue_ids]
    tokens=[t for c in selected for t in c.tokens]
    indices=[i for c in selected for i in c.indices]
    mapping={k:v for c in selected for k,v in c.symbol_map.items()}
    if p.recipe=='concat':
        if any(not c.tokens or c.indices or c.symbol_map for c in selected): raise ValueError('UNUSED_FACTS')
        result=tokens
    elif p.recipe=='index':
        if any(not(c.tokens or c.indices) or c.symbol_map for c in selected): raise ValueError('UNUSED_FACTS')
        if not indices or any(i>len(tokens) for i in indices): raise ValueError('INSUFFICIENT_FACTS')
        result=[tokens[i-1] for i in indices]
    else:
        if any(not(c.tokens or c.symbol_map) or c.indices for c in selected): raise ValueError('UNUSED_FACTS')
        if not tokens or any(t not in mapping for t in tokens): raise ValueError('INSUFFICIENT_FACTS')
        result=[mapping[t] for t in tokens]
    if not result: raise ValueError('INSUFFICIENT_FACTS')
    if p.mechanism=='sequence':
        if len(result)!=4 or len(set(result))!=4 or any(not re.fullmatch('[A-Za-z0-9_-]+',t) for t in result): raise ValueError('INVALID_SEQUENCE')
        return result
    value=''.join(result)
    if not re.fullmatch(r'[0-9]{1,16}',value): raise ValueError('INVALID_CODE')
    return value

def compile_level(raw,room_count,difficulty,*,prove=True,policy_version='1.0.0'):
    if policy_version not in {'1.0.0','0.9.0'}: raise ValueError('POLICY_VERSION')
    d=Draft.model_validate(strict_json(raw))
    catalog=json.loads((Path(__file__).resolve().parents[3]/'frontend'/'src'/'assets'/'generated-catalog.json').read_text(encoding='utf-8-sig'))
    roles={entry['id']:entry['role'] for entry in catalog['assets']}
    if catalog.get('version')!=1 or any(roles.get(r.background_id)!='background' for r in d.rooms) or any(roles.get(o.art_id)!='object' for r in d.rooms for o in r.objects): raise ValueError('ASSET_CATALOG')
    increment={'easy':1,'normal':2,'hard':3}[difficulty]
    if len(d.rooms)!=room_count or len(d.puzzles)!=min(6,room_count+increment): raise ValueError('PUZZLE_COUNT')
    rooms={r.room_id:r for r in d.rooms}; clues={c.clue_id:c for c in d.clues}; puzzles={p.puzzle_id:p for p in d.puzzles}
    objects=[o for r in d.rooms for o in r.objects]
    ids=[r.room_id for r in d.rooms]+[c.clue_id for c in d.clues]+[p.puzzle_id for p in d.puzzles]+[o.object_id for o in objects]+[o.item_id for o in objects if o.item_id]
    if len(ids)!=len(set(ids)) or 'EXIT' in ids: raise ValueError('DUPLICATE_ID')
    if len([o for o in objects if o.kind=='item'])>4: raise ValueError('ITEM_LIMIT')
    items={o.item_id:(r.room_id,o) for r in d.rooms for o in r.objects if o.kind=='item'}
    if any(len({o.slot for o in r.objects})!=len(r.objects) for r in d.rooms): raise ValueError('DUPLICATE_SLOT')
    for o in objects:
        if o.kind=='clue' and (o.clue_id not in clues or o.item_id or o.puzzle_id): raise ValueError('UNKNOWN_REFERENCE')
        if o.kind=='item' and (not o.item_id or o.clue_id or o.puzzle_id): raise ValueError('INVALID_ITEM')
        if o.kind=='puzzle' and (o.puzzle_id not in puzzles or o.clue_id or o.item_id): raise ValueError('UNKNOWN_REFERENCE')
        if len(o.locked_by)!=len(set(o.locked_by)): raise ValueError('DUPLICATE_REFERENCE')
        if any(x not in puzzles for x in o.locked_by): raise ValueError('UNKNOWN_REFERENCE')
    if sorted(o.clue_id for o in objects if o.kind=='clue')!=sorted(clues): raise ValueError('CLUE_REFERENCE')
    if sorted(o.puzzle_id for o in objects if o.kind=='puzzle')!=sorted(puzzles): raise ValueError('PUZZLE_REFERENCE')
    answers={}; combos=0
    for p in d.puzzles:
        if len(p.prerequisite_ids)!=len(set(p.prerequisite_ids)) or len(p.clue_ids)!=len(set(p.clue_ids)): raise ValueError('DUPLICATE_REFERENCE')
        if p.room_id not in rooms or any(x not in puzzles or x==p.puzzle_id for x in p.prerequisite_ids): raise ValueError('UNKNOWN_REFERENCE')
        actual=[r.room_id for r in d.rooms for o in r.objects if o.puzzle_id==p.puzzle_id]
        if actual!=[p.room_id]: raise ValueError('PUZZLE_ROOM')
        if any(x not in clues for x in p.clue_ids): raise ValueError('UNKNOWN_REFERENCE')
        if p.mechanism=='item':
            if p.required_item_id not in items or p.clue_ids: raise ValueError('ITEM_REFERENCE')
        elif p.required_item_id is not None: raise ValueError('UNEXPECTED_ITEM')
        if p.mechanism in {'code','sequence'}:
            answers[p.puzzle_id]=derive(p,clues)
            if len(p.clue_ids)>=2: combos+=1
        elif p.clue_ids: raise ValueError('UNEXPECTED_FACTS')
    if policy_version=='1.0.0' and difficulty=='normal' and combos<1 or difficulty=='hard' and combos<2: raise ValueError('COMBINATION_COUNT')
    def depth(pid,seen):
        if pid in seen: raise ValueError('DEPENDENCY_CYCLE')
        return 1+max([depth(x,seen|{pid}) for x in puzzles[pid].prerequisite_ids] or [0])
    if difficulty=='hard' and max(depth(p,set()) for p in puzzles)<3: raise ValueError('DEPENDENCY_DEPTH')
    for p in puzzles: depth(p,set())
    if room_count>1:
        cross=any(p.mechanism=='item' and items[p.required_item_id][0]!=p.room_id for p in d.puzzles)
        cross=cross or any(any(next(r.room_id for r in d.rooms for o in r.objects if o.clue_id==cid)!=p.room_id for cid in p.clue_ids) for p in d.puzzles)
        if not cross: raise ValueError('CROSS_ROOM_REQUIRED')
    decorative=[d.title,d.story]+[v for r in d.rooms for v in (r.name,r.description)]+[v for o in objects for v in (o.name,o.description)]
    for answer in answers.values():
        if isinstance(answer,str) and len(answer)>=3 and any(answer in text for text in decorative): raise ValueError('ANSWER_IN_PROSE')
        if isinstance(answer,list) and any(sep.join(answer) in text for sep in ('','、',',',' → ') for text in decorative): raise ValueError('ANSWER_IN_PROSE')
    compiled=CompiledLevel(d,answers,[],policy_version)
    if prove:
        witness=solve(compiled)
        compiled=CompiledLevel(d,answers,witness,policy_version)
    return compiled

class GeneratedRules:
    SCHEMA_VERSION='2.0.0'
    LEVEL_VERSION='5.0.0'
    state_model=GeneratedState
    tool_models=TOOL_MODELS
    game_fields=set(GeneratedState.model_fields)-{'revision','generation'}
    def __init__(self,compiled,*,owner_id='private',level_id='private'):
        self.compiled=compiled; self.d=compiled.draft; self.owner_id=owner_id; self.level_id=level_id
        self.rooms={r.room_id:r for r in self.d.rooms}; self.puzzles={p.puzzle_id:p for p in self.d.puzzles}
        self.objects={o.object_id:(r.room_id,o) for r in self.d.rooms for o in r.objects}
        self.clues={c.clue_id:c for c in self.d.clues}
    def initial_state(self,revision=0):
        return GeneratedState(definition_hash=self.compiled.definition_hash,owner_id=self.owner_id,level_id=self.level_id,policy_version=self.compiled.policy_version,room_id=self.d.rooms[0].room_id,started_at=now(),revision=revision,
             circuit_rotations={p.puzzle_id:[0]*9 for p in self.d.puzzles if p.mechanism=='circuit'})
    def validate_invariants(self,s):
        if s.owner_id!=self.owner_id or s.level_id!=self.level_id or s.definition_hash!=self.compiled.definition_hash or s.definition_version!='1.0.0' or s.rules_version!='1.0.0' or s.policy_version!=self.compiled.policy_version or s.level_version!='5.0.0': raise ValueError('DEFINITION_MISMATCH')
        if s.room_id not in self.rooms and s.room_id!='EXIT': raise ValueError('UNKNOWN_ROOM')
        if (s.status=='won')!=(s.room_id=='EXIT') or (s.status=='won')!=(s.finished_at is not None): raise ValueError('WIN_STATE')
        for values,valid in ((s.inventory,{o.item_id for _,o in self.objects.values() if o.item_id}),(s.discovered_clue_ids,set(self.clues)),(s.observed_object_ids,set(self.objects)),(s.solved_puzzle_ids,set(self.puzzles))):
            if len(values)!=len(set(values)) or not set(values)<=valid: raise ValueError('INVALID_STATE_REFERENCE')
        solved=set(s.solved_puzzle_ids)
        for pid in solved:
            p=self.puzzles[pid]
            if not set(p.prerequisite_ids)<=solved: raise ValueError('MISSING_PREREQUISITE')
            if p.mechanism=='item' and p.required_item_id not in s.inventory: raise ValueError('MISSING_ITEM')
            if p.mechanism in {'code','sequence'} and not set(p.clue_ids)<=set(s.discovered_clue_ids): raise ValueError('MISSING_CLUES')
        for _,o in self.objects.values():
            if o.clue_id in s.discovered_clue_ids and o.object_id not in s.observed_object_ids: raise ValueError('CLUE_NOT_OBSERVED')
            if (o.item_id in s.inventory or o.clue_id in s.discovered_clue_ids or o.object_id in s.observed_object_ids) and not set(o.locked_by)<=solved: raise ValueError('LOCKED_OBJECT')
        if set(s.circuit_rotations)!={p.puzzle_id for p in self.d.puzzles if p.mechanism=='circuit'}: raise ValueError('INVALID_CIRCUIT')
        for pid,rot in s.circuit_rotations.items():
            if len(rot)!=9 or any(type(x)!=int or not 0<=x<4 for x in rot): raise ValueError('INVALID_CIRCUIT')
            if pid in solved and not circuit.connected(rot): raise ValueError('DISCONNECTED_CIRCUIT')
        for i,r in enumerate(self.d.rooms):
            if s.room_id==r.room_id and any(p.room_id in {x.room_id for x in self.d.rooms[:i]} and p.puzzle_id not in solved for p in self.d.puzzles): raise ValueError('LOCKED_ROOM')
        if s.status=='won' and len(solved)!=len(self.puzzles): raise ValueError('INCOMPLETE_EXIT')
        if not s.started_at.endswith('Z') or s.finished_at is not None and not s.finished_at.endswith('Z'): raise ValueError('INVALID_TIME')
        start=datetime.fromisoformat(s.started_at.replace('Z','+00:00'))
        if start.tzinfo is None or s.finished_at and datetime.fromisoformat(s.finished_at.replace('Z','+00:00'))<start: raise ValueError('INVALID_TIME')
    def available(self,s):
        return [o for rid,o in self.objects.values() if rid==s.room_id and set(o.locked_by)<=set(s.solved_puzzle_ids) and not(o.kind=='item' and o.item_id in s.inventory)]
    def exits(self,s):
        if s.room_id=='EXIT': return []
        i=[r.room_id for r in self.d.rooms].index(s.room_id)
        result=[]
        if i: result.append({'destination_id':self.d.rooms[i-1].room_id,'name':self.d.rooms[i-1].name,'unlocked':True})
        unlocked=all(p.puzzle_id in s.solved_puzzle_ids for p in self.d.puzzles if p.room_id==s.room_id)
        target=self.d.rooms[i+1].room_id if i+1<len(self.d.rooms) else 'EXIT'
        result.append({'destination_id':target,'name':self.rooms[target].name if target!='EXIT' else '出口','unlocked':unlocked})
        return result
    def visible_state(self,sid,s,save=None):
        objects=[]; games={'circuits':[],'sequences':[],'circuit':None,'sequence':None}
        for o in self.available(s):
            actions=[{'tool':'inspect','label':'查看','arguments':{'object_id':o.object_id}}]
            if s.status=='playing':
                if o.kind=='item': actions.append({'tool':'take','label':'拿取','arguments':{'item_id':o.item_id}})
                if o.kind=='puzzle':
                    p=self.puzzles[o.puzzle_id]
                    if p.puzzle_id not in s.solved_puzzle_ids and set(p.prerequisite_ids)<=set(s.solved_puzzle_ids):
                        if p.mechanism=='item':
                            for item in s.inventory: actions.append({'tool':'use_item','label':'使用物品','arguments':{'item_id':item,'target_id':p.puzzle_id}})
                        else: actions.append({'tool':{'code':'submit_code','sequence':'submit_sequence','circuit':'submit_circuit'}[p.mechanism],'label':'提交','arguments':{'target_id':p.puzzle_id}})
                    if p.mechanism=='circuit' and o.object_id in s.observed_object_ids:
                        board=circuit.board(s.circuit_rotations[p.puzzle_id],p.puzzle_id in s.solved_puzzle_ids); board['target_id']=p.puzzle_id; games['circuits'].append(board)
                    if p.mechanism=='sequence' and o.object_id in s.observed_object_ids:
                        # Options are the public fact vocabulary, never ordered answer data.
                        opts=sorted({v for cid in p.clue_ids for v in self.clues[cid].tokens}|{v for cid in p.clue_ids for v in self.clues[cid].symbol_map.values()})
                        games['sequences'].append({'target_id':p.puzzle_id,'length':4,'devices':[{'device_id':v,'label':v,'symbol':v} for v in opts], 'status':'completed' if p.puzzle_id in s.solved_puzzle_ids else 'editing'})
            description=o.description
            if o.kind=='puzzle':
                p=self.puzzles[o.puzzle_id]
                description+=' '+({'item':'将匹配的背包物品用于此装置，物品不会消耗。','circuit':'旋转模块，让入口与出口通过双方接口连通。'}.get(p.mechanism) or {'concat':'按资料列出的顺序拼接源序。','index':'按资料中的读取位置，从一开始读取源序。','symbol_map':'按资料源序逐项查找对应关系。'}[p.recipe])
            objects.append({'object_id':o.object_id,'name':o.name,'kind':o.kind,'description':description,'art_id':o.art_id,'slot':o.slot,'target_id':o.puzzle_id,'mechanism':self.puzzles[o.puzzle_id].mechanism if o.puzzle_id else None,'completed':o.puzzle_id in s.solved_puzzle_ids if o.puzzle_id else False,'actions':actions})
        clues=[]
        for cid in s.discovered_clue_ids:
            c=self.clues[cid]
            parts=[]
            if c.tokens: parts.append('源序：'+'、'.join(c.tokens))
            if c.indices: parts.append('按位置读取：'+'、'.join(map(str,c.indices)))
            if c.symbol_map: parts.append('对应：'+'；'.join(k+' → '+v for k,v in c.symbol_map.items()))
            clues.append({'clue_id':cid,'object_id':next(o.object_id for _,o in self.objects.values() if o.clue_id==cid),'title':'资料 '+cid,'text':'。'.join(parts)+'。'})
        statistics={'started_at':s.started_at,'finished_at':s.finished_at,'clues_found':len(clues),'clues_total':len(self.clues),'puzzles_solved':len(s.solved_puzzle_ids),'puzzles_total':len(self.puzzles),'hint_count':s.hint_count,'mistake_count':s.mistake_count,'hidden_found':0,'hidden_total':0,'current_hint_level':1}
        settlement=None
        if s.status=='won':
            settlement={**statistics,'elapsed_seconds':max(0,int((datetime.fromisoformat(s.finished_at.replace('Z','+00:00'))-datetime.fromisoformat(s.started_at.replace('Z','+00:00'))).total_seconds())),'rating':('S' if len(clues)>=.9*len(self.clues) and s.hint_count<=1 and s.mistake_count<=2 else 'A' if len(clues)>=.7*len(self.clues) and s.hint_count<=3 and s.mistake_count<=5 else 'B' if s.hint_count<=8 else 'C')}
        games['circuit']=next(iter(games['circuits']),None); games['sequence']=next(iter(games['sequences']),None)
        r=self.rooms.get(s.room_id)
        return {'schema_version':self.SCHEMA_VERSION,'level_version':self.LEVEL_VERSION,'mode':'generated','definition_hash':self.compiled.definition_hash,'session_id':sid,'room_id':s.room_id,'room':{'room_id':s.room_id,'name':r.name if r else '出口','description':r.description if r else '已离开。','background_id':r.background_id if r else 'neutral_control','background_art_id':r.background_id if r else 'neutral_control'},'inventory':[{'item_id':item,'name':next(o.name for _,o in self.objects.values() if o.item_id==item),'art_id':'key'} for item in s.inventory],'objects':objects,'clues':clues,'observed_object_ids':list(s.observed_object_ids),'exits':self.exits(s),'minigames':games,'statistics':statistics,'settlement':settlement,'status':s.status,'revision':s.revision,'generation':s.generation,'save':save,'flags':{}}
    def apply_action(self,original,tool,a):
        s=original.model_copy(deep=True); changed=False; observation=None; new=[]
        if s.status=='won': raise RuleError('GAME_FINISHED','本次已结束。')
        available=self.available(s); byid={o.object_id:o for o in available}
        if tool=='get_inventory': pass
        elif tool=='inspect':
            o=byid.get(a['object_id'])
            if not o: raise RuleError('NOT_VISIBLE','当前无法查看该物件。')
            observation=o.description
            if o.object_id not in s.observed_object_ids: s.observed_object_ids.append(o.object_id); changed=True
            if o.clue_id and o.clue_id not in s.discovered_clue_ids: s.discovered_clue_ids.append(o.clue_id); new.append(o.clue_id); changed=True
        elif tool=='take':
            o=next((o for o in available if o.item_id==a['item_id']),None)
            if not o: raise RuleError('NOT_VISIBLE','当前无法拿取该物品。')
            s.inventory.append(o.item_id); changed=True
        elif tool=='move':
            e=next((e for e in self.exits(s) if e['destination_id']==a['destination_id']),None)
            if not e or not e['unlocked']: raise RuleError('PRECONDITION_FAILED','通道尚未解锁。')
            s.room_id=e['destination_id']; changed=True
            if s.room_id=='EXIT': s.status='won'; s.finished_at=now()
        else:
            p=self.puzzles.get(a.get('target_id')); o=next((o for o in available if p and o.puzzle_id==p.puzzle_id),None)
            if not o or not p: raise RuleError('NOT_VISIBLE','当前无法操作该装置。')
            if o.object_id not in s.observed_object_ids or not set(p.prerequisite_ids)<=set(s.solved_puzzle_ids): raise RuleError('PRECONDITION_FAILED','请先查看装置并完成前置步骤。')
            if p.puzzle_id in s.solved_puzzle_ids: raise RuleError('PRECONDITION_FAILED','该装置已完成。')
            match={'use_item':'item','submit_code':'code','submit_sequence':'sequence','rotate_circuit':'circuit','submit_circuit':'circuit'}
            if match.get(tool)!=p.mechanism: raise RuleError('PRECONDITION_FAILED','操作方式不适用。')
            if tool=='use_item':
                if a['item_id'] not in s.inventory or a['item_id']!=p.required_item_id: raise RuleError('PRECONDITION_FAILED','物品不匹配。')
            elif tool in {'submit_code','submit_sequence'}:
                if not set(p.clue_ids)<=set(s.discovered_clue_ids): raise RuleError('PRECONDITION_FAILED','还没有收集齐必要资料。')
                value=a['code'] if tool=='submit_code' else a['device_ids']
                if value!=self.compiled.answers[p.puzzle_id]: raise RuleError('WRONG_CODE','装置没有接受这次输入，请核对资料。')
            elif tool=='rotate_circuit':
                i=circuit.MODULE_IDS.index(a['module_id']); s.circuit_rotations[p.puzzle_id][i]=(s.circuit_rotations[p.puzzle_id][i]+1)%4
            elif not circuit.connected(s.circuit_rotations[p.puzzle_id]): raise RuleError('WRONG_CODE','线路尚未连通。')
            if tool!='rotate_circuit': s.solved_puzzle_ids.append(p.puzzle_id)
            changed=True
        if changed: s.revision+=1
        self.validate_invariants(s)
        return s,{'changed':changed,'message':'操作完成。','observation':observation,'new_clue_ids':new,'consumed_item_ids':[]}
    def record_mistake(self,original,tool,a,error):
        if error.code!='WRONG_CODE': return original
        s=original.model_copy(deep=True); s.mistake_count+=1; s.revision+=1; return s

def solve(compiled):
    rules=GeneratedRules(compiled); start=rules.initial_state(); deadline=time.monotonic()+5
    # Circuit geometry is fixed. A derived reciprocal-connected witness is expanded.
    rotation=next((list(r) for r in itertools.product(range(4),repeat=9) if circuit.connected(r)),None)
    if rotation is None: raise ValueError('CIRCUIT_UNPROVEN')
    def key(s): return (s.room_id,tuple(sorted(s.inventory)),tuple(sorted(s.discovered_clue_ids)),tuple(sorted(s.observed_object_ids)),tuple(sorted(s.solved_puzzle_ids)))
    seen={key(start)}; queue=deque([(start,[])])
    while queue:
        if len(seen)>25000 or time.monotonic()>deadline: raise ValueError('PROOF_UNKNOWN')
        s,path=queue.popleft()
        if s.status=='won':
            replay=rules.initial_state()
            for action in path: replay,_=rules.apply_action(replay,action['tool'],action['arguments'])
            if replay.status!='won': raise ValueError('WITNESS_REPLAY')
            return path
        options=[]
        for o in rules.available(s):
            if o.object_id not in s.observed_object_ids: options.append([{'tool':'inspect','arguments':{'object_id':o.object_id}}])
            if o.kind=='item': options.append([{'tool':'take','arguments':{'item_id':o.item_id}}])
            if o.kind!='puzzle' or o.object_id not in s.observed_object_ids: continue
            p=rules.puzzles[o.puzzle_id]
            if p.puzzle_id in s.solved_puzzle_ids or not set(p.prerequisite_ids)<=set(s.solved_puzzle_ids): continue
            if p.mechanism=='item' and p.required_item_id in s.inventory: options.append([{'tool':'use_item','arguments':{'item_id':p.required_item_id,'target_id':p.puzzle_id}}])
            if p.mechanism in {'code','sequence'} and set(p.clue_ids)<=set(s.discovered_clue_ids): options.append([{'tool':'submit_code' if p.mechanism=='code' else 'submit_sequence','arguments':{'target_id':p.puzzle_id,('code' if p.mechanism=='code' else 'device_ids'):compiled.answers[p.puzzle_id]}}])
            if p.mechanism=='circuit':
                actions=[]
                for i,target in enumerate(rotation):
                    for _ in range((target-s.circuit_rotations[p.puzzle_id][i])%4): actions.append({'tool':'rotate_circuit','arguments':{'target_id':p.puzzle_id,'module_id':circuit.MODULE_IDS[i]}})
                actions.append({'tool':'submit_circuit','arguments':{'target_id':p.puzzle_id}}); options.append(actions)
        for e in rules.exits(s):
            if e['unlocked']: options.append([{'tool':'move','arguments':{'destination_id':e['destination_id']}}])
        for actions in options:
            nxt=s
            try:
                for action in actions: nxt,_=rules.apply_action(nxt,action['tool'],action['arguments'])
            except RuleError: continue
            k=key(nxt)
            if k not in seen: seen.add(k); queue.append((nxt,path+actions))
    raise ValueError('UNSOLVABLE')

def make_fixture(room_count=2,difficulty='normal'):
    """Private deterministic QA input. Never used as a production fallback."""
    count=min(6,room_count+{'easy':1,'normal':2,'hard':3}[difficulty]); rooms=[]; puzzles=[]; clues=[]
    for i in range(room_count): rooms.append({'room_id':f'G{i+1}','name':f'房间{i+1}','description':'一间安静的实验室。','background_id':['neutral_lab','neutral_archive','neutral_control'][i],'objects':[]})
    def add(room,obj): obj['slot']=len(rooms[room]['objects']); rooms[room]['objects'].append(obj)
    add(0,{'object_id':'obj_key','name':'钥匙','description':'一把可重复使用的钥匙。','art_id':'key','kind':'item','item_id':'shared_key'})
    # Two shared clues keep each room <=8 objects and require cross-room knowledge.
    clues=[{'clue_id':'fact_source','tokens':['1','2','3','4']},{'clue_id':'fact_order','indices':[3,1,4,2]}]
    add(0,{'object_id':'obj_source','name':'数据纸','description':'记录了批次源序。','art_id':'note','kind':'clue','clue_id':'fact_source'})
    add(0,{'object_id':'obj_order','name':'读取说明','description':'记录了读取位置。','art_id':'note','kind':'clue','clue_id':'fact_order'})
    for j in range(count):
        ri=min(room_count-1,j*room_count//count)
        # Codes exercise two-fact combinations; one item gate across rooms when possible.
        mech='code' if j<2 else ('item' if j==count-1 else ('sequence' if j%2 else 'circuit'))
        if difficulty=='easy' and count==2: mech='code' if j==0 else 'item'
        p={'puzzle_id':f'puzzle_{j}','room_id':rooms[ri]['room_id'],'mechanism':mech,'prerequisite_ids':[f'puzzle_{j-1}'] if j else []}
        if mech=='item': p['required_item_id']='shared_key'
        if mech in {'code','sequence'}: p.update(clue_ids=['fact_source','fact_order'],recipe='index')
        puzzles.append(p)
        add(ri,{'object_id':f'obj_puzzle_{j}','name':f'装置{j+1}','description':'根据资料完成操作。','art_id':'circuit' if mech=='circuit' else 'terminal','kind':'puzzle','puzzle_id':p['puzzle_id']})
    return {'title':'测试实验室','story':'这是离线验证用定义。','rooms':rooms,'clues':clues,'puzzles':puzzles}
