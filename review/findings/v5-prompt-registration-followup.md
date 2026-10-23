# V5 prompt repair and trusted registration: finite follow-up

Independent QA on `v5.0-prompt-registration-f2aeeade8826fd47` (402 frozen files), 2026-10-23. Source-before/source-after match the candidate. Only the authorized prompt tests, existing fake-HTTPX production adapter method and two offline evaluator CLI commands ran.

The single pytest command passed **11 cases**, exit **0**: nine explicit room/difficulty numeric requirement cases; caller-schema immutability and equivalent validation semantics with the real `title` data property retained; matching requested synthetic examples compiled and replayed to `won`; maximum four-byte Unicode theme cap; and the original production `GenerationService`/`DeepSeekProvider` fake-HTTPX secret-boundary method. These examples/replies are synthetic, not eleven real generations.

For 3/hard and 2000 four-byte Unicode characters, the actual provider serialized 18,251 bytes, estimated 210,392,000 cost units, and rejected `AI_LIMIT_REACHED` against the unchanged 200,000,000-unit cap. The synthetic transport saw zero sends and the isolated fake ledger stayed at zero calls. This is required fail-closed behavior, not permission to increase the cap. The old Starlette/httpx deprecation warning remains.

Evidence: `evidence/upgrade/v5.0/qa/prompt-fixed/20261023T123000891489Z-f3bc3de5/summary.json`, `pytest.txt`, nine `prompt-{room}-{difficulty}.json` observations and `prompt-unicode-cap.json`. The summary records the exact actual pytest command; no other API suite, browser, build, planner-limit, C1/C2/C3 method or calibration was repeated.

The v3-to-v4 normalized proofs changed only the provenance sentence clarifying that C2's actual forbidden `ai/turns` request returned 404 before an admitted AI turn or production service invocation. Current active registration bytes equal v4; fixed pin is `80b312f31b73d3cef3a29575e07d1ca8f4f84d114490edd8289779aa7cb7a63d`. The 53-source projection, original successful five-method command, raw observations, schema and nine artifact hashes match. It deliberately excludes the changed production generation prompt and does not certify GEN01.

Actual commands:

- `python -B -X utf8 -m evaluation.cli precheck --release v5.0-engineering`: exit **0**, `READY`, no issues. Actual report: `evidence/upgrade/v5.0/evaluator-owner/runs/20261023T123104950553Z/report.json`.
- `python -B -X utf8 -m evaluation.cli evaluate --release v5.0-engineering --mode deterministic`: exit **2**, exactly three `INSUFFICIENT_EVIDENCE` results; final identity precheck remained `READY`. Actual report: `evidence/upgrade/v5.0/evaluator-owner/runs/20261023T123105451983Z/report.json`.

The full interpreter paths, commands, exit codes, raw hashes and 402-source maps are in `evidence/upgrade/v5.0/qa/registration-active/20261023T123104720649Z-c31a3caf/summary.json`. READY validates identity and finite observations. It grants no semantic PASS. No paid evaluator entry was invoked.

The read-only round-two preview review also completed, exit **0**: `evidence/upgrade/v5.0/qa/preflightreview-round2.json`. The inverse byte comparison against the previously reviewed executor differs only in one run ID and two fixed preview filenames. Current sources and payload hashes match; independently recomputed generation bounds are 0.134584 / 0.141112 / 0.147544 CNY. Companion payloads remain explicitly unusable placeholders. No executor import, preparation, dispatch, Key read, canonical-ledger access or network call occurred during this review. **New paid execution is not authorized by this result.**

The new prompt explicitly teaches the previously omitted count, recipe-field compatibility, numeric code and forward-access rules. Offline checks establish that these requested structures and boundaries work; they do not establish that the model will follow them. The original three real rejected drafts, skipped A1/A2 and previous failed epochs remain intact. The four earlier offline product findings retain their own closure evidence. Real generation/companion quality and overall release acceptance remain unestablished. Previous sealed offline result is unchanged.
