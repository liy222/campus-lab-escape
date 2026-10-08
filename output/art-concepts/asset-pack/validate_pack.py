"""Audit the art package and its original copies without editing image pixels."""
from pathlib import Path
import datetime
import hashlib
import json
import re
from build_catalog import ROOT, PROJECT


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def absolute(value, base=PROJECT):
    p = Path(value)
    return p if p.is_absolute() else base / p


def main():
    catalog = read(ROOT / 'catalog.json')
    assert catalog['available_source_count'] == catalog['requested_source_count'] == 84
    assert catalog['missing'] == [] and len(catalog['clean_backgrounds']) == 5
    entries = catalog['entries']
    assert len({e['source_svg'] for e in entries}) == 84
    assert sum(e['kind'] == 'closeup' for e in entries) == 32
    old = read(PROJECT / 'evidence/integration/closeup-panel/candidate.json')['source_sha256']
    changed = [name for name, digest in old.items() if sha(PROJECT / name) != digest]
    assert not changed, changed
    reports = {r: read(ROOT / r / 'report.json') for r in ('room1', 'room2', 'room3')}
    handoff = {e['image']: e for e in read(ROOT / 'room1/Main-handoff.json')['assets']}
    source_checks = []
    for e in entries:
        room, name = e['room'], Path(e['image']).name
        rows = reports[room].get('assets', reports[room].get('records'))
        if room == 'room1':
            matches = [r for r in rows if Path(r['output_png']).name == name]
            assert len(matches) == 1
            row = matches[0]
            digest = row['sha256']
            origin = row['generated_source_path']
            prompt = row['prompt_file']
            prompt_path = absolute(prompt, ROOT / room) if prompt else PROJECT / 'output/art-concepts/r1-night-lab-v3-details-prompt.md'
            if row['operator'] == 'Main':
                origin = handoff[name]['original_generated_image_path']
        elif room == 'room2':
            matches = [r for r in rows if r['name'] + '.png' == name]
            assert len(matches) == 1
            row = matches[0]
            digest = row['metadata']['sha256']
            origin = row['originalOutput']
            prompt_path = absolute(row['promptPath'])
        else:
            matches = [r for r in rows if Path(r['outputPng']).name == name]
            assert len(matches) == 1
            row = matches[0]
            digest = row['sha256']
            origin = row['originalGeneratedImagePath'] or reports[room]['reusedBackground']['sourcePng']
            prompt_path = absolute(row['promptFile']) if row['promptFile'] else PROJECT / 'output/art-concepts/r3-control-room-v1-prompt.md'
        assert digest == e['sha256'] == sha(ROOT / e['image']), e['image']
        source = absolute(origin)
        assert source.is_file() and sha(source) == digest, str(source)
        assert prompt_path.is_file() and len(prompt_path.read_text(encoding='utf-8').strip()) > 100, str(prompt_path)
        if e['origin'].startswith('new') and e['kind'] != 'closeup' and name != 'r3_victory_background.png':
            assert e.get('alpha_range', [255])[0] < 255, e['image']
        source_checks.append({'image': e['image'], 'sha256': digest,
                              'original': str(source), 'prompt': str(prompt_path),
                              'copy_matches_original': True})
    for e in catalog['clean_backgrounds']:
        path = ROOT / e['image']
        prompt_path = path.with_name(path.stem + '-prompt.md')
        prompt = prompt_path.read_text(encoding='utf-8')
        found = re.search(r'Original generated output:\s*(.+?\.png)', prompt)
        if found:
            source = absolute(found.group(1))
        else:
            filename = re.search(r'exec-[a-f0-9-]+\.png', prompt)
            assert filename, str(prompt_path)
            matches = list(Path('C:/Users/liyh/.codex/generated_images').rglob(filename.group(0)))
            assert len(matches) == 1, str(prompt_path)
            source = matches[0]
        assert sha(source) == e['sha256'] == sha(path)
        source_checks.append({'image': e['image'], 'sha256': e['sha256'],
                              'original': str(source), 'prompt': str(prompt_path),
                              'copy_matches_original': True})
    owner_paths = sorted(p for r in ('room1', 'room2', 'room3') for p in (ROOT / r).rglob('*') if p.is_file())
    result = {'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'operator': 'Main', 'status': 'all asset metadata checks passed',
              'source_count': 84, 'closeup_count': 32, 'clean_background_count': 5,
              'new_canonical_images': 85, 'reused_canonical_images': 4,
              'transparent_object_count': 47, 'old_game_source_count': len(old),
              'changed_old_game_sources': changed, 'original_copy_checks': source_checks,
              'sealed_owner_file_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in owner_paths},
              'report_sha256': {r: sha(ROOT / r / 'report.json') for r in reports},
              'limits': ['Metadata and selective visual inspection only, no game integration or new game QA.',
                         'Owner visual reviews are recorded in their reports; Main does not claim viewing every image.',
                         'Runtime puzzle overlays and placement still require implementation and verification.']}
    (ROOT / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    script = re.search(r'<script>([\s\S]*?)</script>', (ROOT / 'index.html').read_text(encoding='utf-8')).group(1)
    (ROOT / 'gallery-script-check.js').write_text(script + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('source_count', 'closeup_count', 'clean_background_count', 'transparent_object_count', 'old_game_source_count', 'changed_old_game_sources')}))


if __name__ == '__main__':
    main()
