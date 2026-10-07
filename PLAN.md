# Plan
Source: docs/execution-plan.md V2.1, R01-R18 and A01-A28 retained without reduction.
M0 T01 scope DONE (course source PPT not supplied), T02 contract READY, T03 runnable scaffold READY, T04 mock probe READY / real BLOCKED.
M1 T05 state <- T02,T03; T06 R1 <- T05; T07 UI <- T02,T03,T06; T08 independent QA <- T06,T07.
M2 T09 rooms <- M1; T10 UI <- T07,T09; T11 transactions <- T06,T09; T12 saves <- T11; T13 manual regression <- T09-T12.
M3 T14 provider <- T04,T02,M2; T15 dispatcher <- T14; T16 confirmation <- T11,T15; T17 UI <- T15,T16; T18 QA <- T14-T17 (real blocked).
M4 T19 check <- M3; T20 boundaries <- T19; T21 freeze <- T20; T22 samples <- T02,T21.
M5 T23 pilot <- T22,approved provider/budget; T24 experiment <- T23; T25 conclusions <- T24; T26 evaluator <- T22; T27 calibration <- T26,E1 (partial without E1/human).
M6 T28 change <- baseline v1 (engineering rehearsal unless teacher approved); T29 implement <- T28; T30 adversarial QA <- T29.
M7 T31 release <- T30; T32 reproduction/human acceptance <- T31.
The dependency outline above is historical planning. Current status is the authoritative progression below; R/A scope is retained and completion is bound to actual evidence, never inferred only from test counts.

Current authoritative progression (2026-10-06): ENGINEERING_DELIVERY_COMPLETE_WITH_DISCLOSED_LIMITS, final docs/Git sync closing. T01-T23 accepted within recorded scopes; T24 frozen experiment terminal data remain69completed/2failures/1notcalled and34fullpairs/36planned, not72success; T25 independent merged1427review accepted. T26/T27 independent source and actual paid11/11calibration/registeredE1PASS2/CH01PASS3 accepted75resultchecks; old failures/INSUF reports retained. T28-T30 CH01 engineering accepted. T31 finalv6 docs closing; T32 committed-source fullmock install/save/restart/rollback plus separate new source-identical true-provider1turn2calls accepted105checks. Human gameplay explanation/signoff remains unprovided; course confirmation excluded by user. Historical labels below are superseded.

2026-10-02 T18/T19/T20 actual checks completed: independent API46/build0/pytest46+159subtests/browserChrome+Edge6routes/manual3routes, actual subprocesscrash and trace boundaries. Controlled real1turn/2calls tools→proposal→confirm PASS, forcedfirstget_inventory explicitly scoped. T21 Main acceptance/commit/hash-chain freeze IN_PROGRESS; T22-T32 still unexecuted except read-only designs. Full project and human acceptance not inferred.

2026-10-01 M0 accepted: T01/T02/T03 complete; T04 isolated mock complete, real provider explicitly blocked. T05/T06 IN_PROGRESS; T07 READY; T08 waits for stable R1. Main approved contract1.0.0.

2026-10-02 recovery: M0 SHA24c8a02 pushed/private verified. T05/T06 stable backend candidate (29 local checks exit0), pending T08 independent acceptance; T07 in progress; T08 QA independent backend cases in progress, overall UI execution waits for stable frontend. T09/T10/T11/T12 not started until M1 gate. DeepSeek4.1 Flash selected; T04 real awaits locally configured key and approved budget. T14/T15 wait for manual baseline.

2026-10-02 M1 accepted: T05/T06/T07/T08 complete within R1 scope. Independent API13passed/1T13deferred, browser3widths passed, checker0/source stable. T09/T10/T11/T12 READY; T13 waits for stable complete manual candidate. RealProvider independent T04 work continues; T14+game AI waits M2. All initial QA scope/launcher/reload-assumption failures retained and do not reduce full-level requirements.

