# QA-R1-001 — R2 gameplay deferred from M1

Target: stable M1 R1 backend working tree, HEAD `24c8a024f86d9f8bc8e68b04fc09faac5a513a8f`; exact files in `evidence/qa/20261002T060937281797Z-r1-api/run.json`.

First formal API run: 2026-10-02 UTC, 14 tests, 13 passed, 1 failed; process exit 1. The failed result remains immutable.

Minimal reproduction: create session; perform R1 route (inspect note and cabinet, open cabinet, take card, unlock R1 door, move R2); submit `use_item {item_id:fuse,target_id:r2_powerbox}` without holding fuse, using current generation/revision and a fresh request ID.

Full-level SPEC expectation (A03): `PRECONDITION_FAILED` with no state change. Actual M1 result: HTTP 409 `NOT_VISIBLE` with no state change. R2 currently projects no objects and explicitly describes gameplay as next stage.

Classification: scope gap awaiting T09/T13, not an R1 defect. Backend candidate was explicitly limited to R1 and R2 return; no implementation fix requested for M1. The dependent unpowered monitor and missing-key checks are not yet verified. QA retains this test with an explicit deferred skip reason and must activate it in T13. A03 is only verified for missing R1 card at M1.

Owner: backend for T09; QA for T13. No claim of complete A03/A10 or full-level acceptance is made.
