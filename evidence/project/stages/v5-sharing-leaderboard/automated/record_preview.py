"""Main's local preview receipt: no login, database opening, or model call."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[5]
BASE = 'http://127.0.0.1:8001'
with urlopen(BASE + '/health', timeout=3) as response:
    health = json.loads(response.read())
with urlopen(BASE + '/', timeout=3) as response:
    html = response.read()
try:
    with urlopen(BASE + '/api/v2/shared-levels', timeout=3) as response:
        status = response.status
except HTTPError as error:
    status = error.code
assert health['service'] == 'campus-lab-escape-v5'
assert status == 401
assert html == (ROOT / 'frontend/dist-v5/index.html').read_bytes()
backups = [
    {'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size,
     'modified_at_utc': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()}
    for path in sorted((ROOT / 'data/backups').glob('game-v5-sharing-v1-*.sqlite'))
]
assert backups, 'Expected the existing V5 database upgrade backup'
receipt = {
    'operator': 'Main', 'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
    'command': r'C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 -m scripts.run_v5',
    'exec_session_id': 12379, 'server_pid': 4712, 'ready': True, 'url': BASE + '/',
    'health': health, 'served_html_matches_build': True,
    'html_sha256': hashlib.sha256(html).hexdigest(),
    'anonymous_shared_list_http_status': status,
    'consistent_backup_files_present': backups,
    'player_database_used_as_test_fixture': False, 'user_login_or_gameplay_by_main': False,
    'real_model_calls': 0,
    'scope': 'Authorized app startup/additive migration, then local health/static/anonymous HTTP checks only.',
    'startup_note': 'Initial background shell wrapper was rejected before execution; the existing launcher was then run directly.'
}
(Path(__file__).parent / 'preview-startup.json').write_text(
    json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'preview_ready': True, 'served_build_matches': True,
                  'anonymous_shared_list_status': status, 'backup_files_present': len(backups)}))
