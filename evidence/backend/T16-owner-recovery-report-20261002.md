# Backend T16 recovery owner stable handoff

This report is owner-local evidence, not independent T18 QA acceptance. Backend production source required no further change during recovery. The current five T16 source hashes match the actual successful `t16-local-20261002T073627954459Z.json` record.

## Files

Inherited T16 production candidate: `backend/app/storage/ai.py`, `backend/app/storage/sqlite.py`, `backend/app/domain/models.py`, `backend/app/api/routes.py`, `backend/app/main.py`. Recovery wrote only `evidence/backend/t16_recovery.py`, the two new timestamp JSON records, and this MD/JSON report. Domain rules and Python dependencies were inspected and left unchanged.

## Actual commands and results

- Explicit `AI_PROVIDER=mock`, `C:\Users\liyh\.conda\envs\1\python.exe -m evidence.backend.t16_local`: exit 0, 29 owner-local checks; `evidence/backend/t16-local-20261002T113615933883Z.json`.
- Explicit `AI_PROVIDER=mock`, `C:\Users\liyh\.conda\envs\1\python.exe -m evidence.backend.t16_recovery`: exit 0, 2 narrow recovery checks; `evidence/backend/t16-recovery-20261002T113741655233Z.json`.

All providers used for these checks were explicit mock or programmatically injected local fakes; synthetic configuration-fault tests patched the configuration factory. No credential or `.env` reads, paid calls, Git operations, or edits outside the assigned Backend evidence paths occurred. The canonical root budget ledger was not accessed or modified.

## Verified scope

The 29-check run exercises complete assisted mock progression with fixed pending proposals, immutable same-ID replay, one-shot concurrent confirmations and confirm/cancel races, expiry/cancellation/manual-state invalidation, reset/restore invalidation including committed proposals, safe full current-generation history and Trace fields, manual mutations during Provider await, stale inflight results with actual mock call count, strict request envelopes, faulty configuration with manual gameplay retained, malformed runtime rejection, and actual Git-exported M2 Store DB creation followed by idempotent migration and old receipt replay. The Git-exported legacy source hash is `21d992feb895ce5535c6b0b3d731887be9619171351a551935e1d10fc2bfae22`.

The two extra checks reconstruct Store after a durable reserved claim without finish or abandon: duplicate returns 503, injected fake Provider calls stay 0, no proposal appears, and the replacement refuses the original owner's callbacks. Public definition validators contain exactly `$defs` and `$ref`.

## Limits and handoff

Formal T18, live HTTP service restart/process-kill acceptance, browser checks and paid integration are not performed here. The reconstruction check does not kill an operating-system process. AI and Frontend owners are independent; Main must bind final candidate hashes after they stop. The original failed 073600 timestamp record and successful 073627 record were retained. A TestClient/httpx deprecation warning remains. Ordinary sandbox launch failed with `helper_unknown_error`; authorized checks ran through approved escalation. One initial evidence read used abbreviated nonexistent filenames (exit 1); exact paths were then read (exit 0).

All source and evidence SHA256 values are in the companion JSON. Backend is stable and stops writing after this report, ready for independent T18.
