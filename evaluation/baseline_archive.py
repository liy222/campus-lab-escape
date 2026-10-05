"""One Main-approved legacy source archive, not a target-selectable alias registry."""
from __future__ import annotations

from .common import EvaluationError, exact_keys, sha256, strict_json
from .reader import safe_read

POINTER_PATH = 'trusted/baseline-source-archive-v1.json'
MAIN_ARCHIVE_PATH = 'evidence/integration/E1-source-archive-20261005.json'
MAIN_ARCHIVE_RAW_SHA256 = '0dab9b9e213a3631a7630eb59cd0a27d8e44c74321891463ed7d71d599d285a6'
PRODUCT_COMMIT = '7821af4efe0613c20a80ea164c1dab1c0f288bab'
BASELINE_MANIFEST_RAW_SHA256 = '9c36943cbb6e4fe08b6e176445ba91835fafa79a2077c2155bbf8d613f8b07c1'
POINTER = {'schema_id': 'baseline-source-archive-v1', 'release_id': 'baseline_v1',
           'product_commit': PRODUCT_COMMIT,
           'main_archive': {'path': MAIN_ARCHIVE_PATH, 'raw_sha256': MAIN_ARCHIVE_RAW_SHA256}}


def validate_archive_record(record, manifest):
    exact_keys(record, ['created_at', 'approved_by', 'archive_release_id', 'product_commit', 'experiment_commit',
                        'count', 'sources', 'formal_plan_raw_sha256', 'baseline_manifest_raw_sha256', 'scope'])
    if record['approved_by'] != 'Main' or record['archive_release_id'] != 'baseline_v1' or record['product_commit'] != PRODUCT_COMMIT or manifest.get('commit') != PRODUCT_COMMIT or manifest.get('release_id') != 'baseline_v1':
        raise EvaluationError('BASELINE_ARCHIVE_VERSION_MISMATCH')
    if record['baseline_manifest_raw_sha256'] != BASELINE_MANIFEST_RAW_SHA256:
        raise EvaluationError('BASELINE_ARCHIVE_MANIFEST_PIN_MISMATCH')
    if not isinstance(record['sources'], dict) or type(record['count']) is not int or record['count'] != 101 or len(record['sources']) != record['count']:
        raise EvaluationError('BASELINE_ARCHIVE_COLLECTION_INVALID')
    for item in record['sources'].values():
        exact_keys(item, ['archive_release_id', 'archive_path', 'raw_sha256', 'git_source_commit', 'git_blob_oid',
                          'git_blob_sha256', 'utf8_lf_v1_sha256', 'binding'])
    baseline = {path: item for path, item in record['sources'].items() if item['git_source_commit'] == PRODUCT_COMMIT}
    if len(baseline) != 60 or len(manifest['sources']) != 60 or set(baseline) != set(manifest['sources']):
        raise EvaluationError('BASELINE_ARCHIVE_SOURCE_SET_MISMATCH')
    other = [item for item in record['sources'].values() if item['git_source_commit'] != PRODUCT_COMMIT]
    if len(other) != 41 or any(item['git_source_commit'] != record['experiment_commit'] for item in other):
        raise EvaluationError('BASELINE_ARCHIVE_EXPERIMENT_SET_INVALID')
    locations = {}
    for path, original in manifest['sources'].items():
        item = baseline[path]
        if item['archive_release_id'] != 'baseline_v1' or item['archive_path'] != 'release/archives/baseline_v1/' + path:
            raise EvaluationError('BASELINE_ARCHIVE_PATH_NOT_FIXED')
        expected = {'raw_sha256': original['candidate_runtime_raw_sha256'], 'git_blob_oid': original['git_blob_oid'],
                    'git_blob_sha256': original['git_blob_sha256'], 'utf8_lf_v1_sha256': original['utf8_lf_v1_sha256'],
                    'binding': original['binding']}
        if any(item[key] != value for key, value in expected.items()):
            raise EvaluationError('BASELINE_ARCHIVE_GIT_OR_RAW_IDENTITY_MISMATCH')
        locations[path] = item
    return locations


def load_baseline_archive(project_root, evaluator_root, manifest):
    pointer = strict_json(safe_read(evaluator_root, POINTER_PATH))
    if pointer != POINTER:
        raise EvaluationError('BASELINE_ARCHIVE_POINTER_NOT_APPROVED')
    data = safe_read(project_root, MAIN_ARCHIVE_PATH)
    if sha256(data) != MAIN_ARCHIVE_RAW_SHA256:
        raise EvaluationError('BASELINE_ARCHIVE_MAIN_RAW_HASH_MISMATCH')
    record = strict_json(data)
    locations = validate_archive_record(record, manifest)
    return {'locations': locations, 'main_archive_path': MAIN_ARCHIVE_PATH,
            'main_archive_raw_sha256': MAIN_ARCHIVE_RAW_SHA256, 'registered_source_count': 101,
            'baseline_source_count': 60, 'experiment_sources_excluded': 41,
            'source_check_location': 'Main-fixed v1 archive; current working sources not certified',
            'archive_executed': False}


def read_baseline_source(project_root, original_path, original, archive):
    item = archive['locations'].get(original_path)
    if item is None:
        raise EvaluationError('BASELINE_ARCHIVE_SOURCE_NOT_REGISTERED')
    data = safe_read(project_root, item['archive_path'])
    # Git CRLF provenance may be approved, but archive runtime raw is exact.
    if sha256(data) != item['raw_sha256'] or item['raw_sha256'] != original['candidate_runtime_raw_sha256']:
        raise EvaluationError('BASELINE_ARCHIVE_RUNTIME_RAW_MISMATCH')
    return data
