"""Minimal pure-request QA for item context; no real narrative-quality claim.

No provider/config/Key/ledger/database/HTTP/solver construction is permitted.
Run the formal command only after Main freezes the new candidate and gives GO.
"""
from __future__ import annotations

import ast
import copy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import httpx
import pytest
from backend.app.ai import v5 as ai_v5
from backend.app.ai.budget import BudgetLedger, cost_units
from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider, GenerationLimits
from backend.app.domain.blueprints import content_schema, request_manifest, select_blueprint
from backend.app.domain import generation_content_v2 as current_content

EPOCH = ROOT / 'evidence/upgrade/v5.0/blueprint-item-context'
PLAN = json.loads((EPOCH / 'plan.json').read_text(encoding='utf-8-sig'))
BASELINE = PLAN['baseline_head']
BASELINE_RAW = json.loads((ROOT / PLAN['baseline_candidate']).read_text(encoding='utf-8-sig'))['source_sha256']


def observe(name, value):
    output = os.environ.get('ITEM_CONTEXT_QA_OUTPUT')
    if output:
        directory = Path(output).resolve()
        directory.relative_to((EPOCH / 'qa').resolve())
        assert Path(name).name == name and name.endswith('.json')
        directory.mkdir(parents=True, exist_ok=True)
        (directory / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


@pytest.fixture(autouse=True)
def forbid_runtime_boundaries(monkeypatch):
    attempted = []
    def forbidden(*args, **kwargs):
        attempted.append(True)
        raise AssertionError('Pure item-context QA reached a forbidden runtime boundary')
    monkeypatch.setattr(ai_v5, '_provider', forbidden)
    monkeypatch.setattr(DeepSeekProvider, '__init__', forbidden)
    monkeypatch.setattr(DeepSeekConfig, 'from_environment', forbidden)
    monkeypatch.setattr(BudgetLedger, '__init__', forbidden)
    monkeypatch.setattr(sqlite3, 'connect', forbidden)
    monkeypatch.setattr(httpx.Client, '__init__', forbidden)
    monkeypatch.setattr(httpx.AsyncClient, '__init__', forbidden)
    yield
    assert attempted == []


@pytest.mark.parametrize('seed', [0, 1])
def test_item_context_uses_actual_reference_only_and_is_fresh(seed):
    bp = select_blueprint(3, 'hard', seed=seed)
    original = copy.deepcopy(bp)
    schema_before = content_schema(bp)
    manifest = request_manifest(bp)
    assert {p.mechanism for p in bp.puzzles} == {'item', 'code', 'sequence', 'circuit'}
    for puzzle, row in zip(bp.puzzles, manifest['puzzles']):
        if puzzle.mechanism == 'item':
            actual = next(obj for obj in bp.objects if obj.kind == 'item' and obj.reference_id == puzzle.required_item_id)
            assert row['item_use'] == {'item_object_slot': actual.object_id, 'tool': 'use_item', 'consumed': False}
            assert type(row['item_use']['consumed']) is bool
        else:
            assert 'item_use' not in row
    item = next(row for row in manifest['puzzles'] if row['mechanism'] == 'item')
    item['item_use']['item_object_slot'] = 'mutated-only-in-return-value'
    assert bp == original and content_schema(bp) == schema_before
    assert next(row for row in request_manifest(bp)['puzzles'] if row['mechanism'] == 'item')['item_use']['item_object_slot'] != 'mutated-only-in-return-value'


@pytest.mark.parametrize('seed', [0, 1])
def test_renamed_item_slot_with_old_name_decoy_is_derived_not_hardcoded(seed):
    bp = select_blueprint(3, 'hard', seed=seed)
    original = copy.deepcopy(bp)
    item = next(obj for obj in bp.objects if obj.kind == 'item')
    renamed = replace(item, object_id='renamed_required_object', reference_id='renamed_inventory_id')
    decoy = replace(item, slot=max(obj.slot for obj in bp.objects if obj.room_id == item.room_id) + 1)
    changed = replace(bp,
        objects=tuple(renamed if obj == item else obj for obj in bp.objects) + (decoy,),
        puzzles=tuple(replace(p, required_item_id='renamed_inventory_id') if p.mechanism == 'item' else p for p in bp.puzzles))
    manifest = request_manifest(changed)
    row = next(row for row in manifest['puzzles'] if row['mechanism'] == 'item')
    assert row['item_use'] == {'item_object_slot': 'renamed_required_object', 'tool': 'use_item', 'consumed': False}
    assert item.object_id in manifest['object_slots'] and 'renamed_required_object' in manifest['object_slots']
    assert bp == original
    observe(f'renamed-slot-{bp.family}.json', {'family': bp.family, 'actual_reference_followed': True,
        'old_object_name_decoy_ignored': True, 'source_blueprint_unchanged': True, 'compile_or_witness_called': False})


def baseline_text(name):
    return subprocess.run(['git', 'show', BASELINE + ':' + name], cwd=ROOT, capture_output=True, check=True).stdout.decode('utf-8-sig')


def test_only_request_manifest_and_generation_prompt_ast_changed():
    def tree_without(text, omit):
        return [ast.dump(node, include_attributes=False) for node in ast.parse(text).body if not omit(node)]
    path = 'backend/app/domain/blueprints.py'
    assert tree_without(baseline_text(path), lambda node: isinstance(node, ast.FunctionDef) and node.name == 'request_manifest') == tree_without((ROOT / path).read_text(encoding='utf-8-sig'), lambda node: isinstance(node, ast.FunctionDef) and node.name == 'request_manifest')
    path = 'backend/app/ai/v5.py'
    is_prompt = lambda node: isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'GENERATION_PROMPT' for target in node.targets)
    # Only the two declared generation imports may differ. Keep every other
    # GenerationService and companion AST node in the full comparison.
    current_tree = ast.parse((ROOT / path).read_text(encoding='utf-8-sig'))
    service = next(node for node in current_tree.body if isinstance(node, ast.ClassDef) and node.name == 'GenerationService')
    imports = [(method.name, node) for method in service.body
               if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
               for node in ast.walk(method) if isinstance(node, ast.ImportFrom)]
    expected = {'messages': ['select_blueprint', 'request_manifest', 'content_schema'],
                'generate': ['select_blueprint', 'assemble_draft']}
    assert len(imports) == 2 and {method for method, _ in imports} == set(expected)
    for method, node in imports:
        assert node.module == 'domain.generation_content_v2' and node.level == 2
        assert [alias.name for alias in node.names] == expected[method]
        assert all(alias.asname is None for alias in node.names)
        node.module = 'domain.blueprints'
    current_nodes = [ast.dump(node, include_attributes=False) for node in current_tree.body if not is_prompt(node)]
    assert tree_without(baseline_text(path), is_prompt) == current_nodes
    frozen = ('contracts/v2/generation-content.schema.json', 'contracts/v2/build_generation_content.py',
              'backend/app/domain/generated.py', 'backend/app/ai/provider.py', 'backend/app/ai/budget.py',
              'backend/app/api/v5.py', 'backend/app/storage/v5.py')
    for name in frozen:
        # Raw authority is the already accepted Windows candidate; Git blob
        # line endings may differ without any source-content change.
        assert BASELINE_RAW[name] == hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), name
    observe('frozen-scope.json', {'only_manifest_and_prompt_AST_changed': True,
        'frozen_raw_paths': list(frozen), 'public_Draft_contract_unchanged': True, 'internal_model_contract': '2.0.0',
        'exact_generation_imports_normalized': 2, 'old_actual_finding_retested': False})


