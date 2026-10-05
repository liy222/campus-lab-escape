# T31/T32 committed-source clean reproduction — 2026-10-05

Result: **PASS within the approved new-source-directory / existing-environment mock scope; overall process exit 0.** No helper or product defect occurred, and no source edit or rerun was needed during this candidate execution. STOP: no required clean-reproduction work remains pending.

## Identity and directories

- Main-provided committed source: `fc70b15b84d811aec62e2a561c468538844b6edf`. Delivery did not invoke Git or independently claim a push verification.
- ZIP: `data/reproduction/20261005T111419Z/source.zip`; SHA256 `bc8e8f86b0f861762e3247507688c1eb1f85ea1ac5f7e3cc86e830c04f61e40e`.
- Main pins: `evidence/integration/reproduction-20261005T111419Z-pins.json`; SHA256 `25ce6a65f8a134cdd58647275840cc8e32f6dfdd4af674d2dafcbbc62f6883d1`. Exact ZIP membership and all **6014** per-file Git/runtime byte pins verified. The same 6014 materialized source bytes remained unchanged after checks, evaluator prechecks and services.
- Helper: `scripts/reproduce.py`; raw SHA256 `7dc71165e3d42479884f8c821093c6561e98c240766b03e4a0e69454ea9ec0e9` verified before and after.
- Main-authorized clean workspace: `D:\深度能力\data\reproduction\20261005T111419Z\clean`; evidence: `D:\深度能力\evidence\delivery\T32-clean-20261005T111419Z`. Both paths were absent before the run. Older failed package directories were untouched.
- History-bound M2 fixture: Main-provided `m2-legacy-sqlite-165a961.py`, raw SHA256 `21d992feb895ce5535c6b0b3d731887be9619171351a551935e1d10fc2bfae22`, source `backend/app/storage/sqlite.py` at `165a961c9d6694ceb44c88ef86c1ea28de2eae71`. It was copied only to the new `data/integration/` fixture path. The M3 migration test creates its own runtime DB; no player or production DB was copied.

Main's fixed per-file LF/CRLF/mixed-newline reconstruction was applied before validation and matches each pinned original runtime raw hash. No target-selected normalization, trusted-rule change, evaluator fallback or source mutation occurred. `materialization.json` records actual modes and mixed-newline indices.

## Actual command

Executed once from `D:\深度能力`, using the designated existing Conda interpreter:

```powershell
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -m scripts.reproduce --source-archive 'D:\深度能力\data\reproduction\20261005T111419Z\source.zip' --archive-sha256 bc8e8f86b0f861762e3247507688c1eb1f85ea1ac5f7e3cc86e830c04f61e40e --commit fc70b15b84d811aec62e2a561c468538844b6edf --main-pins 'D:\深度能力\evidence\integration\reproduction-20261005T111419Z-pins.json' --main-pins-sha256 25ce6a65f8a134cdd58647275840cc8e32f6dfdd4af674d2dafcbbc62f6883d1 --workspace 'D:\深度能力\data\reproduction\20261005T111419Z\clean' --output 'D:\深度能力\evidence\delivery\T32-clean-20261005T111419Z' --legacy-fixture 'D:\深度能力\data\reproduction\20261005T111419Z\m2-legacy-sqlite-165a961.py' --evaluator-release E1-formal-review-v2 --evaluator-release baseline_v1
```

Exact child argument arrays, working directories, timestamps, log hashes and actual exit codes are in `report.json.steps`, `check/20261005T111612.742584Z-36c51e86/summary.json` and the two service ledgers.

