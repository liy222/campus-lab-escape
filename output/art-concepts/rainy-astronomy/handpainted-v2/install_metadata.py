"""Install metadata for actual built-in image_gen outputs; never edits pixels."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MANIFEST = ROOT / 'frontend/src/assets/themes/rainy-astronomy/manifest.json'


def main():
    jobs = json.loads((HERE / 'prompts/generated-assets.json').read_text(encoding='utf-8'))
    assert len(jobs) == len({job['id'] for job in jobs}) == 15
    baseline = HERE / 'manifest-vector-v1.json'
    if not baseline.exists():
        baseline.write_bytes(MANIFEST.read_bytes())
    manifest = json.loads(baseline.read_text(encoding='utf-8'))
    images = []
    variants = {key: variant for group in manifest['objects'].values() for key, variant in group.items()}
    for job in jobs:
        path = ROOT / job['target']
        payload = path.read_bytes()
        assert payload == Path(job['source']).read_bytes(), 'Generated original bytes changed'
        with Image.open(path) as image:
            width, height = image.size
            if job['category'] == 'objects':
                assert 'A' in image.getbands() and image.getchannel('A').getextrema() == (0, 255)
                bounds = image.getchannel('A').point(lambda value: 255 if value >= 16 else 0).getbbox()
                assert bounds
                left, top, right, bottom = bounds
                bbox = {'x': left, 'y': top, 'width': right - left, 'height': bottom - top}
            else:
                assert width >= 1600 and abs(width / height - 16 / 9) < 0.01
                bbox = {'x': 0, 'y': 0, 'width': width, 'height': height}
        url = '/' + path.relative_to(ROOT / 'frontend/public').as_posix()
        if job['category'] == 'backgrounds':
            manifest['backgrounds'][job['id']] = {'src': url, 'width': width, 'height': height, 'bbox': bbox}
        else:
            variants[job['id']].update(src=url, closeup=url, width=width, height=height, bbox=bbox,
                closeup_width=width, closeup_height=height, closeup_bbox=bbox)
        images.append({'id': job['id'], 'path': path.relative_to(ROOT).as_posix(), 'width': width,
            'height': height, 'bbox': bbox, 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(),
            'transparent': job['transparent_background']})
    # Place tabletop props at the new painted table plane; preserve floor slots.
    for slots in manifest['slot_layout'].values():
        for slot in slots[:4]:
            delta = 480 - slot['y']
            slot['y'] = 480
            slot['hotspot']['y'] += delta
    manifest['pack_version'] = '1.1.0'
    manifest['coverage'] = '雨夜天文社相关主题，手绘重建版；其他主题使用通用素材。'
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    report = {'installed_at_utc': datetime.now(timezone.utc).isoformat(), 'method': 'built-in image_gen',
        'image_tool_calls': len(jobs), 'project_provider_paid_calls': 0,
        'physical_images': len(images), 'backgrounds': 3, 'object_state_images': 12,
        'closeup_presentations': 12, 'closeup_policy': 'Same high-resolution original also used for closeup; not 12 extra generated files',
        'pixel_edits_by_this_script': False, 'bbox_alpha_threshold': 16,
        'total_bytes': sum(row['bytes'] for row in images), 'images': images}
    (HERE / 'assets.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({key: report[key] for key in ['physical_images', 'backgrounds', 'object_state_images', 'total_bytes']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
