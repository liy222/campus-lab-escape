"""Read a captured canvas PNG; reject a black or uniform rendered surface."""
import json
from pathlib import Path
import sys
from PIL import Image

path = Path(sys.argv[1])
with Image.open(path) as image:
    width, height = image.size
    sample = image.convert('RGB').resize((160, 90))
    colors = [sample.getpixel((x, y)) for y in range(90) for x in range(160)]
nonblack = sum(max(color) > 24 for color in colors) / len(colors)
distinct = len(set(colors))
span = max(max(color) for color in colors) - min(min(color) for color in colors)
passed = width > 0 and height > 0 and nonblack > 0.15 and distinct > 20 and span > 45
print(json.dumps({'width': width, 'height': height, 'sample_pixels': len(colors), 'nonblack_fraction': round(nonblack, 5), 'distinct_colors': distinct, 'channel_span': span, 'passed': passed}))
raise SystemExit(0 if passed else 1)
