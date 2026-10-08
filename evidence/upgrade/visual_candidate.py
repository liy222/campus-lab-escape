"""Main freezes a visual candidate after owners stop; no product mutation."""
import argparse, hashlib, json
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('stage',choices=['v4.0','v4.1','v4.2'])
parser.add_argument('--epoch',default='candidate')
options=parser.parse_args()
root=Path(__file__).resolve().parents[2]
base=json.loads((root/'evidence/upgrade/v4.0/plan.json').read_text(encoding='utf-8'))
def digest(path): return hashlib.sha256((root/path).read_bytes()).hexdigest()
for path,expected in base['backend_contract_sha256'].items():
    assert digest(path)==expected, 'Frozen backend/contract changed: '+path
paths=set(base['backend_contract_sha256'])
paths.update(str(p.relative_to(root)).replace('\\','/') for p in (root/'frontend/src').rglob('*') if p.is_file() and p.suffix in {'.ts','.tsx','.css','.svg','.png','.jpg','.webp','.wav','.ogg','.mp3'})
paths.update(['frontend/package.json','frontend/package-lock.json','frontend/vite.config.ts','frontend/tsconfig.json','frontend/index.html','scripts/dev.py','启动游戏.cmd'])
record={'stage':options.stage,'design':'docs/visual-plan.md','source_sha256':{p:digest(p) for p in sorted(paths)},'level_version':'3.4.0','schema_version':'1.4.0','backend_contract_immutable_count':len(base['backend_contract_sha256']),'source_count':len(paths),'baseline_head':json.loads((root/'evidence/upgrade/v4.0/baseline-candidate.json').read_text(encoding='utf-8'))['head'],'paid_calls':0,'mode':'frozen after implementation owner SOURCE STOP; Main explicit GO required for formal QA'}
target=root/'evidence/upgrade'/options.stage/(options.epoch+'.json')
assert not target.exists(), 'Preserve prior candidate epoch'
target.parent.mkdir(parents=True,exist_ok=True)
with target.open('w',encoding='utf-8',newline='\n') as output: json.dump(record,output,ensure_ascii=False,indent=2);output.write('\n')
print(json.dumps({'candidate':str(target),'source_count':len(paths),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'backend_contract_match':True},ensure_ascii=False))
