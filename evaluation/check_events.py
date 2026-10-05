"""Owner event checks on synthetic isolated Main fixtures; never paid or product QA."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from . import cli
from .cli import output_folder
from .common import EVALUATOR_ROOT, PROJECT_ROOT, EvaluationError, json_bytes, sha256, strict_json
from .engine import Evaluator, deterministic_facts
from .check import junction
from .events import NEW_SCHEMAS, load_registered_events
from .provider import MockProvider
from .reader import EvidenceTools, safe_read
from .trust import load_trusted, load_tools, source_precheck


def source_map():
    paths = list(EVALUATOR_ROOT.glob('*.py')) + list((EVALUATOR_ROOT / 'schemas').glob('*.json')) + list((EVALUATOR_ROOT / 'trusted').rglob('*.json'))
    return {p.relative_to(PROJECT_ROOT).as_posix(): sha256(p.read_bytes()) for p in sorted(paths)}


class SyntheticFixture:
    """approved_by=Main exists only in this owned fixture root, never production."""
    def __init__(self, root, files):
        self.root = root
        self.install = root / 'evaluation'
        self.files = files
        for path in [*NEW_SCHEMAS, 'trusted/contract.json', *[p for p in files if p.startswith('schemas/')]]:
            target = self.install / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((EVALUATOR_ROOT / path).read_bytes())
        self.source = 'product/source.py'
        (root / 'product').mkdir()
        raw = b'# SYNTHETIC OWNER FIXTURE ONLY; NEVER IMPORTED\n'
        (root / self.source).write_bytes(raw)
        source = {'candidate_runtime_raw_sha256': sha256(raw), 'git_blob_sha256': sha256(raw),
                  'git_blob_oid': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest(),
                  'utf8_lf_v1_sha256': sha256(raw), 'binding': 'raw_equal', 'evidence': ['evidence/qa/result.json']}
        self.release = 'synthetic_event_v1'
        self.event_id = 'synthetic-event-v1'
        self.commit = hashlib.sha1(b'SYNTHETIC PRODUCT COMMIT PLACEHOLDER; NOT A PROJECT COMMIT').hexdigest()
        self.run_id, self.identity_id = self.release + ':RUN001', self.release + ':ID001'
        result = {'exit_code': 0, 'synthetic': True, 'observations': 'Synthetic bound execution; no project tests ran.'}
        self.write('evidence/qa/result.json', result)
        identity = {'release_id': self.release, 'product_commit': self.commit, 'exit_code': 0,
                    'source_before': {self.source: sha256(raw)}, 'source_after': {self.source: sha256(raw)},
                    'artifact_hashes': {self.run_id: sha256(json_bytes(result))}, 'synthetic': True}
        self.write('evidence/qa/identity.json', identity)
        records = [{'evidence_id': eid, 'release_id': self.release, 'path': path,
                    'artifact_raw_sha256': sha256((root / path).read_bytes()), 'artifact_binding': 'raw_equal'}
                   for eid, path in [(self.run_id, 'evidence/qa/result.json'), (self.identity_id, 'evidence/qa/identity.json')]]
        ref = {'evidence_id': self.run_id, 'snippet': 'summary', 'expected_raw_sha256': records[0]['artifact_raw_sha256']}
        self.main = {'schema_id': 'event-registration-v1', 'event_id': self.event_id, 'release_id': self.release,
                     'product_commit': self.commit, 'approved_by': 'Main', 'approved_at': datetime.now(timezone.utc).isoformat(),
                     'manifest': {'release_id': self.release, 'commit': self.commit, 'sources': {self.source: source}, 'evidence': records},
                     'claims': {'release_id': self.release, 'claims': [
                         {'claim_id': 'SYN-' + criterion, 'criterion_id': criterion, 'release_id': self.release,
                          'statement': files['trusted/contract.json']['criteria'][criterion]['must_observe'],
                          'declared_scope': 'Synthetic Owner fixture only, not actual project evidence.', 'declared_na': False,
                          'evidence_refs': [deepcopy(ref)], 'known_scope_status': 'SYNTHETIC_OWNER_ONLY'} for criterion in ('A24', 'A26')]},
                     'windows': {self.run_id: {'summary': {'kind': 'json_fields', 'fields': ['exit_code', 'synthetic', 'observations']}},
                                 self.identity_id: {'summary': {'kind': 'json_fields', 'fields': ['release_id', 'product_commit', 'exit_code']}}},
                     'evidence_roles': {self.run_id: 'execution', self.identity_id: 'identity'},
                     'runtime_records': [{'evidence_id': self.run_id, 'identity_evidence_id': self.identity_id,
                         'release_id_field': 'release_id', 'commit_field': 'product_commit', 'exit_code_field': 'exit_code',
                         'source_before_field': 'source_before', 'source_after_field': 'source_after',
                         'artifact_hashes_field': 'artifact_hashes', 'source_paths': [self.source]}],
                     'coverage': [{'claim_id': 'SYN-' + criterion, 'criterion_id': criterion, 'status': 'full', 'gaps': [],
                                  'required_refs': [{'evidence_id': self.run_id, 'snippet': 'summary'}]} for criterion in ('A24', 'A26')],
                     'human_signoff': None, 'teacher_approval': None}
        self.main_path = 'evidence/integration/event-' + self.event_id + '-registration.json'
        self.freeze_path = 'trusted/events/' + self.event_id + '/freeze.json'
        self.seal()

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(json_bytes(value))

    def seal(self):
        self.write(self.main_path, self.main)
        prefix = 'trusted/events/' + self.event_id + '/'
        inputs = {}
        for name in ('manifest', 'windows', 'claims'):
            path = prefix + name + '.json'
            self.write('evaluation/' + path, self.main[name])
            inputs[path] = sha256(json_bytes(self.main[name]))
        self.pin = {'path': self.main_path, 'raw_sha256': sha256(json_bytes(self.main))}
        freeze = {'freeze_id': 'synthetic-event-freeze-v1', 'event_id': self.event_id, 'release_id': self.release,
                  'product_commit': self.commit, 'main_registration': self.pin, 'frozen_at': datetime.now(timezone.utc).isoformat(),
                  'frozen_before_calls': True, 'contract_raw_sha256': sha256((self.install / 'trusted/contract.json').read_bytes()),
                  'legacy_schema_raw_sha256': {p: sha256((self.install / p).read_bytes()) for p in self.files if p.startswith('schemas/')},
                  'inputs': inputs, 'claim_ids': [c['claim_id'] for c in self.main['claims']['claims']],
                  'evidence_ids': [r['evidence_id'] for r in self.main['manifest']['evidence']],
                  'human_signoff': None, 'teacher_approval': None}
        self.write('evaluation/' + self.freeze_path, freeze)
        self.registry = {'registry_id': 'events-registry-v1', 'events': [{'event_id': self.event_id, 'release_id': self.release,
                          'product_commit': self.commit, 'main_registration': self.pin,
                          'event_freeze_raw_sha256': sha256(json_bytes(freeze))}]}
        self.write('evaluation/trusted/events-registry-v1.json', self.registry)

    def change_identity(self, mutator):
        value = strict_json((self.root / 'evidence/qa/identity.json').read_bytes())
        mutator(value)
        self.write('evidence/qa/identity.json', value)
        self.main['manifest']['evidence'][1]['artifact_raw_sha256'] = sha256(json_bytes(value))
        self.seal()

    def tools(self):
        contexts, manifests, windows = load_registered_events(self.root, self.install, self.files, {}, {})
        tools = EvidenceTools(self.root, self.files['trusted/contract.json'], manifests, windows)
        tools.event_contexts = contexts
        return tools

    def archive(self):
        archive_path = 'release/archives/baseline_v1/' + self.source
        destination = self.root / archive_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((self.root / self.source).read_bytes())
        self.main['source_locations'] = {self.source: {'archive_release_id': 'baseline_v1', 'archive_path': archive_path,
                                                      'raw_sha256': sha256(destination.read_bytes())}}
        source = self.main['manifest']['sources'].pop(self.source)
        self.main['manifest']['sources'][archive_path] = source
        self.seal()

    def identity_archive(self):
        self.archive()
        location=self.main['source_locations'].pop(self.source)
        self.source=location['archive_path']
        self.main['source_locations']={self.source:location}
        self.main['runtime_records'][0]['source_paths']=[self.source]
        self.change_identity(lambda v:v.update(source_before={self.source:location['raw_sha256']},source_after={self.source:location['raw_sha256']}))


async def run():
    folder = output_folder()
    before = source_map()
    _, files = load_trusted()
    results = []
    def record(name, action, expected=None):
        try:
            actual = action()
            if expected is not None and actual != expected:
                raise AssertionError()
            results.append({'name': name, 'passed': True, 'actual': actual})
        except Exception as error:
            results.append({'name': name, 'passed': False, 'error_code': error.code if isinstance(error, EvaluationError) else type(error).__name__})
    def rejects(action, code):
        try:
            action()
        except EvaluationError as error:
            return error.code == code
        return False
    record('synthetic Owner event never registered in production', lambda: 'synthetic_event_v1' not in load_tools()[2].event_contexts, True)
    qa_names=[{'reference':{'evidence_id':'SYN-QA'},'text':'{"failures":[],"checks":["synthetic check"]}'}]
    record('event QA failure-name collection is not inferred integer counts',lambda:deterministic_facts(qa_names,event_bound=True)['issues'],[])
    record('legacy sparse-count rejection unchanged',lambda:deterministic_facts(qa_names)['issues'],['INVALID_TEST_COUNTS:SYN-QA'])
    bad_counts=[{'reference':{'evidence_id':'SYN-QA'},'text':'{"tests_run":1,"failures":[],"errors":0,"skipped":0}'}]
    record('event complete malformed test-count record still rejected',lambda:deterministic_facts(bad_counts,event_bound=True)['issues'],['INVALID_TEST_COUNTS:SYN-QA'])
    failed_counts=[{'reference':{'evidence_id':'SYN-QA'},'text':'{"tests_run":1,"failures":1,"errors":0,"skipped":0}'}]
    record('event complete assertion failure remains authoritative',lambda:deterministic_facts(failed_counts,event_bound=True)['failures'],['ASSERTION_FAILURE:SYN-QA'])
    production_tools=load_tools()[2]
    if 'E1-formal-review-v2' in production_tools.event_contexts:
        actual_qa=production_tools.read_evidence('E1-formal-review-v2:QA','verification')
        record('actual Main E1 QA window not misread as sparse test counts',lambda:(isinstance(strict_json(actual_qa['text'])['failures'],list),deterministic_facts([actual_qa],event_bound=True)['issues']),(True,[]))
    with tempfile.TemporaryDirectory(prefix='synthetic-event-owner-', dir=folder) as temporary:
        temp = Path(temporary)
        assert temp.resolve().is_relative_to(folder.resolve())
        serial = 0
        def fixture():
            nonlocal serial
            serial += 1
            root = temp / str(serial)
            root.mkdir()
            return SyntheticFixture(root, files)
        good = fixture()
        tools = good.tools()
        pre = source_precheck(tools, good.release)
        record('result.json explicit runtime identity accepted', lambda: pre['issues'], [])
        record('runtime source before and after bound', lambda: pre['runtime_source_bindings'][0]['source_before'] == pre['runtime_source_bindings'][0]['source_after'], True)
        record('event paid input is whole freeze raw', lambda: tools.event_contexts[good.release].input_sha256 == good.registry['events'][0]['event_freeze_raw_sha256'], True)
        example = folder / 'synthetic-main-registration-example.json'
        example.write_bytes(json_bytes({'artifact_role': 'Synthetic isolated Main fixture only; not production approval or execution evidence', 'registration': good.main}))
        mutations = [
            ('Main arbitrary path', lambda f: f.registry['events'][0]['main_registration'].update(path='elsewhere.json'), 'EVENT_MAIN_PATH_NOT_FIXED', 'registry'),
            ('Main wrong raw pin', lambda f: f.registry['events'][0]['main_registration'].update(raw_sha256='0'*64), 'EVENT_MAIN_RAW_HASH_MISMATCH', 'registry'),
            ('freeze wrong raw pin', lambda f: f.registry['events'][0].update(event_freeze_raw_sha256='0'*64), 'EVENT_FREEZE_RAW_HASH_MISMATCH', 'registry'),
            ('reserved baseline release', lambda f: f.registry['events'][0].update(release_id='baseline_v1'), 'EVENT_DUPLICATE_OR_RESERVED_RELEASE', 'registry'),
            ('manifest product commit swap', lambda f: f.main['manifest'].update(commit='0'*40), 'EVENT_MANIFEST_IDENTITY_MISSING', 'main'),
            ('sources empty', lambda f: f.main['manifest'].update(sources={}), 'EVENT_MANIFEST_IDENTITY_MISSING', 'main'),
            ('target N/A', lambda f: f.main['claims']['claims'][0].update(declared_na=True), 'EVENT_MUST_OR_NA_DOWNGRADE', 'main'),
            ('criterion statement downgrade', lambda f: f.main['claims']['claims'][0].update(statement='Target-defined easy PASS'), 'EVENT_CRITERION_OR_RELEASE_DOWNGRADE', 'main'),
            ('unknown criterion', lambda f: f.main['claims']['claims'][0].update(criterion_id='NOT-A-MUST'), 'EVENT_MUST_OR_NA_DOWNGRADE', 'main'),
            ('source selector alias', lambda f: f.main['runtime_records'][0].update(source_after_field='source_before'), 'EVENT_RUNTIME_SELECTOR_ALIAS', 'main'),
            ('execution role without mapping', lambda f: f.main['runtime_records'].append(deepcopy(f.main['runtime_records'][0])), 'EVENT_RUNTIME_RECORD_SET_MISMATCH', 'main'),
            ('support-only execution claim', lambda f: [f.main['evidence_roles'].update({f.run_id:'support'})], 'EVENT_RUNTIME_RECORD_SET_MISMATCH', 'main'),
            ('identity points to execution', lambda f: f.main['runtime_records'][0].update(identity_evidence_id=f.run_id), 'EVENT_RUNTIME_IDENTITY_NOT_REGISTERED', 'main'),
            ('missing fixed reference raw pin', lambda f: f.main['claims']['claims'][0]['evidence_refs'][0].pop('expected_raw_sha256'), 'EVENT_REFERENCE_RAW_HASH_REQUIRED', 'main'),
            ('cross-release evidence', lambda f: f.main['manifest']['evidence'][0].update(release_id='other_v1'), 'EVENT_DUPLICATE_OR_FOREIGN_EVIDENCE', 'main'),
            ('unknown window kind', lambda f: f.main['windows'][f.run_id]['summary'].update(kind='shell'), 'EVENT_MAIN_SCHEMA_INVALID', 'main'),
            ('negative window line', lambda f: f.main['windows'][f.run_id].update(summary={'kind':'lines','start':0,'count':1}), 'EVENT_MAIN_SCHEMA_INVALID', 'main'),
            ('boolean window line', lambda f: f.main['windows'][f.run_id].update(summary={'kind':'lines','start':True,'count':1}), 'EVENT_MAIN_SCHEMA_INVALID', 'main'),
            ('duplicated Claim', lambda f: f.main['claims']['claims'].__setitem__(1,deepcopy(f.main['claims']['claims'][0])), 'EVENT_FREEZE_SCHEMA_INVALID', 'main'),
        ]
        for name, change, code, kind in mutations:
            f = fixture();change(f)
            if kind == 'main': f.seal()
            else: f.write('evaluation/trusted/events-registry-v1.json', f.registry)
            record('reject ' + name, lambda f=f, code=code: rejects(f.tools, code), True)
        identity_cases = [
            ('missing before', lambda v:v.pop('source_before'), 'EVENT_RUNTIME_FIELD_MISSING'),
            ('empty before/after', lambda v:v.update(source_before={},source_after={}), 'EVENT_RUNTIME_SOURCE_CHANGED_OR_MISSING_MAP'),
            ('changed after', lambda v:v['source_after'].update({'product/source.py':'0'*64}), 'EVENT_RUNTIME_SOURCE_CHANGED_OR_MISSING_MAP'),
            ('wrong release', lambda v:v.update(release_id='other'), 'EVENT_RUNTIME_VERSION_MISMATCH'),
            ('wrong commit', lambda v:v.update(product_commit='0'*40), 'EVENT_RUNTIME_VERSION_MISMATCH'),
            ('boolean exit', lambda v:v.update(exit_code=True), 'EVENT_RUNTIME_EXIT_INVALID'),
            ('unbound equal raw map', lambda v:v.update(source_before={'product/source.py':'0'*64},source_after={'product/source.py':'0'*64}), 'EVENT_RUNTIME_HASH_NOT_BOUND'),
            ('artifact hash swap', lambda v:v.update(artifact_hashes={}), 'EVENT_RUNTIME_ARTIFACT_NOT_BOUND'),
        ]
        for name, change, code in identity_cases:
            f=fixture();f.change_identity(change);t=f.tools()
            record('runtime rejects ' + name, lambda t=t,f=f,code=code: code in [r['code'] for r in source_precheck(t,f.release)['issues']], True)
        for name, path in [('source','product/source.py'),('Main','evidence/integration/event-synthetic-event-v1-registration.json'),('freeze','evaluation/trusted/events/synthetic-event-v1/freeze.json'),('registry','evaluation/trusted/events-registry-v1.json')]:
            f=fixture();t=f.tools();(f.root/path).write_bytes((f.root/path).read_bytes()+b'\n')
            record('post-load mutation '+name,lambda t=t,f=f: bool(source_precheck(t,f.release)['issues']),True)
        f=fixture();f.archive();t=f.tools()
        (f.root/f.source).write_bytes(b'# synthetic later v2; never imported\n')
        record('archived v1 validates after current v2 changes',lambda: source_precheck(t,f.release)['issues'],[])
        record('archive original raw path binds immutable location',lambda: source_precheck(t,f.release)['runtime_source_bindings'][0]['source_locations'][f.source]['archive_path'], 'release/archives/baseline_v1/product/source.py')
        for name,change,code in [
            ('arbitrary archive path',lambda f:f.main['source_locations'][f.source].update(archive_path=f.source),'EVENT_ARCHIVE_PATH_NOT_FIXED_OR_DUPLICATE'),
            ('archive raw hash mismatch',lambda f:f.main['source_locations'][f.source].update(raw_sha256='0'*64),'EVENT_ARCHIVE_SOURCE_HASH_MISMATCH'),
            ('runtime alias missing',lambda f:f.main['source_locations'].update({'different/source.py':f.main['source_locations'].pop(f.source)}),'EVENT_ARCHIVE_PATH_NOT_FIXED_OR_DUPLICATE')]:
            f=fixture();f.archive();change(f);f.seal()
            record('reject '+name,lambda f=f,code=code: rejects(f.tools,code),True)
        f=fixture();f.archive();t=f.tools()
        (f.root/'release/archives/baseline_v1/product/source.py').write_bytes(b'# archive mutated\n')
        record('archive mutation never accepts current runtime v1 claim',lambda: bool(source_precheck(t,f.release)['issues']),True)
        f=fixture();f.identity_archive();t=f.tools()
        record('already archived identity alias binds original map key',lambda:source_precheck(t,f.release)['issues'],[])
        record('identity alias preserves exact registered runtime key',lambda:source_precheck(t,f.release)['runtime_source_bindings'][0]['source_locations'][f.source]['archive_path'],f.source)
        for name,change,code in [
            ('wrong archive safeid',lambda f:f.main['source_locations'][f.source].update(archive_release_id='different_release'),'EVENT_ARCHIVE_PATH_NOT_FIXED_OR_DUPLICATE'),
            ('different archive path',lambda f:f.main['source_locations'][f.source].update(archive_path=f.source+'.other.py'),'EVENT_ARCHIVE_PATH_NOT_FIXED_OR_DUPLICATE'),
            ('identity alias raw mismatch',lambda f:f.main['source_locations'][f.source].update(raw_sha256='0'*64),'EVENT_ARCHIVE_SOURCE_HASH_MISMATCH')]:
            f=fixture();f.identity_archive();change(f);f.seal()
            record('identity alias rejects '+name,lambda f=f,code=code:rejects(f.tools,code),True)
        for name,key,code in [('prefix only','release/archives/baseline_v1/','EVENT_ARCHIVE_PATH_NOT_FIXED_OR_DUPLICATE'),('prefix lookalike','release/archives/baseline_v10/product/source.py','EVENT_ARCHIVE_PATH_NOT_FIXED_OR_DUPLICATE'),('traversal','release/archives/baseline_v1/../product/source.py','UNSAFE_PATH')]:
            f=fixture();f.identity_archive();loc=f.main['source_locations'].pop(f.source);loc['archive_path']=key
            source=f.main['manifest']['sources'].pop(f.source);f.source=key;f.main['source_locations']={key:loc};f.main['manifest']['sources']={key:source};f.main['runtime_records'][0]['source_paths']=[key]
            f.change_identity(lambda v:v.update(source_before={key:loc['raw_sha256']},source_after={key:loc['raw_sha256']}))
            record('identity alias rejects '+name,lambda f=f,code=code:rejects(f.tools,code),True)
        f=fixture();f.identity_archive();f.main['source_locations']['product/source.py']=deepcopy(f.main['source_locations'][f.source]);f.seal()
        record('identity alias rejects duplicated archive value',lambda:rejects(f.tools,'EVENT_ARCHIVE_PATH_NOT_FIXED_OR_DUPLICATE'),True)
        f=fixture();f.identity_archive();parent=(f.root/f.source).parent;destination=f.root/'owned-reparse-target'
        assert parent.resolve().is_relative_to(f.root.resolve()) and destination.resolve().is_relative_to(f.root.resolve())
        parent.rename(destination)
        try:
            junction(parent,destination)
            record('identity alias rejects actual reparse archive',lambda:rejects(f.tools,'REPARSE_POINT'),True)
        except OSError as error:
            results.append({'name':'identity alias rejects actual reparse archive','passed':False,'limitation':'OS reparse fixture creation unavailable','os_code':error.errno})
        f=fixture();f.identity_archive();t=f.tools();(f.root/f.source).write_bytes(b'# identity archive raw mutation\n')
        record('identity archive raw mutation rejected before model',lambda:'EVENT_ARCHIVE_RUNTIME_RAW_MISMATCH' in [r['code'] for r in source_precheck(t,f.release)['issues']],True)
        f=fixture();raw=b'# synthetic CRLF archive\r\n';canonical=raw.replace(b'\r\n',b'\n')
        (f.root/f.source).write_bytes(raw)
        f.main['manifest']['sources'][f.source].update(candidate_runtime_raw_sha256=sha256(raw),git_blob_sha256=sha256(canonical),git_blob_oid=hashlib.sha1(b'blob '+str(len(canonical)).encode()+b'\0'+canonical).hexdigest(),utf8_lf_v1_sha256=sha256(canonical),binding='approved_crlf_to_lf_only')
        f.change_identity(lambda v:v.update(source_before={f.source:sha256(raw)},source_after={f.source:sha256(raw)}));f.archive();t=f.tools()
        record('Main Git CRLF provenance preserves exact archived raw',lambda:source_precheck(t,f.release)['issues'],[])
        (f.root/'release/archives/baseline_v1/product/source.py').write_bytes(canonical)
        record('archive CRLF raw drift has no canonical fallback',lambda:'EVENT_ARCHIVE_RUNTIME_RAW_MISMATCH' in [x['code'] for x in source_precheck(t,f.release)['issues']],True)
        public_path='release/archives/baseline_v1/experiments/.gitignore'
        destination=temp/public_path;destination.parent.mkdir(parents=True);destination.write_bytes(b'# synthetic public ignore only\n')
        record('public archived ignore only source read allowed',lambda:safe_read(temp,public_path,source=True)==b'# synthetic public ignore only\n',True)
        record('public archived ignore default evidence read rejected',lambda:rejects(lambda:safe_read(temp,public_path),'SECRET_OR_BINARY_PATH'),True)
        for path,code in [('experiments/.gitignore','SECRET_OR_BINARY_PATH'),('release/archives/baseline_v1/other/.gitignore','SECRET_OR_BINARY_PATH'),('release/archives/baseline_v1/experiments/.env','UNSAFE_PATH'),('release/archives/baseline_v1/experiments/secret.txt','SECRET_OR_BINARY_PATH'),('release/archives/baseline_v1/experiments/data.bin','SECRET_OR_BINARY_PATH')]:
            record('archive public exception still rejects '+path,lambda path=path,code=code:rejects(lambda:safe_read(temp,path,source=True),code),True)
        f=fixture();f.main['windows'][f.run_id]['summary']['fields'].append('missing_field');f.seal();t=f.tools()
        record('missing snippet field stops before judgement',lambda: 'EVENT_WINDOW_FIELDS_MISSING' in [r['code'] for r in source_precheck(t,f.release)['issues']],True)
        f=fixture();f.main['coverage'][0].update(status='partial',gaps=['Formal 72-row experiment not executed.']);f.seal();t=f.tools()
        provider=MockProvider([]);ev=Evaluator(t,files,provider)
        out,audit=await ev.evaluate(f.main['claims']['claims'][0])
        record('partial coverage never model or PASS',lambda: (out['status'],provider.calls),('INSUFFICIENT_EVIDENCE',0))
        f=fixture();t=f.tools();claim=f.main['claims']['claims'][0]
        script={'claim_id':claim['claim_id'],'release_id':f.release,'status':'PASS','evidence_refs':[{'evidence_id':f.run_id,'snippet':'summary'}],'reason':'Synthetic mock only.','missing_check':[]}
        class MutatingMock(MockProvider):
            async def complete(self,messages):
                reply=await super().complete(messages)
                (f.root/f.source).write_bytes(b'# changed during synthetic judgement\n')
                return reply
        provider=MutatingMock([script]);ev=Evaluator(t,files,provider);out,audit=await ev.evaluate(claim)
        record('source change during model rejects prior PASS',lambda: out['status'],'INSUFFICIENT_EVIDENCE')
        record('actual scripted request retained after change',lambda: out['execution_scope']['actual_model_requests_this_claim'],1)
        record('unaccepted raw suggestion absent after identity change',lambda: audit['raw_suggestion'],None)
        f=fixture();f.change_identity(lambda v:v.update(exit_code=1));t=f.tools();claim=f.main['claims']['claims'][0]
        provider=MockProvider([dict(script,claim_id=claim['claim_id'],release_id=f.release)])
        ev=Evaluator(t,files,provider);out,audit=await ev.evaluate(claim)
        record('bound nonzero exit dominates mock PASS',lambda: out['status'],'FAIL')
        record('valid failure still enters judgement path',lambda: provider.calls,1)
        f=fixture();t=f.tools();(f.root/f.source).write_bytes(b'# corrupted before paid entry\n')
        args=SimpleNamespace(action='evaluate',release=f.release,mode='paid',approval_id='synthetic-do-not-construct')
        blocked=None
        with patch('evaluation.cli.load_tools',return_value=(load_trusted()[0],files,t)), patch('evaluation.cli.find_gate',side_effect=AssertionError('Paid gate must not be constructed')) as gate_trap:
            try: await cli.run(args)
            except EvaluationError as error: blocked=error.code
        record('registered invalid event paid preflight rejects',lambda: blocked,'EVENT_IDENTITY_PRECHECK_FAILED')
        record('invalid event never constructs paid gate',lambda: gate_trap.call_count,0)
        f=fixture();t=f.tools()
        class CLIChangingMock(MockProvider):
            async def complete(self,messages):
                reply=await super().complete(messages)
                (f.root/f.source).write_bytes(b'# changed inside CLI synthetic mock\n')
                return reply
        captured=[]
        original_output_folder=cli.output_folder
        def capture_folder():
            path=original_output_folder();captured.append(path);return path
        with patch('evaluation.cli.load_tools',return_value=(load_trusted()[0],files,t)), patch('evaluation.cli.output_folder',side_effect=capture_folder), patch('evaluation.cli.MockProvider',side_effect=lambda scripts: CLIChangingMock(scripts)):
            code=await cli.run(SimpleNamespace(action='evaluate',release=f.release,mode='mock',approval_id=None))
        stopped_report=strict_json((captured[0]/'report.json').read_bytes())
        record('CLI identity change stops all remaining requests',lambda: (code,[r['execution_scope']['actual_model_requests_this_claim'] for r in stopped_report['results']]),(2,[1,0]))
        record('CLI changed identity cannot retain positive result',lambda: all(r['status']=='INSUFFICIENT_EVIDENCE' and not r['evidence_refs'] for r in stopped_report['results']),True)
        # Verify zero-budget UNKNOWN_RELEASE behavior through the actual public CLI.
        command=[sys.executable,'-B','-X','utf8','-m','evaluation.cli','evaluate','--release','unregistered_event_v1','--mode','paid','--approval-id','unused']
        process=subprocess.run(command,cwd=PROJECT_ROOT,capture_output=True,text=True,encoding='utf-8',timeout=30)
        (folder/'unknown-event-cli.txt').write_text(process.stdout+process.stderr,encoding='utf-8')
        record('CLI unknown event stops before paid construction',lambda: (process.returncode,'UNKNOWN_RELEASE' in process.stdout),(2,True))
    after=source_map()
    record('stable evaluator source and legacy inputs throughout Owner check',lambda: before==after,True)
    record('no target modules actually imported',lambda: any(k=='backend' or k.startswith(('backend.','experiments.','tests.','scripts.')) for k in sys.modules),False)
    report={'kind':'Evaluator Owner synthetic event checks; not independent QA or E1 execution',
            'command':[sys.executable,'-B','-X','utf8','-m','evaluation.check_events'],
            'executed_at':datetime.now(timezone.utc).isoformat(),'checks_count':len(results),'results':results,
            'source_sha256_before':before,'source_sha256_after':after,'actual_paid_calls':0,'network_calls':0,
            'production_ledger_opened':False,'credentials_read':False,'target_modules_imported':False,
            'target_code_executed':False,'production_event_registry_changed':False,'human_signoff':None,'teacher_approval':None}
    code=0 if all(r['passed'] for r in results) else 1;report['exit_code']=code
    (folder/'event-owner-check.json').write_bytes(json_bytes(report))
    print('Event Owner checks',sum(r['passed'] for r in results),'/',len(results),'evidence',folder/'event-owner-check.json')
    for result in results:
        if not result['passed']: print('Failed:',result['name'],result.get('error_code'))
    return code


if __name__=='__main__': raise SystemExit(asyncio.run(run()))
