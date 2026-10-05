"""Read-only A28 real-segment readiness; never imports or executes game code."""
import ast
import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parents[1]
CLEAN=ROOT/'data/reproduction/20261005T115741Z/clean'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))

def main():
    out=ROOT/('evidence/qa/A28-real-readiness-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));out.mkdir()
    selected=['tests/real_m3_runner.py','tests/qa_runner.py','backend/app/ai/context.py','backend/app/ai/runtime.py','backend/app/ai/provider.py','backend/app/ai/budget.py','backend/app/main.py','backend/app/domain/rules.py','contracts/api.schema.json','contracts/tools.json','scripts/reproduce.py']
    paths=[ROOT/p for p in selected]+[CLEAN/p for p in selected]+[ROOT/'docs/execution-plan.md',ROOT/'evidence/qa/20261002T120735404563Z-m3-real/run.json',ROOT/'evidence/integration/T32-clean-final-20261005T115741Z/report.json',ROOT/'evidence/integration/T32-clean-final-20261005T115741Z/materialization.json',pathlib.Path(__file__).resolve()]
    before={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    recorded=load(ROOT/'evidence/integration/T32-clean-final-20261005T115741Z/report.json')
    materialization=load(ROOT/'evidence/integration/T32-clean-final-20261005T115741Z/materialization.json')
    old=load(ROOT/'evidence/qa/20261002T120735404563Z-m3-real/run.json')
    runner=(CLEAN/'tests/real_m3_runner.py').read_text(encoding='utf-8')
    tree=ast.parse(runner)
    prompt=next(value.value for node in ast.walk(tree) if isinstance(node,ast.Dict) for key,value in zip(node.keys,node.values) if isinstance(key,ast.Constant) and key.value=='message' and isinstance(value,ast.Constant) and isinstance(value.value,str) and 'get_inventory' in value.value)
    pairs={p:{'root_raw_sha256':sha(ROOT/p),'clean_raw_sha256':sha(CLEAN/p),'materialized_expected_raw_sha256':materialization[p]['runtime_raw_sha256']}for p in selected}
    after={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    result={'kind':'A28-read-only-real-readiness','at_utc':datetime.now(timezone.utc).isoformat(),'command':[sys.executable,'-B','-X','utf8','tests/review_a28_real_readiness.py'],'exit_code':0,'source_before':before,'source_after':after,'source_unchanged':before==after,'source_pairs':pairs,'all_selected_clean_bytes_match_materialization':all(v['clean_raw_sha256']==v['materialized_expected_raw_sha256'] for v in pairs.values()),'all_selected_root_clean_bytes_equal':all(v['root_raw_sha256']==v['clean_raw_sha256']for v in pairs.values()),'clean_identity':{k:recorded.get(k)for k in ['workspace','commit','archive_sha256','main_pins_sha256','status','exit_code','provider','actual_paid_calls','completed_at']},'old_real_result':{k:old.get(k)for k in ['candidate','status','exit_code','actual_provider_attempts','additional_conservative_charge_cny','canonical_ledger']},'exists_only':{'clean_is_directory':CLEAN.is_dir(),'Root_canonical_ledger_exists':(ROOT/'data/ai-budget.sqlite').exists(),'clean_derived_ledger_exists':(CLEAN/'data/ai-budget.sqlite').exists()},'runner_prompt_static':prompt,'hidden_numeric_answers_in_prompt_static':any(code in prompt for code in ('382','724','231')),'readiness':'CONDITIONAL; original runner cannot directly use clean with existing Root canonical ledger','guard_facts':['runner CANONICAL resolves from its module ROOT; missing clean ledger stops before calls','clean DeepSeekProvider rejects an explicit Root ledger unless its expected resolved path aliases same canonical file','Main may prepare an exact physical-file symlink alias after explicit authorization; never copy or initialize a clean budget','First get_inventory forced; two preceding inspect actions scripted; one AI turn, max3 calls, .50CNY segment upper, no retry','Main separate gate string is record marker, not self-validating authorization; specific payload/limits authorization still required'], 'actions_not_taken':['No target import/execution','No paid/network request','No credential/env read','No database content read or write','No symlink or environment creation','No full regression or service startup','No Git operation'],'limits':['Read-only preparation does not complete A28 real-AI acceptance','Runtime execution still requires separately approved concrete payload and canonical ledger gate','Old controlled real result does not prove autonomous whole-game behavior or human signoff']}
    if not result['source_unchanged'] or not result['all_selected_clean_bytes_match_materialization']:result['exit_code']=1
    (out/'readiness.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'evidence':str(out),'exit_code':result['exit_code'],'files_hashed':len(before),'unchanged':result['source_unchanged'],'selected_clean_pins_match':result['all_selected_clean_bytes_match_materialization'],'direct_runner_ready':False},ensure_ascii=False))
    return result['exit_code']

if __name__=='__main__':sys.exit(main())
