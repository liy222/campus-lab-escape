"""Draft single-G3 real validation executor; authoring is not paid authorization.

--prepare is offline: selected Host blueprints, production messages and bounds
only. --execute is Main-only after independent review and a NEW actual finite
user approval. Marker/journal consume each case including failure; no retry,
model-content repair, fixture, historical fallback, companion or evaluator.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import secrets
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent
MODEL = 'deepseek-flash'
APPROVED_REPORTED_MODELS = frozenset({'deepseek-flash', 'deepseek-v4.1-flash', 'DeepSeek-V4.1-Flash', 'deepseek-v4.1-flash-1017', 'DeepSeek-V4.1-Flash-1017'})
RUN_ID = 'v5-slot-completeness-real-G3-pending-approval'
# Main explicitly named this candidate after the pause. No latest-file search.
CANDIDATE_RELATIVE_PATH = 'evidence/upgrade/v5.0/blueprint-slot-completeness/candidate.json'
EXPECTED_CANDIDATE_BUNDLE = '71155c8b17d70383499ad845db6b3e7e4b61a620c52cb9ecb803c69ea1618dc4'
EXPECTED_UNKNOWN_IDENTITY_SHA256 = 'b7490c5f157e75f973533e518a1e245c1ea0a3818318065c9c7ddf5e5b59085e'
MAX_CALLS = 1
MAX_RESERVED_UNITS = 200_000_000
CASES = (
    {'case_id': 'G3', 'theme': '校园生态实验楼标本交接：三间相连实验室保留采样资料与维护装置，需要跨房间核对材料后完成离楼检查。', 'room_count': 3, 'difficulty': 'hard', 'host_seed': 1, 'expected_family': 'mapping_v1', 'cap_units': 200_000_000},
)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


class StopRun(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def source_map():
    """Bind all 410 named sources, the candidate file bytes, and this runner."""
    candidate_path = ROOT / CANDIDATE_RELATIVE_PATH
    candidate = json.loads(candidate_path.read_text(encoding='utf-8'))
    expected = candidate.get('source_sha256')
    if (candidate.get('source_count') != 410 or not isinstance(expected, dict)
            or len(expected) != 410 or candidate.get('source_bundle_sha256') != EXPECTED_CANDIDATE_BUNDLE):
        raise StopRun('UNAPPROVED_PRODUCT_CANDIDATE')
    sources = {}
    for name, digest in expected.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise StopRun('CANDIDATE_SOURCE_PATH_INVALID')
        actual = sha(path.read_bytes())
        if actual != digest:
            raise StopRun('PRODUCT_SOURCE_CHANGED')
        sources[name] = actual
    sources[CANDIDATE_RELATIVE_PATH] = sha(candidate_path.read_bytes())
    sources[str(Path(__file__).resolve().relative_to(ROOT)).replace('\\', '/')] = sha(Path(__file__).read_bytes())
    return sources


def payload(messages, max_tokens):
    return {'model': MODEL, 'messages': messages, 'max_tokens': max_tokens,
            'thinking': {'type': 'disabled'}, 'stream': False,
            'response_format': {'type': 'json_object'}}


def estimate(body, max_tokens):
    from backend.app.ai.budget import cost_units
    encoded = json.dumps(body, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    bound = len(encoded) * 4 + 8192
    return {'payload_utf8_bytes': len(encoded), 'input_token_bound': bound,
            'output_token_bound': max_tokens, 'cost_upper_units': cost_units(bound, max_tokens),
            'cost_upper_cny': cost_units(bound, max_tokens) / 1e9, 'payload_sha256': sha(encoded)}


def raw_write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def prepare():
    preview_path = OUT / 'offline-preview-v1.json'
    if preview_path.exists() or (OUT / 'execute-started.json').exists():
        raise StopRun('PREVIEW_OR_EXECUTION_ALREADY_EXISTS')
    sources = source_map()
    from backend.app.ai.v5 import GenerationService
    from backend.app.domain.blueprints import select_blueprint
    generations = []
    for case in CASES:
        blueprint = select_blueprint(case['room_count'], case['difficulty'], seed=case['host_seed'])
        if blueprint.family != case['expected_family']:
            raise StopRun('CONTROLLED_HOST_FAMILY_MISMATCH')
        messages = GenerationService.messages(theme=case['theme'], room_count=case['room_count'],
            difficulty=case['difficulty'], blueprint=blueprint)
        body = payload(messages, 6000)
        bound = estimate(body, 6000)
        if bound['cost_upper_units'] > case['cap_units']:
            raise StopRun('GENERATION_PREVIEW_BOUND_EXCEEDED')
        generations.append({**case, 'scope': 'v5_generation', 'json_mode': True,
            'timeout_seconds': 60, 'blueprint_id': blueprint.blueprint_id,
            'controlled_host_selection': True, 'public_seed_api_added': False,
            'payload': body, 'bound': bound})
    if sum(case['bound']['cost_upper_units'] for case in generations) > MAX_RESERVED_UNITS:
        raise StopRun('PREVIEW_TOTAL_BOUND_EXCEEDED')
    if source_map() != sources:
        raise StopRun('SOURCE_CHANGED_DURING_PREPARE')
    value = {'kind': 'offline_preview_not_execution', 'prepared_utc': stamp(), 'run_id': RUN_ID,
        'candidate_sha256': sha(canonical(sources).encode()), 'source': sources,
        'product_candidate_path': CANDIDATE_RELATIVE_PATH,
        'product_source_bundle_sha256': EXPECTED_CANDIDATE_BUNDLE,
        'generation_cases': generations,
        'fixed_limits': {'maximum_cases': MAX_CALLS, 'scope': ['G3'],
            'generation_case_cap_cny': 0.20, 'sum_reserved_upper_units': MAX_RESERVED_UNITS,
            'sum_reserved_upper_cny': 0.20, 'automatic_retries': 0,
            'historical_unknown_calls_required': 3, 'evaluation_calls_allowed': 0},
        'execute_prerequisites': [
            'Independent source/payload preflight, then NEW explicit finite human approval. Main alone dispatches.',
            'Main records actual approval reference and creates user-authorization.json bound to this exact preview/source/scope/max1/.20. The file does not itself prove human approval.',
            'Authorization precedes execution marker, configuration, Key and canonical ledger access.',
            'Canonical 10CNY ledger only; old3unknown identity hash unchanged, pending0, not frozen. Newunknown/model anomaly/secret/concurrent ledger changes stop.',
            'Production GenerationService is unchanged. Only Host family choice is controlled in this isolated test process; model content must be real and pass original admission.',
        ],
        'safety': {'prepare_key_or_config_loaded': False, 'prepare_canonical_ledger_opened': False,
            'prepare_game_database_opened': False, 'prepare_provider_or_network_calls': 0,
            'actual_paid_dispatch': False, 'evaluation_invoked': False}}
    raw_write(preview_path, value)
    report = {'kind': 'offline_preparation_only', 'prepared_utc': stamp(),
        'runner_sha256': sha(Path(__file__).read_bytes()), 'preview_sha256': sha(preview_path.read_bytes()),
        'candidate_sha256': value['candidate_sha256'], 'source_count': len(sources),
        'generation_upper_cny': [case['bound']['cost_upper_cny'] for case in generations],
        'authorization_file_created': False, 'actual_command': 'python -B -X utf8 evidence/upgrade/v5.0/blueprint-slot-completeness/real-samples/run.py --prepare',
        'exit_code': 0, 'key_or_config_loaded': False, 'canonical_ledger_opened': False,
        'database_opened': False, 'network_calls': 0, 'paid_calls': 0,
        'limitations': ['Controlled Host selection is disclosed; no public seed parameter is added.',
            'No actual model output, admission or gameplay quality is established by this preview.',
            'Current preparation contains no paid authorization; actual new user approval remains required.']}
    raw_write(OUT / 'preparation-report.json', report)
    print(canonical({'status': 'prepared_only', 'run_id': RUN_ID,
        'candidate_sha256': value['candidate_sha256'], 'generation_upper_cny': report['generation_upper_cny'],
        'key_or_config_loaded': False, 'canonical_ledger_opened': False, 'network_calls': 0}))


def authorization_matches(value, preview, preview_sha256):
    return (isinstance(value, dict) and value.get('approved') is True
        and value.get('run_id') == RUN_ID
        and value.get('preview_file_sha256') == preview_sha256
        and value.get('candidate_sha256') == preview['candidate_sha256']
        and value.get('scope') == ['G3']
        and type(value.get('max_calls')) is int and value['max_calls'] == MAX_CALLS
        and type(value.get('max_reserved_units')) is int and value['max_reserved_units'] == MAX_RESERVED_UNITS
        and isinstance(value.get('actual_user_approval_reference'), str)
        and bool(value['actual_user_approval_reference'].strip()))


def require_authorization(preview):
    try:
        path = OUT / 'user-authorization.json'
        value = json.loads(path.read_text(encoding='utf-8'))
        matches = authorization_matches(value, preview, sha((OUT / 'offline-preview-v1.json').read_bytes()))
    except (OSError, ValueError, TypeError):
        raise StopRun('FRESH_EXPLICIT_AUTHORIZATION_REQUIRED') from None
    if not matches:
        raise StopRun('AUTHORIZATION_SCOPE_OR_BINDING_MISMATCH')
    return {'authorization_sha256': sha(path.read_bytes()),
            'actual_user_approval_reference': value['actual_user_approval_reference']}


def ledger_readonly():
    from backend.app.ai.budget import PROJECT_LEDGER
    if not PROJECT_LEDGER.is_file():
        raise StopRun('CANONICAL_LEDGER_MISSING')
    db = sqlite3.connect(PROJECT_LEDGER.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        db.execute('PRAGMA query_only=ON')
        cap, frozen = db.execute('SELECT cap,frozen FROM budget_config WHERE id=1').fetchone()
        rows = db.execute('SELECT id,state,charged FROM budget_calls ORDER BY id').fetchall()
    finally:
        db.close()
    unknown = [(ident, state) for ident, state, _ in rows if state == 'unknown']
    return {'cap_units': cap, 'frozen': bool(frozen), 'charged_upper_units': sum(row[2] for row in rows),
        'calls': len(rows), 'unknown_calls': len(unknown), 'pending_calls': sum(row[1] == 'reserved' for row in rows),
        'unknown_identity_sha256': sha(canonical(unknown).encode()), '_all_ids': {row[0] for row in rows}}


def public_snapshot(value):
    return {key: item for key, item in value.items() if not key.startswith('_')}


class Controller:
    def __init__(self, preview, key, baseline):
        self.preview = preview; self.secrets = {key}; self.key = key; self.baseline = baseline
        self.reserved_units = 0; self.attempts = []; self.stopped = None
        self.current_case = None; self.call_ids = set(); self.selected = {}

    def stop(self, code):
        # The API worker sanitizes exceptions; retain a durable in-process stop.
        self.stopped = code
        raise StopRun(code)

    def add_secret(self, value):
        if isinstance(value, str) and value: self.secrets.add(value)

    def scrub(self, value):
        if isinstance(value, str):
            for secret in sorted(self.secrets, key=len, reverse=True): value = value.replace(secret, '[REDACTED]')
            return value
        if isinstance(value, list): return [self.scrub(item) for item in value]
        if isinstance(value, tuple): return [self.scrub(item) for item in value]
        if isinstance(value, dict): return {self.scrub(str(key)): self.scrub(item) for key, item in value.items()}
        return value

    def secret_present(self, value):
        text = canonical(value)
        return any(secret and secret in text for secret in self.secrets)

    def save(self, name, value):
        raw_write(OUT / name, self.scrub(value))

    def journal(self, value):
        line = canonical(self.scrub(value)) + '\n'
        fd = os.open(OUT / 'dispatch-journal.jsonl', os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try: os.write(fd, line.encode()); os.fsync(fd)
        finally: os.close(fd)

    def safe_ledger(self):
        current = ledger_readonly()
        if (current['cap_units'] != 10_000_000_000 or current['frozen'] or current['pending_calls']
                or current['unknown_calls'] != 3 or current['unknown_identity_sha256'] != self.baseline['unknown_identity_sha256']):
            self.stopped = 'LEDGER_UNSAFE_OR_NEW_UNKNOWN'; raise StopRun(self.stopped)
        foreign = current['_all_ids'] - self.baseline['_all_ids'] - self.call_ids
        if foreign: self.stopped = 'CONCURRENT_LEDGER_CHANGE'; raise StopRun(self.stopped)
        return current

    def select(self, original_select, room_count, difficulty, *, seed=None):
        """Only the isolated test's Host family choice is controlled, once per case."""
        case = next((case for case in CASES if case['case_id'] == self.current_case), None)
        if (case is None or self.current_case in self.selected or seed is not None
                or type(room_count) is not int or room_count != case['room_count']
                or difficulty != case['difficulty'] or self.stopped):
            self.stop('UNAPPROVED_OR_REPEATED_HOST_SELECTION')
        blueprint = original_select(room_count, difficulty, seed=case['host_seed'])
        reviewed = next(case for case in self.preview['generation_cases'] if case['case_id'] == self.current_case)
        if blueprint.family != case['expected_family'] or blueprint.blueprint_id != reviewed['blueprint_id']:
            self.stop('CONTROLLED_HOST_SELECTION_CHANGED')
        self.selected[self.current_case] = {'blueprint_id': blueprint.blueprint_id,
            'family': blueprint.family, 'host_seed': case['host_seed'], 'controlled_host_selection': True}
        return blueprint

    def begin(self, messages, tools, limits, scope, tool_choice):
        ident = self.current_case
        if self.stopped or ident not in {'G3'} or ident in self.attempts:
            self.stop('STOPPED_OR_DUPLICATE_CASE')
        if ident not in self.selected:
            self.stop('MISSING_CONTROLLED_HOST_SELECTION')
        try:
            current_sources = source_map()
        except StopRun as error:
            self.stop(error.code)
        if current_sources != self.preview['source']:
            self.stop('SOURCE_CHANGED')
        if (tools or tool_choice != 'none' or scope != 'v5_generation' or limits.max_tokens != 6000
                or limits.timeout_seconds != 60 or limits.max_cost_units != 200_000_000 or limits.json_mode is not True):
            self.stop('UNAPPROVED_PROFILE')
        body = payload(messages, 6000); bound = estimate(body, 6000)
        if self.secret_present(body):
            self.stopped = 'SECRET_IN_MODEL_PAYLOAD'; raise StopRun(self.stopped)
        if (bound['cost_upper_units'] > 200_000_000
                or self.reserved_units + bound['cost_upper_units'] > MAX_RESERVED_UNITS
                or len(self.attempts) >= MAX_CALLS):
            self.stop('RUN_BOUND_EXCEEDED')
        reviewed = next(case for case in self.preview['generation_cases'] if case['case_id'] == ident)
        if bound['payload_sha256'] != reviewed['bound']['payload_sha256']:
            self.stop('PAYLOAD_DIFFERS_FROM_REVIEWED_PREVIEW')
        before = self.safe_ledger()
        self.save(ident + '-exact-payload.json', {'case_id': ident,
            'source_candidate_sha256': self.preview['candidate_sha256'], 'scope': scope,
            'selection': self.selected[ident], 'payload': body, 'bound': bound,
            'ledger_before': public_snapshot(before)})
        self.attempts.append(ident); self.reserved_units += bound['cost_upper_units']
        self.journal({'phase': 'before_dispatch', 'case_id': ident, 'utc': stamp(), 'bound': bound,
            'attempt_number': len(self.attempts), 'sum_reserved_upper_units': self.reserved_units, 'automatic_retry': False})
        return ident, bound


