from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
import sys
root=Path.cwd();candidate=json.loads(Path('evidence/upgrade/v3.4/candidate.json').read_text(encoding='utf-8-sig'))
source={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in candidate['source_sha256']}
assert source==candidate['source_sha256']
p=Path('启动游戏.cmd');raw=p.read_bytes();text=raw.decode('utf-8');dev=Path('scripts/dev.py').read_text(encoding='utf-8')
checks={'no_CRCRLF':b'\r\r\n' not in raw,'no_BOM':not raw.startswith(b'\xef\xbb\xbf'),'all_newlines_CRLF':raw.count(b'\n')==raw.count(b'\r\n'),'v34_SQLite':'set "SQLITE_PATH=./data/game-v3.4.sqlite"' in text,'upgrade_environment':'set "GAMEPLAY_VERSION=upgrade"' in text,'explicit_mock_provider':'-m scripts.dev --provider mock --open-browser' in text,'old_versions_preserved':all(x in dev for x in ('legacy','v3.1','v3.2','v3.3'))}
after={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in candidate['source_sha256']};assert after==source
code=0 if all(checks.values()) else 1
record={'command':[sys.executable,'-B','-X','utf8',sys.argv[0]],'exit_code':code,'recorded_at':datetime.now(timezone.utc).isoformat(),'candidate':'evidence/upgrade/v3.4/candidate.json','source_sha256_before':source,'source_sha256_after':after,'candidate_before_after_match':True,'file':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'checks':checks,'actual_root_CMD_started':False,'limitation':'Read-only byte/config check; actual services launched directly by independent browser runner, not rootCMD'}
Path('evidence/upgrade/v3.4/qa/launcher-byte-check.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'exit_code':code,'checks':checks,'source_files':len(source),'actual_root_CMD_started':False},ensure_ascii=False));raise SystemExit(code)