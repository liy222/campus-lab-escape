# V5 third-round independent preflight: ready for a finite proposal, not execution

Independent review completed on 2026-10-23, **exit0**, no blocking finding. The preparation may be presented for a fresh explicit user decision. This report grants **no paid dispatch authorization**. No approval file or execution marker exists at the checked point.

Frozen identities:

- Runner: `82daf8a6bf0d164997df61b50ffc92bab44a93a95e07a2e36d59d5e0fb5ebcdb`.
- Preview: `3d5e33b1abdfff67665e9d7b06d8095f337cbd4fca1b5712a61460bd673ee4cf`.
- Bound source bundle: `02349e27e6523be15474ca019ba302a96a36083ec9728447a50c0a1f2d375b4e`.

All 45 bound inputs match before and after this review; the 403 product/QA/evaluator sources still match their accepted offline candidate. Four original round-two capture hashes and the old executor hash are checked separately. The new source map includes the historical captures, so a change blocks dispatch. No old result, runner, preview or capture was modified.

The fixed prospective scope is **G2, G3, A1, A2**, at most **four calls / 0.50 CNY**, no retries. G1 is explicitly forbidden as a new paid call. Existing official provider/model, canonical 10 CNY ledger, per-generation 0.20 / per-companion 0.05 caps and old-three-unknown gate remain. The exact G2/G3 payloads were reconstructed from the current production message builder and compared byte-for-byte through their canonical serialized representation. Independently recomputed full-payload bounds are:

| Case | Conservative upper bound CNY | Status |
|---|---:|---|
| G2 | 0.143528 | Exact generation payload reviewed |
| G3 | 0.149960 | Exact generation payload reviewed |
| A1 | 0.046688 | Exact historical-public-stage payload reviewed |
| A2 | 0.049000 | Placeholder only, never a dispatch payload |

The preview sum is 0.389176 CNY; the proposed hard run ceiling remains 0.50. A real successful A1 may change A2's full payload size. That actual payload must contain the newly API/Store-delivered A1 answer, be saved with its own bound before dispatch and fit 0.05; otherwise it fails closed without an extra send. The placeholder estimate is neither an approved actual A2 payload nor a promise that A2 will fit.

The historical real G1 is legitimate **test setup**, not a new generation or production fallback. Its unchanged raw response independently compiles to definition hash `b4270160c24398843182d327a8e8f2ef194bd4bea2d2e749505c3238966bf34d`, with the same eight-action witness hash `5eb15981794eb5b21d7da77ae16836d0a7ec2de8d4388a81e669255a3339de4e`; independent pure-memory replay reaches EXIT. The Owner's already executed API preparation is reviewed rather than mechanically repeated. Source and evidence show one existing `reserve_job`→validating→`commit_level` setup, then actual authenticated API session creation, all eight actions to EXIT, reset and the four-action prefix `inspect/inspect/take/inspect`. There is no state injection or draft edit.

The saved reconstructed and original public projections match exactly after excluding only new `session_id`, `level_id`, `generation` and the actual start timestamp. Revision remains **13 on both sides**; gameplay, inventory, discoveries, puzzle state and other metadata are retained. The actual committed action history is selected by session/generation, with the latest three converted back to chronological order: **inspect/take/inspect**. It matches the old actual three public labels and the new exact A1 bounded messages. One historical setup reservation plus two new generation reservations respects the existing three-jobs-in-ten-minutes limit. A1's historical session remains independent of whether new G2/G3 admit.

Safety review and independent memory checks confirm:

- Fresh authorization binds run ID, preview raw hash, source bundle, exact four-case scope, integer call/cost ceilings and an actual user-reply reference. Nine invalid variants are refused. The actual missing-file guard refuses now. AST order places this gate before the single-use marker, credential/config loading and canonical-ledger access. The authorization file alone is explicitly not proof that a human approved it.
- The marker uses exclusive creation and fsync. The pre-dispatch journal consumes each attempt, including failures. G1, duplicate case, aggregate-cap excess, changed A1 payload and A2 without the newly successful A1 history were independently refused using memory-only stubs.
- Only an actual HTTP200/API-success, deepseek `model_calls=1`, Store-guarded A1 delivery sets `previous_answer`; raw provider success alone does not. A2 uses Store history, never a synthetic substitute. Gameplay projection and exact permitted hint/revision deltas are checked around both turns.
- The provider-capture, ledger stop logic and durable journal AST are unchanged from the reviewed round-two executor. Canonical cap/unknown identity/pending/freeze checks, concurrent-call detection, both success/exception reported-model checks and credential/cookie scrubbing remain. Payloads containing transient secrets stop before dispatch. New unknown, model anomaly, secret or freeze stops the round; no evaluator entry is invoked.
- Isolation sets `SQLITE_PATH` to TEMP `game-v5.sqlite` before importing main, with fixed same-origin Host/Origin. Credential/config/canonical-ledger access remains exclusive to a later authorized execute path.

Actual independent commands: `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 -` with the inline read-only probe, tool **e850c6**, **exit0**. The probe loaded definitions with an absolute non-main `runpy` name, called no `execute` or `prepare`, and used only in-memory compiler/public-context/authorization/controller checks. The exact inline code is retained in that tool invocation. Read-only source/data inspections `4a6a87`, `38456a` and `ca8b5c` also exited0. No provider instance, database, Key, canonical ledger, network, fixture matrix, API preparation, test suite, build, browser or evaluator was executed by QA.

Evidence: `evidence/upgrade/v5.0/qa/round3-preflight-review.json`, SHA256 **`050fbbff7931672feb9df6d326cc3cf10b13b9f0d58dce08c1e8c0c2d1e12353`**. It records source maps, payload hashes/arithmetic, authorization and controller observations, original-capture bindings and explicit limitations. Owner's one successful `--prepare` remains development evidence; its earlier relative-runpy diagnostic exit1 and corrected memory-check exit0 are preserved, not hidden or relabelled.

New G2/G3 admission and real successful A1/A2 behavior remain unobserved. Previous actual failures and offline findings retain their own epochs. Main may prepare the reviewed finite proposal for submission; only a new explicit user approval may authorize the personal one-time dispatch. No unused old slot is reused, no universal quality/security/human acceptance is claimed, and no overall release acceptance follows. **SOURCE STOP.**
