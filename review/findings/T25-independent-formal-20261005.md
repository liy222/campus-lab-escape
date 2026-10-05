# T25 independent formal result review

Final verdict: PASS for integrity, offline judgments, accounting and interpretation of this preserved stopped run. Final audit actual exit 0, 1829/1829 checks; full formal response target remains incomplete, unknown remains unresolved and paid calls remain on hold.

Scope: all 72 terminal records from `experiments/runs/20261005T053334004502Z-formal-real-48d972eb`. This is evidence review, not approval to repeat or extend paid calls. Formal completion of 72 model responses was not achieved.

First offline execution used `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 tests/review_e1_results.py --run experiments/runs/20261005T053334004502Z-formal-real-48d972eb --formal-plan experiments/runs/20261002T125600594673Z-formal-plan-949ddff0 --output evidence/qa/T25-independent-20261005T054700Z`, working directory `D:\深度能力`. Actual exit 1, chunk `73118b`, 1730/1731 checks passed. Only failure: auxiliary Owner index `review/experiment.md` hash recorded `ba747c5089d841710b1f329077c2a15f36f1e6e52124b589e2f626171b0fa48e` while revised explanation bytes hash `6e73e494411a65865b9437b72e86f7972775fe68cd23822d871acf996936ce48`. The result artifacts, gold and experiment implementation passed. Original index and QA failure evidence are retained; Owner is to supply a separate corrective index. Final rerun result will be appended after that correction is available.

Observed terminal sequence is 22 completed, 1 timeout at row 23 (`formal-C12-full_history-1`), then 49 not_called. There are 23 unique paid-attempt IDs, 22 confirmed HTTP 200 normalized responses and one unknown response/delivery. All 72 original row identities, order, input hashes and complete input files match the frozen plan. No failed or uncalled row is dropped, silently made zero usage or replaced. The 22 replies reproduce deterministic offline judgments twice without mutating samples; gold is unchanged. Five completed actions are legal but not accepted useful next steps: C05 A/B, C06 A/B and C08 A.

| Formal metric | A full history | B structured summary |
|---|---:|---:|
| Planned | 36 | 36 |
| Paid attempts | 12 | 11 |
| Completed | 11 | 11 |
| Unknown timeout | 1 | 0 |
| Not called | 24 | 25 |
| Legal / completed | 11/11 | 11/11 |
| Correct / planned | 8/36 (22.22%) | 9/36 (25.00%) |
| Correct / completed | 8/11 (72.73%) | 9/11 (81.82%) |
| Valid references / completed | 11/11 | 11/11 |
| Usage coverage / planned | 11/36 | 11/36 |
| Known prompt tokens mean | 2306.27 | 1936.27 |
| Known prompt tokens median / p95 nearest rank | 2349 / 3853 | 1991 / 3061 |
| Completed latency median / p95 seconds | 1.72295 / 2.17403 | 1.64539 / 2.01831 |
| Cache-hit fraction of known prompt tokens | 73.16% | 22.84% |
| Known settled formal charge CNY | 0.02662440 | 0.04795256 |
| Charged upper total CNY | 0.18954440 | 0.04795256 |

Saved per-variant summary fields all equal independent recalculation, including every response/delivery/paid/usage denominator and latency handling. A's all-attempt latency p95 is 20.02675 seconds due to its timeout; the completed-only latency row above explicitly excludes it and cannot be substituted for the saved all-attempt figure. Known 22-response token totals: prompt 46,668; completion 3,394; cached input 23,424; total 50,062.

There are 11 fully observed paired checkpoints, C01–C11, first repeat only: 8 both correct, 2 both incorrect, 1 only B correct, 0 only A correct. The only correctness discordance is C08. This is an incomplete prefix without the planned three-repeat coverage; it supports descriptive comparisons only. Known B prompt-token mean is 370 lower (16.04%) but completed B output tokens are greater on average and cache benefits differ sharply. A's aggregate upper charge includes the unknown timeout. Neither summary superiority nor a general cost advantage follows from these observations. No model architecture, autonomous solving or all free-text factuality claim is supported.

Formal charged upper total is 237,496,960 units = ¥0.23749696: known settled ¥0.07457696 plus unknown maximum reservation ¥0.16292000. Raw/input SHA reconstruction binds timeout payload UTF-8 bytes 17,317, input token bound 77,460, max output 1,000, and reservation 162,920,000 units. The original call ID `520a5c50b9204960a3f9915952ed9b97` stays state=unknown, reason=MODEL_TIMEOUT; prompt/completion/cache remain null. Start 05:34:18.979494 UTC, original budget created 05:34:18.992257, end 05:34:39.008228. This maximum accounting is not a supplier invoice or known consumption.

