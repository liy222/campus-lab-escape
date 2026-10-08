"""Record syntax-only preparation and byte preservation; no services/browser."""
import hashlib
import ast
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[4]
folder = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
baseline = json.loads((folder / 'baseline-api/run.json').read_text(encoding='utf-8'))
legacy = baseline['test_sha256_after']
legacy_after = {name: sha(root / name) for name in legacy}
assert legacy == legacy_after, 'Existing API tests changed'
prior_runner = root / 'tests/e2e/run_multiple_saves.mjs'
assert sha(prior_runner) == 'bed78881b88a46b9e26de5dd17a73adacc875b0a682eec4f35b40b53be6d58b5'
for name in ['formal-api/runner.py', 'formal_build.py', 'pixel_check.py']:
    ast.parse((folder / name).read_text(encoding='utf-8'), filename=name)
command = [r'C:\Program Files\nodejs\node.exe', '--check', 'tests/e2e/run_visual_v40.mjs']
process = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding='utf-8')
record = {
    'status': 'STATIC PREPARATION STOP; formal visual acceptance awaits frozen Main candidate GO',
    'recorded_at': datetime.now(timezone.utc).isoformat(),
    'command': command, 'cwd': str(root), 'exit_code': process.returncode,
    'stdout': process.stdout, 'stderr': process.stderr,
    'generation_command': [r'C:\Users\liyh\.conda\envs\1\python.exe', '-B', '-X', 'utf8', 'evidence/upgrade/v4.0/qa/prepare_visual_runner.py'],
    'generation_exit_code': 0,
    'files_sha256': {name: sha(root / name) for name in ['tests/e2e/run_visual_v40.mjs', 'evidence/upgrade/v4.0/qa/prepare_visual_runner.py', 'evidence/upgrade/v4.0/qa/seal_preparation.py', 'evidence/upgrade/v4.0/qa/formal-api/runner.py', 'evidence/upgrade/v4.0/qa/formal_build.py', 'evidence/upgrade/v4.0/qa/pixel_check.py']},
    'prior_api_test_count': len(legacy), 'prior_api_tests_byte_identical_to_baseline': legacy == legacy_after,
    'prior_api_tests_sha256': legacy_after,
    'prior_multiple_save_runner_sha256': sha(prior_runner),
    'old_e2e_preparation_sha256': {str(path.relative_to(root)).replace('\\', '/'): sha(path) for path in sorted((root / 'tests/e2e').glob('*.mjs')) if path.name != 'run_visual_v40.mjs'},
    'formal_visual_runs': 0, 'product_edits': 0, 'paid_calls': 0,
    'assertion_policy': 'New adapter retains full previous route/save/restore/reload/restart/minigame/hint/score/namespace assertions. Extra R1 mouse/keyboard/notebook/error/snapshot checks; four archive moments plus old slot. Renderer accepts explicitly canvas or webgl, with actual PNG pixel nonblack/nonuniform checks independent of assets-ready. Prior runner remains unchanged.',
    'limitations': ['Public selector adapter follows in-progress implementation; final freeze still required.', 'No visual acceptance or screenshot claim from syntax-only checks.', 'Controlled missing-asset behavior not yet in runner; route/lifecycle/successful load and pageerror checks are prepared.']
}
(folder / 'preparation-runner-renderer.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
preparation = json.loads((folder / 'preparation.json').read_text(encoding='utf-8'))
preparation['status'] = record['status']
preparation['baseline_runs'] = {'API': 'baseline-api/run.json: exit 0, 127 methods/337 subtests', 'build': 'baseline-build/run.json: exit 0'}
preparation['new_runner'] = {'path': 'tests/e2e/run_visual_v40.mjs', 'sha256': record['files_sha256']['tests/e2e/run_visual_v40.mjs'], 'static_evidence': 'preparation-runner-renderer.json', 'prior_static_epoch': 'preparation-runner.json'}
(folder / 'preparation.json').write_text(json.dumps(preparation, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'exit_code': process.returncode, 'old_api_files': len(legacy), 'old_api_byte_match': legacy == legacy_after, 'runner_sha256': record['files_sha256']['tests/e2e/run_visual_v40.mjs'], 'formal_visual_runs': 0}))
raise SystemExit(process.returncode)
