"""Finite metadata for local generation diagnosis; never stores supplied text."""
from __future__ import annotations
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE_FILES = (
    'backend/app/api/v5.py', 'backend/app/ai/v5.py',
    'backend/app/ai/provider.py', 'backend/app/ai/budget.py',
    'backend/app/storage/v5.py', 'backend/app/domain/generation_content_v2.py',
    'backend/app/domain/generation_observability.py', 'backend/app/domain/generated.py',
    'backend/app/domain/blueprints.py', 'backend/app/domain/structure_variants.py',
    'backend/app/domain/puzzle_purpose.py',
    'frontend/src/assets/generated-catalog.json',
)
STAGES = frozenset({'pending', 'generating', 'validating', 'ready', 'failed', 'rejected', 'unknown'})
NAME_REASONS = frozenset({'name_suffix', 'name_access', 'name_container'})
REASONS = frozenset({'requested', 'started', 'generated', 'completed', 'parse', 'schema',
    'narrative', 'assembly', 'credential', 'admission', 'proof', 'provider',
    'provider_unavailable', 'provider_unknown', 'response_envelope', 'timeout',
    'cancelled', 'process_restart', 'internal', 'unspecified'}) | NAME_REASONS
COUNT_FIELDS = frozenset({'theme_characters', 'theme_utf8_bytes', 'requested_rooms', 'difficulty_rank',
    'messages_utf8_bytes', 'model_response_characters', 'model_response_utf8_bytes',
    'draft_response_characters', 'draft_response_utf8_bytes', 'rooms', 'objects',
    'clues', 'puzzles', 'witness_steps'})


def safe_counts(value):
    if not isinstance(value, dict): return {}
    return {key: count for key, count in value.items()
            if key in COUNT_FIELDS and type(count) is int and 0 <= count <= 1_000_000_000}


def safe_reason(value):
    return value if isinstance(value, str) and value in REASONS else 'unspecified'


def text_counts(prefix, value):
    if not isinstance(value, str): return {}
    result = {prefix + '_characters': len(value)}
    try: result[prefix + '_utf8_bytes'] = len(value.encode('utf-8'))
    except UnicodeEncodeError: pass
    return safe_counts(result)


def draft_counts(value):
    if not isinstance(value, dict): return {}
    result = {key: len(value[key]) for key in ('rooms', 'clues', 'puzzles')
              if isinstance(value.get(key), list)}
    if isinstance(value.get('rooms'), list):
        result['objects'] = sum(len(room['objects']) for room in value['rooms']
                                if isinstance(room, dict) and isinstance(room.get('objects'), list))
    return safe_counts(result)


def source_snapshot():
    # Hash only this explicit source/catalog list, never directories or data.
    fingerprints = {}
    for name in SOURCE_FILES:
        try: fingerprints[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        except OSError: fingerprints[name] = None
    revision = None
    try:
        git = ROOT / '.git'
        if git.is_file():
            line = git.read_text(encoding='utf-8').strip()
            if line.startswith('gitdir: '): git = (ROOT / line[8:]).resolve()
        head = (git / 'HEAD').read_text(encoding='ascii').strip()
        if re.fullmatch(r'[a-f0-9]{40,64}', head): revision = head
        elif re.fullmatch(r'ref: refs/[A-Za-z0-9_./-]+', head) and '..' not in head:
            target = head[5:]
            try: revision = (git / target).read_text(encoding='ascii').strip()
            except OSError:
                for line in (git / 'packed-refs').read_text(encoding='ascii').splitlines():
                    parts = line.split(' ')
                    if len(parts) == 2 and parts[1] == target: revision = parts[0]
        if not isinstance(revision, str) or not re.fullmatch(r'[a-f0-9]{40,64}', revision): revision = None
    except (OSError, UnicodeError): pass
    return {'source_version': 'generation-observability-v1', 'git_revision': revision,
            'file_fingerprints': fingerprints}
