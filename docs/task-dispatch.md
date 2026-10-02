# Dispatch ledger

All paths are relative to D:\深度能力. Every task reads AGENTS.md and accepted docs/execution-plan.md, uses contract v1 when frozen, returns changed files / commands / actual exit codes / evidence / limitations. Main alone commits. No child spawns permitted by these task cards.

| Task | Agent / requested actual tool config | Dependencies | Allowed writes | Acceptance |
|---|---|---|---|---|
| T02 | spec_content / gpt-6.1-sol high | T01 registered | docs/SPEC.md, docs/level_design.md, contracts/ | Exact shared schemas, strict tools, visible projection, positive route + negative cases, R/A map; main reviews freeze |
| T03 | delivery_docs / gpt-6.1-sol high | T01 | scripts/, README.md, release/, .gitignore, .env.example; temporary backend entry/deps and frontend scaffold | Required Python environment, actual /api/health and front-page HTTP smoke, build, dependency lock, dev/check/reset entrances |
| T04 | ai_integration / gpt-6.1-sol high | T01; real config absent | backend/app/ai/, docs/provider.md, evidence/provider/ | Isolated normal and adverse mock probes actually run; real call status explicitly unverified |

T03 temporary paths transfer only after explicit owner handoff. T05/T06 backend and T07 frontend wait for contract freeze and runnable scaffold. T08 independent QA waits for stable implementation. Formal UI/browser acceptance stays open while browser tool is unavailable.

M0 accepted at local commit24c8a024f86d9f8bc8e68b04fc09faac5a513a8f. T03 backend/front temporary ownership relinquished.
T05/T06 backend_engine gpt-6.1-sol/high owns backend domain/api/storage/main/dependencies, excludes ai; prerequisites T02/T03 passed; acceptance actual R1 route + no card/wrong code/hidden take/strict validation, then independent QA.
T07 frontend_ui gpt-6.1-sol/high owns frontend/ + evidence/frontend; frozen contract1.0.0; acceptance real R1 UI, build, visible-only actions, sessionStorage, errors/accessibility/responsiveness. Tests owned by QA separately.

2026-10-02 recovery: resumed existing backend_engine T05/T06, frontend_ui T07, delivery_docs consistency via followup_task. Three role threads active; no new spawn/model override succeeded on resumption (existing names reserved). Ownership and reporting conditions restated. T08 formal QA waits for stable candidate; T09 waits for M1 acceptance.

T04-real/provider: new /root/ai_provider spawned with explicit gpt-6.1-sol/high, fork none. Backend AI/docs/provider/evidence/provider only; data/ai-budget.sqlite runtime allowed. Prerequisites T01/T02/T04 mock + user selected DeepSeek/CNY10; independently implement Provider and shared conservative budget, no gameplay integration before M2. Max real probe allowance0.20 CNY, credential empty -> BLOCKED not fabricated. Acceptance actual protocol/usage or blocker, mocks adverse checks, no credential output, no commit/spawn.
Simple delivery-index: new /root/delivery_index explicit gpt-6-luna/medium, fork none; README.md and release/README.md ownership transferred from stopped delivery_docs only; scripts/config remain delivery owner. Acceptance actual existing paths and honest R1 candidate/unfinished items; no code/paid calls/secret reads/commit/spawn.
T08 whole R1: frontend/backend/scripts source stable, QA independently browser/API/build. AI Provider independent probe is outside M1 target; M3 must include AI hashes. M1 accepted only after QA actual scope results.

M1 accepted and pushed8a7348a09561102e5cb7146ad575349a2086bb30. T09/T11/T12 backend_m2 explicitly spawnedgpt-6.1-sol/high/forknone owns backenddomain/api/storage/main/deps+evidence/backend; acceptance18stepmanual path, negative boundaries, concurrency/idempotency, strict versioned single-slot save/restore/reset with immutable local evidence. T10+T12UI frontend_m2 explicitly spawnedgpt-6.1-sol/high/forknone ownsfrontend+evidence/frontend; acceptance data-driven R2/R3/EXIT/manual path, save/restore/reset, loading/errors/generation invalidation, 3widths keyboard. Both stop at stable candidate for independentT13, no sharedcode/commit/spawn/paidcalls. M3gameAI awaitsM2 gate.

Narrow integration ownership handoff: main temporarily owns .gitignore to append .vite/ (QA launcher-generated local cache found untracked), then returns future delivery edits toDelivery. Existing ignored directories and files preserved; no deletion.

ai_provider T04stable/handoff-20261002T064002444444Z: budget/provider/provider_check/docs-provider Owner stopped. Actual4requests including2failedstrict-indexparse then2successfultoolreturn; local19checks0. No moreprobe paidcalls. delivery_index(gpt-6-luna/medium existingthread) assigned narrowREADME/release-index update toacceptedM1/isolatedT04 scope, no sourcecode/credentials/tests changes.

T13 formal GO after backend_m2/frontend_m2 explicitly stable/stopped. qa_security owns tests/, review/findings/, evidence/qa/; full manual route, negative conditions, idempotency/concurrency, snapshot invariants/owner/version, true service restart persistence,3widths UI and overall checker with exact source hashes. Any implementation defect goes to Owner then independent retest. No real calls/commits/spawns.
T14/T15 preparation: ai_m3 newly spawned explicitgpt-6.1-sol/high/forknone, read-only until M2 acceptance; then backend/app/ai/ + evidence/ai/ only. Prepare minimal Store/runtime boundary, no network in SQLite write transaction, shared request reservations/current generation, visible-only context, hard turn limits/proposal precheck. No paid calls before separate integration validation gate.

Simple M2 delivery-index: new delivery_m2_index explicitly spawned gpt-6-luna/medium/fork none after prior delivery_index stopped; owns README.md/release/README.md and evidence/delivery/docs-index-M2-*.json only. Update actual manual candidate/controls and safe reset limitations; independent API27passed but browser/checker still pending. No code/testing/payment/key reads/commit/spawn. Read-only T16/AI protocol preparations complete; no QA source changes.
