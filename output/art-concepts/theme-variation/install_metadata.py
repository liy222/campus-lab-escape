"""Copy generated originals, inspect pixels and install additive visual metadata."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
THEMES = ('rainy-astronomy', 'library-archive', 'chemistry-lab', 'computer-room', 'campus-broadcast')
DEVICES = ('terminal', 'cabinet', 'circuit', 'panel')


def slots(table_y):
    result = []
    for index, x in enumerate((190, 530, 1070, 1410, 275, 625, 975, 1325)):
        y, height, width = (table_y, 190, 230) if index < 4 else (855, 230, 250)
        result.append(dict(x=x, y=y, height=height, hotspot=dict(x=x-width/2, y=round(y-height*.96, 2), width=width, height=round(height*1.045, 2))))
    return result


def run():
    stage_path = ROOT/'evidence/project/stages/v5-theme-variation/stage.json'
    stage = json.loads(stage_path.read_text(encoding='utf-8'))
    cutoff = stage['catalog_additions_available_from']
    records = []
    for path in sorted(HERE.glob('*.json')):
        job = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(job, dict) or 'target' not in job:
            continue
        assert job['theme'] in (*THEMES, 'shared') and job['available_from'] == cutoff
        destination = (ROOT/job['target']).resolve()
        destination.relative_to((ROOT/'frontend/public/art-themes'/job['theme']/'variation-v1').resolve())
        source = Path(job['source'])
        payload = source.read_bytes()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            assert destination.read_bytes() == payload, 'Refusing to replace an existing original'
        else:
            shutil.copyfile(source, destination)
        with Image.open(destination) as image:
            width, height = image.size
            if job['transparent_background']:
                assert 'A' in image.getbands()
                alpha = image.getchannel('A')
                assert alpha.getextrema()[0] == 0 and alpha.getextrema()[1] > 16
                bounds = alpha.point(lambda value: 255 if value >= 16 else 0).getbbox()
                assert bounds
                left, top, right, bottom = bounds
                box = dict(x=left, y=top, width=right-left, height=bottom-top)
            else:
                box = dict(x=0, y=0, width=width, height=height)
        records.append({**job, 'width': width, 'height': height, 'bbox': box, 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
    complete = len(records) == 31
    if complete:
        for theme in THEMES:
            pack = json.loads((HERE/(theme+'-manifest-base.json')).read_text(encoding='utf-8'))
            pack['pack_version'] = '1.2.0' if theme == 'rainy-astronomy' else '1.1.0'
            for role in DEVICES:
                for variant in pack['objects'][role].values():
                    variant.setdefault('family', role+'-original')
            pack['background_variants'] = {}
            selected = [row for row in records if row['theme'] in (theme, 'shared')]
            for row in selected:
                url = '/' + Path(row['target']).relative_to('frontend/public').as_posix()
                metadata = dict(src=url, width=row['width'], height=row['height'], bbox=row['bbox'])
                if row['category'] == 'backgrounds':
                    base = row['base_id']
                    pack['background_variants'][base] = [
                        dict(id=theme+':'+base+':original', background=copy.deepcopy(pack['backgrounds'][base]), slots=copy.deepcopy(pack['slot_layout'][base])),
                        dict(id=theme+':'+row['id'], background=metadata, slots=slots(row['table_y']), available_from=cutoff),
                    ]
                else:
                    variant = dict(role=row['role'], state=row['state'], note_style=row.get('note_style'),
                        available_from=cutoff, **metadata, closeup=url, closeup_width=row['width'], closeup_height=row['height'], closeup_bbox=row['bbox'])
                    if row.get('family'):
                        variant['family'] = row['family']
                    pack['objects'][row['role']][row['theme']+'-'+row['id']] = variant
            assert len(pack['background_variants']) == 3
            path = ROOT/'frontend/src/assets/themes'/theme/'manifest.json'
            path.write_text(json.dumps(pack, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    result = dict(installed_at_utc=datetime.now(timezone.utc).isoformat(), method='built-in image_gen',
        image_tool_calls=len(records), physical_new_images=len(records), project_provider_paid_calls=0,
        pixel_edits_by_this_script=False, available_from=cutoff, manifests_installed=complete,
        closeup_policy='Same high-resolution original pixels used for scene and closeup', images=records)
    (HERE/'assets.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    target = ROOT/'evidence/project/stages/v5-theme-variation/logs/image-generation.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    stage.update(image_tool_calls=len(records), copied_originals=len(records), manifests_installed=complete)
    stage_path.write_text(json.dumps(stage, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'copied_originals': len(records), 'manifests_installed': complete}, ensure_ascii=False))


if __name__ == '__main__':
    run()
