"""Copy generated originals and read pixel metadata; never edit image pixels."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
THEMES = {
    'library-archive': ('图书馆档案', '图书馆阅览、书库与档案整理主题；三房背景与专属资料、终端。', 380),
    'chemistry-lab': ('化学实验室', '校园化学实验、试剂准备和实验管理主题；三房背景与专属资料、终端。', 410),
    'computer-room': ('计算机机房', '校园计算机、微机与机房设备主题；三房背景与专属资料、终端。', 410),
    'campus-broadcast': ('校园广播室', '校园广播、播音和录音资料主题；三房背景与专属资料、终端。', 420),
}
REQUIRED = {'neutral_lab', 'neutral_archive', 'neutral_control', 'note-logbook', 'note-sealed', 'terminal-off', 'terminal-on'}


def run():
    original = json.loads((ROOT/'frontend/src/assets/themes/rainy-astronomy/manifest.json').read_text(encoding='utf-8'))
    records = []
    for path in sorted(HERE.glob('*.json')):
        job = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(job, dict) or 'target' not in job:
            continue
        assert job['theme'] in THEMES
        destination = (ROOT/job['target']).resolve()
        destination.relative_to((ROOT/'frontend/public/art-themes'/job['theme']/'v1').resolve())
        source = Path(job['source'])
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = source.read_bytes()
        if destination.exists():
            assert destination.read_bytes() == payload, 'Refusing to overwrite different original'
        else:
            shutil.copyfile(source, destination)
        with Image.open(destination) as image:
            width, height = image.size
            if job['transparent_background']:
                assert 'A' in image.getbands(), 'Cutout needs real alpha'
                alpha = image.getchannel('A')
                assert alpha.getextrema()[0] == 0 and alpha.getextrema()[1] > 16
                bounds = alpha.point(lambda value: 255 if value >= 16 else 0).getbbox()
                assert bounds
                left, top, right, bottom = bounds
                box = dict(x=left, y=top, width=right-left, height=bottom-top)
            else:
                box = dict(x=0, y=0, width=width, height=height)
        records.append({**job, 'width': width, 'height': height, 'bbox': box, 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
    complete = []
    for theme, (name, coverage, table_y) in THEMES.items():
        selected = [row for row in records if row['theme'] == theme]
        if {row['id'] for row in selected} != REQUIRED:
            continue
        pack = copy.deepcopy(original)
        pack.update(theme_id=theme, pack_version='1.0.0', display_name=name, coverage=coverage)
        pack['objects']['note'] = {}
        pack['objects']['terminal'] = {}
        for row in selected:
            url = '/' + Path(row['target']).relative_to('frontend/public').as_posix()
            metadata = dict(src=url, width=row['width'], height=row['height'], bbox=row['bbox'])
            if row['category'] == 'backgrounds':
                pack['backgrounds'][row['id']] = metadata
            else:
                role = 'note' if row['id'].startswith('note-') else 'terminal'
                variant = dict(role=role, state='completed' if row['id'].endswith('-on') else 'default',
                    note_style=('sealed-note' if row['id']=='note-sealed' else 'logbook') if role=='note' else None,
                    **metadata, closeup=url, closeup_width=row['width'], closeup_height=row['height'], closeup_bbox=row['bbox'])
                pack['objects'][role][theme+'-'+row['id']] = variant
        for slots in pack['slot_layout'].values():
            for index, slot in enumerate(slots):
                if index >= 4:
                    continue
                delta = table_y-slot['y']
                slot['y'] = table_y
                slot['hotspot']['y'] += delta
        target = ROOT/'frontend/src/assets/themes'/theme/'manifest.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(pack, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        complete.append(theme)
    result = dict(installed_at_utc=datetime.now(timezone.utc).isoformat(), method='built-in image_gen',
        image_tool_calls=len(records), physical_new_images=len(records), project_provider_paid_calls=0,
        pixel_edits_by_this_script=False, closeup_policy='Same original pixels, shared scene/closeup presentation',
        shared_roles=['key', 'cabinet', 'circuit', 'panel'], completed_packs=complete, images=records)
    (HERE/'assets.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    stage=ROOT/'evidence/project/stages/v5-campus-theme-library/stage.json'
    current=json.loads(stage.read_text(encoding='utf-8'))
    current.update(image_tool_calls=len(records), copied_originals=len(records), completed_packs=complete)
    stage.write_text(json.dumps(current, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'copied_originals': len(records), 'completed_packs': complete}, ensure_ascii=False))


if __name__ == '__main__':
    run()
