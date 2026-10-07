# Agent ownership
The human is the sole developer. The attachment docs/execution-plan.md is the accepted project scope, not proof of execution. Never invent tests, people, approvals or model calls.
Main owns AGENTS.md, PLAN.md, STATUS.md, DECISIONS.md, integration and git. Agents write only assigned paths, never commit, never spawn further agents. Shared workspace; do not overwrite another owner's files. Default delegates gpt-6.1-sol/high, simple mechanical tasks gpt-6-luna/medium. No Astra unless needed. Main runtime model is not independently introspectable and must not be claimed as verified.
Spec owns docs/SPEC.md, docs/level_design.md, contracts/. Delivery owns scripts/, README.md, release/, .gitignore, .env.example. Backend owns backend/app/{domain,api,storage}, backend/app/main.py and Python dependencies. Frontend owns frontend/. AI owns backend/app/ai/. QA owns tests/ and review/findings/. Experiments owns experiments/. Evaluator owns evaluation/.
Every task report: files, actual commands/exit codes, evidence paths, unresolved limitations. Formal QA runs only after candidate implementation is stable. Secrets, session tokens, databases, node_modules, environments and raw sensitive logs must never be committed. No public deployment or Actions. Real paid calls require credentials and approved budget. Do not delete/reset existing environments.

Recovery dispatch: main records requested model configurations only from actual spawn results; resuming existing agents does not independently reveal their runtime model. On 2026-10-02, ai_provider was spawned as gpt-6.1-sol/high and delivery_index as gpt-6-luna/medium. Delivery README/release index handed to delivery_index after delivery_docs stopped; scripts/config code remains Delivery engineering owner. No Astra call was made in this recovery.

Sequential role handoff on 2026-10-06: qa_events_oct05 sealed its old-source independent QA before Main reassigned it temporarily as Evaluator Owner for evaluation/engine.py, evaluation/README.md, review/calibration.md and new prompt-reference-fix evidence. It does not certify its own new implementation; qa_ch01_oct05 is assigned the subsequent independent QA. Existing requested configurations are historical spawn facts only; resuming does not reveal runtime. Main did not use Astra.

Final documentation handoff on 2026-10-06: after Evaluator code and actual-result QA were sealed SOURCE STOP, Main assigns delivery_final_docs_oct05 the two mechanical metadata paths evaluation/README.md and review/calibration.md in addition to its Delivery document paths. No Python code or old run evidence is changed. This is a separate document epoch; c9 original source-map Markdown hashes remain historical. Existing Luna configuration is a recorded prior spawn fact, not independently verified on resume.


## 2026-10-06 gameplay AI settings task
User requested an in-game mock/real AI selector and manually entered API Key. Main dispatched play_ai_backend and play_ai_frontend with requested gpt-6.1-sol/high, as returned by spawn task creation; Main runtime is not independently verified. Backend owns routes.py and ai/runtime.py for this epoch; Frontend owns Assistant.tsx/api.ts/style.css. Credentials are ephemeral request headers to the local backend, never persisted or sent as model content. Explicit mock is free; explicit deepseek requires entered key and fixed existing official provider/model, retains canonical budget. Independent QA follows stable SOURCE STOP; no paid call is needed to implement or verify this task.


# Future commit identity, 2026-10-06
User explicitly requests all future project commits use their GitHub account. Verified gh user: liy222, id 177762329. Repository-local Git user.name is liy222; user.email is 177762329+liy222@users.noreply.github.com. Use this configured identity for both author and committer; never override with Codex/codex@local.invalid. Do not rewrite historical commits or tags under this authorization.


## Upgrade epoch 2026-10-06
Primary accepted upgrade design baseline: docs/upgrade-plan.md, copied byte-identically from the user attachment. The old execution-plan remains historical scope/evidence. Execute v3.0 -> v3.1 -> v3.2 -> v3.3 -> v3.4 -> v4.0 -> v4.1 -> v4.2; no Phaser/final art before full v3.4 graybox passes. Reuse current backend/API/AI/storage/sync; retain three rooms and stated small puzzle scope. Baseline HEAD502a383 first full reads and existing pytest/build, then v3.0. Each version requires actual main route/save/restore/reload tests, old-save policy, documents and own normal commit/push using liy222 identity. Keep reports concise, simple tasks Luna, implementation/complex independent review Sol as needed; no Astra unless necessary. Prior ignored runtime artifacts remain untouched. Actual dispatch configurations are recorded in evidence/upgrade/baseline-plan-20261006.json; Main runtime not independently verified.


### v3.1 multistate implementation GO
v3.0 commit1499610 and tagv3.0-gameplay-information verified on private remote, authorliy222. Backend Owner now owns newupgrade state/rules, Store and AIStore shared rule dispatch, main and contract generator/schema/routes for this epoch; Frontend Luna owns current3UI/API plus optional vite-env declaration; Delivery Luna owns dev launcher/CMD and README/UPGRADES. Legacy create_app remains original rules, production upgraded; use separate game-v3.1 DB/storage namespace and same-code legacy opt-in to preserve oldsave access. Newmanualinteract strict, four serverdevice state chains, old clue network until3.2. Formal independent QA waits stable source. No minigames/hints/art/Phaser yet. Plan: evidence/upgrade/v3.1/plan.json. Main runtime and resumed agent runtime not independently introspected.

