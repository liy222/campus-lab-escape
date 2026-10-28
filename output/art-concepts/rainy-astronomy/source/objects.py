"""Object sprites and close-ups for the rainy-astronomy pack.

Every role keeps one recognisable silhouette in scene, inventory and close-up.
Art never contains a real code, order or wiring answer: that stays server data.
"""
from __future__ import annotations

import math
import random

from .artlib import circle, ellipse, f, group, lin, path, poly, rad, rect, svg, text

VBW, VBH = 1000, 800
DEFS = "".join([
    lin("oBrass", [(0, "#f0cf92", 1), (.42, "#c9974f", 1), (.72, "#9a6c33", 1), (1, "#7a5228", 1)]),
    lin("oBrassDark", [(0, "#a97c3f", 1), (1, "#6d4a22", 1)]),
    lin("oLeather", [(0, "#3f5a4c", 1), (.5, "#2d4438", 1), (1, "#1e2f27", 1)]),
    lin("oPaper", [(0, "#f7ecd2", 1), (.6, "#ebdbb8", 1), (1, "#d6c29a", 1)]),
    lin("oWood", [(0, "#7d5738", 1), (.45, "#5f4028", 1), (1, "#3f2a1b", 1)]),
    lin("oSteel", [(0, "#8d9a96", 1), (.5, "#5d6b68", 1), (1, "#394746", 1)]),
    lin("oGlass", [(0, "#bcd8da", .35), (.5, "#7fa5aa", .16), (1, "#4c6f74", .3)]),
    rad("oScreen", [(0, "#f6d9a0", .18), (.7, "#7c8f70", .10), (1, "#0d1a1a", .55)], .5, .5, .7),
    rad("oPlate", [(0, "#284456", .95), (.55, "#1b3242", .95), (1, "#132634", .95)]),
    rad("oGlow", [(0, "#ffd98d", .85), (.45, "#eab469", .35), (1, "#b8802f", 0)]),
    rad("oShadow", [(0, "#0a1412", .38), (1, "#0a1412", 0)]),
]) + '<clipPath id="clipCabinet"><rect x="214" y="110" width="552" height="560" rx="4"/></clipPath>' 


def _doc(body: str, extra_defs: str = "") -> str:
    return svg(VBW, VBH, body, DEFS + extra_defs)


def _page(x, y, w, h, tone="#f2e5c8", rotation=0, lines=5) -> str:
    parts = [f'<g transform="rotate({f(rotation)} {f(x + w / 2)} {f(y + h / 2)})">']
    parts.append(rect(x + 6, y + 8, w, h, "#1c150f", .30, rx=3))
    parts.append(rect(x, y, w, h, tone, .97, rx=3))
    parts.append(rect(x + 8, y + 8, w - 16, h - 16, "#ffffff", .10, rx=2))
    for i in range(lines):
        ly = y + h * (0.18 + i * 0.13)
        width = w * (0.86 - (i % 3) * 0.12)
        parts.append(rect(x + w * .08, ly, width, 2.6, "#8b7a56", .34, rx=1.3))
    parts.append("</g>")
    return "".join(parts)


