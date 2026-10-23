"""Independent offline V5 evaluator probes. All evidence/judgements synthetic.

This file is intentionally separate from product suites: registration/pin changes
need a new evaluator epoch, never another product-suite claim. No CLI output is
written into Owner paths. No target code, paid transport or ledger is invoked.
"""
import asyncio
import copy
import json
from pathlib import Path
import pytest
from evaluation import v5
from evaluation.common import EvaluationError
from evaluation.engine import Evaluator
from evaluation.provider import MockProvider
from evaluation.reader import safe_read

@pytest.fixture
def isolated_evaluator(tmp_path):
    for name in ['source','support','failure','injection','na','self-claim']:
        relative=v5.ROOT+'fixtures/'+name+'.json'
        target=tmp_path/relative;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(safe_read(v5.PROJECT_ROOT,relative))
    return v5._fixture_tools(tmp_path)

def suggestion(claim,**changes):
    value={'claim_id':claim['claim_id'],'release_id':claim['release_id'],'status':'PASS',
           'evidence_refs':copy.deepcopy(claim['evidence_refs']),
           'reason':'Independent QA synthetic scripted judgement only. No real interpretation.',
           'missing_check':[]}
    value.update(changes);return value

@pytest.mark.parametrize('index,expected',[(0,'PASS'),(1,'FAIL'),(2,'INSUFFICIENT_EVIDENCE'),(3,'FAIL'),(4,'INSUFFICIENT_EVIDENCE'),(5,'NOT_APPLICABLE'),(6,'INSUFFICIENT_EVIDENCE')])
def test_independent_k1_k6_four_states_no_false_pass(isolated_evaluator,index,expected):
    files,tools,context=isolated_evaluator; claim=context.claims[index]
    script=suggestion(claim)
    if index==4: script['evidence_refs']=[{'evidence_id':'synthetic:unread','snippet':'summary'}]
    provider=MockProvider([script])
    result,audit=asyncio.run(Evaluator(tools,files,provider).evaluate(claim,tools.contract['contract_id'],v5.VERSION))
    assert result['status']==expected
    assert result['execution_scope']['real_paid_judgement'] is False
    assert result['execution_scope']['synthetic_judgement'] is True
    assert result['human_signoff'] is None and result['human_signoff_status']=='pending'
    if index in {1,3}:
        assert audit['raw_suggestion']['status']=='PASS' and result['status']=='FAIL'
        assert provider.calls==1
    if index in {2,5,6}: assert provider.calls==0

def test_deterministic_only_never_passes_supported_fixture(isolated_evaluator):
    files,tools,context=isolated_evaluator; claim=context.claims[0]
    result,_=asyncio.run(Evaluator(tools,files).evaluate(claim,tools.contract['contract_id'],v5.VERSION))
    assert result['status']=='INSUFFICIENT_EVIDENCE'
    assert result['execution_scope']['actual_model_requests_this_claim']==0

@pytest.mark.parametrize('mutation',['source','evidence','during-source','during-evidence','bad-reference','bad-hash','wrong-release','wrong-contract','na-must'])
def test_identity_reference_and_na_attacks_fail_closed(isolated_evaluator,mutation):
    files,tools,context=isolated_evaluator; claim=copy.deepcopy(context.claims[0]); script=suggestion(claim)
    version=v5.VERSION
    if mutation in {'source','evidence'}:
        relative=v5.ROOT+'fixtures/'+('source' if mutation=='source' else 'support')+'.json'
        target=context.root/relative;target.write_bytes(target.read_bytes()+b' ')
    elif mutation=='bad-reference': script['evidence_refs']=[{'evidence_id':claim['evidence_refs'][0]['evidence_id'],'snippet':'unread'}]
    elif mutation=='bad-hash': claim['evidence_refs'][0]['expected_raw_sha256']='0'*64
    elif mutation=='wrong-release': script['release_id']='not-this-release'
    elif mutation=='wrong-contract': version='9.0.0'
    elif mutation=='na-must': script['status']='NOT_APPLICABLE'
    class Mutating(MockProvider):
        async def complete(self,messages):
            if mutation in {'during-source','during-evidence'}:
                relative=v5.ROOT+'fixtures/'+('source' if mutation=='during-source' else 'support')+'.json'
                target=context.root/relative;target.write_bytes(target.read_bytes()+b' ')
            return await super().complete(messages)
    provider=Mutating([script])
    result,_=asyncio.run(Evaluator(tools,files,provider).evaluate(claim,tools.contract['contract_id'],version))
    assert result['status']=='INSUFFICIENT_EVIDENCE'
    assert result['status']!='PASS'

@pytest.mark.parametrize('path',['../outside.json','C:/outside.json','//server/share/file.json','.env','data/game-v5.sqlite','x:stream.json','.git/config','folder/../file.json'])
def test_evaluator_reader_rejects_untrusted_paths(tmp_path,path):
    with pytest.raises(EvaluationError): safe_read(tmp_path,path)

def test_semantic_false_and_missing_observation_distinct():
    support=json.loads((Path(__file__).resolve().parents[2]/'evaluation/v5/fixtures/support.json').read_text(encoding='utf-8'))
    failures,gaps=v5._semantic('V5-C1',support)
    assert failures==[] and gaps==[]
    false=copy.deepcopy(support);false['checks']['admissions'][0]['replay_won']=False
    failures,_=v5._semantic('V5-C1',false);assert 'OBSERVED_FALSE_replay_won' in failures
    missing=copy.deepcopy(support);missing['checks']['admissions'].pop()
    failures,gaps=v5._semantic('V5-C1',missing)
    assert failures==[] and 'NINE_DISTINCT_ROOM_DIFFICULTY_REPLAYS_REQUIRED' in gaps
