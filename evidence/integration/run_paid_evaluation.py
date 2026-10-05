"""Main process-only credential relay for an already approved finite evaluator gate.

Reads only local ignored .env as data; never writes/logs the key, never imports
target backend code, and does not create/reset/copy the canonical budget ledger.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

def credential():
    values = {}
    for original in (ROOT/'.env').read_text(encoding='utf-8-sig').splitlines():
        line=original.strip()
        if not line or line.startswith('#'):
            continue
        name,sep,value=line.partition('=')
        name=name.strip();value=value.strip()
        if not sep or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name) or name in values:
            raise ValueError('invalid local environment data')
        if value.startswith(('"',"'")):
            if len(value)<2 or value[-1]!=value[0]:
                raise ValueError('invalid local environment quoting')
            value=value[1:-1]
        values[name]=value
    key=values.get('MODEL_API_KEY','')
    if not key.strip():
        raise ValueError('local MODEL_API_KEY is missing')
    return key

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--approval-id',required=True)
    p.add_argument('--action',choices=['calibrate','evaluate'],required=True)
    p.add_argument('--release')
    args=p.parse_args()
    if ROOT.resolve()!=Path('D:/深度能力').resolve():
        raise ValueError('approved canonical root required')
    if not re.fullmatch(r'[A-Za-z0-9-]{1,40}',args.approval_id):
        raise ValueError('invalid approval id')
    gates=json.loads((ROOT/'evaluation/trusted/paid-gates.json').read_text(encoding='utf-8'))
    matches=[g for g in gates['approvals'] if g['approval_id']==args.approval_id]
    if len(matches)!=1:
        raise ValueError('existing finite Main gate required')
    gate=matches[0]
    if gate['purpose']!=('calibration' if args.action=='calibrate' else 'claims'):
        raise ValueError('approval purpose mismatch')
    if args.action=='evaluate' and not args.release:
        raise ValueError('registered release required')
    ledger=ROOT/'data/ai-budget.sqlite'
    for path in [ledger,*ledger.parents]:
        if path.is_symlink() or getattr(path.lstat(),'st_file_attributes',0)&0x400:
            raise ValueError('ledger reparse point forbidden')
    with sqlite3.connect(ledger.resolve().as_uri()+'?mode=ro',uri=True) as db:
        config=db.execute('SELECT id,cap,frozen FROM budget_config').fetchall()
        if config!=[(1,10_000_000_000,0)]:
            raise ValueError('unchanged approved budget required')
        if db.execute("SELECT COUNT(*) FROM budget_calls WHERE state IN ('reserved','unknown')").fetchone()[0]:
            raise ValueError('unresolved call blocks dispatch')
        if db.execute('SELECT COUNT(*) FROM budget_calls WHERE id LIKE ?',('eval_'+args.approval_id+'_%',)).fetchone()[0]:
            raise ValueError('gate already used; do not retry')
    output=ROOT/('evidence/integration/paid-evaluation-'+args.approval_id+'-process.json')
    started=output.with_name(output.stem+'-started.json')
    if output.exists() or started.exists():
        raise ValueError('existing dispatch record; do not resend')
    command=[sys.executable,'-B','-X','utf8','-m','evaluation.cli',args.action,'--mode','paid','--approval-id',args.approval_id]
    command+=['--fixture-set','k1-k6-v1'] if args.action=='calibrate' else ['--release',args.release]
    source_hashes={str(f.relative_to(ROOT)) :hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((ROOT/'evaluation').glob('*.py'))}
    environment={k:v for k,v in os.environ.items() if not re.search(r'KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL',k,re.I) and not k.upper().startswith(('MODEL_','AI_','DEEPSEEK_','OPENAI_','ANTHROPIC_'))}
    environment['EVALUATION_MODEL_API_KEY']=credential()
    environment['PYTHONUTF8']='1'
    before={str(f.relative_to(ROOT)) for f in (ROOT/'evaluation/runs').glob('*') if f.is_dir()}
    start_record={'approval_id':args.approval_id,'command':command,'cwd':str(ROOT),'started_at':datetime.now(timezone.utc).isoformat(),
                  'evaluator_source_before':source_hashes,'credential_mapping':'ignored MODEL_API_KEY -> child EVALUATION_MODEL_API_KEY; value omitted',
                  'gate':gate,'scope':'One finite invocation; no retry; original shared CNY10 ledger.'}
    with started.open('x',encoding='utf-8') as f:
        f.write(json.dumps(start_record,ensure_ascii=False,indent=2)+'\n');f.flush();os.fsync(f.fileno())
    proc=subprocess.run(command,cwd=ROOT,env=environment,check=False)
    environment.pop('EVALUATION_MODEL_API_KEY',None)
    after_hashes={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((ROOT/'evaluation').glob('*.py'))}
    after={str(f.relative_to(ROOT)) for f in (ROOT/'evaluation/runs').glob('*') if f.is_dir()}
    result={**start_record,'ended_at':datetime.now(timezone.utc).isoformat(),'actual_exit_code':proc.returncode,
            'evaluator_source_after':after_hashes,'source_unchanged':source_hashes==after_hashes,'new_run_directories':sorted(after-before),
            'wrapper_raw_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with output.open('x',encoding='utf-8') as f:
        f.write(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('Main process record:',output,'; exit:',proc.returncode,'; source unchanged:',result['source_unchanged'])
    return proc.returncode if result['source_unchanged'] else 2

if __name__=='__main__':
    raise SystemExit(main())
