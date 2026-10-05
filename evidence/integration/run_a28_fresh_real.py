"""Main one-shot relay for original scoped A28 real check; no evaluation payloads."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
CLEAN=ROOT/'data/reproduction/20261005T115741Z/clean'
LEDGER=ROOT/'data/ai-budget.sqlite'
OUT=ROOT/'evidence/integration/A28-real-fresh-process-20261006.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert not OUT.exists(), 'Consumed A28 relay; no replay'
    assert CLEAN.is_dir() and LEDGER.is_file()
    names=['tests/real_m3_runner.py','tests/qa_runner.py','backend/app/ai/provider.py','backend/app/ai/budget.py','backend/app/ai/runtime.py','backend/app/ai/context.py','contracts/tools.json','backend/app/domain/rules.py','scripts/reproduce.py','backend/app/main.py','contracts/api.schema.json']
    pins={n:sha(CLEAN/n) for n in names}
    for n,d in pins.items():assert sha(ROOT/n)==d,n
    with sqlite3.connect(LEDGER.as_uri()+'?mode=ro',uri=True) as db:
        assert db.execute('SELECT id,cap,frozen FROM budget_config').fetchall()==[(1,10_000_000_000,0)]
        assert db.execute("SELECT COUNT(*) FROM budget_calls WHERE state!='settled'").fetchone()[0]==0
        count,total=db.execute('SELECT COUNT(*),SUM(charged) FROM budget_calls').fetchone()
    assert total+500_000_000<=10_000_000_000
    record={'at_utc':datetime.now(timezone.utc).isoformat(),'purpose':'Original A28 real game integration check; no revised evaluation dispatch','candidate_commit':'833aafb09ad20dc1ba82cfed198485ce13300067','clean':str(CLEAN),'canonical_ledger':str(LEDGER),'maximum_calls':3,'additional_upper_cap_cny':.5,'budget_before':{'calls':count,'charged_upper_units':total,'cap_units':10_000_000_000},'sources_before':pins,'source_guard':'Root and clean exact same eleven relevant files; full clean pack identity certified separately. Ancestor git head is not clean candidate identity.','process_started':False,'actual_paid_calls':0}
    with OUT.open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2);f.write('\n')
    link=CLEAN/'data/ai-budget.sqlite'
    assert not link.exists() and not link.is_symlink(), 'Never replace a local budget'
    try:
        link.parent.mkdir(exist_ok=True)
        os.symlink(str(LEDGER),str(link),target_is_directory=False)
    except OSError as exc:
        record.update({'pre_dispatch_stop':'Runtime file symlink privilege unavailable; no provider request attempted','error_type':type(exc).__name__,'process_exit_code':1})
        OUT.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'record':str(OUT.relative_to(ROOT)),'exit_code':1,'actual_paid_calls':0,'reason':'File symlink unavailable'}))
        return 1
    assert link.resolve(strict=True)==LEDGER.resolve(strict=True)
    sys.path.insert(0,str(ROOT))
    from scripts.dev import load_env_file
    env=os.environ.copy();load_env_file(ROOT/'.env',env)
    assert env.get('MODEL_API_KEY','').strip(), 'Missing credential; no request'
    env['PYTHONUTF8']='1';env['PYTHONDONTWRITEBYTECODE']='1'
    cmd=[sys.executable,'-B','-X','utf8','-m','tests.real_m3_runner','--candidate','A28-clean-833aafb-controlled-real-20261006','--main-real-go','A28-original-project-scope-CNY10-once-20261006']
    before=set((CLEAN/'evidence/qa').glob('*-m3-real'))
    record.update({'process_started':True,'command':cmd,'runtime_link':str(link),'runtime_link_resolves_to_original':True})
    OUT.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    result=subprocess.run(cmd,cwd=CLEAN,env=env,check=False)
    after=set((CLEAN/'evidence/qa').glob('*-m3-real'));created=after-before
    assert len(created)==1,'Record actual process outcome even on failure; no replay'
    folder=next(iter(created));run=json.loads((folder/'run.json').read_bytes())
    record.update({'process_exit_code':result.returncode,'evidence':str(folder),'actual_paid_calls':run['actual_provider_attempts'],'actual_result_status':run['status'],'run_sha256':sha(folder/'run.json'),'sources_after':{n:sha(CLEAN/n) for n in names},'additional_conservative_charge_cny':run['additional_conservative_charge_cny']})
    assert record['sources_before']==record['sources_after']
    OUT.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'record':str(OUT.relative_to(ROOT)),'process_exit_code':result.returncode,'status':run['status'],'actual_paid_calls':run['actual_provider_attempts']}))
    return result.returncode
if __name__=='__main__':raise SystemExit(main())