Original shared ledger is accessed through SQLite `mode=ro`, no initialization/writes. The formal calls match original scope/ID, reservation, usage/cost or unknown fields; uncalled rows have no paid ID. Current original ledger is 35 calls = 34 settled + 1 unknown; charged 277,602,960 units, frozen=false. Owner before snapshot is 12 settled / 40,106,000 units; the difference matches formal upper total. Numerical remaining allowance does not resolve unknown state. Existing runner admission blocks a subsequent paid phase while unknown/pending exists; this review neither clears that record nor authorizes resending.

Frozen formal plan is 12 checkpoints × 2 contexts × 3 repeats, AB/BA 18 pairs each; independent public-history reconstruction, request serialization and maximum reservation calculations match all 72 inputs. Plan canonical hash `bb9d603d75d16dcf9473e534a38687ce7a90d548035a6ad76ad682a16b459539`; freeze hash `f4436d0b4d9009788993092246b278e44c03021558bddb8b87337372b3eb1066`. Raw SHA256 `74c20c72ac39e236bd3e5c48062f71e2c98a92b9368269c3e67a95c841db2e28`; summary raw SHA256 `83870be5f56b8f53a4c5be6a42fe049aee78c8159dac872f20ef04c74a4ecb11`. The approved baseline manifest raw `9c36943cbb6e4fe08b6e176445ba91835fafa79a2077c2155bbf8d613f8b07c1` retains the baseline commit label `7821af4efe0613c20a80ea164c1dab1c0f288bab` through actual source/evidence-byte binding, without QA Git operations.

Owner `source-timeout-accounting.json` openly defines before as original plan.freeze.source_hashes and after as current actual bytes; it is not a separately captured immediate pre-run Owner snapshot. QA compares each of its 41 source records with the original plan and actual files, and separately captures before/after of its own audit. Original raw/run/plan/journal/summary are preserved. The known invocation/finalization journal covers only the 23 attempts, and there are no journal attempts for the remaining 49 records.

Real process exit 0 is Owner evidence in `process-result.json`: session 82634, completion chunk `8b04ad`, retries/extra probes 0. Exit 0 means orderly terminal-row recording under the stop gate, not 72 successful responses. QA directly observes its own offline process exits only. Source/credential pattern scan is scoped to the authorized public artifacts, and not an exhaustive secret certification; no environment, credentials, network, paid provider calls or Git were accessed by QA. No human/teacher approval was invented.

Files: updated assigned `tests/review_e1_results.py`; this report; new `evidence/qa/T25-independent-20261005T054700Z/{checks,judgments,result}.json`. No implementation, raw response, gold or Owner file was modified by QA. Final evidence path and actual final command/exit will be appended below.

## Final rerun and bookkeeping finding closure

Experiments Owner added only `owner-artifact-sha256-v2.json`, raw SHA256 `bfb62e9aac64de1500ed5112ef1b8baff31f7b52db70b6cb812618711b3217e2`; original index remains. It records the old/current experiment explanation hashes and explains that Main-requested timeout/source supplement was appended after the original index. It also binds the source accounting and process supplement. QA validates every current v2 target hash, including the previously mismatched review file; the auxiliary index finding is closed. No raw response, plan, summary, gold, ledger or frozen experiment source was changed for this correction.

Final actual command, working directory `D:\深度能力`:

```text
C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 tests/review_e1_results.py --run experiments/runs/20261005T053334004502Z-formal-real-48d972eb --formal-plan experiments/runs/20261002T125600594673Z-formal-plan-949ddff0 --output evidence/qa/T25-independent-20261005T055600Z
```

Actual exit 0, chunk `5f626a`, 1829 checks, 1829 passed, no failures. Evidence: `evidence/qa/T25-independent-20261005T055600Z/{checks,judgments,result,process-result}.json`. Final result raw SHA256 `84ca0cc505476cabd8daaefb1b9dbb826e07853319bb3148d8107e9a2b3f21ea`. The audit records unchanged before/after hashes of 163 reviewed artifacts and 41 frozen experiment sources, and rechecks the approved baseline. All 23 attempted journal before-ID prefixes and time orders match. The timeout's original ledger created timestamp, reason and null tokens match the supplement; its maximum reservation remains unknown.

No observation of a human-supplied later fee estimate changes these recorded results. Actual supplier billing and timeout completion remain unresolved; no new paid execution is authorized here. The observed descriptive comparison and stop gate are accepted for Main's decision record; T24's complete three-repeat response goal is not achieved. Original first-run bookkeeping failure is preserved as evidence, not silently discarded.

QA source STOP: final assigned harness raw SHA256 `a6432a28143a859f3b01f0eca329a3489b7bba1941112bcea3a634ade02b33ee`. No further implementation or harness edits are planned under this dispatch. Further event-evaluator or CH01 review requires Main's separate stable candidate handoff.
