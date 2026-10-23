"""Independent narrow regressions for the two observed V5 product findings.

Prepare only until Main freezes the candidate. Synthetic definitions/credentials;
never use player data or emit answer, cookie or CSRF values.
"""
import copy
import hashlib
import json
from types import SimpleNamespace
import time
import pytest
from .conftest import Actor,PASSWORD,BASE,assert_error,observed_output,make_fixture
from backend.app.domain import generated as g
from backend.app.storage import v5 as storage

def material_fixture(recipe='concat'):
    draft=make_fixture(1,'normal')
    facts={
        'concat':[{'clue_id':'material_alpha','tokens':['1','2']},{'clue_id':'material_beta','tokens':['3','4']}],
        'index':[{'clue_id':'material_alpha','tokens':['1','2'],'indices':[1]},{'clue_id':'material_beta','tokens':['3','4'],'indices':[2]}],
        'symbol_map':[{'clue_id':'material_alpha','tokens':['A','B'],'symbol_map':{'A':'1','B':'2'}},{'clue_id':'material_beta','tokens':['C','D'],'symbol_map':{'C':'3','D':'4'}}],
    }
    draft['clues']=facts[recipe]
    for obj in draft['rooms'][0]['objects']:
        if obj.get('clue_id'):
            obj['clue_id']='material_alpha' if obj['clue_id']=='fact_source' else 'material_beta'
            obj['name']='资料甲' if obj['clue_id']=='material_alpha' else '资料乙';obj['description']='一份公开材料。'
    for puzzle in draft['puzzles']:
        if puzzle['mechanism']=='code':puzzle.update(clue_ids=['material_alpha','material_beta'],recipe=recipe)
    return draft

def puzzle_description(rules,state):
    return next(o['description'] for o in rules.visible_state('synthetic',state)['objects'] if o['target_id']=='puzzle_0')

@pytest.mark.parametrize('recipe',['concat','index','symbol_map'])
def test_public_material_order_only_after_observed_puzzle_and_all_clues(recipe):
    outputs=[]
    for reverse in [False,True]:
        draft=material_fixture(recipe)
        if reverse:draft['puzzles'][0]['clue_ids'].reverse()
        compiled=g.compile_level(draft,1,'normal');rules=g.GeneratedRules(compiled);state=rules.initial_state()
        early=puzzle_description(rules,state)
        assert 'material_alpha' not in early and 'material_beta' not in early
        state,_=rules.apply_action(state,'inspect',{'object_id':'obj_puzzle_0'})
        state,_=rules.apply_action(state,'inspect',{'object_id':'obj_source'})
        partial=puzzle_description(rules,state)
        assert 'material_beta' not in partial
        state,_=rules.apply_action(state,'inspect',{'object_id':'obj_order'})
        description=puzzle_description(rules,state)
        expected=draft['puzzles'][0]['clue_ids']
        assert all(cid in description for cid in expected)
        assert description.index(expected[0])<description.index(expected[1])
        # Revealed clue IDs establish order, never an oracle answer field/value.
        for answer in compiled.answers.values():
            if isinstance(answer,str) and len(answer)>=3:assert answer not in description
        outputs.append({'reversed':reverse,'definition_hash':compiled.definition_hash,
                        'order_public_after_all_materials':True,'private_answer_not_emitted':True})
    observed_output('material-order-'+recipe+'.json',{'recipe':recipe,'observations':outputs,
        'scope':'Actual domain projection after legal observations; answer values omitted'})

def test_all_materials_without_puzzle_observation_do_not_publish_order():
    rules=g.GeneratedRules(g.compile_level(material_fixture(),1,'normal'));state=rules.initial_state()
    for object_id in ['obj_source','obj_order']:state,_=rules.apply_action(state,'inspect',{'object_id':object_id})
    description=puzzle_description(rules,state)
    assert 'material_alpha' not in description and 'material_beta' not in description

