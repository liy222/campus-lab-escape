"""Seal strict input schemas and per-case hashes before any judgement calls."""
from datetime import datetime,timezone
from .common import EVALUATOR_ROOT,json_bytes,sha256,strict_json


def main():
    path=EVALUATOR_ROOT/'trusted/freeze.json';freeze=strict_json(path.read_bytes())
    if 'case_sha256' in freeze:raise SystemExit('Already sealed; no mutation permitted.')
    string={'type':'string','minLength':1,'maxLength':4000}
    digest={'type':'string','pattern':'^[0-9a-f]{64}$'}
    def obj(props,required=None,additional=False):return {'type':'object','additionalProperties':additional,'properties':props,'required':list(props) if required is None else required}
    ref=obj({'evidence_id':string,'snippet':string,'expected_raw_sha256':digest},['evidence_id','snippet'])
    claim=obj({'claim_id':string,'criterion_id':string,'release_id':string,'statement':string,'declared_scope':string,
               'declared_na':{'type':'boolean'},'evidence_refs':{'type':'array','maxItems':20,'items':ref},'known_scope_status':string})
    criterion=obj({'title':string,'operation':string,'must_observe':string,'require_execution':{'type':'boolean'},'na_allowed':{'type':'boolean'}})
    contract=obj({'contract_id':{'const':'campus-lab-engineering'},'version':{'const':'1.0.0'},'approved_by':string,
                   'teacher_approval':{'type':'null'},'human_signoff':{'type':'null'},'source_plan':string,'source_plan_raw_sha256':digest,
                   'requirements':{'type':'object','additionalProperties':obj({'must':string,'acceptance':string}),'minProperties':18,'maxProperties':18},
                   'criteria':{'type':'object','additionalProperties':criterion,'minProperties':29,'maxProperties':29},
                   'approved_na':{'type':'array','items':obj({'claim_id':string,'release_id':string,'approval_evidence_id':string,'basis':string})},
                   'policy':obj({'must_cannot_be_downgraded':{'const':True},'states':{'const':['PASS','FAIL','INSUFFICIENT_EVIDENCE','NOT_APPLICABLE']},
                     'no_target_execution':{'const':True},'no_teacher_grade':{'const':True},'no_human_signoff_inference':{'const':True},
                     'positive_requires_valid_evidence':{'const':True},'deterministic_failure_cannot_be_overridden':{'const':True}})})
    source=obj({'candidate_runtime_raw_sha256':digest,'git_blob_sha256':digest,'git_blob_oid':{'type':'string','pattern':'^[0-9a-f]{40}$'},
                'utf8_lf_v1_sha256':digest,'binding':{'enum':['raw_equal','approved_crlf_to_lf_only']},'evidence':{'type':'array','items':string}})
    ev_props={'evidence_id':string,'path':string,'release_id':string,'artifact_raw_sha256':digest,
              'artifact_binding':{'enum':['raw_equal','approved_crlf_to_lf_only']},'artifact_git_blob_sha256':digest,
              'artifact_git_blob_oid':{'type':'string','pattern':'^[0-9a-f]{40}$'},'artifact_utf8_lf_v1_sha256':digest,
              'artifact_source_commit':{'type':'string','pattern':'^[0-9a-f]{40}$'},'exit_code':{'type':['integer','null']},
              'recorded_head':{'type':['object','string','null']},'scope':{'type':['string','null']}}
    evidence=obj(ev_props,['evidence_id','path','release_id','artifact_raw_sha256','artifact_binding'])
    manifest=obj({'release_id':string,'sources':{'type':'object','additionalProperties':source},'evidence':{'type':'array','minItems':1,'maxItems':100,'items':evidence},
       'commit':{'type':'string','pattern':'^[0-9a-f]{40}$'},'tree':{'type':'string','pattern':'^[0-9a-f]{40}$'},'builder_command':{'type':'array','items':string},
       'builder_raw_sha256':digest,'approved_by':string,'approved_at':string,'teacher_approval':{'type':'null'},'human_signoff':{'type':'null'},
       'versions':{'type':'object'},'hash_policy':{'type':'object'},'generated_artifacts':{'type':'object'},'unbound_prior_source_records':{'type':'array'},
       'limitations':{'type':'array','items':string},'superseded_evidence_ids':{'type':'array','items':string},'facts_authoritative_evidence_id':string,
       'addendum_id':string,'synthetic_calibration':{'type':'boolean'}},['release_id','sources','evidence'])
    for name,value in [('claim',claim),('contract',contract),('manifest',manifest),('evidence-index',{'type':'array','items':evidence})]:
        relative='schemas/'+name+'.schema.json';data=json_bytes(value);(EVALUATOR_ROOT/relative).write_bytes(data);freeze['inputs'][relative]=sha256(data)
    # Main future paid gate is mutable trusted-root config, not fixture data or target config.
    freeze['inputs'].pop('trusted/paid-gates.json',None)
    cases=strict_json((EVALUATOR_ROOT/'fixtures/cases.json').read_bytes())['cases']
    freeze['case_sha256']={c['case_id']:sha256(json_bytes(c)) for c in cases}
    freeze['frozen_at']=datetime.now(timezone.utc).isoformat()
    path.write_bytes(json_bytes(freeze));print('Sealed schemas and',len(cases),'individual case hashes before calls.')
    return 0


if __name__=='__main__':raise SystemExit(main())
