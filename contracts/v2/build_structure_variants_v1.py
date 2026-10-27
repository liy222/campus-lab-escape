"""Explicit rebuild/check of the full internal structure1/content2 catalog."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.domain.generation_content_v2 import CONTENT_VERSION, content_schema, select_blueprint
from backend.app.domain.structure_variants import CATALOG_VERSION, VARIANTS

TARGET = Path(__file__).with_name('generation-structures-v1.schema.json')


def build():
    variants = [content_schema(select_blueprint(rooms, difficulty, seed=seed))
                for seed in range(4) for rooms in (1, 2, 3)
                for difficulty in ('easy', 'normal', 'hard')]
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema',
            'title': 'Host structure1 catalog with AI content2 names and typed facts',
            'structure_catalog_version': CATALOG_VERSION,
            'content_contract_version': CONTENT_VERSION,
            'structure_variants': list(VARIANTS),
            '$defs': variants[0]['$defs'], 'oneOf': variants}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Read-only exact 36-variant catalog check')
    args = parser.parse_args()
    encoded = json.dumps(build(), ensure_ascii=False, indent=2) + '\n'
    if args.check:
        if not TARGET.exists() or TARGET.read_text(encoding='utf-8') != encoded:
            raise SystemExit('Internal structure1 catalog is missing or stale')
        print('generation-structures-v1.schema.json matches all 36 variants')
    else:
        TARGET.write_text(encoded, encoding='utf-8')
        print('Wrote generation-structures-v1.schema.json (36 variants)')


if __name__ == '__main__':
    main()