def test_conflicting_selected_maps_rejected_identical_and_unselected_allowed():
    draft=material_fixture('symbol_map');draft['clues'][1]['symbol_map']['A']='9'
    with pytest.raises(ValueError):g.compile_level(draft,1,'normal')
    same=copy.deepcopy(draft);same['clues'][1]['symbol_map']['A']='1'
    assert g.compile_level(same,1,'normal').witness
    unused=material_fixture('symbol_map');unused['clues'].append({'clue_id':'unused_map','symbol_map':{'A':'9'}})
    unused['rooms'][0]['objects'].append({'object_id':'obj_unused_map','name':'附加资料','description':'另一份材料。',
        'slot':7,'art_id':'note','kind':'clue','clue_id':'unused_map'})
    assert g.compile_level(unused,1,'normal').witness

def test_anonymous_context_stable_fixed_600_seconds_not_sliding(system,monkeypatch):
    app,_=system;clock=[time.time()];monkeypatch.setattr(storage,'time',SimpleNamespace(time=lambda:clock[0]))
    a=Actor(app);first=a.get('/auth/csrf').json()['data']['csrf_token'];nonce=a.client.cookies.get('campus_v5_csrf')
    with app.state.v5_database.transaction() as c:created=c.execute('SELECT created_at FROM anonymous_csrf WHERE nonce_hash=?',(storage.digest(nonce),)).fetchone()[0]
    clock[0]+=599
    second=a.get('/auth/csrf').json()['data']['csrf_token']
    assert second==first and a.client.cookies.get('campus_v5_csrf')==nonce
    with app.state.v5_database.transaction() as c:assert c.execute('SELECT created_at FROM anonymous_csrf WHERE nonce_hash=?',(storage.digest(nonce),)).fetchone()[0]==created
    clock[0]+=1
    expired=a.get('/auth/csrf').json()['data']['csrf_token']
    assert expired!=first and a.client.cookies.get('campus_v5_csrf')!=nonce
    a.headers['X-CSRF-Token']=first
    assert_error(a.post('/auth/register',{'username':'qa_expired_form','password':PASSWORD}),403,'CSRF_FAILED')

def test_legacy_random_anonymous_context_rotates_safely(system):
    app,_=system;a=Actor(app);nonce='synthetic-old-random-nonce';csrf='synthetic-old-random-csrf'
    with app.state.v5_database.transaction() as c:c.execute('INSERT INTO anonymous_csrf VALUES(?,?,?)',(storage.digest(nonce),storage.digest(csrf),time.time()))
    a.client.cookies.set('campus_v5_csrf',nonce,domain='127.0.0.1',path='/api/v2')
    response=a.get('/auth/csrf');fresh=response.json()['data']['csrf_token']
    assert fresh!=csrf and a.client.cookies.get('campus_v5_csrf')!=nonce
    assert a.get('/auth/csrf').json()['data']['csrf_token']==fresh

def test_logout_seeds_shared_anonymous_context_two_tabs_old_form_valid(system):
    app,_=system;a=Actor(app).authenticate('qa_logout_tabs')
    assert a.post('/auth/logout').status_code==200
    nonce=a.client.cookies.get('campus_v5_csrf');assert nonce
    first=a.get('/auth/csrf').json()['data']['csrf_token'];second=a.get('/auth/csrf').json()['data']['csrf_token']
    assert first==second and a.client.cookies.get('campus_v5_csrf')==nonce
    a.headers['X-CSRF-Token']=first
    assert_error(a.post('/auth/register',{'username':'qa_other_tab','password':PASSWORD},headers={'Origin':'null'}),403,'INVALID_ORIGIN')
    assert_error(a.post('/auth/register',{'username':'qa_other_tab','password':PASSWORD},headers={'X-CSRF-Token':'wrong'}),403,'CSRF_FAILED')
    result=a.post('/auth/register',{'username':'qa_other_tab','password':PASSWORD});assert result.status_code==201,result.text
    observed_output('anonymous-tabs-fixed.json',{'seeded_on_logout':bool(nonce),'two_gets_same_context':first==second,
        'earlier_form_register_status':result.status_code,'wrong_origin_rejected':True,'wrong_csrf_rejected':True,
        'secret_values_recorded':False})
