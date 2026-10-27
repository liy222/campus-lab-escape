"""One necessary v5 build with current-source and complete dist provenance."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[5]
QA = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve(); output.relative_to(QA)
    candidate_path = args.candidate.resolve()
    candidate = json.loads(candidate_path.read_text(encoding='utf-8'))
    expected = candidate['source_sha256']
    assert expected and all(sha(ROOT / p) == value for p, value in expected.items())
    assert expected.get(Path(__file__).relative_to(ROOT).as_posix()) == sha(Path(__file__))
    output.mkdir(parents=True, exist_ok=False)
    command = [os.environ.get('ComSpec', 'C:\\Windows\\System32\\cmd.exe'), '/d', '/c',
               'C:\\Program Files\\nodejs\\npm.cmd', '--prefix', 'frontend', 'run', 'build']
    env = os.environ.copy(); env.update(VITE_GAMEPLAY_VERSION='v5', AI_PROVIDER='mock')
    report = {'kind': 'SD3 necessary v5 build only', 'actor': 'Independent AI QA agent',
        'candidate_sha256': sha(candidate_path), 'source_count': len(expected),
        'source_bundle_sha256': candidate['source_bundle_sha256'], 'source_before_match': True,
        'actual_command': command, 'started_utc': datetime.now(timezone.utc).isoformat(),
        'VITE_GAMEPLAY_VERSION': 'v5', 'paid_calls': 0, 'exit_code': 1}
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=120)
        (output / 'output.txt').write_bytes(result.stdout)
        report['exit_code'] = result.returncode
        if result.returncode == 0:
            dist = ROOT / 'frontend/dist-v5'
            report['dist_sha256'] = {p.relative_to(ROOT).as_posix(): sha(p)
                                    for p in sorted(dist.rglob('*')) if p.is_file()}
            assert report['dist_sha256'] and 'frontend/dist-v5/index.html' in report['dist_sha256']
    except subprocess.TimeoutExpired as error:
        (output / 'output.txt').write_bytes(error.stdout or b'')
        report['exit_code'] = 124
    except BaseException as error:
        report.update(exit_code=1, error_class=type(error).__name__)
    finally:
        report['source_after_match'] = all(sha(ROOT / p) == value for p, value in expected.items())
        if not report['source_after_match']: report['exit_code'] = 1
        report['ended_utc'] = datetime.now(timezone.utc).isoformat()
        (output / 'run.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'exit_code': report['exit_code'], 'source_after_match': report['source_after_match'],
                      'dist_files_hashed': len(report.get('dist_sha256', {}))}))
    return report['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
