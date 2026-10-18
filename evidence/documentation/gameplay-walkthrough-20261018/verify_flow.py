"""Verify a documented route in domain memory only; no app, DB, provider or UI."""
from pathlib import Path
from datetime import datetime, timezone
from itertools import product
import hashlib
import json
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from backend.app.domain import graybox_rules as rules, circuit
from backend.app.domain.mini_rules import SOURCE_SYMBOLS, READ_INDICES, SYMBOL_DEVICES
from backend.app.domain.puzzle_rules import CABINET_CODE, LOGIN_USERNAME, LOGIN_PASSWORD
state=rules.initial_state();steps=[]
def act(tool,**arguments):
    global state
    before=state
    state,result=rules.apply_action(state,tool,arguments)
    rules.validate_invariants(state)
    steps.append({'step':len(steps)+1,'room_before':before.room_id,'tool':tool,'arguments':arguments,'room_after':state.room_id,'device_states':state.device_states.model_dump(),'puzzle_states':state.puzzle_states.model_dump(),'new_clue_ids':result['new_clue_ids'],'message':result['message']})
def inspect(*objects):
    for obj in objects:act('inspect',object_id=obj)
def interact(target):act('interact',target_id=target)
inspect('r1_clock','r1_record','r1_plaque','r1_microscope','sample_slide')
act('take',item_id='sample_slide');act('use_item',item_id='sample_slide',target_id='r1_microscope');inspect('r1_microscope','r1_cabinet')
act('submit_code',target_id='r1_cabinet',code=CABINET_CODE);interact('r1_cabinet');inspect('r1_symbols','r1_fuse');act('take',item_id='fuse');inspect('r1_photo','r1_door');interact('r1_door');act('move',destination_id='R2')
inspect('r2_maintenance','r2_powerbox');interact('r2_powerbox');interact('r2_powerbox');act('use_item',item_id='fuse',target_id='r2_powerbox')
options=[range(2) if shape=='I' else range(4) for shape in circuit.SHAPES]
rotations=next(tuple(values) for values in product(*options) if circuit.connected(values))
assert rotations==(1,1,2,2,0,0,0,1,3),rotations
alternative=list(rotations);alternative[4]=1
assert circuit.connected(alternative),'Center is not a required segment for this valid route.'
for module,target_rotation in zip(circuit.MODULE_IDS,rotations):
    current=state.circuit_rotations[circuit.MODULE_IDS.index(module)]
    for _ in range((target_rotation-current)%4):act('rotate_circuit',target_id='r2_powerbox',module_id=module)
act('submit_circuit',target_id='r2_powerbox');assert not state.flags['power_on'];interact('r2_powerbox');inspect('r2_service_label','r2_monitor');interact('r2_monitor');interact('r2_monitor')
act('submit_login',target_id='r2_monitor',username=LOGIN_USERNAME,password=LOGIN_PASSWORD);interact('r2_monitor');inspect('research_strip','access_card');act('take',item_id='research_strip');act('take',item_id='access_card');inspect('r2_door');interact('r2_door');act('move',destination_id='R3')
inspect('r3_legend','r3_panel');act('use_item',item_id='research_strip',target_id='r3_panel')
early=rules.visible_state('offline-documentation',state)
assert early['minigames']['sequence'] is not None and state.device_states.exit=='LOCKED'
assert not any(a['tool']=='submit_sequence' for o in early['objects'] if o['object_id']=='r3_panel' for a in o['actions'])
inspect('exit_door');act('use_item',item_id='access_card',target_id='exit_door');interact('exit_door')
answer=[SYMBOL_DEVICES[SOURCE_SYMBOLS[index-1]] for index in READ_INDICES]
assert answer==['ventilation','cooling','lighting','safety']
act('submit_sequence',target_id='r3_panel',device_ids=answer);assert state.flags['check_done'] and state.device_states.exit=='FINAL_CHECK'
interact('exit_door');interact('exit_door');assert state.status=='playing';act('move',destination_id='EXIT');assert state.status=='won'
projection=rules.visible_state('offline-documentation',state)
assert len(projection['clues'])==10 and projection['statistics']['hidden_found']==2
paths=['backend/app/domain/puzzle_rules.py','backend/app/domain/mini_rules.py','backend/app/domain/graybox_rules.py','backend/app/domain/circuit.py','backend/app/domain/device_flow.py','frontend/src/components/Room3.tsx','backend/app/ai/hints.py']
sha=lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
result={'recorded_at':datetime.now(timezone.utc).isoformat(),'client_date':'2026-10-18','baseline_head':subprocess.check_output(['git','-c','safe.directory=D:/深度能力','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'command':[sys.executable,'-B','-X','utf8','evidence/documentation/gameplay-walkthrough-20261018/verify_flow.py'],'exit_code':0,'scope':'Pure domain-memory walkthrough verification. Not an HTTP/browser/save/AI quality test.','level_version':rules.LEVEL_VERSION,'schema_version':rules.SCHEMA_VERSION,'source_sha256':{p:sha(p) for p in paths},'route_steps':steps,'circuit_example':{'clockwise_clicks_from_initial':dict(zip(circuit.MODULE_IDS,rotations)),'port_directions':{module:''.join(circuit.SIDES[side] for side in sorted(circuit.ports(index,rotations[index]))) for index,module in enumerate(circuit.MODULE_IDS)},'path':['c00','c01','c02','c12','c22','c21','c20','c10'],'center_not_required_and_alternative_valid':True},'answers':{'cabinet':CABINET_CODE,'login_username':LOGIN_USERNAME,'login_password':LOGIN_PASSWORD,'final_sequence':answer},'final_status':state.status,'discovered_clue_ids':[c['clue_id'] for c in projection['clues']],'hidden_found':projection['statistics']['hidden_found'],'paid_calls':0,'limitations':['No product changes, provider calls, database access, HTTP or browser operation.','One valid route including two optional story clues, not a unique or minimum-length route.','Current UI observations and draft inputs are explained from source; this verification only executes domain actions.','Future AI suggestions in the document are proposals, not implemented functionality.']}
(ROOT/'evidence/documentation/gameplay-walkthrough-20261018/verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'exit_code':0,'domain_actions':len(steps),'status':state.status,'clues':len(projection['clues']),'hidden':projection['statistics']['hidden_found'],'rotations':rotations,'sequence':answer,'no_DB_no_API_no_paid':True},ensure_ascii=False))
