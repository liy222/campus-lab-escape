"""Exact frozen candidate focused API + old archive regression; no full backend suite."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import io
import os
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));os.environ['PYTHONDONTWRITEBYTECODE']='1'
candidate_path=ROOT/sys.argv[1];candidate=json.loads(candidate_path.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
before={p:sha(p) for p in candidate['source_sha256']};assert before==candidate['source_sha256']
folder=ROOT/'evidence/integration/save-delete/qa'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f-api');folder.mkdir(parents=True)
from tests.api import test_save_delete as deletion
from tests.api import test_multiple_saves as saves
from tests.api import test_r1 as base
suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(deletion.SaveDeleteAcceptance),unittest.defaultTestLoader.loadTestsFromTestCase(saves.MultipleSavesAcceptance)])
class CountResult(unittest.TextTestResult):
    def __init__(self,*a,**k):super().__init__(*a,**k);self.subtests=0
    def addSubTest(self,*a,**k):self.subtests+=1;super().addSubTest(*a,**k)
stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=CountResult).run(suite)
(folder/'output.txt').write_text(base.sanitize(stream.getvalue()),encoding='utf-8')
(folder/'http-exchanges.json').write_text(json.dumps(base.sanitize(base.EXCHANGES),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
commands=[{'command':[sys.executable,*sys.argv],'exit_code':0 if result.wasSuccessful() else 1}]
contract_command=[sys.executable,'-B','-X','utf8','contracts/check_contracts.py','--output',str(folder/'contracts.json')]
p=subprocess.run(contract_command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8');commands.append({'command':contract_command,'exit_code':p.returncode})
(folder/'contracts-output.txt').write_text(p.stdout+p.stderr,encoding='utf-8')
after={p:sha(p) for p in candidate['source_sha256']};code=int(not result.wasSuccessful() or p.returncode!=0 or before!=after)
report={'candidate':sys.argv[1],'candidate_sha256':sha(sys.argv[1]),'commands':commands,'exit_code':code,'methods':result.testsRun,'subtests':result.subtests,
    'failure_count':len(result.failures),'error_count':len(result.errors),'checks':deletion.CHECKS_DELETE,'source_sha256_before':before,'source_sha256_after':after,
    'paid_calls':0,'limitations':['Only focused deletion plus unchanged old archive suite; no 127-method suite.','Pending receipt and postdelete rollback are synthetic owned database fault probes.','No user database, real provider, human timing, root launcher or OS restart claim.']}
(folder/'run.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'evidence':str(folder),'exit_code':code,'methods':result.testsRun,'subtests':result.subtests,'failures':len(result.failures),'errors':len(result.errors)}));sys.exit(code)
