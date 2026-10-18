"""Read-only independent audit of a Main-owned real-run manifest.

No backend imports, network, credentials or direct ledger access. Stdlib only.
Main may adapt its manifest to this schema or QA may narrowly adapt after seeing
the actual result; do not interpret this checker as a semantic model judge.
"""
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'evidence/integration/ai-companion-real/qa'


def contained(relative):
    path = (ROOT / relative).resolve()
    if ROOT.resolve() not in path.parents:
        raise ValueError('Manifest path escapes workspace')
    return path


def check(manifest_path):
    manifest = json.loads(contained(manifest_path).read_text(encoding='utf-8-sig'))
    checks, issues = [], []
    def require(ok, name):
        checks.append({'check': name, 'passed': bool(ok)})
        if not ok: issues.append(name)
    for group in ('source_sha256', 'artifact_sha256'):
        require(isinstance(manifest.get(group), dict) and bool(manifest.get(group)), group+' present')
        for relative, expected in manifest.get(group, {}).items():
            require(hashlib.sha256(contained(relative).read_bytes()).hexdigest() == expected, group+':'+relative)
    cases = manifest.get('case_results', [])
    require(isinstance(cases, list) and bool(cases), 'actual case records present')
    ids = [c.get('case_id') for c in cases]
    require(len(ids) == len(set(ids)), 'case IDs unique')
    dispatches = sum(c.get('provider_dispatches', 0) for c in cases)
    require(0 <= dispatches <= 8, 'at most8 real dispatches')
    require(dispatches == manifest.get('actual_provider_dispatches'), 'dispatch total matches cases')
    charged = sum((Decimal(str(c.get('charged_cny', 0))) for c in cases), Decimal(0))
    reserved = sum((Decimal(str(c.get('reserved_cny', 0))) for c in cases), Decimal(0))
    require(0 <= charged <= Decimal('1.50'), 'actual charged within epoch ceiling')
    require(0 <= reserved <= Decimal('1.50'), 'reserved upper total within epoch ceiling')
    require(charged == Decimal(str(manifest.get('actual_charged_cny', -1))), 'charged total matches cases')
    require(Decimal(str(manifest.get('original_cap_cny', -1))) == Decimal('10'), 'original cap10 unchanged')
    require(manifest.get('historical_unknown_retried') is False, 'historical unknown requests not retried')
    if manifest.get('new_unknown_count', 0):
        require(bool(manifest.get('stopped_reason')), 'new unknown has stop reason')
    controls = [c for c in cases if c.get('kind') == 'local_control']
    require(bool(controls), 'local whole-answer control recorded')
    for c in controls:
        require(c.get('provider_dispatches') == 0, c['case_id']+' local0call')
        require(c.get('hint_count_delta') == 0 and c.get('revision_delta') == 0, c['case_id']+' local unchanged')
    result = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'scope': 'Read-only manifest arithmetic/path/hash/control audit; semantic review is separate.', 'input_manifest': manifest_path, 'input_sha256': hashlib.sha256(contained(manifest_path).read_bytes()).hexdigest(), 'checks': checks, 'issues': issues, 'exit_code': 0 if not issues else 1, 'paid_calls_by_QA': 0, 'direct_ledger_access': False}
    QA.mkdir(parents=True, exist_ok=True)
    out = QA / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-manifest-review.json')
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'evidence': str(out), 'exit_code': result['exit_code'], 'checks': len(checks), 'issues': issues}, ensure_ascii=False))
    return result['exit_code']


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Pass a Main-owned result manifest; this script never sends requests.')
    raise SystemExit(check(sys.argv[1]))
