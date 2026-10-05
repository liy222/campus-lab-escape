"""Independent offline E1 result audit. No provider, environment or network access."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import socket
import sqlite3
import statistics
import sys
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def dump(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)

def summary_independent(rows):
    groups = {}
    for variant in ('full_history', 'structured_summary'):
        subset = [r for r in rows if r['variant'] == variant]
        n = len(subset)
        counts = {key: sum(r[key] is True for r in subset) for key in
                  ('legal', 'correct', 'reference_valid', 'reference_sufficient')}
        completed = sum(r['status'] == 'completed' for r in subset)
        paid = sum(r['actually_called'] is True for r in subset)
        usage = [r['usage'] for r in subset if r['usage'] is not None]
        latency = sorted(r['latency_seconds'] for r in subset if r['latency_seconds'] is not None)
        cost = [r['charged_upper_cny'] for r in subset if r['charged_upper_cny'] is not None]
        ratio = lambda num, den: num / den if den else None
        g = dict(planned=n, completed=completed, **counts)
        for name, field, val in (
            ('paid_attempts_confirmed','actually_called',True), ('paid_attempts_uncertain','actually_called',None),
            ('local_attempts','local_attempted',True), ('responses_received','response_received',True),
            ('responses_unknown','response_received',None), ('responses_not_received','response_received',False),
            ('delivery_confirmed','upstream_delivery_known',True), ('delivery_unknown','upstream_delivery_known',None),
            ('delivery_not_attempted','upstream_delivery_known',False),
            ('normalized_responses_received','normalized_response_received',True)):
            g[name] = sum(r.get(field) is val for r in subset)
        g.update(completed_per_planned=ratio(completed,n), completed_per_paid_attempt=ratio(completed,paid),
                 legal_per_completed=ratio(counts['legal'],completed), correct_per_completed=ratio(counts['correct'],completed),
                 correct_per_planned=ratio(counts['correct'],n), reference_valid_per_completed=ratio(counts['reference_valid'],completed),
                 usage_known_rows=len(usage), usage_coverage_per_planned=ratio(len(usage),n),
                 prompt_tokens_mean_known=statistics.mean(u['prompt_tokens'] for u in usage) if usage else None,
                 completion_tokens_mean_known=statistics.mean(u['completion_tokens'] for u in usage) if usage else None,
                 latency_known_rows=len(latency), latency_median_seconds=statistics.median(latency) if latency else None,
                 latency_p95_nearest_rank_seconds=latency[math.ceil(.95*len(latency))-1] if latency else None,
                 cost_known_rows=len(cost), charged_upper_sum_known_cny=sum(cost) if cost else None,
                 status_counts=dict(sorted(Counter(r['status'] for r in subset).items())))
        groups[variant] = g
    return groups

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--formal-plan', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    run, formal_dir, out = [(ROOT / x).resolve() for x in (args.run,args.formal_plan,args.output)]
    if not out.is_relative_to(ROOT / 'evidence/qa') or out.exists():
        raise ValueError('NEW_QA_OUTPUT_REQUIRED')
    for p in (run,formal_dir):
        if not p.is_relative_to(ROOT/'experiments/runs'):
            raise ValueError('RUN_SCOPE_REQUIRED')
    def no_network(*a, **kw):
        raise RuntimeError('QA_NETWORK_FORBIDDEN')
    socket.create_connection = no_network
    socket.socket.connect = no_network
    from experiments.common import load, sha, baseline_binding, experiment_hashes, strict_load
    from experiments.plan import make_plan, input_for
    from experiments.judger import judge
    from experiments.summarize import calculate
    from backend.app.domain.models import GameState
    from backend.app.domain.rules import apply_action
    from jsonschema import Draft202012Validator
    checks=[]
    def check(name, value, details=None):
        checks.append(dict(name=name, passed=bool(value), details=details))
    watched = list(run.rglob('*')) + list(formal_dir.rglob('*'))
    watched = [p for p in watched if p.is_file()]
    before = {str(p.relative_to(ROOT)).replace('\\','/'):digest(p) for p in watched}
    source_before = experiment_hashes()
    binding = baseline_binding()
    check('baseline_binding',binding['manifest_raw_sha256']=='9c36943cbb6e4fe08b6e176445ba91835fafa79a2077c2155bbf8d613f8b07c1')
    manifest=load(run/'run.json'); phase=manifest['phase']; is_formal=phase=='formal'; expected_n=72 if is_formal else 6
    plan, formal, owner, saved = [load(p) for p in
        (run/'plan.json',formal_dir/'plan.json',run/('owner-formal-report.json' if is_formal else 'owner-pilot-report.json'),run/'summary.json')]
    rows=[strict_load(line) for line in (run/'raw.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    events=[strict_load(line) for line in (run/'journal.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    completion=load(run/'completion.json')
    check('real_manifest',manifest['mode']=='real' and phase in {'pilot','formal'} and manifest['planned']==expected_n)
    check('plan_exact_current',plan==make_plan(phase))
    check('plan_hash',sha(plan)==manifest['plan_hash']==saved['plan_hash'])
    check('freeze_binding',sha(plan['freeze'])==manifest['authorization']['freeze_hash'])
    check('formal_plan_exact_current',formal==make_plan('formal'))
    check('formal_freeze_same',formal['freeze']==plan['freeze'])
    check('planned_raw_identity_order', [r['row_id'] for r in rows]==[r['row_id'] for r in plan['rows']])
    check('raw_unique_complete',len(rows)==expected_n and len({r['row_id'] for r in rows})==expected_n)
    expected_stop='STOP_AFTER_UNKNOWN_TIMEOUT_OR_PROVIDER_ABNORMALITY' if is_formal else None
    check('completion_binding',completion['rows_hash']==sha(rows)==saved['rows_hash'] and completion['stop_reason']==expected_stop)
    for rel, expected in owner['artifact_hashes' if is_formal else 'files_sha256'].items():
        check('owner_file_hash:'+rel,digest((ROOT if is_formal else run)/rel)==expected)
    if is_formal:
        index_path=run/('owner-artifact-sha256-v2.json' if (run/'owner-artifact-sha256-v2.json').exists() else 'owner-artifact-sha256.json')
        index=load(index_path)
        for rel,expected in index['sha256'].items():
            check('owner_index:'+rel,digest(ROOT/rel)==expected)
        recovery=load(ROOT/'experiments/runs/20261005T052614Z-readonly-recovery/recovery-audit.json')
        check('owner_source_before_snapshot_matches',source_before==recovery['source_hashes_before']==plan['freeze']['source_hashes'])
        supplement=load(run/'source-timeout-accounting.json')
        check('supplement_not_paid_or_ledger_mutation',supplement['model_calls_added']==0 and supplement['env_read'] is False and supplement['ledger_mutated'] is False)
        check('supplement_original_plan_binding',supplement['source_comparison']['before_plan_canonical_hash']==sha(plan) and
              supplement['source_comparison']['before_plan_raw_sha256']==digest(run/'plan.json'))
        for rel,record in supplement['source_comparison']['files'].items():
            check('source_before_after:'+rel,record['before_from_original_plan_raw']==plan['freeze']['source_hashes'][rel] and
                  record['after_current_actual_raw']==digest(ROOT/rel)==record['before_from_original_plan_raw'] and record['equal'] is True)
        check('supplement_source_graph_complete',set(supplement['source_comparison']['files'])==set(source_before))
    input_records={}
    for label, directory, active_plan in ((phase+'run',run,plan),('formaldesign',formal_dir,formal)):
        check(label+'_input_cardinality', len(list((directory/'inputs').glob('*.json')))==active_plan['planned'])
        for r in active_plan['rows']:
            prefix=r['row_id']
            sample=load(ROOT/'experiments/fixtures'/ (r['sample_id']+'.json'))
            truth=load(ROOT/'experiments/ground_truth'/ (r['sample_id']+'.json'))
            inp=load(directory/'inputs'/ (prefix+'.json'))
            messages,tools,hashes=input_for(sample,r['variant'])
            check(prefix+':input_exact',inp==dict(messages=messages,tools=tools,**hashes))
            check(prefix+':plan_input_hashes',all(r[k]==v for k,v in hashes.items()))
            wire_tools=deepcopy(tools)
            for t in wire_tools: t['function'].pop('strict',None)
            wire_messages=[dict(role=m['role'],content=m['content']) for m in inp['messages']]
            wire=dict(model=r['requested_model'],messages=wire_messages,max_tokens=1000,
                      thinking={'type':'disabled'},stream=False,tools=wire_tools,tool_choice='none')
            raw_wire=json.dumps(wire,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
            check(prefix+':wire_hash',sha(raw_wire)==r['input_hash'] and len(raw_wire)==r['payload_utf8_bytes'])
            check(prefix+':max_reservation',r['input_token_bound']==len(raw_wire)*4+8192 and
                  r['reservation_units']==r['input_token_bound']*2000+1000*8000)
            context=json.loads(inp['messages'][1]['content'])
            if 'visible_history_summary' in context:
                packed=context['visible_history_summary']; history=[None]*packed['record_count']
                for group in packed['groups']:
                    for index,vals in zip(group['indices'],group['rows']): history[index]=dict(zip(group['fields'],vals))
            else: history=context['visible_history']
            check(prefix+':same_public_facts', context['visible_state']==sample['visible_state'] and
                  history==sample['visible_history'] and context['message']==sample['message'])
            check(prefix+':gold_sample_binding',truth['public_sample_hash']==sha(sample))
            check(prefix+':no_private_input_fields',set(context)<= {'message','visible_state','visible_history','visible_history_summary'})
            for action in truth['acceptable_actions']:
                state=GameState.model_validate(deepcopy(truth['state']))
                apply_action(state,action['tool'],deepcopy(action['arguments']))
            check(prefix+':frozen_gold_legal',bool(truth['acceptable_actions']))
            input_records[prefix]={**hashes,'input_file_raw_sha256':digest(directory/'inputs'/(prefix+'.json')),
                                   'gold_file_raw_sha256':digest(ROOT/'experiments/ground_truth'/(r['sample_id']+'.json'))}
    check('formal_72_36_each',formal['planned']==72 and Counter(r['variant'] for r in formal['rows'])=={'full_history':36,'structured_summary':36})
    check('formal_12x3_pairs',Counter((r['sample_id'],r['repeat']) for r in formal['rows'])=={(f'C{i:02}',rep):2 for i in range(1,13) for rep in range(1,4)})
    pairs=Counter('AB' if formal['rows'][i]['variant']=='full_history' else 'BA' for i in range(0,72,2))
    check('formal_AB_BA_18_each',pairs=={'AB':18,'BA':18})
    check('formal_no_retries_or_execution',formal['controls']['retry'] is False and formal['controls']['suggestions_executed'] is False)
    judgments=[]; total_units=0
    settled_units=0; unknown_units=0
    for r,p in zip(rows,plan['rows']):
        prefix=r['row_id']
        check(prefix+':identity_fields',all(r[k]==v for k,v in p.items() if k not in
              {'reported_model','status','error','start_time','end_time','latency_seconds','response','tool_proposal','usage','usage_known',
               'call_id','actually_called','provider_invoked','response_received','upstream_delivery_known','local_attempted',
               'http_status_code','normalized_response_received','charged_upper_cny','legal','correct','reference_valid','reference_sufficient'}))
        if r['status']!='completed':
            check(prefix+':unobserved_fields_null',all(r[k] is None for k in
                  ('response','tool_proposal','usage','reported_model','http_status_code','legal','correct','reference_valid','reference_sufficient')) and
                  r['usage_known'] is False and r['normalized_response_received'] is False)
            selected=[e for e in events if e['row_id']==prefix]
            if r['status']=='timeout':
                units=r['reservation_units']; total_units+=units; unknown_units+=units
                check(prefix+':timeout_keeps_uncertainty',r['error']=='MODEL_TIMEOUT' and r['actually_called'] is True and
                      r['provider_invoked'] is True and r['call_id'] is not None and r['response_received'] is None and
                      r['upstream_delivery_known'] is None and round(r['charged_upper_cny']*1e9)==units)
                check(prefix+':timeout_journal',len(selected)==2 and selected[0]['event']=='invocation_started' and
                      selected[1]['event']=='row_finalized' and selected[1]['row_hash']==sha(r))
            else:
                check(prefix+':not_called_kept',r['status']=='not_called' and r['actually_called'] is False and
                      r['provider_invoked'] is False and r['response_received'] is False and r['upstream_delivery_known'] is False and
                      r['call_id'] is None and r['charged_upper_cny'] is None and r['start_time'] is None and r['end_time'] is None and
                      r['latency_seconds'] is None and r['error']==expected_stop and not selected)
            judgments.append(dict(row_id=prefix,judgment=None,status=r['status'],usage_observed=False))
            continue
        sample=load(ROOT/'experiments/fixtures'/(r['sample_id']+'.json'))
        sample_before=sha(sample)
        judged=judge(r['response'],sample)
        check(prefix+':deterministic_repeat_no_mutation',judged==judge(r['response'],sample) and sha(sample)==sample_before)
        check(prefix+':judgment_matches',all(r[k]==judged[k] for k in ('legal','correct','reference_valid','reference_sufficient')) and
              r['error']==judged['reason'] and r['tool_proposal']==judged['next_action'])
        Draft202012Validator(load(ROOT/'experiments/schema.json')).validate(json.loads(r['response']))
        check(prefix+':actual_completed_known',r['status']=='completed' and r['actually_called'] is True and r['provider_invoked'] is True
              and r['http_status_code']==200 and r['response_received'] is True and r['normalized_response_received'] is True
              and r['upstream_delivery_known'] is True and r['usage_known'] is True and r['reported_model']=='deepseek-flash')
        u=r['usage']; units=(u['prompt_tokens']-u['prompt_cache_hit_tokens'])*2000+u['prompt_cache_hit_tokens']*40+u['completion_tokens']*8000
        check(prefix+':usage_arithmetic',u['total_tokens']==u['prompt_tokens']+u['completion_tokens'] and 0<=u['prompt_cache_hit_tokens']<=u['prompt_tokens'])
        check(prefix+':cost_known',round(r['charged_upper_cny']*1e9)==units)
        total_units+=units
        settled_units+=units
        selected=[e for e in events if e['row_id']==prefix]
        check(prefix+':journal_pair',len(selected)==2 and selected[0]['event']=='invocation_started' and selected[1]['event']=='row_finalized' and selected[1]['row_hash']==sha(r))
        judgments.append(dict(row_id=prefix,judgment=judged,cost_upper_units=units))
    c06=[r for r in rows if r['sample_id']=='C06']
    c06=[r for r in c06 if r['status']=='completed']
    check('C06_failures_preserved',len(c06)==2 and all(r['legal'] is True and r['correct'] is False and r['error']=='LEGAL_BUT_NOT_USEFUL_NEXT_ACTION' for r in c06))
    independent=summary_independent(rows)
    check('independent_summary_all_fields',independent==saved['by_variant'])
    check('owner_calculator_matches_independent',calculate(rows)['by_variant']==independent)
    check('summary_complete_identity',saved['row_count']==expected_n and saved['run_id']==manifest['run_id'] and
          saved['phase']==phase and saved['mode']=='real' and saved['baseline_unbound_prior_records']==binding['unbound_prior_source_records'])
    for variant in independent:
        g=independent[variant]
        expected_completed=11 if is_formal else 3; expected_correct=(8 if variant=='full_history' else 9) if is_formal else 2
        check(variant+':denominators',g['planned']==(36 if is_formal else 3) and g['completed']==g['legal']==g['usage_known_rows']==expected_completed and
              g['correct']==expected_correct and g['correct_per_planned']==expected_correct/g['planned'])
    check('phase_cost',total_units==(237496960 if is_formal else 29751520) and round(completion['phase_charged_upper_cny']*1e9)==total_units)
    ledger_path=(ROOT/'data/ai-budget.sqlite').resolve()
    with sqlite3.connect(ledger_path.as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        cap,frozen=db.execute('SELECT cap,frozen FROM budget_config WHERE id=1').fetchone()
        ledger_aggregate=[dict(x) for x in db.execute('SELECT state,COUNT(*) AS n,SUM(charged) AS charged FROM budget_calls GROUP BY state')]
        experiment_calls=[dict(x) for x in db.execute("SELECT id,scope,created_at,reserved,charged,state,reason,prompt_tokens,completion_tokens,cache_hit_tokens FROM budget_calls WHERE scope='experiments'")]
    ledger=dict(mode='ro',path='data/ai-budget.sqlite',cap_units=cap,frozen=bool(frozen),states=ledger_aggregate,experiment_calls=experiment_calls)
    for r in rows:
        if r['call_id'] is None:
            check(r['row_id']+':no_ledger_id',r['actually_called'] is False)
            continue
        matches=[c for c in experiment_calls if c['id']==r['call_id']]
        if r['status']=='timeout':
            check(r['row_id']+':unknown_original_ledger',len(matches)==1 and matches[0]['state']=='unknown' and
                  matches[0]['charged']==matches[0]['reserved']==r['reservation_units'] and
                  all(matches[0][k] is None for k in ('prompt_tokens','completion_tokens','cache_hit_tokens')))
            check(r['row_id']+':timeout_budget_creation_during_request',datetime.fromisoformat(r['start_time'])<=
                  datetime.fromisoformat(matches[0]['created_at'])<=datetime.fromisoformat(r['end_time']) and matches[0]['reason']=='MODEL_TIMEOUT')
            check(r['row_id']+':owner_supplement_original_ledger_match',matches[0]==supplement['original_ledger_timeout_safe'])
            continue
        check(r['row_id']+':original_ledger_match',len(matches)==1 and matches[0]['state']=='settled' and
              matches[0]['charged']==round(r['charged_upper_cny']*1e9) and matches[0]['reserved']==r['reservation_units'] and
              matches[0]['prompt_tokens']==r['usage']['prompt_tokens'] and matches[0]['completion_tokens']==r['usage']['completion_tokens'] and
              matches[0]['cache_hit_tokens']==r['usage']['prompt_cache_hit_tokens'])
    check('historical_ledger_owner_record',owner['shared_ledger_after']['state_counts']==({'settled':34,'unknown':1} if is_formal else {'settled':12}) and
          owner['shared_ledger_after']['charged_units']==(277602960 if is_formal else 40106000) and owner['shared_ledger_after']['frozen'] is False and
          owner['shared_ledger_after']['pending_or_unknown']==(1 if is_formal else 0))
    check('current_ledger_contains_pilot',sum(x['n'] for x in ledger_aggregate)>=12 and sum(x['charged'] for x in ledger_aggregate)>=40106000)
    check('ledger_owner_before_after_delta',owner['shared_ledger_before']['total_calls']==(12 if is_formal else 6) and owner['shared_ledger_after']['total_calls']==(35 if is_formal else 12) and
          owner['shared_ledger_after']['charged_units']-owner['shared_ledger_before']['charged_units']==total_units)
    if is_formal:
        check('current_original_ledger_35_known_unknown',ledger_aggregate==[{'state':'settled','n':34,'charged':114682960},{'state':'unknown','n':1,'charged':162920000}] and frozen==0)
        check('formal_terminal_counts',Counter(r['status'] for r in rows)=={'completed':22,'timeout':1,'not_called':49})
        check('formal_23_unique_attempts',sum(r['actually_called'] is True for r in rows)==23 and len({r['call_id'] for r in rows if r['call_id']})==23)
        check('formal_stopped_prefix',[r['status'] for r in rows]==['completed']*22+['timeout']+['not_called']*49)
        check('formal_journal_only_attempts',len(events)==46 and {e['row_id'] for e in events}=={r['row_id'] for r in rows[:23]})
        original_ids=[c['id'] for c in owner['shared_ledger_before']['experiment_calls']]
        for i,r in enumerate(rows[:23]):
            begin,end=[e for e in events if e['row_id']==r['row_id']]
            check(r['row_id']+':journal_original_call_prefix',begin['experiment_ids_before']==original_ids+[x['call_id'] for x in rows[:i]])
            check(r['row_id']+':time_order',datetime.fromisoformat(begin['at'])<=datetime.fromisoformat(r['end_time'])<=datetime.fromisoformat(end['at']))
        check('unknown_blocks_subsequent_paid_go',any(c['state']=='unknown' for c in experiment_calls) and all(r['actually_called'] is False for r in rows[23:]))
        check('formal_gate_finite_bound',manifest['authorization']['approved'] is True and manifest['authorization']['approved_by']=='Main' and
              manifest['authorization']['max_calls']==72 and manifest['authorization']['additional_upper_cap_units']==8000000000 and
              manifest['authorization']['pilot_review_accepted'] is True)
    pricing_path=ROOT/manifest['authorization']['pricing_evidence']
    pricing=load(pricing_path)
    check('price_bound_evidence',digest(pricing_path)==manifest['authorization']['pricing_sha256'] and pricing['peak_cny_per_million']=={'input_miss':2,'input_hit':.04,'output':8})
    process=load(run/'process-result.json')
    check('owner_real_process_record',process['actual_exit_code']==0 and process['retries']==0 and process['extra_probes']==0 and
          (process['planned']==72 and process['completed']==22 and process['timeout']==1 and process['not_called']==49 if is_formal else process['formal_called'] is False))
    comparison={}
    if is_formal:
        completed=[r for r in rows if r['status']=='completed']; paired=[]
        for sample in range(1,13):
            pair=[r for r in completed if r['sample_id']==f'C{sample:02}' and r['repeat']==1]
            if len(pair)==2:
                pair=sorted(pair,key=lambda r:r['variant'])
                paired.append(dict(sample_id=f'C{sample:02}',A_correct=pair[0]['correct'],B_correct=pair[1]['correct'],
                                   prompt_token_delta_B_minus_A=pair[1]['usage']['prompt_tokens']-pair[0]['usage']['prompt_tokens']))
        check('fully_observed_pairs11_prefix',len(paired)==11 and [p['sample_id'] for p in paired]==[f'C{i:02}' for i in range(1,12)])
        comparison['paired_completed']=paired
        comparison['paired_outcomes']=dict(Counter(('both_correct' if p['A_correct'] and p['B_correct'] else
                   'both_incorrect' if not p['A_correct'] and not p['B_correct'] else 'A_only_correct' if p['A_correct'] else 'B_only_correct') for p in paired))
        comparison['known_usage_totals']={k:sum(r['usage'][k] for r in completed) for k in ('prompt_tokens','completion_tokens','prompt_cache_hit_tokens','total_tokens')}
        for variant in independent:
            subset=[r for r in completed if r['variant']==variant]; stats={}
            for field in ('prompt_tokens','completion_tokens','prompt_cache_hit_tokens'):
                vals=sorted(r['usage'][field] for r in subset)
                stats[field]=dict(n=len(vals),mean=statistics.mean(vals),median=statistics.median(vals),p95_nearest_rank=vals[math.ceil(.95*len(vals))-1])
            vals=sorted(r['latency_seconds'] for r in subset)
            stats['completed_latency_seconds']=dict(n=len(vals),median=statistics.median(vals),p95_nearest_rank=vals[math.ceil(.95*len(vals))-1])
            stats['cache_hit_fraction_known']=sum(r['usage']['prompt_cache_hit_tokens'] for r in subset)/sum(r['usage']['prompt_tokens'] for r in subset)
            stats['settled_charge_known_cny']=sum(round(r['charged_upper_cny']*1e9) for r in subset)/1e9
            comparison[variant]=stats
    # Scan only authorized public experiment result artifacts, never environment or secrets.
    import re
    patterns=[r'(?i)bearer\s+[a-z0-9._-]{8,}',r'sk-[A-Za-z0-9_-]{16,}',r'(?i)"(?:api_key|session_token|authorization_header)"\s*:']
    leak_paths=[str(p.relative_to(ROOT)).replace('\\','/') for p in watched if any(re.search(pattern,p.read_text(encoding='utf-8')) for pattern in patterns)]
    check('public_result_secret_pattern_scan',not leak_paths,leak_paths)
    after={rel:digest(ROOT/rel) for rel in before}
    check('reviewed_artifacts_unchanged',before==after)
    check('experiment_sources_unchanged',source_before==experiment_hashes())
    check('baseline_still_bound',binding==baseline_binding())
    result=dict(task='T25-independent-formal-stopped-results' if is_formal else 'T23-independent-pilot-and-formal-design',created_at=datetime.now(timezone.utc).isoformat(),
                command=[sys.executable,*sys.argv],working_directory=str(ROOT),actual_paid_calls_by_qa=0,network_calls_by_qa=0,
                checks=len(checks),passed=sum(c['passed'] for c in checks),failures=[c for c in checks if not c['passed']],
                run_id=manifest['run_id'],plan_hash=sha(plan),freeze_hash=sha(plan['freeze']),formal_plan_hash=sha(formal),
                baseline_commit=binding['commit'],baseline_manifest_raw_sha256=binding['manifest_raw_sha256'],
                summary_independent=independent,phase_cost_upper_cny=total_units/1e9,formal_pair_order=dict(pairs),
                phase_settled_known_cny=settled_units/1e9,phase_unknown_reservation_upper_cny=unknown_units/1e9,comparison_descriptive_only=comparison,
                reviewed_artifact_hashes=before,experiment_source_hashes=source_before,
                real_process_evidence=process,ledger_readonly=ledger,
                limitations=[('Formal stopped after 23 paid attempts: 22 completed, 1 unknown timeout, 49 not called; not 72 successful model responses.' if is_formal else
                              'Formal 72-result audit is separate; this report audits only pilot results and formal frozen design. QA issues no paid GO.'),
                             'Supplier billing not independently verified; costs are shared-ledger conservative upper accounting.',
                             'Observed fixed-checkpoint prefix only; no statistical superiority or free-text hallucination certification.',
                             'Real process exit is Owner supplied process-result.json; QA directly observes only offline audit exit.',
                             'Secret scan checks explicit credential patterns without reading secret values; it is not exhaustive.',
                             'Baseline binding uses approved manifest and bytes; no Git command performed.'])
    dump(out/'checks.json',checks); dump(out/'judgments.json',judgments); dump(out/'result.json',result)
    print(json.dumps(dict(checks=result['checks'],passed=result['passed'],failed=len(result['failures']),output=str(out),
                         phase_cost_upper_cny=result['phase_cost_upper_cny'],formal_plan_hash=result['formal_plan_hash']),ensure_ascii=False))
    return 0 if not result['failures'] else 1

if __name__=='__main__':
    raise SystemExit(main())
