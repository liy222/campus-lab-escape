# T17 Frontend owner recovery report — 2026-10-02

Result: stable frontend M3 candidate, ready for Main to dispatch independent T18 after integration. Final local mock browser Owner run passed 23 recorded checks, zero errors, exit 0. This report does not claim independent QA, human playtesting, course approval, or real AI acceptance.

## Ownership and files

Recovery edits only:
- `frontend/src/Assistant.tsx`: change usage.model_calls label from “模型请求” to “服务调用尝试”. This field is Provider invocation attempts, including local mock attempts and failures; it is not a paid HTTP request count.
- `frontend/scripts/owner-ai-smoke.mjs`: explicitly exercise clue references with focus + Enter at 1280/768/390 and assert focus reaches the actual discovered clue; add a lower-revision delayed AI response case using real local backend projections; bind the executing script and backend domain rules in source hashes.
- `evidence/frontend/T17-owner-2026-10-02T11-40-34-560Z/`: new result.json and six screenshots, preserving all older result files.
- `evidence/frontend/T17-recovery-2026-10-02/`: build.log, build-exit.txt, owner-ai-run.log, owner-ai-exit.txt, source-audit.json, this report.

The inherited M3 frontend candidate includes Assistant.tsx, API AI/confirm/cancel helpers, App integration/version protection and responsive CSS. Recovery did not change the manual game, API, App or CSS logic. No backend, AI, tests, contracts, shared project documents, .env or git changes were made by this owner. The build generated ignored frontend/dist outputs. No environment/database was deleted or reset.

## Recovered baseline

Read `AGENTS.md`, `docs/SPEC.md`, `contracts/routes.json` and relevant API schema entries; inspected frontend source and both Owner scripts.

Before the recovery edits, current App.tsx / Assistant.tsx / api.ts / style.css SHA-256 all matched `T17-owner-2026-10-02T07-38-31-730Z/result.json` before/after hashes. That inherited JSON reports passed, source_unchanged=true, 22 checks, errors empty, and stopped children. It is existing evidence, not a fresh recovery process exit measurement. The older `T17-owner-2026-10-02T07-31-44-175Z/result.json` also reports 22 checks and no errors; it binds an earlier Assistant/runtime hash and is retained.

Latest manual evidence `T10-owner-m2-2026-10-02T07-35-15-719Z/result.json` reports 22 checks, errors empty, three-width complete 18-action manual route, save/reset/restore/refresh and uncertain-control GET reconciliation. Its six bound frontend/backend sources still match current files, as verified in source-audit.json. The recovery only changed AI usage text and the AI Owner script, so the full manual route was not rerun. The older T10-T12 report described AI as unavailable at its original checkpoint; that statement does not describe the current M3 candidate.

## Actual recovery commands and results

Working directory was `D:\深度能力` for reads/edits/hash audit and `D:\深度能力\frontend` for build and browser run. Existing Python was `C:\Users\liyh\.conda\envs\1\python.exe`.

| Actual command / operation | Exit or observed result | Evidence |
| --- | --- | --- |
| PowerShell Get-Content/Get-ChildItem/rg/Get-FileHash reads | Exit 0 for source/contract/evidence reads | Actual owner tool outputs; source-audit.json records current hashes |
| Python stdin edits to the two assigned frontend files | Exit 0 | Candidate files listed above |
| `node.exe --check frontend/scripts/owner-ai-smoke.mjs` | Exit 0 | Actual tool output |
| `npm.cmd run build` | Exit 0; TypeScript/Vite build passed | build.log and build-exit.txt |
| `node.exe scripts/owner-ai-smoke.mjs` | Exit 0; 23 checks, errors=[] | owner-ai-run.log, owner-ai-exit.txt, timestamped result.json |
| Post-run `Get-NetTCPConnection -State Listen -LocalPort 8117,5117 -ErrorAction SilentlyContinue` | Exit 1 for no matching rows; no listener observed | Actual tool output |
| Python final hash/evidence assertions | Exit 0 | source-audit.json |

