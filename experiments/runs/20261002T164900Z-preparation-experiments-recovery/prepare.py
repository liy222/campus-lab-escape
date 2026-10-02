"""Read-only plan review plus append-only preparation artifacts; no env/ledger/provider."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from experiments.common import load, sha, baseline_binding, experiment_hashes, encoded
from experiments.plan import make_plan, input_for

DEST=Path(__file__).resolve().parent
before=experiment_hashes()
binding_before=baseline_binding()
plans={}
for phase, rel in {
 'pilot':'experiments/runs/20261002T125617836186Z-pilot-plan-07a086ba/plan.json',
 'formal':'experiments/runs/20261002T125600594673Z-formal-plan-949ddff0/plan.json'
}.items():
 path=ROOT/rel
 stored=load(path)
 current=make_plan(phase)
 inputs=[]
 for row in stored['rows']:
  inp=path.parent/'inputs'/(row['row_id']+'.json')
  messages, tools, hashes=input_for(load(ROOT/'experiments/fixtures'/(row['sample_id']+'.json')),row['variant'])
  inputs.append({'row_id':row['row_id'],'file':str(inp.relative_to(ROOT)).replace('\\','/'),
   'raw_sha256':sha(inp.read_bytes()),'matches_current':load(inp)=={'messages':messages,'tools':tools,**hashes}
    and all(row[k]==hashes[k] for k in hashes),'input_hash':row['input_hash'],
   'payload_utf8_bytes':row['payload_utf8_bytes'],'input_token_bound':row['input_token_bound'],
   'reservation_units':row['reservation_units']})
 plans[phase]={'source_plan':rel,'plan_hash':sha(stored),'plan_raw_sha256':sha(path.read_bytes()),
  'freeze_hash':sha(stored['freeze']),'matches_current_plan':stored==current,
  'input_count':len(inputs),'all_saved_inputs_match':all(i['matches_current'] for i in inputs),
  'planned':stored['planned'],'sum_reservation_units':sum(i['reservation_units'] for i in inputs),
  'max_reservation_units':max(i['reservation_units'] for i in inputs),'inputs':inputs}
 if stored!=current or not all(i['matches_current'] for i in inputs):
  raise ValueError('FROZEN_PLAN_OR_INPUT_CHANGED')
pricing_path=ROOT/'evidence/integration/pricing-check-20261002T120000Z.json'
pricing=load(pricing_path)
checked=datetime.fromisoformat(pricing['checked_at_utc'].replace('Z','+00:00'))
now=datetime.now(timezone.utc)
report={'kind':'read-only-preparation-not-model-evidence-not-authorization','prepared_at_utc':now.isoformat(),
 'python':sys.executable,'actual_command':sys.argv,'plans':plans,'source_hashes_before':before,
 'baseline':{'commit':binding_before['commit'],'manifest_raw_sha256':binding_before['manifest_raw_sha256'],
  'bound_sources':len(binding_before['sources']),'bound_evidence':len(binding_before['artifacts']),
  'unbound_prior_source_records':binding_before['unbound_prior_source_records'],
  'generated_runtime_only':binding_before['generated_runtime_only'],'limitations':binding_before['limitations']},
 'pricing':{'path':str(pricing_path.relative_to(ROOT)).replace('\\','/'),'raw_sha256':sha(pricing_path.read_bytes()),
  'checked_at_utc':pricing['checked_at_utc'],'age_seconds_at_preparation':(now-checked).total_seconds(),
  'valid_until_utc_inclusive':(checked+timedelta(hours=24)).isoformat(),
  'peak_cny_per_million':pricing['peak_cny_per_million'],'fresh_at_preparation':0<=(now-checked).total_seconds()<=86400},
 'recommendation':{'pilot_max_calls':6,'pilot_additional_upper_cap_units':700000000,'pilot_additional_upper_cap_cny':0.7,
  'pilot_sum_reservation_cny':plans['pilot']['sum_reservation_units']/1e9,
  'formal_sum_reservation_cny':plans['formal']['sum_reservation_units']/1e9,
  'formal_authorization':'Separate new Main GO only after completed known-usage real pilot and cost review',
  'unique_shared_ledger':'data/ai-budget.sqlite','shared_total_cap_cny':10,
  'last_ledger_facts':'Main-reported only: 6 settled, charge 10354480 units, remaining 9989645520 units, no pending/frozen. Not re-read by Experiments.'},
 'safe_credential_entry':{'existing_loader':'backend.app.ai.provider.DeepSeekConfig.from_environment',
  'loads_only_after':'runner.main -> approve(...); execute real -> DeepSeekConfig.from_environment()',
  'env_file':'Project root .env; read as UTF-8-sig data, allowlist MODEL_API_KEY/MODEL_NAME/MODEL_BASE_URL; process env overrides',
  'shell_evaluation':False,'credential_printing':False,'manual_env_loading_required':False},
 'env_read':False,'ledger_read':False,'provider_constructed':False,'network_calls':0,'paid_calls':0,
 'owner_tests_repeated':False,'limitations':['Preparation is not independent QA or experimental outcome.',
  'No issued Main authorization was used; paid calls require exact raw SHA and explicit GO.',
  'Pilot cap and pricing age must still be checked at execution time; shared ledger is authoritative.',
  'Formal pilot acceptance uses completed and known-usage rows; Main must independently review quality and costs.',
  'Failures are retained and no authorization reuse/resend is allowed.']}

def new_file(name,value):
 with (DEST/name).open('xb') as handle:
  handle.write(value if isinstance(value,bytes) else encoded(value)+b'\n')

template={'id':'T23-pilot-Main-REQUIRES-ISSUANCE','approved_by':'Main','approved':False,'phase':'pilot',
 'plan_hash':plans['pilot']['plan_hash'],'freeze_hash':plans['pilot']['freeze_hash'],'max_calls':6,
 'additional_upper_cap_units':700000000,'expires_at':'MAIN_SET_FUTURE_OFFSET_AWARE_UTC_BEFORE_PRICING_EXPIRES',
 'pricing_evidence':report['pricing']['path'],'pricing_sha256':report['pricing']['raw_sha256'],
 'template_only':True,'note':'Not an authorization. Main must issue a new file under experiments/authorizations and provide its raw SHA256 plus explicit GO.'}
new_file('pilot-authorization-template.json',template)
entry='''# T23 preparation; real execution remains gated

No credentials or ledger were read for this preparation. No model or network calls were made. Frozen experiment code and documents were not edited.

The existing real runner reads root .env only inside the real execution branch after approve() succeeds. DeepSeekConfig.from_environment reads three allowlisted fields as data (UTF-8-sig), with process environment taking precedence. Do not dot-source .env, evaluate its values as PowerShell, print its contents, or perform a preliminary provider construction. Existing provider checks the official deepseek-flash model and https://api.deepseek.com endpoint and original data/ai-budget.sqlite.

The template in this folder is deliberately invalid: approved=false, no real expiry, and outside authorizations/. Main must create a new authorization with an unused id in experiments/authorizations/, approved=true, reviewed UTC expiry, the exact plan/freeze/pricing hashes and max_calls=6/additional_upper_cap_units=700000000 (0.70 CNY), and provide the file raw SHA plus explicit GO after independent QA acceptance. This cap is phase-local and does not grant a new allowance.

Run from D:\\深度能力 only after that GO:

```powershell
& 'C:\\Users\\liyh\\.conda\\envs\\1\\python.exe' -B -X utf8 -m experiments.runner pilot --mode real --authorization '<MAIN_ISSUED_FILE_UNDER_experiments/authorizations>' --authorization-sha '<MAIN_PROVIDED_RAW_SHA256>'
```

Execute once; do not reuse the authorization or resend failure rows. Preserve run/plan/input/raw/journal/completion/summary. Unexpected exit or interruption requires read-only reconciliation, with no resend. Unknown usage, timeout, abnormal model/rate/auth/bounds, source/input changes, shared/phase budget stop and repeated known-cost failures retain the stop result.

Formal execution is a separate phase with 72 max_calls, exact formal plan hash, same freeze hash, and a new finite cap. It also requires the real pilot_run_id, pilot_summary_sha256 and pilot_review_accepted=true after Main reviews six completed known-usage pilot rows, actual cost and quality. This preparation does not issue that GO.

Price evidence checked at 2026-10-02T12:00:00Z is accepted by existing code only up to age 86400 seconds. Its temporal validity is checked again at admission; this document cannot extend it. Reservation upper bounds are not provider bills or measured token cost.
'''
new_file('safe-real-entry.md',entry.encode('utf8'))
report['source_hashes_after']=experiment_hashes()
report['experiment_sources_unchanged']=before==report['source_hashes_after']
report['baseline_binding_unchanged']=binding_before==baseline_binding()
if not report['experiment_sources_unchanged'] or not report['baseline_binding_unchanged']:
 raise ValueError('SOURCE_CHANGED_DURING_PREPARATION')
new_file('preparation.json',report)
files={p.name:sha(p.read_bytes()) for p in DEST.iterdir() if p.is_file()}
new_file('artifact-sha256.json',files)
print(json.dumps({'preparation_directory':str(DEST),'files':files,'source_unchanged':True,
 'pilot':{k:v for k,v in plans['pilot'].items() if k!='inputs'},'formal':{k:v for k,v in plans['formal'].items() if k!='inputs'}},ensure_ascii=False))
