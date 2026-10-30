# V5 generation reliability: focused QA

**Focused QA:** 66 passed, exit 0. One Starlette/httpx deprecation warning. No real provider call or paid request was made. This does not establish story quality or a general success rate.

## Tests executed

Command:

```text
C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 -m pytest -q tests/v5/test_generation_reliability.py tests/v5/test_passage_semantics.py::test_passage_carrier_names_reject_cabinet_identity_preserve_location tests/v5/test_passage_semantics.py::test_strict_schema_name_gate_precedes_assembly_and_keeps_raw tests/v5/test_narrative_guard.py::test_original_strict_json_schema_precede_narrative_guard tests/v5/test_narrative_guard.py::test_one_production_mock_send_rejected_worker_publishes_no_level tests/v5/test_generation_observability.py::test_actual_content_failure_branches_have_safe_distinct_reasons
```

Environment: `PYTHONUTF8=1`, `PYTHONDONTWRITEBYTECODE=1`. Result log: [pytest.log](../automated/qa-20261030T101456628Z/pytest.log); exit: [exit-code.txt](../automated/qa-20261030T101456628Z/exit-code.txt).

Coverage includes all 36 blueprint/seed metadata combinations (not proof runs), three representative legal-name assemblies with unchanged mechanics and successful compile witnesses, exact safe diagnostics for invalid suffix/access/container names, prompt guidance, continued narrative rejection, and a synthetic MockTransport request rejected once without retry or name leakage. Existing passage-name, narrative and observability regression nodes were included.

The first focused execution exited 1 and is preserved at [initial QA result](../automated/qa-20261030T101351335Z/pytest.log). It exposed puzzle names in two pre-existing SP-01 synthetic fixtures that are outside the current admission vocabulary; the fixtures now use names from the existing requirements helper. The validator vocabulary was not loosened or otherwise changed by this QA. The initial runner-cap assertion also still expected 1.20 CNY after Main tightened the cap to 1.00 CNY. The targeted rerun passed; no product code was changed by this QA owner.

## Offline sample preflight

After the runner’s final cap update, the authorized `--prepare` command completed offline with exit 0:

```text
C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 -m scripts.generation_reliability --prepare
```

Latest preview: [preview.json](../automated/preflight-20261030T101510Z-b0c69e53/preview.json). It describes six one-attempt samples, a conservative total upper bound of **0.99208 CNY**, maximum single-sample upper bound **0.195448 CNY**, against a **1.00 CNY / six-call** cap. The preview records credentials not loaded, ledger not opened, and zero network calls. The command log is [prepare.log](../automated/preflight-command-20261030T101510423Z/prepare.log); exit is 0.

I reviewed that approval validation precedes credential/ledger construction, the actual payload is checked against the preview, each case reaches the provider through one call with no same-case retry, and provider/budget anomalies stop the sample. The earlier previews predate the final cap and are stale. No approval was present for real execution, so **`--execute` was not run**. The latest preview is not evidence of user approval and does not authorize real requests.

After review, the static runner-source assertion in the new test was replaced with a runtime gate check using a private temporary stage and four invalid approval records (unapproved, wrong preview digest, wrong call limit, wrong total limit). Each was rejected before source/payload scans, credential loading, ledger construction, or any execute marker. This one replacement node passed (exit 0); result: [runner-gate pytest.log](../automated/runner-gate-20261030T101909636Z/pytest.log), [exit-code.txt](../automated/runner-gate-20261030T101909636Z/exit-code.txt). The earlier 66-test result remains the execution evidence for the rest of the focused suite; this one-node rerun is not added to or presented as a repeated 67-test run.

## Limits

All executed tests use synthetic content, isolated test databases/ledgers, and MockTransport. No player database was accessed. The six-sample plan is an after-only controlled sample, not a paired comparison or a broad success-rate estimate. Main’s earlier diagnostic review identified recent failures as safe reason `narrative`; no raw source text was used here, and this QA makes no claim that narrative quality was fixed. Human review remains pending.