class CaptureProvider:
    """Retains the reviewed round3 provider capture/model/secret/ledger protocol."""
    def __init__(self, config, ledger, controller):
        from backend.app.ai.provider import DeepSeekProvider
        self.inner = DeepSeekProvider(config, ledger=ledger)
        self.controller = controller; self.last_response_metadata = None

    def check_model_anomaly(self, reply=None):
        metadata = self.inner.last_response_metadata
        models = []
        if isinstance(metadata, dict) and 'reported_model' in metadata:
            models.append(metadata['reported_model'])
        if reply is not None: models.append(reply.reported_model)
        if any(model not in APPROVED_REPORTED_MODELS for model in models):
            self.controller.stopped = 'MODEL_ANOMALY_STOP'; return True
        return False

    async def complete(self, messages, tools, limits, *, scope, tool_choice):
        c = self.controller; ident, bound = c.begin(messages, tools, limits, scope, tool_choice)
        try:
            reply = await self.inner.complete(messages, tools, limits, scope=scope, tool_choice=tool_choice)
            self.last_response_metadata = self.inner.last_response_metadata
            if reply.call_id: c.call_ids.add(reply.call_id)
            if self.check_model_anomaly(reply): raise StopRun('MODEL_ANOMALY_STOP')
            contains_secret = c.secret_present(reply.content or '')
            c.save(ident + '-provider-result.json', {'case_id': ident, 'fictional_test_content': True,
                'content_redacted': reply.content, 'content_raw_sha256': sha((reply.content or '').encode()),
                'usage': reply.usage, 'requested_model': reply.requested_model, 'reported_model': reply.reported_model,
                'finish_reason': reply.finish_reason, 'call_id': reply.call_id,
                'cost_upper_cny': reply.cost_upper_cny, 'secret_detected': contains_secret})
            after = c.safe_ledger()
            c.journal({'phase': 'after_dispatch', 'case_id': ident, 'utc': stamp(), 'outcome': 'response',
                'usage': reply.usage, 'ledger_after': public_snapshot(after)})
            if contains_secret: c.stopped = 'SECRET_IN_MODEL_RESPONSE'; raise StopRun(c.stopped)
            return reply
        except BaseException as error:
            self.last_response_metadata = self.inner.last_response_metadata
            call_id = getattr(error, 'call_id', None) or (self.last_response_metadata or {}).get('call_id')
            if call_id: c.call_ids.add(call_id)
            anomaly = self.check_model_anomaly()
            code = 'MODEL_ANOMALY_STOP' if anomaly or c.stopped == 'MODEL_ANOMALY_STOP' else getattr(error, 'code', 'INTERRUPTED_OR_INTERNAL')
            if not isinstance(code, str) or not re.fullmatch('[A-Z_]{1,64}', code): code = 'SANITIZED_PROVIDER_FAILURE'
            try: after = public_snapshot(c.safe_ledger())
            except BaseException: after = {'status': 'unsafe_or_unavailable'}
            c.journal({'phase': 'after_dispatch', 'case_id': ident, 'utc': stamp(), 'outcome': 'failed',
                'error_code': code, 'ledger_after': after})
            raise


