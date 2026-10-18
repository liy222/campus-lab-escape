"""Read-only default-hint audit over real rule snapshots; no DB/API/provider calls."""
from pathlib import Path
import asyncio,copy,hashlib,json,subprocess,sys
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from backend.app.domain import graybox_rules as rules
from backend.app.ai.hints import available_topics,bounded_render,TEMPLATES,NO_HINT
from backend.app.ai.runtime import Runtime
from backend.app.ai.mock import DeterministicMockProvider
from backend.app.ai.types import Snapshot,TurnStart
trace=json.loads((ROOT/'evidence/documentation/gameplay-walkthrough-20261018/verification.json').read_text(encoding='utf-8'))['route_steps']
state=rules.initial_state();snapshots=[]
def save(label):
    visible=rules.visible_state('default-hint-audit',state)
    topics=available_topics(visible)
    for option in topics:
        assert set(option['clue_refs']) <= {c['clue_id'] for c in visible['clues']}
    snapshots.append({'label':label,'state':copy.deepcopy(visible),'topics':topics})
save('initial')
for step in trace:
    state,_=rules.apply_action(state,step['tool'],step['arguments'])
    save(str(step['step'])+':'+step['tool']+':'+str(step['arguments'].get('object_id',step['arguments'].get('target_id',step['arguments'].get('destination_id','')))))
assert state.status=='won'
covered=set();rendered={}
for entry in snapshots:
    v=entry['state']
    for topic in entry['topics']:
        covered.add(topic['topic']);rendered.setdefault(topic['topic'],{})
        for level in (1,2,3):
            projection=copy.deepcopy(v);projection['statistics']['current_hint_level']=level
            answer,refs=bounded_render(projection,topic['clue_refs'],topic['topic'])
            assert answer==TEMPLATES[topic['topic']][level-1]
            assert not any(text in answer for text in ('4217','LAB-42','2117','4792','231','通风 → 冷却 → 照明 → 安全'))
            rendered[topic['topic']][str(level)]={'answer':answer,'clue_refs':refs}
assert covered==set(TEMPLATES)
all_r1=next(e for e in snapshots if e['state']['room']['room_id']=='R1' and [t['topic'] for t in e['topics']]==['sample_time','sample_mark'])
all_login=next(e for e in snapshots if [t['topic'] for t in e['topics']]==['login_identity','login_time'])
class Callback:
    def __init__(self,state):self.state=state
    async def snapshot(self,expected):return Snapshot(copy.deepcopy(self.state))
    async def read_tool(self,*a,**k):raise AssertionError('No tool read allowed in this audit')
    async def precheck_proposal(self,*a,**k):raise AssertionError('No proposal allowed in this audit')
async def ask(v,message,history=()):
    runtime=Runtime(DeterministicMockProvider())
    result=await runtime.run(TurnStart('offline-audit',message,copy.deepcopy(v),history),Callback(v))
    assert result.data['usage']['model_calls']==0 and result.data['usage']['read_tool_calls']==0
    return result.data
async def probes():
    records=[]
    for name,entry,q1,q2 in [('r1_both_topics',all_r1,'只问样本编号这一部分','只问时间这一部分'),('login_both_topics',all_login,'我忘了密码格式','我忘了用户名格式')]:
        a=await ask(entry['state'],q1);b=await ask(entry['state'],q2,({'kind':'ai_turn','answer':'已经讨论过第一主题'},))
        assert a['answer']==b['answer']==TEMPLATES[entry['topics'][0]['topic']][0]
        records.append({'probe':name,'topics':[t['topic'] for t in entry['topics']],'question_and_history_changed_but_answer_same':True,'selected':entry['topics'][0]['topic'],'answer':a['answer'],'runtime_model_calls':0})
    labels=[('cabinet_code_accepted',lambda s:s['device_states']['cabinet']=='CODE_ACCEPTED'),('cabinet_open',lambda s:s['device_states']['cabinet']=='OPEN'),('powerbox_missing_fuse',lambda s:s['device_states']['powerbox']=='MISSING_FUSE'),('circuit_ready_not_powered',lambda s:s['room']['room_id']=='R2' and s['device_states']['powerbox']=='CIRCUIT_READY'),('computer_booting',lambda s:s['device_states']['computer']=='BOOTING'),('computer_unlocked_not_read',lambda s:s['device_states']['computer']=='UNLOCKED'),('tray_data_read',lambda s:s['room']['room_id']=='R2' and s['device_states']['computer']=='DATA_READ'),('paper_inserted_before_card',lambda s:s['room']['room_id']=='R3' and s['puzzle_states']['panel']=='STRIP_INSERTED' and s['device_states']['exit']=='LOCKED'),('card_accepted_not_started',lambda s:s['device_states']['exit']=='CARD_ACCEPTED'),('check_passed_door_locked',lambda s:s['progress']['check_done'] and s['device_states']['exit']=='FINAL_CHECK'),('exit_unlocked',lambda s:s['device_states']['exit']=='UNLOCKED'),('exit_open_not_left',lambda s:s['device_states']['exit']=='OPEN')]
    for name,predicate in labels:
        e=next(e for e in snapshots if e['state']['status']=='playing' and predicate(e['state']))
        assert not e['topics'],name
        result=await ask(e['state'],'下一步应该关注什么？');assert result['answer']==NO_HINT
        records.append({'probe':name,'snapshot':e['label'],'clues_known':len(e['state']['clues']),'topics':[],'answer':result['answer'],'runtime_model_calls':0})
    return records
results=asyncio.run(probes())
paths=['backend/app/ai/hints.py','backend/app/ai/runtime.py','backend/app/storage/ai.py','frontend/src/Assistant.tsx','backend/app/domain/graybox_rules.py','backend/app/domain/mini_rules.py','backend/app/domain/puzzle_rules.py','docs/gameplay-walkthrough.md']
report={'recorded_at':datetime.now(timezone.utc).isoformat(),'client_date':'2026-10-18','command':[sys.executable,'-B','-X','utf8','evidence/review/default-hints-20261018/probe.py'],'exit_code':0,'baseline_head':subprocess.check_output(['git','-c','safe.directory=D:/深度能力','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},'actual_domain_snapshots':len(snapshots),'actual_existing_topics_rendered':len(rendered),'actual_level_variants_rendered':sum(len(x) for x in rendered.values()),'template_rendering':rendered,'runtime_probes':results,'actual_model_calls':0,'DB_access':False,'HTTP_requests':False,'product_changes':0,'scope':'In-memory actual domain states, topic eligibility and mock Runtime only; text correctness also requires source/manual comparison.','counting_conclusion_source_only':{'NO_HINT':'storage/ai.py156-166 early return, hint_count unchanged and no provider call','valid_template':'storage/ai.py378-387 validated rendered hint adds1, including repeated same-content new requests'},'limitations':['No Store/API/browser/counting integration test was executed; those claims are source inspection and existing-test review only.','Question/history comparison holds state fixed and does not test frontend rendering or simulated Store counter updates.','Provider branch not called; no real or fake model-quality acceptance.','Findings describe current fixed-template design scope and gaps, not a claim every old safety requirement was violated.']}
(ROOT/'evidence/review/default-hints-20261018/probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'exit_code':0,'actual_snapshots':len(snapshots),'topics':len(rendered),'level_variants':18,'runtime_probes':len(results),'model_calls':0,'product_changes':0},ensure_ascii=False))
