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
All not otherwise marked are PLANNED. R/A matrix is retained in source sections 3 and 18 and will be mapped to actual evidence, never inferred from test counts.

Current authoritative progression (2026-10-05): T01-T22 DONE within recorded engineering scopes; T23 real pilot6 independently accepted; T24 STOPPED_INCOMPLETE (22completed/1timeout/49not_called); T25 independently accepted1829checks for stopped-run evidence/descriptive conclusions only. T26 foundation independently accepted193checks; T27 eventregistration/manual accounting under review, real calibration not run. T28 CH01 engineering spec active after101-source raw archive. T29-T32 progress by subsequent stable dependency gates. Human acceptance pending; course confirmation excluded by user. Earlier lines below are historical, superseded by this progression and STATUS.md.

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
