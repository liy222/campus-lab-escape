# V5 independent offline joint QA

Operator: assigned independent QA agent. Runtime model identity is not independently verified. Product offline gate: **PASS within the finite scopes below**. This is a joint result across explicitly bound candidates and affected reruns, not one complete all-green run. No real model call, canonical budget ledger, player database, human playtest or teacher approval is claimed.

## Actual execution boundaries

| Epoch | Actual result | Evidence under `evidence/upgrade/v5.0/qa/` |
|---|---|---|
| Original 399-source candidate | auth 11 passed; kernel 30 passed; integration 24 passed; security 12 passed; legacy 8 passed; contracts old/new exit 0 | Each named suite's first timestamped run |
| Original generation suite | 16 passed / 1 failed, exit 1: new QA maximal-history fixture incorrectly required success instead of the intended pre-send cost refusal | `generation/20261022T173653.900880Z-9648ea30/` |
| Fixed source, affected only | Generation's one corrected method passed; planner 3 methods passed (nine good/twenty bad inputs, exact state cap and controlled deadline); evaluator 26 passed | `generation-narrow/20261023T060456.344729Z-7b310b59/`, `planner-fixed/20261023T060454591215Z-872c5a05/`, `evaluation/20261023T060528203756Z-4901985e/` |
| Original production build | exit 0 | `build-fixed-20261023T0606/` |
| Take-closeup product fix | Necessary affected production build exit 0 | `build-takefix-1/` |
| Auth/material product fix | 11 passed / 1 failed, exit 1: synthetic legacy cookie was inserted without its host domain, causing HTTPX jar ambiguity | `authmaterial/20261023T063608354079Z-3c340e58/` |
| Final necessary successful command | Exactly five methods passed, exit 0: failed legacy-cookie method plus finite C1 and existing C2/C3 methods for truthful registration | `authmaterial-qa-fixed/20261023T064227981427Z-1ba7558d/` |
| Final identity-only browser | exit 0, issues/page errors/missing assets all empty | `browser-identity-only/20261023T064251.533151Z-15ecff84/` |

Each formal command has its own summary, actual command/exit and equal source-before/source-after map. Commands use the existing Python interpreter and pytest through `scripts.check_v5` or recorded isolated subprocess wrappers. Builds use `tests/v5/run_build.py`. Browser commands use `scripts.check_v5 --suite browser` with the explicit continuation environment recorded in `final-offline-result.json`. Repeated scopes are never added to a grand test count.

## Browser joint coverage and retained failures

Five failed browser epochs remain unchanged:

1. `browser/20261023T060606.736332Z-f42e37ab/`: real classic Phaser and dashboard/classic 1280x720, 390x844, 812x375 controls/overflow passed; QA exact theme label failed because its label includes a character counter.
2. `browser-remaining/20261023T061016.133458Z-ebecd2b1/`: QA exact select labels failed because implicit labels include option text; no generation dispatch occurred.
3. `browser-remaining2/20261023T061406.194090Z-cccf7e62/`: actual generation/status/key clearing, early archive and G1 viewport matrix passed; actual take-closeup product defect blocked subsequent input.
4. `browser-takefix/20261023T062042.556640Z-9c899a5f/`: explicit take-without-Escape recovery, first real inspect via Enter, background click with no action, R2/R3 three-viewports, 38 legal UI actions including reciprocal circuits and sequence to explicit EXIT, three archives/cancel/selected delete/early restore/reload/owned backend restart/relogin passed; actual anonymous-CSRF cross-tab defect blocked B registration.
5. `browser-authmaterial/20261023T063801.567576Z-61ffd296/`: all three actual material-modal conditions passed; QA waited for a fixed welcome heading although a valid registration form was visible after identity invalidation. This was a QA mode expectation, not a product failure.

