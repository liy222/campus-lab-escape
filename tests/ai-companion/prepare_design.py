"""Read-only design review snapshot. No product imports or test execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
out = ROOT / 'evidence/integration/ai-companion/qa'
out.mkdir(parents=True, exist_ok=True)
paths = ['backend/app/ai/runtime.py', 'backend/app/ai/context.py', 'backend/app/ai/provider.py', 'backend/app/ai/types.py', 'backend/app/ai/hints.py', 'backend/app/storage/ai.py', 'backend/app/api/routes.py', 'frontend/src/Assistant.tsx']
tests = [p.replace('\\', '/') for p in subprocess.check_output(['rg', '--files', 'tests'], cwd=ROOT, text=True, encoding='utf-8').splitlines() if not p.replace('\\', '/').startswith('tests/ai-companion/') and p.replace('\\', '/') != 'tests/api/test_ai_companion.py']
digest = lambda p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
payload = {
    'recorded_at': datetime.now(timezone.utc).isoformat(),
    'head': subprocess.check_output(['git', '-c', 'safe.directory=D:/深度能力', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'status': 'Design review only; formal waits Main SOURCE STOP candidate GO.',
    'source_sha256_at_review_snapshot': {p: digest(p) for p in paths},
    'old_test_sha256': {p: digest(p) for p in sorted(tests)},
    'report': 'review/findings/ai-companion.md',
    'report_sha256': digest('review/findings/ai-companion.md'),
    'command': ['C:/Users/liyh/.conda/envs/1/python.exe', '-B', '-X', 'utf8', 'tests/ai-companion/prepare_design.py'],
    'exit_code': 0,
    'formal_tests': 0, 'builds': 0, 'browser_runs': 0, 'paid_calls': 0, 'product_changes': 0,
    'limitations': ['Snapshot can precede concurrent Owner implementation; this is not a frozen formal candidate.', 'Read-only source review does not certify runtime behavior, semantic safety or real-model quality.'],
}
(out / 'design-review.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': 'design-only', 'head': payload['head'], 'source_files': len(paths), 'old_test_files': len(tests), 'formal_tests': 0, 'exit_code': 0}))
