"""Final static legacy fixture and reused-method proof; no imports of targets."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
base=ROOT/'evidence/integration/T32-clean-final-20261005T115741Z';workspace=ROOT/'data/reproduction/20261005T115741Z/clean'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
report=json.loads((base/'report.json').read_text(encoding='utf-8'));process=json.loads((ROOT/'evidence/integration/T32-clean-final-process-20261005.json').read_text(encoding='utf-8'))
source=Path(process['actual_command'][process['actual_command'].index('--legacy-fixture')+1]);runtime=workspace/report['legacy_fixture']['runtime_path']
assert sha(source)==sha(runtime)==report['legacy_fixture']['sha256']=='21d992feb895ce5535c6b0b3d731887be9619171351a551935e1d10fc2bfae22'
p=workspace/'tests/api/test_m3.py';t=ast.parse(p.read_text(encoding='utf-8-sig'));c=next(x for x in t.body if isinstance(x,ast.ClassDef) and x.name=='M3Acceptance');methods=[x.name for x in c.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name.startswith('test_')];assert len(methods)==19
with (OUT/'static-supplement.json').open('x',encoding='utf-8') as f:json.dump(dict(legacy_fixture_source=str(source),legacy_fixture_runtime=str(runtime),legacy_fixture_raw_sha256=sha(runtime),Main_reported_legacy_commit=report['legacy_fixture']['commit'],legacy_Git_history_independently_queried=False,reused_M3_methods=methods,test_source_raw_sha256=sha(p),static_parse_only=True,target_imported=False),f,ensure_ascii=False,indent=2)
print('2 static supplemental checks passed')