T04 isolatedrealAdapter DONE (actualDeepSeek toolcall/resultreturn completed); exactsuccesssourcehash bound inproviderhandoff; local19checks0 and4realrequests. GameAI T14/T15 notstarted; independentT18 notclaimed. Tokenreservation boundbytes*4+8192 is conservativeengineeringestimate, not officialtokenizerproof; accountingusesreportedusage/high-peakrates andfreeze-on-overrun. Priorfailureprecisesourcehashmissing disclosed.

2026-10-02 M2 stable candidates: Backend T09/T11/T12 owner49checks0; Frontend T10/T12 owner22checks0/build0. Both stopped. T13 formal GO; M2 not accepted until independent results. AI T14/T15 read-only preparation only, no source writes until M2 gate.

2026-10-02 M2 accepted: T09-T13 complete for manual baseline1.0.0; independentAPI27/0skip, browser3width complete/save/resetrestore, overallcheck0/source stable. T14/T15/T16/T17 READY after M2 commit; T18 waits stable M3candidate.

T21 DONE: baseline_v1 product commit7821af4efe0613c20a80ea164c1dab1c0f288bab accepted with explicit scopes/hash chain/unfinished items. T22 implementation READY for experiments/evaluator; T23/T24 real calls await Main finite pilot/formal gates. CH01 stays deferred until E1 on unchanged baseline.

2026-10-03 authoritative continuation: T21 corrected identity independently accepted/pushed9702fe3. T22 experiments original independent review passed; recovery verifies handoff. T26 budget repair stable with independent full review recovering from possible QA harness failures. T23 finite pilot preparation active, no real GO. T24/T25/T27-T32 pending. Course confirmation excluded from blockers by user instruction; no human-signoff claim.

T22 experiment sample/harness scope DONE by independent fresh764checks/actualexit0/83sourcesunchanged. Evaluator T22 fixtures frozen; T26 candidate waits OPEN T26-EVAL-002 Owner fix/independent retest. T23 READY for Main finite pilot6 gate after staged artifact audit/sync; T24 waits actual pilot. Baseline v1 remains unchanged before E1.

2026-10-05 authoritative: T26 engineering DONE by fresh independent193checks/actualexit0/34sourcesunchanged, both Findings CLOSED. T23 actual finite pilot newly admitted; previous quota-interrupted pilot had zero real calls and expired gate, no replacement of failures. T24/T25 wait real pilot evidence. T27 calibration and event registry READY after T26 foundation sync and separate finite paid gates. T28-T32 pending, no human signoff inferred.

T23 DONE engineering pretrial scope: six actual completed known-usage calls and retained two incorrect C06 next actions, upper0.02975152CNY. Main finiteformal72/additional8CNY GO on samefrozeninputs after verifiedcost/headroom; T24 ACTIVE, T25 independent read review waits actual terminal rows. T26 foundation accepted/pushedf9417a7; T27 event registry implementation active, no real calibration yet. T28-T32 unchanged pending.

2026-10-05 T28 specification accepted structuralscope(checker0) and committed/pushedeb81b345184237a12f54a11c5d83b30ae0198c44. T29 Backend candidate stable, T30 independentAPI/browser/check active after54API53pass/one overlystrictQAtext assertion corrected with firstfailure preserved, no productfix claimed. T27 budget accounting isolated124QA0/apply0/readonly48QA0, allcharges/cap retained; newcalibration stillneedsfinitegate afterstableEvaluatorQA. Optional reviewed49notcalled E1 continuation design would preserveoriginaltimeout/incorrectresults and use archivedv1judger; noimplementation/paid GO yet.

2026-10-05 T29/T30 ACCEPTED scopedCH01/RT01-05 with exactrules73a77 and68 Mainchecked evidenceIDs; noproductFinding, twoQAharness failures retained. T31/T32 Deliveryengineering prepared pendingcommittedv2sourcepack, newSol/high actualspawn; T27 formalQApending, 49-firstattemptContinuation codingno paid.
2026-10-05 19:xx: T29/T30 accepted and pushed242ecfc/tagCH01_v2. T27 independent structure168+114 accepted; real calibration exact payload approval pending after auto-review rejection(no request executed). T31 docs prepared, T32 new committed-source reproduction pending. 49-first-attempt continuation stableOwner221, independentQA active, no paid.
2026-10-05 current: T24 continuation independent449 ACCEPTED, Main finite49 preparation0 but real dispatch auto-review rejected beforeprocess; exactpayload approval pending(no calls). T32 clean committedfc70b15 PASS0 with6014bytes/73pytest203subtests/build/npmci/deps/OSrestart-v2-v1, independentread QAactive. T27 E2/E3cardv3 fixedall162archives and minimalidentityalias extension pendingindependentreview; no paid semanticverdict. T31 docs requirelatestfacts finalupdate.

