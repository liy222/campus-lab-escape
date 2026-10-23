"""P06/E2: relevant shared regressions and isolated classic compatibility."""
import hashlib
import json
import os
import sqlite3
import unittest
import pytest
from .conftest import Actor, rid, make_fixture, compile_level, assert_error
from backend.app.storage.v5 import V5Database
from backend.app.api.v5 import GenerationRequest
from backend.app.main import create_app, create_v5_app

def test_non_v5_database_refused_before_any_mutation(tmp_path):
    path=tmp_path/'existing-classic.sqlite'
    with sqlite3.connect(path) as c: c.execute('CREATE TABLE original(value TEXT)'); c.execute("INSERT INTO original VALUES('preserve')")
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match='Refusing existing non-v5'): V5Database(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before

def test_account_classic_uses_v34_and_snapshot_rules(actor,system):
    state=actor.session(); sid=state['session_id']
    assert state['level_version']=='3.4.0' and state['room']['room_id']=='R1'
    assert state['mode']=='classic' and state['schema_version']=='1.4.0'
    response=actor.action(state,'inspect',{'object_id':'r1_clock'}); assert response.status_code==200,response.text
    state=response.json()['data']['visible_state']
    assert any('21:17' in c['text'] for c in state['clues'])
    save=actor.post(f'/sessions/{sid}/saves',actor.versioned(state,name='classic'))
    assert save.status_code==201
    slot=save.json()['data']['slot']; assert slot['level_version']=='3.4.0'
    assert system[1].calls==[]

def test_policy09_definition_and_archive_reopen_without_recompile_policy_change(actor,system):
    app,generator=system; db=app.state.v5_database
    draft=make_fixture(1,'normal')
    for p in draft['puzzles']:
        if p['mechanism']=='code': p.update(clue_ids=['fact_source'],recipe='concat')
    with pytest.raises(ValueError,match='COMBINATION_COUNT'): compile_level(draft,1,'normal')
    compiled=compile_level(draft,1,'normal',policy_version='0.9.0')
    uid=actor.auth['user']['user_id']; status,job,_=db.reserve_job(uid,GenerationRequest(request_id=rid(),theme='private pre-release simulation',room_count=1,difficulty='normal'))
    assert status==202; db.job_phase(job['job_id'],'validating'); db.commit_level(job['job_id'],compiled)
    lid=db.jobs(uid,job['job_id'])['level_id']; state=actor.session('generated',lid); sid=state['session_id']
    save=actor.post(f'/sessions/{sid}/saves',actor.versioned(state,name='private-policy09')); assert save.status_code==201
    save_id=save.json()['data']['slot']['save_id']
    with db.transaction() as c: original=c.execute('SELECT definition_json FROM generated_levels WHERE level_id=?',(lid,)).fetchone()[0]
    reopened=create_v5_app(db.path,generation_service=generator); other=Actor(reopened).authenticate('qa_alpha',False)
    result=other.post(f'/sessions/{sid}/saves/{save_id}/restore',other.versioned(other.state(sid)))
    assert result.status_code==200,result.text
    assert result.json()['data']['visible_state']['definition_hash']==compiled.definition_hash
    with reopened.state.v5_database.transaction() as c: assert c.execute('SELECT definition_json FROM generated_levels WHERE level_id=?',(lid,)).fetchone()[0]==original
    assert generator.calls==[]

@pytest.mark.parametrize('name',[
    'tests.api.test_closeup_panel.CloseupPanelProjection.test_early_public_devices_keep_final_check_guard_then_finish',
    'tests.api.test_closeup_panel.CloseupPanelV33Compatibility.test_v33_keeps_sequence_hidden_until_final_check',
    'tests.api.test_multiple_saves.MultipleSavesAcceptance.test_append_immutable_three_moments_restore_stats_reset_and_reopen',
    'tests.api.test_multiple_saves.MultipleSavesAcceptance.test_owned_corrupt_crossversion_snapshot_rejection_preserves_live_and_other_archives',
    'tests.api.test_hint_flow.HintFlowHTTP.test_http_route_to_r3_and_no_topic_fallback_count_zero_after_exit',
])
def test_selected_unchanged_classic_regression(name):
    """Run only five relevant historic methods; no legacy full collection."""
    environment={key:os.environ.get(key) for key in ['SQLITE_PATH','GAMEPLAY_VERSION','AI_PROVIDER']}
    try:
        suite=unittest.defaultTestLoader.loadTestsFromName(name)
        result=unittest.TestResult(); suite.run(result)
        assert result.testsRun==1
        assert not result.errors and not result.failures, result.errors+result.failures
    finally:
        for key,value in environment.items():
            if value is None: os.environ.pop(key,None)
            else: os.environ[key]=value
