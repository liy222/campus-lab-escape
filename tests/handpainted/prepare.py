"""Prepare new QA adapters only; never execute the game or build."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'evidence/integration/handpainted/qa'
OUT.mkdir(parents=True, exist_ok=True)
paths = set()
for directory in ('backend', 'contracts', 'tests', 'output/art-concepts/asset-pack'):
    for path in (ROOT / directory).rglob('*'):
        if path.is_file() and not any(part in ('__pycache__', 'node_modules', '.venv') for part in path.parts):
            rel = path.relative_to(ROOT).as_posix()
            if directory == 'tests' and rel.startswith('tests/handpainted/'):
                continue
            paths.add(rel)
paths.add('frontend/src/api.ts')
paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT / 'frontend/src/assets').glob('*.svg'))
protocol = {
    'status': 'Independent adapter preparation; formal execution waits Main frozen candidate GO',
    'protocol_ready': False,
    'operator': 'paint_qa',
    'scope': 'One frontend build and real UI route, state/render/clue/hotspot checks, archives/reload/one backend restart, PNG retry/lazy/Victory',
    'paid_calls': 0,
    'failure_asset': '**/art-handpainted/backgrounds/r1-room-shell.png*',
    'bbox_protocol': 'Transparent objects alpha>16; catalog kind closeup, clean backgrounds and no-alpha images full canvas',
    'paint_frame_marker': 'bbox-contain-v1',
    'controlled_clues_protocol': 'comma-separated known state.clues object IDs matching projection.view, plus r1_symbols while viewing r1_cabinet; original order',
    'minigame_hotspot_protocol': 'Actual responsive DOM rectangles of modules/devices pairwise nonoverlapping with 0.05 CSS px float epsilon; desktop edge mouse/keyboard correct object/module receipt or device draft per room',
    'immutable_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sorted(paths)},
    'limitations': ['No build/browser/API execution by this preparation.', 'Final asset and geometry protocol needs owner SOURCE STOP.'],
}
(OUT / 'preparation.json').write_text(json.dumps(protocol, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
old = (ROOT / 'tests/e2e/run_closeup_panel.mjs').read_text(encoding='utf-8-sig')
scaffold = old[:old.index('async function run(){')]
scaffold = scaffold.replace("'../..'", "'../..'")
scaffold = scaffold.replace('evidence/integration/closeup-panel/qa', 'evidence/integration/handpainted/qa')
scaffold = scaffold.replace('campus-closeup-panel-', 'campus-handpainted-')
scaffold = scaffold.replace("assert(['all','r1','r2','r3','remaining'].includes(only));", "assert.equal(only,'all');")
fragment = (ROOT / 'tests/handpainted/browser-body.mjs').read_text(encoding='utf-8')
runner = scaffold + fragment
(ROOT / 'tests/handpainted/run_browser.mjs').write_text(runner, encoding='utf-8')
print(json.dumps({'status': 'prepared only', 'immutable_files': len(paths), 'formal_runs': 0}))
