"""Background artwork for the rainy-astronomy pack (authored SVG, 1600x900)."""
from __future__ import annotations

import random

from .artlib import (blur, book_row, circle, droplets, dust, ellipse, f, floorlight, group, lamp_glow, lin, path,
                     poly, rad, rain, rect, shelf, soft_light, star_chart, svg, telescope, text, vignette,
                     window_frame, window_night, wood_panel, grain_overlay, definition_block, paper_sheet)

W, H = 1600, 900


def _defs(extra: str = "") -> str:
    return definition_block() + extra


def _slot(x, y, height, width=250) -> dict:
    return {"x": x, "y": y, "height": height,
            "hotspot": {"x": x - width / 2, "y": y - height * .96, "width": width, "height": height * .98 + 14}}


def _table(x, y, w, h, drawers=2) -> str:
    parts = [rect(x, y, w, h, "url(#gDesk)"), rect(x, y, w, 8, "#9a6d45", .55), rect(x, y + h, w, 9, "#241811", .8)]
    for i in range(drawers):
        dw = w / drawers * .86
        dx = x + w * (i + .5) / drawers - dw / 2
        parts.append(rect(dx, y + h * .16, dw, h * .62, "#4a3121", .55, rx=3))
        parts.append(rect(dx, y + h * .16, dw, 3, "#8a6040", .35, rx=2))
        parts.append(circle(dx + dw / 2, y + h * .47, 4.2, "url(#gBrass)", .9))
    # legs
    for lx in (x + 26, x + w - 34):
        parts.append(rect(lx, y + h + 8, 12, 900 - (y + h + 8), "#2b1d15"))
    return "".join(parts)


