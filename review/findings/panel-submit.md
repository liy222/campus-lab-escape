# Panel submit focused independent QA

Frozen candidate 1006844932ecfb2962512f9a4f7e4ae2b953ee3733cae5e5b4be7b64f0a88a75 passed the single new build and R3 browser run. All 242 product hashes matched before/after and at final audit. QA changed no product, old tests or old evidence.

## Findings

Baseline git-source investigation independently confirmed selected-item routing swallowed device draft input, selected card prevented overview panel inspection, and the panel lacked the authorized CARD_ACCEPTED → FINAL_CHECK entry. Static evidence is reproduction.json; no old-baseline browser reproduction is claimed.

The candidate closes all three. Desktop 1280×900 mouse/keyboard and 375×812 touch/keyboard each verified: natural paper insertion; four early buttons with submission prohibited; explicit direct API pre-card PRECONDITION_FAILED guard; real card use retaining selection; real overview Canvas click inspecting the inserted panel while card remains selected; four device clicks editing only local draft without action/use_item requests; explicit panel start issuing existing interact target exit_door while retaining draft and selected card; clear; WRONG_CODE rejection and one authoritative mistake increment; corrected submission; manual archive/selected restore/reload before submission with local draft clearing according to original rules; UNLOCKED → OPEN → EXIT.

Four representative actual PNGs were opened and inspected: started-held-card-1280.png, card-accepted-draft-375.png, started-held-card-375.png, passed-375.png. No new product or presentation finding was found. Mobile CARD_ACCEPTED uses the existing scroll panel; after start, submit is visible and actual normal Playwright click succeeds. No force click was used.

## Actual commands and evidence

- Python tests/panel-submit/prepare.py: exit 0. New static git show evidence and copied/adapted isolated helpers only.
- Node --check tests/panel-submit/run_browser.mjs: exit 0, syntax only.
- Python tests/panel-submit/run_build.py evidence/integration/panel-submit/candidate.json: exit 0; one build. Evidence: evidence/integration/panel-submit/qa/20261014T062753804700-build/run.json and output.txt.
- Node tests/panel-submit/run_browser.mjs evidence/integration/panel-submit/candidate.json: exit 0; issues []; 154 records (includes public fixture/process records; not a count of UI assertions). Evidence: evidence/integration/panel-submit/qa/20261014T062820276Z-browser/run.json and 14 PNGs.
- Python tests/panel-submit/seal_result.py: exit 0; exact result.json records candidate, actual commands, check categories, screenshot review and artifact digests.

## Files and limits

New QA source only tests/panel-submit/; report review/findings/panel-submit.md; evidence evidence/integration/panel-submit/qa/. All old source/test/evidence paths remain untouched.

R1/R2 used isolated public API prerequisites and are not counted as real UI/human main route. No full 127-method backend suite, paid provider, historical user database, root CMD interactive launch, OS restart or human timing claim. Page draft is intentionally not archived; restored server FINAL_CHECK remains usable after refilling draft. Session tokens and API keys were neither logged nor saved. No new formal failure run occurred; build/browser evidence is retained.