@pytest.mark.parametrize('seed', [0, 1])
def test_messages_serialize_item_interaction_contract_without_output_schema_change(seed):
    bp = current_content.select_blueprint(3, 'hard', seed=seed)
    before = copy.deepcopy(bp)
    legacy_schema = {'caller_owned': ['sentinel']}; original = copy.deepcopy(legacy_schema)
    messages = ai_v5.GenerationService.messages(theme='校园交接', room_count=3, difficulty='hard',
        draft_schema=legacy_schema, blueprint=bp)
    value = json.loads(messages[1]['content'])
    assert value['schema'] == current_content.content_schema(bp)
    assert value['blueprint'] == current_content.request_manifest(bp)
    assert bp == before and legacy_schema == original
    manifest = value['blueprint']
    item_rows = [row for row in manifest['puzzles'] if row['mechanism'] == 'item']
    assert len(item_rows) == 1
    interaction = item_rows[0]['item_use']
    assert interaction['item_object_slot'] in manifest['object_slots']
    assert manifest['object_slots'][interaction['item_object_slot']]['kind'] == 'item'
    assert interaction['tool'] == 'use_item' and interaction['consumed'] is False
    assert all('item_use' not in row for row in manifest['puzzles'] if row['mechanism'] != 'item')
    assert 'item_use' not in value['schema']['properties']
    assert set(value['schema']['properties']) == {'content_version', 'blueprint_id', 'title', 'story', 'rooms', 'objects', 'parameters'}


