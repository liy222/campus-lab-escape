# v1 product facts before T21 commit binding

This is Main's engineering fact index, not a course grade or human signature. Exact release commit/tree/blob binding is recorded separately in `baseline_v1-manifest.json` after this artifact is committed.

| Scope | Actual evidence | Limits |
|---|---|---|
| Three-room manual game, strict actions, versions, single-slot state | Independent M3 API46 and manual browser1280/768/390 | Current M3 actual OS service restart on sameDB verified; PID20340→12352, events14→15 |
| AI visible-only context, six restricted tools, bounded rounds, fixed proposals/confirmation, foreign sessions, concurrency, crash/no retry | `evidence/qa/20261002T120504699455Z-m3-api/run.json` | Synthetic/scripted providers and fake transport; logical45sec and shortened timeout checks explicitly disclosed |
| UI ask/ref/cancel/confirm/manual recovery and stale/late/uncertain responses | `evidence/qa/20261002T115503579Z-m3-browser/run.json` | Chrome/Edge each1280/768/390; automated test player, no human playtest |
| Frontend build and whole deterministic regression | `evidence/qa/check/20261002T120553.430164Z-b81339d5/summary.json` | build0,46passed,159subtests,source unchanged; one existing deprecation warning |
| Actual DeepSeek tool return and proposal-confirm | `evidence/qa/20261002T120735404563Z-m3-real/run.json` | 1turn/2calls; first tool forcedget_inventory, subsequentauto; confirms only R1 cabinet stage |
| Charge upper bound and privacy | Same real run and `pricing-check-20261002T120000Z.json` | Canonical CNY10 ledger,6settled calls,totalupper0.01035448; provider bill not independently verified, selected scans not exhaustive security proof |

All 28 acceptance IDs remain in `acceptance-M3.json`; future E1/evaluator/CH01/clean reproduction are NOT_RUN, partial evidence is explicit. Initial QA harness failures are retained. No human playtest, accept/reject-AI decision, signoff, peer review or teacher approval is invented. Course eligibility/deadline/approver questions are excluded from pursuit under the user's direct instruction.
