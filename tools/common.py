"""Part model, shared drawing pieces (JST sockets, plugs, wires, pads) and the generic
schematic symbol and PCB footprint builders."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from svgkit import Font, circle, crect, el, find_font, g, line, n, path, rect, stroke, svg_doc

MONO = Font(find_font("MB_FONT_MONO", ["JetBrainsMono-Medium.ttf", "jetbrains_mono_medium.ttf",
                                       "JetBrainsMono-Regular.ttf", "jetbrains_mono_regular.ttf"]))
SANS = Font(find_font("MB_FONT_SANS", ["Inter-Regular.ttf", "inter_regular.ttf"]))
BOLD = Font(find_font("MB_FONT_BOLD", ["Inter-SemiBold.ttf", "inter_semibold.ttf", "Inter-Bold.ttf",
                                       "inter_bold.ttf"]))

PITCH = 2.54          # the board's own connector pitch (JST-XH plugs are 2.50 and fit)
U = 2.54              # schematic grid, 0.1 inch

# colours shared by every drawing
SILK = "#f4f4f4"
HOUSING = "#f6f4ef"
HOUSING_EDGE = "#c9c4b8"
HOUSING_IN = "#dedad0"
METAL = "#9aa0a6"
METAL_DARK = "#6c7278"
METAL_LIGHT = "#d5d9dd"
HOLE = "#1b1620"
PAD = "#c9cdd1"
GREEN_PCB = "#1c8a4a"
GREEN_PCB_EDGE = "#136b38"
BLUE_PCB = "#1d4fa8"
BLUE_PCB_EDGE = "#153b80"
WIRE = {"red": "#d6322f", "black": "#2a2a2c", "white": "#ececea", "blue": "#2f6fd6",
        "yellow": "#f2c230", "brown": "#6b3f24", "orange": "#f0761e"}
KIT_CABLE_3 = ["blue", "white", "red"]              # signal, VCC, GND: the kit's 3-wire cable as photographed
KIT_CABLE_4 = ["red", "white", "blue", "yellow"]    # VCC, GND and the two signals: the kit's 4-wire cable
WIRE_EDGE = {"red": "#8f1d1b", "black": "#000000", "white": "#a9a9a4", "blue": "#1c478f",
             "yellow": "#a8820f", "brown": "#3d2212", "orange": "#a34c0c"}


@dataclass
class Pin:
    """One connector of a part."""
    name: str                     # shown in Fritzing when the mouse is over the pin
    desc: str                     # longer text
    label: str = ""               # short label in the schematic symbol (defaults to name)
    kind: str = "male"            # male, female or wire
    net: str | None = None        # pins of one net are joined inside the part (a Fritzing bus)
    side: str = "L"               # schematic side: L, R or B
    gap: bool = False             # leave an empty slot before this pin in the schematic
    pcb: tuple[float, float] | None = None   # pad centre in the footprint
    pad: tuple[float, float] = (0.74, 0.5)   # pad ring: centre-line radius, ring width


@dataclass
class Part:
    slug: str                     # file name stem
    module_id: str
    title: str
    label: str                    # reference designator prefix
    family: str
    description: str
    tags: list[str]
    props: dict[str, str]
    pins: list[Pin]
    bb_size: tuple[float, float] = (0, 0)
    bb_body: str = ""             # breadboard drawing; pins carry id="connector<i>pin"
    pcb_size: tuple[float, float] = (0, 0)
    pcb_silk: str = ""            # silkscreen artwork for the footprint
    sch_title: list[str] = field(default_factory=list)
    summary: str = ""             # one line for the README
    photo: str = ""               # what the drawing was made from
    home: str = ""                # plug-in parts: the board connector the part is drawn for
    origin: tuple[float, float] = (0, 0)   # plug-in parts: where the board's corner is in the drawing
    in_bin: bool = True           # listed in the parts bin


# ---------------------------------------------------------------- drawing pieces

def cid(i: int | None) -> str | None:
    return None if i is None else f"connector{i}pin"


def hole_pad(x, y, i: int | None = None, r=0.95, square=False) -> str:
    """A bare plated hole, as on the photographed boards. The ring is the connector."""
    ring = (crect(x, y, 2 * r, 2 * r, PAD, id=cid(i)) if square else circle(x, y, r, PAD, id=cid(i)))
    return ring + circle(x, y, 0.5, HOLE)


def solder_joint(x, y, r=0.8) -> str:
    return circle(x, y, r, METAL) + circle(x - 0.15, y - 0.15, r * 0.45, METAL_LIGHT)


def jst_socket(cx, cy, count, ids=None, vertical=False, key=1) -> str:
    """A white JST-XH socket seen from above (looking into it). `ids` are the connector numbers
    of its pins in drawing order: left to right, or top to bottom when vertical. key=1 puts the
    slotted wall below (right when vertical), key=-1 on the other side.

    The connector of a pin is its whole slice of the socket, not the thin metal pin. Fritzing
    joins a plug to a socket when the centre of each plug pin lies inside a socket connector, so
    a plug dropped on roughly, or pulled up to 1.27 mm sideways by the 0.1 inch grid, still
    connects, and to the right pins."""
    length = PITCH * (count - 1) + 4.9
    depth = 5.75

    def box(u, v, w, h, fill, **a):
        return crect(cx + v, cy + u, h, w, fill, **a) if vertical else crect(cx + u, cy + v, w, h, fill, **a)

    out = [box(0, 0, length, depth, HOUSING, rx=0.45, stroke=HOUSING_EDGE, stroke_width=0.14)]
    if ids:             # one slice of the housing per pin, the full pitch wide: the plug's target
        out += [box((k - (count - 1) / 2) * PITCH, 0, PITCH, depth - 0.3, HOUSING, id=cid(i)) for k, i in enumerate(ids)]
    out.append(box(0, -0.25 * key, length - 1.7, depth - 2.3, HOUSING_IN, rx=0.25))
    for s in (-1, 1):   # the two slots of the keyed wall
        out.append(box(s * (length / 2 - 2.3), key * (depth / 2 - 0.55), 0.9, 1.1, HOUSING_IN))
    for k in range(count):
        out.append(box((k - (count - 1) / 2) * PITCH, -0.25 * key, 0.74, 0.74, METAL, stroke=METAL_DARK, stroke_width=0.1))
    return "".join(out)


def jst_plug(cx, cy, count, ids, colours, up=True) -> tuple[str, list[tuple[float, float]]]:
    """A JST-XH cable plug lying flat, wires leaving upward (or downward). Returns the drawing
    and where each wire enters, so the caller can draw the cable."""
    length = 2.5 * (count - 1) + 4.9
    h = 6.4
    s = -1 if up else 1
    out = [crect(cx, cy, length, h, HOUSING, rx=0.4, stroke=HOUSING_EDGE, stroke_width=0.14)]
    entries = []
    for k in range(count):
        x = cx + (k - (count - 1) / 2) * 2.5
        out.append(crect(x, cy - s * 0.5, 1.5, 3.6, HOUSING_IN, rx=0.2))
        out.append(crect(x, cy + s * 2.35, 1.1, 1.7, HOUSING_IN))
        out.append(crect(x, cy - s * 0.3, 0.8, 2.2, METAL, stroke=METAL_DARK, stroke_width=0.1, id=cid(ids[k])))
        out.append(crect(x, cy + s * (h / 2 - 0.35), 1.0, 0.7, WIRE[colours[k]]))
        entries.append((x, cy + s * h / 2))
    return "".join(out), entries


def wire(d, colour, sw=1.0) -> str:
    return stroke(d, WIRE_EDGE[colour], sw + 0.3) + stroke(d, WIRE[colour], sw)


def bare_end(x, y, i, vertical=True, length=2.6) -> str:
    """A stripped, tinned wire end; the connector of a flying lead."""
    if vertical:
        return crect(x, y + length / 2, 0.7, length, METAL_LIGHT, stroke=METAL_DARK, stroke_width=0.1, id=cid(i))
    return crect(x + length / 2, y, length, 0.7, METAL_LIGHT, stroke=METAL_DARK, stroke_width=0.1, id=cid(i))


def pcb_plate(x, y, w, h, fill, edge, rx=0.6) -> str:
    return rect(x, y, w, h, fill, rx=rx, stroke=edge, stroke_width=0.15)


def mount_hole(x, y, r=1.5, ring=PAD) -> str:
    return circle(x, y, r + 0.5, ring) + circle(x, y, r, "#ffffff")


def silk(s, x, y, size, rot_deg=0.0, anchor="m", fill=SILK, font=None) -> str:
    return (font or MONO).text(s, x, y, size, fill, anchor=anchor, rot_deg=rot_deg)


def mesh(cx, cy, r, step, colour, sw=0.12) -> str:
    """Woven steel gauze clipped to a circle."""
    d = []
    k = -r + step / 2
    while k < r:
        half = math.sqrt(max(r * r - k * k, 0))
        d.append(f"M{n(cx - half)} {n(cy + k)}H{n(cx + half)}M{n(cx + k)} {n(cy - half)}V{n(cy + half)}")
        k += step
    return stroke("".join(d), colour, sw, cap="butt")


# ---------------------------------------------------------------- views

def breadboard_svg(part: Part, layer: str = "breadboard") -> str:
    w, h = part.bb_size
    return svg_doc(w, h, g(part.bb_body, id=layer), part.title,
                   f"{part.title}. MakerBuddy IoT Kit, https://makerbuddy.cc. CC BY-SA 4.0.")


def schematic_svg(part: Part) -> str:
    """A box symbol on the 0.1 inch grid: pins left, right and along the bottom."""
    size = 1.5
    ink, pin_ink = "#000000", "#555555"
    sides = {s: [] for s in "LRB"}
    for i, p in enumerate(part.pins):
        if p.gap and sides[p.side]:
            sides[p.side].append(None)
        sides[p.side].append(i)
    lab = lambda i: part.pins[i].label or part.pins[i].name
    wide = lambda idx: max([SANS.width(lab(i), size) for i in idx if i is not None] or [0])
    wl, wr, wb = wide(sides["L"]), wide(sides["R"]), wide(sides["B"])
    title_size = 2.1
    wt = max(BOLD.width(t, title_size) for t in part.sch_title)
    rows = max(len(sides["L"]), len(sides["R"]), 2)
    inner = wl + wr + wt + (4.5 if (wl or wr) else 2.0)
    cols = max(math.ceil(inner / U), len(sides["B"]) + 1, 4)
    box_w = cols * U
    x0 = U if sides["L"] else 0.3
    top = 0.3
    side_bottom = (rows + 0.5) * U
    bottom_rows = math.ceil((wb + 2.0 + (len(part.sch_title) * 3.2 if not (wl or wr) else 0)) / U) if sides["B"] else 0
    yb = (rows + bottom_rows + (1 if sides["B"] else 0)) * U if sides["B"] else side_bottom
    if not sides["B"]:
        yb = (rows + 1) * U - 0.3
    width = x0 + box_w + (U if sides["R"] else 0.3)
    height = yb + (U if sides["B"] else 0.3)
    out = [rect(x0, top, box_w, yb - top, "#ffffff", stroke=ink, stroke_width=0.3, stroke_linejoin="round")]

    def pin(i, x1, y1, x2, y2, tx, ty):
        out.append(line(x1, y1, x2, y2, pin_ink, 0.25, id=cid(i)))
        out.append(rect(tx - 0.05, ty - 0.05, 0.1, 0.1, "none", id=f"connector{i}terminal"))

    for k, i in enumerate(sides["L"]):
        if i is None:
            continue
        y = (k + 1) * U
        pin(i, 0.125, y, x0, y, 0.125, y)
        out.append(SANS.text(lab(i), x0 + 0.7, y, size, pin_ink, anchor="l"))
    for k, i in enumerate(sides["R"]):
        if i is None:
            continue
        y = (k + 1) * U
        pin(i, x0 + box_w, y, width - 0.125, y, width - 0.125, y)
        out.append(SANS.text(lab(i), x0 + box_w - 0.7, y, size, pin_ink, anchor="r"))
    first = x0 + (cols - len(sides["B"]) + 1) // 2 * U
    for k, i in enumerate(sides["B"]):
        if i is None:
            continue
        x = first + k * U
        pin(i, x, yb, x, height - 0.125, x, height - 0.125)
        out.append(SANS.text(lab(i), x, yb - 0.7, size, pin_ink, anchor="l", rot_deg=-90))
    low = (side_bottom if sides["B"] else yb) if (wl or wr) else yb - wb - 1.5
    ty = (top + low) / 2 - (len(part.sch_title) - 1) * 1.6
    tx = x0 + wl + (box_w - wl - wr) / 2 if (wl or wr) else x0 + box_w / 2
    for k, t in enumerate(part.sch_title):
        f, s, c = (BOLD, title_size, ink) if k == 0 else (SANS, 1.5, pin_ink)
        out.append(f.text(t, tx, ty + k * 3.2, s, c))
    return svg_doc(width, height, g(out, id="schematic"), part.title + " (schematic symbol)")


def pcb_svg(part: Part) -> str:
    """Footprint: white silkscreen and through-hole pads on both copper layers."""
    w, h = part.pcb_size
    pads = []
    for i, p in enumerate(part.pins):
        if p.pcb is None:
            raise ValueError(f"{part.slug}: pin {p.name} has no pad")
        r, ring = p.pad
        pads.append(circle(p.pcb[0], p.pcb[1], r, "none", stroke="#F7BD13", stroke_width=ring, id=cid(i)))
    body = g(part.pcb_silk, id="silkscreen") + g(g(pads, id="copper0"), id="copper1")
    return svg_doc(w, h, body, part.title + " (PCB footprint)")


def silk_outline(w, h, inset=0.15) -> str:
    return rect(inset, inset, w - 2 * inset, h - 2 * inset, "none", stroke="#ffffff", stroke_width=0.2)


def silk_text(s, x, y, size, rot_deg=0.0, anchor="m") -> str:
    return MONO.text(s, x, y, size, "#ffffff", anchor=anchor, rot_deg=rot_deg)
