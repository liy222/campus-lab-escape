# T27 independent conservative budget reconciliation review

Final verdict: PASS after Main's helper repair, 124/124 checks, actual exit 0. Finding T27-BUDGET-001 is closed. Original ledger remains unknown and untouched by QA; only isolated memory fixtures exercise writes. This accepts the narrow conservative implementation, not an independent supplier bill or a paid execution authorization.

Initial verdict: FAIL pending Main's narrow helper repair. The normal conservative closure is correct in the isolated fixture, but post-update invariants are incomplete under fault injection. Original project ledger has no triggers and remains unchanged; this Finding does not claim that an actual corrupted closure occurred.

Files: assigned `tests/review_budget_reconciliation.py`; this report; new `evidence/qa/T27-budget-reconcile-20261005T060400Z/{checks,cases,result}.json`. Main owns `evidence/integration/reconcile_timeout_upper.py`; QA does not modify it. No original `--apply` operation was executed.

Actual command, working directory `D:\深度能力`:

```text
C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 tests/review_budget_reconciliation.py --output evidence/qa/T27-budget-reconcile-20261005T060400Z
```

Actual exit 1, chunk `1a5c3d`, 101/109 checks passed. Reviewed helper raw SHA256 `9e6ceebaf1fd8cfa49e7caa411d203250839802b367d6eacbc7dff1ca64860a1`. All tests that mutate or apply use SQLite `:memory:` only. Original `data/ai-budget.sqlite` is opened twice via URI `mode=ro`, with exact row/config/totals/states/trigger inventory compared before and after. It remains 35 calls, 277,602,960 charged units, cap 10,000,000,000, frozen 0, 34 settled plus 1 unknown; no actual schema triggers. Exact target call remains unknown/MODEL_TIMEOUT with 162,920,000 reserved/charged and null tokens.

## T27-BUDGET-001: post-update exact row/config verification missing

The helper checks the target tuple and configuration before update, and total charged/count afterward. It does not assert that the post-update target is the exact expected closed tuple or reread the config. Four actual SQLite in-memory AFTER UPDATE triggers respectively set prompt_tokens=1, cap=20,000,000,000, frozen=1, or target reason=WRONG. Each preserves SUM(charged)/count, so the current helper commits. Each causes two QA failures: expected rejection and exact rollback. No supplier, original ledger or network is involved.

Small repair: after the target read, require `after == (tuple(closed) if apply else row)`; reread `SELECT id,cap,frozen FROM budget_config` and require equality with the original config snapshot. Raise on disagreement so the existing exception handler rolls back. Preserve original integer charge/reservation, null usage, explicit accounting marker, cap and frozen flag. Do not reduce charges to the human-reported amount or initialize a new allowance. Retest the same isolated failures after Main's stable repair.

Passing coverage already includes exact normal closure, only intended state/reason change, original reservation and token NULL retention, dryrun no writes, dryrun with SQLite query_only, refusal of apply on query_only, apply/dryrun idempotence, wrong ID/scope/time/reservation/charge/state/reason/token fields, missing target/config, wrong prior closure marker, lower/higher cap, frozen config, duplicate config, total over cap, other reserved/unknown calls, reported cost over retained bound, failed commit rollback, KeyboardInterrupt rollback after update, ignored atomic update, SQLite abort, attempted charge reclamation and row-count mutation. No failure was hidden or replaced.

Human owner statement “这笔超时请求费用为人民币 0.05 元” is the accounting basis. It is not independent supplier billing. The proposed close changes only the accounting state/marker and retains the full ¥0.16292 upper charge, with token usage still unknown. Original timeout raw/summary/QA records permanently describe the original unknown event; later accounting closure must not rewrite those observations. This QA gives no paid call authorization, supplier-response certification, token reconstruction or permission to execute original apply.

Final repair/retest, exact command/exit and source STOP will be appended if Main provides the repaired stable helper.

## Repair verification and final source STOP

Main's repaired helper rereads and verifies the complete target tuple and original config, and compares every full budget_calls row sorted by ID with the original snapshot except the approved target state/reason. Original sum/count check remains. No charge, cap, reserved value or token field is reclaimed or changed.

Final actual command, working directory `D:\深度能力`:

```text
C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 tests/review_budget_reconciliation.py --output evidence/qa/T27-budget-reconcile-20261005T061300Z
```

Actual exit 0, chunk `8b0dcb`, 124/124 checks, zero failures. Final evidence: `evidence/qa/T27-budget-reconcile-20261005T061300Z/{checks,cases,result,process-result}.json`. Result raw SHA256 `bef67641c46f742b70d185f0f1150dfc0293382df399ee86cd44b38f06c42fc4`; repaired helper raw SHA256 `e4a5981b810a71b294321b14fe2947fb2613856b80268e4ac14b3faa10b44f8b`. Helper bytes remained unchanged during this final audit.