The final identity-only run used a real owned generated level as necessary setup, then verified cross-tab logout, a valid anonymous auth form, B registration, A's adoption of B identity, cleared temporary Key, no old owner's level in B's list, no browser key/legacy bearer storage, same-origin requests and no page/missing-asset errors. Earlier route/material/size scopes were explicitly reused, not repeated or counted again.

QA viewed the relevant actual PNGs, including failure scenes, classic portrait/landscape, generated R2 portrait/R3 landscape and the new ordered-material modal. Viewports are browser emulation; long pages can scroll vertically. The existing Vite chunk-size and Starlette/HTTPX deprecation warnings remain.

## Four product findings

| Finding | Status and closure evidence |
|---|---|
| P2 planner tracked more than 25,000 states | Closed by pre-insertion capacity check; independent actual count is exactly 25,000 with `PROOF_UNKNOWN`. The controlled deadline is disabled only for the count probe, whose actual elapsed time is 27.95s; this is not a five-second CPU claim. The original E1 25,005 record stays historical. Later material repair leaves the count-guard logic unchanged. |
| P1 taking an item leaves invisible blocking closeup | Closed by the single functional invalid-view cleanup and the actual no-Escape enabled-hotspot/continued route check in the take-fix browser epoch. |
| P2 anonymous CSRF invalidates another tab | Closed by stable derived anonymous context, fixed 600s non-sliding expiry, legacy-context rotation and logout seeding. Independent new API cases and final actual A-to-B browser flow pass. Original behavior failed closed; no disclosure or cross-account access was observed. |
| P1 private material order / conflicting maps | Closed by ordered material instructions only after observing the puzzle and discovering all its required materials; three recipes and early-visibility gates pass. Selected-clue conflicting symbol values reject; identical and unselected mappings remain allowed. The real modal spotcheck confirms rendering without exposing answers. |

Discovery reports and counterexamples remain separate: `v5-planner-bound.md`, `v5-generated-take-closeup.md`, `v5-anonymous-csrf-tabs.md`, `v5-material-sufficiency.md` and their original evidence files. Counterexample commands exiting 0 mean the defect reproduced, not product acceptance.

## Current finite Claim observations

The final successful five-method command produced, without private values:

- `C1-admission-affected.json`: nine room/difficulty admissions with real domain witness replay, twenty frozen bad definitions rejected, exact original input-file hash.
- `C2-observations.json`: eleven private-ID read/write probes, public owner/intruder IDs, actual HTTP statuses and immediate equal target-state hashes including revision/generation.
- `C3-moments.json`: three distinct saved-state hashes, each actually restored equal to its saved hash and original definition hash.
- `C3-bad-checksum.json`: actual rejection and equal current-state hashes. The other three corruption cases remain passed in the original integration scope and are not represented as rerun by this final command.

Main may register the actual successful command and exact source/evidence projection. A failed combined command is never rewritten as exit 0. Final trusted evaluator registration/pin is a separate metadata epoch requiring its own narrow read-only review; the 26 offline evaluator cases are synthetic, not real semantic judgement.

## Remaining release boundaries

Offline generation uses explicit synthetic inputs or a test-only injected generator. Provider-adapter tests use only HTTPX MockTransport and temporary fake ledgers. No real-generation success or broad companion quality is established. Real samples remain Main's separately capped activity after the offline gate, and paid semantic evaluation stays blocked by the three preserved historical unknown reservations.

`preflightreview-v4.json` independently verifies only the executor's two fixed preview-name changes, source binding and all five unchanged payload hashes/cost calculations, with no Key, ledger or network access. Actual A1/A2 payloads must still derive from a successful real generated public stage and real successful A1 history, be saved/bounded before dispatch, and obey the unchanged single-use/five-call/0.70-CNY/no-retry/stop conditions. Placeholder payloads are not actual companion dispatch approval.

No physical mobile device, OS restart, interactive root CMD launch, public deployment, universal security, arbitrary-level solvability, human difficulty timing, complete model naturalness, human signoff or teacher approval is claimed. All Git/integration decisions remain Main-owned.
