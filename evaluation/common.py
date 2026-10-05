from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

EVALUATOR_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = EVALUATOR_ROOT.parent
MAX_FILE = 10 * 1024 * 1024
MAX_SNIPPET = 16384
STATES = ('PASS', 'FAIL', 'INSUFFICIENT_EVIDENCE', 'NOT_APPLICABLE')


class EvaluationError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(data: bytes) -> bytes:
    # Exact Main-approved algorithm, never selected by target configuration.
    return data.decode('utf-8', errors='strict').replace('\r\n', '\n').encode('utf-8')


def strict_json(data: str | bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise EvaluationError('DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    try:
        value = json.loads(data, object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(EvaluationError('NONFINITE_JSON')))
        def depth(item, n=0):
            if n > 40:
                raise EvaluationError('JSON_TOO_DEEP')
            if isinstance(item, dict):
                for child in item.values(): depth(child, n + 1)
            elif isinstance(item, list):
                for child in item: depth(child, n + 1)
        depth(value)
        return value
    except (UnicodeError, ValueError, TypeError, RecursionError):
        raise EvaluationError('INVALID_JSON') from None


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def exact_keys(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise EvaluationError('INVALID_STRUCTURE')


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_:.-]{1,128}', value):
        raise EvaluationError('INVALID_ID')
    return value


def clean_text(value, maximum=4000):
    if not isinstance(value, str) or not 1 <= len(value) <= maximum or any(ord(c) < 32 and c not in '\n\t' for c in value):
        raise EvaluationError('INVALID_TEXT')
    return value