def make_temp_client(app, add_secret):
    from fastapi.testclient import TestClient
    client = TestClient(app, base_url='http://127.0.0.1:8001', headers={'Origin': 'http://127.0.0.1:8001'})
    csrf = client.get('/api/v2/auth/csrf').json()['data']['csrf_token']; add_secret(csrf)
    for value in client.cookies.values(): add_secret(value)
    client.headers['X-CSRF-Token'] = csrf
    password = secrets.token_urlsafe(24); add_secret(password)
    response = client.post('/api/v2/auth/register', json={'username': 'blueprint_real_samples', 'password': password})
    if response.status_code != 201: raise StopRun('TEMP_AUTH_FAILED')
    data = response.json()['data']
    add_secret(data['csrf_token']); add_secret(data['auth_context'])
    for value in client.cookies.values(): add_secret(value)
    client.headers.update({'X-CSRF-Token': data['csrf_token'], 'X-Auth-Context': data['auth_context']})
    return client


def version_body(state):
    return {'request_id': str(uuid4()), 'revision': state['revision'], 'generation': state['generation']}


def execute(preview):
    if source_map() != preview['source']:
        raise StopRun('SOURCE_CHANGED_SINCE_REVIEWED_PREVIEW')
    if sha(canonical(preview['source']).encode()) != preview['candidate_sha256']:
        raise StopRun('PREVIEW_SOURCE_HASH_MISMATCH')
    # The actual approval record is checked before any marker/config/Key/ledger.
    authorization = require_authorization(preview)
    marker = OUT / 'execute-started.json'
    try: fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError: raise StopRun('RUN_ALREADY_STARTED_NO_RETRY') from None
    try:
        os.write(fd, canonical({'run_id': RUN_ID, 'utc': stamp(), 'single_use_no_resume_or_retry': True,
            'candidate_sha256': preview['candidate_sha256'], 'authorization_sha256': authorization['authorization_sha256']}).encode())
        os.fsync(fd)
    finally: os.close(fd)
    controller = None; cases = []; exit_code = 1; run_failure_code = None
    try:
        from backend.app.ai.provider import DeepSeekConfig
        from backend.app.ai.budget import BudgetLedger, PROJECT_LEDGER
        from backend.app.ai.v5 import GenerationService
        from backend.app.domain import blueprints
        config = DeepSeekConfig.from_environment()
        if (not config.api_key.strip() or config.model != MODEL
                or config.base_url.rstrip('/') != 'https://api.deepseek.com'):
            raise StopRun('MISSING_OR_UNAPPROVED_PROVIDER_CONFIG')
        baseline = ledger_readonly()
        if (baseline['cap_units'] != 10_000_000_000 or baseline['frozen']
                or baseline['unknown_calls'] != 3 or baseline['pending_calls']
                or baseline['unknown_identity_sha256'] != EXPECTED_UNKNOWN_IDENTITY_SHA256):
            raise StopRun('INITIAL_LEDGER_UNSAFE')
        controller = Controller(preview, config.api_key, baseline)
        controller.save('authorization-binding.json', authorization)
        controller.save('ledger-before.json', public_snapshot(baseline))
        ledger = BudgetLedger(PROJECT_LEDGER)
        def factory(key):
            if key != config.api_key: raise StopRun('REQUEST_KEY_CHANGED')
            return CaptureProvider(config, ledger, controller)
        original_select = blueprints.select_blueprint
        with tempfile.TemporaryDirectory(prefix='v5-slot-completeness-approved-real-G3-') as tmp:
            os.environ['GAMEPLAY_VERSION'] = 'v5'
            os.environ['SQLITE_PATH'] = str(Path(tmp) / 'game-v5.sqlite')
            os.environ['AI_PROVIDER'] = 'mock'
            from backend.app.main import create_v5_app
            app = create_v5_app(generation_service=GenerationService(factory))
            client = make_temp_client(app, controller.add_secret)
            # In this isolated process only: retain the production generate method
            # and seed only its one Host selection through the original selector.
            with patch.object(blueprints, 'select_blueprint',
                    side_effect=lambda room_count, difficulty, *, seed=None:
                        controller.select(original_select, room_count, difficulty, seed=seed)):
                for case in CASES:
                    controller.safe_ledger(); controller.current_case = case['case_id']
                    response = client.post('/api/v2/level-generations', json={
                        'request_id': 'item-context-real-' + case['case_id'], 'theme': case['theme'],
                        'room_count': case['room_count'], 'difficulty': case['difficulty']},
                        headers={'X-AI-Api-Key': config.api_key})
                    record = {'case_id': case['case_id'], 'api_status': response.status_code,
                        'theme': case['theme'], 'room_count': case['room_count'], 'difficulty': case['difficulty'],
                        'real_model_attempted': case['case_id'] in controller.attempts,
                        'controlled_host_selection': controller.selected.get(case['case_id']),
                        'public_seed_api_added': False, 'model_reply_repaired_or_substituted': False}
                    job = response.json().get('data', {}).get('job')
                    if job:
                        job = client.get('/api/v2/level-generations/' + job['job_id']).json()['data']['job']
                        record['job'] = job
                    if job and job['status'] == 'ready':
                        response = client.post('/api/v2/sessions', json={
                            'request_id': 'item-context-play-' + case['case_id'], 'mode': 'generated', 'level_id': job['level_id']})
                        if response.status_code not in {200, 201}: raise StopRun('GENERATED_SESSION_FAILED')
                        sid = response.json()['data']['session_id']; state = response.json()['data']['visible_state']
                        owner = app.state.v5_database.authenticate(client.cookies.get('campus_v5_session'))
                        store = app.state.v5_database.owned(owner, sid); witness = store.rules.compiled.witness
                        # Private test-answer material remains local evidence only;
                        # it is never included in any later model request.
                        private_dir = OUT / 'raw-sensitive'
                        private_dir.mkdir(mode=0o700, exist_ok=False)
                        definition_file = 'raw-sensitive/' + case['case_id'] + '-private-definition-local.json'
                        witness_file = 'raw-sensitive/' + case['case_id'] + '-witness-local.json'
                        replay_file = 'raw-sensitive/' + case['case_id'] + '-api-replay-local.json'
                        controller.save(definition_file, {'local_only': True,
                            'not_for_model_or_publication': True, 'definition': store.rules.compiled.private_dump()})
                        controller.save(witness_file, {'local_only': True,
                            'not_for_model_or_publication': True, 'witness': witness})
                        trace = {'local_only': True, 'not_for_model_or_publication': True,
                            'definition_hash': store.rules.compiled.definition_hash,
                            'initial_visible_state_sha256': sha(canonical(state).encode()),
                            'steps': [], 'complete': False, 'final_visible_state': state}
                        controller.save(replay_file, trace)
                        for index, action in enumerate(witness):
                            replay = client.post(f'/api/v2/sessions/{sid}/actions', json={**version_body(state), **action})
                            value = replay.json()
                            step = {'index': index, 'tool': action['tool'], 'http_status': replay.status_code,
                                'api_result_sha256': sha(canonical(value).encode())}
                            if replay.status_code == 200:
                                state = value['data']['visible_state']
                                step['visible_state_sha256'] = sha(canonical(state).encode())
                            trace['steps'].append(step); trace['final_visible_state'] = state
                            controller.save(replay_file, trace)
                            if replay.status_code != 200: raise StopRun('REAL_WITNESS_REPLAY_FAILED')
                        if state['status'] != 'won' or state['room_id'] != 'EXIT': raise StopRun('REAL_WITNESS_NOT_EXIT')
                        trace['complete'] = True
                        controller.save(replay_file, trace)
                        record.update(status='ready_and_replayed', definition_hash=store.rules.compiled.definition_hash,
                            definition_version=store.rules.compiled.version, witness_actions=len(witness),
                            witness_sha256=sha(canonical(witness).encode()), settlement=state['settlement'],
                            local_only_private_evidence=[definition_file, witness_file, replay_file],
                            real_api_save_restore_tested=False)
                    else:
                        record.update(status='not_successful', error_code=response.json().get('error', {}).get('code') or (job or {}).get('error_code'))
                    cases.append(record); controller.save(case['case_id'] + '-api-result.json', record)
                    controller.safe_ledger()
                    if controller.stopped: raise StopRun(controller.stopped)
            controller.safe_ledger()
            exit_code = 0 if len(cases) == MAX_CALLS and all(case.get('status') == 'ready_and_replayed' for case in cases) else 1
    except BaseException as error:
        code = getattr(error, 'code', 'SANITIZED_RUN_FAILURE')
        if not isinstance(code, str) or not re.fullmatch('[A-Z_]{1,64}', code): code = 'SANITIZED_RUN_FAILURE'
        run_failure_code = code
        if controller:
            controller.stopped = controller.stopped or code
            controller.save('run-failure.json', {'error_code': code, 'utc': stamp(), 'no_retry': True})
        else: raw_write(OUT / 'run-failure.json', {'error_code': code, 'utc': stamp(), 'no_retry': True})
        exit_code = 1
    finally:
        result = {'kind': 'actual_paid_slot_completeness_G3_validation', 'run_id': RUN_ID,
            'candidate_sha256': preview['candidate_sha256'], 'end_utc': stamp(), 'exit_code': exit_code,
            'scope': ['G3'], 'cases': cases, 'attempted_case_ids': controller.attempts if controller else [],
            'sum_reserved_upper_cny': controller.reserved_units / 1e9 if controller else 0,
            'maximum_reserved_upper_cny': 0.20,
            'stopped_reason': controller.stopped if controller else run_failure_code or 'PRE_DISPATCH_FAILURE',
            'finalization_failures': [],
            'automatic_retries': 0, 'evaluation_invoked': False, 'companion_invoked': False,
            'real_api_save_restore_tested': False,
            'game_database': 'TEMP game-v5.sqlite only; removed after run'}
        try:
            result['source_after'] = source_map()
            if result['source_after'] != preview['source']:
                result['source_after_status'] = 'changed'
                result['stopped_reason'] = result['stopped_reason'] or 'SOURCE_CHANGED_DURING_RUN'
                result['finalization_failures'].append('SOURCE_CHANGED_DURING_RUN')
                exit_code = 1; result['exit_code'] = 1
        except BaseException:
            result['source_after_status'] = 'changed_or_unavailable'
            result['stopped_reason'] = result['stopped_reason'] or 'SOURCE_CHANGED_OR_UNAVAILABLE'
            result['finalization_failures'].append('SOURCE_CHANGED_OR_UNAVAILABLE')
            exit_code = 1; result['exit_code'] = 1
        if controller:
            try:
                controller.save('ledger-after.json', public_snapshot(controller.safe_ledger()))
            except BaseException as error:
                result['ledger_after_status'] = 'unsafe_or_unavailable'
                reason = getattr(error, 'code', 'FINAL_LEDGER_UNAVAILABLE')
                if not isinstance(reason, str) or not re.fullmatch('[A-Z_]{1,64}', reason):
                    reason = 'FINAL_LEDGER_UNAVAILABLE'
                result['ledger_after_error_code'] = reason
                result['stopped_reason'] = result['stopped_reason'] or reason
                result['finalization_failures'].append(reason)
                exit_code = 1
            result['exit_code'] = exit_code
            controller.save('result.json', result)
        else:
            result['exit_code'] = exit_code
            raw_write(OUT / 'result.json', result)
        print(canonical({'run_id': RUN_ID, 'exit_code': exit_code,
            'attempted_case_ids': result['attempted_case_ids'], 'sum_reserved_upper_cny': result['sum_reserved_upper_cny'],
            'automatic_retries': 0}))
    return exit_code


def main():
    os.chdir(ROOT)
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--prepare', action='store_true'); modes.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.prepare: prepare(); return 0
    preview = json.loads((OUT / 'offline-preview-v1.json').read_text(encoding='utf-8'))
    if preview.get('run_id') != RUN_ID: raise StopRun('UNAPPROVED_RUN_ID')
    return execute(preview)


if __name__ == '__main__':
    try: raise SystemExit(main())
    except StopRun as error:
        print(canonical({'status': 'stopped', 'error_code': error.code, 'no_retry': True}))
        raise SystemExit(1)