2026-10-05 continuation checkpoint: User exact49+3 payload approvals received. Actual E1 continuation orderly stop48calls/47responses/1unknown/1not_called; merge and independent result QA required. Shared83call upper0.44896184/pending1 prevents calibration. NewCH01 evaluation79/79 and T32read/hash accepted; preserve every historical failed/stopped evidence. T31aggregate manifest and final committed-source clean reproduction remain engineering follow-up.

2026-10-05 remaining work: independent merged69-response/72-terminal data review; new10778-source finalclean read/hash; calibration actual2paid10/11expected must be reported as partial not success. No new fee investigation per user; complete retained upper permits safe original-budget accounting without pretending invoice/usage. Combined6 external payload authorization needed by auto-review, preview generated only. T31manifest and finaldocs must reflect actual limits; normalGit sync continues.


## 2026-10-06 prompt repair accepted offline
Main re-read independent QA:223 checks/36 scenarios/30 captured mock payloads,81 raw sources unchanged,actual exit0 b1dd96. Only explicit citation IDs/output-schema guidance added; strict checkers and old records remain. Evidence: evidence/integration/prompt-repair-accepted-20261006.json. New8 concrete payload authorization remains pending; old approved6 were already dispatched once. Latest verified remote before this acceptance: f80c6af075f6041aa11a4f79ba2e6cb1ea9ecd80. T31 documentation is being corrected to bind exact hashes; T32 fresh-directory real AI and genuine human acceptance remain unverified. No repeated full regression or fee investigation.


## 2026-10-06 human-requested pause
User exact: 尽快完成现有小任务后暂时停止. Current small tasks completed: T31 v5/51 Main raw hash pairs accepted; A28 read-only preparation/relay review finished SOURCE STOP without invocation. Main stops this owned mock demo only (taskkill0; supervised process intentionally ends1); saves and environments preserved. No new paid calls, symlink, credential injection or background automation. New8 evaluation authorization, A28 real segment and genuine human signoff remain pending; old6 calls never replay. Recovery entry: evidence/integration/pause-checkpoint-20261006.json and release/README.md. Resume only when the user requests it. All chronological older states remain history.


## 2026-10-06 human-requested resume
User: 继续，尽快完成. Pause revoked; Main resumes only remaining finite acceptance and delivery. A28 initial file symlink attempt exited1/c4f09f before provider dispatch (0calls); preserve record. New source-identical10778 directory and Root canonical ledger directoryjunction prepared0/c986b6; no data/budget copy or source guard relaxation. Independent fast review before paid segment. New8 revised evaluation approval still pending; old6 payloads not resent. No full regression or fees investigation repeated.


## 2026-10-06 final actual engineering acceptance
A28 new fixed-source directory controlled true-provider check actualexit0/6c6318,2calls/1turn,independent105/105 exit0/e56e64; original0-call symlink privilege failure retained and avoided via new directoryjunction using same original ledger. New approved8 evaluation calls actual3/2/3 eachprocess0 (b12baf/36d62b/e00085),source14 unchanged; calibration11/11 (3paid+8deterministic),E1registered stopped-materialPASS2,CH01scripted-engineeringPASS3. Independent75/75 actual0/02f6ff. No old outcome/call replay, no new budget/invoice claim. Full source/mock clean and controlled true segment are separate accepted scopes. E1frozen72 terminal still69complete/2fail/1notcalled and34completepairs/36planned; no fabricated full success. Human explanation/signoff remains unprovided; excluded course questions not pursued. Deliveryv6 is final document epoch, then normal commit/push.


