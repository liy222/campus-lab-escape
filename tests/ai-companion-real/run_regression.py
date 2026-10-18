"""Frozen quality-fix regression; offline, new epoch output only."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import io
import json
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'tests/ai-companion'))
RECORDS = []


def read(p):
    return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))


class QualityContext(unittest.TestCase):
    def test_catalog_procedural_emptyrefs_unknown_reject_and_normal_relations(self):
        from backend.app.ai.companion import build_companion_context, validate_companion_reply
        cases = {c['case_id']: c for c in read('evidence/integration/ai-companion-real/20261018T110144068872Z-real/result.json')['case_results']}
        for cid in ('C01','C03','C04','C05','C06','C07'):
            with self.subTest(case=cid):
                c = cases[cid]
                state = c['before_public']
                context = build_companion_context(state, c['question'])
                expected = [{'object_id': o['object_id'], 'name': o['name']} for o in state['objects']]
                self.assertEqual(context['visible_object_catalog'], expected)
                self.assertTrue(all(set(x)=={'object_id','name'} for x in context['visible_object_catalog']))
                self.assertLessEqual({x['object_id'] for x in context['visible_objects']}, {x['object_id'] for x in expected})
                if cid=='C01':
                    self.assertEqual(len(expected),7)
                    self.assertGreater(len(expected),len(context['visible_objects']))
                if cid in ('C04','C05','C06'):
                    self.assertEqual(context['allowed_clue_refs'], [], 'Procedural facts do not cite unrelated clues')
                    with self.assertRaises(ValueError):
                        validate_companion_reply(state, {'answer':'可以先关注装置当前提供的操作。','clue_refs':['r2_maintenance_clue']}, c['question'], allowed_refs=context['allowed_clue_refs'])
                if cid=='C03':
                    self.assertLessEqual({'r1_clock_clue','r1_record_clue'},set(context['allowed_clue_refs']))
                    value={'answer':'可以把记录里最后两位的规则，与已知钟面的分钟部分对应起来。','clue_refs':['r1_clock_clue','r1_record_clue']}
                    self.assertEqual(validate_companion_reply(state,value,c['question'],allowed_refs=context['allowed_clue_refs']),value)
                if cid=='C07':
                    self.assertLessEqual({'r1_symbols_clue','r2_indices_clue','r3_legend_clue'},set(context['allowed_clue_refs']))
                with self.assertRaises(ValueError):
                    validate_companion_reply(state,{'answer':'可以先看看当前装置。','clue_refs':['r1_cabinet_clue']},c['question'],allowed_refs=context['allowed_clue_refs'])
                RECORDS.append({'check':'quality-context','case':cid,'catalog':context['visible_object_catalog'],'allowed_clue_refs':context['allowed_clue_refs'],'director':context['director']})


def main():
    cp=sys.argv[1]
    candidate=read(cp)
    sha=lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    before={p:sha(p) for p in candidate['source_sha256']}
    assert before==candidate['source_sha256']
    prep=read('evidence/integration/ai-companion/qa/preparation.json')
    assert all(sha(p)==h for p,h in prep['old_test_sha256'].items())
    first=read('evidence/integration/ai-companion-real/20261018T110144068872Z-real/result.json')
    old_artifacts={p:sha(p) for p in first['artifact_sha256']}
    assert old_artifacts==first['artifact_sha256']
    from tests.api import test_ai_companion as original
    from tests.api import test_hint_flow as preset
    from tests.api import test_play_ai_settings as legacy
    from tests.api import test_r1 as capture
    from fake_runtime import create_test_runtime
    class QualityHTTP(original.CompanionAcceptance):
        def test_procedural_free_refs_runtime_and_store_authority(self):
            for tool,args in original.ROUTE[:10]: self.action(tool,args)
            question='是不是只有储物柜可以看？输入已接受但柜门没开，该如何理解这个状态？'
            answer='储物柜并不是唯一可看的物件，墙钟和实验记录也在场景中。数字锁已经接受输入，柜门仍合着，可以留意拉开柜门这个操作。'
            self.steps=[original.reply(answer)]
            data,_=self.accepted(question)
            self.assertEqual(data['answer'],answer)
            context=json.loads(next(m['content'] for m in self.calls[-1]['messages'] if m['role']=='user'))
            self.assertEqual(context['allowed_clue_refs'],[])
            self.assertEqual(len(context['visible_object_catalog']),len(self.state()['objects']))
            before=self.state()
            self.steps=[original.reply(answer,['r1_clock_clue'])]
            rejected,_=self.turn(question)
            self.assertEqual(rejected['status'],'stopped')
            self.assertEqual(self.state(),before)
            class Fake:
                async def run(fake,start,callbacks):
                    from backend.app.ai.types import TurnResult,Version
                    return TurnResult({'answer':answer,'clue_refs':['r1_clock_clue'],'status':'no_suggestion','stop_reason':None,'usage':{'provider':'deepseek','model':'qa-fake','input_tokens':1,'output_tokens':1,'model_calls':1,'read_tool_calls':0}},None,(),Version.from_state(start.visible_state))
            with patch('backend.app.ai.runtime.create_request_runtime',return_value=Fake()):
                rejected,_=self.turn(question)
            self.assertEqual(rejected['status'],'stopped')
            self.assertEqual(self.state(),before)
            RECORDS.append({'check':'runtime-and-store-disallow-known-but-unsupported-refs','status':rejected['status'],'catalog_count':len(context['visible_object_catalog'])})
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(original), unittest.defaultTestLoader.loadTestsFromTestCase(QualityContext), QualityHTTP('test_procedural_free_refs_runtime_and_store_authority')])
    for name in prep['old_preset_methods']:suite.addTest(preset.HintFlowHTTP(name))
    for name in prep['old_legacy_methods']:suite.addTest(legacy.PlayAiSettings(name))
    folder=ROOT/'evidence/integration/ai-companion-real/qa'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-fixed-regression')
    folder.mkdir(parents=True)
    output=io.StringIO()
    with patch('backend.app.ai.runtime.create_request_runtime',create_test_runtime):
        result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
    after={p:sha(p) for p in candidate['source_sha256']}
    oldtests=all(sha(p)==h for p,h in prep['old_test_sha256'].items())
    oldevidence=all(sha(p)==h for p,h in old_artifacts.items())
    code=0 if result.wasSuccessful() and before==after and oldtests and oldevidence else 1
    def safe(v):
        if isinstance(v,dict):return{k:safe(x) for k,x in v.items()}
        if isinstance(v,list):return[safe(x) for x in v]
        if isinstance(v,str):
            for secret in capture.SECRETS|{original.KEY,legacy.KEY_A,legacy.KEY_B}:v=v.replace(secret,'[REDACTED]')
        return v
    (folder/'unittest.txt').write_text(safe(output.getvalue()),encoding='utf-8')
    (folder/'checks.json').write_text(json.dumps(safe(RECORDS+original.RECORDS),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    payload={'candidate':cp,'candidate_sha':'d4bf7c1c95f866118bed12b675b449d0fa53954dce0fbb8777992dee9884c2e5','command':[sys.executable,'-B','-X','utf8',*sys.argv],'exit_code':code,'methods':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'source_sha256_before':before,'source_sha256_after':after,'old_test_files_unchanged':len(prep['old_test_sha256']) if oldtests else False,'first_batch_artifacts_unchanged':oldevidence,'qa_script_sha256':sha('tests/ai-companion-real/run_regression.py'),'paid_calls':0,'canonical_budget_access':False,'builds':0,'UI_runs':0,'limitations':['Offline fake provider pipeline and context/guard regression; not actual model quality retest.','Existing first7 paid outputs stay historical, no claim they all pass after the fix.']}
    (folder/'run.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(safe(output.getvalue()))
    print(json.dumps({'evidence':str(folder),'exit_code':code,'methods':result.testsRun,'failures':len(result.failures),'errors':len(result.errors)}))
    return code


if __name__=='__main__':
    sys.exit(main())
