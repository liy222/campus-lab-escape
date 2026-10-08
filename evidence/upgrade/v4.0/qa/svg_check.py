"""Independent public SVG clock angles and four-wheel lock geometry check."""
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[4]
namespace = {'svg': 'http://www.w3.org/2000/svg'}
records = []
number = r'(-?\d+(?:\.\d+)?)'
pattern = re.compile(r'M'+number+r'\s+'+number+r'\s+'+number+r'\s+'+number+r'M'+number+r'\s+'+number+r'\s+'+number+r'\s+'+number)
for name in ['r1_clock.svg', 'closeup_clock.svg']:
    document = ET.parse(root / 'frontend/src/assets' / name)
    segments = [pattern.fullmatch(element.get('d', '')) for element in document.findall('.//svg:path', namespace)]
    matches = [match for match in segments if match]
    assert len(matches) == 1, name
    values = list(map(float, matches[0].groups()))
    hands = []
    for x,y,end_x,end_y in [values[:4], values[4:]]:
        hands.append({'clockwise_degrees_from_12': math.degrees(math.atan2(end_x-x, -(end_y-y))) % 360, 'length': math.hypot(end_x-x,end_y-y)})
    hour, minute = sorted(hands,key=lambda hand:hand['length'])
    assert abs(hour['clockwise_degrees_from_12'] - (9*30+17/60*30)) < 1, name
    assert abs(minute['clockwise_degrees_from_12'] - 17*6) < 1.5, name
    records.append({'asset':name,'hour_degrees':round(hour['clockwise_degrees_from_12'],3),'minute_degrees':round(minute['clockwise_degrees_from_12'],3)})
lock = ET.parse(root / 'frontend/src/assets/closeup_cabinet_locked.svg')
wheels = lock.findall('.//svg:circle',namespace)
assert len(wheels) == 4
assert len({element.get('cx') for element in wheels}) == 4
print(json.dumps({'clock_geometry':records,'lock_wheels':len(wheels),'passed':True}))
