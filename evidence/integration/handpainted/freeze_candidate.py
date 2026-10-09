"""Main integration snapshot after both implementation Owners declare SOURCE STOP."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    plan = json.loads((HERE / 'plan.json').read_text(encoding='utf-8'))
    assert (HERE / 'frontend/report.json').is_file(), 'Owner final report required'
    errors = [p for p, h in plan['immutable_file_sha256'].items() if digest(p) != h]
    assert not errors, errors
    assert digest('docs/visual-plan.md') == plan['visual_plan_sha256']
    assert all(digest(p) == h for p, h in plan['art_input_report_sha256'].items())
    assert digest('frontend/src/assets/painted-metadata.json') == plan['asset_metadata_sha256']
    assert digest(plan['asset_SOURCE_STOP_report']) == plan['asset_report_sha256']
    names = subprocess.check_output(['rg', '--files', 'frontend/src', 'frontend/public/art-handpainted'], cwd=ROOT).decode('utf-8').splitlines()
    paths = set(plan['source154_sha256']) | {p.replace('\\', '/') for p in names}
    source = {p: digest(p) for p in sorted(paths)}
    result = {'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'operator': 'Main', 'baseline_head': plan['baseline_head'],
              'source_sha256': source, 'source_count': len(source),
              'source_scope': 'Product/spec files including original SVGs and new installed PNGs/metadata/helpers; no runtime or independent QA scripts',
              'changed_previous_sources': [p for p, h in plan['source154_sha256'].items() if source[p] != h],
              'immutable_files_checked': len(plan['immutable_file_sha256']),
              'owner_report_sha256': {r: digest('evidence/integration/handpainted/' + r + '/report.json') for r in ('frontend', 'assets')},
              'policy': 'Product SOURCE STOP; independent QA may finalize only new adapter/protocol before formal execution. Any proven product finding requires a new freeze and narrow affected retest.'}
    path = HERE / 'candidate.json'
    assert not path.exists(), 'Never overwrite an earlier frozen candidate'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'source_count': len(source), 'immutable_files': len(plan['immutable_file_sha256']),
                      'changed_previous_sources': result['changed_previous_sources'], 'candidate_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