def wire_body(messages):
    """The unchanged provider's complete outgoing JSON shape, without construction."""
    return {'model': 'deepseek-flash', 'messages': messages, 'max_tokens': 6000,
            'thinking': {'type': 'disabled'}, 'stream': False, 'response_format': {'type': 'json_object'}}


@pytest.mark.parametrize('seed', [0, 1])
def test_whole_request_short_and_four_byte_theme_budget_measurements(seed):
    bp = current_content.select_blueprint(3, 'hard', seed=seed)
    limits = GenerationLimits()
    assert limits.max_cost_units == 200_000_000 and limits.max_tokens == 6000 and limits.timeout_seconds == 60
    measurements = []
    for label, theme in [('short', '校园实验交接'), ('four-byte-max', '\U0001f9ea' * 2000)]:
        messages = ai_v5.GenerationService.messages(theme=theme, room_count=3, difficulty='hard', blueprint=bp)
        body = wire_body(messages)
        encoded = json.dumps(body, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
        input_bound = len(encoded) * 4 + 8192
        bound = cost_units(input_bound, 6000)
        assert bound == input_bound * 2000 + 6000 * 8000
        assert input_bound < 1_000_000
        if label == 'short':
            assert bound <= limits.max_cost_units
        else:
            assert len(theme) == 2000 and len(theme.encode()) == 8000
        measurements.append({'theme_kind': label, 'theme_characters': len(theme),
            'whole_payload_utf8_bytes': len(encoded), 'whole_payload_sha256': hashlib.sha256(encoded).hexdigest(),
            'input_token_bound': input_bound, 'upper_cost_units': bound,
            'original_cap_units': limits.max_cost_units, 'within_original_budget_cap': bound <= limits.max_cost_units,
            'actual_dispatch_or_refusal_tested': False})
    observe(f'budget-{bp.family}.json', {'family': bp.family, 'measurements': measurements,
        'scope': 'pure complete-payload accounting only; provider never constructed', 'paid_calls': 0})


def main():
    import argparse
    from datetime import datetime, timezone
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--scope', default='')
    args = parser.parse_args()
    args.output.resolve().relative_to((EPOCH / 'qa').resolve())
    args.output.mkdir(parents=True, exist_ok=False)
    candidate = json.loads(args.candidate.read_text(encoding='utf-8-sig'))
    expected = candidate.get('source_sha256', candidate.get('source_hashes', {}))
    assert expected
    hashes = lambda: {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in expected}
    before = hashes()
    command = [sys.executable, '-m', 'pytest', 'tests/v5/test_blueprint_item_context.py', '-q', '-p',
               'no:cacheprovider', '--junitxml=' + str(args.output / 'junit.xml')]
    if args.scope:
        command.extend(['-k', args.scope])
    environment = os.environ.copy()
    environment.update(PYTHONUTF8='1', AI_PROVIDER='mock', ITEM_CONTEXT_QA_OUTPUT=str(args.output / 'observations'))
    environment.pop('V5_QA_OUTPUT', None)
    report = {'candidate': str(args.candidate), 'candidate_sha256': hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
        'started_at': datetime.now(timezone.utc).isoformat(), 'source_before': before, 'command': command,
        'scope': 'Only new pure request context cases, no old suite or runtime', 'paid_calls': 0,
        'provider_or_ledger_or_database_or_network_calls': 0, 'exit_code': 1}
    try:
        assert before == expected, 'Candidate mismatch before pure QA'
        process = subprocess.run(command, cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        (args.output / 'output.txt').write_bytes(process.stdout)
        report['exit_code'] = process.returncode
    except subprocess.TimeoutExpired as error:
        (args.output / 'output.txt').write_bytes(error.stdout or b'')
        report.update(exit_code=124, error='Narrow pure suite timeout')
    except Exception as error:
        report['error'] = str(error)
    report.update(source_after=hashes(), ended_at=datetime.now(timezone.utc).isoformat())
    report['source_unchanged'] = before == report['source_after']
    if not report['source_unchanged']:
        report['exit_code'] = 1
    (args.output / 'run.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'evidence': str(args.output), 'exit_code': report['exit_code']}))
    return report['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
