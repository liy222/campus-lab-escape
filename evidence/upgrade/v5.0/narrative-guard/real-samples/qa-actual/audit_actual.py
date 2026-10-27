"""Closed-output local diagnosis of this rejected sample only; no dispatch."""
from __future__ import annotations

import ast
import hashlib
import importlib.abc
import json
import re
import socket
import sqlite3
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parent.parent
QA = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(name, value):
    path = QA / name
    assert not path.exists()
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n',
                    encoding='utf-8')


class DenyServiceImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if (fullname.startswith('backend.app.ai')
                or fullname.startswith('backend.app.storage')
                or fullname.startswith('backend.app.api')
                or fullname == 'backend.app.main'):
            raise RuntimeError('FORBIDDEN_SERVICE_IMPORT')
        return None


def denied(*args, **kwargs):
    raise RuntimeError('FORBIDDEN_RUNTIME_ACCESS')


def main():
    # No provider/config/ledger/DB/network access, even accidentally.
    sys.meta_path.insert(0, DenyServiceImports())
    socket.socket.connect = denied
    socket.socket.connect_ex = denied
    socket.create_connection = denied
    sqlite3.connect = denied

    provider_path = OUT / 'G3-provider-result.json'
    relative_provider = str(provider_path.relative_to(ROOT)).replace('\\', '/')
    ignored = subprocess.run(['git', 'check-ignore', '--', relative_provider],
                             capture_output=True, text=True, encoding='utf-8')
    assert ignored.returncode == 0 and ignored.stdout.strip() == relative_provider
    provider_before = provider_path.read_bytes()
    envelope = json.loads(provider_before)
    raw = envelope['content_redacted']
    assert isinstance(raw, str)
    raw_hash = digest(raw.encode())
    assert raw_hash == envelope['content_raw_sha256']
    assert envelope['secret_detected'] is False

    preview_path = OUT / 'offline-preview-v1.json'
    preview = read(preview_path)
    result = read(OUT / 'result.json')
    actual = read(OUT / 'G3-exact-payload.json')
    api = read(OUT / 'G3-api-result.json')
    before = read(OUT / 'ledger-before.json')
    after = read(OUT / 'ledger-after.json')
    approval_path = OUT / 'user-authorization.json'
    approval = read(approval_path)
    marker = read(OUT / 'execute-started.json')
    binding = read(OUT / 'authorization-binding.json')
    journal = [json.loads(line) for line in
               (OUT / 'dispatch-journal.jsonl').read_text(encoding='utf-8').splitlines()]
    prepared = preview['generation_cases'][0]
    assert approval['approved'] is True and approval['scope'] == ['G3']
    assert type(approval['max_calls']) is int and approval['max_calls'] == 1
    assert approval['max_reserved_units'] == 200_000_000
    assert approval['preview_file_sha256'] == digest(preview_path.read_bytes())
    assert approval['candidate_sha256'] == preview['candidate_sha256']
    assert 'call_4697af95db5049239a2626b66178c69d item0' in approval['actual_user_approval_reference']
    assert marker['run_id'] == approval['run_id'] == preview['run_id'] == result['run_id']
    assert marker['authorization_sha256'] == binding['authorization_sha256'] == digest(approval_path.read_bytes())
    assert marker['candidate_sha256'] == preview['candidate_sha256']
    assert marker['single_use_no_resume_or_retry'] is True
    assert datetime.fromisoformat(approval['recorded_utc']) < datetime.fromisoformat(marker['utc'])
    assert actual['payload'] == prepared['payload'] and actual['bound'] == prepared['bound']
    assert actual['source_candidate_sha256'] == preview['candidate_sha256']
    body = json.dumps(actual['payload'], ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode()
    assert digest(body) == prepared['bound']['payload_sha256']
    assert result['source_after'] == preview['source']
    assert len(preview['source']) == 428
    assert all(digest((ROOT / p).read_bytes()) == d for p, d in preview['source'].items())
    assert digest(canonical(preview['source'])) == preview['candidate_sha256']
    assert result['attempted_case_ids'] == ['G3'] and len(result['cases']) == 1
    assert result['exit_code'] == 1 and api['job']['status'] == 'rejected'
    assert api['error_code'] == api['job']['error_code'] == 'MODEL_INVALID_OUTPUT'
    assert result['automatic_retries'] == 0
    assert result['companion_invoked'] is False and result['evaluation_invoked'] is False
    assert result['finalization_failures'] == [] and result['stopped_reason'] is None
    assert len(journal) == 2 and [j['phase'] for j in journal] == ['before_dispatch', 'after_dispatch']
    assert journal[0]['case_id'] == journal[1]['case_id'] == 'G3'
    assert journal[0]['attempt_number'] == 1 and journal[0]['automatic_retry'] is False
    assert journal[1]['outcome'] == 'response' and journal[1]['usage'] == envelope['usage']
    assert not (OUT / 'raw-sensitive').exists()
    assert not api['job'].get('level_id')

    usage = envelope['usage']
    assert usage['prompt_tokens'] == 2927 and usage['completion_tokens'] == 528
    assert usage['prompt_cache_hit_tokens'] == 2688 and usage['total_tokens'] == 3455
    bt = ast.parse((ROOT / 'backend/app/ai/budget.py').read_text(encoding='utf-8'))
    rates = {n.targets[0].id: ast.literal_eval(n.value) for n in bt.body
             if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
             and n.targets[0].id in ('INPUT_MISS_UNITS', 'INPUT_HIT_UNITS', 'OUTPUT_UNITS')}
    cost = ((usage['prompt_tokens'] - usage['prompt_cache_hit_tokens']) * rates['INPUT_MISS_UNITS']
            + usage['prompt_cache_hit_tokens'] * rates['INPUT_HIT_UNITS']
            + usage['completion_tokens'] * rates['OUTPUT_UNITS'])
    assert cost == 4_809_520 == after['charged_upper_units'] - before['charged_upper_units']
    assert envelope['cost_upper_cny'] == cost / 1e9
    assert result['sum_reserved_upper_cny'] == prepared['bound']['cost_upper_cny'] == .158208
    assert before['calls'] == 147 and after['calls'] == 148
    assert before['charged_upper_units'] == 1_127_578_000 and after['charged_upper_units'] == 1_132_387_520
    unknown_hash = 'b7490c5f157e75f973533e518a1e245c1ea0a3818318065c9c7ddf5e5b59085e'
    assert before['unknown_identity_sha256'] == after['unknown_identity_sha256'] == unknown_hash
    for snapshot in (before, after):
        assert snapshot['unknown_calls'] == 3 and snapshot['pending_calls'] == 0
        assert snapshot['frozen'] is False and snapshot['cap_units'] == 10_000_000_000

    # Pure domain functions only. Do not compile, plan, prove or replay anything.
    from backend.app.domain import generation_content_v2 as v2
    from backend.app.domain import generated
    bp = v2.select_blueprint(3, 'hard', seed=1)
    schema = v2.content_schema(bp)
    requested = json.loads(prepared['payload']['messages'][1]['content'])
    assert schema == requested['schema'] and bp.blueprint_id == prepared['blueprint_id']
    counts = {'strict': 0, 'guard': 0, 'description': 0, 'v1_helper': 0}
    original_strict, original_guard = v2.strict_json, v2._guard_narrative

    def strict_spy(value):
        counts['strict'] += 1
        return original_strict(value)

    def guard_spy(blueprint, content):
        counts['guard'] += 1
        return original_guard(blueprint, content)

    def description_denied(*args, **kwargs):
        counts['description'] += 1
        raise RuntimeError('DIAGNOSTIC_HOST_DESCRIPTION_BOUNDARY')

    def helper_denied(*args, **kwargs):
        counts['v1_helper'] += 1
        raise RuntimeError('DIAGNOSTIC_V1_HELPER_BOUNDARY')

    strict_ok = False
    strict_code = None
    content = None
    try:
        content = original_strict(raw)
        strict_ok = True
    except (ValueError, TypeError, RecursionError) as exc:
        code = str(exc)
        strict_code = code if re.fullmatch('[A-Z_]{1,64}', code) else 'STRICT_JSON_INVALID'
    schema_errors = list(v2.v1._IntegerValidator(schema).iter_errors(content)) if strict_ok else []
    schema_ok = strict_ok and not schema_errors
    expected_objects = set(schema['properties']['objects']['required'])
    actual_objects = content.get('objects', {}) if isinstance(content, dict) else {}
    object_mapping = isinstance(actual_objects, dict)
    missing_objects = sorted(expected_objects - set(actual_objects)) if object_mapping else []
    # Missing names are trusted public schema slot identifiers, never model values.
    structural = {
        'strict_json_passed': strict_ok, 'strict_error_code': strict_code,
        'exact_v2_schema_passed': schema_ok,
        'schema_error_count': len(schema_errors),
        'schema_validator_counts': dict(Counter(str(e.validator) for e in schema_errors)),
        'expected_object_slots': len(expected_objects),
        'actual_object_slot_count': len(actual_objects) if object_mapping else None,
        'missing_required_public_schema_object_slots': missing_objects,
        'extra_object_slot_count': len(set(actual_objects) - expected_objects) if object_mapping else None,
    }
    with patch.object(v2, 'strict_json', side_effect=strict_spy), \
         patch.object(v2, '_guard_narrative', side_effect=guard_spy), \
         patch.object(v2, '_describe', side_effect=description_denied), \
         patch.object(v2.v1, 'assemble_draft', side_effect=helper_denied), \
         patch.object(generated, 'compile_level', side_effect=denied):
        code = None
        try:
            v2.assemble_draft(bp, raw)
        except (ValueError, RuntimeError) as exc:
            text = str(exc)
            code = text if re.fullmatch('[A-Z0-9_]{1,64}', text) else 'SANITIZED_DIAGNOSTIC_ERROR'
        assert code is not None
    assert counts['description'] == counts['v1_helper'] == 0
    assert provider_path.read_bytes() == provider_before
    assert all(digest((ROOT / p).read_bytes()) == d for p, d in preview['source'].items())

    metadata = {
        'kind': 'Explicit safe metadata derivative, not the original provider response',
        'actor': 'Independent AI QA agent',
        'local_private_provider_file_sha256': digest(provider_before),
        'original_content_raw_sha256': raw_hash,
        'original_content_utf8_bytes': len(raw.encode()),
        'original_content_not_published': True,
        'usage': {k: usage[k] for k in ('prompt_tokens', 'completion_tokens', 'prompt_cache_hit_tokens', 'total_tokens')},
        'requested_model_approved': envelope['requested_model'] == 'deepseek-flash',
        'reported_model_approved': envelope['reported_model'] in {
            'deepseek-flash', 'deepseek-v4.1-flash', 'DeepSeek-V4.1-Flash',
            'deepseek-v4.1-flash-1017', 'DeepSeek-V4.1-Flash-1017'},
        'finish_reason_stop': envelope['finish_reason'] == 'stop',
        'secret_detected': envelope['secret_detected'], 'usage_upper_cny': cost / 1e9,
    }
    assert metadata['requested_model_approved'] and metadata['reported_model_approved'] and metadata['finish_reason_stop']
    write('provider-metadata-derived.json', metadata)
    diagnosis = {
        'kind': 'Independent AI QA finite local diagnosis of rejected actual sample',
        'utc': datetime.now(timezone.utc).isoformat(),
        'actor': 'Independent AI QA agent; no human reviewer',
        'actual_executor_exit_code': 1, 'local_diagnostic_exit_code': 0,
        'local_diagnostic_production_assembler_code': code,
        'structural': structural, 'assembler_spy_call_counts': counts,
        'first_refusal_layer': 'strict_json' if not strict_ok else ('exact_v2_schema' if not schema_ok else 'finite_narrative_guard'),
        'approved_single_scope_bound': True, 'authorization_before_marker': True,
        'one_dispatch_journal_closed': True, 'payload_equals_approved_preview': True,
        'source428_before_after_current_match': True,
        'no_level_no_privateproof_no_replay': True,
        'ledger_saved_snapshots': {'calls_before': 147, 'calls_after': 148,
            'charged_upper_units_before': before['charged_upper_units'],
            'charged_upper_units_after': after['charged_upper_units'],
            'usage_upper_units_delta': cost, 'old_unknown_count': 3,
            'old_unknown_identity_unchanged': True, 'new_unknown': 0,
            'pending': 0, 'frozen': False},
        'approved_slot_used': 1, 'remaining_authorized_calls': 0,
        'reserved_upper_cny': .158208, 'usage_upper_cny': cost / 1e9,
        'finalization_failures_empty': True,
        'raw_original_hash_and_bytes_unchanged': True,
        'private_originals': {relative_provider: digest(provider_before)},
        'raw_parameters_clues_answers_or_projection_output': False,
        'rejected_story_or_names_output': False,
        'narrative_quality_assessed': False,
        'guard_actual_effectiveness_proven': False,
        'runtime_boundary': 'Denied ai/storage/api/main imports, socket connections and sqlite3.connect; only pure domain strict/schema/guard/assembler diagnosis. No compiler/planner/proof/HTTP/model/test/build/eval.',
        'limits': ['One rejected real sample, no ready level or gameplay/public prose quality result.',
                   'No original raw repair, retry, old private read, Key/config/liveledger/userDB/provider/network/paid access.',
                   'No narrative pass, efficacy/yield/false-positive rate, human difficulty or automatic OPEN closure.'],
    }
    write('local-diagnosis-v1.json', diagnosis)
    print(json.dumps({'diagnostic_exit_code': 0, 'first_refusal_layer': diagnosis['first_refusal_layer'],
                      'production_error_code': code, 'structural': structural,
                      'assembler_spy_call_counts': counts,
                      'usage_upper_cny': cost / 1e9,
                      'diagnosis_sha256': digest((QA / 'local-diagnosis-v1.json').read_bytes()),
                      'provider_metadata_sha256': digest((QA / 'provider-metadata-derived.json').read_bytes())}))


if __name__ == '__main__':
    try:
        main()
    except BaseException as exc:
        # Deliberately no traceback or raw exception text, including validation errors.
        print(json.dumps({'diagnostic_exit_code': 1, 'error_class': type(exc).__name__,
                          'raw_details_suppressed': True}))
        raise SystemExit(1)
