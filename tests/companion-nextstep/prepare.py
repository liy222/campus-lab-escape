"""No-import preparation only; formal execution waits for Main's frozen GO."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'evidence/integration/companion-nextstep/qa'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    preserved = {}
    for base in ('tests', 'evidence/integration/ai-companion-quality',
                 'evidence/integration/ai-companion-real', 'evidence/integration/ai-companion'):
        for path in sorted((ROOT / base).rglob('*')):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix == '.pyc':
                continue
            rel = path.relative_to(ROOT).as_posix()
            if rel.startswith('tests/companion-nextstep/'):
                continue
            preserved[rel] = digest(path)
    parsed = []
    for path in sorted((ROOT / 'tests/companion-nextstep').glob('*.py')):
        ast.parse(path.read_text(encoding='utf-8-sig'))
        parsed.append(path.relative_to(ROOT).as_posix())
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        'recorded_at': datetime.now(timezone.utc).isoformat(),
        'command': [sys.executable, '-B', '-X', 'utf8', *sys.argv],
        'exit_code': 0, 'formal_execution': False, 'formal_tests': 0,
        'source_gate': 'Await Main SOURCE STOP and frozen candidate authorization',
        'parsed_python': parsed, 'preserved_sha256': preserved,
        'paid_calls': 0, 'external_network': False, 'canonical_database_access': False,
        'scope': [
            'Ordinary next-step wording across public route stages, especially before glass-slide placement and early R2',
            'One currently legal public step without private puzzle answers or action execution',
            'Runtime and independent Store rejection preserve full visible state including revision and hint count',
            'Companion failure wording describes a reply, not a suggestion awaiting execution',
            'Preserve explicit explanation/relation queries, strict JSON, refs, no-tools and whole-answer boundaries'],
        'limitations': [
            'Preparation is AST/hash capture only, not executed implementation validation.',
            'Synthetic provider and request-shape checks cannot prove actual model answer quality.',
            'User raw output not available to QA; no exact reproduction of the reported real request is claimed.']}
    (OUT / 'preparation.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'exit_code': 0, 'formal_tests': 0, 'python_AST': len(parsed),
                      'preserved_files': len(preserved)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
