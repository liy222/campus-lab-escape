"""Pure current-request accounting and prompt-only source audit; no dispatch."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.abc
import json
import socket
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
QA = Path(__file__).resolve().parent
PLAN = ROOT / 'evidence/upgrade/v5.0/duplicate-json-prompt/plan.json'
sys.path.insert(0, str(ROOT))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def denied(*args, **kwargs):
    raise RuntimeError('PURE_REQUEST_RUNTIME_BOUNDARY')


class NoPersistenceImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if (fullname.startswith('backend.app.storage')
                or fullname.startswith('backend.app.api')
                or fullname == 'backend.app.main'):
            raise RuntimeError('PURE_REQUEST_FORBIDDEN_IMPORT')
        return None


def audit(candidate_path, output):
    output.resolve().relative_to(QA)
    assert not output.exists()
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    candidate = json.loads(candidate_path.read_text(encoding='utf-8'))
    expected = candidate['source_sha256']
    assert all(sha(ROOT / p) == value for p, value in expected.items())
    baseline = json.loads((ROOT / plan['baseline_source_map']).read_text(encoding='utf-8'))
    changed = sorted(p for p, value in baseline['source'].items() if sha(ROOT / p) != value)
    assert len(baseline['source']) == 428 and changed == ['backend/app/ai/v5.py']
    current = (ROOT / changed[0]).read_bytes()
    insertion = plan['inserted_instruction'].encode('utf-8')
    assert current.count(insertion) == 1
    # Main inserted CRLF before this sentence, preserving the anchor's old LF.
    inserted_buffer = b'\r\n' + insertion
    assert current.count(inserted_buffer) == 1
    inverse = current.replace(inserted_buffer, b'', 1)
    assert hashlib.sha256(inverse).hexdigest() == baseline['source'][changed[0]]

    def without_prompt(value):
        tree = ast.parse(value.decode('utf-8-sig'))
        tree.body = [node for node in tree.body if not (
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'GENERATION_PROMPT'
                    for target in node.targets))]
        return ast.dump(tree, include_attributes=False)

    assert without_prompt(current) == without_prompt(inverse)
    # No actual secrets, provider construction, environment credentials, DB or network.
    sys.meta_path.insert(0, NoPersistenceImports())
    socket.socket.connect = denied
    socket.socket.connect_ex = denied
    socket.create_connection = denied
    sqlite3.connect = denied
    from backend.app.ai.budget import BudgetLedger, cost_units
    from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider, GenerationLimits
    DeepSeekConfig.from_environment = denied
    DeepSeekProvider.__init__ = denied
    BudgetLedger.__init__ = denied
    from backend.app.ai import v5
    from backend.app.domain import generation_content_v2 as content
    v5._provider = denied
    v5.GenerationService.__init__ = denied

    old_case = baseline['generation_cases'][0]
    assert old_case['case_id'] == 'G3'
    selected = content.select_blueprint(3, 'hard', seed=1)
    assert selected.family == old_case['expected_family'] == 'mapping_v1'
    messages = v5.GenerationService.messages(theme=old_case['theme'], room_count=3,
                                            difficulty='hard', blueprint=selected)
    limits = GenerationLimits()
    assert limits.max_tokens == 6000 and limits.max_cost_units == 200_000_000
    assert limits.timeout_seconds == 60 and limits.json_mode is True
    old_messages = old_case['payload']['messages']
    assert messages[1] == old_messages[1]
    assert messages[0]['role'] == old_messages[0]['role'] == 'system'
    assert messages[0]['content'].count(plan['inserted_instruction']) == 1
    assert messages[0]['content'].replace(plan['inserted_instruction'] + '\n', '', 1) == old_messages[0]['content']
    body = {'model': 'deepseek-flash', 'messages': messages, 'max_tokens': limits.max_tokens,
            'thinking': {'type': 'disabled'}, 'stream': False,
            'response_format': {'type': 'json_object'}}
    encoded = json.dumps(body, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
    tokens = len(encoded) * 4 + 8192
    units = cost_units(tokens, limits.max_tokens)
    assert units <= limits.max_cost_units
    assert all(sha(ROOT / p) == value for p, value in expected.items())
    value = {
        'kind': 'Independent AI QA prompt-only static audit and same-G3 pure request measurement',
        'actor': 'Independent AI QA agent; no human reviewer',
        'candidate_sha256': sha(candidate_path), 'source_count': len(expected),
        'source_before_after_current_match': True,
        'historical_baseline_source_count': 428, 'historical_baseline_now_current': False,
        'old428_exactly_one_authorized_delta': changed,
        'inverse_entire_raw_hash_matches_historical_AI_source': True,
        'all_nonprompt_AST_including_companion_and_GenerationService_unchanged': True,
        'same_G3_theme_3hard_mapping_seed1': True,
        'user_message_schema_manifest_requirements_profile_unchanged': True,
        'system_message_only_exact_instruction_insertion': True,
        'payload_utf8_bytes': len(encoded), 'input_token_bound': tokens,
        'output_token_bound': limits.max_tokens, 'cost_upper_units': units,
        'cost_upper_cny': units / 1e9, 'unchanged_cap_cny': .20,
        'payload_sha256': hashlib.sha256(encoded).hexdigest(),
        'pure_request_only_not_provider_send_or_approval_proposal': True,
        'provider_factory_config_Key_ledger_DB_network_access': False,
        'old_actual_private_body_read': False, 'paid_calls': 0,
        'limits': ['No real model compliance, duplicate-rate reduction, yield or narrative quality claim.',
                   'Historical actual rejection and OPEN findings unchanged; no repair or retry.',
                   'Accounting is a bound for a pure request, not an actual charge or new paid-run proposal.'],
    }
    with output.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'status': 'PURE_REQUEST_AND_PROMPT_ONLY_AUDIT_COMPLETE',
                      'payload_utf8_bytes': len(encoded), 'input_token_bound': tokens,
                      'output_token_bound': limits.max_tokens, 'cost_upper_cny': units / 1e9,
                      'audit_sha256': sha(output), 'paid_calls': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        audit(args.candidate, args.output)
    except BaseException as error:
        print(json.dumps({'status': 'PURE_AUDIT_FAILED', 'error_class': type(error).__name__,
                          'raw_error_details_suppressed': True}))
        raise SystemExit(1)
