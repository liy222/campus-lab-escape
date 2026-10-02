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

2026-10-01 M0 accepted: T01/T02/T03 complete; T04 isolated mock complete, real provider explicitly blocked. T05/T06 IN_PROGRESS; T07 READY; T08 waits for stable R1. Main approved contract1.0.0.

2026-10-02 recovery: M0 SHA24c8a02 pushed/private verified. T05/T06 stable backend candidate (29 local checks exit0), pending T08 independent acceptance; T07 in progress; T08 QA independent backend cases in progress, overall UI execution waits for stable frontend. T09/T10/T11/T12 not started until M1 gate. DeepSeek4.1 Flash selected; T04 real awaits locally configured key and approved budget. T14/T15 wait for manual baseline.

2026-10-02 M1 accepted: T05/T06/T07/T08 complete within R1 scope. Independent API13passed/1T13deferred, browser3widths passed, checker0/source stable. T09/T10/T11/T12 READY; T13 waits for stable complete manual candidate. RealProvider independent T04 work continues; T14+game AI waits M2. All initial QA scope/launcher/reload-assumption failures retained and do not reduce full-level requirements.
