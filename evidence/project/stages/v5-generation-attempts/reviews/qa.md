# V5 generation attempt limits: focused QA

**Result:** The authorized focused test run passed (exit 0). This is an independent check of attempt-history behavior and adjacent failure, concurrency/idempotency, and budget-refusal paths. It is not a review of generated narrative quality.

## What changed in the test

Replaced the obsolete ten-minute/day quota test with one isolated Synthetic case. It submits four consecutive failed attempts, then eleven successful same-day attempts, then confirms another request completes. It also checks that the earlier job records remain visible and that replaying the same `request_id` returns the existing job without another generator call.

## Actual command and result

Command:

```text
C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 -m pytest -q tests/v5/test_generation.py::test_generation_attempts_do_not_accumulate_limits_and_replay_is_idempotent tests/v5/test_generation.py::test_jobs_failure_states_and_same_id_never_dispatch_again tests/v5/test_generation.py::test_concurrent_jobs_per_user_global_and_replay tests/v5/test_generation.py::test_fake_budget_and_oversize_limits_prevent_send
```

Environment: `PYTHONUTF8=1`, `PYTHONDONTWRITEBYTECODE=1`. Result: **8 passed**, one upstream Starlette/httpx deprecation warning, exit code **0**.

- Log: [pytest.log](../automated/qa-20261030T093953009Z/pytest.log)
- Exit code: [exit-code.txt](../automated/qa-20261030T093953009Z/exit-code.txt)

## Scope limits

These checks use the existing test fixture and deterministic local generator. They do not contact a real provider, make paid calls, access the player database, run browser/build suites, or establish narrative quality. The test confirms old attempt records remain in the task list; it does not claim any broader retention guarantee beyond this fixture scenario. No product source was changed by this QA owner.
