"""Isolated reconciliation QA; original ledger only ever opened mode=ro."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HELPER=ROOT/'evidence/integration/reconcile_timeout_upper.py'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f: json.dump(v,f,ensure_ascii=False,indent=2)

def fixture(helper,factory=sqlite3.Connection):
    db=sqlite3.connect(':memory:',isolation_level=None,factory=factory)
    db.execute('CREATE TABLE budget_config(id INTEGER PRIMARY KEY,cap INTEGER NOT NULL,frozen INTEGER NOT NULL)')
    db.execute('CREATE TABLE budget_calls(id TEXT PRIMARY KEY,scope TEXT NOT NULL,created_at TEXT NOT NULL,reserved INTEGER NOT NULL,charged INTEGER NOT NULL,state TEXT NOT NULL,reason TEXT,prompt_tokens INTEGER,completion_tokens INTEGER,cache_hit_tokens INTEGER)')
    db.execute('INSERT INTO budget_config VALUES(1,10000000000,0)')
    db.execute('INSERT INTO budget_calls VALUES(?,?,?,?,?,?,?,?,?,?)',helper.PREVIOUS)
    # Synthetic remainder of the original aggregate; no nonexperiment actual call IDs copied.
    for i in range(34):
        charge=114682960 if i==0 else 0
        db.execute('INSERT INTO budget_calls VALUES(?,?,?,?,?,?,?,?,?,?)',
                   (f'isolated-history-{i}','synthetic','2026-01-01',charge,charge,'settled',None,0,0,0))
    return db

def snapshot(db):
    return dict(config=db.execute('SELECT * FROM budget_config ORDER BY id').fetchall(),
                calls=db.execute('SELECT * FROM budget_calls ORDER BY id').fetchall())

class CommitFailure(sqlite3.Connection):
    def commit(self): raise sqlite3.OperationalError('isolated commit fault')

class InterruptedUpdate(sqlite3.Connection):
    def execute(self,sql,parameters=()):
        result=super().execute(sql,parameters)
        if sql.startswith('UPDATE budget_calls SET state='):
            raise KeyboardInterrupt('isolated interrupt after update')
        return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    out=(ROOT/args.output).resolve()
    if not out.is_relative_to(ROOT/'evidence/qa') or out.exists(): raise ValueError('NEW_QA_OUTPUT_REQUIRED')
    spec=importlib.util.spec_from_file_location('isolated_reconcile',HELPER)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    before_helper=sha(HELPER);checks=[];cases=[]
    def check(name,yes,details=None): checks.append(dict(name=name,passed=bool(yes),details=details))
    def rejected(name,mutate=lambda db:None,factory=sqlite3.Connection):
        db=fixture(helper,factory);mutate(db);before=snapshot(db);err=None
        try: helper.reconcile(db,True)
        except BaseException as e: err=type(e).__name__+': '+str(e)
        after=snapshot(db)
        check(name+':reject',err is not None,err)
        check(name+':rollback_exact',before==after)
        check(name+':transaction_released',not db.in_transaction)
        cases.append(dict(case=name,error=err,before=before,after=after,isolated_in_memory=True));db.close()
    # Direct readonly actual evidence, no helper main and no --apply on project DB.
    ledger=ROOT/'data/ai-budget.sqlite'
    with sqlite3.connect(ledger.resolve().as_uri()+'?mode=ro',uri=True,isolation_level=None) as ro:
        actual_before=dict(config=ro.execute('SELECT id,cap,frozen FROM budget_config').fetchall(),
                           row=ro.execute('SELECT '+helper.COLS+' FROM budget_calls WHERE id=?',(helper.CALL,)).fetchone(),
                           totals=ro.execute('SELECT COUNT(*),SUM(charged) FROM budget_calls').fetchone(),
                           states=ro.execute('SELECT state,COUNT(*) FROM budget_calls GROUP BY state ORDER BY state').fetchall(),
                           schema_triggers=ro.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall())
    check('original_exact_unknown_row',actual_before['row']==helper.PREVIOUS)
    check('original_exact_aggregate',actual_before['totals']==(35,277602960) and actual_before['config']==[(1,10000000000,0)] and actual_before['states']==[('settled',34),('unknown',1)])
    dry=json.loads((ROOT/'evidence/integration/timeout-human-fee-20261005-dryrun.json').read_text(encoding='utf-8'))
    prior_path=ROOT/'evidence/qa/T27-budget-reconcile-20261005T060400Z/result.json'
    prior=json.loads(prior_path.read_text(encoding='utf-8')) if prior_path.exists() else None
    historical_source=prior['helper_raw_sha256'] if prior else None
    check('main_historical_dryrun_bound_to_reviewed_source',dry['helper_raw_sha256'] in (before_helper,historical_source))
    check('main_dryrun_preserves_known_unknown',dry['applied'] is False and dry['before']==dry['after']==list(helper.PREVIOUS) and
          dry['charged_upper_units']==277602960 and dry['human_reported_cost_units']==50000000 and dry['retained_charge_units']==162920000 and
          dry['provider_usage_known'] is False and dry['provider_invoice_independently_verified'] is False)
    db=fixture(helper);before=snapshot(db);writes=db.total_changes
    result=helper.reconcile(db,False)
    check('dryrun_no_write',snapshot(db)==before and db.total_changes==writes and not db.in_transaction)
    check('dryrun_unknown_remains',result['applied'] is False and result['before']==result['after']==list(helper.PREVIOUS))
    db.execute('PRAGMA query_only=ON');ro_result=helper.reconcile(db,False)
    check('dryrun_query_only_works',ro_result==result and snapshot(db)==before)
    err=None
    try: helper.reconcile(db,True)
    except sqlite3.OperationalError as e: err=str(e)
    check('apply_query_only_denied',err is not None and snapshot(db)==before and not db.in_transaction)
    db.close()
    db=fixture(helper);before=snapshot(db);result=helper.reconcile(db,True);after=snapshot(db)
    expected=list(helper.PREVIOUS);expected[5:7]=['settled',helper.REASON]
    check('correct_exact_closure',result['before']==list(helper.PREVIOUS) and result['after']==expected and
          result['applied'] is True and result['already_closed'] is False)
    before_calls={r[0]:r for r in before['calls']};after_calls={r[0]:r for r in after['calls']}
    check('only_intended_state_reason_changes',set(before_calls)==set(after_calls) and all(after_calls[k]==(tuple(expected) if k==helper.CALL else v) for k,v in before_calls.items()))
    check('charge_reserved_tokens_cap_frozen_retained',after['config']==before['config'] and result['charged_upper_units']==277602960 and
          result['calls']==35 and result['retained_charge_units']==162920000 and result['after'][3:5]==[162920000,162920000] and result['after'][7:]==[None,None,None])
    check('human_fee_not_invoice_or_provider_usage',result['human_reported_cost_units']==50000000 and result['provider_usage_known'] is False and result['provider_invoice_independently_verified'] is False)
    replay=helper.reconcile(db,True)
    check('idempotent_apply',replay['already_closed'] is True and snapshot(db)==after)
    replay_dry=helper.reconcile(db,False)
    check('idempotent_dryrun',replay_dry['already_closed'] is True and replay_dry['before']==replay_dry['after']==expected and snapshot(db)==after)
    cases.append(dict(case='normal_closure',before=before,after=after,result=result,replay=replay,isolated_in_memory=True));db.close()
    mutation_values={'id':'different-id','scope':'game','created_at':'2026-10-05T05:34:19+00:00','reserved':162920001,'charged':50000000,
                     'state':'reserved','reason':'NETWORK_UNKNOWN','prompt_tokens':0,'completion_tokens':0,'cache_hit_tokens':0}
    for field,val in mutation_values.items():
        rejected('wrong_'+field,lambda db,f=field,v=val:db.execute('UPDATE budget_calls SET '+f+'=? WHERE id=?',(v,helper.CALL)))
    rejected('missing_target',lambda db:db.execute('DELETE FROM budget_calls WHERE id=?',(helper.CALL,)))
    rejected('wrong_closure_reason',lambda db:db.execute("UPDATE budget_calls SET state='settled',reason='OTHER' WHERE id=?",(helper.CALL,)))
    for name,sql in (
        ('cap_lower','UPDATE budget_config SET cap=9999999999'),('cap_higher','UPDATE budget_config SET cap=10000000001'),
        ('frozen','UPDATE budget_config SET frozen=1'),('missing_config','DELETE FROM budget_config'),
        ('extra_config','INSERT INTO budget_config VALUES(2,10000000000,0)'),
        ('total_over_cap',"UPDATE budget_calls SET charged=10000000000 WHERE id='isolated-history-0'"),
        ('other_reserved',"UPDATE budget_calls SET state='reserved' WHERE id='isolated-history-1'"),
        ('other_unknown',"UPDATE budget_calls SET state='unknown' WHERE id='isolated-history-1'")):
        rejected(name,lambda db,s=sql:db.execute(s))
    previous_reported=helper.REPORTED;helper.REPORTED=helper.BOUND+1
    rejected('reported_fee_exceeds_upper');helper.REPORTED=previous_reported
    rejected('commit_exception_rollback',factory=CommitFailure)
    rejected('interrupt_after_update_rollback',factory=InterruptedUpdate)
    triggers={
        'atomic_update_ignored':"CREATE TRIGGER fault BEFORE UPDATE OF state ON budget_calls BEGIN SELECT RAISE(IGNORE); END",
        'update_raises':"CREATE TRIGGER fault BEFORE UPDATE OF state ON budget_calls BEGIN SELECT RAISE(ABORT,'isolated fault'); END",
        'charge_reclamation':"CREATE TRIGGER fault AFTER UPDATE OF state ON budget_calls BEGIN UPDATE budget_calls SET charged=50000000 WHERE id=NEW.id; END",
        'row_count_change':"CREATE TRIGGER fault AFTER UPDATE OF state ON budget_calls BEGIN DELETE FROM budget_calls WHERE id='isolated-history-1'; END",
        'tokens_changed_after_update':"CREATE TRIGGER fault AFTER UPDATE OF state ON budget_calls BEGIN UPDATE budget_calls SET prompt_tokens=1 WHERE id=NEW.id; END",
        'cap_changed_after_update':"CREATE TRIGGER fault AFTER UPDATE OF state ON budget_calls BEGIN UPDATE budget_config SET cap=20000000000; END",
        'frozen_changed_after_update':"CREATE TRIGGER fault AFTER UPDATE OF state ON budget_calls BEGIN UPDATE budget_config SET frozen=1; END",
        'closure_reason_changed':"CREATE TRIGGER fault AFTER UPDATE OF state ON budget_calls BEGIN UPDATE budget_calls SET reason='WRONG' WHERE id=NEW.id; END",
        'other_row_scope_changed':"CREATE TRIGGER fault AFTER UPDATE OF state ON budget_calls BEGIN UPDATE budget_calls SET scope='WRONG' WHERE id='isolated-history-1'; END",
        'other_row_created_changed':"CREATE TRIGGER fault AFTER UPDATE OF state ON budget_calls BEGIN UPDATE budget_calls SET created_at='WRONG' WHERE id='isolated-history-1'; END",
        'other_row_tokens_changed':"CREATE TRIGGER fault AFTER UPDATE OF state ON budget_calls BEGIN UPDATE budget_calls SET completion_tokens=1 WHERE id='isolated-history-1'; END",
        'other_row_unknown_added':"CREATE TRIGGER fault AFTER UPDATE OF state ON budget_calls BEGIN UPDATE budget_calls SET state='unknown' WHERE id='isolated-history-1'; END",
        'charge_swap_same_total':"CREATE TRIGGER fault AFTER UPDATE OF state ON budget_calls BEGIN UPDATE budget_calls SET charged=114682959 WHERE id='isolated-history-0'; UPDATE budget_calls SET charged=1 WHERE id='isolated-history-1'; END",
    }
    for name,sql in triggers.items(): rejected(name,lambda db,s=sql:db.execute(s))
    with sqlite3.connect(ledger.resolve().as_uri()+'?mode=ro',uri=True,isolation_level=None) as ro:
        actual_after=dict(config=ro.execute('SELECT id,cap,frozen FROM budget_config').fetchall(),
                          row=ro.execute('SELECT '+helper.COLS+' FROM budget_calls WHERE id=?',(helper.CALL,)).fetchone(),
                          totals=ro.execute('SELECT COUNT(*),SUM(charged) FROM budget_calls').fetchone(),
                          states=ro.execute('SELECT state,COUNT(*) FROM budget_calls GROUP BY state ORDER BY state').fetchall(),
                          schema_triggers=ro.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall())
    check('original_ledger_unchanged_readonly',actual_before==actual_after)
    check('reviewed_helper_source_unchanged',before_helper==sha(HELPER))
    result=dict(task='T27-budget-reconciliation-independent',at_utc=datetime.now(timezone.utc).isoformat(),command=[sys.executable,*sys.argv],
                working_directory=str(ROOT),checks=len(checks),passed=sum(c['passed'] for c in checks),failures=[c for c in checks if not c['passed']],
                helper_raw_sha256=before_helper,original_ledger_before=actual_before,original_ledger_after=actual_after,
                preserved_historical_dryrun_helper_raw_sha256=dry['helper_raw_sha256'],historical_helper_review=str(prior_path.relative_to(ROOT)) if prior else None,
                original_ledger_mode='ro',original_apply_executed=False,isolated_databases='SQLite :memory: only',paid_calls=0,network_calls=0,
                limitations=['Human CNY0.05 is an explicit owner report, not independently obtained supplier billing.',
                             'Testing may call reconcile(apply=True) only on in-memory fixtures; original main/--apply is never executed.',
                             'Known original token/response/HTTP uncertainty is not recovered or fabricated.',
                             'Synthetic fault triggers test post-update invariants; presence of actual ledger triggers is explicitly recorded.'])
    dump(out/'checks.json',checks);dump(out/'cases.json',cases);dump(out/'result.json',result)
    print(json.dumps(dict(checks=result['checks'],passed=result['passed'],failed=len(result['failures']),output=str(out)),ensure_ascii=False))
    return 1 if result['failures'] else 0

if __name__=='__main__': raise SystemExit(main())
