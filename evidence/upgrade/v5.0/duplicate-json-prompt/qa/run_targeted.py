"""Run only the frozen DJ2 seven existing nodes after Main GO.

No old suite, actual raw/private artifact, live DB/provider, build/UI/evaluation
or paid call. The previously verified Windows socketpair isolation is reused.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[5]
QA = Path(__file__).resolve().parent
ITEMS = ['tests/v5/test_generation_text_authority.py::test_raw_invalid_v2_never_reaches_v1_helper[duplicate-root]', 'tests/v5/test_generation_text_authority.py::test_raw_invalid_v2_never_reaches_v1_helper[duplicate-nested]', 'tests/v5/test_narrative_guard.py::test_original_strict_json_schema_precede_narrative_guard[duplicate-DUPLICATE_KEY]', 'tests/v5/test_blueprint_generation.py::test_invalid_model_reply_is_rejected_after_one_send_without_repair_retry_or_fallback[duplicate]', 'tests/v5/test_generation.py::test_real_adapter_fake_httpx_generation_profile_and_secret_boundary', 'tests/v5/test_prompt_fixed.py::test_four_byte_unicode_theme_whole_payload_budget_is_measured_without_raising_cap[0]', 'tests/v5/test_prompt_fixed.py::test_four_byte_unicode_theme_whole_payload_budget_is_measured_without_raising_cap[1]']
REQUIRED_INPUTS = {
    'evidence/upgrade/v5.0/duplicate-json-prompt/plan.json',
    'evidence/upgrade/v5.0/duplicate-json-prompt/qa/run_targeted.py',
    'evidence/upgrade/v5.0/duplicate-json-prompt/qa/nodes-v1.json',
    'evidence/upgrade/v5.0/duplicate-json-prompt/qa/audit_request.py',
    'tests/v5/conftest.py',
    'tests/v5/test_generation_text_authority.py',
    'tests/v5/test_narrative_guard.py',
    'tests/v5/test_blueprint_generation.py',
    'tests/v5/test_generation.py',
    'tests/v5/test_prompt_fixed.py',
    'evidence/upgrade/v5.0/narrative-guard/plan.json',
    'evidence/upgrade/v5.0/narrative-guard/qa/run_targeted.py',
    'evidence/upgrade/v5.0/narrative-guard/real-samples/offline-preview-v1.json',
}



def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def selected_items(arguments):
    if arguments.nodes_file is None:
        return ITEMS
    path = arguments.nodes_file.resolve()
    path.relative_to(QA)
    nodes = json.loads(path.read_text(encoding='utf-8'))['nodeids']
    assert isinstance(nodes, list) and nodes and len(nodes) == len(set(nodes))
    assert nodes == ITEMS, 'Only the frozen exact seven-node set is authorized'
    return nodes


def worker(arguments):
    """Only fake ledgers/TEMP databases and injected HTTP transports are allowed."""
    import socket
    import sqlite3
    import threading
    import httpx
    import pytest
    from backend.app.ai.provider import DeepSeekConfig
    attempted = []
    internal_ipc_connects = []
    original_connect = sqlite3.connect
    original_socketpair = socket.socketpair
    original_socket_connect = socket.socket.connect
    original_socket_connect_ex = socket.socket.connect_ex
    socketpair_context = threading.local()
    def deny(*args, **kwargs):
        attempted.append('forbidden_runtime_boundary')
        raise AssertionError('Synthetic QA attempted external network or environment credentials')
    def inside_original_socketpair(address):
        return (getattr(socketpair_context, 'active', False)
                and isinstance(address, tuple) and len(address) in (2, 4)
                and address[0] in {'127.0.0.1', '::1'}
                and type(address[1]) is int and 0 < address[1] <= 65535)
    def guarded_socket_connect(connection, address):
        if inside_original_socketpair(address):
            internal_ipc_connects.append(True)
            return original_socket_connect(connection, address)
        return deny()
    def guarded_socket_connect_ex(connection, address):
        if inside_original_socketpair(address):
            internal_ipc_connects.append(True)
            return original_socket_connect_ex(connection, address)
        return deny()
    def guarded_socketpair(*args, **kwargs):
        previous = getattr(socketpair_context, 'active', False)
        socketpair_context.active = True
        try:
            return original_socketpair(*args, **kwargs)
        finally:
            socketpair_context.active = previous
    def temp_connect(database, *args, **kwargs):
        if str(database) != ':memory:':
            path = Path(database).resolve()
            if not path.is_relative_to(Path(tempfile.gettempdir()).resolve()):
                attempted.append('non_TEMP_database')
                raise AssertionError('Synthetic QA attempted a non-TEMP database')
        return original_connect(database, *args, **kwargs)
    class Safety:
        def pytest_sessionstart(self, session):
            self.patch = pytest.MonkeyPatch()
            self.patch.setattr(socket, 'socketpair', guarded_socketpair)
            self.patch.setattr(socket.socket, 'connect', guarded_socket_connect)
            self.patch.setattr(socket.socket, 'connect_ex', guarded_socket_connect_ex)
            self.patch.setattr(socket, 'create_connection', deny)
            self.patch.setattr(httpx.HTTPTransport, 'handle_request', deny)
            self.patch.setattr(httpx.AsyncHTTPTransport, 'handle_async_request', deny)
            self.patch.setattr(DeepSeekConfig, 'from_environment', deny)
            self.patch.setattr(sqlite3, 'connect', temp_connect)
        def pytest_sessionfinish(self, session, exitstatus):
            if attempted:
                session.exitstatus = 1
            write(Path(arguments.output) / 'runtime-guard.json', {
                'external_network_config_or_nonTEMP_DB_attempts': len(attempted),
                'stdlib_socketpair_local_IPC_connects': len(internal_ipc_connects),
                'all_database_connections_restricted_to_TEMP': True,
                'provider_transports_synthetic_only': True, 'real_paid_calls': 0})
            self.patch.undo()
    command = selected_items(arguments) + ['-q', '-p', 'no:cacheprovider', '--tb=short',
                       '--junitxml=' + str(Path(arguments.output) / 'junit.xml')]
    if arguments.scope:
        command += ['-k', arguments.scope]
    return int(pytest.main(command, plugins=[Safety()]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scope', default='')
    parser.add_argument('--nodes-file', type=Path, help='Frozen exact seven existing node identifiers')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    if args.worker:
        return worker(args)
    if args.candidate is None:
        parser.error('--candidate is required')
    output = args.output.resolve()
    output.relative_to(QA)
    candidate = json.loads(args.candidate.read_text(encoding='utf-8-sig'))
    expected = candidate['source_sha256']
    assert REQUIRED_INPUTS <= set(expected), 'Candidate omits an actual policy/helper input'
    assert expected and Path(__file__).resolve().relative_to(ROOT).as_posix() in expected
    if args.nodes_file is not None:
        assert args.nodes_file.resolve().relative_to(ROOT).as_posix() in expected
    before_matches = all(sha(ROOT / name) == digest for name, digest in expected.items())
    assert before_matches, 'Candidate source mismatch before formal QA'
    output.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, '-B', '-X', 'utf8', str(Path(__file__).resolve()),
               '--worker', '--output', str(output)]
    if args.scope:
        command += ['--scope', args.scope]
    if args.nodes_file is not None:
        command += ['--nodes-file', str(args.nodes_file.resolve())]
    env = os.environ.copy()
    env.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1', AI_PROVIDER='mock')
    env.pop('NARRATIVE_GUARD_QA_OUTPUT', None)
    env.pop('ITEM_CONTEXT_QA_OUTPUT', None)
    env.pop('TEXT_AUTHORITY_QA_OUTPUT', None)
    env.pop('V5_QA_OUTPUT', None)
    env.pop('BLUEPRINT_QA_OUTPUT', None)
    report = {'started_utc': now(), 'candidate_path': str(args.candidate),
        'candidate_sha256': sha(args.candidate), 'source_count': len(expected),
        'source_bundle_sha256': candidate['source_bundle_sha256'], 'source_before_matches': True,
        'actual_command': command, 'pytest_items': selected_items(args), 'scope_filter': args.scope,
        'nodes_file_sha256': sha(args.nodes_file) if args.nodes_file else None,
        'scope': 'Exact seven existing duplicate/profile/budget nodes only; no actual private raw input',
        'required_inputs_explicit_in_candidate': sorted(REQUIRED_INPUTS),
        'timeout_seconds': 120, 'exit_code': 1, 'real_paid_calls': 0}
    try:
        process = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, timeout=120)
        (output / 'output.txt').write_bytes(process.stdout)
        report['exit_code'] = process.returncode
        if report['exit_code'] == 0:
            audit_command = [sys.executable, '-B', '-X', 'utf8', str(QA / 'audit_request.py'),
                             '--candidate', str(args.candidate.resolve()),
                             '--output', str(output / 'static-request-audit.json')]
            report['pure_request_audit_command'] = audit_command
            try:
                audit_process = subprocess.run(audit_command, cwd=ROOT, env=env,
                                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
                (output / 'audit-output.txt').write_bytes(audit_process.stdout)
                report['pure_request_audit_exit_code'] = audit_process.returncode
            except subprocess.TimeoutExpired as error:
                (output / 'audit-output.txt').write_bytes(error.stdout or b'')
                report['pure_request_audit_exit_code'] = 124
            report['exit_code'] = report['pure_request_audit_exit_code']
    except subprocess.TimeoutExpired as error:
        (output / 'output.txt').write_bytes(error.stdout or b'')
        report.update(exit_code=124, error='Targeted synthetic QA timeout')
    finally:
        report['ended_utc'] = now()
        report['source_after_matches'] = all(sha(ROOT / name) == digest for name, digest in expected.items())
        if not report['source_after_matches']:
            report['exit_code'] = 1
        write(output / 'run.json', report)
    print(json.dumps({'output': str(output), 'exit_code': report['exit_code'],
        'source_after_matches': report['source_after_matches']}))
    return report['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