def note_logbook():
    body = [rect(40, 640, 920, 90, "url(#oShadow)", 1)]
    # cover
    body.append(path("M120 250 Q 130 210 190 206 L 820 206 Q 880 210 884 258 L 880 640 Q 872 682 812 686 L 196 686 Q 132 680 124 638 Z", "#21332b"))
    body.append(path("M126 252 Q 136 216 196 212 L 818 212 Q 872 216 876 260 L 872 636 Q 864 674 808 678 L 200 678 Q 140 672 132 636 Z", "url(#oLeather)"))
    body.append(path("M126 252 Q 136 216 196 212 L 818 212 Q 872 216 876 260 L 872 300 L 130 300 Z", "#ffffff", .05))
    # brass corners
    for cx, cy, sx, sy in ((140, 226, 1, 1), (860, 226, -1, 1), (140, 662, 1, -1), (860, 662, -1, -1)):
        body.append(path(f"M{cx} {cy} l{58 * sx} 0 l0 {14 * sy} l{-44 * sx} 0 l{-14 * sy} 14 Z", "url(#oBrass)", .95))
    # pages
    body.append(path("M206 300 L200 646 Q 206 664 246 666 L 780 666 Q 826 664 830 644 L 836 300 Z", "#e6d6b0"))
    body.append(path("M214 306 L208 640 Q 214 656 246 658 L 492 658 L 494 306 Z", "url(#oPaper)"))
    body.append(path("M500 306 L498 658 L 776 658 Q 820 656 826 640 L 832 306 Z", "url(#oPaper)"))
    body.append(rect(494, 306, 8, 352, "#b9a67f", .8))
    # handwritten observation rows (decorative, no answers)
    rng = random.Random(5)
    for i in range(11):
        ly = 342 + i * 28
        body.append(rect(232, ly, 190 + rng.uniform(0, 50), 2.4, "#6d5c3f", .35, rx=1.2))
        body.append(rect(516, ly, 170 + rng.uniform(0, 70), 2.4, "#6d5c3f", .3, rx=1.2))
    # constellation sketch on right page
    pts = [(560, 470), (612, 432), (668, 452), (716, 404), (770, 436), (742, 500), (676, 512)]
    for i in range(len(pts) - 1):
        body.append(path(f"M{pts[i][0]} {pts[i][1]} L {pts[i + 1][0]} {pts[i + 1][1]}", stroke="#4a5f52", width=2))
    for px, py in pts:
        body.append(circle(px, py, 4, "#3c4f45", .85))
    # ribbon
    body.append(path("M612 538 L648 542 L646 610 L610 606 Z", "#8d3f34"))
    body.append(path("M610 606 L646 610 L644 622 L608 618 Z", "#6d2f27"))
    # brass clasp
    body.append(rect(452, 640, 96, 36, "url(#oBrass)", .9, rx=6))
    body.append(rect(470, 650, 60, 16, "#3a2a18", .5, rx=4))
    return body


