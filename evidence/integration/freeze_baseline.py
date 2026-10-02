"""Main-owned release identity: preserve runtime hashes and bind Git blobs explicitly."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
GIT = ['git', '-c', 'safe.directory=D:/深度能力']


def git(*args: str) -> bytes:
    return subprocess.check_output(GIT + list(args), cwd=ROOT)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(data: bytes) -> bytes:
    # Approved by Main, never inferred from target claims. Preserve BOM and EOF.
    return data.decode('utf-8', errors='strict').replace('\r\n', '\n').encode('utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--release', required=True)
    parser.add_argument('--evidence', action='append', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    commit = git('rev-parse', args.commit + '^{commit}').decode().strip()
    tree = git('rev-parse', commit + '^{tree}').decode().strip()
    output = ROOT / args.output
    if output.exists():
        raise ValueError('immutable manifest already exists')
    records, sources, gaps = [], {}, []
    for evidence_path in args.evidence:
        path = (ROOT / evidence_path).resolve()
        path.relative_to(ROOT)
        raw = path.read_bytes()
        artifact_blob = git('show', f'{commit}:{evidence_path}')
        artifact_raw_equal = raw == artifact_blob
        if not artifact_raw_equal and canonical(raw) != canonical(artifact_blob):
            raise ValueError(f'artifact not bound to commit: {evidence_path}')
        payload = json.loads(raw) if path.suffix == '.json' else {}
        before = payload.get('source_sha256_before', payload.get('source_hashes_before', payload.get('source_hashes', {})))
        after = payload.get('source_sha256_after', payload.get('source_hashes_after', {}))
        if 'source_hashes' in payload and payload.get('source_unchanged') is True:
            after = payload['source_hashes']
        if before and before != after:
            raise ValueError(f'evidence source changed: {evidence_path}')
        records.append({'evidence_id': f'{args.release}:E{len(records)+1:03d}',
                        'path': evidence_path, 'release_id': args.release,
                        'artifact_raw_sha256': digest(raw),
                        'artifact_git_blob_sha256': digest(artifact_blob),
                        'artifact_git_blob_oid': git('rev-parse', f'{commit}:{evidence_path}').decode().strip(),
                        'artifact_utf8_lf_v1_sha256': digest(canonical(raw)),
                        'artifact_binding': 'raw_equal' if artifact_raw_equal else 'approved_crlf_to_lf_only',
                        'exit_code': payload.get('exit_code'),
                        'recorded_head': payload.get('head'),
                        'scope': payload.get('target', payload.get('provider'))})
        for name, recorded in before.items():
            name = name.replace('\\', '/')
            current = (ROOT / name).read_bytes()
            if digest(current) != recorded:
                if name.startswith(('backend/', 'frontend/src/', 'contracts/', 'scripts/')):
                    raise ValueError(f'product source changed after evidence: {name}')
                # A test harness can change between API and browser runs; do not
                # silently widen the earlier result to the replacement harness.
                gaps.append({'evidence': evidence_path, 'path': name,
                             'recorded_raw_sha256': recorded,
                             'current_raw_sha256': digest(current),
                             'binding': 'not_same_runtime_bytes'})
                continue
            blob = git('show', f'{commit}:{name}')
            raw_equal = current == blob
            canonical_equal = canonical(current) == canonical(blob)
            if not canonical_equal:
                raise ValueError(f'candidate not bound to commit: {name}')
            sources[name] = {'candidate_runtime_raw_sha256': recorded,
                             'git_blob_sha256': digest(blob),
                             'git_blob_oid': git('rev-parse', f'{commit}:{name}').decode().strip(),
                             'utf8_lf_v1_sha256': digest(canonical(current)),
                             'binding': 'raw_equal' if raw_equal else 'approved_crlf_to_lf_only',
                             'evidence': sorted(set(sources.get(name, {}).get('evidence', []) + [evidence_path]))}
    manifest = {'release_id': args.release, 'commit': commit, 'tree': tree,
                'approved_by': 'Main engineering acceptance under user project authorization',
                'approved_at': datetime.now(timezone.utc).isoformat(),
                'teacher_approval': None, 'human_signoff': None,
                'versions': {'contract': '1.0.0', 'schema': '1.0.0', 'level': '1.0.0',
                             'tool_schema': '1.0.0', 'game_prompt': 'baseline-v1-source-bound',
                             'requested_model': 'deepseek-flash', 'base_url': 'https://api.deepseek.com'},
                'hash_policy': {'raw': 'SHA256 of exact read_bytes; never rewritten',
                                'canonical': 'utf8-lf-v1: strict UTF8, CRLF to LF only; preserve BOM, EOF and all other bytes',
                                'conversion_approval': 'Main; canonical identity does not assert raw byte identity'},
                'sources': sources, 'evidence': records, 'unbound_prior_source_records': gaps,
                'limitations': ['Scope follows each original run; recorded old HEAD alone does not establish tested commit.',
                                'Changed harness records remain historical and cannot certify their replacement.',
                                'This manifest is a version binding, not an evaluator grade or human signature.']}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'manifest': args.output, 'commit': commit,
                      'bound_sources': len(sources), 'historical_unbound_records': len(gaps)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
