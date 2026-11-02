# V5 conservative recovery — independent QA

**Result:** the isolated QA logic passed after the test fixtures were corrected. The run history contains several earlier nonzero exits; they remain preserved and are not combined into a claim of one all-green run.

## Scope and commands

The tests use an in-memory SQLite ledger for reconciliation and fake ledger/provider facades for the paid path. The evaluator context reads the currently registered source/evidence inputs read-only. No project budget database, API credential, real provider, or network connection was used. No real apply, Main preview, historical C1–C3 product node, browser, or build was run by this QA.

Initial combined command:

```powershell
C:\Users\liyh\.conda\envs\1\python.exe -m pytest -q tests/v5/test_unknown_reconciliation.py tests/v5/test_paid_recovery.py
```

Exit **1**. The 14 reconciliation cases passed. The paid test fixture then had environment-monitoring mistakes; the output recorded 20 passed, 2 failed, and 19 setup errors. Full log and command record: [initial combined result](../automated/qa-20261102T113242Z-d598a5d4/).

The paid file was repaired and rerun only where the failure occurred. Earlier outputs are retained:

- [first paid-only supplement](../automated/paid-narrow-20261102T113315Z-c4848c8b/): exit **1**; the process-wide environment sentinel intercepted pytest’s own terminal settings.
- [second paid-only supplement](../automated/paid-narrow-20261102T113346Z-da934a5d/): exit **1**; fixture used the wrong constant and allowance assertion assumptions.
- [third paid-only supplement](../automated/paid-narrow-20261102T113422Z-d0db836a/): exit **1**; remaining rejection-stage and threshold expectations were corrected.
- [fourth paid-only supplement](../automated/paid-narrow-20261102T113503Z-356efd0d/): exit **1**; two allowance-edge assumptions remained incorrect.
- [final paid-only supplement](../automated/paid-narrow-20261102T113544Z-2680698e/): exit **0**, **28 passed**, one existing Starlette/httpx deprecation warning.

The final narrow command was:

```powershell
C:\Users\liyh\.conda\envs\1\python.exe -m pytest -q tests/v5/test_paid_recovery.py
```

The reconciliation tests were not rerun because the failure and fixes were confined to the paid test fixture. Their 14 passing cases remain evidenced by the initial combined run. Therefore, the evidence is **one initial mixed result plus a later paid-only green supplement**, not a single combined green run.

## Coverage reviewed

- `test_unknown_reconciliation.py`: dry-run leaves the full in-memory schema/data snapshot unchanged; apply changes only the three fixed targets’ state/reason while retaining amounts and NULL token fields; unrelated rows/config remain unchanged; closed replay emits no UPDATE; frozen/cap/target drift, extra unknown/reserved rows, partial closure, and reviewed-snapshot drift reject; injected trigger failure rolls back both target and unrelated-row writes; approval checks bind the exact dry-run/source/targets/window; CLI apply without the fixed approval rejects before a read/write connection.
- `test_paid_recovery.py`: fixed-gate missing/expired/wrong-binding/over-limit cases; current binding shape; evidence and identity/gate rechecks; global unknown/reserved, frozen/cap, and same-approval call/cost allowance checks before the fake provider; metadata clearing after a later guard rejection; exception, invalid response, and insufficient-evidence stop behavior without retry; a valid synthetic FAIL remains recorded while later fake claims finish; free preview wire bytes/costs match the captured engine messages and the existing wire/cost functions.

The paid tests patch `evaluation.v5`’s ledger/provider/gate/binding seams. A few control-flow cases pass the fixed registered claim list through the new evaluator loop using scripted local replies; this is not a rerun of the four C1–C3 product nodes and is not evidence about semantic accuracy. The fake provider reports `actual_network_call=False`, no call ID, and no usage. Credential reads are guarded at module-local seams; test code does not inspect or expose a real key. This verifies branch ordering and bookkeeping with synthetic inputs; it does not establish real provider quality, real billing, or supplier invoice status.

## Independent source review

Reviewed the stopped `scripts/reconcile_v5_unknowns.py`, `evaluation/v5.py`, and `scripts/preview_v5_evaluation.py` against their public test seams. The reconciler validates the exact target tuples/configuration, uses a read transaction for dry-run and an immediate transaction for apply, validates the proposed full snapshot, and commits only the approved three-row state/reason closure. Its CLI validates the fixed approval and reviewed dry-run before opening the ledger read/write. The paid evaluator orders evidence and gate checks before ledger readiness, defers provider construction/key access until after shared and same-gate ledger checks, repeats identity/gate checks before each dispatch, clears last-call metadata before a new attempt, and stops remaining claims after an uncertain result. The preview uses the evaluator engine to capture messages, then the same wire/cost helpers, with no paid provider or ledger path.

No product implementation defect was found by these finite checks. Main separately reports a read-only canonical-ledger dry-run at [the Main-owned result](../runs/20261102T113622500889Z-4ea33b806f6f/result.json); that is Main’s operation, not an independent QA database run. The ledger has not been applied, and no paid evaluation was authorized or executed.

## Limits

The reconciliation/apply semantics are tested against synthetic in-memory SQLite data, not by modifying the canonical ledger. The evaluator tests exercise fake-provider control flow only; credentials, provider transport, actual charge settlement, invoice verification, and semantic correctness of model judgments remain untested. No C1–C3 product replay was repeated. A genuine bounded paid evaluation remains blocked pending a separate explicit authorization after Main’s free preview and any required review.
