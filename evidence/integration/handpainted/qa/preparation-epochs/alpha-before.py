"""Read-only frozen-candidate and exact PNG/metadata checks; output new QA evidence."""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8-sig'))
def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('candidate')
    args = parser.parse_args()
    candidate = read(args.candidate)
    protocol = read('evidence/integration/handpainted/qa/preparation.json')
    assert protocol['protocol_ready'], 'Main frozen candidate GO and final owner protocol required'
    errors, checks = [], []
    for label, hashes in [('candidate', candidate['source_sha256']), ('immutable', protocol['immutable_sha256'])]:
        bad = [p for p, h in hashes.items() if digest(p) != h]
        checks.append({'check': label + '-raw-hashes', 'files': len(hashes), 'changed': bad})
        errors.extend(bad)
    catalog = read('output/art-concepts/asset-pack/catalog.json')
    expected = {Path(e['image']).name: e for e in catalog['entries'] if not e['origin'].startswith('reuse')}
    expected.update({Path(e['image']).name: e for e in catalog['clean_backgrounds']})
    metadata = read('frontend/src/assets/painted-metadata.json')
    assert len(metadata) == 85
    used = set()
    for key, entry in metadata.items():
        public = 'frontend/public' + entry['url']
        source = expected.get(Path(public).name)
        assert source, key + ' unexpected copied image'
        used.add(Path(public).name)
        assert digest(public) == source['sha256'], key + ' canonical copy bytes'
        with Image.open(ROOT / public) as image:
            image.load()
            assert image.size == (entry['width'], entry['height'])
            box = image.getchannel('A').getbbox() if 'A' in image.getbands() else (0, 0, *image.size)
            assert box
            bbox = {'x': box[0], 'y': box[1], 'width': box[2]-box[0], 'height': box[3]-box[1]}
            assert bbox == entry['bbox'], key + ' exact nonzero alpha bbox'
            checks.append({'check': 'canonical-PNG-dimensions-alpha-bbox', 'key': key, 'url': entry['url'], 'size': image.size, 'bbox': bbox, 'sha256': source['sha256']})
    assert used == set(expected)
    folder = ROOT / 'evidence/integration/handpainted/qa' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '-static')
    folder.mkdir(parents=True)
    result = {'candidate': args.candidate, 'candidate_sha256': digest(args.candidate), 'exit_code': int(bool(errors)), 'checks': checks, 'errors': errors, 'limitations': ['Static bytes and alpha geometry only; no image appearance or browser claim.']}
    (folder / 'run.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'evidence': str(folder), 'exit_code': result['exit_code'], 'PNG_count': len(metadata)}))
    return result['exit_code']

if __name__ == '__main__':
    raise SystemExit(main())
