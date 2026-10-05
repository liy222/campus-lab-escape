"""Main accounting closure from human fee report; retain the full reserved upper.

This does not recover a response, token usage, HTTP receipt or provider invoice.
It never reduces a charge, changes the cap, clears a frozen flag, or retries HTTP.
"""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import sqlite3

ROOT = Path(__file__).resolve().parents[2]
CALL = '520a5c50b9204960a3f9915952ed9b97'
BOUND = 162_920_000
REPORTED = 50_000_000
REASON = 'HUMAN_FEE_REPORTED_UPPER_RETAINED'
PREVIOUS = (CALL, 'experiments', '2026-10-05T05:34:18.992257+00:00', BOUND, BOUND,
            'unknown', 'MODEL_TIMEOUT', None, None, None)
COLS = 'id,scope,created_at,reserved,charged,state,reason,prompt_tokens,completion_tokens,cache_hit_tokens'

def reconcile(db, apply=False):
    db.execute('BEGIN IMMEDIATE' if apply else 'BEGIN')
    try:
        config = db.execute('SELECT id,cap,frozen FROM budget_config').fetchall()
        if config != [(1, 10_000_000_000, 0)]:
            raise ValueError('unchanged unfrozen original CNY10 cap required')
        row = db.execute('SELECT '+COLS+' FROM budget_calls WHERE id=?', (CALL,)).fetchone()
        closed = list(PREVIOUS)
        closed[5:7] = ['settled', REASON]
        if row not in (PREVIOUS, tuple(closed)):
            raise ValueError('exact original timeout or exact prior closure required')
        if REPORTED > BOUND:
            raise ValueError('human reported fee exceeds retained upper')
        totals = db.execute('SELECT COUNT(*),COALESCE(SUM(charged),0) FROM budget_calls').fetchone()
        all_before = db.execute('SELECT '+COLS+' FROM budget_calls ORDER BY id').fetchall()
        if totals[1] > config[0][1]:
            raise ValueError('existing total exceeds cap')
        pending = db.execute("SELECT id,state FROM budget_calls WHERE state IN ('unknown','reserved') AND id!=?", (CALL,)).fetchall()
        if pending:
            raise ValueError('other unresolved calls remain')
        if apply and row == PREVIOUS:
            cur = db.execute("UPDATE budget_calls SET state='settled',reason=? WHERE id=? AND state='unknown' AND reason='MODEL_TIMEOUT' AND reserved=? AND charged=? AND prompt_tokens IS NULL AND completion_tokens IS NULL AND cache_hit_tokens IS NULL",
                             (REASON, CALL, BOUND, BOUND))
            if cur.rowcount != 1:
                raise ValueError('atomic expected row update failed')
        after = db.execute('SELECT '+COLS+' FROM budget_calls WHERE id=?', (CALL,)).fetchone()
        expected_after = tuple(closed) if apply else row
        if after != expected_after:
            raise ValueError('complete target row changed beyond approved state/reason')
        if db.execute('SELECT id,cap,frozen FROM budget_config').fetchall() != config:
            raise ValueError('budget configuration changed')
        all_expected = [expected_after if r[0] == CALL else r for r in all_before]
        if db.execute('SELECT '+COLS+' FROM budget_calls ORDER BY id').fetchall() != all_expected:
            raise ValueError('unapproved change to another ledger row')
        if db.execute('SELECT COUNT(*),COALESCE(SUM(charged),0) FROM budget_calls').fetchone() != totals:
            raise ValueError('charge/count changed')
        result = {'applied': apply, 'already_closed': row == tuple(closed),
                  'columns': COLS.split(','), 'before': list(row), 'after': list(after),
                  'human_reported_cost_units': REPORTED, 'retained_charge_units': BOUND,
                  'calls': totals[0], 'charged_upper_units': totals[1], 'cap_units': config[0][1],
                  'provider_usage_known': False, 'provider_invoice_independently_verified': False,
                  'accounting_basis': 'Human owner explicitly identified this timeout fee as CNY0.05. Conservatively keep CNY0.16292, close accounting hold only; token NULLs, timeout and original experiment evidence remain unchanged.'}
        if apply:
            db.commit()
        else:
            db.rollback()
        return result
    except BaseException:
        db.rollback()
        raise

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    ledger = ROOT/'data/ai-budget.sqlite'
    if ROOT.resolve() != Path('D:/深度能力').resolve() or not ledger.is_file():
        raise ValueError('existing canonical project ledger required')
    for path in [ledger, *ledger.parents]:
        if path.is_symlink() or getattr(path.lstat(), 'st_file_attributes', 0) & 0x400:
            raise ValueError('reparse ledger path forbidden')
    suffix = 'applied' if args.apply else 'dryrun'
    output = ROOT/f'evidence/integration/timeout-human-fee-20261005-{suffix}.json'
    if output.exists():
        raise ValueError('append-only record already exists; inspect it instead')
    mode = 'rw' if args.apply else 'ro'
    with closing(sqlite3.connect(ledger.resolve().as_uri()+'?mode='+mode, uri=True, isolation_level=None, timeout=15)) as db:
        result = reconcile(db, args.apply)
    result.update({'created_at': datetime.now(timezone.utc).isoformat(), 'call_id': CALL,
                   'approved_by': 'Main', 'human_reply_exact': '这笔超时请求费用为人民币 0.05 元',
                   'helper_raw_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   'actual_command': ['C:\\Users\\liyh\\.conda\\envs\\1\\python.exe', '-B', '-X', 'utf8', 'evidence/integration/reconcile_timeout_upper.py']+(['--apply'] if args.apply else []),
                   'limitations': ['No token reconstruction; original timeout/null response remains.', 'Human fee statement is not an independently obtained invoice.', 'Full reservation remains charged; no new allowance or experiment retry.', 'Future real calls still require separate finite gates and source review.']})
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'record': str(output), 'applied': args.apply, 'charged_upper_units': result['charged_upper_units']}, ensure_ascii=False))

if __name__ == '__main__':
    main()
