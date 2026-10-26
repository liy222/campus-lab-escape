"""Explicit content2 rebuild/check; never writes the historical v1 contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.domain.generation_content_v2 import CONTENT_VERSION, FAMILIES, content_schema, select_blueprint

TARGET = Path(__file__).with_name('generation-content-v2.schema.json')


def build():
    variants = []
    for seed, family in enumerate(FAMILIES):
        for room_count in (1, 2, 3):
            for difficulty in ('easy', 'normal', 'hard'):
                blueprint = select_blueprint(room_count, difficulty, seed=seed)
                assert blueprint.family == family
                variants.append(content_schema(blueprint))
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema',
            'title': 'Host descriptions with AI names and typed facts (internal content2)',
            'content_contract_version': CONTENT_VERSION,
            '$defs': variants[0]['$defs'], 'oneOf': variants}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Read-only exact content2 contract check')
    args = parser.parse_args()
    encoded = json.dumps(build(), ensure_ascii=False, indent=2) + '\n'
    if args.check:
        if not TARGET.exists() or TARGET.read_text(encoding='utf-8') != encoded:
            raise SystemExit('Internal generation content2 contract is missing or stale')
        print('generation-content-v2.schema.json matches all 18 current variants')
    else:
        TARGET.write_text(encoded, encoding='utf-8')
        print('Wrote generation-content-v2.schema.json (18 variants)')


if __name__ == '__main__':
    main()
