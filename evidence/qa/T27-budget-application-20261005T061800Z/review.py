"""Readonly post-application audit. Never invokes reconciliation helper."""
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
def load(rel): return json.loads((ROOT/rel).read_text(encoding='utf-8'))
def sha(rel): return hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
def write(name,value):
    with (OUT/name).open('x',encoding='utf-8') as f: json.dump(value,f,ensure_ascii=False,indent=2)
checks=[]
def check(name,yes,details=None): checks.append(dict(name=name,passed=bool(yes),details=details))
helper='evidence/integration/reconcile_timeout_upper.py'
applied_path='evidence/integration/timeout-human-fee-20261005-applied.json'
dry_path='evidence/integration/timeout-human-fee-20261005-dryrun.json'
t25_path='evidence/qa/T25-independent-20261005T055600Z/result.json'
t27_path='evidence/qa/T27-budget-reconcile-20261005T061300Z/result.json'
run='experiments/runs/20261005T053334004502Z-formal-real-48d972eb/'
watch=[helper,applied_path,dry_path,t25_path,t27_path,*[run+x for x in ('run.json','plan.json','raw.jsonl','journal.jsonl','completion.json','summary.json')]]
before={p:sha(p) for p in watch}
applied,dry,t25,t27=[load(p) for p in (applied_path,dry_path,t25_path,t27_path)]
expected_helper='e4a5981b810a71b294321b14fe2947fb2613856b80268e4ac14b3faa10b44f8b'
check('exact_helper_application_and_qa_pin',before[helper]==applied['helper_raw_sha256']==t27['helper_raw_sha256']==expected_helper)
check('independent_124_result_pin',before[t27_path]=='bef67641c46f742b70d185f0f1150dfc0293382df399ee86cd44b38f06c42fc4' and t27['checks']==t27['passed']==124 and not t27['failures'])
check('historical_T25_pin',before[t25_path]=='84ca0cc505476cabd8daaefb1b9dbb826e07853319bb3148d8107e9a2b3f21ea')
check('historical_dryrun_source_unchanged',dry['helper_raw_sha256']=='9e6ceebaf1fd8cfa49e7caa411d203250839802b367d6eacbc7dff1ca64860a1' and dry['applied'] is False and dry['before']==dry['after'])
expected=list(dry['before']);expected[5:7]=['settled','HUMAN_FEE_REPORTED_UPPER_RETAINED']
check('applied_only_state_reason',applied['applied'] is True and applied['already_closed'] is False and applied['before']==dry['before'] and applied['after']==expected)
check('full_bound_token_null_retained',applied['after'][3:5]==[162920000,162920000] and applied['after'][7:]==[None,None,None])
check('human_report_not_invoice_or_usage',applied['human_reported_cost_units']==50000000 and applied['retained_charge_units']==162920000 and applied['provider_usage_known'] is False and applied['provider_invoice_independently_verified'] is False)
check('original_aggregate_cap_counts',applied['calls']==dry['calls']==35 and applied['charged_upper_units']==dry['charged_upper_units']==277602960 and applied['cap_units']==dry['cap_units']==10000000000)
cols=applied['columns'];call=applied['call_id']
ledger=ROOT/'data/ai-budget.sqlite'
with sqlite3.connect(ledger.resolve().as_uri()+'?mode=ro',uri=True,isolation_level=None) as db:
    db.row_factory=sqlite3.Row
    config=[dict(r) for r in db.execute('SELECT id,cap,frozen FROM budget_config')]
    totals=dict(db.execute('SELECT COUNT(*) AS calls,SUM(charged) AS charged FROM budget_calls').fetchone())
    states=[dict(r) for r in db.execute('SELECT state,COUNT(*) AS calls FROM budget_calls GROUP BY state')]
    current=[dict(r) for r in db.execute('SELECT '+','.join(cols)+" FROM budget_calls WHERE scope='experiments'")]
    other_aggregate=dict(db.execute("SELECT COUNT(*) AS calls,SUM(charged) AS charged FROM budget_calls WHERE scope!='experiments'").fetchone())
    triggers=[dict(r) for r in db.execute("SELECT name FROM sqlite_master WHERE type='trigger'")]
