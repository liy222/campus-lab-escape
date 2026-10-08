"""Preserve exact verified QA runner epochs and compact first failure diagnosis."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[4]
folder = Path(__file__).resolve().parent
epochs = folder / 'runner-epochs'
epochs.mkdir(exist_ok=True)
current = (root / 'tests/e2e/run_visual_v40.mjs').read_bytes()
text = current.decode('utf-8').replace('\r\n', '\n')
added = '''    checks.push({check:keyboard?'keyboard-independent-hotspot':'real-canvas-one-inspect-closeup',object_id:id,passed:true});
    if(['r1_record','r1_plaque','r1_microscope','r1_photo'].includes(id)) {
      const stage=id==='r1_microscope'?(state.puzzle_states.microscope+(state.clues.some(clue=>clue.object_id===id)?'-eyepiece':'')):'reading';
      const imagePath=path.join(folder,id+'-'+stage+'.png');if(!fs.existsSync(imagePath)) {await canvasPixels(page,id+'-'+stage);await page.locator('.visual-room').screenshot({path:imagePath});}
    }return body;'''
second = text.replace(added, "    checks.push({check:keyboard?'keyboard-independent-hotspot':'real-canvas-one-inspect-closeup',object_id:id,passed:true});return body;")
second = second.replace('  await menu(page);await expect(row).toBeVisible();\n  checks.push', '  await expect(row).toBeVisible();\n  checks.push')
first = second.replace("await expect(page.locator('.menu-statistics [data-stat=\"hint_count\"]')).toHaveText('3');await closeDrawer(page);", "await expect(page.locator('.run-statistics [data-stat=\"hint_count\"]')).toHaveText('3');")
records = []
for name, data, expected in [
    ('first.mjs', first.replace('\n', '\r\n').encode(), '6267beb77f29bf8d3bb97167a7c9c4a8d9994b1750a6ad1c8b8c2b6f95589114'),
    ('second.mjs', second.replace('\n', '\r\n').encode(), 'c7e899062405bc97c423c85dc66bfce95c39cf9c820ca1b3e8530e75b78caeb3'),
    ('third.mjs', current, '246b1ef37c438e84850b88be0b9c9e50a417486149555f9635419c79bf7885b3'),
]:
    actual = hashlib.sha256(data).hexdigest()
    assert actual == expected, name
    (epochs / name).write_bytes(data)
    records.append({'path': str((epochs / name).relative_to(root)).replace('\\', '/'), 'sha256': actual, 'purpose': 'QA source archival copy only, not a runnable entry point'})
attempts = []
for name, failure in [
    ('20261007T135059759Z-browser', 'New QA selector run-statistics absent in visual R1; actual menu-statistics has server hint count. Exact3 assertion retained with container adaptation.'),
    ('20261007T135341093Z-browser', 'New QA assumes archive row visible after generation-changing restore. Product closes menu on restore; reopen menu before retained row-visibility assertion.'),
]:
    path = folder / name / 'run.json'
    record = json.loads(path.read_text())
    attempts.append({'run': str(path.relative_to(root)).replace('\\', '/'), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'command': record['command'], 'exit_code': record['exit_code'], 'checks_count': len(record['checks']), 'source_85_before_after_same': record['source_sha256_before'] == record['source_sha256_after'], 'diagnosis': failure, 'issues': record['issues']})
(folder / 'browser-attempts.json').write_text(json.dumps({'runner_epochs': records, 'first_attempts': attempts, 'scope': 'Historical failures preserved; repeated checks are not added to final coverage', 'product_edits': 0}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'exit_code': 0, 'verified_runner_epochs': len(records), 'preserved_attempts': len(attempts)}))
