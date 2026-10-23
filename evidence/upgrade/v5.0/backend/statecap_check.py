"""One owner state-cap probe; deadline disabled only to reach the count guard."""
import json,sys,time
from types import SimpleNamespace
from pathlib import Path
from backend.app.domain import generated as domain
from experiments.v5.dataset import inputs

def main():
    row=next(item for item in inputs() if item['case_id']=='LIMIT-03')
    original=domain.time; old_trace=sys.gettrace(); observed={}
    def trace(frame,event,arg):
        if event=='call':
            if frame.f_code.co_name!='solve' or frame.f_globals.get('__name__')!='backend.app.domain.generated': return None
            frame.f_trace_lines=False
        if event=='exception' and frame.f_code.co_name=='solve' and str(arg[1])=='PROOF_UNKNOWN':
            observed['state_peak']=len(frame.f_locals['seen'])
        return trace
    domain.time=SimpleNamespace(monotonic=lambda:0.0); sys.settrace(trace); started=time.perf_counter()
    try:
        try:
            domain.compile_level(row['raw'],row['room_count'],row['difficulty'])
            raise AssertionError('Stress input unexpectedly admitted')
        except ValueError as error:
            assert str(error)=='PROOF_UNKNOWN'
            assert observed.get('state_peak')==25000,observed
    finally:
        domain.time=original; sys.settrace(old_trace)
    result={'kind':'owner_narrow_statecap_probe_not_formal_qa','fixture':'Existing E1 LIMIT-03 stress input only','actual_result':'PROOF_UNKNOWN','state_peak':observed['state_peak'],'elapsed_seconds':time.perf_counter()-started,'controlled_clock':'deadline disabled only in probe; production5s guard unchanged','paid_calls':0,'network_calls':0,'api_suites_run':0,'full_fixture_matrix_run':False}
    Path('evidence/upgrade/v5.0/backend/statecap-probe-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
if __name__=='__main__': main()
