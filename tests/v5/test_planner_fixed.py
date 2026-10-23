"""Affected planner-only checks over the original frozen E1 inputs.

No nine HTTP routes or complete E1 experiment is repeated here. The state-cap
probe disables only the deadline in memory and reports actual wall time.
"""
import hashlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import pytest
from backend.app.domain import generated as domain
from .conftest import observed_output

INPUTS=Path(__file__).resolve().parents[2]/'evidence/upgrade/v5.0/experiments-owner/run1/inputs.json'
INPUTS_SHA256='7609c5b66fcaaf662c04a5783d3ffac6e3d00c89cda0ed7ba1a804e1fe111cef'

def frozen_rows():
    raw=INPUTS.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==INPUTS_SHA256
    return json.loads(raw)

def test_affected_nine_and_twenty_original_inputs():
    rows=frozen_rows();admissions=[];rejections=[]
    selected=[row for row in rows if row['category']!='limit']
    assert len(selected)==29
    for row in selected:
        encoded=json.dumps(row['raw'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
        result={'case_id':row['case_id'],'input_sha256':hashlib.sha256(encoded).hexdigest()}
        try:
            compiled=domain.compile_level(row['raw'],row['room_count'],row['difficulty'])
            rules=domain.GeneratedRules(compiled);state=rules.initial_state()
            for action in compiled.witness: state,_=rules.apply_action(state,action['tool'],action['arguments'])
            accepted=True
            result.update(room_count=row['room_count'],difficulty=row['difficulty'],admitted=True,
                replay_won=state.status=='won',steps=len(compiled.witness),definition_hash=compiled.definition_hash)
        except (ValueError,TypeError,KeyError,RecursionError) as error:
            accepted=False
            result.update(category='semantic' if row['category']=='semantics' else row['category'],rejected=True,
                error_code='PROOF_UNKNOWN' if str(error)=='PROOF_UNKNOWN' else 'ADMISSION_REJECTED')
        if row['category']=='good':admissions.append(result)
        else:rejections.append(result)
        observed_output('C1-admission-affected.json',{'frozen_input_file_sha256':hashlib.sha256(INPUTS.read_bytes()).hexdigest(),
            'scope':'Only nine domain admissions/real witness replays and twenty frozen bad definitions; no HTTP or full E1 repeat',
            'admissions':admissions,'rejections':rejections})
        assert accepted==(row['expected_full']=='accept'),row['case_id']
        if accepted:assert result['replay_won'] and result['steps']>0
    assert len(admissions)==9 and len(rejections)==20

def test_exact_25000_registered_states_remains_unknown():
    row=next(r for r in frozen_rows() if r['case_id']=='LIMIT-03')
    original_time=domain.time;original_trace=sys.gettrace();observed={};started=time.perf_counter()
    def trace(frame,event,arg):
        if event=='call':
            if frame.f_code.co_name!='solve' or frame.f_globals.get('__name__')!='backend.app.domain.generated':return None
            frame.f_trace_lines=False
        if event=='exception' and frame.f_code.co_name=='solve' and str(arg[1])=='PROOF_UNKNOWN':
            observed['registered_abstract_states']=len(frame.f_locals.get('seen',()))
        return trace
    try:
        domain.time=SimpleNamespace(monotonic=lambda:0.0)
        sys.settrace(trace)
        with pytest.raises(ValueError,match='^PROOF_UNKNOWN$'):
            domain.compile_level(row['raw'],row['room_count'],row['difficulty'])
    finally:
        sys.settrace(original_trace);domain.time=original_time
        observed.update(case_id='LIMIT-03',controlled_clock='deadline_disabled_only',
            real_elapsed_seconds=time.perf_counter()-started,
            limit=25000,classification='PROOF_UNKNOWN',playable=False,
            limitations=['Controlled clock reaches the actual count guard; elapsed time is not a five-second production timing measurement.'])
        observed_output('state-cap-affected.json',observed)
    assert observed.get('registered_abstract_states')==25000

def test_controlled_deadline_remains_unknown():
    row=next(r for r in frozen_rows() if r['case_id']=='LIMIT-04')
    original_time=domain.time;started=time.perf_counter();ticks=iter([0.0,6.0])
    try:
        domain.time=SimpleNamespace(monotonic=lambda:next(ticks,6.0))
        with pytest.raises(ValueError,match='^PROOF_UNKNOWN$'):
            domain.compile_level(row['raw'],row['room_count'],row['difficulty'])
    finally:
        domain.time=original_time
        observed_output('deadline-affected.json',{'case_id':'LIMIT-04','classification':'PROOF_UNKNOWN',
            'controlled_clock':'first 0 then 6 seconds crosses production deadline branch',
            'real_elapsed_seconds':time.perf_counter()-started,'playable':False,
            'limitations':['Controlled-clock branch verification, not five seconds of measured CPU or a full E1 repeat.']})
