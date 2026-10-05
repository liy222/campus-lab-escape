# T31/T32 preparation — 2026-10-05

Status: helper prepared; committed-candidate clean reproduction **NOT RUN**. Waiting for Main's committed source ZIP, byte pins, approved new workspace and explicit GO.

Owned change: `scripts/reproduce.py`. No existing dev/check/reset, README, release, contracts, product, test or Main-owned file edited. No Git command, environment installation/reset, original DB/config/ledger access, model call or deployment.

Actual command results from `D:\深度能力` with `C:\Users\liyh\.conda\envs\1\python.exe`:

- `python.exe -B -m scripts.reproduce --help`: exit 0.
- Isolated inline Python helper safety probe: exit 0; six assertions recorded in `checks.json`. Synthetic inherited credentials/import path removal, unsafe ZIP paths/env/database/dependency member refusal, exact explicitly pinned CRLF restoration and wrong-runtime-hash refusal were checked. The probe uses synthetic ZIP/text assets stored alongside this report; it does not reproduce the product candidate.
- Read-only version checks: Python `3.14.7`, Node `v24.17.0`, npm `11.13.0`. A combined exploratory command subsequently requested nonexistent `evaluation/tools.py` and exited 1; this is not a dependency or product failure. Other exploratory reads requested nonexistent `release/manifest.json` / `release/baseline_v1/archive-index.json` and nonexistent guessed test patterns, which produced visible errors. Actual paths were located and read.
- Initial default-sandbox command launches and Node REPL failed before process execution with `helper_unknown_error: setup refresh had errors`; no command exit code exists for these failures. Explicit assigned-project commands passed automatic escalation review and executed successfully. No auto-review rejection occurred.

Required Main inputs: source ZIP SHA256 and full commit; pinned ZIP members with each Git blob SHA256, expected runtime raw SHA256 and optional per-path `main_pinned_lf_to_crlf`; pins-file SHA256; history-bound M2 fixture; new clean workspace. The M3 fixture is `data/integration/m2-legacy-sqlite-165a961.py`, expected raw SHA256 `21d992feb895ce5535c6b0b3d731887be9619171351a551935e1d10fc2bfae22`, original source `backend/app/storage/sqlite.py` at commit `165a961c9d6694ceb44c88ef86c1ea28de2eae71`. Main provides/extracts it; the archive is not claimed to contain a runtime DB.

Planned actual clean run: verify existing Python lock versions and `pip check`; install frontend only with fresh `npm ci`; execute unchanged `scripts.check` for build and full pytest; optionally exact evaluator identity prechecks; launch separate backend/frontend subprocesses and verify health/proxy/route/save; stop/restart backend and restore; launch archived v1 in its own cwd with independent v1 DB and retain the baseline key. All child environments strip inherited model/evaluator credentials and `PYTHONPATH`, force mock and isolated SQLite. Child process start/termination exit codes and source before/after hashes are retained. Existing Conda packages are read-only; no pip install occurs.

The evaluator derives its deterministic project root from its source location. Absolute original-ledger values belong to paid execution; this helper invokes only deterministic precheck if Main explicitly selects releases. Exact trusted/evidence byte checks remain enforced. No normalization fallback or target-selected trust change is permitted.

Limitations: no fresh source install, pytest/build, product service route, persistence, v1 rollback or clean evaluator verdict has run yet. T30 evidence belongs to QA and is not reused as an invented T32 result. The previous T27 paid work and continuation are outside this task's authority and result.