The first ordinary sandbox read could not start a shell because the helper reported setup refresh errors. The same authorized read was rerun with escalation and exited 0. This was not an application failure or permission denial. A pre-run listener query also returned exit 1 with no matching rows.

## Final observed behavior and evidence bounds

Final run is explicitly AI_PROVIDER=mock, isolated temporary SQLite under ignored frontend/node_modules/.cache, and loopback-only backend/Vite on 8117/5117. It filters inherited AI/model/secret variables, does not load root .env, and exports no request headers, creation tokens, sessionStorage, database, browser trace or raw service logs. No real provider or paid call was made.

- At 1280/768/390, actual mock discovery produces genuine state clue IDs. Reference anchors work with keyboard Enter and move focus to the referenced clue. Proposal tool/arguments are rendered read-only. Keyboard cancel changes no gameplay; keyboard confirm shows the real game execution receipt and disables duplicate UI confirmation. Six screenshots have no horizontal overflow. Owner visually inspected final proposed-390 and committed-768 plus inherited proposed-390/committed-1280 and latest manual won-390.
- Every nine observed confirm/cancel request bodies was exactly `{}`; the path proposal ID selects fixed server parameters. UI never sends a substitute code, item, target, revision or generation in these requests.
- Manual progression invalidates pending proposals; restore changes generation and clears assistant state, question and proposal. Another UI client changing state makes the server reject stale confirmation while current inventory remains displayed.
- A local transport delay held an actual backend mock AI response for at least 16,000 ms: AI remained pending beyond the manual 15-second budget, and manual inventory remained usable. This is an actual local 16-second transport wait, not real provider latency.
- A gated older-generation response released after reset did not restore old clues/answer/proposal. A separate actual AI response at revision 9 was held; GET synchronized its discovered clues, then the user-facing cabinet password submission (derived from those clue texts) advanced the actual manual game. Releasing revision 9 did not overwrite the now-open cabinet or display the older AI answer/proposal. No invented revision or generation was used.
- Local response injections cover stopped reason display with retained discovered clues, rejection of unknown clue IDs, and rejected display without inventing a receipt. The rejected fixture follows an actual confirm and rewrites its browser response; it proves UI behavior, not a server rejection.
- Client expiry uses accelerated browser clock. The 55,000 ms AI timer registration and abort/reconciliation path are exercised by locally accelerating that timer to 50 ms while holding transport, not by waiting a real 55 seconds or inducing a real model timeout. Manual requests retain the 15,000 ms default. Source review confirms uncertainty triggers GET reconciliation without mutation/AI resend, and an unknown confirmation result disables blind confirmation until the player obtains a fresh valid suggestion; dedicated real lost-confirmation/concurrency semantics remain QA scope.
- App applies no lower revision or retired generation, and generation change clears temporary input/history. Successful confirm Trace uses the backend receipt; proposed/cancelled/rejected entries cannot serve as committed evidence. API failure does not erase the game.

## Binding, cleanup and limits

Final result binds identical before/after SHA-256 for the executing Owner script, four frontend files, backend routes/rules/storage/main and seven AI files. Final current hashes match that map. Runtime SHA-256 is `96bb5d7143ac28a3afe46a5daccc7c5012aa213672c01ac6a11036b6179cf064`, the final AI owner handoff candidate; no source changed during verification.

Frontend and backend children stopped with SIGTERM. Their actual child records are exit_code=null, signal=SIGTERM, stopped=true, not numeric exit 0. The Owner parent command itself exited 0. Temporary database remains only in ignored cache; it is not committed or delivered as evidence. Ports had no listener after the run.

Formal T18/CH01/adversarial API checks, concurrent confirm atomicity, actual provider fault handling/TTL, real AI budget/credentials, human playtest and course acceptance are not established by this frontend Owner run. Frontend source is now stable and stopped pending Main integration/T18. No commit, push, deployment, Actions or paid model request was performed.
