"""No-import/no-provider QA preparation: AST, historical-output review, hashes."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'evidence/integration/ai-companion-quality/qa'


def read(p):
    return json.loads((ROOT / p).read_text(encoding='utf-8-sig'))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    preserved = {}
    for base in ('tests', 'evidence/integration/ai-companion', 'evidence/integration/ai-companion-real'):
        for path in sorted((ROOT / base).rglob('*')):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix == '.pyc':
                continue
            relative = path.relative_to(ROOT).as_posix()
            if relative.startswith('tests/ai-companion-quality/'):
                continue
            preserved[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    preserved['review/findings/ai-companion-real.md'] = hashlib.sha256((ROOT / 'review/findings/ai-companion-real.md').read_bytes()).hexdigest()
    prior = read('evidence/integration/ai-companion/qa/preparation.json')
    parsed = []
    for path in sorted((ROOT / 'tests/ai-companion-quality').glob('*.py')):
        ast.parse(path.read_text(encoding='utf-8-sig'))
        parsed.append(path.relative_to(ROOT).as_posix())
    provider_paths = [f'evidence/integration/ai-companion-real/20261018T110144068872Z-real/C{n:02}-provider.json' for n in range(1, 8)]
    provider_paths.append('evidence/integration/ai-companion-real/targeted/20261018T111212456755Z-real/C08-provider.json')
    reviews = []
    comments = {
        'C01': 'Historical fact failure: only experiment record claimed directly observable despite seven public objects. Not retested by the lone C08.',
        'C02': 'Historical followup repeats false exclusivity; actual prior history supplied, but no exact duplicate. Needs actual followup quality sample.',
        'C03': 'Historical local time/record relation supported by discovered evidence; no new model test in this preparation.',
        'C04': 'Historical invented cabinet clue rejected; guard success does not make delivered response useful.',
        'C05': 'Historical circuit explanation relevant but maintenance reference unrelated; no new real retest yet.',
        'C06': 'Historical logged-in next-step relevant but maintenance reference unrelated; no new real retest yet.',
        'C07': 'Historical partial transcription relation supported; no full order disclosed in this sample.',
        'C08': 'Historical narrow improvement in catalog/ref policy; CODE_ACCEPTED and implementation vocabulary still leaked. Naturalness weak.'}
    for path in provider_paths:
        obj = read(path)
        content = json.loads(obj['raw_content'])
        reviews.append({'case_id': obj['case_id'], 'provider_evidence': path, 'raw_answer': content['answer'],
                        'raw_refs': content['clue_refs'], 'offline_assessment': comments[obj['case_id']],
                        'current_candidate_retest': False})
    (OUT / 'historical-eight-review.json').write_text(json.dumps({'operator': 'Independent QA offline reading of existing sanitized provider evidence',
        'paid_calls': 0, 'canonical_budget_access': False, 'case_count': len(reviews), 'cases': reviews,
        'limitation': 'Historical outputs span two old source epochs; this is not new model quality evidence or a new global pass.'}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    payload = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'formal_execution': False, 'formal_tests': 0,
               'command': [sys.executable, '-B', '-X', 'utf8', *sys.argv], 'exit_code': 0, 'parsed_python': parsed,
               'gate': 'Wait for Main SOURCE STOP and frozen candidate GO before run_regression.py',
               'preserved_sha256': preserved, 'old_preset_methods': prior['old_preset_methods'], 'old_legacy_methods': prior['old_legacy_methods'],
               'scope': ['Runtime and Store internal-code rejection/no count or revision delta',
                         'Explicit clarification exact-prior-answer rejection on both boundaries; ordinary questions compatibility',
                         'Natural public-state and discovered USER/PASS format wording allowed',
                         'Current question/history/Chinese wire payload plus original catalog/ref guard regression',
                         'Whole-guess local no-call policy and restore-generation history isolation',
                         'Old companion methods plus chosen freepreset/legacy methods unchanged'],
               'builds': 0, 'UI_runs': 0, 'paid_calls': 0, 'canonical_budget_access': False,
               'real_followup_preview_owner': 'Main prepares at most four questions: cabinet, same-session clarification, circuit, logged-in; QA does not create or execute paid runner.',
               'limitations': ['AST syntax check only; runner not executed before candidate freeze.',
                               'Prompt/context assertions and fake provider regression cannot certify actual relevance/naturalness/followup quality.']}
    (OUT / 'preparation.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'exit_code': 0, 'formal_tests': 0, 'python_AST': len(parsed), 'preserved_files': len(preserved), 'historical_outputs_read': len(reviews)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
