"""Free V5 evaluation wire preview; synthetic capture only, no credentials/ledger."""
from __future__ import annotations

import argparse
import asyncio
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from uuid import uuid4

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from evaluation.common import EvaluationError, json_bytes, sha256
from evaluation.engine import Evaluator
from evaluation.provider import MODEL, OFFICIAL_BASE, Suggestion, cost_units
from evaluation.v5 import (CLAIMS, CONTRACT, VERSION, load_v5, paid_wire_bytes,
                           require_paid_evidence)

OUTPUT_ROOT = PROJECT / 'evidence/project/stages/v5-conservative-recovery/evaluation'


class CaptureProvider:
    """Explicit mock capture, never a semantic judgement or a network adapter."""
    mode = 'mock'

    def __init__(self):
        self.calls = 0
        self.messages = []
        self.last_metadata = None

    async def complete(self, messages):
        self.calls += 1
        self.messages.append(copy.deepcopy(messages))
        claim = json.loads(messages[1]['content'])['TARGET_DATA']['claim']
        value = {'claim_id': claim['claim_id'], 'release_id': claim['release_id'],
                 'status': 'INSUFFICIENT_EVIDENCE', 'evidence_refs': claim['evidence_refs'],
                 'reason': 'Synthetic message capture only; no model judgement requested.',
                 'missing_check': ['Obtain a new finite authorization before any real judgement.']}
        self.last_metadata = {'mode': 'mock', 'actual_network_call': False, 'usage': None, 'call_id': None,
                              'synthetic_capture_only': True}
        return Suggestion(json.dumps(value, ensure_ascii=False), self.last_metadata)


async def build_preview(*, max_tokens=1000, timeout_seconds=20):
    if (type(max_tokens) is not int or not 1 <= max_tokens <= 1000
            or type(timeout_seconds) not in (int, float) or not 0 < timeout_seconds <= 20):
        raise EvaluationError('INVALID_GATE_LIMITS')
    files, tools, context = load_v5()
    binding = require_paid_evidence(tools, context)
    capture = CaptureProvider()
    evaluator = Evaluator(tools, files, capture)
    records = []
    for claim in context.claims:
        previous = capture.calls
        result, audit = await evaluator.evaluate(claim, CONTRACT, VERSION)
        if (capture.calls != previous + 1 or audit['validation_errors']
                or result['status'] != 'INSUFFICIENT_EVIDENCE'):
            raise EvaluationError('V5_PREVIEW_CAPTURE_INCOMPLETE')
        wire = paid_wire_bytes(capture.messages[-1], max_tokens=max_tokens)
        input_bound = len(wire) * 4 + 8192
        if input_bound > 1_000_000:
            raise EvaluationError('INPUT_TOO_LARGE')
        records.append({'claim_id': claim['claim_id'], 'wire_sha256': sha256(wire),
                        'wire_bytes': len(wire), 'input_token_bound': input_bound,
                        'output_token_cap': max_tokens, 'cost_upper_units': cost_units(input_bound, max_tokens),
                        'synthetic_capture_only': True, 'real_model_calls': 0})
    require_paid_evidence(tools, context, expected_binding=binding)
    if [row['claim_id'] for row in records] != list(CLAIMS):
        raise EvaluationError('V5_PREVIEW_CAPTURE_INCOMPLETE')
    total = sum(row['cost_upper_units'] for row in records)
    return {'kind': 'Free synthetic V5 engine-message/wire preview, not semantic evaluation',
            'status': 'PREVIEW_ONLY', 'paid_input_binding': binding, 'claims': records,
            'provider_profile': {'model': MODEL, 'base_url': OFFICIAL_BASE, 'max_tokens': max_tokens,
                                 'timeout_seconds': timeout_seconds},
            'proposed_max_calls': len(CLAIMS), 'total_cost_upper_units': total,
            'total_cost_upper_cny': total / 1_000_000_000,
            'peak_single_call_upper_units': max(row['cost_upper_units'] for row in records),
            'capture_dispatches': capture.calls, 'synthetic_capture_only': True,
            'credentials_accessed': False, 'ledger_opened': False, 'real_model_calls': 0,
            'actual_paid_calls': 0, 'actual_network_calls': 0,
            'limitations': ['No gate or paid approval is created or inherited.',
                            'Wire bounds are conservative estimates, not provider usage.',
                            'Unknown/reserved/frozen/cap and finite authorization still gate any future paid run.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-tokens', type=int, default=1000)
    parser.add_argument('--timeout-seconds', type=float, default=20)
    args = parser.parse_args()
    started = datetime.now(timezone.utc)
    code = 0
    try:
        result = asyncio.run(build_preview(max_tokens=args.max_tokens, timeout_seconds=args.timeout_seconds))
    except (EvaluationError, UnicodeError) as error:
        result = {'status': 'STOPPED', 'error_code': error.code if isinstance(error, EvaluationError) else 'NON_UTF8_TRUSTED_DATA',
                  'credentials_accessed': False, 'ledger_opened': False, 'real_model_calls': 0,
                  'actual_paid_calls': 0, 'actual_network_calls': 0}
        code = 2
    result.update(command=list(getattr(sys, 'orig_argv', [sys.executable, *sys.argv])),
                  started_at_utc=started.isoformat(), ended_at_utc=datetime.now(timezone.utc).isoformat(), exit_code=code)
    output = OUTPUT_ROOT / ('preview-' + started.strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid4().hex[:8])
    output.mkdir(parents=True, exist_ok=False)
    (output / 'preview.json').write_bytes(json_bytes(result))
    print('Free V5 evaluation preview:', output / 'preview.json')
    print('Exit:', code, '; model/network/ledger/credential access: 0')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
