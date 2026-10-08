"""Check the new QA black-frame detector with owned synthetic PNG fixtures."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from PIL import Image

folder = Path(__file__).resolve().parent
root = folder.parents[3]
checks = []
with tempfile.TemporaryDirectory(prefix='campus-qa-pixel-') as temporary:
    for name, expected in [('black', 1), ('uniform-dark', 1), ('varied-visible', 0)]:
        image = Image.new('RGB', (160, 90), (0, 0, 0) if name == 'black' else (27, 36, 43))
        if name == 'varied-visible':
            for y in range(90):
                for x in range(160):
                    image.putpixel((x, y), (x, y + 40, (x + y) % 256))
        path = Path(temporary) / (name + '.png')
        image.save(path)
        command = [sys.executable, '-B', '-X', 'utf8', str(folder / 'pixel_check.py'), str(path)]
        process = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding='utf-8')
        checks.append({'fixture': name, 'fixture_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'command': command, 'exit_code': process.returncode, 'expected_exit_code': expected, 'stdout': process.stdout.strip(), 'stderr': process.stderr.strip()})
        assert process.returncode == expected, name
record = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'scope': 'Synthetic QA detector fixtures only; no product/browser run or screenshot', 'command': [sys.executable, '-B', '-X', 'utf8', str(Path(__file__))], 'exit_code': 0, 'checks': checks, 'pixel_check_sha256': hashlib.sha256((folder / 'pixel_check.py').read_bytes()).hexdigest(), 'formal_visual_runs': 0}
(folder / 'pixel-fixtures.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'exit_code': 0, 'checks': len(checks), 'expected_detector_exits': [check['exit_code'] for check in checks], 'formal_visual_runs': 0}))
