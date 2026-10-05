"""Independent T25 byte/lineage/statistics review; only archived v1 domain executes."""
import csv
import hashlib
import io
import json
import math
import pathlib
import statistics
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal

ROOT = pathlib.Path(__file__).resolve().parents[1]
OLD = '20261005T053334004502Z-formal-real-48d972eb'
NEW = '20261005T114740304313Z-continuation-real-b584e838'
MERGE = '20261005T115228Z-continuation-merged-owner'
ARCHIVE = ROOT / 'release/archives/baseline_v1'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def lines(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x]

def block_network():
    import socket
    def blocked(*args, **kwargs):
        raise RuntimeError('QA_OFFLINE_NETWORK_FORBIDDEN')
    socket.create_connection = blocked
    socket.socket.connect = blocked

def child():
    block_network()
    sys.path.insert(0, str(ARCHIVE))
    import copy
    from jsonschema import Draft202012Validator
    from backend.app.domain.models import GameState, RuleError
    from backend.app.domain.rules import apply_action
    index = load(ROOT / 'evidence/integration/E1-source-archive-20261005.json')
    modules = {}
    for name in sorted(n for n in sys.modules if n == 'backend' or n.startswith('backend.')):
        assert not any(part in name.split('.') for part in ('ai', 'api', 'storage', 'main'))
        p = pathlib.Path(sys.modules[name].__file__).resolve()
        logical = p.relative_to(ARCHIVE).as_posix()
        digest = sha(p.read_bytes())
        assert digest == index['sources'][logical]['raw_sha256']
        modules[name] = {'path': str(p), 'raw_sha256': digest}
    schema = load(ARCHIVE / 'experiments/schema.json')
    fixtures = {f'C{i:02}': load(ARCHIVE / f'experiments/fixtures/C{i:02}.json') for i in range(1, 13)}
    truths = {k: load(ARCHIVE / f'experiments/ground_truth/{k}.json') for k in fixtures}
    for k, truth in truths.items():
        assert sha(canon(fixtures[k])) == truth['public_sample_hash']
        for action in truth['acceptable_actions']:
            apply_action(GameState.model_validate(copy.deepcopy(truth['state'])), action['tool'], copy.deepcopy(action['arguments']))
    state, _ = apply_action(GameState.model_validate(truths['C10']['state']), 'use_item', {'item_id': 'emergency_key', 'target_id': 'r2_door'})
    assert 'emergency_key' in state.inventory and state.flags['r3_unlocked']
    results = []
    for row in json.load(sys.stdin):
        def pairs(items):
            result = {}
            for k, v in items:
                if k in result:
                    raise ValueError('DUPLICATE_JSON_KEY')
                result[k] = v
            return result
        value = json.loads(row['response'], object_pairs_hook=pairs, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
        Draft202012Validator(schema).validate(value)
        proposed = value['next_action']
        sample, truth = fixtures[row['sample_id']], truths[row['sample_id']]
        known = {c['clue_id'] for c in sample['visible_state']['clues']}
        valid = all(ref in known for ref in value['clue_refs'] + (proposed['clue_refs'] if proposed else []))
        legal = False
        if proposed:
            original = GameState.model_validate(copy.deepcopy(truth['state']))
            before = original.model_dump()
            try:
                apply_action(original.model_copy(deep=True), proposed['tool'], copy.deepcopy(proposed['arguments']))
                legal = True
            except RuleError:
                pass
            assert original.model_dump() == before
        action = {'tool': proposed['tool'], 'arguments': proposed['arguments']} if proposed else None
        required = set(truth['required_code_refs']) if proposed and proposed['tool'] == 'submit_code' else set()
        results.append({'row_id': row['row_id'], 'legal': legal, 'correct': bool(legal and action in truth['acceptable_actions']),
                        'reference_valid': valid, 'reference_sufficient': bool(proposed and valid and required <= set(proposed['clue_refs'])),
                        'tool_proposal': proposed})
    import importlib.metadata
    dependencies = {}
    for name in ('pydantic', 'jsonschema'):
        module = sys.modules[name]
        p = pathlib.Path(module.__file__)
        dependencies[name] = {'version': importlib.metadata.version(name), 'path': str(p), 'raw_sha256': sha(p.read_bytes())}
    print(json.dumps({'results': results, 'modules': modules, 'dependencies': dependencies, 'v1_key_retained': True, 'gold_actions_legally_checked': sum(len(t['acceptable_actions']) for t in truths.values())}, ensure_ascii=False))

def main():
    block_network()
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = ROOT / ('evidence/qa/T25-merged-' + timestamp)
    out.mkdir()
    failures, checks, paths, before = [], [], set(), {}
    def check(name, condition, detail=None):
        checks.append({'check': name, 'pass': bool(condition), 'detail': detail})
        if not condition:
            failures.append(name)
    def bind(relative, expected=None):
        p = ROOT / relative
        key = p.relative_to(ROOT).as_posix()
        paths.add(key)
        digest = sha(p.read_bytes()) if p.is_file() else None
        before.setdefault(key, digest)
        if expected is not None:
            check('raw_sha:' + key, digest == expected, {'expected': expected, 'actual': digest})
        return p
    m = ROOT / 'experiments/runs' / MERGE
    bind('tests/review_e1_merged_result.py')
    o, n = [ROOT / 'experiments/runs' / x for x in (OLD, NEW)]
    index = load(bind((m / 'artifact-sha256.json').relative_to(ROOT), '071aa2bcfa2a568eeffd28b0e21c9c7cdbb018a73deaeee4e2059fcb22c8b369'))
    for entry in index['artifacts']:
        p = bind(entry['path'], entry['raw_sha256'])
        check('artifact_size:' + entry['path'], p.stat().st_size == entry['bytes'])
    check('18_indexed_artifacts', len(index['artifacts']) == 18)
    ei, sm, lineage = [load(m / x) for x in ('evidence-index.json', 'source-map.json', 'lineage.json')]
    for name in ('original_artifact_raw_sha256', 'continuation_artifact_raw_sha256'):
        for p, digest in ei[name].items():
            base = o if name == 'original_artifact_raw_sha256' else n
            bind((base / p).relative_to(ROOT), digest)
    ai = load(bind('evidence/integration/E1-source-archive-20261005.json', sm['archive_precheck_actual']['archive_index_raw_sha256']))
    for logical, record in ai['sources'].items():
        bind(record['archive_path'], record['raw_sha256'])
        check('archive_alias:' + logical, sm['logical_v1_archive_aliases'][logical]['raw_sha256'] == record['raw_sha256'])
    check('101_archive_sources', len(ai['sources']) == 101)
    # Manifest is retained in immutable archive, rather than current release manifest.
    manifest_candidates = [p for p, v in ai['sources'].items() if v['raw_sha256'] == sm['archive_precheck_actual']['manifest_raw_sha256']]
    check('historical_manifest_index_binding', ai['baseline_manifest_raw_sha256'] == sm['archive_precheck_actual']['manifest_raw_sha256'], {'archive_materialized_candidates': manifest_candidates, 'limitation': 'Historical manifest pin binding checked; raw materialization not assumed.'})
    bind('evidence/integration/baseline_v1-manifest.json', sm['archive_precheck_actual']['manifest_raw_sha256'])
    for group, count in (('original41', 41), ('new5', 5)):
        check(group + '_count', len(sm[group]) == count)
        for logical, record in sm[group].items():
            bind(logical, record['before_sha256'])
            actual_path = ai['sources'][logical]['archive_path'] if logical in ai['sources'] else logical
            digest = sha(bind(actual_path).read_bytes())
            # Historical source hashes may use original CRLF bytes; archive alias pins normalized bytes.
            if logical in ai['sources']:
                check(group + '_historical_bind:' + logical, record['before_sha256'] == record['after_sha256'] and digest == ai['sources'][logical]['raw_sha256'])
            else:
                check(group + '_unchanged:' + logical, digest == record['before_sha256'] == record['after_sha256'])
    for logical, record in sm['canonical_paid_client'].items():
        bind(logical, record['raw_sha256'])
    for p, digest in sm['archive_precheck_actual']['original_evidence_raw_sha256'].items():
        bind(p, digest)
    for row in sm['v1_worker_actual_imports_by_completed_row']:
        for record in row['modules'].values():
            bind(record['file'], record['raw_sha256'])
    original, continuation, merged = [lines(p / 'raw.jsonl') for p in (o, n, m)]
    op, np = load(o / 'plan.json'), load(n / 'plan.json')
    check('72_unique_exact_plan_order', len(merged) == 72 and len({r['row_id'] for r in merged}) == 72 and [r['row_id'] for r in merged] == [r['row_id'] for r in op['rows']])
    check('raw_merged_byte_equal', (m/'raw.jsonl').read_bytes() == (m/'merged.jsonl').read_bytes())
    check('original23_objects_preserved', merged[:23] == original[:23])
    check('original22_responses_preserved', sum(r['status'] == 'completed' for r in original[:23]) == 22 and all(a['response'] == b['response'] for a,b in zip(merged[:23], original[:23])))
    check('new49_exact_plan', np['rows'] == op['rows'][23:] and len(continuation) == 49 and merged[23:] == continuation)
    check('new_plan_identity', np['original_plan_hash'] == sha(canon(op)) and np['original_freeze'] == op['freeze'] and np['retry'] is False and np['one_continuation_per_origin'] is True)
    immutable = ('row_id','order','sample_id','repeat','variant','commit','level_version','schema_version','prompt_version','context_version','judger_version','provider','model','requested_model','base_url','input_hash','payload_utf8_bytes','input_token_bound','reservation_units','visible_facts_hash')
    for row, plan, binding, link in zip(merged, op['rows'], ei['unit_input_bindings'], lineage['units']):
        rid = row['row_id']
        check('plan_fields:' + rid, all(row[k] == plan[k] for k in immutable))
        p = bind(binding['original_input_path'], binding['original_input_raw_sha256'])
        payload = load(p)
        tools = load(ARCHIVE / 'contracts/tools.json')
        check('saved_tools_values:' + rid, tools == payload['tools'])
        for tool in tools:
            tool['function'].pop('strict', None)
        wire = {'model': row['requested_model'], 'messages': [{k: msg[k] for k in ('role','content')} for msg in payload['messages']], 'max_tokens': 1000, 'thinking': {'type':'disabled'}, 'stream': False, 'tools': tools, 'tool_choice':'none'}
        raw = json.dumps(wire, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        check('wire:' + rid, sha(raw) == row['input_hash'] == payload['input_hash'] and len(raw) == row['payload_utf8_bytes'] and row['input_token_bound'] == 4*len(raw)+8192 and row['reservation_units'] == row['input_token_bound']*2000+8000000)
        user = json.loads(payload['messages'][1]['content'])
        fixture = load(ARCHIVE / ('experiments/fixtures/' + row['sample_id'] + '.json'))
        if 'visible_history_summary' in user:
            compact = user['visible_history_summary']; expanded = [None] * compact['record_count']
            for group in compact['groups']:
                for i, values in zip(group['indices'], group['rows']):
                    assert expanded[i] is None
                    expanded[i] = dict(zip(group['fields'], values))
        else:
            expanded = user['visible_history']
        check('visible_facts:' + rid, user['message'] == fixture['message'] and user['visible_state'] == fixture['visible_state'] and expanded == fixture['visible_history'])
        if binding['continuation_input_path']:
            p2 = bind(binding['continuation_input_path'], binding['continuation_input_raw_sha256'])
            check('input_copy:' + rid, p.read_bytes() == p2.read_bytes())
        origin_row = original[row['order']-1]
        selected = OLD if row['order'] <= 23 else NEW
        check('lineage:' + rid, link['row_id'] == rid and link['original_row_hash'] == sha(canon(origin_row)) and link['selected_result_row_hash'] == sha(canon(row)) and link['actual_attempt_count'] == int(row['actually_called']) and link['selected_result_run_id'] == selected)
    journal = lines(n / 'journal.jsonl')
    started = [j for j in journal if j.get('event') == 'invocation_started']
    finalized = [j for j in journal if j.get('event') == 'row_finalized']
    check('48_network_attempts_47_responses', len(started) == len(finalized) == 48 and sum(r['actually_called'] for r in continuation) == 48 and sum(r['response_received'] is True for r in continuation) == 47)
    check('started_exact48_order_inputs', [(j['row_id'],j['input_hash']) for j in started] == [(r['row_id'],r['input_hash']) for r in continuation[:48]])
    check('finalized_exact48_rowhashes', [(j['row_id'],j['row_hash']) for j in finalized] == [(r['row_id'],sha(canon(r))) for r in continuation[:48]])
    completion = load(n/'completion.json')
    check('continuation_completion_hash', completion['rows_hash'] == sha(canon(continuation)) and completion['real'] is True and completion['planned'] == 49)
    check('69complete_1timeout_1failed_1notcalled', Counter(r['status'] for r in merged) == Counter(completed=69,timeout=1,failed=1,not_called=1))
    check('failure_nulls_preserved', all(all(r[k] is None for k in ('usage','response','reported_model','legal','correct','reference_valid','reference_sufficient','tool_proposal')) for r in merged if r['status'] != 'completed'))
    check('MODEL_UNAVAILABLE_unknown', merged[70]['error'] == 'MODEL_UNAVAILABLE' and merged[70]['actually_called'] is True and merged[70]['response_received'] is None and merged[71]['actually_called'] is False)
    completed = [r for r in merged if r['status']=='completed']
    child_command = [sys.executable,'-B','-X','utf8',str(pathlib.Path(__file__).resolve()),'--v1-judge-child']
    result = subprocess.run(child_command, input=json.dumps(completed,ensure_ascii=False), text=True, encoding='utf-8', capture_output=True, cwd=ARCHIVE)
    (out/'v1-judge-stderr.txt').write_text(result.stderr,encoding='utf-8')
    child_result = json.loads(result.stdout) if result.returncode == 0 else None
    (out/'v1-judge.json').write_text(json.dumps({'command':child_command,'cwd':str(ARCHIVE),'exit_code':result.returncode,'result':child_result},ensure_ascii=False,indent=2),encoding='utf-8')
    check('69_independent_v1_rejudged', result.returncode == 0 and len(child_result['results']) == 69 if child_result else False)
    if child_result:
        for row, judged in zip(completed, child_result['results']):
            check('v1_judgment:' + row['row_id'], all(row[k] == judged[k] for k in ('row_id','legal','correct','reference_valid','reference_sufficient','tool_proposal')))
    summary = load(m/'summary.json')
    check('summary_binding', summary['rows_hash'] == sha(canon(merged)) and summary['row_count'] == summary['planned'] == 72 and summary['synthetic'] is False)
    summary_csv = list(csv.DictReader((m/'summary.csv').open(encoding='utf-8-sig',newline='')))
    def numeric(a,b):
        return math.isclose(float(a),float(b),rel_tol=1e-11,abs_tol=1e-10)
    def cost(row):
        u=row['usage'];h=u.get('prompt_cache_hit_tokens',0)
        return Decimal((u['prompt_tokens']-h)*2000+h*40+u['completion_tokens']*8000)/Decimal(10**9)
    total_known = sum((cost(r) for r in completed),Decimal(0))
    unknown = sum((Decimal(str(r['charged_upper_cny'])) for r in merged if r['actually_called'] and not r['usage_known']),Decimal(0))
    check('formal_cost_bound_not_invoice', total_known == Decimal('0.15139984') and unknown == Decimal('0.257456') and total_known+unknown == Decimal('0.40885584'))
    for r in completed:
        check('known_cost:' + r['row_id'], numeric(cost(r),r['charged_upper_cny']))
    expected_counts = {'full_history':(36,36,34,26),'structured_summary':(36,35,35,29)}
    for record in summary_csv:
        v=record['variant'];rs=[r for r in merged if r['variant']==v];cs=[r for r in rs if r['status']=='completed'];paid=[r for r in rs if r['actually_called']]
        counts=(len(rs),len(paid),len(cs),sum(r['correct'] is True for r in cs))
        check('variant_counts:'+v,counts == expected_counts[v])
        lat=sorted(r['latency_seconds'] for r in rs if r['latency_seconds'] is not None)
        values={'planned':len(rs),'paid_attempts_confirmed':len(paid),'completed':len(cs),'correct':counts[3], 'completed_per_planned':len(cs)/len(rs),'completed_per_paid_attempt':len(cs)/len(paid),'correct_per_completed':counts[3]/len(cs),'correct_per_planned':counts[3]/len(rs),'latency_known_rows':len(lat),'latency_median_seconds':statistics.median(lat),'latency_p95_nearest_rank_seconds':lat[math.ceil(.95*len(lat))-1], 'prompt_tokens_mean_known':statistics.mean(r['usage']['prompt_tokens'] for r in cs),'completion_tokens_mean_known':statistics.mean(r['usage']['completion_tokens'] for r in cs),'known_usage_settled_charge_cny':sum((cost(r) for r in cs),Decimal(0)), 'unknown_usage_retained_upper_cny':sum((Decimal(str(r['charged_upper_cny'])) for r in paid if not r['usage_known']),Decimal(0))}
        for k,value in values.items():
            check('summary_csv:'+v+':'+k,numeric(record[k],value))
            if k in summary['by_variant'][v]:
                check('summary_json:'+v+':'+k,numeric(summary['by_variant'][v][k],value))
        check('summary_csv_flags:'+v,all(int(record[k])==sum(r[k] is True for r in cs) for k in ('legal','reference_valid','reference_sufficient')))
        more = {'charged_upper_sum_known_cny':sum((Decimal(str(r['charged_upper_cny'])) for r in paid),Decimal(0)), 'cost_known_rows':len(paid),'delivery_confirmed':sum(r['upstream_delivery_known'] is True for r in rs),'delivery_not_attempted':sum(not r['actually_called'] for r in rs),'delivery_unknown':sum(r['actually_called'] and r['upstream_delivery_known'] is None for r in rs),'local_attempts':sum(r['local_attempted'] for r in rs),'normalized_responses_received':sum(r['normalized_response_received'] for r in rs),'paid_attempts_uncertain':0,'responses_not_received':sum(r['response_received'] is False for r in rs),'responses_received':sum(r['response_received'] is True for r in rs),'responses_unknown':sum(r['response_received'] is None for r in rs),'usage_coverage_per_planned':len(cs)/len(rs),'usage_known_rows':len(cs),'legal_per_completed':sum(r['legal'] is True for r in cs)/len(cs),'reference_valid_per_completed':sum(r['reference_valid'] is True for r in cs)/len(cs)}
        for k,value in more.items():
            check('summary_all:'+v+':'+k,numeric(record[k],value) and numeric(summary['by_variant'][v][k],value))
        statuses = Counter(r['status'] for r in rs)
        check('summary_statuses:'+v, summary['by_variant'][v]['status_counts']==dict(statuses) and all(int(record[k]) == statuses[k] for k in ('timeout','failed','not_called')))
    pairs={(r['sample_id'],r['repeat']) for r in merged}
    fullpairs=sum(all(r['status']=='completed' for r in merged if (r['sample_id'],r['repeat'])==p) for p in pairs)
    check('34_full_pairs_of36',len(pairs)==36 and fullpairs==34)
    phase = load(m/'phase-metrics.json')
    for filename, key in (('usage-cache-by-phase.csv','usage_cache'),('latency-by-phase.csv','latency')):
        data=list(csv.DictReader((m/filename).open(encoding='utf-8-sig',newline='')))
        check('phase_json_csv:'+key,len(data)==len(phase[key]) and all(all(str(actual[k])==str(value) if isinstance(value,str) else str(actual[k])==str(value) if isinstance(value,bool) else numeric(actual[k],value) for k,value in expected.items()) for actual,expected in zip(data,phase[key])))
    for record in csv.DictReader((m/'usage-cache-by-phase.csv').open(encoding='utf-8-sig',newline='')):
        batch=original if record['batch']==OLD else continuation;rs=[r for r in batch if r['variant']==record['variant']];cs=[r for r in rs if r['usage_known']]
        prompt=sum(r['usage']['prompt_tokens'] for r in cs);cache=sum(r['usage'].get('prompt_cache_hit_tokens',0) for r in cs)
        values={'planned_in_batch':len(rs),'usage_known_rows':len(cs),'prompt_tokens_known':prompt,'completion_tokens_known':sum(r['usage']['completion_tokens'] for r in cs),'cache_hit_tokens_known':cache,'cache_hit_fraction_known_input':cache/prompt,'known_charge_cny':sum((cost(r) for r in cs),Decimal(0)),'unknown_usage_retained_upper_cny':sum((Decimal(str(r['charged_upper_cny'])) for r in rs if r['actually_called'] and not r['usage_known']),Decimal(0))}
        for k,v in values.items():check('phase_usage:'+record['batch']+':'+record['variant']+':'+k,numeric(record[k],v))
    for record in csv.DictReader((m/'latency-by-phase.csv').open(encoding='utf-8-sig',newline='')):
        batch=original if record['batch']==OLD else continuation
        vals=sorted(r[record['metric']] for r in batch if r['variant']==record['variant'] and r.get(record['metric']) is not None)
        check('phase_latency:'+record['batch']+':'+record['variant']+':'+record['metric'], int(record['known_attempt_rows'])==len(vals) and numeric(record['median_seconds'],statistics.median(vals)) and numeric(record['p95_nearest_rank_seconds'],vals[math.ceil(.95*len(vals))-1]))
    check('phase_costs', numeric(summary['phase_costs']['original_charged_upper_cny'],sum(r['charged_upper_cny'] or 0 for r in original)) and numeric(summary['phase_costs']['continuation_charged_upper_cny'],sum(r['charged_upper_cny'] or 0 for r in continuation)))
    # Current accounting is a separate time-stamped read-only observation; no original row is rewritten.
    import sqlite3
    ledger_path = ROOT / 'data/ai-budget.sqlite'
    ledger_at = datetime.now(timezone.utc).isoformat()
    connection = sqlite3.connect(ledger_path.as_uri()+'?mode=ro',uri=True)
    connection.execute('PRAGMA query_only=ON')
    count, charged = connection.execute('SELECT COUNT(*),SUM(charged) FROM budget_calls').fetchone()
    pending = connection.execute("SELECT id,scope,state,reason,reserved,charged FROM budget_calls WHERE state NOT IN ('settled','released') ORDER BY created_at").fetchall()
    calls = connection.execute('SELECT id,state,reason,reserved,charged,prompt_tokens,completion_tokens,cache_hit_tokens FROM budget_calls WHERE id IN (?,?)', (merged[22]['call_id'],merged[70]['call_id'])).fetchall()
    connection.close()
    historical = load(m/'accounting-notes.json')
    ledger_observation = {'at_utc':ledger_at,'mode':'sqlite URI mode=ro plus query_only=ON','total_calls':count,'charged_upper_units':charged,'charged_upper_cny':str(Decimal(charged)/Decimal(10**9)),'pending_safe_fields':pending,'two_formal_failure_calls_safe_fields':calls,'historical_owner_at_utc':historical.get('at_utc',historical.get('at')),'historical_owner_snapshot':{k:v for k,v in historical['ledger_snapshot'].items() if k!='experiment_calls'}}
    (out/'ledger-observation.json').write_text(json.dumps(ledger_observation,ensure_ascii=False,indent=2),encoding='utf-8')
    after={p:sha((ROOT/p).read_bytes()) if (ROOT/p).is_file() else None for p in sorted(paths)}
    check('all_read_sources_unchanged',before==after,{'count':len(before)})
    report={'kind':'T25-independent-merged-QA','at_utc':datetime.now(timezone.utc).isoformat(),'command':[sys.executable,'-B','-X','utf8','tests/review_e1_merged_result.py'],'exit_code':int(bool(failures)),'checks':checks,'failures':failures,'source_before':before,'source_after':after,'counts':{v:expected_counts[v] for v in expected_counts},'full_pairs':fullpairs,'independent_v1_rejudged':len(child_result['results']) if child_result else 0,'known_usage_charge_cny':str(total_known),'unknown_usage_retained_upper_cny':str(unknown),'formal_upper_cny':str(total_known+unknown),'owner_process_record':load(m/'process-result.json'),'limits':['No paid calls, provider import, network, env read, ledger write, or current v2 execution.','Owner historical ledger snapshot is not current accounting.','Batch/time/cache/missing-pair effects prevent causal B-superiority conclusions.']}
    (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'evidence':str(out),'exit_code':report['exit_code'],'failures':failures,'checks':len(checks),'sources':len(before),'v1_rejudged':report['independent_v1_rejudged']},ensure_ascii=False))
    return report['exit_code']

if __name__ == '__main__':
    if '--v1-judge-child' in sys.argv:
        child()
    else:
        sys.exit(main())