def note_chart():
    import random as _random
    rng = _random.Random(11)
    body = [rect(120, 700, 780, 60, "url(#oShadow)", .9)]
    body.append(path("M180 118 L 800 96 Q 828 98 826 132 L 806 664 Q 804 700 766 698 L 196 716 Q 160 716 158 678 Z", "#20180f", .3))
    body.append(path("M170 108 L 792 84 Q 820 86 818 120 L 798 652 Q 796 688 758 686 L 186 704 Q 150 704 148 666 Z", "url(#oPaper)"))
    body.append(path("M170 108 L 792 84 Q 820 86 818 120 L 798 652 Q 796 688 758 686 L 186 704 Q 150 704 148 666 Z", "#8d7a52", .16, stroke="#8d7a52", width=1))
    # engraved night plate
    body.append(path("M232 172 Q 236 156 256 156 L 726 140 Q 748 140 748 162 L 736 566 Q 734 588 710 588 L 258 602 Q 236 602 234 580 Z", "#182a3a", .92))
    body.append(path("M232 172 Q 236 156 256 156 L 726 140 Q 748 140 748 162 L 736 566 Q 734 588 710 588 L 258 602 Q 236 602 234 580 Z", "url(#oPlate)", 1))
    body.append(path("M232 172 Q 236 156 256 156 L 726 140 Q 748 140 748 162 L 736 566 Q 734 588 710 588 L 258 602 Q 236 602 234 580 Z", "none", 1, stroke="#d8c39a", width=1.4))
    # coordinate grid inside the plate
    for i in range(1, 7):
        gy = 166 + i * 62
        body.append(path(f"M240 {gy} L 742 {gy - 8}", stroke="#8fb0bf", width=.8, extra='stroke-opacity=".22"'))
    for i in range(1, 6):
        gx = 236 + i * 84
        body.append(path(f"M{gx} 152 L {gx - 6} 594", stroke="#8fb0bf", width=.8, extra='stroke-opacity=".18"'))
    # constellation field
    pts = [(rng.uniform(300, 690), rng.uniform(210, 540)) for _ in range(11)]
    for i in range(len(pts) - 1):
        body.append(path(f"M{pts[i][0]} {pts[i][1]} L {pts[i + 1][0]} {pts[i + 1][1]}", stroke="#cfe3df", width=1.3, extra='stroke-opacity=".5"'))
    for i, (px, py) in enumerate(pts):
        r = 3.4 if i % 4 else 5.2
        body.append(circle(px, py, r, "#e9f1e4", .85))
        body.append(circle(px, py, r * 3.4, "#cfe3df", .10))
    # hand-drawn constellation ring
    body.append(f'<ellipse cx="520" cy="372" rx="182" ry="146" fill="none" stroke="#9fbcc4" stroke-width="1.1" stroke-dasharray="7 9" stroke-opacity=".38"/>')
    # compass rose bottom-left of the plate
    body.append(circle(298, 520, 34, "#101f2c", .55))
    body.append(circle(298, 520, 30, "#d8c39a", .22))
    for ang in (0, 90, 180, 270):
        dx, dy = 26 * __import__("math").sin(ang * 3.14159 / 180), -26 * __import__("math").cos(ang * 3.14159 / 180)
        body.append(path(f"M298 520 L{298 + dx} {520 + dy}", stroke="#e0d2ae", width=1.6, extra='stroke-opacity=".6"'))
    body.append(text(298, 526, "N", 13, "#e6d8b4", .8, family="Georgia, serif"))
    # margin ruling and labels
    body.append(rect(196, 128, 180, 9, "#7a6845", .38, rx=4))
    body.append(rect(198, 146, 96, 5, "#7a6845", .24, rx=2))
    for i in range(4):
        body.append(rect(614, 612 + i * 16, 150 - i * 22, 2.4, "#6f5f42", .32, rx=1))
    body.append(text(210, 690, "天文社 · 观测星图", 20, "#6f5b3c", .55, anchor="start", family="Georgia, 'Songti SC', serif"))
    # curled bottom-right corner
    body.append(path("M758 640 Q 700 664 664 700 L 758 686 Z", "#c9b58d", .95))
    body.append(path("M758 640 Q 704 660 668 698", stroke="#a48f66", width=2, extra='fill="none"'))
    # brass pin
    body.append(circle(700, 120, 11, "url(#oBrass)", .9))
    body.append(circle(700, 120, 4, "#5c4526", .8))
    return body


def note_sealed():
    body = [rect(130, 690, 740, 70, "url(#oShadow)", .9)]
    body.append(path("M170 240 L 826 226 Q 846 228 844 256 L 836 654 Q 834 682 800 684 L 190 700 Q 158 700 156 668 L 162 268 Q 164 242 170 240 Z", "#241a12", .32))
    body.append(path("M160 228 L 816 214 Q 836 216 834 244 L 826 642 Q 824 670 790 672 L 180 688 Q 148 688 146 656 L 152 256 Q 154 230 160 228 Z", "#d8c49b"))
    body.append(path("M160 228 L 816 214 Q 836 216 834 244 L 826 642 Q 824 670 790 672 L 180 688 Q 148 688 146 656 L 152 256 Q 154 230 160 228 Z", "#8d7444", .14))
    # flap
    body.append(path("M162 230 L 492 452 L 828 222 L 826 300 L 492 520 L 150 306 Z", "#cdb88c", .95))
    body.append(path("M162 230 L 492 452 L 828 222", stroke="#a08a5c", width=2.4, extra='fill="none"'))
    # string + wax seal
    body.append(path("M300 470 Q 420 540 560 470 Q 640 430 700 470", stroke="#8d6f4a", width=4, extra='fill="none"'))
    body.append(circle(700, 476, 44, "#4a1f1c", .95))
    body.append(circle(700, 476, 37, "#8d3a30", .98))
    body.append(circle(700, 476, 26, "#a34a3c", .9))
    body.append(circle(700, 476, 12, "#7d2f28", .95))
    body.append(path("M688 476 l8 -14 l9 14 z", "#d9a08a", .55))
    # label + archive stamps
    body.append(rect(232, 320, 210, 96, "#efe2c2", .95, rx=2))
    body.append(rect(232, 320, 210, 96, "#8d7444", .2, rx=2))
    for i in range(3):
        body.append(rect(250, 342 + i * 22, 150 - i * 26, 3, "#6d5c3f", .4, rx=1.5))
    body.append(text(700, 640, "封存 / 天文社", 26, "#7d6547", .55, family="Georgia, 'Songti SC', serif"))
    return body


