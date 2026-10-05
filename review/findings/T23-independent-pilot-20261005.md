# T23 independent real pilot review

Verdict: PASS for the six observed pilot rows and the frozen formal design. This is not a paid authorization and does not accept formal results.

Files added: `tests/review_e1_results.py`; this report; `evidence/qa/T23-independent-20261005T053500Z/{checks,judgments,result}.json`; `evidence/qa/T23-independent-20261005T053700Z/{checks,judgments,result}.json`; final directory `process-result.json`.

Actual offline command, working directory `D:\深度能力`:

```text
C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 tests/review_e1_results.py --run experiments/runs/20261005T052822923700Z-pilot-real-0378672e --formal-plan experiments/runs/20261002T125600594673Z-formal-plan-949ddff0 --output evidence/qa/T23-independent-20261005T053700Z
```

Actual exit 0, 638/638 checks. First run using output `T23-independent-20261005T053500Z` exited 1, 560/638: all 78 failures were QA reconstruction of request bytes using canonical saved object key order instead of Provider message key order (`role`, `content`). The harness now reconstructs that order and uses original contract tool order. Both results remain. The game, experiment code, inputs, gold and raw responses were not modified.

Baseline remains commit label `7821af4efe0613c20a80ea164c1dab1c0f288bab`, approved manifest raw SHA256 `9c36943cbb6e4fe08b6e176445ba91835fafa79a2077c2155bbf8d613f8b07c1`. Binding rechecks actual source/evidence bytes without Git. Pilot plan canonical hash `476f4615855eac7d6a24322358e1a17635ffffe45b3f06ee4dc5c1d1ed24558b`; formal plan hash `bb9d603d75d16dcf9473e534a38687ce7a90d548035a6ad76ad682a16b459539`. All reviewed result bytes and frozen experiment sources were unchanged across audit. Detailed fingerprints are in `result.json`.

Pilot evidence is six unique rows in planned order, one call ID per row, invocation/finalization journal pairs matching row hashes, HTTP 200, normalized schema outputs, known usage and reported `deepseek-flash`. Offline judging twice produces identical outputs without sample mutation. Input regeneration, independent wire reconstruction and independent unpacking confirm identical public facts in A/B, controlled options and frozen gold. Every expected input exists; no row was dropped, retried or replaced. Both C06 responses remain completed, legal, reference valid and incorrect with `LEGAL_BUT_NOT_USEFUL_NEXT_ACTION`.

Independent summary recomputation equals every saved per-variant field and the Owner calculator: each variant planned/completed/legal/usage 3, correct 2; correct/planned and correct/completed both 2/3. Each prompt/completion total and cache counts recompute. Costs use bound peak rates (input miss 2, hit .04, output 8 CNY/million). Six-row total is 29,751,520 integer units = ¥0.02975152; full history ¥0.01486592 and summary ¥0.01488560. These are conservative ledger charges, not independently verified supplier bills.

Original shared ledger was opened directly with SQLite URI `mode=ro`; no initialization and no writes. All six pilot call IDs match experiment scope, settled state, reservation, charged units and token/cache counts. Owner historical before/after evidence records 6→12 settled, charge 10,354,480→40,106,000 units, frozen=false, unknown/pending=0, matching the pilot delta. Current ledger aggregates are separately recorded because Main's later formal run overlaps this audit; they must not be mistaken for the pilot completion snapshot. No non-experiment call IDs are copied.

The formal design is 12 checkpoints × 2 variants × 3 repeats = 72, each variant 36, AB/BA pair order 18 each. All 72 saved inputs match the current frozen plan, wire hashes, public facts and frozen sample/gold bindings. Retry=false and suggestions_executed=false. This report does not inspect or accept the subsequent formal raw rows.

Real pilot process exit 0 comes from Owner `process-result.json` with actual command/session/chunks, retries 0 and extra probes 0; QA directly observed only its offline process exit. Explicit credential-pattern scan of authorized public result artifacts found no matches; this is not an exhaustive secret certification. No environment, credentials, network or paid call was accessed by QA. Auxiliary Owner artifact indexes are ordinary bookkeeping artifacts, not model observations.

Limits: six fixed checkpoint pairs support no statistical superiority claim; action correctness does not certify every free-text assertion; baseline Git provenance is inherited from the approved manifest; formal T25 requires a separate stable-result review; no human course approval was fabricated.
