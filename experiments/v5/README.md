# V5 offline engineering experiments

These are Backend-owner development experiments, not independent QA, real AI generation, a public exploit demonstration, or human difficulty research. They never open a production database. All accounts, inputs and SQLite files are isolated synthetic fixtures; database files are removed with the temporary workspace. No network or paid provider call is made.

Run from the repository root using the existing Python interpreter. Preparation writes expectations and source/input hashes before execution. Use a new evidence directory for each execution epoch; completed outputs cannot be overwritten.

```powershell
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 -m experiments.v5.run --prepare --output evidence/upgrade/v5.0/experiments-owner/new-run
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 -m experiments.v5.run --output evidence/upgrade/v5.0/experiments-owner/new-run
```

`dataset.py` defines nine room-count/difficulty combinations, twenty invalid definitions (five reference, five dependency, five semantics, five layout) and five size/depth/planning/truncated-output cases. E1 compares strict `Draft` shape validation with complete compilation and real-action witness replay. Unknown proof remains unplayable and is not classified as proven unsolvable. The state-budget case disables only the deadline in the harness to reach the existing count guard; its elapsed time does not represent production's five-second runtime. The time-budget case uses a controlled clock and records actual elapsed time separately.

E2 seeds an explicitly private 0.9.0 policy fixture, saves it through API v2, rejects the same new single-clue normal input under 1.0.0, then restarts the isolated app and restores the original frozen definition/save without an LLM. This is a planned compatibility rehearsal, not a historical public release or user migration.

E3 sends B's authenticated requests against A's session/archive and checks both live states. A separate read-only query on an isolated SQLite backup removes only the owner predicate to show private archive disclosure. The control does not modify product code and does not perform a successful product restore.

Actual first execution: `evidence/upgrade/v5.0/experiments-owner/run1/`. Both preparation and execution exited 0. E1 admitted all nine valid fixtures, rejected all twenty bad fixtures, and matched all five limit expectations; shape validation alone accepted seventeen bad fixtures. E2 and E3 matched their preregistered expectations. Forty relevant source hashes matched before and after execution. The Starlette/httpx deprecation warning remains.

These finite synthetic results do not establish general model quality, arbitrary-level solvability, universal security, human play time or independent acceptance.
