# V5 finite engineering evaluator

This adapter reads registered evidence through the existing `EvidenceTools` and `Evaluator`. It never imports or runs game code, target scripts, hooks or AGENTS instructions. The three real criteria are limited to C1 nine room/difficulty admissions and actual replays plus twenty rejected examples; C2 two-account read/restore isolation; C3 three saved moments and corrupt-save preservation. They do not certify arbitrary generated levels, absolute security, model quality or human approval.

The trusted contract is `contract.json`, ID `campus-lab-v5-engineering`, version `1.0.0`. `registration.schema.json` is strict, and `registration.template.json` is an intentionally unusable template. The current pinned `registration.json` is READY for source/evidence identity checks. The new loader uses its own EvidenceTools instance. No old contract, freeze, case, engine, reader, provider or old result is changed. The CLI change is only the exact v5 release/fixture routing branch.


## Current read-only status (2026-10-27)

Main's existing precheck returned READY (exit 0); the existing deterministic assessment returned exit 2 with C1, C2 and C3 all `INSUFFICIENT_EVIDENCE`. The 81 evaluator inputs matched before and after, and the 53 registered source entries and nine evidence entries remain matched. READY confirms pinned identity/coverage only, not semantic PASS; this registration does not certify newer Host structure-catalog behavior (36 content-contract variants, not 36 topologies). The three historical unknown paid-call records remain a gate; no paid evaluation, Key, ledger or network access occurred. See the [precheck report](../../evidence/upgrade/v5.0/evaluator-owner/runs/20261027T145049591159Z/report.json), [deterministic report](../../evidence/upgrade/v5.0/evaluator-owner/runs/20261027T145050057576Z/report.json) and [read-only result receipt](../../evidence/upgrade/v5.0/delivery-readiness/readonly-results.json).

## Main registration handoff (future trusted re-registration)

The steps below describe a future trusted re-registration only. They do not automatically modify the current READY registration or its pinned evidence.

Only Main may perform the final registration after actual runs and independent review. Do not fill placeholders from planned scope, completion prose or synthetic fixtures.

1. Keep `REGISTRATION_RAW_SHA256=None` in `evaluation/v5.py` until the concrete record is final. There is no CLI argument, environment override or target-directed path for this pin.
2. Copy the registration template to the fixed `evaluation/v5/registration.json`. Set `status=READY`, exact release/contract/version, and the actual candidate identifier. For every source, record the raw SHA256; the nonempty source map must exactly equal each registered runtime record's source-before and source-after maps. No newline equivalence is permitted here. Runtime outputs from an earlier source epoch cannot be presented as the final candidate.
3. Register each actual output and any Main-derived normalized observation record as separate evidence entries with raw hashes and exact windows. Derived observations must identify their actual operator, actual command and original outputs in provenance; the original outputs should also be pinned and cited. Hashes establish byte identity, not provenance. `proof.template.json` describes the observation shape; its short lists are examples, not execution evidence. Do not manufacture missing rows.
4. Every C1/C2/C3 proof reference must select a `json_fields` window containing `claim_id`, `checks`, `provenance`, plus the registered release/candidate/exit fields. Before/after maps are read by the precheck outside the model snippet. Each model window remains at most 16 KiB, each file at most 10 MiB, and the engine retains its 64 KiB per Claim cap. A raw output too large for a window needs a genuinely derived registered bounded record, not a raised limit.
5. C1 checks: `admissions` has exactly nine distinct `{room_count,difficulty,admitted,replay_won,steps}` observations covering 1..3 x easy/normal/hard; `steps` is positive. `rejections` has twenty distinct `{case_id,category,rejected}` rows, five each of reference/dependency/semantic/layout. C2 checks: distinct nonempty `owner_id`/`intruder_id`, `requests` containing read and restore, each with actual `http_status`, `target_before_sha256`, `target_after_sha256`. C3 checks: `original_definition_sha256`, exactly three `restores` with distinct `moment_id` and `saved_state_sha256`, each containing `restored_state_sha256` and `restored_definition_sha256`; at least one `bad_saves` row with `rejected` and equal `current_before_sha256`/`current_after_sha256`.
6. Fill registration `installation` with the exact `INSTALLATION_PINS` mapping from the adapter; extra installation files can be bound. Do not create a raw self-reference by embedding `v5.py` (which contains the registration pin) inside that same registration. Main's outer final source-stop/QA record binds the loader/CLI, and the adapter additionally snapshots and rechecks their raw bytes before/after dispatch and the complete run.
7. Validate the schema without changing any actual evidence. Compute registration raw SHA256 and replace only `REGISTRATION_RAW_SHA256` with that digest. Main should record this as a separate trusted metadata epoch; do not falsely reuse an earlier evaluator-source hash. Run precheck again. Changing registration, source or evidence after pinning blocks evaluation; do not automatically refresh pins.

The loader requires required windows, raw hashes, exact nonempty source maps and release/candidate binding. Missing observation coverage yields INSUFFICIENT_EVIDENCE. An observed nonzero exit or deterministic failure remains FAIL even if a mock says PASS. Identity changes block judgement; there is no automatic target execution to repair evidence. Real C1-C3 have no N/A permission. Only `fixture-contract.json` permits isolated `NA-DEMO`.

## Commands and outcomes

Use the existing interpreter from the handoff:

```
python -B -X utf8 -m evaluation.cli precheck --release v5.0-engineering
python -B -X utf8 -m evaluation.cli evaluate --release v5.0-engineering --mode deterministic
python -B -X utf8 -m evaluation.cli evaluate --release v5.0-engineering --mode mock
python -B -X utf8 -m evaluation.cli calibrate --fixture-set v5-k1-k6-v1 --mode mock
python -B -X utf8 -m evaluation.cli calibrate --fixture-set v5-k1-k6-v1 --mode deterministic
```

For a future unregistered record, precheck may report NOT_READY and exit 2. In the current read-only check, precheck is READY, while deterministic C1-C3 remain INSUFFICIENT_EVIDENCE. A ready precheck is identity/coverage validation, not semantic PASS. Deterministic-only assessment cannot produce semantic PASS; definite failures may still be FAIL. Real-release mock always asks for INSUFFICIENT_EVIDENCE. Mock judgements are explicitly synthetic.

`--mode paid` immediately stops with `PRIOR_CALL_UNKNOWN_STOP` for this v5 route. It does not open a budget ledger, instantiate PaidProvider, read a Key, send a request, reserve funds or erase historical unknowns. There is no approval-ID escape hatch in this adapter. Reports are written only below `evidence/upgrade/v5.0/evaluator-owner/runs/`.

The offline calibration inputs and answers are explicitly synthetic. K1 supports a mock PASS; K2 has an exit failure that a mock PASS cannot override; K3 has self-claims without execution; K4 includes hostile instructions plus deterministic failure; K5 supplies a fake citation; K6 has legal isolated and illegal MUST N/A examples. Additional isolated probes alter source/evidence bytes, contract/runtime versions, empty or differing source maps, and source/evidence during judgement. Expected and actual states are recorded per case; false PASS must be zero. These are not real model calibration or independent QA. Temporary files are created only under the owned evidence directory and never modify product sources or original fixtures.
