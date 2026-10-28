"""Small SVG authoring helpers for the rainy-astronomy theme pack.

The theme pack is drawn as layered vector illustration and rasterised locally
with headless Chrome. No image generation service is contacted; the output is
deterministic from this source.
"""
from __future__ import annotations

import math
import random
from html import escape


def f(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def lin(gid: str, stops: list[tuple[float, str, float]], x1=0, y1=0, x2=0, y2=1) -> str:
    body = "".join(f'<stop offset="{f(a)}" stop-color="{c}" stop-opacity="{f(o)}"/>' for a, c, o in stops)
    return (f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{body}</linearGradient>')


def rad(gid: str, stops: list[tuple[float, str, float]], cx=.5, cy=.5, r=.5) -> str:
    body = "".join(f'<stop offset="{f(a)}" stop-color="{c}" stop-opacity="{f(o)}"/>' for a, c, o in stops)
    return f'<radialGradient id="{gid}" cx="{cx}" cy="{cy}" r="{r}">{body}</radialGradient>'


def blur(fid: str, std: float) -> str:
    return f'<filter id="{fid}" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="{f(std)}"/></filter>'


def grain(fid: str, freq=0.85, octaves=3, opacity=0.16, matrix="1 0 0 0 0.36  0 1 0 0 0.33  0 0 1 0 0.24  0 0 0 -0.62 0.52") -> str:
    """Paper/paint grain; used as a soft-light overlay rectangle."""
    return (
        f'<filter id="{fid}" x="0" y="0" width="100%" height="100%">'
        f'<feTurbulence type="fractalNoise" baseFrequency="{freq}" numOctaves="{octaves}" seed="7" result="n"/>'
        f'<feColorMatrix in="n" type="matrix" values="{matrix}"/>'
        f'<feComposite operator="in" in2="SourceGraphic"/></filter>'
    )


def rect(x, y, w, h, fill, opacity=1.0, rx=0, extra="") -> str:
    return (f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(rx)}" '
            f'fill="{fill}" fill-opacity="{f(opacity)}" {extra}/>')


def poly(points: list[tuple[float, float]], fill, opacity=1.0, extra="") -> str:
    body = " ".join(f"{f(px)},{f(py)}" for px, py in points)
    return f'<polygon points="{body}" fill="{fill}" fill-opacity="{f(opacity)}" {extra}/>'


def path(d: str, fill="none", opacity=1.0, stroke=None, width=1.0, extra="") -> str:
    stroke_attr = f'stroke="{stroke}" stroke-width="{f(width)}" stroke-linecap="round" stroke-linejoin="round"' if stroke else ""
    return f'<path d="{d}" fill="{fill}" fill-opacity="{f(opacity)}" {stroke_attr} {extra}/>'


def ellipse(cx, cy, rx, ry, fill, opacity=1.0, extra="") -> str:
    return (f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" '
            f'fill="{fill}" fill-opacity="{f(opacity)}" {extra}/>')


def circle(cx, cy, r, fill, opacity=1.0, extra="") -> str:
    return f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="{fill}" fill-opacity="{f(opacity)}" {extra}/>'


def text(x, y, value, size, fill, opacity=1.0, anchor="middle", family="Georgia, 'Songti SC', serif", extra="") -> str:
    return (f'<text x="{f(x)}" y="{f(y)}" font-family="{family}" font-size="{f(size)}" fill="{fill}" '
            f'fill-opacity="{f(opacity)}" text-anchor="{anchor}" {extra}>{escape(value)}</text>')


def group(body: str, opacity=1.0, transform="", extra="") -> str:
    t = f'transform="{transform}"' if transform else ""
    return f'<g opacity="{f(opacity)}" {t} {extra}>{body}</g>'


def svg(width: int, height: int, body: str, defs: str = "", box: tuple[int, int] | None = None) -> str:
    bx, by = (box if box else (width, height))
    view = f"0 0 {bx} {by}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="{view}" preserveAspectRatio="xMidYMid meet">{("<defs>" + defs + "</defs>") if defs else ""}{body}</svg>')


# --------------------------------------------------------------------------
# Reusable painted parts
# --------------------------------------------------------------------------

def rain(width: int, height: int, count=170, seed=11, top=0, bottom=None, alpha=.30, tint="#cfe3ec", scale=1.0) -> str:
    """Slanted rain strokes read as weather even at small display size."""
    rng = random.Random(seed)
    bottom = height if bottom is None else bottom
    parts = []
    for _ in range(count):
        x = rng.uniform(-40, width + 40)
        y = rng.uniform(top, bottom)
        length = rng.uniform(26, 74) * scale
        wid = rng.uniform(.7, 1.9) * scale
        a = alpha * rng.uniform(.35, 1.0)
        parts.append(f'<line x1="{f(x)}" y1="{f(y)}" x2="{f(x - length * .22)}" y2="{f(y + length)}" '
                     f'stroke="{tint}" stroke-opacity="{f(a)}" stroke-width="{f(wid)}" stroke-linecap="round"/>')
    return "".join(parts)


def droplets(width: int, height: int, count=90, seed=5, alpha=.34) -> str:
    rng = random.Random(seed)
    parts = []
    for _ in range(count):
        x, y = rng.uniform(0, width), rng.uniform(0, height)
        r = rng.uniform(1.4, 4.6)
        a = alpha * rng.uniform(.3, 1)
        parts.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="#dbe9ef" fill-opacity="{f(a)}"/>')
        parts.append(f'<circle cx="{f(x - r * .3)}" cy="{f(y - r * .35)}" r="{f(r * .38)}" fill="#ffffff" fill-opacity="{f(a * .7)}"/>')
    return "".join(parts)


def dust(width: int, height: int, count=80, seed=9, alpha=.5) -> str:
    rng = random.Random(seed)
    parts = []
    for _ in range(count):
        x, y = rng.uniform(0, width), rng.uniform(0, height)
        r = rng.uniform(.7, 2.3)
        parts.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="#f6dfa8" fill-opacity="{f(alpha * rng.uniform(.15, .6))}"/>')
    return "".join(parts)


def wood_panel(x, y, w, h, base="#5c4030", dark="#3d2a20", light="#7b563d", planks=4, horizontal=True, opacity=1.0) -> str:
    parts = [rect(x, y, w, h, base, opacity)]
    steps = planks
    for i in range(steps):
        if horizontal:
            ph, py = h / steps, y + i * h / steps
            parts.append(rect(x, py, w, ph * .985, light, .10 * opacity))
            parts.append(f'<line x1="{f(x)}" y1="{f(py + ph)}" x2="{f(x + w)}" y2="{f(py + ph)}" stroke="{dark}" stroke-opacity="{f(.55 * opacity)}" stroke-width="2.4"/>')
            for k in range(3):
                gy = py + ph * (k + .5) / 3
                parts.append(f'<path d="M{f(x)} {f(gy)} C {f(x + w*.3)} {f(gy - 3)} {f(x + w*.7)} {f(gy + 3)} {f(x + w)} {f(gy)}" stroke="{dark}" stroke-opacity="{f(.18 * opacity)}" stroke-width="2" fill="none"/>')
        else:
            pw, px = w / steps, x + i * w / steps
            parts.append(rect(px, y, pw * .985, h, light, .08 * opacity))
            parts.append(f'<line x1="{f(px + pw)}" y1="{f(y)}" x2="{f(px + pw)}" y2="{f(y + h)}" stroke="{dark}" stroke-opacity="{f(.5 * opacity)}" stroke-width="2"/>')
    return "".join(parts)


def shelf(x, y, w, depth=18, fill="#4a3427") -> str:
    return (rect(x, y, w, depth, fill) + rect(x, y - depth * .55, w, depth * .55, "#67492f", .9) +
            rect(x, y + depth, w, 7, "#241a15", .55))


def book_row(x, y, w, h, seed=3, palette=("#8e5d40", "#3f5a52", "#6d6a4a", "#7c4a3d", "#4c5566")) -> str:
    rng = random.Random(seed)
    parts, cursor = [], x
    while cursor < x + w - 8:
        bw = rng.uniform(9, 20)
        bh = h * rng.uniform(.72, 1.0)
        color = rng.choice(palette)
        tilt = rng.uniform(-4, 4) if rng.random() < .18 else 0
        parts.append(f'<rect x="{f(cursor)}" y="{f(y + h - bh)}" width="{f(bw)}" height="{f(bh)}" fill="{color}" fill-opacity=".92" transform="rotate({f(tilt)} {f(cursor + bw/2)} {f(y + h)})"/>')
        if rng.random() < .5:
            parts.append(f'<rect x="{f(cursor + 1.6)}" y="{f(y + h - bh + 5)}" width="{f(bw - 3.4)}" height="2.4" fill="#e6d3a6" fill-opacity=".42"/>')
        cursor += bw + rng.uniform(1.2, 3.4)
    return "".join(parts)


def paper_sheet(x, y, w, h, rotation=0, tone="#e8dbbc") -> str:
    return (f'<g transform="rotate({f(rotation)} {f(x + w/2)} {f(y + h/2)})">'
            + rect(x + 4, y + 5, w, h, "#221a13", .35, rx=2)
            + rect(x, y, w, h, tone, .96, rx=2)
            + rect(x + 6, y + 7, w - 12, h - 14, "#ffffff", .10, rx=1)
            + f'<path d="M{f(x+9)} {f(y+h*.34)} L{f(x+w-9)} {f(y+h*.34)}" stroke="#8d7b56" stroke-opacity=".35" stroke-width="1.4"/>'
            + f'<path d="M{f(x+9)} {f(y+h*.5)} L{f(x+w-14)} {f(y+h*.5)}" stroke="#8d7b56" stroke-opacity=".28" stroke-width="1.4"/>'
            + f'<path d="M{f(x+9)} {f(y+h*.66)} L{f(x+w-22)} {f(y+h*.66)}" stroke="#8d7b56" stroke-opacity=".22" stroke-width="1.4"/>'
            + '</g>')


def star_chart(x, y, w, h, rotation=0, seed=21, ink="#7d6b45") -> str:
    """Constellation sheet: decorations only, never a puzzle answer."""
    rng = random.Random(seed)
    parts = [paper_sheet(x, y, w, h, rotation, "#ded0ae")]
    pts = [(rng.uniform(.12, .88), rng.uniform(.16, .84)) for _ in range(7)]
    for i in range(len(pts) - 1):
        parts.append(f'<line x1="{f(x + pts[i][0]*w)}" y1="{f(y + pts[i][1]*h)}" x2="{f(x + pts[i+1][0]*w)}" y2="{f(y + pts[i+1][1]*h)}" stroke="{ink}" stroke-opacity=".55" stroke-width="1.2"/>')
    for i, (px, py) in enumerate(pts):
        parts.append(circle(x + px * w, y + py * h, 2.4 if i % 2 else 3.2, ink, .8))
    for i in range(len(pts) - 1):
        parts.append(f'<line x1="{f(x + pts[i][0]*w)}" y1="{f(y + pts[i][1]*h)}" x2="{f(x + pts[i+1][0]*w)}" y2="{f(y + pts[i+1][1]*h)}" stroke="{ink}" stroke-opacity=".55" stroke-width="1.2"/>')
    return "".join(parts)


def lamp_glow(cx, cy, r, color="#f7c877", core=.55) -> str:
    return (f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="url(#gLamp)" opacity="{f(core)}"/>')


def window_night(x, y, w, h, seed=4, moon=(.28, .22), sky=("#0a1620", "#173345")) -> str:
    """Tall window: night sky, campus rooftops, trees and rain."""
    rng = random.Random(seed)
    parts = [rect(x, y, w, h, "#0a141c", 1, rx=3)]
    parts.append(f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="url(#gSky)" rx="3"/>')
    mx, my = x + w * moon[0], y + h * moon[1]
    parts.append(f'<circle cx="{f(mx)}" cy="{f(my)}" r="{f(w*.26)}" fill="url(#gMoon)" opacity=".9"/>')
    parts.append(circle(mx, my, w * .05, "#f4efd4", .95))
    parts.append(circle(mx - w * .012, my - w * .012, w * .038, "#fffbe6", .5))
    base = y + h * .70
    bx = x - 10
    roofs = []
    while bx < x + w + 20:
        bw = rng.uniform(w * .14, w * .30)
        bh = rng.uniform(h * .10, h * .26)
        roofs.append((bx, base - bh, bw, bh))
        bx += bw * rng.uniform(.82, 1.1)
    for rx0, ry0, rw, rh in roofs:
        parts.append(f'<rect x="{f(rx0)}" y="{f(ry0)}" width="{f(rw)}" height="{f(rh + 6)}" fill="#081119" fill-opacity=".97"/>')
        parts.append(f'<path d="M{f(rx0-4)} {f(ry0)} L{f(rx0 + rw/2)} {f(ry0 - rh*.34)} L{f(rx0 + rw + 4)} {f(ry0)} Z" fill="#0a141c" fill-opacity=".97"/>')
        for wx_i in range(int(rw / 16)):
            if rng.random() < .34:
                lx0 = rx0 + 6 + wx_i * 16
                ly0 = ry0 + rng.uniform(10, max(12, rh - 10))
                parts.append(f'<rect x="{f(lx0)}" y="{f(ly0)}" width="5" height="7" fill="#f0c479" fill-opacity="{f(rng.uniform(.25,.7))}"/>')
    for i in range(10):
        tx = x + rng.uniform(.02, .96) * w
        ty = base + rng.uniform(-h * .02, h * .06)
        parts.append(ellipse(tx, ty, rng.uniform(8, 18), rng.uniform(9, 22), "#0b1a1a", .95))
    parts.append(rect(x, y + h * .84, w, h * .16, "#050c11", .9))
    parts.append(f'<g transform="translate({f(x)} {f(y)})">'
                 + rain(int(w), int(h), count=int(w * .40), seed=seed, top=0, bottom=h, alpha=.30, scale=.85)
                 + droplets(int(w), int(h), count=int(w * .22), seed=seed + 2, alpha=.22) + '</g>')
    parts.append(rect(x, y, w, h, "#0d2430", .18))
    parts.append(circle(mx, my, w * .30, "#cfe3e6", .05))
    return "".join(parts)


def window_frame(x, y, w, h, bars=(2, 3), thickness=13, frame="#3b2a20") -> str:
    parts = [f'<rect x="{f(x-thickness/2)}" y="{f(y-thickness/2)}" width="{f(w+thickness)}" height="{f(h+thickness)}" '
             f'fill="none" stroke="{frame}" stroke-width="{f(thickness)}" rx="3"/>']
    for i in range(1, bars[1]):
        bx = x + w * i / bars[1]
        parts.append(rect(bx - 3.5, y, 7, h, frame, .95))
    for i in range(1, bars[0]):
        by = y + h * i / bars[0]
        parts.append(rect(x, by - 3.5, w, 7, frame, .95))
    # wet rim light on the glass
    parts.append(rect(x, y, w, 2.5, "#a8c6d2", .22))
    parts.append(rect(x, y, 2.5, h, "#a8c6d2", .16))
    return "".join(parts)


def vignette(width, height, strength=.55) -> str:
    return rect(0, 0, width, height, "url(#gVignette)", strength)


def floorlight(cx, cy, rx, ry, color="url(#gWarmFloor)", opacity=.6) -> str:
    return f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" fill="{color}" opacity="{f(opacity)}"/>'


def telescope(x, y, scale=1.0, tilt=-24, brass="#c1904c", dark="#2a2118") -> str:
    """Decorative telescope silhouette (never an interactive puzzle object)."""
    g = [f'<g transform="translate({f(x)} {f(y)}) scale({f(scale)})">']
    # tripod
    g.append(f'<path d="M0 0 L-58 132" stroke="{dark}" stroke-width="7" stroke-linecap="round"/>')
    g.append(f'<path d="M0 0 L54 134" stroke="{dark}" stroke-width="7" stroke-linecap="round"/>')
    g.append(f'<path d="M0 0 L-4 140" stroke="{dark}" stroke-width="8" stroke-linecap="round"/>')
    g.append(f'<path d="M-30 70 L34 76" stroke="{dark}" stroke-width="4" stroke-opacity=".8"/>')
    # mount
    g.append(f'<circle cx="0" cy="0" r="11" fill="{brass}"/>')
    g.append(f'<circle cx="0" cy="0" r="5" fill="#7b5a30"/>')
    # tube
    g.append(f'<g transform="rotate({f(tilt)})">')
    g.append(f'<rect x="-96" y="-15" width="196" height="30" rx="15" fill="{brass}"/>')
    g.append(f'<rect x="-96" y="-15" width="196" height="11" rx="6" fill="#e6bd7c" fill-opacity=".55"/>')
    g.append(f'<rect x="-108" y="-19" width="26" height="38" rx="8" fill="#8c6537"/>')
    g.append(f'<rect x="88" y="-12" width="20" height="24" rx="6" fill="#6d4f2c"/>')
    g.append(f'<ellipse cx="104" cy="0" rx="6" ry="13" fill="#d9e6e6" fill-opacity=".55"/>')
    g.append('</g></g>')
    return "".join(g)


def definition_block() -> str:
    """Shared gradients/filters used by every scene."""
    return "".join([
        lin("gSky", [(0, "#050d15", 1), (.45, "#0d2233", 1), (1, "#1b3b4d", 1)]),
        rad("gMoon", [(0, "#f3f0d6", .55), (.45, "#c9dbe0", .18), (1, "#b9d0d8", 0)]),
        rad("gLamp", [(0, "#ffdfa1", .95), (.35, "#f3b968", .55), (.7, "#c98338", .18), (1, "#8a5625", 0)]),
        rad("gCool", [(0, "#a9c9d6", .30), (.45, "#7ea6b6", .12), (1, "#3b6573", 0)]),
        rad("gWarmSoft", [(0, "#f3c078", .34), (.45, "#d99b4e", .13), (1, "#8a5c2b", 0)]),
        lin("gMoonSpill", [(0, "#a8c9d6", .30), (.55, "#7ea6b6", .12), (1, "#48707f", 0)]),
        rad("gWarmFloor", [(0, "#f6cf8a", .55), (.55, "#e0a95c", .22), (1, "#8a5c2b", 0)]),
        rad("gVignette", [(0, "#000000", 0), (.62, "#000000", 0), (1, "#04121a", .92)], .5, .5, .75),
        lin("gWall", [(0, "#33291f", 1), (.55, "#2a2119", 1), (1, "#1b1512", 1)]),
        lin("gFloor", [(0, "#4a3123", 1), (1, "#241812", 1)]),
        lin("gDesk", [(0, "#7a5334", 1), (1, "#4c3322", 1)]),
        lin("gBrass", [(0, "#e8c07c", 1), (.5, "#bd8c48", 1), (1, "#8a6130", 1)]),
        lin("gPaper", [(0, "#f4e8cd", 1), (1, "#d9c8a4", 1)]),
        lin("gGreen", [(0, "#20303a", 1), (1, "#0e1a22", 1)]),
        blur("fSoft", 26),
        blur("fSoft2", 9),
        grain("fGrain", freq=.9, octaves=3, opacity=.16),
    ])


def grain_overlay(width: int, height: int, opacity=.22) -> str:
    return (f'<rect x="0" y="0" width="{width}" height="{height}" fill="#808080" '
            f'filter="url(#fGrain)" opacity="{opacity}" style="mix-blend-mode:soft-light"/>')


def soft_light(cx, cy, r, color="#f8d089", opacity=.35) -> str:
    return f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="{color}" opacity="{f(opacity)}" filter="url(#fSoft)"/>'
