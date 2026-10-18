"""Static review of Main's four-call preview; never import its paid executor."""
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import ast
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'evidence/integration/ai-companion-quality/qa'


def read(p):
    return json.loads((ROOT / p).read_text(encoding='utf-8-sig'))


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def main():
    candidate_path = 'evidence/integration/ai-companion-quality/candidate.json'
    preview_path = 'evidence/integration/ai-companion-quality/paid/payload-preview.json'
    wrapper_path = 'evidence/integration/ai-companion-quality/run_retest.py'
    sealed_path = 'evidence/integration/ai-companion-real/run_playtest.py'
    candidate, preview = read(candidate_path), read(preview_path)
    checks = []
    def check(name, condition):
        checks.append({'check': name, 'passed': bool(condition)})
    source = candidate['source_sha256']
    check('preview-exact-frozen-source', preview['baseline_source_sha256'] == source)
    check('current-243-source-match', len(source) == 243 and all(sha(p) == h for p, h in source.items()))
    check('sealed-executor-unchanged', sha(sealed_path) == preview['executor_sha256'])
    check('fixed-official-model-endpoint', preview['model'] == 'deepseek-flash' and preview['endpoint'] == 'https://api.deepseek.com/chat/completions')
    tree = ast.parse((ROOT / wrapper_path).read_text(encoding='utf-8-sig'))
    assignments = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Attribute):
            if isinstance(node.targets[0].value, ast.Name) and node.targets[0].value.id == 'executor' and node.targets[0].attr in {'LIMIT', 'CASES'}:
                assignments[node.targets[0].attr] = ast.literal_eval(node.value)
    check('four-cases-round-cap-no-retry', len(assignments['CASES']) == preview['maximum_real_calls'] == 4 and assignments['LIMIT'] == preview['round_limit_cny'] == .30 and preview['no_retries'] is True)
    check('single-executor-call-site', sum(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == 'executor' and n.func.attr == 'execute' for n in ast.walk(tree)) == 1)
    check('reservation-upper-in-cap', sum(Decimal(str(c['offline_bound_cny'])) for c in preview['cases']) <= Decimal('.30'))
    historical = read('evidence/integration/ai-companion-real/20261018T110144068872Z-real/result.json')
    states = {c['case_id']: c['before_public'] for c in historical['case_results'] if 'before_public' in c}
    states['C08'] = read('evidence/integration/ai-companion-real/targeted/20261018T111212456755Z-real/result.json')['case_results'][0]['before_public']
    mapping = {'Q01': 'C08', 'Q02': 'C08', 'Q03': 'C05', 'Q04': 'C06'}
    for case, definition in zip(preview['cases'], assignments['CASES']):
        cid, prefix, kind, question = definition
        body = case['body']
        context = json.loads(next(m['content'] for m in body['messages'] if m['role'] == 'user'))
        state = states[mapping[cid]]
        text = json.dumps(context, ensure_ascii=False)
        check(cid + '-ordinary-question-route-match', case['case_id'] == cid and case['legal_route_prefix'] == prefix and context['question'] == question)
        check(cid + '-full-public-catalog', {o['name'] for o in context['visible_object_catalog']} == {o['name'] for o in state['objects']})
        known = {c['clue_id']: {k: c[k] for k in ('clue_id', 'title', 'text')} for c in state['clues']}
        check(cid + '-evidence-previously-discovered', all(c == known.get(c['clue_id']) for c in context['known_evidence']))
        check(cid + '-procedural-refs-empty', context['allowed_clue_refs'] == [])
        check(cid + '-no-internal-codes-or-object-id-fields', all(s not in text for s in ('CODE_ACCEPTED', 'STRIP_INSERTED', 'UNLOCKED', '"object_id"', '"target_id"', '"item_id"', '"module_id"', '"r1_cabinet"', '"r2_monitor"')))
        check(cid + '-no-complete-solution-or-private-history', all(s not in text for s in ('4217', '2117', '4792', 'r1_photo', '柜底凹槽', 'session_id', 'api_key', 'session_token')))
        check(cid + '-no-tools-fixed-600', 'tools' not in body and body['max_tokens'] == 600 and body['stream'] is False)
        if cid == 'Q02':
            check('Q02-history-placeholder-explicit', len(context['recent_history']) == 1 and context['recent_history'][0]['question'] == assignments['CASES'][0][3] and 'actual accepted Q01' in context['recent_history'][0]['answer'])
    issue = [c['check'] for c in checks if not c['passed']]
    payload = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'command': [sys.executable, '-B', '-X', 'utf8', *sys.argv],
               'exit_code': 0 if not issue else 1, 'verdict': 'preflight_GO_not_quality_acceptance' if not issue else 'needs_review',
               'checks': checks, 'issues': issue, 'sha256': {p: sha(p) for p in (candidate_path, preview_path, wrapper_path, sealed_path)},
               'reservation_upper_cny_preview': str(sum(Decimal(str(c['offline_bound_cny'])) for c in preview['cases'])),
               'paid_calls': 0, 'canonical_budget_access': False,
               'static_executor_review': ['Sealed executor checks source equality before credentials and every dispatch reserve versus mutable LIMIT=.30; no retry loop.',
                   'Four CASES with one Runtime attempt each; Q02 uses actual accepted Q01 in same session and skips when Q01 is stopped.',
                   'New unknown/freeze/potential full-solution stops execution; old unknown calls never replayed.',
                   'Q02 placeholder reservation is only preview; executor recalculates actual payload bound with actual accepted history before dispatch.'],
               'limitations': ['This is offline preflight, not model-output quality. Actual raw/displayed replies require independent six-axis review.',
                   'Old executor wider authorization wording remains historical; new wrapper four/.30 assertions and actual summaries govern this run.']}
    (OUT / 'preflight-review.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'exit_code': payload['exit_code'], 'checks': len(checks), 'issues': issue, 'reservation_upper_cny_preview': payload['reservation_upper_cny_preview']}))
    return payload['exit_code']


if __name__ == '__main__':
    sys.exit(main())
