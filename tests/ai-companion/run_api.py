"""Frozen-candidate focused API runner; no paid calls, all epochs retained."""
from pathlib import Path
import hashlib
import io
import json
import sys
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    candidate_path = sys.argv[1]
    candidate = json.loads((ROOT / candidate_path).read_text(encoding='utf-8-sig'))
    source = candidate['source_sha256']
    digest = lambda p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
    before = {p: digest(p) for p in source}
    assert before == source
    prep = json.loads((ROOT / 'evidence/integration/ai-companion/qa/preparation.json').read_text(encoding='utf-8'))
    assert prep['protocol_ready']
    assert all(digest(p) == h for p, h in prep['old_test_sha256'].items())
    folder = ROOT / 'evidence/integration/ai-companion/qa' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-api')
    folder.mkdir(parents=True)
    from tests.api import test_ai_companion as new
    from tests.api import test_hint_flow as preset
    from tests.api import test_play_ai_settings as legacy
    from tests.api import test_r1 as capture
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(new)])
    for name in prep['old_preset_methods']: suite.addTest(preset.HintFlowHTTP(name))
    for name in prep['old_legacy_methods']: suite.addTest(legacy.PlayAiSettings(name))
    output = io.StringIO()
    from fake_runtime import create_test_runtime
    with patch('backend.app.ai.runtime.create_request_runtime', create_test_runtime):
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    after = {p: digest(p) for p in source}
    old_match = all(digest(p) == h for p, h in prep['old_test_sha256'].items())
    code = 0 if result.wasSuccessful() and before == after and old_match else 1
    def safe(value):
        if isinstance(value, dict): return {k: safe(v) for k, v in value.items()}
        if isinstance(value, list): return [safe(v) for v in value]
        if isinstance(value, str):
            for secret in capture.SECRETS | {new.KEY, legacy.KEY_A, legacy.KEY_B}: value = value.replace(secret, '[REDACTED]')
        return value
    (folder/'unittest.txt').write_text(safe(output.getvalue()), encoding='utf-8')
    (folder/'checks.json').write_text(json.dumps(safe(new.RECORDS), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (folder/'http.json').write_text(json.dumps(safe([x for x in capture.EXCHANGES if x['path'].endswith('/ai/turns')]), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    payload = {'candidate': candidate_path, 'command': [sys.executable, '-B', '-X', 'utf8', *sys.argv], 'exit_code': code, 'methods': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'source_sha256_before': before, 'source_sha256_after': after, 'old_tests_unchanged': old_match, 'old_preset_methods': prep['old_preset_methods'], 'old_legacy_methods': prep['old_legacy_methods'], 'paid_calls': 0, 'canonical_budget_access': False, 'limitations': ['Synthetic request-runtime constructor and complete replacement validate real HTTP mode/context/finalizer branches, not production provider construction/budget or real-model semantic quality.', 'Owned temporary DB fixtures only; no historical user DB.', 'Focused old-method selection, no full127 suite or mobile.']}
    (folder/'run.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(safe(output.getvalue()))
    print(json.dumps({'evidence': str(folder), 'exit_code': code, 'methods': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors)}))
    return code


if __name__ == '__main__':
    sys.exit(main())
