"""P02/N01: all nine finite definitions, real actions, strict admission."""
import copy
import json
import pytest
from pydantic import ValidationError
from backend.app.domain import generated as g, circuit
from backend.app.domain.models import RuleError

@pytest.mark.parametrize('rooms',[1,2,3])
@pytest.mark.parametrize('difficulty',['easy','normal','hard'])
def test_nine_definitions_actual_domain_witness(rooms,difficulty):
    compiled=g.compile_level(g.make_fixture(rooms,difficulty),rooms,difficulty)
    rules=g.GeneratedRules(compiled); state=rules.initial_state()
    assert len(compiled.draft.puzzles)==min(6,rooms+{'easy':1,'normal':2,'hard':3}[difficulty])
    for action in compiled.witness:
        if action['tool'] in {'submit_code','submit_sequence'}:
            p=rules.puzzles[action['arguments']['target_id']]
            assert set(p.clue_ids)<=set(state.discovered_clue_ids)
        state,_=rules.apply_action(state,action['tool'],action['arguments'])
        rules.validate_invariants(state)
    assert state.status=='won' and compiled.witness[-1]=={'tool':'move','arguments':{'destination_id':'EXIT'}}
    assert len(state.solved_puzzle_ids)==len(compiled.draft.puzzles)
    assert not {'answers','draft','witness','validation_report'} & rules.visible_state('qa',state).keys()
    draft=compiled.draft; draft.title='mutated copy'
    assert compiled.draft.title!='mutated copy'

@pytest.mark.parametrize('raw', ['{"x":1,"x":2}', '{"x":NaN}', '{', '[]', '{"x":"https://example.invalid"}', '{"x":"<script>"}'])
def test_strict_json_rejects_untrusted_output(raw):
    with pytest.raises((ValueError,ValidationError,TypeError)): g.compile_level(raw,1,'easy')

def test_depth_size_unknown_and_unsafe_fields():
    raw=[]
    for _ in range(35): raw=[raw]
    with pytest.raises(ValueError,match='OUTPUT_DEPTH'): g.strict_json(raw)
    with pytest.raises(ValueError,match='OUTPUT_SIZE'): g.strict_json('"'+'x'*65536+'"')
    draft=g.make_fixture(1,'easy'); draft['answer']='private'
    with pytest.raises(ValidationError): g.compile_level(draft,1,'easy')
    for text in ['file:///tmp/x','C:\\tmp\\x','javascript:alert(1)','__import__("os")']:
        draft=g.make_fixture(1,'easy'); draft['story']=text
        with pytest.raises(ValueError,match='UNSAFE_TEXT'): g.compile_level(draft,1,'easy')

@pytest.mark.parametrize('mutation,code',[
    ('reference','UNKNOWN_REFERENCE'),('slot','DUPLICATE_SLOT'),('selflock','UNSOLVABLE'),
    ('cycle','DEPENDENCY_CYCLE'),('facts','INSUFFICIENT_FACTS'),('clue_missing','CLUE_REFERENCE'),
    ('duplicate','DUPLICATE_ID'),('answer','ANSWER_IN_PROSE'),('depth','DEPENDENCY_DEPTH'),
])
def test_admission_invalid_semantics(mutation,code):
    draft=g.make_fixture(2,'hard')
    if mutation=='reference': draft['puzzles'][0]['clue_ids']=['missing']
    elif mutation=='slot': draft['rooms'][0]['objects'][1]['slot']=0
    elif mutation=='selflock': draft['rooms'][0]['objects'][1]['locked_by']=['puzzle_0']
    elif mutation=='cycle': draft['puzzles'][0]['prerequisite_ids']=['puzzle_1']
    elif mutation=='facts': draft['clues'][1]['indices']=[8]
    elif mutation=='clue_missing': draft['rooms'][0]['objects']=[o for o in draft['rooms'][0]['objects'] if o.get('clue_id')!='fact_order']
    elif mutation=='duplicate': draft['rooms'][0]['objects'][0]['object_id']='G1'
    elif mutation=='answer': draft['story']='密码为3142'
    elif mutation=='depth':
        for p in draft['puzzles']: p['prerequisite_ids']=[]
    with pytest.raises(ValueError,match=code): g.compile_level(draft,2,'hard')

def test_proof_timeout_is_unknown_not_unsolvable(monkeypatch):
    ticks=iter([0,6])
    monkeypatch.setattr(g.time,'monotonic',lambda:next(ticks,6))
    with pytest.raises(ValueError,match='PROOF_UNKNOWN'): g.compile_level(g.make_fixture(1,'easy'),1,'easy')

@pytest.mark.parametrize('recipe',['concat','index','symbol_map'])
def test_sequence_derivation_all_recipes_real_submission(recipe):
    draft=g.make_fixture(3,'hard'); p=next(p for p in draft['puzzles'] if p['mechanism']=='sequence')
    p['recipe']=recipe
    if recipe=='concat': p['clue_ids']=['fact_source']
    elif recipe=='symbol_map':
        draft['clues'].append({'clue_id':'fact_map','symbol_map':{'1':'cool','2':'light','3':'air','4':'safe'}})
        draft['rooms'][0]['objects'].append({'object_id':'obj_map','name':'对应表','description':'设备对应关系。','slot':7,'art_id':'note','kind':'clue','clue_id':'fact_map'})
        p['clue_ids']=['fact_source','fact_map']
    compiled=g.compile_level(draft,3,'hard'); rules=g.GeneratedRules(compiled); state=rules.initial_state()
    for action in compiled.witness: state,_=rules.apply_action(state,action['tool'],action['arguments'])
    assert state.status=='won'

def test_circuit_reciprocal_and_material_gates():
    assert not circuit.connected([0]*9)
    compiled=g.compile_level(g.make_fixture(3,'hard'),3,'hard'); rules=g.GeneratedRules(compiled); state=rules.initial_state()
    # A derived correct answer must not bypass material/observation prerequisites.
    with pytest.raises(RuleError,match=''):
        rules.apply_action(state,'submit_code',{'target_id':'puzzle_0','code':compiled.answers['puzzle_0']})
    state,_=rules.apply_action(state,'inspect',{'object_id':'obj_puzzle_0'})
    with pytest.raises(RuleError) as error: rules.apply_action(state,'submit_code',{'target_id':'puzzle_0','code':compiled.answers['puzzle_0']})
    assert error.value.code=='PRECONDITION_FAILED'
    rotations=[a for a in compiled.witness if a['tool']=='rotate_circuit']
    assert rotations
