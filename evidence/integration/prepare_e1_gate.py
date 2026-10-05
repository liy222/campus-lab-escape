"""Main finite E1 authorization writer; no credentials, transport or paid calls."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3

from experiments.common import ROOT, HOME, encoded, load, sha, baseline_binding
from experiments.plan import make_plan


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['pilot', 'formal'], required=True)
    parser.add_argument('--qa-result', required=True)
    parser.add_argument('--cap-units', type=int, required=True)
    parser.add_argument('--pilot-run-id')
    parser.add_argument('--pricing-evidence', default='evidence/integration/pricing-check-20261002T120000Z.json')
    args = parser.parse_args()
    qa_path = (ROOT / args.qa_result).resolve()
    if not qa_path.is_relative_to((ROOT / 'evidence/qa').resolve()):
        raise ValueError('QA_PATH_OUTSIDE_APPROVED_ROOT')
    qa = load(qa_path)
    if qa.get('passed') is not True or qa.get('failed') or not qa.get('checks'):
        raise ValueError('INDEPENDENT_QA_NOT_PASSED')
    if qa['source_before'] != qa['source_after']:
        raise ValueError('QA_SOURCE_CHANGED')
    for relative, digest in qa['source_after'].items():
        if sha((ROOT / relative).read_bytes()) != digest:
            raise ValueError('REVIEWED_SOURCE_CHANGED:' + relative)
    baseline_binding()
    plan = make_plan(args.phase)
    if not 0 < args.cap_units <= 10_000_000_000:
        raise ValueError('FINITE_CAP_REQUIRED')
    pricing_path = (ROOT / args.pricing_evidence).resolve()
    if not pricing_path.is_relative_to((ROOT / 'evidence/integration').resolve()):
        raise ValueError('PRICING_OUTSIDE_MAIN_REGISTRATION')
    pricing = load(pricing_path)
    now = datetime.now(timezone.utc)
    age = (now - datetime.fromisoformat(pricing['checked_at_utc'].replace('Z', '+00:00'))).total_seconds()
    if not 0 <= age <= 86400 or pricing['peak_cny_per_million'] != {'input_miss': 2, 'input_hit': .04, 'output': 8}:
        raise ValueError('FRESH_PRICING_REQUIRED')
    db_path = (ROOT / 'data/ai-budget.sqlite').resolve()
    with sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True) as db:
        cap, frozen = db.execute('SELECT cap,frozen FROM budget_config WHERE id=1').fetchone()
        charged, count = db.execute('SELECT COALESCE(SUM(charged),0),COUNT(*) FROM budget_calls').fetchone()
        pending = db.execute("SELECT COUNT(*) FROM budget_calls WHERE state IN ('reserved','unknown')").fetchone()[0]
    if cap != 10_000_000_000 or frozen or pending or charged + args.cap_units > cap:
        raise ValueError('SHARED_BUDGET_NOT_READY')
    gate_id = 'E1-' + args.phase + '-' + now.strftime('%Y%m%dT%H%M%S%fZ')
    gate = dict(id=gate_id, approved_by='Main', approved=True, phase=args.phase,
                freeze_hash=sha(plan['freeze']), plan_hash=sha(plan), max_calls=plan['planned'],
                additional_upper_cap_units=args.cap_units,
                expires_at=(now + timedelta(hours=1)).isoformat(),
                pricing_evidence=pricing_path.relative_to(ROOT).as_posix(), pricing_sha256=sha(pricing_path.read_bytes()),
                independent_qa_result=qa_path.relative_to(ROOT).as_posix(), independent_qa_sha256=sha(qa_path.read_bytes()),
                budget_snapshot=dict(cap_units=cap, charged_upper_units=charged, remaining_units=cap-charged,
                                     calls=count, unknown_or_pending=pending, frozen=bool(frozen)))
    if args.phase == 'formal':
        pilot = HOME / 'runs' / (args.pilot_run_id or '')
        run, summary = load(pilot / 'run.json'), load(pilot / 'summary.json')
        if run['mode'] != 'real' or run['phase'] != 'pilot' or run['plan_hash'] != sha(make_plan('pilot')):
            raise ValueError('REAL_FROZEN_PILOT_REQUIRED')
        for group in summary['by_variant'].values():
            if group['completed'] != group['planned'] or group['usage_known_rows'] != group['planned'] or group['paid_attempts_uncertain']:
                raise ValueError('PILOT_NOT_COMPLETE_WITH_KNOWN_USAGE')
        gate.update(pilot_run_id=run['run_id'], pilot_summary_sha256=sha((pilot / 'summary.json').read_bytes()),
                    pilot_review_accepted=True)
    path = HOME / 'authorizations' / (gate_id + '.json')
    path.parent.mkdir(exist_ok=True)
    data = encoded(gate) + b'\n'
    with path.open('xb') as handle:
        handle.write(data)
    registration = ROOT / 'evidence/integration' / (gate_id + '.json')
    with registration.open('xb') as handle:
        handle.write(encoded(dict(gate=gate, authorization_path=path.relative_to(ROOT).as_posix(),
                                  authorization_raw_sha256=sha(data), actual_paid_calls=0,
                                  scope='Main finite GO; gate preparation is not an executed experiment')) + b'\n')
    print(json.dumps(dict(path=str(path), raw_sha256=sha(data), registration=str(registration),
                          planned=plan['planned'], all_reservation_units=sum(r['reservation_units'] for r in plan['rows'])), ensure_ascii=False))


if __name__ == '__main__':
    main()
