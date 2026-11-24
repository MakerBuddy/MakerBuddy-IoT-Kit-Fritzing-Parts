"""Small SVG helpers shared by the part drawings.

Everything is written with plain presentation attributes (no CSS, no <use>, no gradients, no
<text>) so the same file renders the same way in Fritzing, a browser, Inkscape and KiCad's or
draw.io's SVG import. Lettering is converted to outlines, so no font has to be installed.
"""
from __future__ import annotations

import math
import os
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont


def n(v: float, d: int = 3) -> str:
    """A number as short as it can be written."""
    s = f"{float(v):.{d}f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def el(tag: str, body=None, **attrs) -> str:
    parts = [tag]
    for k, v in attrs.items():
        if v is None:
            continue
        k = k.rstrip("_").replace("_", "-")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            v = n(v)
        parts.append(f'{k}="{v}"')
    head = "<" + " ".join(parts)
    if body is None:
        return head + "/>"
    if isinstance(body, (list, tuple)):
        body = "".join(body)
    return f"{head}>{body}</{tag}>"


def rect(x, y, w, h, fill, **a) -> str:
    return el("rect", x=x, y=y, width=w, height=h, fill=fill, **a)


def crect(cx, cy, w, h, fill, **a) -> str:
    """A rectangle given by its centre."""
    return rect(cx - w / 2, cy - h / 2, w, h, fill, **a)


def circle(cx, cy, r, fill, **a) -> str:
    return el("circle", cx=cx, cy=cy, r=r, fill=fill, **a)


def ellipse(cx, cy, rx, ry, fill, **a) -> str:
    return el("ellipse", cx=cx, cy=cy, rx=rx, ry=ry, fill=fill, **a)


def path(d, fill="none", **a) -> str:
    return el("path", d=d, fill=fill, **a)


def line(x1, y1, x2, y2, stroke, sw, cap="round", **a) -> str:
    return el("line", x1=x1, y1=y1, x2=x2, y2=y2, stroke=stroke, stroke_width=sw, stroke_linecap=cap, **a)


def stroke(d, colour, sw, cap="round", join="round", **a) -> str:
    return el("path", d=d, fill="none", stroke=colour, stroke_width=sw, stroke_linecap=cap,
              stroke_linejoin=join, **a)


def g(children, **a) -> str:
    return el("g", children, **a)


def pts(points) -> str:
    return " ".join(f"{n(x)},{n(y)}" for x, y in points)


def polygon(points, fill, **a) -> str:
    return el("polygon", points=pts(points), fill=fill, **a)


def rot(x, y, cx, cy, deg):
    """(x, y) turned `deg` clockwise (SVG's y runs down) about (cx, cy)."""
    r = math.radians(deg)
    dx, dy = x - cx, y - cy
    return cx + dx * math.cos(r) - dy * math.sin(r), cy + dx * math.sin(r) + dy * math.cos(r)


class Font:
    """Turns text into outline path data."""

    def __init__(self, file: str | os.PathLike):
        self.tt = TTFont(str(file))
        self.glyphs = self.tt.getGlyphSet()
        self.cmap = self.tt.getBestCmap()
        self.upm = self.tt["head"].unitsPerEm
        self.cap = getattr(self.tt["OS/2"], "sCapHeight", 0) or 0.7 * self.upm
        self.hmtx = self.tt["hmtx"]

    def _glyph(self, ch: str) -> str:
        return self.cmap.get(ord(ch)) or self.cmap.get(ord("?")) or ".notdef"

    def width(self, s: str, size: float, track: float = 0.0) -> float:
        return sum(self.hmtx[self._glyph(c)][0] / self.upm + track for c in s) * size - track * size

    def d(self, s: str, x: float, y: float, size: float, anchor: str = "m", rot_deg: float = 0.0,
          valign: str = "m", track: float = 0.0) -> str:
        """Path data for `s`. anchor: l, m or r. valign: m centres the capital height on y, b puts
        the baseline on y. rot_deg turns the text clockwise about (x, y)."""
        k = size / self.upm
        total = self.width(s, size, track)
        ox = {"l": 0.0, "m": -total / 2, "r": -total}[anchor]
        oy = self.cap * k / 2 if valign == "m" else 0.0
        c, sn = math.cos(math.radians(rot_deg)), math.sin(math.radians(rot_deg))
        out = []
        for ch in s:
            name = self._glyph(ch)
            pen = SVGPathPen(self.glyphs, ntos=lambda v: n(v, 2))
            tp = TransformPen(pen, (k * c, k * sn, k * sn, -k * c, x + ox * c - oy * sn, y + ox * sn + oy * c))
            self.glyphs[name].draw(tp)
            cmds = pen.getCommands()
            if cmds:
                out.append(cmds)
            ox += (self.hmtx[name][0] / self.upm + track) * size
        return "".join(out)

    def text(self, s, x, y, size, fill, anchor="m", rot_deg=0.0, valign="m", track=0.0, **a) -> str:
        return el("path", d=self.d(s, x, y, size, anchor, rot_deg, valign, track), fill=fill, **a)


def find_font(env: str, names: list[str]) -> Path:
    """A font file from $env, tools/fonts/, or the usual system folders."""
    here = Path(__file__).resolve().parent
    if os.environ.get(env):
        return Path(os.environ[env])
    roots = [here / "fonts", Path.home() / "Library/Fonts", Path("/Library/Fonts"),
             Path.home() / ".fonts", Path.home() / ".local/share/fonts", Path("/usr/share/fonts"),
             Path("C:/Windows/Fonts")]
    for root in roots:
        if not root.exists():
            continue
        for name in names:
            hit = next(iter(root.rglob(name)), None)
            if hit:
                return hit
    raise SystemExit(f"Font not found: put one of {names} in tools/fonts/ or set ${env} to its path "
                     "(see README, 'Rebuilding').")


def svg_doc(w: float, h: float, body: str, title: str, desc: str = "") -> str:
    """A complete SVG file, sized in millimetres with one user unit per millimetre."""
    meta = el("title", title) + (el("desc", desc) if desc else "")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="{n(w)}mm" height="{n(h)}mm" '
            f'viewBox="0 0 {n(w)} {n(h)}">{meta}{body}</svg>\n')
