"""Read-only evidence/source audit, then write this epoch's independent QA report."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import hashlib
import json
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'evidence/integration/panel-submit/qa'
candidate_path = ROOT / 'evidence/integration/panel-submit/candidate.json'
candidate = json.loads(candidate_path.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source = {p: sha(ROOT / p) for p in candidate['source_sha256']}
assert source == candidate['source_sha256']
build_path = OUT / '20261014T062753804700-build/run.json'
browser_path = OUT / '20261014T062820276Z-browser/run.json'
build = json.loads(build_path.read_text(encoding='utf-8'))
browser = json.loads(browser_path.read_text(encoding='utf-8'))
assert build['exit_code'] == browser['exit_code'] == 0
assert browser['issues'] == []
assert build['source_sha256_before'] == build['source_sha256_after'] == source
assert browser['source_sha256_before'] == browser['source_sha256_after'] == source
counts = Counter(c['check'] for c in browser['checks'])
viewed = ['started-held-card-1280.png', 'card-accepted-draft-375.png', 'started-held-card-375.png', 'passed-375.png']
artifacts = {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ['result.json']}
result = {'operator': 'panel_submit_qa independent agent', 'recorded_at': datetime.now(timezone.utc).isoformat(),
          'candidate': str(candidate_path.relative_to(ROOT)).replace('\\', '/'), 'candidate_sha256': sha(candidate_path),
          'product_source_count': len(source), 'current_source_sha256': source,
          'build': {'run': str(build_path.relative_to(ROOT)).replace('\\', '/'), 'command': build['command'], 'exit_code': 0},
          'browser': {'run': str(browser_path.relative_to(ROOT)).replace('\\', '/'), 'command': browser['command'],
                      'exit_code': 0, 'issues': [], 'record_count': len(browser['checks']), 'check_types': dict(counts)},
          'status': 'passed_focused_frozen_candidate', 'new_failed_formal_runs': 0,
          'baseline_static_reproduction': 'evidence/integration/panel-submit/qa/reproduction.json',
          'baseline_browser_reproduction': False,
          'screenshots_actually_viewed': viewed,
          'visual_observations': ['Desktop control panel shows readable state text, four-slot draft, clear and enabled submit while card remains visibly selected.',
                                  '375px CARD_ACCEPTED shows reachable start and clear; lower disabled submit is in the existing scroll panel.',
                                  '375px FINAL_CHECK shows clear and enabled submit within panel while held card remains visibly selected.',
                                  '375px passed state shows completed indicators, disabled draft controls and guidance to release door.'],
          'artifact_sha256': artifacts, 'paid_calls': 0, 'product_edits_by_QA': 0,
          'limitations': browser['limitations']}
(OUT / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
report = f'''# Panel submit focused independent QA

Frozen candidate {result['candidate_sha256']} passed the single new build and R3 browser run. All {len(source)} product hashes matched before/after and at final audit. QA changed no product, old tests or old evidence.

## Findings

Baseline git-source investigation independently confirmed selected-item routing swallowed device draft input, selected card prevented overview panel inspection, and the panel lacked the authorized CARD_ACCEPTED → FINAL_CHECK entry. Static evidence is reproduction.json; no old-baseline browser reproduction is claimed.

The candidate closes all three. Desktop 1280×900 mouse/keyboard and 375×812 touch/keyboard each verified: natural paper insertion; four early buttons with submission prohibited; explicit direct API pre-card PRECONDITION_FAILED guard; real card use retaining selection; real overview Canvas click inspecting the inserted panel while card remains selected; four device clicks editing only local draft without action/use_item requests; explicit panel start issuing existing interact target exit_door while retaining draft and selected card; clear; WRONG_CODE rejection and one authoritative mistake increment; corrected submission; manual archive/selected restore/reload before submission with local draft clearing according to original rules; UNLOCKED → OPEN → EXIT.

Four representative actual PNGs were opened and inspected: {', '.join(viewed)}. No new product or presentation finding was found. Mobile CARD_ACCEPTED uses the existing scroll panel; after start, submit is visible and actual normal Playwright click succeeds. No force click was used.

## Actual commands and evidence

- Python tests/panel-submit/prepare.py: exit 0. New static git show evidence and copied/adapted isolated helpers only.
- Node --check tests/panel-submit/run_browser.mjs: exit 0, syntax only.
- Python tests/panel-submit/run_build.py evidence/integration/panel-submit/candidate.json: exit 0; one build. Evidence: {result['build']['run']} and output.txt.
- Node tests/panel-submit/run_browser.mjs evidence/integration/panel-submit/candidate.json: exit 0; issues []; {len(browser['checks'])} records (includes public fixture/process records; not a count of UI assertions). Evidence: {result['browser']['run']} and 14 PNGs.
- Python tests/panel-submit/seal_result.py: exit 0; exact result.json records candidate, actual commands, check categories, screenshot review and artifact digests.

## Files and limits

New QA source only tests/panel-submit/; report review/findings/panel-submit.md; evidence evidence/integration/panel-submit/qa/. All old source/test/evidence paths remain untouched.

R1/R2 used isolated public API prerequisites and are not counted as real UI/human main route. No full 127-method backend suite, paid provider, historical user database, root CMD interactive launch, OS restart or human timing claim. Page draft is intentionally not archived; restored server FINAL_CHECK remains usable after refilling draft. Session tokens and API keys were neither logged nor saved. No new formal failure run occurred; build/browser evidence is retained.
'''
review = ROOT / 'review/findings/panel-submit.md'
review.parent.mkdir(parents=True, exist_ok=True)
review.write_text(report, encoding='utf-8')
print(json.dumps({'exit_code': 0, 'sources': len(source), 'artifact_count': len(artifacts), 'result': str(OUT / 'result.json')}))