## Final delivery handoff, 2026-10-06
Deliveryv6 stable SOURCE STOP; Main81 current path/SHA pairs passed with no mismatch, source14 unchanged and7document hashes match Owner report. Existing failed/unknown/notcalled/olderINSUF records preserved. Local free mock demo started at http://127.0.0.1:5173/ with explicit v2 database; no background Agent/paid work. Engineering/source/scoped actual acceptance completed; genuine human gameplay explanation/signature is still unprovided and the experiment retains its statedpartial terminal outcomes. No pending new8 authorization or uncalled new8 jobs remains. Normal final commit/push follows; exact synced SHA is current Git HEAD after verification.


## 2026-10-06 one-click startup addon
User requested Windows double-click startup. Added 启动游戏.cmd with specified Python, v2 database and free mock provider; scripts.dev opens the browser only after both services are healthy. Actual launcher from scripts directory passed frontend/backend HTTP 200; Ctrl+C stopped both services with no remaining listeners. Interrupted Windows CMD wrapper exited1, preserved without claiming exit0. Evidence: evidence/integration/one-click-startup-20261006.json. Earlier product tags/source and document hashes remain historical; this is a separate addon epoch. No dependency install, environment reset or paid call.


## 2026-10-06 gameplay AI settings task
User requested an in-game mock/real AI selector and manually entered API Key. Main dispatched play_ai_backend and play_ai_frontend with requested gpt-6.1-sol/high, as returned by spawn task creation; Main runtime is not independently verified. Backend owns routes.py and ai/runtime.py for this epoch; Frontend owns Assistant.tsx/api.ts/style.css. Credentials are ephemeral request headers to the local backend, never persisted or sent as model content. Explicit mock is free; explicit deepseek requires entered key and fixed existing official provider/model, retains canonical budget. Independent QA follows stable SOURCE STOP; no paid call is needed to implement or verify this task.


## 2026-10-06 gameplay AI settings accepted
Stable five-file implementation accepted after independent API7+9 and actual Chrome375/1280 exit0. Existing backend regression46+88 passed; frontend build0. Key is password input in React memory, only passed to local AI-turn request headers; request-specific provider and original canonical budget retained. Refresh/mode/session/reset/restore clears key, no save/database/model-message credential leakage; mock proposals and manual actions verified. Main reread report, checked candidate hashes and viewed mobile screenshot. Initial browser-script assumption failure retained. No paid calls or real-key validity claims. Evidence: evidence/integration/play-ai-settings-accepted-20261006.json. Normal private GitHub synchronization follows.


## Upgrade epoch 2026-10-06
Primary accepted upgrade design baseline: docs/upgrade-plan.md, copied byte-identically from the user attachment. The old execution-plan remains historical scope/evidence. Execute v3.0 -> v3.1 -> v3.2 -> v3.3 -> v3.4 -> v4.0 -> v4.1 -> v4.2; no Phaser/final art before full v3.4 graybox passes. Reuse current backend/API/AI/storage/sync; retain three rooms and stated small puzzle scope. Baseline HEAD502a383 first full reads and existing pytest/build, then v3.0. Each version requires actual main route/save/restore/reload tests, old-save policy, documents and own normal commit/push using liy222 identity. Keep reports concise, simple tasks Luna, implementation/complex independent review Sol as needed; no Astra unless necessary. Prior ignored runtime artifacts remain untouched. Actual dispatch configurations are recorded in evidence/upgrade/baseline-plan-20261006.json; Main runtime not independently verified.


### Upgrade baseline accepted / v3.0 active
Actual baseline pytest80+212subtests and frontendbuild exit0; team full reads completed after re-reading truncated output. Evidence: evidence/upgrade/baseline-accepted-20261006.json. v3.0 limited to information/interactions/neutral feedback, same level2/save schema. Backend owns rules.py; frontend Luna owns App.tsx/style.css; QA Luna prepares independent new tests and full browser main route/save/restore/reload after stable candidate. Every stage commit/push remains required. v3.1+ will inject rule/state models into original Store, with legacy entry and separate production upgrade database; no new stack or silent old-save reinterpretation.