check('current_exact_cap_frozen',config==[dict(id=1,cap=10000000000,frozen=0)])
check('current_calls_charge_same',totals==dict(calls=35,charged=277602960))
check('current_no_pending_unknown',states==[dict(state='settled',calls=35)])
check('no_actual_sqlite_triggers',not triggers)
prior={r['id']:r for r in t25['ledger_readonly']['experiment_calls']};now={r['id']:r for r in current}
check('experiment_scope_original29_ids',set(prior)==set(now) and len(now)==29)
for row_id,p in prior.items():
    want=dict(p)
    if row_id==call:want.update(state='settled',reason='HUMAN_FEE_REPORTED_UPPER_RETAINED')
    check('exact_original_experiment_row:'+row_id,now[row_id]==want)
check('target_current_matches_application',tuple(now[call][c] for c in cols)==tuple(applied['after']))
check('other_scope_aggregate_preserved',other_aggregate==dict(calls=6,charged=10354480))
check('original_timeout_raw_preserved',before[run+'raw.jsonl']=='74c20c72ac39e236bd3e5c48062f71e2c98a92b9368269c3e67a95c841db2e28' and before[run+'summary.json']=='83870be5f56b8f53a4c5be6a42fe049aee78c8159dac872f20ef04c74a4ecb11')
original_rows=[json.loads(l) for l in (ROOT/run/'raw.jsonl').read_text(encoding='utf-8').splitlines()]
timeout=next(r for r in original_rows if r['call_id']==call)
check('original_model_unknown_not_rewritten',timeout['status']=='timeout' and timeout['error']=='MODEL_TIMEOUT' and timeout['usage'] is None and timeout['response_received'] is None and timeout['reported_model'] is None and timeout['charged_upper_cny']==.16292)
check('historical_T25_unknown_accounting_unchanged',t25['phase_unknown_reservation_upper_cny']==.16292 and t25['ledger_readonly']['states']==[dict(state='settled',n=34,charged=114682960),dict(state='unknown',n=1,charged=162920000)])
after={p:sha(p) for p in watch};check('all_reviewed_artifacts_unchanged',before==after)
result=dict(task='T27-budget-application-readonly',created_at=datetime.now(timezone.utc).isoformat(),command=[sys.executable,*sys.argv],working_directory=str(ROOT),checks=len(checks),passed=sum(c['passed'] for c in checks),failures=[c for c in checks if not c['passed']],
            reviewed_artifact_hashes=before,ledger_mode='ro',current_safe_snapshot=dict(config=config,totals=totals,states=states,experiment_calls=current,other_scope_aggregate=other_aggregate,triggers=triggers),original_apply_by_qa=False,qa_network_calls=0,qa_paid_calls=0,
            main_application_exit_report=dict(actual_exit_code=0,chunk='5c5c65',provenance='Main task handoff; QA independently observes only this read-only audit process exit'),
            limitations=['Human fee report is not independently obtained supplier invoice; full upper charge retained and missing model response/usage not recovered.',
                         'All 29 experiment rows independently compare with actual pre-apply T25 row snapshots. Six other-scope row identities were not saved in prior public QA; their aggregate is independently unchanged, while exact all-row preservation is enforced by the pinned helper reviewed in 124 isolated checks.',
                         'Accounting closure does not rewrite original T25 timeout evidence and grants no new paid phase authorization.'])
write('checks.json',checks);write('result.json',result)
print(json.dumps(dict(checks=result['checks'],passed=result['passed'],failed=len(result['failures']),output=str(OUT)),ensure_ascii=False))
raise SystemExit(1 if result['failures'] else 0)