def key():
    body = [rect(180, 700, 640, 50, "url(#oShadow)", .8)]
    body.append(f'<g transform="translate(500 420) rotate(-18)">')
    # brass key
    body.append(circle(-250, -10, 78, "url(#oBrass)", 1))
    body.append(circle(-250, -10, 60, "#2b2419", .55))
    body.append(circle(-250, -10, 52, "url(#oBrass)", .55))
    body.append(path("M-250 -78 l0 -20", stroke="#8d6531", width=16))
    body.append(path("M-300 -10 l-20 0", stroke="#8d6531", width=16))
    body.append(path("M-200 -10 l-20 0", stroke="#8d6531", width=16))
    body.append(rect(-196, -22, 400, 44, "url(#oBrass)", 1, rx=10))
    body.append(rect(-196, -22, 400, 12, "#f6e0ae", .35, rx=6))
    body.append(rect(120, 18, 26, 62, "url(#oBrassDark)", 1, rx=4))
    body.append(rect(176, 18, 22, 46, "url(#oBrassDark)", 1, rx=4))
    body.append(circle(196, 0, 8, "#f4dda8", .5))
    # leather tag on a cord
    body.append(path("M-250 -84 Q -300 -190 -206 -196", stroke="#7d5b3a", width=6, extra='fill="none"'))
    body.append(f'<g transform="translate(-180 -220) rotate(-12)">')
    body.append(rect(-84, -56, 168, 112, "#3c2a1e", .55, rx=10))
    body.append(rect(-90, -62, 168, 112, "#8a6242", 1, rx=10))
    body.append(rect(-78, -50, 144, 88, "#a37a52", .6, rx=7))
    body.append(text(0, 6, "天文社", 34, "#3d2c1d", .8))
    body.append(circle(-62, -44, 6, "#3d2c1d", .5))
    body.append('</g></g>')
    return body