### v3.1 final document handoff
After Frontend source stop, Main assigns upgrade_frontend_read temporary mechanical Delivery document ownership of README.md and release/UPGRADES.md only. Existing Delivery scripts/CMD remain frozen. Restoring the historical delivery thread hit agent thread limit; no model identity inferred or extra agent created. Final docs wait actual independent QA result; original source evidence and historical reports remain untouched.

Main integration owns only the v3.1 root CMD CRCRLF-to-CRLF normalization after staged whitespace check; command content unchanged, prior Owner/QA epochs preserved. Independent QA byte delta check precedes final commit.

### v3.2 puzzle redesign GO
After cfab661/tagv3.1-object-state push verified, Backend owns newpuzzle state/rules and narrow shareddevice helper plus Store selection/main and cross-Spec contracts/docsSPEC/leveldesign; Frontend Luna owns frontend plus temporary Delivery scripts/dev.py/rootCMD/README/UPGRADES. QA owns new3.2 tests/runner/report/evidence; old3.1 fixture selectors may explicitly choosev3.1, assertions retained. Keep old3.1/legacy entries and isolated3.2 data/session. FormalQA only after allstable; no Phaser/art/minigames. evidence/upgrade/v3.2/plan.json records design and dispatch.

Main grants Backend v3.2 only AI runtime read-guard cross-role edit for neutral observed-ID revision increments, with target-only additions/no knowledge deletion and legacy compatibility. Provider/payment/auth remain unchanged; independent QA covers guard and existing AI regression.


### 2026-10-07 upgrade recovery ownership
Prior upgrade agents are no longer live. Main created upgrade_qa_oct07 (requested gpt-6.1-sol/high), upgrade_frontend_oct07 (requested gpt-6-luna/medium), upgrade_backend_oct07 (requested gpt-6.1-sol/high), as returned by actual spawn calls. QA owns tests/review/v3.2 QA evidence and runs only the final fullAPI on SOURCE STOP candidate-fixed. Frontend temporarily owns mechanical README/releaseUPGRADES only until v3.2 closes. Backend reads/plans only until v3.2 commit/push gate. Main retains integration/Git/root documents; no Astra or paid calls. Main runtime remains unverified. Earlier usage-limit interruption is retained, not a completed QA/document claim.


### v3.3 mini-games GO, 2026-10-07
v3.2 commit519c8d0/tagv3.2-puzzle-redesign verified on remote, author/committerliy222; stage60 privacy0 and source/docwhitespace0. Current Oct07 agents own exact plan paths in evidence/upgrade/v3.3/plan.json. Backend cross-AI limited to protecting minigames from reads; cross-Spec docs/contracts owned by Backend. FrontendLuna also owns launchers and mechanical docs. QA may change old3.2 fixture selectors to explicitv3.2 only, no weakened assertions. Only circuit+sequence now; noPhaser/hints/score until3.4.


### v3.4 complete graybox GO, 2026-10-07
v3.3 commit58587cf/tagv3.3-mini-games pushed/remoteverified0, author+committerliy222; stage61 privacy0 and source/docwhitespace0. Ownership and exact constraints: evidence/upgrade/v3.4/plan.json. Backend may temporarily edit AIruntime/newhints helper and storageAI hint request/finalization alongside normalrules/Store/main/contracts/SPEC/leveldesign. Provider/auth/budget code remains frozen. FrontendLuna owns hint selector/settlement/launcher/doc updates, noPhaser. QA owns independent newtests/evidence, runs afterstable. Statistics restore with savedrun; server realelapsed includes offline time; no fabricated human timing. Nextvisual gate waits accepted/pushed3.4.

### User visual-stage hold, 2026-10-07
User explicitly requests stopping before the visual upgrade to supply a detailed plan. Complete only current v3.4 frozen-candidate independent QA, necessary fixes, documentation and normal commit/push. Do not begin v4.0, install Phaser, or perform visual implementation/research until a new user instruction. Existing v3.4 source ownership remains; no paid calls.

### v3.4 accepted / visual stage held, 2026-10-07
Main accepts frozen38-source v3.4 graybox from independent joint QA: first full118methods/315subtests+1newQA erroneous503-mapping expectation (exit1), corrected new method1+3subtests exit0, finalbuild0/Chrome132checks0/issues[]/launcherbyte0. No product fix or second full-green claim; repeated subtests not summed. Three hint levels, two optional stories, statistics/time/score, route/save/restore/reload/OSrestart tested. Evidence: evidence/upgrade/v3.4/accepted.json and qa/result.json. Root CMD not interactively launched; no paid-provider quality/human20-30minute claim. Final version tag v3.4-graybox-complete resolves accepted commit after authorized normal synchronization. Explicit user hold: stop before visuals; no Phaser/v4 work until user provides detailed plan.

### v3.4 remote sync sealed / stopped before visuals, 2026-10-07
Private remote main and tag v3.4-graybox-complete verified at 49a2f925a78055552781685e79ee96496bb9bdd6; GitHub author and committer liy222. Initial version staged64files, selected-secret/runtime-path audit0 and source/doc whitespace0. Main now owns only mechanical post-sync metadata in README.md/release/UPGRADES.md plus normal root progress/sync evidence; Delivery docs.json hashes remain the preceding historical document epoch. No product/source/spec/QA file changes, no retest or additional paid calls. Visual development is STOPPED pending user detailed plan; no Phaser introduced.