def scene_lab():
    rng = random.Random(17)
    body = []
    # ---- room shell -----------------------------------------------------
    body.append(rect(0, 0, W, 700, "url(#gWall)"))
    for i in range(18):  # uneven plaster
        body.append(ellipse(rng.uniform(0, W), rng.uniform(80, 620), rng.uniform(60, 210), rng.uniform(30, 90),
                            "#000000", rng.uniform(.02, .06)))
    # ceiling with a beam and lamp cords
    body.append(rect(0, 0, W, 92, "#191310"))
    body.append(rect(0, 66, W, 34, "#241a13"))
    body.append(rect(0, 66, W, 5, "#0f0a08"))
    body.append(rect(0, 92, W, 9, "#0c0806"))
    for i in range(6):
        body.append(rect(120 + i * 270, 60, 26, 40, "#2f2218", .8))
    # wainscot
    body.append(rect(0, 470, W, 190, "#241b14"))
    for i in range(9):
        bx = 40 + i * 176
        body.append(rect(bx, 486, 152, 150, "#2c2118", .85, rx=3))
        body.append(rect(bx, 486, 152, 3, "#4c3928", .5))
    body.append(rect(0, 462, W, 12, "#3a2a1d"))
    body.append(rect(0, 646, W, 16, "#171009"))
    # floor
    body.append(rect(0, 660, W, 240, "#2a1d15"))
    body.append(wood_panel(0, 662, W, 238, "#4a3123", "#221610", "#5d4030", planks=7, horizontal=False, opacity=.95))
    body.append(f'<rect x="0" y="660" width="{W}" height="240" fill="url(#gFloor)" opacity=".55"/>')

    # ---- window ---------------------------------------------------------
    wx, wy, ww, wh = 74, 104, 352, 344
    body.append(rect(wx - 24, wy - 24, ww + 48, wh + 48, "#1a1310"))
    body.append(window_night(wx, wy, ww, wh, seed=41, moon=(.55, .19)))
    # rooftop observatory dome outside: astronomy identity through the glass
    cx, cy, cr = wx + ww * .70, wy + wh * .58, 58
    body.append(poly([(cx - cr, cy), (cx - cr * .55, cy - cr * .72), (cx, cy - cr * .95),
                      (cx + cr * .55, cy - cr * .72), (cx + cr, cy)], "#060d13", .97))
    body.append(rect(cx - cr, cy, cr * 2, wh * .42, "#050b10", .97))
    body.append(rect(cx - 8, cy - 8, 16, 9, "#f3d99a", .7))
    body.append(rain(ww, wh, count=110, seed=13, top=0, bottom=wh, alpha=.30, scale=.85))
    body.append(droplets(ww, wh, count=64, seed=8, alpha=.26))
    body.append(f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" fill="#0b1c26" opacity=".18"/>')
    body.append(poly([(wx + 18, wy + 236), (wx + 150, wy + 26), (wx + 196, wy + 26), (wx + 52, wy + 286)],
                     "#f6d9a4", .06))
    body.append(window_frame(wx, wy, ww, wh, bars=(2, 3), thickness=14, frame="#33241a"))
    body.append(rect(wx - 36, wy + wh + 14, ww + 72, 24, "#5a3f2c"))
    body.append(rect(wx - 36, wy + wh + 14, ww + 72, 5, "#8a6444", .5))
    body.append(rect(wx - 36, wy + wh + 38, ww + 72, 9, "#1a120d", .6))
    # moonlight spill: cool light on the wall and floor near the window
    body.append(poly([(wx + 60, wy + wh - 10), (wx + ww - 30, wy + wh - 10), (470, 900), (250, 900)],
                     "url(#gMoonSpill)", .34, extra='filter="url(#fSoft)"'))
    body.append(ellipse(330, 828, 250, 60, "#9fc4d2", .06))

    # ---- right shelf wall ----------------------------------------------
    sx, sy = 1012, 96
    body.append(rect(sx - 12, sy - 14, 552, 372, "#2b2018"))
    body.append(rect(sx, sy, 528, 352, "#1d1510"))
    for row in range(3):
        ry = sy + 112 + row * 116
        body.append(rect(sx, ry, 528, 12, "#463326"))
        body.append(rect(sx, ry - 116, 528, 104, "#241a13", .5))
    body.append("".join(rect(sx + 22 + i * 13, sy + 34, 11, 72, c, .9) for i, c in enumerate(
        ["#7d5036", "#42594f", "#6a6547", "#7a463a", "#4d566a", "#5f4a35", "#7d5036", "#42594f"])))
    body.append(rect(sx + 150, sy + 22, 96, 84, "#5d4630", .95, rx=3))
    body.append(rect(sx + 158, sy + 34, 80, 10, "#d9c9a3", .45))
    body.append(rect(sx + 158, sy + 52, 60, 7, "#d9c9a3", .3))
    for i, c in enumerate(["#6f4a33", "#3f544b", "#71583a"]):
        body.append(rect(sx + 300 + i * 22, sy + 18, 18, 90, c, .92, rx=4))
    body.append("".join(rect(sx + 26 + i * 15, sy + 150, 13, 66, c, .88) for i, c in enumerate(
        ["#5b4a35", "#7a5038", "#3d4f4a", "#6d5c3e", "#54493a", "#7a5038", "#3d4f4a"])))
    body.append(rect(sx + 190, sy + 138, 120, 78, "#63492f", .95, rx=3))
    body.append(circle(sx + 250, sy + 168, 16, "url(#gBrass)", .9))
    body.append(circle(sx + 250, sy + 168, 6, "#6b4a26", .9))
    body.append(rect(sx + 330, sy + 132, 130, 84, "#4d3826", .95, rx=3))
    body.append(star_chart(sx + 340, sy + 140, 110, 70, -2, 5))
    for i in range(4):
        body.append(rect(sx + 30 + i * 26, sy + 250, 20, 96, "#b9a780", .9, rx=9))
        body.append(rect(sx + 30 + i * 26, sy + 250, 20, 12, "#8e7d5c", .8, rx=6))
    body.append(circle(sx + 236, sy + 296, 46, "url(#gBrass)", .85))
    body.append(circle(sx + 236, sy + 296, 40, "#5d5140", .55))
    body.append(rect(sx + 340, sy + 262, 150, 84, "#3f2f22", .95, rx=2))
    body.append(paper_sheet(sx + 350, sy + 272, 64, 64, -5))
    body.append(paper_sheet(sx + 420, sy + 274, 60, 60, 4, "#d5c6a2"))

    # ---- wall decor: charts, pinboard, clock, lamp ----------------------
    body.append(poly([(548, 292), (552, 96), (806, 88), (812, 296)], "#3a2b1f", .9))
    body.append(star_chart(566, 106, 226, 176, -1.4, 33))
    body.append(rect(556, 116, 14, 14, "#a8865a", .8))
    body.append(rect(788, 108, 14, 14, "#a8865a", .8))
    body.append(paper_sheet(828, 150, 112, 138, 2.4, "#cbbd99"))
    body.append(rect(842, 166, 84, 3, "#6d5c3d", .4))
    body.append(rect(842, 182, 66, 3, "#6d5c3d", .32))
    # club plaque
    body.append(rect(596, 322, 196, 62, "#3a2a1c", .9, rx=4))
    body.append(rect(602, 328, 184, 50, "url(#gBrass)", .55, rx=3))
    body.append(text(694, 362, "天文社 · 活动室", 26, "#332415", .78, family="Georgia, 'Songti SC', serif"))
    body.append(circle(612, 340, 3, "#5b4426", .8))
    body.append(circle(776, 340, 3, "#5b4426", .8))
    # pinned photos and a folded campus notice
    body.append(rect(842, 330, 132, 104, "#4a3423", .85, rx=2))
    body.append(rect(848, 336, 120, 92, "#cabb95", .55, rx=1))
    body.append(rect(858, 346, 48, 40, "#7d7a5e", .55))
    body.append(rect(914, 346, 44, 40, "#8c8061", .5))
    body.append(rect(858, 392, 100, 3, "#6d5c3d", .5))
    body.append(circle(908, 340, 3, "#c9a05a", .9))
    body.append(rect(1002, 380, 96, 70, "#d8c9a4", .35, rx=2))
    body.append(rect(1012, 392, 76, 3, "#5d4c31", .4))
    body.append(rect(1012, 404, 60, 3, "#5d4c31", .3))
    # brass wall clock
    body.append(circle(944, 232, 46, "#3a2a1d"))
    body.append(circle(944, 232, 40, "url(#gBrass)", .92))
    body.append(circle(944, 232, 33, "#e8dcc0", .92))
    for i in range(12):
        ang = i * 30 * 3.14159 / 180
        body.append(circle(944 + 26 * __import__("math").sin(ang), 232 - 26 * __import__("math").cos(ang), 1.9, "#5b4a33", .8))
    body.append(path("M944 232 L944 210", stroke="#3c2f22", width=3))
    body.append(path("M944 232 L962 240", stroke="#3c2f22", width=2.4))
    # pendant lamp
    body.append(rect(757, 92, 4, 56, "#141010"))
    body.append(poly([(730, 148), (786, 148), (812, 196), (704, 196)], "#2e3a35"))
    body.append(poly([(704, 196), (812, 196), (806, 206), (710, 206)], "#c9a262", .8))
    body.append(circle(758, 210, 11, "#ffe9b8", .95))
    body.append(lamp_glow(758, 214, 330, core=.5))

    # ---- work table -----------------------------------------------------
    body.append(_table(140, 482, 1360, 64, drawers=3))
    body.append(rect(140, 482, 1360, 6, "#a2754c", .5))
    body.append(rect(140, 482, 1360, 40, "#000000", .10))
    # non-interactive clutter between placement slots
    body.append(circle(486, 470, 15, "#c9c2ab", .95))
    body.append(rect(476, 470, 20, 16, "#b3ab93", .95))
    body.append(path("M496 476 q12 0 10 10", stroke="#b3ab93", width=5))
    body.append(paper_sheet(846, 448, 84, 34, -3))
    body.append(paper_sheet(856, 442, 74, 30, 4, "#ddcfae"))
    body.append(rect(1176, 452, 18, 34, "#b9a480", .95, rx=8))
    body.append(rect(1176, 452, 18, 8, "#8d7a58", .9, rx=4))

    # ---- floor life -----------------------------------------------------
    body.append(poly([(210, 690), (1470, 690), (1560, 900), (120, 900)], "#33241a", .45))
    # worn rug under the table
    body.append(path("M300 724 L1330 700 L1400 880 L210 892 Z", "#59372e", .55))
    body.append(path("M330 742 L1300 720 L1360 862 L240 872 Z", "#6b4535", .30))
    body.append(path("M330 742 L1300 720", stroke="#c4a377", width=2, extra='stroke-opacity=".18"'))
    body.append(path("M240 872 L1360 862", stroke="#c4a377", width=2, extra='stroke-opacity=".12"'))
    # table shadow grounding
    body.append(rect(150, 640, 1340, 26, "#120c08", .45, extra='filter="url(#fSoft2)"'))
    body.append(floorlight(640, 790, 520, 120, opacity=.26))
    body.append(floorlight(300, 700, 220, 90, opacity=.20))
    for fx, fy in [(470, 700), (508, 726), (546, 752), (584, 778)]:
        body.append(ellipse(fx, fy, 13, 7, "#0d1a20", .5, extra=f'transform="rotate(-18 {fx} {fy})"'))
    body.append(ellipse(300, 800, 74, 12, "#0c171c", .4))
    # stool
    body.append(ellipse(1430, 792, 62, 16, "#20140f", .7))
    body.append(rect(1402, 700, 12, 92, "#3d2b1e"))
    body.append(rect(1450, 700, 12, 92, "#3d2b1e"))
    body.append(ellipse(1432, 702, 54, 13, "#6a4a31"))
    body.append(ellipse(1432, 698, 54, 12, "#7d5839"))
    # archive box on the floor left
    body.append(rect(78, 720, 132, 96, "#5a4230", .95, rx=3))
    body.append(rect(78, 720, 132, 10, "#7d5c3e", .9))
    body.append(rect(96, 748, 96, 6, "#c8b38c", .45))
    body.append(rect(96, 764, 70, 5, "#c8b38c", .3))

    # ---- atmosphere -----------------------------------------------------
    body.append(soft_light(760, 300, 260, "#f8d089", .18))
    body.append(soft_light(250, 250, 210, "#8fb7c9", .12))
    body.append(dust(W, H, count=110, seed=4, alpha=.55))
    body.append(vignette(W, H, .66))
    body.append(grain_overlay(W, H, .20))
    return svg(W, H, "".join(body), _defs()), W, H


def scene_archive():
    rng = random.Random(29)
    body = []
    body.append(rect(0, 0, W, 720, "url(#gWall)"))
    body.append(rect(0, 0, W, 58, "#141010"))
    for i in range(16):
        body.append(ellipse(rng.uniform(0, W), rng.uniform(70, 640), rng.uniform(70, 200), rng.uniform(30, 90),
                            "#000000", rng.uniform(.02, .06)))
    body.append(rect(0, 660, W, 240, "#231810"))
    body.append(wood_panel(0, 660, W, 240, "#45301f", "#1f1510", "#573c2b", planks=8, horizontal=False, opacity=.95))
    body.append(f'<rect x="0" y="660" width="{W}" height="240" fill="url(#gFloor)" opacity=".5"/>')

    # tall archive shelving left
    for unit in range(2):
        ux = 40 + unit * 300
        body.append(rect(ux, 84, 280, 560, "#2a1e16"))
        body.append(rect(ux, 84, 280, 8, "#4a3626", .7))
        body.append(rect(ux + 10, 94, 260, 540, "#170f0b"))
        for row in range(5):
            ry = 100 + row * 110
            body.append(rect(ux + 10, ry + 96, 260, 10, "#42301f"))
            body.append(rect(ux + 10, ry + 96, 260, 3, "#6d5236", .45))
            if row % 2 == 0:
                for b in range(3):
                    bx = ux + 22 + b * 82
                    bw = 66 - (b % 2) * 6
                    bh = 82 - (b % 3) * 6
                    body.append(rect(bx, ry + 96 - bh, bw, bh, ["#6a4f36", "#75543a", "#5c452f"][b % 3], .94, rx=3))
                    body.append(rect(bx + 6, ry + 96 - bh + 14, bw - 12, 24, "#d9c8a4", .34, rx=1))
                    body.append(rect(bx + 10, ry + 96 - bh + 20, bw - 24, 3, "#6d5c3f", .45))
                    body.append(rect(bx + 10, ry + 96 - bh + 28, bw - 32, 2.6, "#6d5c3f", .3))
            else:
                body.append(book_row(ux + 20, ry + 14, 240, 82, seed=row * 7 + unit, palette=("#6b4a35", "#4a5a4c", "#7d5c3c", "#5c4a3a", "#6a6046")))
                body.append(paper_sheet(ux + 176, ry + 40, 62, 52, -3, "#d8c8a6"))
        body.append(rect(ux, 84, 280, 560, "#000000", .10))
    # central aisle lamp
    body.append(rect(700, 56, 4, 120, "#120e0c"))
    body.append(poly([(672, 174), (732, 174), (760, 222), (644, 222)], "#2f3a34"))
    body.append(circle(702, 236, 12, "#ffe8b4", .9))
    body.append(lamp_glow(702, 240, 300, core=.42))

    # high rain slit window on the right wall
    wx, wy, ww, wh = 1188, 92, 268, 176
    body.append(rect(wx - 16, wy - 16, ww + 32, wh + 32, "#1a1310"))
    body.append(window_night(wx, wy, ww, wh, seed=57, moon=(.22, .28)))
    body.append(f'<g transform="translate({wx} {wy})">' + rain(ww, wh, count=70, seed=3, top=0, bottom=wh, alpha=.26, scale=.7) + '</g>')
    body.append(window_frame(wx, wy, ww, wh, bars=(1, 2), thickness=10, frame="#33241a"))
    body.append(rect(wx - 24, wy + wh + 10, ww + 48, 16, "#563c2a"))

    # filing wall: index cards, map drawers, ledger stack
    body.append(rect(1112, 366, 200, 150, "#3d2b1f"))
    for i in range(3):
        body.append(rect(1120, 374 + i * 46, 184, 38, "#553d2a", .95, rx=2))
        body.append(rect(1160, 390 + i * 46, 104, 6, "#c5ac83", .5))
    body.append(rect(1336, 358, 220, 158, "#33241a"))
    body.append(paper_sheet(1352, 372, 92, 128, -2))
    body.append(paper_sheet(1444, 380, 88, 122, 3, "#ccbc98"))

    # pinned finding board above the sorting table
    body.append(rect(742, 250, 340, 190, "#3a2a1d", .85, rx=3))
    body.append(rect(752, 260, 320, 170, "#4a3a28", .5, rx=2))
    for i, (px, py, pw, ph, rot) in enumerate([(768, 276, 86, 64, -3), (872, 282, 74, 58, 2), (960, 274, 92, 70, -1), (816, 356, 104, 52, 1)]):
        body.append(paper_sheet(px, py, pw, ph, rot, "#d8c9a6"))
        body.append(circle(px + pw / 2, py + 5, 3, "#c9a05a", .8))
    # long sorting table across the back
    body.append(_table(180, 500, 1240, 62, drawers=3))
    body.append(rect(180, 500, 1240, 6, "#9c7049", .45))
    # table clutter
    body.append(rect(430, 470, 120, 32, "#6d5138", .9, rx=2))
    body.append(paper_sheet(444, 458, 92, 20, -2, "#ddd0ae"))
    body.append(circle(940, 486, 13, "#b9b09a", .9))
    body.append(rect(1130, 468, 130, 34, "#5d4630", .92, rx=2))
    body.append(rect(1146, 478, 98, 5, "#cbb894", .4))
    body.append(rect(1146, 490, 74, 4, "#cbb894", .3))

    # floor: archive boxes and a cart
    body.append(floorlight(700, 800, 540, 120, opacity=.24))
    body.append(rect(96, 716, 150, 104, "#58402c", .96, rx=3))
    body.append(rect(96, 716, 150, 12, "#7c5b3d", .92))
    body.append(rect(96, 792, 150, 10, "#3a281b", .8))
    body.append(rect(250, 740, 118, 82, "#4e3927", .95, rx=3))
    body.append(rect(250, 740, 118, 10, "#6f5136", .9))
    body.append(ellipse(1420, 800, 70, 14, "#1e140f", .6))
    body.append(rect(1372, 706, 96, 96, "#43301f", .95, rx=4))
    body.append(rect(1372, 736, 96, 6, "#6a4c33", .8))
    body.append(rect(1372, 770, 96, 6, "#6a4c33", .8))

    body.append(soft_light(700, 280, 240, "#f7cf88", .16))
    body.append(dust(W, H, count=120, seed=12, alpha=.55))
    body.append(vignette(W, H, .7))
    body.append(grain_overlay(W, H, .20))
    return svg(W, H, "".join(body), _defs()), W, H


def scene_control():
    rng = random.Random(43)
    body = []
    # ---- shell ----------------------------------------------------------
    body.append(rect(0, 0, W, 720, "url(#gGreen)"))
    for i in range(16):
        body.append(ellipse(rng.uniform(0, W), rng.uniform(60, 660), rng.uniform(80, 220), rng.uniform(40, 100),
                            "#000000", rng.uniform(.03, .07)))
    body.append(rect(0, 0, W, 40, "#0a1116"))
    # ---- roof slit with rain and moon ----------------------------------
    sx, sy, sw, sh = 250, 48, 1080, 150
    body.append(rect(sx - 26, sy - 16, sw + 52, sh + 34, "#101a20"))
    body.append(rect(sx, sy, sw, sh, "#08131a"))
    body.append(f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="url(#gSky)" opacity=".95"/>')
    body.append(f'<g transform="translate({sx} {sy})">' + rain(sw, sh, count=150, seed=23, top=0, bottom=sh, alpha=.34, scale=.95) + '</g>')
    body.append(circle(sx + sw * .20, sy + sh * .34, 26, "#eee9cf", .6))
    body.append(circle(sx + sw * .20, sy + sh * .34, 12, "#f6f2da", .85))
    for i in range(7):
        body.append(rect(sx + 16 + i * 152, sy + 4, 7, sh - 8, "#1d2b33", .95))
    body.append(rect(sx, sy + sh - 7, sw, 10, "#1a2830"))
    body.append(rect(sx - 30, sy + sh + 16, sw + 60, 14, "#26343a"))
    body.append(rect(sx - 30, sy + sh + 16, sw + 60, 4, "#4a5c5e", .5))
    # ---- wall decor: observation charts --------------------------------
    body.append(rect(1050, 306, 300, 190, "#1d2a2d", .9, rx=3))
    body.append(rect(1058, 314, 284, 174, "#243336", .6, rx=2))
    for i, (px, py, pw, ph, rot) in enumerate([(1072, 328, 116, 86, -2), (1204, 334, 120, 92, 2)]):
        body.append(paper_sheet(px, py, pw, ph, rot, "#d9d0b0"))
        body.append(circle(px + pw / 2, py + 6, 3, "#c9a05a", .8))
    body.append(star_chart(1084, 344, 92, 62, -2, 9))
    body.append(rect(1130, 424, 140, 4, "#7d8b7a", .18))
    body.append(rect(1130, 436, 96, 4, "#7d8b7a", .12))
    for i in range(6):
        body.append(rect(120 + i * 250, 214, 3, 430, "#0c161b", .5))
    body.append(rect(0, 470, W, 6, "#0c161b", .45))
    body.append(rect(0, 214, W, 5, "#22323a", .5))
    # wall gauges
    for i, gx in enumerate((930, 976)):
        body.append(circle(gx, 386, 26, "#1b262a", 1))
        body.append(circle(gx, 386, 21, "#c9c2a6", .55))
        body.append(path(f"M{gx} 386 L{gx + 12} 372", stroke="#3c2f22", width=2.4))
    body.append(rect(900, 424, 110, 6, "#7d8b7a", .2))
    # instrument rack left
    body.append(rect(58, 300, 202, 300, "#243033"))
    body.append(rect(70, 314, 178, 272, "#141d20"))
    for i in range(3):
        body.append(rect(86, 336 + i * 82, 146, 60, "#2a383a", .95, rx=3))
        body.append(rect(98, 352 + i * 82, 60, 6, "#8fa39b", .22))
        body.append(circle(204, 366 + i * 82, 8, "#c9a768", .35))
    body.append(path("M58 596 q-28 30 -32 64", stroke="#2c3a3a", width=7, extra='fill="none"'))
    # ---- small refractor on a tripod, right corner ----------------------
    body.append(ellipse(1408, 812, 84, 16, "#0a1418", .6))
    body.append(telescope(1408, 800, .82, -46))
    # ---- control console right ------------------------------------------
    body.append(rect(1188, 452, 372, 208, "#2c3a3d"))
    body.append(rect(1188, 452, 372, 12, "#465a5c", .9))
    body.append(rect(1204, 476, 340, 92, "#1a2529"))
    for i in range(3):
        body.append(rect(1216, 486 + i * 26, 156, 12, "#8f9d8a", .24, rx=2))
        body.append(rect(1392, 486 + i * 26, 58, 12, "#c9a768", .3, rx=6))
    for i in range(4):
        body.append(circle(1236 + i * 58, 600, 14, "#3c4a44", .95))
        body.append(circle(1236 + i * 58, 600, 9, "url(#gBrass)", .7))
    body.append(rect(1188, 660, 372, 14, "#101a1d"))
    # ---- equipment bench left-front (objects stand here) ----------------
    body.append(rect(60, 470, 560, 44, "#3a4a4a"))
    body.append(rect(60, 470, 560, 8, "#5b6f6c", .55))
    body.append(rect(60, 514, 560, 132, "#263336"))
    body.append(rect(70, 528, 250, 6, "#8fa39b", .20))
    body.append(rect(70, 546, 170, 5, "#8fa39b", .14))
    body.append(rect(60, 646, 560, 12, "#101a1d"))
    # cable coils and crates
    body.append(path("M980 742 a44 44 0 1 0 88 0 a44 44 0 1 0 -88 0", stroke="#2f3c3b", width=7, extra='fill="none"'))
    body.append(path("M1000 742 a24 24 0 1 0 48 0 a24 24 0 1 0 -48 0", stroke="#3a4a48", width=6, extra='fill="none"'))
    body.append(rect(1512, 700, 74, 104, "#222b2d", .95, rx=5))
    body.append(circle(1549, 728, 12, "#7f938c", .4))
    body.append(rect(1330, 748, 84, 56, "#2b3335", .9, rx=3))
    body.append(rect(1330, 748, 84, 8, "#46524f", .7, rx=3))
    # ---- atmosphere ------------------------------------------------------
    body.append(lamp_glow(1240, 300, 320, core=.16))
    body.append(lamp_glow(430, 560, 240, core=.10))
    body.append(dust(W, H, count=100, seed=15, alpha=.45))
    body.append(vignette(W, H, .70))
    body.append(grain_overlay(W, H, .20))
    return svg(W, H, "".join(body)), W, H


SLOTS = {
    "neutral_lab": [
        _slot(310, 512, 186, 230), _slot(668, 512, 186, 226), _slot(1022, 512, 186, 226), _slot(1372, 512, 186, 226),
        _slot(304, 856, 236, 250), _slot(672, 856, 236, 250), _slot(1036, 856, 236, 250), _slot(1382, 856, 236, 250),
    ],
    "neutral_archive": [
        _slot(340, 528, 190, 230), _slot(700, 528, 190, 226), _slot(1046, 528, 190, 226), _slot(1382, 528, 190, 226),
        _slot(324, 856, 232, 246), _slot(700, 856, 232, 246), _slot(1064, 856, 232, 246), _slot(1400, 856, 232, 246),
    ],
    "neutral_control": [
        _slot(310, 512, 188, 230), _slot(576, 512, 188, 224), _slot(1178, 520, 190, 226), _slot(1438, 520, 190, 226),
        _slot(304, 856, 236, 246), _slot(608, 856, 236, 246), _slot(930, 856, 236, 246), _slot(1248, 856, 236, 246),
    ],
}

SCENES = {
    "neutral_lab": scene_lab,
    "neutral_archive": scene_archive,
    "neutral_control": scene_control,
}
