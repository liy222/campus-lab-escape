# T23 preparation; real execution remains gated

No credentials or ledger were read for this preparation. No model or network calls were made. Frozen experiment code and documents were not edited.

The existing real runner reads root .env only inside the real execution branch after approve() succeeds. DeepSeekConfig.from_environment reads three allowlisted fields as data (UTF-8-sig), with process environment taking precedence. Do not dot-source .env, evaluate its values as PowerShell, print its contents, or perform a preliminary provider construction. Existing provider checks the official deepseek-flash model and https://api.deepseek.com endpoint and original data/ai-budget.sqlite.

The template in this folder is deliberately invalid: approved=false, no real expiry, and outside authorizations/. Main must create a new authorization with an unused id in experiments/authorizations/, approved=true, reviewed UTC expiry, the exact plan/freeze/pricing hashes and max_calls=6/additional_upper_cap_units=700000000 (0.70 CNY), and provide the file raw SHA plus explicit GO after independent QA acceptance. This cap is phase-local and does not grant a new allowance.

Run from D:\深度能力 only after that GO:

```powershell
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 -m experiments.runner pilot --mode real --authorization '<MAIN_ISSUED_FILE_UNDER_experiments/authorizations>' --authorization-sha '<MAIN_PROVIDED_RAW_SHA256>'
```

Execute once; do not reuse the authorization or resend failure rows. Preserve run/plan/input/raw/journal/completion/summary. Unexpected exit or interruption requires read-only reconciliation, with no resend. Unknown usage, timeout, abnormal model/rate/auth/bounds, source/input changes, shared/phase budget stop and repeated known-cost failures retain the stop result.

Formal execution is a separate phase with 72 max_calls, exact formal plan hash, same freeze hash, and a new finite cap. It also requires the real pilot_run_id, pilot_summary_sha256 and pilot_review_accepted=true after Main reviews six completed known-usage pilot rows, actual cost and quality. This preparation does not issue that GO.

Price evidence checked at 2026-10-02T12:00:00Z is accepted by existing code only up to age 86400 seconds. Its temporal validity is checked again at admission; this document cannot extend it. Reservation upper bounds are not provider bills or measured token cost.