All original four post-update counterexamples now reject and rollback completely. Additional requested fault triggers changing another row's scope, timestamp, token count or unresolved state also reject; a charge transfer between two other rows preserving total sum/count rejects and rolls back exactly. Normal closure and repeat apply/dryrun remain idempotent. Exception paths include SQLite abort/ignored update, failed commit and interrupt after update. Post-error transactions are released and the complete isolated data/config snapshot remains equal to before. These are executed cases, not invented supplier calls.

The old Main dryrun retains its historical helper SHA `9e6ceebaf1fd8cfa49e7caa411d203250839802b367d6eacbc7dff1ca64860a1`, independently bound to the preserved initial QA result; it is not mislabeled as execution of the repaired helper. Current repaired dryrun behavior is directly exercised in memory, including query_only mode. QA never runs the helper main or actual `--apply`. Original row/config/count/total/state/trigger inventory before and after final QA still match exactly, with the timeout record state unknown and all original null tokens retained.

Files added/updated under this dispatch are the assigned harness, this report and both new QA evidence directories. Initial 101/109 failure result and before/after fault snapshots remain unchanged. QA did not edit the integration helper, original ledger, experiment raw/summary, gold, environments or Git. No network/paid calls or credentials were accessed.

QA stable source STOP: assigned harness raw SHA256 `e5b4cd0b8d7f137ea13b200ae2bb382d776ccdceb31159914c32e1f7291a21a5`. Main may separately review and execute the authorized accounting action with its own append-only actual record; this QA does not assert that it has been applied. Future real phases require their own finite gates and stable source review. Independent supplier billing, missing HTTP response/model/token details and original timeout remain unresolved observations even if the accounting hold is later closed using the human statement.

## Later Main application: independent readonly follow-up

Main subsequently reported actual apply exit 0, chunk `5c5c65`, and saved `evidence/integration/timeout-human-fee-20261005-applied.json`, raw SHA256 `b6492c291a528c9b89ee23ac83be37b70a2b4ad29b76c3fd37d586afb3d040df`. This is a later accounting event; all earlier QA and experimental unknown observations above remain historical facts. The application record binds exactly the repaired helper raw `e4a5981b810a71b294321b14fe2947fb2613856b80268e4ac14b3faa10b44f8b` verified by the independent 124-check result.

QA follow-up actual command, working directory `D:\深度能力`:

```text
C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 evidence/qa/T27-budget-application-20261005T061800Z/review.py
```

Actual exit 0, chunk `0e1107`, 48/48 checks. Added files under this new QA directory: `review.py`, `checks.json`, `result.json`, `process-result.json`. Final result raw SHA256 `86474a17f093741f4be5aec1a50b2579bafe809d134f9e4ee1819c7808d5ab7c`; readonly audit source raw SHA256 `cd5fc22144c66a4a1fda693b44a2cc34dc4f40a23d934cb60d924a4a29bf7cc9`. QA did not invoke the helper, execute original apply, or write to the original ledger.

Current ledger is 35 settled records, no pending/unknown; total charged 277,602,960, cap 10,000,000,000, frozen=0. Target tuple differs from the prior actual timeout snapshot only in state (`settled`) and reason (`HUMAN_FEE_REPORTED_UPPER_RETAINED`). Its reserved/charged remain 162,920,000; three token fields remain null. Application before tuple equals the original dryrun tuple and actual T25 snapshot; application after tuple equals the current readonly row. The historical dryrun retains its original old-helper SHA and original unknown state.

All 29 experiment rows are independently compared by all ten safe ledger columns with prior actual T25 row snapshots: only the designated target state/reason changed. The other six non-experiment rows have unchanged independently checked count and total (6, 10,354,480); their individual identities were not preserved in the prior public QA, so a new independent exact pre/post row comparison for those six cannot be claimed. Exact preservation of all other rows is enforced in the pinned helper's transactional full-table comparison, which was independently fault-tested, including same-total charge swapping. This limitation is recorded explicitly rather than inventing old snapshots.

Original formal raw and summary hashes remain `74c20c72ac39e236bd3e5c48062f71e2c98a92b9368269c3e67a95c841db2e28` and `83870be5f56b8f53a4c5be6a42fe049aee78c8159dac872f20ef04c74a4ecb11`; the original timeout still has MODEL_TIMEOUT, null response/delivery/model/usage, and .16292 retained upper. All reviewed evidence bytes remain unchanged during this follow-up. Actual Main apply exit is reported by the trusted handoff; QA directly observes only its readonly follow-up exit.

Follow-up source STOP. Accounting closure from the human statement does not establish an independently verified invoice, reconstruct missing tokens or supplier response, amend T25's stopped-run conclusion, or authorize a later paid phase. Event-evaluator review waits for a separate stable handoff.
