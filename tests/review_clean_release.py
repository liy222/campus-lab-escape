"""Independent T32 read/hash audit: never imports or executes the target helper."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STAMP = '20261005T111419Z'
COMMIT = 'fc70b15b84d811aec62e2a561c468538844b6edf'
ARCHIVE_SHA = 'bc8e8f86b0f861762e3247507688c1eb1f85ea1ac5f7e3cc86e830c04f61e40e'
PINS_SHA = '25ce6a65f8a134cdd58647275840cc8e32f6dfdd4af674d2dafcbbc62f6883d1'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def filehash(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def readjson(path):
    return json.loads(path.read_text(encoding='utf-8'))

def require(ok, message):
    if not ok:
        raise AssertionError(message)

def safe_source(name):
    path = PurePosixPath(name)
    require(not path.is_absolute() and '..' not in path.parts and '\\' not in name, 'Unsafe source path: '+name)
    require(path.name != '.env' and not (path.name.startswith('.env.') and path.name != '.env.example'), 'Secret env member: '+name)
    require(path.suffix.lower() not in {'.sqlite','.sqlite3','.db'}, 'Database member forbidden: '+name)

def materialize(blob, pin):
    # Only Main's explicit per-file policy controls this independent byte operation.
    mode = pin['materialization']
    if mode == 'raw_equal':
        return blob
    require(mode == 'main_pinned_line_endings', 'Unknown Main materialization mode')
    indices = pin['crlf_newline_indices']
    require(all(type(i) is int for i in indices) and indices == sorted(set(indices)), 'Malformed Main newline indices')
    normalized = blob.replace(b'\r\n', b'\n')
    pieces = normalized.split(b'\n')
    require(all(0 <= i < len(pieces)-1 for i in indices), 'Main newline index outside source')
    selected = set(indices)
    out = bytearray()
    for i, piece in enumerate(pieces):
        out.extend(piece)
        if i < len(pieces)-1:
            out.extend(b'\r\n' if i in selected else b'\n')
    return bytes(out)

def gamefields(state):
    return {k: state[k] for k in ['status','room','objects','inventory','clues','exits','progress']}

def audit():
    output = ROOT/'evidence/qa'/('T32-independent-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    output.mkdir(exist_ok=False)
    delivery = ROOT/'evidence/delivery'/('T32-clean-'+STAMP)
    parent = ROOT/'data/reproduction'/STAMP
    clean = parent/'clean'
    pins_path = ROOT/'evidence/integration'/('reproduction-'+STAMP+'-pins.json')
    handoff_path = ROOT/'evidence/integration'/('reproduction-'+STAMP+'-handoff.json')
    result = {'review':'T32 independent read/hash only','actual_command':[sys.executable,*sys.orig_argv[1:]],'cwd':str(ROOT),'started':datetime.now(timezone.utc).isoformat(),'reviewer_source_sha256':filehash(Path(__file__)),'limitations':['No target/helper/test/build/service/evaluator execution by this audit','No Git command: commit provenance is Main-authorized ZIP comment/handoff/pins metadata, not independently fetched Git history','Only clean fc70 package identity, not later root release/event changes or semantic calibration','Recorded dependency versions reviewed; audit does not query or mutate installed packages','Actual .env checked for existence only; no env/database contents read','No real-model call, language-robustness claim, human playtest, teacher approval or human signoff'],'teacher_approval':None,'human_signoff':None,'actual_paid_calls':0}
    try:
        handoff = readjson(handoff_path); pins = readjson(pins_path)
        report = readjson(delivery/'report.json'); verification = readjson(delivery/'verification.json')
        index = readjson(delivery/'evidence-index.json'); materialization = readjson(delivery/'materialization.json')
        require(filehash(pins_path)==PINS_SHA==handoff['pins_sha256']==report['main_pins_sha256'], 'Main pins hash chain mismatch')
        require(filehash(parent/'source.zip')==ARCHIVE_SHA==handoff['archive_sha256']==pins['archive_sha256']==report['archive_sha256'], 'ZIP hash chain mismatch')
        require(all(x['commit']==COMMIT for x in [handoff,pins,report,index,verification]), 'Commit metadata chain mismatch')
        require(Path(handoff['workspace']).resolve()==clean.resolve()==Path(report['workspace']).resolve(), 'Clean root metadata mismatch')
        require(len(pins['files'])==6014==handoff['members']==index['source_member_count']==verification['archive_member_count'], 'Member count chain mismatch')
        require(materialization==pins['files'], 'Delivery materialization differs from explicit Main pins')
        require(report['source_hashes_before']==report['source_hashes_after'] and report['source_unchanged'] and index['source_unchanged'] and verification['archive_source_unchanged'], 'Delivery before/after source map differs')
        result['main_chain']={'commit':COMMIT,'archive_sha256':ARCHIVE_SHA,'pins_sha256':PINS_SHA,'handoff_sha256':filehash(handoff_path),'delivery_report_sha256':filehash(delivery/'report.json'),'evidence_index_sha256':filehash(delivery/'evidence-index.json'),'materialization_sha256':filehash(delivery/'materialization.json')}
        evidence = {}
        require(len(index['files'])==23, 'Expected 23 evidence files')
        for name, record in index['files'].items():
            safe_source(name)
            path = delivery/name
            actual = filehash(path)
            require(actual==record['sha256'] and path.stat().st_size==record['size_bytes'], 'Evidence file hash/size differs: '+name)
            evidence[name]={'sha256':actual,'size_bytes':path.stat().st_size}
        result['delivery_evidence_files']=evidence
        snapshots={}; mapping={}
        with zipfile.ZipFile(parent/'source.zip') as archive:
            infos=archive.infolist(); files=[i.filename for i in infos if not i.is_dir()]
            require(len(files)==len(set(files))==6014 and set(files)==set(pins['files']), 'ZIP file membership differs')
            require(archive.comment.decode('ascii')==COMMIT, 'ZIP commit comment mismatch')
            for name in sorted(files):
                safe_source(name);pin=pins['files'][name];blob=archive.read(name)
                zipped=digest(blob)
                require(zipped==pin['git_blob_sha256'], 'ZIP bytes differ from Main Git-blob pin: '+name)
                restored=materialize(blob,pin);expected=digest(restored)
                require(expected==pin['runtime_raw_sha256'], 'Independent Main materialization differs: '+name)
                actual=filehash(clean/name)
                require(actual==expected==report['source_hashes_before'][name]==report['source_hashes_after'][name], 'Clean/source map byte hash differs: '+name)
                snapshots[name]=actual
                mapping[name]={'zip_git_blob_sha256':zipped,'materialization':pin['materialization'],'crlf_newline_indices':pin.get('crlf_newline_indices'),'independent_runtime_raw_sha256':expected,'clean_read_sha256':actual,'delivery_before_sha256':report['source_hashes_before'][name],'delivery_after_sha256':report['source_hashes_after'][name]}
            result['zip_counts']={'files':len(files),'directories':sum(i.is_dir() for i in infos),'total_members':len(infos)}
        require(set(report['source_hashes_before'])==set(snapshots), 'Delivery source map paths differ')
        result['materialization_mode_counts']=dict(Counter(p['materialization'] for p in pins['files'].values()))
        result['all_6014_raw_mapping']=mapping
        result['clean_source_hashes_before_review']=snapshots
        env_paths=[clean/'.env',clean/'release/archives/baseline_v1/.env']
        require(all(not p.exists() for p in env_paths) and verification['clean_env_absent'], 'Unexpected clean .env exists')
        result['env_existence_only']={str(p):p.exists() for p in env_paths}
        require(filehash(clean/'scripts/reproduce.py')==handoff['helper_raw_sha256']==verification['helper_raw_sha256']=='7dc71165e3d42479884f8c821093c6561e98c240766b03e4a0e69454ea9ec0e9','Helper identity mismatch')
        lock={line.split('==',1)[0]:line.split('==',1)[1].strip() for line in (clean/'backend/requirements.lock.txt').read_text(encoding='utf-8').splitlines() if '==' in line and not line.startswith('#')}
        deps=report['locked_python_dependencies']
        require(len(lock)==len(deps)==verification['locked_python_package_count']==28, 'Locked dependency count mismatch')
        require(all(deps[name]['expected']==deps[name]['actual']==version for name,version in lock.items()), 'Recorded locked versions differ')
        result['locked_dependency_records']=deps
        require(len(report['steps'])==7 and all(s['exit_code']==0 for s in report['steps']), 'Outer command step count/exit mismatch')
        for step in report['steps']:
            require(filehash(delivery/step['log'])==step['log_sha256'],'Outer step log differs')
        summaries=list((delivery/'check').glob('*/summary.json'));require(len(summaries)==1,'Ambiguous unified check result')
        summary=readjson(summaries[0])
        require(summary['exit_code']==0 and summary['source_unchanged'] and len(summary['steps'])==2, 'Unified check did not pass')
        for step in summary['steps']:
            require(step['exit_code']==0 and filehash(summaries[0].parent/step['log'])==step['sha256'], 'Unified child log/exit mismatch')
        text=(summaries[0].parent/'deterministic-tests.txt').read_text(encoding='utf-8')
        require('73 passed, 1 warning, 203 subtests passed' in text,'Test result counts mismatch')
        leaves=[s for s in report['steps'] if s['name']!='unified-check']+summary['steps']
        require(len(leaves)==8 and all(s['exit_code']==0 for s in leaves),'Eight leaf command exits mismatch')
        result['outer_steps']=report['steps'];result['eight_leaf_commands']=leaves
        result['pytest_summary']={'collected_tests':73,'subtests':203,'warnings':1,'scope':'Contains 19 reused M3 unittest methods imported by CH01; not 73 distinct acceptance scenarios'}
        evals={}
        for release,record in verification['evaluators'].items():
            path=delivery/record['evidence_path'];ev=readjson(path)
            require(filehash(path)==record['raw_sha256']==filehash(Path(record['source_path'])), 'Evaluator copied report raw hash mismatch')
            require(ev['exit_code']==record['exit_code']==0 and ev['actual_paid_calls']==record['actual_paid_calls']==0 and not ev['precheck']['issues'] and record['issues']==0 and ev['target_code_executed'] is False, 'Evaluator identity result mismatch')
            evals[release]={'raw_sha256':filehash(path),'source_report_sha256':filehash(Path(record['source_path'])),'exit_code':ev['exit_code'],'issues':ev['precheck']['issues'],'scope':ev['precheck']['scope'],'target_code_executed':False,'actual_paid_calls':0,'evaluator_source_sha256_record':ev['evaluator_source_sha256']}
        require(set(evals)=={'E1-formal-review-v2','baseline_v1'},'Evaluator report set mismatch')
        result['strict_identity_prechecks']=evals
        services={};stops=[]
        for version,name,cwd in [('2.0.0','v2-services.json',clean),('1.0.0','v1-rollback.json',clean/'release/archives/baseline_v1')]:
            service=readjson(delivery/name)
            require(service['status']=='PASS' and service['version']==version and service['provider']=='mock' and service['actual_paid_calls']==0,'Service result mismatch')
            starts=[e for e in service['service_ledger'] if e['event']=='start' and '-m' in e['command'] and 'uvicorn' in e['command']]
            require(len(starts)==2 and starts[0]['pid']!=starts[1]['pid'] and all(Path(e['cwd']).resolve()==cwd.resolve() for e in starts),'Actual distinct service restart/cwd mismatch')
            saved=service['saved_state'];before=service['state_before_restart'];restored=service['restored_state'];receipt=service['unlock_receipt']
            require(saved['level_version']==before['level_version']==restored['level_version']==version,'Service public versions mismatch')
            require(gamefields(restored)==gamefields(saved) and restored['revision']==before['revision']+1 and restored['generation']!=before['generation'] and restored['save']==saved['save'],'Restore state/generation mismatch')
            require(saved['revision']==13 and receipt['revision_before']==12 and receipt['revision_after']==13 and receipt['changed'] and receipt['arguments']=={'item_id':'emergency_key','target_id':'r2_door'},'Unlock receipt mismatch')
            key=lambda s:'emergency_key' in [i['item_id'] for i in s['inventory']]
            if version=='2.0.0':
                require(before['status']=='won' and before['revision']==18 and [i['item_id'] for i in before['inventory']]==['access_card'],'Recorded 18-step terminal state mismatch')
                require(receipt['consumed_item_ids']==['emergency_key'] and not any(key(s) for s in [saved,before,restored]),'v2 key lifecycle mismatch')
            else:
                require(receipt['consumed_item_ids']==[] and all(key(s) for s in [saved,before,restored]),'v1 retained key mismatch')
            require(any(e['destination_id']=='R3' and e['unlocked'] for e in restored['exits']),'Restored R3 door locked')
            stopped=[e for e in service['service_ledger'] if e['event']=='stop'];stops.extend(stopped)
            services[version]={'ledger':service['service_ledger'],'saved_state_sha256':digest(json.dumps(saved,sort_keys=True,ensure_ascii=False).encode()),'restored_generation':restored['generation'],'revision_before_restart':before['revision'],'restored_revision':restored['revision'],'consumed_item_ids':receipt['consumed_item_ids'],'restored_inventory':[i['item_id'] for i in restored['inventory']],'scope':'Independent review of recorded public states/receipts and process ledger; audit itself made no HTTP request'}
        require(len(stops)==5 and all(s['taskkill_exit_code']==0 and s['exit_code']==1 for s in stops),'Five intentional stop exit records mismatch')
        require(report['exit_code']==index['overall_actual_exit_code']==0 and report['actual_paid_calls']==index['actual_paid_calls']==0,'Overall result mismatch')
        v1db=clean/'data/rollback/game-v1.sqlite';v2db=clean/'data/runtime/game-v2.sqlite'
        require(v1db.exists() and v2db.exists() and v1db.resolve()!=v2db.resolve(),'Distinct DB path existence mismatch')
        result['db_path_existence_only']={'v1':str(v1db),'v2':str(v2db),'paths_distinct':True,'both_exist':True,'contents_read':False,'runtime_assignment_provenance':'Delivery report.md identifies these isolated runtime paths; service ledgers independently record different cwd/ports/PIDs'}
        result['service_results']=services;result['five_owned_stops']=stops
        after={p:filehash(clean/p) for p in snapshots}
        require(after==snapshots,'Clean source changed during independent read/hash review')
        result['clean_source_hashes_after_review']=after
        result['clean_source_unchanged_during_review']=True
        result['owner_actual_command_provenance']={'path':'report.md','flags':'-B, no -X option in recorded Delivery reproduction command','actual_command_rerun_by_QA':False}
        result.update(status='PASS_READ_HASH_SCOPE_STOP',exit_code=0)
    except Exception as error:
        result.update(status='FAIL',exit_code=1,error=str(error))
    result['ended']=datetime.now(timezone.utc).isoformat()
    path=output/'result.json';path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':result['status'],'exit_code':result['exit_code'],'evidence':str(path),'sha256':filehash(path),'error':result.get('error')},ensure_ascii=False))
    return result['exit_code']

if __name__ == '__main__':
    raise SystemExit(audit())