def terminal(completed: bool):
    body = [ellipse(500, 720, 320, 52, "url(#oShadow)", .9)]
    # wooden case
    body.append(rect(238, 168, 524, 448, "#3f2c1d", 1, rx=18))
    body.append(rect(238, 168, 524, 448, "url(#oWood)", .55, rx=18))
    body.append(rect(258, 188, 484, 408, "#1b1712", 1, rx=12))
    body.append(rect(276, 206, 448, 330, "#0e1a1a", 1, rx=10))
    body.append(rect(276, 206, 448, 330, "url(#oScreen)", 1, rx=10))
    if completed:
        body.append(rect(276, 206, 448, 330, "#12331f", .55, rx=10))
        for i in range(0, 330, 6):
            body.append(rect(276, 206 + i, 448, 2, "#8fd6a0", .05))
        body.append(rect(316, 250, 210, 5, "#8fe0a8", .5, rx=2))
        body.append(rect(316, 276, 300, 4, "#8fe0a8", .35, rx=2))
        body.append(rect(316, 300, 250, 4, "#8fe0a8", .28, rx=2))
        body.append(rect(316, 340, 368, 150, "#0c2418", .8, rx=6))
        pts = [(360, 440), (404, 392), (452, 418), (504, 372), (556, 404), (612, 366), (656, 396)]
        for i in range(len(pts) - 1):
            body.append(path(f"M{pts[i][0]} {pts[i][1]} L {pts[i + 1][0]} {pts[i + 1][1]}", stroke="#7fd196", width=2))
        for px, py in pts:
            body.append(circle(px, py, 4, "#b8f0c6", .9))
        body.append(rect(300, 214, 400, 26, "#8fe0a8", .10))
        body.append(circle(700, 500, 120, "#7fd196", .05))
    else:
        body.append(rect(276, 206, 448, 330, "#1a2a2b", .7, rx=10))
        body.append(rect(300, 236, 180, 5, "#557a70", .35, rx=2))
        body.append(rect(300, 256, 120, 4, "#557a70", .25, rx=2))
        body.append(path("M600 420 a34 34 0 1 0 0.1 0", stroke="#4a6b62", width=3, extra='fill="none"'))
        body.append(path("M600 420 l0 -22", stroke="#4a6b62", width=3))
    # glass sheen + bezel
    body.append(poly([(300, 206), (420, 206), (300, 420)], "#dff0ec", .06))
    body.append(rect(258, 546, 484, 50, "#2c2a22", 1, rx=8))
    body.append(rect(300, 560, 60, 20, "url(#oBrass)", .9, rx=4))
    body.append(circle(680, 570, 12, "url(#oBrass)", .9))
    body.append(circle(712, 570, 8, "#d9c9a2", .5))
    body.append(rect(420, 568, 140, 5, "#c9b98f", .35, rx=2))
    # brass antennae + plate
    body.append(path("M300 168 l-40 -70", stroke="#8d6531", width=8))
    body.append(path("M700 168 l40 -70", stroke="#8d6531", width=8))
    body.append(rect(430, 128, 140, 42, "url(#oBrassDark)", .95, rx=6))
    body.append(text(500, 157, "OBSERVATION", 17, "#f1dfb0", .85, family="Georgia, serif"))
    return body


def cabinet(completed: bool):
    body = [ellipse(500, 726, 300, 50, "url(#oShadow)", .95)]
    body.append(rect(206, 96, 588, 620, "#241712", .35, rx=10))
    body.append(rect(196, 86, 588, 620, "url(#oWood)", 1, rx=10))
    body.append(rect(196, 86, 588, 620, "#2f2015", .30, rx=10))
    body.append(rect(186, 66, 608, 34, "#4b3220", 1, rx=6))
    body.append(rect(186, 66, 608, 9, "#8a6444", .55, rx=4))
    body.append(rect(408, 74, 184, 42, "url(#oBrassDark)", .92, rx=5))
    body.append(text(500, 102, "ARCHIVE", 18, "#f0dfb4", .85, family="Georgia, serif"))
    body.append(rect(214, 110, 552, 560, "#1b1210", 1, rx=4))
    body.append('<g clip-path="url(#clipCabinet)">')
    for i in range(3):
        sy = 132 + i * 176
        body.append(rect(226, sy, 528, 10, "#4a3424", .95))
        body.append(rect(226, sy + 10, 528, 150, "#241a13", .55))
        for b in range(5):
            bw = 40 + (b % 3) * 12
            body.append(rect(238 + b * 102, sy - 84, bw, 84, ["#8a6b46", "#5d6f5c", "#7d5a3e", "#6a5b42"][b % 4], .72, rx=2))
            body.append(rect(244 + b * 102, sy - 70, bw - 14, 3, "#e8d8b2", .28, rx=1))
    body.append(rect(226, 524, 528, 6, "#4a3424", .9))
    body.append('</g>')
    for door in range(2):
        dx = 226 + door * 276
        body.append(rect(dx, 116, 264, 540, "url(#oGlass)", 1, rx=4))
        body.append(rect(dx, 116, 264, 540, "none", 0, rx=4, extra='stroke="#5c4128" stroke-width="9"'))
    body.append(poly([(250, 654), (350, 116), (416, 116), (316, 654)], "#d9eef0", .07))
    body.append(rect(494, 116, 8, 540, "#3d2a1b", .9))
    for door in range(2):
        hx = 470 if door == 0 else 534
        body.append(rect(hx - 7, 356, 14, 58, "url(#oBrass)", .95, rx=7))
    if completed:
        body.append(poly([(770, 116), (900, 152), (900, 604), (770, 656)], "#241811", .5))
        body.append(poly([(766, 116), (886, 150), (886, 596), (766, 652)], "url(#oWood)", .98))
        body.append(poly([(774, 128), (874, 158), (874, 584), (774, 638)], "#2c1e15", .92))
        body.append(poly([(774, 128), (874, 158), (874, 220), (774, 196)], "#8a6444", .18))
        for yy in (300, 470):
            body.append(rect(778, yy, 92, 12, "#5a3f28", .55))
        body.append(rect(862, 330, 12, 62, "url(#oBrass)", .9, rx=6))
        body.append(rect(500, 128, 264, 528, "#ffd98a", .07))
        body.append(circle(560, 380, 210, "#ffd98a", .06))
    return body


