"""Refresh only the new QA browser adapter while keeping prior execution evidence sealed."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
old=(ROOT/'tests/e2e/run_closeup_panel.mjs').read_text(encoding='utf-8-sig')
scaffold=old[:old.index('async function run(){')].replace('evidence/integration/closeup-panel/qa','evidence/integration/handpainted/qa').replace('campus-closeup-panel-','campus-handpainted-').replace("assert(['all','r1','r2','r3','remaining'].includes(only));", "assert(['all','remaining','presentation'].includes(only));")
(ROOT/'tests/handpainted/run_browser.mjs').write_text(scaffold+(ROOT/'tests/handpainted/browser-body.mjs').read_text(encoding='utf-8'),encoding='utf-8')
print('New QA runner refreshed only; no product/build/browser execution')
