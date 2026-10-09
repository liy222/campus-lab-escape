from __future__ import annotations
import hashlib, json, shutil
from pathlib import Path
from PIL import Image

ROOT = Path('.')
PACK = ROOT / 'output/art-concepts/asset-pack'
DEST = ROOT / 'frontend/public/art-handpainted'
META = ROOT / 'frontend/src/assets/painted-metadata.json'
REPORT = ROOT / 'evidence/integration/handpainted/assets/report.json'
CATALOG = json.loads((PACK / 'catalog.json').read_text(encoding='utf-8'))
entries = [e for e in CATALOG['entries'] if e['origin'].startswith('new generated')]
assert len(entries) == 80, f'expected 80 new object images, got {len(entries)}'
backgrounds = [
    ('r1_background', 'backgrounds/r1-room-shell.png'),
    ('r2_background_dark', 'backgrounds/r2-room-shell-off.png'),
    ('r2_background_on', 'backgrounds/r2-room-shell-on.png'),
    ('r3_background', 'backgrounds/r3-room-shell-on.png'),
    ('r3_background_off', 'backgrounds/r3-room-shell-off.png'),
]

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def target_for(rel: str) -> Path:
    return DEST / rel

def copy_exact(source: Path, target: Path):
    if target.exists():
        if sha(source) != sha(target):
            raise RuntimeError(f'refusing to overwrite different existing file: {target}')
        return 'already_identical'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    if sha(source) != sha(target):
        raise RuntimeError(f'copy hash mismatch: {source} -> {target}')
    return 'copied'

def image_meta(path: Path, force_full: bool):
    with Image.open(path) as im:
        im.load()
        w, h = im.size
        if force_full or 'A' not in im.getbands():
            box = (0, 0, w, h)
            threshold = None
        else:
            alpha = im.getchannel('A')
            # Ignore barely visible shadow pixels at alpha 16 and below.
            mask = alpha.point(lambda p: 255 if p > 16 else 0)
            box = mask.getbbox()
            threshold = 16
            if box is None:
                raise RuntimeError(f'no pixels with alpha > 16: {path}')
        x0, y0, x1, y1 = box
        if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
            raise RuntimeError(f'out-of-bounds bbox: {path} {box} {w}x{h}')
        return {'width': w, 'height': h, 'bbox': {'x': x0, 'y': y0, 'width': x1-x0, 'height': y1-y0}}, threshold

metadata = {}
copy_rows = []
for e in entries:
    rel = e['image']
    src = PACK / rel
    dst = target_for(rel)
    status = copy_exact(src, dst)
    force_full = e.get('kind') == 'closeup'
    m, threshold = image_meta(dst, force_full)
    key = Path(e['source_svg']).stem
    if key in metadata:
        raise RuntimeError(f'duplicate metadata key: {key}')
    metadata[key] = {'url': '/art-handpainted/' + rel.replace('\\', '/'), **m}
    copy_rows.append({'source': rel, 'target': str(dst).replace('\\', '/'), 'sha256': sha(src), 'status': status, 'alpha_threshold': threshold, 'forced_full_bbox': force_full})
for key, rel in backgrounds:
    src = PACK / rel
    dst = target_for(rel)
    status = copy_exact(src, dst)
    m, _ = image_meta(dst, True)
    metadata[key] = {'url': '/art-handpainted/' + rel.replace('\\', '/'), **m}
    copy_rows.append({'source': rel, 'target': str(dst).replace('\\', '/'), 'sha256': sha(src), 'status': status, 'alpha_threshold': None, 'forced_full_bbox': True})
if len(metadata) != 85 or len(copy_rows) != 85:
    raise RuntimeError(f'expected 85 delivered metadata/image items, got {len(metadata)}/{len(copy_rows)}')
META.parent.mkdir(parents=True, exist_ok=True)
META.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
report = {
    'status': 'SOURCE STOP',
    'scope': 'Copy 80 new source-mapped object PNGs and 5 clean backgrounds; no pixel editing; omit 4 reused scene images.',
    'actual_commands': [
        {'command': 'Get-Location', 'exit_code': 0},
        {'command': 'C:\\Users\\liyh\\.conda\\envs\\1\\python.exe evidence\\integration\\handpainted\\assets\\install_handpainted.py', 'exit_code': 0},
    ],
    'counts': {'object_pngs': 80, 'clean_backgrounds': 5, 'reused_scene_images_not_copied': 4, 'delivered_total': 85, 'metadata_entries': len(metadata)},
    'metadata_file': 'frontend/src/assets/painted-metadata.json',
    'metadata_schema': 'flat object; source SVG basename without extension keys for 80 object images, plus r1_background, r2_background_dark, r2_background_on, r3_background, r3_background_off; each value has url,width,height,bbox{x,y,width,height}.',
    'bbox_rule': 'PNG source pixels; alpha > 16 for transparent objects; RGB or no-alpha images use full canvas; 32 closeups and five clean backgrounds forced to full-canvas bbox.',
    'files': copy_rows,
    'limitations': ['No scene, SVG, asset manifest, or game integration edits.', 'Four reused full-scene studies are not copied; r2_light_overlay_on is a full-scene image, not a transparent light layer.', 'Bounding boxes are geometric alpha bounds only; runtime alignment/hotspot calibration remains out of scope.'],
}
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'copied_or_identical={len(copy_rows)} metadata={len(metadata)}')