def circuit(completed: bool):
    body = [ellipse(500, 716, 300, 46, "url(#oShadow)", .9)]
    body.append(rect(236, 108, 528, 580, "#1d2523", .5, rx=12))
    body.append(rect(224, 96, 528, 580, "#3c4a45", 1, rx=12))
    body.append(rect(224, 96, 528, 580, "#5d6d64", .18, rx=12))
    body.append(rect(248, 120, 480, 452, "#232d2a", 1, rx=6))
    body.append(rect(248, 120, 480, 24, "#0f1715", .8, rx=4))
    body.append(text(488, 138, "DISTRIBUTION", 18, "#c8b98d", .55, family="Georgia, serif"))
    for i in range(4):
        cx = 310 + i * 122
        body.append(rect(cx - 40, 190, 80, 126, "#4a5650", 1, rx=8))
        body.append(rect(cx - 34, 198, 68, 110, "#161d1b", 1, rx=6))
        body.append(rect(cx - 12, 204, 24, 98, "#b9b09a" if not completed else "#8fbf9a", .92, rx=10))
        if completed:
            body.append(rect(cx - 8, 210, 16, 86, "#d4f0cc", .35, rx=8))
        body.append(circle(cx, 190, 9, "url(#oBrass)", .9))
        body.append(circle(cx, 316, 9, "url(#oBrass)", .9))
    body.append(rect(296, 366, 408, 30, "#151d1b", 1, rx=15))
    body.append(rect(300, 370, 400, 22, "#2f3b37", 1, rx=11))
    lx = 646 if completed else 354
    body.append(circle(lx, 381, 24, "#1a2220", 1))
    body.append(rect(lx - 12, 344, 24, 74, "url(#oBrassDark)", 1, rx=10))
    body.append(circle(lx, 352, 13, "url(#oBrass)", .95))
    body.append(text(316, 424, "OFF", 14, "#c9c3ae", .55, anchor="start", family="Georgia, serif"))
    body.append(text(676, 424, "ON", 14, "#c9c3ae", .55, anchor="end", family="Georgia, serif"))
    body.append(circle(716, 500, 26, "#1a2220", 1))
    body.append(circle(716, 500, 16, "#ffcf82" if completed else "#4a4438", .95))
    if completed:
        body.append(circle(716, 500, 64, "#ffcf82", .12))
    body.append(rect(296, 470, 220, 8, "#8d9a8f", .22, rx=4))
    body.append(rect(296, 492, 160, 6, "#8d9a8f", .16, rx=3))
    body.append(rect(296, 520, 300, 8, "#8d9a8f", .14, rx=4))
    body.append(path("M224 556 q-64 26 -74 96", stroke="#1a211f", width=15, extra='fill="none"'))
    body.append(path("M752 556 q64 26 74 96", stroke="#1a211f", width=15, extra='fill="none"'))
    return body


