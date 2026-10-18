"""Read-only first actual batch audit; semantic judgments are explicit below."""
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = 'evidence/integration/ai-companion-quality/'


def read(p):
    return json.loads((ROOT / p).read_text(encoding='utf-8-sig'))


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def main():
    summary = read(BASE + 'paid-summary.json')
    path = summary['result_path']
    result = read(path)
    folder = str(Path(path).parent).replace('\\', '/')
    issues = []
    def ensure(ok, message):
        if not ok: issues.append(message)
    ensure(sha(path) == summary['result_sha256'], 'result-summary hash')
    ensure(result['source_sha256'] == read(BASE + 'candidate.json')['source_sha256'], 'frozen source batch')
    ensure(result['source_matches_prepared'] is True, 'preview source match')
    for p, h in result['artifact_sha256'].items():
        ensure(sha(p) == h, 'artifact: ' + p)
    ensure(result['actual_provider_dispatches'] == summary['actual_provider_dispatches'] == 3, 'actual dispatch count')
    before, after = result['before_budget'], result['after_budget']
    delta = Decimal(str(after['charged_upper_cny'])) - Decimal(str(before['charged_upper_cny']))
    ensure(delta == Decimal(str(summary['actual_charged_cny'])) == Decimal('0.00740048'), 'charged upper summary arithmetic')
    ensure(before['unknown_or_pending_calls'] == after['unknown_or_pending_calls'] == 2 and result['new_unknown_count'] == 0, 'unknown unchanged')
    ensure(not before['frozen'] and not after['frozen'] and result['historical_unknown_retried'] is False, 'no freeze/history retry')
    assessments = {
        'Q01': {'relevance': 'pass_in_raw', 'factual_grounding': 'pass_in_raw', 'useful_partial_guidance': 'pass_in_raw',
                'no_complete_solution': 'pass_in_raw', 'natural_non_template': 'pass_in_raw', 'followup_coherence': 'not_applicable',
                'delivery': 'fail_non_JSON_stopped', 'overall': 'failed_delivery',
                'basis': 'Raw explains input accepted versus door physically closed and allows other visible objects; strict JSON failure means player only sees generic stopped text.'},
        'Q02': {'relevance': 'not_tested', 'factual_grounding': 'not_tested', 'useful_partial_guidance': 'not_tested',
                'no_complete_solution': 'not_tested', 'natural_non_template': 'not_tested', 'followup_coherence': 'not_tested',
                'delivery': 'skipped_parent_stopped', 'overall': 'no_actual_followup_evidence', 'basis': 'Q01 was not accepted; parent skip policy correctly dispatches zero.'},
        'Q03': {'relevance': 'pass_in_raw', 'factual_grounding': 'pass_in_raw', 'useful_partial_guidance': 'pass_in_raw',
                'no_complete_solution': 'pass_in_raw', 'natural_non_template': 'pass_in_raw', 'followup_coherence': 'not_applicable',
                'delivery': 'fail_non_JSON_stopped', 'overall': 'failed_delivery',
                'basis': 'Raw describes adjacent reciprocal ports without rotations/full layout, but non-JSON fails delivery and player only sees generic stopped text.'},
        'Q04': {'relevance': 'weak', 'factual_grounding': 'fail', 'useful_partial_guidance': 'weak',
                'no_complete_solution': 'pass', 'natural_non_template': 'weak', 'followup_coherence': 'not_applicable',
                'delivery': 'displayed', 'overall': 'unsupported_relation_and_regressive_focus',
                'basis': 'Opening recognizes login passed and record unread; later suggests date/number relation between maintenance label, service note and unread record without any evidence of such relation, then returns to the completed login identity issue. Visible/discovered objects alone do not support this connection; empty refs do not validate prose.'}}
    records = []
    for case in result['case_results']:
        cid = case['case_id']
        record = {'case_id': cid, 'assessment': assessments[cid], 'question': case.get('question'), 'dispatches': case['provider_dispatches']}
        if case.get('skipped'):
            ensure(cid == 'Q02' and case['provider_dispatches'] == 0, 'skip case')
            record['skip_reason'] = case['skipped']
        else:
            provider_path = folder + '/' + cid + '-provider.json'
            provider = read(provider_path)
            raw = provider['raw_content']
            try:
                value = json.loads(raw)
                valid_json = isinstance(value, dict)
            except ValueError:
                value, valid_json = None, False
            displayed = case['response']['data']
            ensure(case['provider_dispatches'] == 1, cid + ' single call')
            ensure(valid_json == (cid == 'Q04'), cid + ' exact JSON classification')
            ensure(case['hint_count_delta'] == case['revision_delta'] == (1 if cid == 'Q04' else 0), cid + ' count/revision delta')
            ensure(displayed['status'] == ('no_suggestion' if cid == 'Q04' else 'stopped'), cid + ' display status')
            if cid == 'Q04': ensure(displayed['answer'] == value['answer'] and displayed['clue_refs'] == [], 'Q04 exact raw/display')
            record.update(raw_provider_path=provider_path, raw_content=raw, JSON_object=valid_json,
                          displayed_answer=displayed['answer'], status=displayed['status'], stop_reason=displayed['stop_reason'],
                          hint_count_delta=case['hint_count_delta'], revision_delta=case['revision_delta'])
        records.append(record)
    payload = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'command': [sys.executable, '-B', '-X', 'utf8', *sys.argv],
               'audit_exit_code': 0 if not issues else 1, 'audit_issues': issues,
               'semantic_verdict': 'NOT_ACCEPTED_needs_narrow_fix_preserve_first_batch',
               'result': path, 'result_sha256': sha(path), 'artifact_files_checked': len(result['artifact_sha256']),
               'actual_dispatches': 3, 'displayed_model_replies': 1, 'blocked_non_JSON': 2, 'skipped_followup': 1,
               'charge_upper_cny': str(delta), 'budget_cumulative_upper_cny': str(after['charged_upper_cny']),
               'budget_remaining_cny': str(after['remaining_cny']), 'unknown_before_after': [2, 2],
               'QA_paid_calls': 0, 'QA_canonical_budget_access': False, 'cases': records,
               'required_fix': ['Preserve strict schema rejection; improve provider-side JSON compliance without silently wrapping raw prose.',
                                'Constrain inferred relations to provided supporting facts; known visibility alone is insufficient.',
                                'Keep successful login acknowledged and ground the explanation in current unread-record feedback.'],
               'limitations': ['Three actual calls, one displayed model reply; no real followup answer occurred.',
                               'Audit exit0 means records/hash/arithmetic consistent, not semantic quality accepted.',
                               'No paid retries, provider judge, UI/build or human experience claim.']}
    (ROOT / BASE / 'qa/first-retest-review.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'audit_exit_code': payload['audit_exit_code'], 'issues': issues, 'semantic_verdict': payload['semantic_verdict'], 'artifact_files_checked': payload['artifact_files_checked']}))
    return payload['audit_exit_code']


if __name__ == '__main__':
    sys.exit(main())
