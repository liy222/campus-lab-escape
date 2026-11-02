# V5 conservative recovery — execution result review

**Review mode:** read-only review of Main’s approved execution records. No tests, ledger operation, preview, provider, network, or credential access was performed for this review.

## Authorization

The human round-01 record preserves the reply **“批准核账及3次评价／0.40元（推荐）”** and ties it to the concrete proposal: close the three identified unknown ledger entries by changing only their state/reason, retain the 0.110616 CNY upper amount, then evaluate the fixed claims at most once each with a 0.40 CNY total limit. The fixed approval file is marked approved, has the same reply and purpose, binds the exact dry-run bytes and current reconciliation helper, and lists those three targets. The dry-run digest and helper digest matched the approval during this review.

This is authorization for the recorded reconciliation and finite paid run. The human review record still marks overall stage review `undecided`; this review does not change that status.

## Reconciliation

Main’s apply result is [runs/20261102T114636930048Z-2ecb52918a60/result.json](../runs/20261102T114636930048Z-2ecb52918a60/result.json). It reports `status=ok`, `mode=apply`, and `applied=true`. The original [read-only dry-run](../runs/20261102T113622500889Z-4ea33b806f6f/result.json) remained unapplied and had matching before/after fingerprints.

The apply result matches the approved proposed-after fingerprint. For each of the three targets, the only differences are `state: unknown → settled` and the reason marker `→ HUMAN_ACCEPTED_UPPER_RETAINED`. Scope, timestamps, reserved/charged amounts, and all three NULL token fields are unchanged. The table row count remains 175 during reconciliation; the retained upper amount remains 110,616,000 units (0.110616 CNY). The result explicitly says provider usage is unknown and supplier invoice verification is false. This closes accounting state under the human-approved upper-bound treatment; it does not recover provider usage or establish what a supplier billed.

## Paid evaluation and post-run snapshot

The free [preview](../evaluation/preview-20261102T113731971881Z-e6d252b2/preview.json) is `PREVIEW_ONLY`, with a three-call upper estimate of 0.38296 CNY and zero credentials, ledger, model, or network access. Its three claim wire hashes and order match the paid report.

The paid [report](../evaluation/paid-20261102T114835067721Z-d8ca9df3/report.json) and [execution record](../evaluation/execution-v5-claims-20261102T114624Z.json) show one actual request for each of V5-C1, V5-C2, and V5-C3; each has one reserved-call delta, a distinct call ID, and no retry. The recorded gate is limited to 3 calls, 400,000,000 units (0.40 CNY), and 1,000 output tokens. All three returned `PASS`, their references have no validation errors, and the evaluator source identities and paid input binding match before and after. Both prechecks are `READY`; the run stop reason is null.

The recorded token usage recomputes to 26,072,240 units, or **0.02607224 CNY**, below the approved 0.40 CNY limit. This is an estimate from provider-reported usage, not a verified supplier invoice. The three finite `PASS` results apply only to these registered C1–C3 claims; they are not whole-project certification or human acceptance.

The [after-execution snapshot](../logs/after-execution-readonly.json) was collected in SQLite read-only/query-only mode. It reports 178 rows, all settled; 0 unknown, 0 reserved, unchanged 10 CNY cap, and unfrozen configuration. The follow-up snapshot itself made 0 new model calls. The increase from 175 to 178 is consistent with the three recorded paid attempts.

## Review command and scope

The review used two read-only Python projections over the specified JSON records and human round-01 record; both exited **0**. The first compared approval, dry-run, apply, preview, paid report, execution map, and after-snapshot fields. The second extracted only the paid gate limits:

```powershell
C:\Users\liyh\.conda\envs\1\python.exe -
```

Exit code: **0**. It checked the approval/dry-run/source bindings, allowed ledger deltas, preview-to-paid wire equality, attempt count/order, usage arithmetic, before/after identity, reference validation statuses, and post-run counters. It did not open the database or inspect a key, raw credentials, or raw model answer text.

No tests were rerun. No new ledger apply or paid call was made during this review. The execution records do not establish supplier invoice accuracy or general model quality beyond the three finite registered claims.