def panel(completed: bool):
    body = [ellipse(500, 716, 290, 44, "url(#oShadow)", .8)]
    body.append(rect(300, 76, 400, 640, "#1b1410", .45, rx=18))
    body.append(rect(288, 64, 400, 640, "#2a1d15", 1, rx=18))
    body.append(rect(300, 76, 376, 616, "url(#oBrass)", .55, rx=14))
    body.append(rect(316, 92, 344, 584, "#2b2a24", 1, rx=10))
    body.append(rect(316, 92, 344, 584, "#9aa89a", .10, rx=10))
    body.append(text(488, 136, "OBSERVATORY", 22, "#e6cf9c", .65, family="Georgia, serif"))
    body.append(text(488, 164, "SEQUENCE", 18, "#e6cf9c", .45, family="Georgia, serif"))
    # four recessed medallions (decorative; real symbols come from server data)
    positions = [(420, 260), (564, 260), (420, 430), (564, 430)]
    for i, (cx, cy) in enumerate(positions):
        body.append(circle(cx, cy, 58, "#1a1a16", 1))
        body.append(circle(cx, cy, 52, "url(#oBrass)", .8))
        body.append(circle(cx, cy, 42, completed and "#3f5a3e" or "#232a24", 1))
        if completed:
            body.append(circle(cx, cy, 34, "#a9d8a0", .22))
            body.append(path(f"M{cx-14} {cy+2} l10 12 l20 -24", stroke="#cdeec4", width=5, extra='fill="none"'))
        else:
            body.append(path(f"M{cx-16} {cy} l32 0", stroke="#6f7a6a", width=2.4, extra='stroke-opacity=".5"'))
        body.append(circle(cx, cy, 58, "#000000", .0, extra='stroke="#5d4a2a" stroke-width="3"'))
    # engraved footing + lamp
    body.append(rect(400, 540, 200, 8, "#8d7645", .35, rx=4))
    body.append(circle(640, 600, 18, "#1a1a16", 1))
    body.append(circle(640, 600, 12, "#ffd58c" if completed else "#4a4a3e", .9))
    body.append(rect(360, 620, 280, 6, "#8d7645", .22, rx=3))
    return body


def _wrap(parts: list[str]) -> str:
    return _doc("".join(parts))


VARIANTS = {
    "note": [
        {"id": "note-logbook", "state": "default", "note_style": "logbook", "parts": note_logbook},
        {"id": "note-chart", "state": "default", "note_style": "star-chart", "parts": note_chart},
        {"id": "note-sealed", "state": "default", "note_style": "sealed-note", "parts": note_sealed},
    ],
    "key": [{"id": "key-brass", "state": "default", "note_style": None, "parts": key}],
    "terminal": [
        {"id": "terminal-off", "state": "default", "note_style": None, "parts": lambda: terminal(False)},
        {"id": "terminal-on", "state": "completed", "note_style": None, "parts": lambda: terminal(True)},
    ],
    "cabinet": [
        {"id": "cabinet-closed", "state": "default", "note_style": None, "parts": lambda: cabinet(False)},
        {"id": "cabinet-open", "state": "completed", "note_style": None, "parts": lambda: cabinet(True)},
    ],
    "circuit": [
        {"id": "circuit-off", "state": "default", "note_style": None, "parts": lambda: circuit(False)},
        {"id": "circuit-on", "state": "completed", "note_style": None, "parts": lambda: circuit(True)},
    ],
    "panel": [
        {"id": "panel-idle", "state": "default", "note_style": None, "parts": lambda: panel(False)},
        {"id": "panel-lit", "state": "completed", "note_style": None, "parts": lambda: panel(True)},
    ],
}