### v3.0 accepted, synchronization closing
Independent actual82pytest/220subtests/build0; ChromeR1-R2-R3-EXIT,8wrongtarget attempts preserve state/revision/inventory, R2 save/restore/refreshcontinue and desktop1280/mobile375 layouts passed0. Main checked source RAW against stable candidate and browser before/after. Earlier QA helper/selector failures preserved. Backend level2.0/schema1.0 unchanged; old saves remain compatible, no data migration. Evidence: evidence/upgrade/v3.0/accepted.json. No Phaser/final art/paid calls or human playtime claims. Independent v3.0 commit/push before v3.1GO.


### v3.1 multistate implementation GO
v3.0 commit1499610 and tagv3.0-gameplay-information verified on private remote, authorliy222. Backend Owner now owns newupgrade state/rules, Store and AIStore shared rule dispatch, main and contract generator/schema/routes for this epoch; Frontend Luna owns current3UI/API plus optional vite-env declaration; Delivery Luna owns dev launcher/CMD and README/UPGRADES. Legacy create_app remains original rules, production upgraded; use separate game-v3.1 DB/storage namespace and same-code legacy opt-in to preserve oldsave access. Newmanualinteract strict, four serverdevice state chains, old clue network until3.2. Formal independent QA waits stable source. No minigames/hints/art/Phaser yet. Plan: evidence/upgrade/v3.1/plan.json. Main runtime and resumed agent runtime not independently introspected.

### v3.1 accepted
Four authoritative device chains accepted after invariant fix. Final full89pytest/235subtests0; pre-fixbuild/Chrome0 retained separately, final39stepAPI/save-reopen-restore recertifies delta. Normal own commit/push/tag v3.1-object-state before3.2. Evidence: evidence/upgrade/v3.1/accepted.json.

### v3.2 active
v3.1 cfab661/tagv3.1-object-state pushed and remoteauthor verifiedliy222. Rebuild three-room puzzle dependencies and graybox placement, preserving old version entry/data and same Store/API/AI. Scope/ownership/dependency design: evidence/upgrade/v3.2/plan.json. QA afterstable, owncommit/push before3.3.


### v3.2 accepted, 2026-10-07
Three-room/four-item clue redesign accepted: fixed fullAPI97/257 exit0, all23source/tests before-after identical. First runtime existing-clue text forgery failure retained; narrow complete-record/duplicateID guard independently closed. Originalcandidate build0/Chrome61checks0 (main route/save/restore/reload/OS restart/mobile/oldentries) retained honestly; no UI delta so not rerun afterguard. Evidence evidence/upgrade/v3.2/accepted.json. No paid/Phaser/human timing claim; own commit/push precedes3.3.


### v3.3 mini-games GO, 2026-10-07
v3.2 commit519c8d0/tagv3.2-puzzle-redesign verified on remote, author/committerliy222; stage60 privacy0 and source/docwhitespace0. Current Oct07 agents own exact plan paths in evidence/upgrade/v3.3/plan.json. Backend cross-AI limited to protecting minigames from reads; cross-Spec docs/contracts owned by Backend. FrontendLuna also owns launchers and mechanical docs. QA may change old3.2 fixture selectors to explicitv3.2 only, no weakened assertions. Only circuit+sequence now; noPhaser/hints/score until3.4.


### v3.3 accepted, 2026-10-07
Circuit graph/partial rotation persistence and device sequence accepted on frozen27sources. Independent fullAPI first105pass/291subtests plus1QAwrongexpectedpanelinteract; correct reject expectation directed1pass/3subtests0 provides jointcoverage, not a later full106exit0. Chrome102checks/build0 with save/restore/reload/OSrestart and oldnamespaces; Main viewed partial circuit/sequence screenshots. First QA launcherflag mistake retained then byte/config0. ActualrootCMD/humanplaytime/realmodelquality unverified; paid0/Phaser0. Evidence evidence/upgrade/v3.3/accepted.json; owncommit/push before3.4GO.
