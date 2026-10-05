"""Independent T30 evidence wrapper. Never reads or invokes evaluation target code."""
import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
def sources():
    selected=[]
    for folder in ['backend/app','frontend/src','contracts','scripts','tests/api','tests/e2e','release/archives/baseline_v1']:
        selected += [p for p in (ROOT/folder).rglob('*') if p.is_file() and not {'__pycache__','node_modules','dist'}.intersection(p.parts)]
    selected += [ROOT/p for p in ['tests/qa_ch01_runner.py','docs/SPEC.md','review/change_CH01.md','evidence/integration/E1-source-archive-20261005.json']]
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(selected)}

def main():
    folder=ROOT/'evidence/qa'/('T30-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-api')
    folder.mkdir(parents=True)
    os.environ.update(AI_PROVIDER='mock',PYTHONUTF8='1',SQLITE_PATH=str(folder/'isolated-data'/'default.sqlite'))
    before=sources();started=datetime.now(timezone.utc).isoformat()
    assert before['backend/app/domain/rules.py']=='73a77e8bbc9a26d59a9519315af99f8c640c5447e8e41cff303229278d850bbb'
    stream=io.StringIO();stderr=io.StringIO()
    names=['tests.api.test_r1','tests.api.test_m2','tests.api.test_m3.M3Acceptance','tests.api.test_ch01.CH01Acceptance']
    with contextlib.redirect_stderr(stderr):
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    from tests.api.test_r1 import EXCHANGES,sanitize
    (folder/'unittest-output.txt').write_text(sanitize(stream.getvalue()),encoding='utf-8')
    (folder/'stderr.txt').write_text(sanitize(stderr.getvalue()),encoding='utf-8')
    (folder/'http-exchanges.json').write_text(json.dumps(sanitize(EXCHANGES),ensure_ascii=False,indent=2),encoding='utf-8')
    after=sources();code=0 if result.wasSuccessful() and before==after else 1
    data={'candidate':'CH01 stable v2 raw source hash','schema_version':'1.0.0','level_version':'2.0.0','command':[sys.executable,'-m','tests.qa_ch01_runner'],'started':started,'ended':datetime.now(timezone.utc).isoformat(),'provider':'mock/scripted, no real network model','python':sys.version,'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'source_sha256_before':before,'source_sha256_after':after,'source_unchanged':before==after,'exit_code':code,'evidence_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()},'limits':['RT01 checks deterministic scripted structure boundaries; no real-language robustness claim','RT06 delegated to separate Evaluator QA; target evaluation code not read or invoked','No teacher or human signoff']}
    (folder/'run.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(stream.getvalue());print('Evidence:',folder);return code

if __name__=='__main__': raise SystemExit(main())
