"""Deterministic inputs for the preregistered v5 admission comparison."""
import copy
import json
from backend.app.domain.generated import make_fixture

def case(identifier,category,raw,rooms=1,difficulty='easy',expected='reject',**extra):
    return {'case_id':identifier,'category':category,'raw':raw,'room_count':rooms,'difficulty':difficulty,'expected_full':expected,**extra}

def inputs():
    rows=[]
    for rooms in (1,2,3):
        for difficulty in ('easy','normal','hard'):
            rows.append(case(f'GOOD-{rooms}-{difficulty}','good',make_fixture(rooms,difficulty),rooms,difficulty,'accept'))
    def changed(identifier,category,modify,rooms=1,difficulty='easy'):
        raw=make_fixture(rooms,difficulty); modify(raw)
        rows.append(case(identifier,category,raw,rooms,difficulty))
    changed('REF-01','reference',lambda x:x['puzzles'][0].update(room_id='missing_room'))
    changed('REF-02','reference',lambda x:x['puzzles'][0].update(clue_ids=['missing_clue']))
    changed('REF-03','reference',lambda x:x['puzzles'][-1].update(required_item_id='missing_item'))
    changed('REF-04','reference',lambda x:x['puzzles'][0].update(prerequisite_ids=['missing_puzzle']))
    changed('REF-05','reference',lambda x:x['rooms'][0]['objects'][1].update(object_id=x['rooms'][0]['objects'][0]['object_id']))
    changed('DEP-01','dependency',lambda x:x['puzzles'][0].update(prerequisite_ids=['puzzle_0']))
    changed('DEP-02','dependency',lambda x:x['puzzles'][0].update(prerequisite_ids=['puzzle_1']))
    changed('DEP-03','dependency',lambda x:x['rooms'][0]['objects'][1].update(locked_by=['puzzle_0']))
    changed('DEP-04','dependency',lambda x:x['rooms'][0]['objects'][0].update(locked_by=['puzzle_1']))
    def future_clue(x):
        clue=x['rooms'][0]['objects'].pop(1)
        clue['slot']=len(x['rooms'][1]['objects']); x['rooms'][1]['objects'].append(clue)
        for i,obj in enumerate(x['rooms'][0]['objects']): obj['slot']=i
    changed('DEP-05','dependency',future_clue,2,'normal')
    changed('SEM-01','semantics',lambda x:x['clues'][1].update(indices=[8,1,4,2]))
    changed('SEM-02','semantics',lambda x:x['clues'][1].update(indices=[1,1,1,1]),3,'hard')
    def single(x):
        for puzzle in x['puzzles']:
            if puzzle['mechanism'] in ('code','sequence'): puzzle.update(clue_ids=['fact_source'],recipe='concat')
    changed('SEM-03','semantics',single,1,'normal')
    changed('SEM-04','semantics',single,3,'hard')
    changed('SEM-05','semantics',lambda x:x['puzzles'][0].update(recipe='symbol_map'))
    changed('LAY-01','layout',lambda x:x['rooms'][0]['objects'][1].update(slot=0))
    changed('LAY-02','layout',lambda x:x['rooms'][0]['objects'][0].update(slot=8))
    changed('LAY-03','layout',lambda x:x['rooms'][0]['objects'][0].update(art_id='external_image'))
    def too_many(x):
        for i in range(4): x['rooms'][0]['objects'].append({'object_id':f'extra_{i}','name':'多余物件','description':'超出布局预算。','slot':i,'art_id':'note','kind':'clue','clue_id':'fact_source'})
    changed('LAY-04','layout',too_many)
    changed('LAY-05','layout',lambda x:x['puzzles'][0].update(room_id=x['rooms'][1]['room_id']),2,'normal')
    huge=make_fixture(1,'easy'); huge['story']='x'*66000
    rows.append(case('LIMIT-01','limit',json.dumps(huge),expected='reject',limit='output_bytes'))
    deep={}; cursor=deep
    for _ in range(34): cursor['nested']={}; cursor=cursor['nested']
    raw=make_fixture(1,'easy'); raw['unexpected']=deep
    rows.append(case('LIMIT-02','limit',raw,expected='reject',limit='output_depth'))
    stress=make_fixture(3,'hard'); index=0
    for room in stress['rooms']:
        while len(room['objects'])<8:
            cid=f'optional_fact_{index}'
            stress['clues'].append({'clue_id':cid,'tokens':[str(index%9)]})
            room['objects'].append({'object_id':f'optional_object_{index}','name':'可选资料','description':'独立的观察资料。','slot':len(room['objects']),'art_id':'note','kind':'clue','clue_id':cid})
            index+=1
    rows.append(case('LIMIT-03','limit',stress,3,'hard','unknown',limit='planner_states',clock='disable_deadline_only'))
    rows.append(case('LIMIT-04','limit',make_fixture(1,'easy'),expected='unknown',limit='planner_seconds',clock='controlled_boundary'))
    rows.append(case('LIMIT-05','limit','{"title":',expected='reject',limit='truncated_output'))
    assert len(rows)==34 and sum(r['category']=='good' for r in rows)==9
    return rows