| Actual check | Exit / result | Evidence |
|---|---:|---|
| Existing Python locked dependency versions | All 28 exactly match | `report.json.locked_python_dependencies` |
| `python -m pip check` | 0; no broken requirements | `pip-check.txt` |
| Node/npm versions | 0 / 0; 24.17.0 / 11.13.0 | `node-version.txt`, `npm-version.txt` |
| Fresh `npm --prefix frontend ci` in clean directory | 0; 72 packages added, 0 audit vulnerabilities reported | `npm-ci.txt` |
| Unchanged `scripts.check --suite deterministic` | 0 | `unified-check.txt`, `check/.../summary.json` |
| TypeScript/Vite build | 0 | `check/.../frontend-build.txt` |
| Full `pytest tests -q -p no:cacheprovider` | 0; 73 collected tests / 203 subtests passed | `check/.../deterministic-tests.txt` |
| Evaluator `precheck --release E1-formal-review-v2` | 0; no identity issue; 0 paid calls | `evaluator-E1-formal-review-v2-report.json` |
| Evaluator `precheck --release baseline_v1` | 0; no identity issue; 0 paid calls | `evaluator-baseline_v1-report.json` |
| v2 actual dual-service health/proxy/route/save/restart/restore | PASS | `v2-services.json` |
| Independent archived-v1 service/DB unlock/save/restart/restore | PASS | `v1-rollback.json` |
| Post-run evidence/identity assertions, inline Python | 0 | `verification.json` |

The 73 collected tests include reused M3 unittest methods imported by CH01; they are not described as 73 distinct acceptance scenarios. One existing Starlette/HTTPX deprecation warning remains. Existing Conda Python is 3.14.7; no pip install, new Python environment, environment reset or environment deletion occurred. Actual installed frontend versions: React/React DOM 19.3.0, Vite 7.3.6, TypeScript 5.9.3, React Vite plugin 5.2.0, Playwright 1.63.0 (`verification.json`).

## Actual service and persistence scope

v2 backend on loopback port2927 used PIDs **15564 → 24140**; frontend PID18860 on port2928. Both health endpoints and frontend `/api/health` proxy responded successfully. The exact 18-action public HTTP route reached `won`, with only the access card in the final inventory. The first R3 unlock consumed exactly `emergency_key`; a save made after unlocking had revision13 and no key. After the backend process was stopped and a new OS process started, persistent current state still equaled the won state; restore returned the saved unlocked R2 state with a new generation and no key. This is an actual OS-process restart, not only construction of another app object.

v1 ran from `clean/release/archives/baseline_v1`, with independent DB `clean/data/rollback/game-v1.sqlite`, loopback port2965, PIDs **12972 → 2752**. Its 13-action unlock retained `emergency_key`, original receipt consumption was empty, and save/restart/restore retained that v1 behavior. Current v2 code and v2 DB were not used as the rollback implementation/input.

All five owned service-process terminations were observed: Windows process exit **1**, `taskkill` exit **0**. These are intentional process-stop facts preserved in the service ledgers; the encompassing reproduction exits0. No service remains owned/running after the helper's cleanup. Service startup logs use `--no-access-log`; session capabilities are never written to the report. The clean root has no `.env`. Child environments strip inherited model/evaluator credentials and import-path overrides, force mock and isolated DBs. Original `.env`, player DB, budget ledger and existing environments were not accessed or modified by this task. No model-network/paid call, additional budget allowance, public deployment, Actions, Git or subagent operation occurred.

The two evaluator reports were copied byte-for-byte from their clean `evaluation/runs/` outputs to this evidence directory. Their original clean paths and exact SHA256 values are in `verification.json`; reports establish registered identity, not a new semantic/paid evaluation verdict.

## Changed files and remaining limits

This execution added only the assigned `evidence/delivery/T32-clean-20261005T111419Z/` outputs and generated files under the approved ignored new workspace (frontend dependencies/build, fixture and isolated runtime DBs). Existing helper and every packaged source member were unchanged. Preparation revisions/evidence are separately preserved at `T32-preparation-20261005/` and `T32-preparation-v2-20261005/`; no earlier result was overwritten. Main owns Git/integration and another owner owns README/release documents.

Scope is a fresh source directory on the user's existing Windows/Conda/Node environment. It is not a clean OS, a newly created Python environment, human gameplay, teacher approval, human signoff, real-model language robustness or whole-course acceptance. This run does not repeat T30's Chrome/Edge screenshot matrix and makes no new browser-matrix claim. The original packaging failure reported by Main remains a separate preserved Main event; this clean-run command had no failure. Formal paid evaluator continuation and human decision/signature work remain outside this Delivery verdict.
