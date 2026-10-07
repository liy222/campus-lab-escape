"""Read-only check of exactly the Chrome runner's owned PIDs and ports."""
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
BROWSER=OUT/'20261007T121307604Z-browser/run.json'
record=json.loads(BROWSER.read_text(encoding='utf-8'))
pids=sorted({v['pid'] for v in record['checks'] if v['check']=='stop-owned-process-tree'})
ports=sorted({int(v['arguments'][v['arguments'].index('--port')+1]) for v in record['commands'] if '--port' in v['arguments']})
script='$qaOwnedPids=@('+','.join(map(str,pids))+'); $qaOwnedPorts=@('+','.join(map(str,ports))+'); '
script+=' $qaActivePids=@(Get-Process -Id $qaOwnedPids -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id); '
script+=' $qaListeners=@(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $qaOwnedPorts -contains $_.LocalPort } | Select-Object LocalAddress,LocalPort,OwningProcess); '
script+=' [pscustomobject]@{ active_owned_pids=$qaActivePids; owned_port_listeners=$qaListeners } | ConvertTo-Json -Compress -Depth 4'
args=['powershell','-NoProfile','-Command',script]
run=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
assert run.returncode==0,'Read-only cleanup query failed'
actual=json.loads(run.stdout)
result={'recorded_at':datetime.now(timezone.utc).isoformat(),'command':[sys.executable,'-B','-X','utf8',str(Path(__file__).relative_to(ROOT)).replace('\\','/')],
    'nested_command':args,'exit_code':run.returncode,'stdout':actual,'checked_pids':pids,'checked_ports':ports,
    'owned_cleanup_complete':not actual['active_owned_pids'] and not actual['owned_port_listeners'],
    'policy':'Only read exact PID/port list from successful QA Chrome cleanup; no process killed and existing user services untouched'}
(OUT/'cleanup-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'exit_code':run.returncode,'owned_cleanup_complete':result['owned_cleanup_complete'],'pids':len(pids),'ports':len(ports)},ensure_ascii=False))
raise SystemExit(0 if result['owned_cleanup_complete'] else 1)
