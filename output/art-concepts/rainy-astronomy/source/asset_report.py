"""Write ASSET-LIST.md from the built manifest, with real file sizes."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PACK = ROOT / "output/art-concepts/rainy-astronomy"
PUBLIC = ROOT / "frontend/public/art-themes/rainy-astronomy"
MANIFEST = ROOT / "frontend/src/assets/themes/rainy-astronomy/manifest.json"

ROLE_CN = {"note": "资料纸面", "key": "钥匙", "terminal": "资料终端", "cabinet": "资料柜", "circuit": "配电设备", "panel": "顺序面板"}
NOTE_CN = {"logbook": "观测记录册", "star-chart": "星图资料页", "sealed-note": "封存便笺"}


def kb(path: Path) -> str:
    return f"{path.stat().st_size / 1024:.0f} KB"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    lines = [
        "# 素材清单 · rainy-astronomy",
        "",
        f"主题包 `{manifest['theme_id']}` / `{manifest['pack_version']}`，显示名「{manifest['display_name']}」。",
        "本文件由 `source/asset_report.py` 按实际构建结果生成：尺寸、bbox、文件大小都来自磁盘上的 PNG。",
        "",
        "## 已接入背景（3）",
        "",
        "| 背景ID | 用途 | 文件 | 尺寸 | 大小 |",
        "|---|---|---|---|---|",
    ]
    usage = {"neutral_lab": "天文社旧活动室（1/2/3房第一间）", "neutral_archive": "封存观测资料空间", "neutral_control": "观测设备空间"}
    for key, entry in manifest["backgrounds"].items():
        path = ROOT / "frontend/public" / entry["src"].lstrip("/")
        lines.append(f"| `{key}` | {usage.get(key, '')} | `{entry['src']}` | {entry['width']}×{entry['height']} | {kb(path)} |")
    lines += ["", "## 已接入物件与特写", "", "| 角色 | 变体 | 状态 | 场景图 | 特写 | bbox | 场景/特写大小 |", "|---|---|---|---|---|---|---|"]
    total = 0
    for role, variants in manifest["objects"].items():
        for variant_id, variant in variants.items():
            scene = ROOT / "frontend/public" / variant["src"].lstrip("/")
            close = ROOT / "frontend/public" / variant["closeup"].lstrip("/")
            total += scene.stat().st_size + close.stat().st_size
            box = variant["bbox"]
            label = NOTE_CN.get(variant.get("note_style") or "", variant["state"] == "completed" and "完成态" or "默认")
            lines.append(f"| {ROLE_CN.get(role, role)} | `{variant_id}` | {'完成' if variant['state'] == 'completed' else '默认'} | `{variant['src']}` | `{variant['closeup']}` | {box['width']}×{box['height']} | {kb(scene)} / {kb(close)} |")
    lines += ["", f"物件与特写合计约 {total / 1024 / 1024:.1f} MiB。", ""]
    lines += [
        "## 覆盖与未覆盖",
        "",
        "- 三个原背景角色 `neutral_lab / neutral_archive / neutral_control` 都有专属画面；服务端背景ID不变。",
        "- 六个物件角色 note / key / terminal / cabinet / circuit / panel 全部有专属外观；资料纸面另有观测记录册、星图资料页、封存便笺三种外观，按公开物件名称选择。",
        "- terminal / cabinet / circuit / panel 各有默认与「已完成」两种状态图；状态来自服务端公开 `completed`，前端不推导中间步骤。",
        "- 每个外观都有独立特写文件（`/art-themes/rainy-astronomy/closeups/`），场景、物品与特写使用同一张矢量源绘制。",
        "- 未覆盖：其他主题（图书馆、化学实验室等）没有专属美术，按设计回退到原有通用手绘素材；包内也没有新的可交互望远镜、星象仪等玩法物件。",
        "- 图中不含真实密码、线路方向、设备顺序或线索数值；这些仍由服务端数据在界面中绘制。",
        "",
        "## 资源来源",
        "",
        "全部图像由本目录 `source/` 下的 SVG 源文件经本机 headless Chrome 渲染得到，未使用图像生成模型或外部付费服务。",
        "渲染命令见 `source/build.py`；提示词文档见 `prompts/`（记录的是本阶段实际使用的矢量绘制说明，不是模型提示词）。",
    ]
    (PACK / "ASSET-LIST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("ASSET-LIST.md written")


if __name__ == "__main__":
    main()
