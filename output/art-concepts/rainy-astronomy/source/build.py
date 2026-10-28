"""Render the rainy-astronomy theme pack with local tools only.

Pipeline: Python authors SVG -> headless Chrome screenshots it -> Pillow records
real pixel sizes / alpha bounding boxes -> manifest.json is written from actual
output. No image generation model or paid service is used.
"""
from __future__ import annotations

import datetime
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

from . import objects as objmod
from . import scenes as scenemod
from .artlib import svg as svgdoc

ROOT = Path(__file__).resolve().parents[4]
PACK = ROOT / "output/art-concepts/rainy-astronomy"
PUBLIC = ROOT / "frontend/public/art-themes/rainy-astronomy"
ASSETS = ROOT / "frontend/src/assets/themes/rainy-astronomy"
CHROME = next((c for c in (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
) if Path(c).exists()), None)


def render(svg: str, width: int, height: int, target: Path, transparent: bool) -> dict:
    if not CHROME:
        raise RuntimeError("No local Chrome/Edge available for SVG rasterisation")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="theme-svg-") as tmp:
        html = Path(tmp) / "page.html"
        bg = "transparent" if transparent else "#0d1b26"
        html.write_text(
            "<!doctype html><meta charset='utf-8'><style>html,body{margin:0;padding:0;background:%s;}"
            "svg{display:block}</style>%s" % (bg, svg),
            encoding="utf-8",
        )
        out = Path(tmp) / "shot.png"
        cmd = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
               "--force-device-scale-factor=1", "--default-background-color=00000000",
               f"--window-size={width},{height}", f"--screenshot={out}", html.as_uri()]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if not out.exists():
            raise RuntimeError(f"Chrome produced no screenshot: {result.stderr[-500:]}")
        shutil.copyfile(out, target)
    image = Image.open(target).convert("RGBA")
    if image.size != (width, height):
        raise RuntimeError(f"Unexpected render size {image.size} for {target.name}")
    bbox = image.getbbox() if transparent else (0, 0, width, height)
    if bbox is None:
        raise RuntimeError(f"Empty render for {target.name}")
    return {"width": width, "height": height,
            "bbox": {"x": bbox[0], "y": bbox[1], "width": bbox[2] - bbox[0], "height": bbox[3] - bbox[1]}}


def crop_to_bbox(path: Path, bbox: dict, pad: int = 10) -> dict:
    image = Image.open(path).convert("RGBA")
    left = max(0, bbox["x"] - pad)
    top = max(0, bbox["y"] - pad)
    right = min(image.width, bbox["x"] + bbox["width"] + pad)
    bottom = min(image.height, bbox["y"] + bbox["height"] + pad)
    cropped = image.crop((left, top, right, bottom))
    cropped.save(path, optimize=True)
    return {"width": cropped.width, "height": cropped.height, "bbox": {"x": 0, "y": 0, "width": cropped.width, "height": cropped.height}}


def save_source(name: str, svg: str) -> None:
    src = PACK / "source" / "svg" / f"{name}.svg"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(svg, encoding="utf-8")


def build(only: str | None = None) -> None:
    manifest = {"schema_version": 1, "theme_id": "rainy-astronomy", "pack_version": "1.0.0",
                "display_name": "雨夜天文社", "coverage": "astronomy-club", "backgrounds": {},
                "objects": {}, "slot_layout": {}}
    if not (only and only in objmod.VARIANTS):
        for key, builder in scenemod.SCENES.items():
            if only and only != key:
                continue
            svg, width, height = builder()
            save_source(f"background-{key}", svg)
            info = render(svg, width, height, PUBLIC / "backgrounds" / f"{key}.png", transparent=False)
            manifest["backgrounds"][key] = {"src": f"/art-themes/rainy-astronomy/backgrounds/{key}.png", **info}
            manifest["slot_layout"][key] = scenemod.SLOTS[key]
    for role, variants in objmod.VARIANTS.items():
        for variant in variants:
            if only and only != variant["id"]:
                continue
            scene_w, scene_h = 640, 512
            close_w, close_h = 1200, 960
            scene_svg = svgdoc(scene_w, scene_h, "".join(variant["parts"]()), objmod.DEFS, box=(objmod.VBW, objmod.VBH))
            close_svg = svgdoc(close_w, close_h, "".join(variant["parts"]()), objmod.DEFS, box=(objmod.VBW, objmod.VBH))
            save_source(variant["id"], close_svg)
            scene_info = render(scene_svg, scene_w, scene_h, PUBLIC / "objects" / f"{variant['id']}.png", transparent=True)
            close_path = PUBLIC / "closeups" / f"{variant['id']}.png"
            close_info = render(close_svg, close_w, close_h, close_path, transparent=True)
            cropped = crop_to_bbox(close_path, close_info["bbox"])
            manifest["objects"].setdefault(role, {})[variant["id"]] = {
                "role": role, "state": variant["state"], "note_style": variant.get("note_style"),
                "src": f"/art-themes/rainy-astronomy/objects/{variant['id']}.png",
                "closeup": f"/art-themes/rainy-astronomy/closeups/{variant['id']}.png",
                "width": scene_info["width"], "height": scene_info["height"], "bbox": scene_info["bbox"],
                "closeup_width": cropped["width"], "closeup_height": cropped["height"],
                "closeup_bbox": cropped["bbox"],
            }
    meta = {"built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "renderer": "headless Chrome screenshot of authored SVG",
            "backgrounds": sorted(manifest["backgrounds"]),
            "objects": {k: sorted(v) for k, v in manifest["objects"].items()}}
    if only:
        print(json.dumps({"partial": True, "rerendered": only}, ensure_ascii=False))
        return
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (PACK / "build-report.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else None)
