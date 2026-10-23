"""Read staged blobs; emit locations/counts only, never captured values."""
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[4]


def git(*args, input=None):
    return subprocess.run(['git', *args], cwd=ROOT, input=input,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout


def staged_names():
    return [item.decode('utf-8') for item in git('diff', '--cached', '--name-only', '-z', '--').split(b'\0') if item]


def main():
    names = staged_names()
    entries = {}
    for item in git('ls-files', '--stage', '-z', '--').split(b'\0'):
        if not item:
            continue
        fields, path = item.split(b'\t', 1)
        mode, oid, stage = fields.split()
        name = path.decode('utf-8')
        if name in names:
            assert stage == b'0'
            entries[name] = oid.decode()
    # Read each captured immutable blob, rather than racing later index edits.
    raw = git('cat-file', '--batch', input=''.join(oid + '\n' for oid in entries.values()).encode())
    stream = io.BytesIO(raw)
    blobs = {}
    for name, oid in entries.items():
        header = stream.readline().split()
        assert header[:2] == [oid.encode(), b'blob']
        blobs[name] = stream.read(int(header[2]))
        assert stream.read(1) == b'\n'

    # Fixed source literals are labelled, never silently counted as generated
    # credentials. This set exists in memory only and is never printed/saved.
    fixed = set()
    for name, content in blobs.items():
        if name.startswith('tests/v5/') and name.endswith('.py'):
            try:
                tree = ast.parse(content.decode('utf-8-sig'))
            except (UnicodeError, SyntaxError):
                continue
            fixed.update(node.value for node in ast.walk(tree)
                if isinstance(node, ast.Constant) and isinstance(node.value, str))

    patterns = {
        'cookie_repr': re.compile(r'<Cookie\s+([A-Za-z0-9_.-]+)=([^\s>]+)'),
        'cookie_assignment': re.compile(r'\b(campus_v5_[A-Za-z0-9_]+)[\"\']?\s*[:=]\s*[\"\']?([A-Za-z0-9_.~-]{16,})'),
        'quoted_secret_field': re.compile(r'''["'](csrf_token|auth_context|session_token|access_token|refresh_token|nonce|api_key|password)["']\s*:\s*["']([A-Za-z0-9_.~-]{16,})["']''', re.I),
        'secret_variable_literal': re.compile(r'''\b(csrf|nonce|csrf_token|auth_context|session_token|api_key|password)\s*=\s*["']([A-Za-z0-9_.~-]{16,})["']''', re.I),
        'bearer_literal': re.compile(r'\b(Bearer)\s+([A-Za-z0-9_.~-]{20,})', re.I),
        'set_cookie_header': re.compile(r'''\b(Set-Cookie)\s*:\s*[A-Za-z0-9_.-]+=([A-Za-z0-9_.~-]{16,})''', re.I),
    }
    hits = []
    scanned = []
    skipped = []
    for name, content in blobs.items():
        if b'\x00' in content:
            skipped.append(name)
            continue
        try:
            text = content.decode('utf-8-sig')
        except UnicodeError:
            skipped.append(name)
            continue
        scanned.append(name)
        for kind, pattern in patterns.items():
            for match in pattern.finditer(text):
                value = match.group(2)
                fixed_literal = value in fixed or any(value in literal for literal in fixed if len(literal) < 512)
                placeholder = bool(re.search(r'REDACTED|PLACEHOLDER|ACTUAL_|SYNTHETIC|QA[-_]', value, re.I))
                hits.append({'path': name, 'line': text.count('\n', 0, match.start()) + 1,
                    'pattern': kind, 'label': match.group(1), 'characters': len(value),
                    'classification': 'fixed_test_literal' if fixed_literal else 'explicit_placeholder' if placeholder else 'requires_review_opaque_value'})
    after_names = staged_names()
    opaque = [hit for hit in hits if hit['classification'] == 'requires_review_opaque_value']
    report = {'kind': 'independent_read_only_staged_V5_text_privacy_pattern_review',
        'utc': datetime.now(timezone.utc).isoformat(),
        'actual_command': 'python evidence/upgrade/v5.0/qa/scan_round2_staged_privacy.py',
        'exit_code': 0, 'staged_paths_at_start': len(names), 'text_blobs_scanned': len(scanned),
        'non_utf8_or_binary_skipped': skipped, 'staged_name_inventory_unchanged_during_scan': names == after_names,
        'captured_staged_blob_ids': entries, 'pattern_counts': dict(Counter(hit['pattern'] for hit in hits)),
        'classification_counts': dict(Counter(hit['classification'] for hit in hits)),
        'hits_without_values': hits, 'opaque_hits_requiring_review': len(opaque),
        'reported_original_raw_is_staged': 'evidence/upgrade/v5.0/qa/authmaterial/20261023T063608354079Z-3c340e58/output.txt' in entries,
        'secrets_output': False, 'originals_modified': False, 'git_index_modified_by_QA': False,
        'tests_run': 0, 'provider_calls': 0, 'network_calls': 0,
        'limits': ['Finite pattern review of immutable captured staged UTF-8 text blobs only; not a universal secret audit.',
            'Public IDs and SHA256 hashes are not treated as credentials merely because they look random.',
            'Known fixed test literals and explicit redactions are labelled separately; unknown opaque credential-shaped values require review.',
            'No sealed original evidence or product/Git data was modified.']}
    out = Path(__file__).with_name('round2-privacy-staged-review.json')
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'exit_code': 0, 'staged_paths': len(names), 'text_blobs': len(scanned),
        'pattern_counts': report['pattern_counts'], 'classifications': report['classification_counts'],
        'opaque_hits_without_values': opaque, 'original_raw_is_staged': report['reported_original_raw_is_staged'],
        'inventory_unchanged': names == after_names, 'output': str(out.relative_to(ROOT)),
        'output_sha256': hashlib.sha256(out.read_bytes()).hexdigest()}, ensure_ascii=True))


if __name__ == '__main__':
    main()
