# E1 49-unit continuation envelope v1

This executor is new source with its own explicit source manifest/gate. It preserves the original41-file f443 freeze and original formal72 files. Its only eligible requests are original order24–72 (A24/B25). Original22 completed and1 timeout are never retried or replaced. This directory is excluded by the original freeze by existing design; executor.py, v1_judge_worker.py, schema.json, README.md and owner_tests.py are explicitly bound separately in each new plan and Main gate.

Use existing Python from D:/深度能力, no installation:

```
C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 experiments/runs/E1-continuation-executor-v1/executor.py plan
C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 experiments/runs/E1-continuation-executor-v1/executor.py mock
C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 experiments/runs/E1-continuation-executor-v1/owner_tests.py
```

Plan/mock do not load .env, construct a Provider or access the original ledger. The worker receives only sample_id/content data, runs with isolated Python -I/-B, strips MODEL_* environment variables, verifies a fixed Main archive101 index and needed module/data raw bytes before import, blocks repository reads outside its fixed allowlist and any write/socket/subprocess, and records imported module paths/hashes and LEVEL1. Its backend-domain namespace exists only in the child. Parent paid imports remain canonical Provider/budget at D:/深度能力, with original data/ai-budget.sqlite. Current v2 product is never used for E1 judgements; archive Provider/budget are never executed.

Real execution is separately gated and not performed by Owner tests:

```
C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 experiments/runs/E1-continuation-executor-v1/executor.py real --authorization <new-Main-file-under-experiments/authorizations> --authorization-sha <rawSHA>
```

Main must independently review this exact candidate and issue a new finite gate matching schema.json. Plan hash binds original run/artifact identities,49 row IDs/repeats/original orders/input artifacts/wire hashes, originalfreeze/101 archive aliases/14 prior evidence/canonical client/new source identities. Gate also binds fresh pricing, accepted pilot, independent candidate QA and accounting closure evidence. Suggested finite cap5.30 CNY covers49 old input-bound reservations totaling5.29968 CNY; it remains within the original shared10 CNY ledger and never grants another allowance. All admission/unique-origin/consumed-ID and pending/frozen checks precede the sole credential loader. A pre-call journal fsync and wire-hash observer preserve one attempt per unit.20s/1000 tokens/tool_choice=none/thinking disabled; temperature/seed not sent; no retry/repair. A timeout, unknown usage/model/provider abnormality or two known-cost failures stops remaining units. Real admission is consumed even on a credential/config failure. Any further continuation needs another reviewed design, never automatic replay.

Saved input artifacts were written with sorted JSON keys, while original Provider wire serialization used insertion order. The executor restores message role/content key order and the exact registered v1 contract tool key order after checking all values equal the saved objects. It never changes message strings or tool values. Exact outgoing byte hash/length must match each original unit; semantic equality alone is insufficient.

Only isolated MockTransport with synthetic keys and temporary test SQLite is accepted by programmatic synthetic tests. No test CLI can choose a production replacement ledger/transport or fake a real gate. Synthetic rows carry local/synthetic markers and actual paid attempts=false; they are not model observations.

Read-only crash recovery writes new reconciled JSONL/audit, never resends:

```
... executor.py reconcile --run-dir <new-continuation-real-dir>
... executor.py merge --run-dir <new-continuation-real-dir> --output <new-runs-directory-containing-continuation->
```

Merged72 first-attempt rows and lineage are separate outputs. Original timeout keeps unknown HTTP/model/usage and full0.16292 ledger upper even though accounting closure reports a separate user fee0.05. It is not rebilled or rejudged. Completed/incorrect original rows remain unchanged. If49 new rows complete, merged result is71 completed+1 original timeout,35 fully responded pairs+1 incomplete pair; it is not72 completed. Failure/uncertainty and per-planned36 denominators remain. Latency includes new isolated-judge overhead; provider_latency_seconds is separately recorded in new rows. Merged old/new latency is not a uniform model metric. Time/cache/load/pause and order continuity changed. No superiority, general model quality, autonomous completion or human signoff claim is made.

Outputs are append-only new directories under experiments/runs containing continuation- in their first path component. Originalrun/archive/current product/shared ledger cannot be changed by output/merge/reconcile. Dependency maps are explicit; old current-root baseline verifier is not silently relaxed or globally monkeypatched. Real candidate acceptance and Main GO remain required after Owner checks.
