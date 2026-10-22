"""Full Draft2020-12 data validation plus additive route/schema drift check."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT))
from jsonschema import Draft202012Validator, FormatChecker
from contracts.v2.build_contracts import HERE, build, ref
from backend.app.api.v5 import router
from backend.app.domain.generated import Draft, GeneratedRules, compile_level, make_fixture

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path,required=True); args=parser.parse_args()
    if args.output.exists(): raise SystemExit('Refusing to overwrite evidence')
    checks=[]; code=0
    try:
        built=build()
        for name,value in built.items():
            assert json.loads((HERE/name).read_text(encoding='utf-8'))==value, 'CONTRACT_DRIFT:'+name
            if name.endswith('.schema.json'): Draft202012Validator.check_schema(value)
        routes=built['routes.json']['routes']; actual={(method,r.path) for r in router.routes for method in r.methods}
        assert {(r['method'],r['path']) for r in routes}==actual and len(routes)==20, 'ROUTE_DRIFT'
        schema=built['api.schema.json']
        def validate(name,value): Draft202012Validator({**schema,**ref(name)},format_checker=FormatChecker()).validate(value)
        samples=0
        for rooms in range(1,4):
            for difficulty in ('easy','normal','hard'):
                raw=make_fixture(rooms,difficulty); Draft202012Validator(built['level-draft.schema.json']).validate(raw)
                compiled=compile_level(raw,rooms,difficulty); rules=GeneratedRules(compiled); state=rules.initial_state()
                for action in [None,*compiled.witness]:
                    if action: state,_=rules.apply_action(state,action['tool'],action['arguments'])
                    visible=rules.visible_state('contract_fixture',state); visible['level_id']='fixture_level'; validate('visible_state',visible); samples+=1
                assert state.status=='won'
        bad=copy.deepcopy(visible); bad['answers']=['not-public']
        assert list(Draft202012Validator({**schema,**ref('visible_state')}).iter_errors(bad)), 'PRIVATE_FIELD_ALLOWED'
        checks=['generated Draft full schema instances','20 exact route bindings','nine real-rule witness projections including minigames and EXIT','strict unknown public field rejection','reproducible schema artifacts']
        result={'exit_code':0,'checks':checks,'validated_generated_states':samples,'route_count':20}
    except Exception as error:
        code=1; result={'exit_code':1,'checks_completed':checks,'error_type':type(error).__name__,'error':str(error)[:3000]}
    result.update(ended_at=datetime.now(timezone.utc).isoformat(),source_sha256={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob('*')) if p.is_file()},limitations=['Development contract checks, not independent QA or real model validation.','Classic response validation is additionally covered by API integration QA.'],paid_calls=0)
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result,ensure_ascii=False)); return code
if __name__=='__main__': raise SystemExit(main())
