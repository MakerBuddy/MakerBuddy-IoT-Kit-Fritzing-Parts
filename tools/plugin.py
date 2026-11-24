"""The kit parts as they are used: each part with its cable.

The kit has no loose wires. A sensor reaches the board through a JST cable, and the whole plug
goes into one socket. Two things in Fritzing come close to that, and both are built here.

flexible (the parts in the bin): the wires of the cable are "bendable legs", the leads Fritzing
gives its own LEDs, motors and battery clips. A lead's free end can be dragged onto a pin, and
with Alt held the part can be moved while its leads stay where they are and stretch. Each part
is drawn where it lies beside the board with its lead ends exactly on the pins of its home
socket, so dropping it there connects every wire at once; after that it can go anywhere.

fixed (fritzing/parts/fixed-cable/): the part, a drawn cable and a drawn plug as one rigid
piece. Dropping the plug on the socket connects it, but the part cannot be moved away from it.

Fritzing has no cable whose plug moves as one piece: it moves a whole part, or one wire end.
"""
from __future__ import annotations

import dataclasses
import re

import modules
from board import CONN
from common import (HOUSING, HOUSING_EDGE, HOUSING_IN, KIT_CABLE_3, KIT_CABLE_4, METAL, METAL_DARK, PITCH, WIRE,
                    WIRE_EDGE, Part, Pin, cid, leg, silk_text, wire)
from modules import PAD_SCREW, SITE, lead_footprint
from svgkit import circle, crect, g, n, path, polygon, rect, stroke

SPACING = 1.25    # between the wires of a cable
RIGHT, DOWN, LEFT = (1, 0), (0, 1), (-1, 0)


def home(conn_id: str):
    """Pin centres of a board connector (board millimetres) and the way a cable leaves it:
    always off the nearest edge of the board."""
    pins = [(p[1], p[2]) for p in CONN[conn_id]["pins"]]
    if conn_id in ("PORT_26", "PORT_25", "PORT_33", "PORT_32"):
        return pins, RIGHT
    if conn_id in ("PORT_23", "PORT_19", "PORT_18"):
        return pins, DOWN
    return pins, LEFT


class Drawing:
    """Collects artwork drawn in board millimetres and moves it to its own page at the end."""

    def __init__(self):
        self.items: list[str] = []
        self.pts: list[tuple[float, float]] = []

    def add(self, svg: str, *pts) -> None:
        self.items.append(svg)
        self.pts += pts

    def finish(self, margin=1.0):
        x1, y1 = min(p[0] for p in self.pts) - margin, min(p[1] for p in self.pts) - margin
        x2, y2 = max(p[0] for p in self.pts) + margin, max(p[1] for p in self.pts) + margin
        body = g(self.items, transform=f"translate({n(-x1)},{n(-y1)})")
        return (x2 - x1, y2 - y1), body, (-x1, -y1)


def pt(p) -> str:
    return f"{n(p[0])} {n(p[1])}"


def board_plug(pins, d0, colours, first=0):
    """A JST-XH plug seen from above, pushed into a socket whose pins are at `pins`. Returns its
    body, its pins (the connectors) and, per wire, the start of its path and where it joins the
    cable. The wire of the pin nearest the way out runs down the middle; the others pass it on
    either side, so no wire lies over another pin."""
    count = len(pins)
    cx, cy = sum(p[0] for p in pins) / count, sum(p[1] for p in pins) / count
    along, across = PITCH * (count - 1) + 3.7, 4.4
    w, h = (along, across) if d0[0] else (across, along)
    body = crect(cx, cy, w, h, "#fbfaf7", rx=0.4, stroke="#a8a294", stroke_width=0.2)
    n0 = (d0[1], -d0[0])
    lane_c = (cx + d0[0] * (along / 2 + 1.2), cy + d0[1] * (along / 2 + 1.2))
    by_exit = sorted(range(count), key=lambda k: -(pins[k][0] * d0[0] + pins[k][1] * d0[1]))
    starts = [None] * count
    for rank, k in enumerate(by_exit):
        o = (0, -1, 1, -2, 2)[rank] * SPACING
        p = pins[k]
        side = (p[0] + n0[0] * o, p[1] + n0[1] * o)
        lane = (lane_c[0] + n0[0] * o, lane_c[1] + n0[1] * o)
        d = f"M{pt(p)}"
        if o:
            d += f"Q{pt(side)} {pt((side[0] + d0[0] * 1.3, side[1] + d0[1] * 1.3))}"
        starts[k] = (d + f"L{pt(lane)}", lane, o)
    entries = "".join(crect(p[0], p[1], 1.4, 1.4, WIRE[c], stroke=WIRE_EDGE[c], stroke_width=0.12, id=cid(first + k))
                      for k, (p, c) in enumerate(zip(pins, colours)))
    corners = [(cx - w / 2, cy - h / 2), (cx + w / 2, cy + h / 2)]
    return body, entries, starts, corners


def cable(dr: Drawing, starts, d0, end, d1, colours, l0, l1) -> None:
    """The wires from the plug to `end`, arriving there against d1 (the way a cable leaves the
    part). They keep their order side by side all the way."""
    n1 = (-d1[1], d1[0])
    for (d, lane, o), colour in zip(starts, colours):
        e = (end[0] + n1[0] * o, end[1] + n1[1] * o)
        c1 = (lane[0] + d0[0] * l0, lane[1] + d0[1] * l0)
        c2 = (e[0] + d1[0] * l1, e[1] + d1[1] * l1)
        dr.add(wire(d + f"C{pt(c1)} {pt(c2)} {pt(e)}", colour, 0.95), lane, c1, c2, e)


def placed(part: Part, x, y, turn=0):
    """Transform, point map and direction map for a module drawing put with its top-left corner
    at (x, y); turn=-90 stands it on end with what was its right edge on top."""
    w, h = part.bb_size
    if turn == 0:
        return (f"translate({n(x)},{n(y)})", lambda px, py: (x + px, y + py), lambda d: d, [(x + 1, y + 1), (x + w - 1, y + h - 1)])
    if turn == -90:
        return (f"translate({n(x)},{n(y + w)}) rotate(-90)", lambda px, py: (x + py, y + w - px), lambda d: (d[1], -d[0]),
                [(x + 1, y + 1), (x + h - 1, y + w - 1)])
    raise ValueError(turn)


def strip_pins(body: str, keep: dict[int, int]) -> str:
    """A module drawing without its connectors, except those in `keep` (old number: new number)."""
    def swap(m):
        i = int(m.group(1))
        return f' id="connector{keep[i]}pin"' if i in keep else ""
    return re.sub(r' id="connector(\d+)pin"', swap, body)


def module_cap(sock):
    """The cable's plug sitting in the module's own socket, in the module's own coordinates.
    Returns the artwork, where the cable ends under it, and its corners."""
    cx, cy = sock["c"]
    ex, ey = sock["exit"]
    if sock.get("side"):      # a socket that takes its plug from the side (soil sensor)
        x1, x2 = cx + 1.6, cx + 7.4
        art = rect(x1, cy - 4.6, x2 - x1, 9.2, HOUSING, rx=0.4, stroke=HOUSING_EDGE, stroke_width=0.14)
        art += "".join(rect(x1 + 0.9, cy + (k - 1) * 2.5 - 0.6, 2.6, 1.2, HOUSING_IN) for k in range(3))
        return art, (x2 - 1.0, cy), [(x1, cy - 4.6), (x2, cy + 4.6)]
    along, across = PITCH * (sock["n"] - 1) + 3.7, 4.4
    w, h = (across, along) if sock["vertical"] else (along, across)
    art = crect(cx, cy, w, h, HOUSING, rx=0.4, stroke=HOUSING_EDGE, stroke_width=0.14)
    for k in range(sock["n"]):
        off = (k - (sock["n"] - 1) / 2) * PITCH
        px, py = (cx, cy + off) if sock["vertical"] else (cx + off, cy)
        art += crect(px, py, 1.3, 1.3, HOUSING_IN)
    return art, (cx + ex * 0.9, cy + ey * 0.9), [(cx - w / 2, cy - h / 2), (cx + w / 2, cy + h / 2)]


# ---------------------------------------------------------------- modules on a kit cable

def cabled(bare: Part, conn_id: str, x, y, turn=0, l0=14.0, l1=8.0, pin_order=None, summary="") -> Part:
    sock = modules.SOCKETS[bare.slug]
    pins, d0 = home(conn_id)
    colours = KIT_CABLE_3 if len(pins) == 3 else KIT_CABLE_4
    tf, at, turn_dir, corners = placed(bare, x, y, turn)
    keep = {3: 3, 4: 4, 5: 5} if bare.slug == "relay-module" else {}
    module = g(strip_pins(bare.bb_body, keep), transform=tf)
    body, entries, starts, plug_corners = board_plug(pins, d0, colours)
    dr = Drawing()
    dr.pts += corners + plug_corners
    d1 = turn_dir(sock["exit"])
    if sock.get("hidden"):                       # the socket is on the back: the cable goes under the module
        dr.add(body)
        cable(dr, starts, d0, at(*sock["c"]), d1, colours, l0, l1)
        dr.add(module)
    else:
        art, end, cap_corners = module_cap(sock)
        dr.add(module)
        dr.add(body)
        cable(dr, starts, d0, at(*end), d1, colours, l0, l1)
        dr.add(g(art, transform=tf), *[at(*c) for c in cap_corners])
    dr.add(entries)
    size, art_all, origin = dr.finish()

    order = pin_order or list(range(len(pins)))
    count = len(order)
    (pcb_size, pcb_silk, pads) = lead_footprint(count, bare.sch_title[0].upper()[:13], None)
    out_pins = [dataclasses.replace(bare.pins[i], kind="male", pcb=pads[k], pad=(0.74, 0.5), side="L", gap=False)
                for k, i in enumerate(order)]
    if keep:                                     # the relay's three screw terminals stay on the module
        w, h = pcb_size
        pcb_silk += rect(0.3, h + 0.2, w - 0.6, 6.6, "none", stroke="#ffffff", stroke_width=0.2)
        for k, i in enumerate(sorted(keep)):
            pad = (w / 2 + (k - 1) * 3.5, h + 3.5)
            out_pins.append(dataclasses.replace(bare.pins[i], pcb=pad, pad=(1.0, 0.7)))
        pcb_size = (w, h + 7.1)
    label = CONN[conn_id]["label"]
    where = f"connector {label}" if label.isdigit() else f"the {label} connector"
    return dataclasses.replace(
        bare, module_id=f"makerbuddy-kit-{bare.slug}-r2",
        title=bare.title.replace(" (MakerBuddy)", " with its cable (MakerBuddy)"),
        summary=summary or bare.summary,
        description=(bare.description.replace(" " + SITE, "")
                     + f" This part comes with the kit's {count}-wire cable and its plug: drop the plug on {where} of "
                       f"the MakerBuddy IoT Kit board and all {count} pins connect at once. " + SITE),
        props={**bare.props, "cable": "kit cable with plug"},
        pins=out_pins, bb_size=size, bb_body=art_all, pcb_size=pcb_size, pcb_silk=pcb_silk,
        home=conn_id, origin=origin, in_bin=True)


def as_fixed(part: Part) -> Part:
    """The rigid version, kept outside the bin."""
    return dataclasses.replace(
        part, slug=part.slug + "-fixed-cable",
        title=part.title.replace(" with its cable (MakerBuddy)", " with fixed cable and plug (MakerBuddy)")
        .replace(" on its lead (MakerBuddy)", " with fixed lead and plug (MakerBuddy)"),
        props={**part.props, "cable": "fixed, with plug"}, in_bin=False, folder="fixed-cable")


# ---------------------------------------------------------------- modules on bendable leads

def crosses(a1, a2, b1, b2) -> bool:
    side = lambda p, q, r: (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return side(a1, a2, b1) * side(a1, a2, b2) < 0 and side(b1, b2, a1) * side(b1, b2, a2) < 0


def leads(dr: Drawing, roots, ends, colours) -> None:
    """One bendable lead per pin, from the part to the socket, never crossing each other."""
    if crosses(roots[0], ends[0], roots[-1], ends[-1]):
        roots = roots[::-1]
    for k, (root, end, colour) in enumerate(zip(roots, ends, colours)):
        dr.add(leg(k, root, end, colour), root, end)


def flexible(bare: Part, conn_id: str, x, y, turn=0, roots=None, pin_order=None) -> Part:
    """A module with the kit cable as bendable leads. (x, y) is where its drawing goes in board
    millimetres; `roots` says where the leads come out when the socket is on the back."""
    sock = modules.SOCKETS[bare.slug]
    pins, _ = home(conn_id)
    count = len(pins)
    colours = KIT_CABLE_3 if count == 3 else KIT_CABLE_4
    tf, at, _turn_dir, corners = placed(bare, x, y, turn)
    keep = {3: 3, 4: 4, 5: 5} if bare.slug == "relay-module" else {}
    dr = Drawing()
    dr.add(g(strip_pins(bare.bb_body, keep), transform=tf), *corners)
    if roots is None:                              # the leads leave the plug sitting in the module's socket
        art, _end, cap_corners = module_cap(sock)
        dr.add(g(art, transform=tf), *[at(*c) for c in cap_corners])
        (cx, cy), (ex, ey) = sock["c"], sock["exit"]
        edge = (cx + 7.4, cy) if sock.get("side") else (cx + ex * 2.2, cy + ey * 2.2)
        roots = [(edge[0] - ey * (k - (count - 1) / 2) * 1.3, edge[1] + ex * (k - (count - 1) / 2) * 1.3)
                 for k in range(count)]
    leads(dr, [at(*r) for r in roots], pins, colours)
    size, art_all, origin = dr.finish()
    fixed = cabled(bare, conn_id, x, y, turn, pin_order=pin_order)   # for its pins and footprint only
    label = CONN[conn_id]["label"]
    where = f"connector {label}" if label.isdigit() else f"the {label} connector"
    pins_out = [dataclasses.replace(p, leg=(k < count)) for k, p in enumerate(fixed.pins)]
    return dataclasses.replace(
        fixed, module_id=f"makerbuddy-kit-{bare.slug}-r3", pins=pins_out, bb_size=size, bb_body=art_all, origin=origin,
        description=(bare.description.replace(" " + SITE, "")
                     + f" This part comes with the kit's {count}-wire cable. Drop it with the cable's ends on {where} "
                       f"of the MakerBuddy IoT Kit board and all {count} wires connect; then hold Alt (Option) and "
                       "drag the part to move it while the cable stays plugged in. Each wire end can also be dragged "
                       "to a pin on its own. " + SITE),
        props={**bare.props, "cable": "kit cable, flexible"})


def servo_flexible() -> Part:
    fixed = servo()
    pins, _ = home("PORT_19")
    dr = Drawing()
    fx, fy = 7.0, 96.5
    dr.add(servo_body(fx, fy), (fx, fy - 0.4), (fx + 32.3, fy + 12.6))
    leads(dr, [(fx + 2.0 + k * 1.1, fy + 0.2) for k in range(3)], pins, ["orange", "red", "brown"])
    size, body, origin = dr.finish()
    return dataclasses.replace(
        fixed, module_id="makerbuddy-kit-sg90-servo-r3", bb_size=size, bb_body=body, origin=origin,
        pins=[dataclasses.replace(p, leg=True) for p in fixed.pins],
        description=fixed.description.replace(
            "Drop the plug on connector 19 of the MakerBuddy IoT Kit board and all three pins connect at once.",
            "Drop it with the lead's ends on connector 19 of the MakerBuddy IoT Kit board and all three wires connect; "
            "then hold Alt (Option) and drag the servo to move it while the lead stays plugged in."),
        props={**fixed.props, "cable": "own lead, flexible"})


def ds18b20_flexible() -> Part:
    fixed = ds18b20()
    pins, _ = home("PORT_26")
    dr = Drawing()
    stub = "M84 1V7"
    dr.add(stroke(stub, "#000000", 4.3, cap="butt") + stroke(stub, "#222226", 3.8, cap="butt"), (82, 1), (86, 7))
    dr.add(path("M81 -12V-42a3 3 0 0 1 6 0V-12Z", "#c9cdd2", stroke="#868c92", stroke_width=0.2)
           + stroke("M82.6 -41V-14", "#f1f3f5", 0.7), (81, -45), (87, -12))
    dr.add(rect(80.4, -13, 7.2, 14.5, "#19191c", rx=0.8, stroke="#000000", stroke_width=0.15), (80.4, -13), (87.6, 1.5))
    leads(dr, [(84 + (k - 1) * 0.95, 7.2) for k in range(3)], pins, ["yellow", "red", "black"])
    size, body, origin = dr.finish()
    return dataclasses.replace(
        fixed, module_id="makerbuddy-kit-ds18b20-probe-r3", bb_size=size, bb_body=body, origin=origin,
        pins=[dataclasses.replace(p, leg=True) for p in fixed.pins],
        description=fixed.description.replace(
            "Drop the plug on connector 26 of the MakerBuddy IoT Kit board, the connector with the 4.7 k 1-Wire "
            "pull-up, and all three pins connect at once.",
            "Drop it with the lead's ends on connector 26 of the MakerBuddy IoT Kit board, the connector with the "
            "4.7 k 1-Wire pull-up, and all three wires connect; then hold Alt (Option) and drag the probe to move it "
            "while the lead stays plugged in."),
        props={**fixed.props, "cable": "own lead, flexible"})


def module_only(bare: Part) -> Part:
    return dataclasses.replace(
        bare, slug=bare.slug.removesuffix("-module") + "-module-only", module_id=f"makerbuddy-kit-{bare.slug}-bare-r2",
        title=bare.title.replace(" (MakerBuddy)", ", module only (MakerBuddy)"),
        props={**bare.props, "cable": "none"}, in_bin=False, folder="module-only")


# ---------------------------------------------------------------- parts with their own lead

def own_lead(slug, title, label, summary, description, tags, props, names, conn_id, dr, origin_size, sch, photo) -> Part:
    size, body, origin = origin_size
    pcb_size, pcb_silk, pads = lead_footprint(3, sch[0].upper()[:9], None)
    pins = [Pin(name, desc, pcb=pads[k]) for k, (name, desc) in enumerate(names)]
    return Part(slug=slug, module_id=f"makerbuddy-kit-{slug}-r2", title=title, label=label,
                family=f"MakerBuddy {props['type']}", summary=summary, description=description + " " + SITE,
                tags=["MakerBuddy", "IoT Kit"] + tags, props=props, pins=pins, bb_size=size, bb_body=body,
                pcb_size=pcb_size, pcb_silk=pcb_silk, sch_title=sch, photo=photo, home=conn_id, origin=origin)


def servo_body(fx, fy) -> str:
    """The SG90 seen facing its shaft; (fx, fy) is the top-left corner of its mounting flange."""
    cx, cy = fx + 16.15, fy + 6.1
    sx = cx + 5.35
    art = [rect(fx, fy, 32.3, 12.2, "#1f4fbf", rx=0.8, stroke="#16388a", stroke_width=0.15)]
    for hx in (fx + 2.25, fx + 30.05):
        art.append(circle(hx, cy, 1.1, "#ffffff") + rect(hx - 0.4, cy - 0.3, 0.8, 0.6, "#ffffff"))
    art.append(rect(fx + 4.9, fy - 0.4, 22.5, 13.0, "#2f6ae0", rx=1.0, stroke="#1c3f96", stroke_width=0.15))
    art.append(circle(sx - 6.6, cy, 2.9, "#3f7bf0", stroke="#1c3f96", stroke_width=0.12)
               + circle(sx, cy, 5.9, "#3f7bf0", stroke="#1c3f96", stroke_width=0.12))
    arm = [(sx, cy - 3.0), (sx - 15.0, cy - 1.7), (sx - 15.0, cy + 1.7), (sx, cy + 3.0)]
    art.append(polygon(arm, "#f6f4ee", stroke="#c2bdb1", stroke_width=0.15, stroke_linejoin="round")
               + circle(sx - 15.0, cy, 1.7, "#f6f4ee", stroke="#c2bdb1", stroke_width=0.15)
               + circle(sx, cy, 3.2, "#f6f4ee", stroke="#c2bdb1", stroke_width=0.15))
    art += [circle(sx - k, cy, 0.4, "#b9b4a8") for k in (5.5, 7.5, 9.5, 11.5, 13.5)]
    art.append(circle(sx, cy, 1.0, METAL, stroke=METAL_DARK, stroke_width=0.12)
               + stroke(f"M{n(sx - 0.6)} {n(cy)}h1.2M{n(sx)} {n(cy - 0.6)}v1.2", METAL_DARK, 0.2))
    return "".join(art)


def servo() -> Part:
    pins, d0 = home("PORT_19")
    colours = ["orange", "red", "brown"]
    body, entries, starts, corners = board_plug(pins, d0, colours)
    dr = Drawing()
    dr.add(body, *corners)
    fx, fy = 14.0, 106.0                      # the servo's mounting flange, top-left corner
    for (d, lane, o), colour in zip(starts, colours):
        ex = fx + 3.0 + o * 0.9
        dr.add(wire(d + f"C{n(lane[0])} {n(lane[1] + 12)} {n(ex)} {n(fy - 11)} {n(ex)} {n(fy + 0.6)}", colour, 0.95))
    dr.add(servo_body(fx, fy), (fx, fy - 0.4), (fx + 32.3, fy + 12.6))
    dr.add(entries)
    return own_lead(
        "sg90-servo", "SG90 micro servo on its lead (MakerBuddy)", "M",
        "SG90 9 g servo. Its own lead ends in the plug.",
        "SG90 9 g micro servo, 0 to 180 degrees. Its three-wire lead ends in a JST plug: PWM (orange), VCC (red), "
        "GND (brown). Drop the plug on connector 19 of the MakerBuddy IoT Kit board and all three pins connect at once.",
        ["SG90", "servo", "motor", "actuator"],
        {"type": "micro servo", "model": "SG90", "interface": "PWM", "connector": "JST-XH 3-pin plug",
         "board connector": "19", "cable": "own lead with plug"},
        [("PWM", "Control signal (orange wire). On the board: connector 19 (GPIO 19)."), ("VCC", "5 V supply (red wire)"),
         ("GND", "Ground (brown wire)")],
        "PORT_19", dr, dr.finish(), ["SG90", "servo"], "sg90-servo-with-horns")


def ds18b20() -> Part:
    pins, d0 = home("PORT_26")
    colours = ["yellow", "red", "black"]
    body, entries, starts, corners = board_plug(pins, d0, colours)
    dr = Drawing()
    dr.add(body, *corners)
    y0 = pins[0][1]
    for (d, lane, o), colour in zip(starts, colours):
        dr.add(wire(d + f"C{n(lane[0] + 3)} {n(lane[1])} {n(81)} {n(y0 + o * 0.7)} {n(84)} {n(y0 + o * 0.7)}", colour, 0.95))
    lead = f"M83 {n(y0)}C90.5 {n(y0)} 92 {n(y0 - 4)} 92 5"
    dr.add(stroke(lead, "#000000", 4.3, cap="butt") + stroke(lead, "#222226", 3.8, cap="butt"))
    dr.add(path("M89 -8V-38a3 3 0 0 1 6 0V-8Z", "#c9cdd2", stroke="#868c92", stroke_width=0.2)
           + stroke("M90.6 -37V-10", "#f1f3f5", 0.7), (89, -41), (95, -8))
    dr.add(rect(88.4, -9, 7.2, 14.5, "#19191c", rx=0.8, stroke="#000000", stroke_width=0.15), (88.4, -9), (95.6, 5.5))
    dr.add(entries)
    return own_lead(
        "ds18b20-probe", "DS18B20 waterproof temperature probe on its lead (MakerBuddy)", "T",
        "Waterproof DS18B20 probe. Its own lead ends in the plug.",
        "DS18B20 digital temperature sensor in a waterproof stainless-steel tube. Its lead ends in a JST plug: DQ "
        "(yellow), VCC (red), GND (black). Drop the plug on connector 26 of the MakerBuddy IoT Kit board, the "
        "connector with the 4.7 k 1-Wire pull-up, and all three pins connect at once. Drawn with the 1 m lead "
        "shortened.",
        ["DS18B20", "temperature", "probe", "1-Wire", "sensor"],
        {"type": "temperature probe", "sensor": "DS18B20", "interface": "1-Wire", "connector": "JST-XH 3-pin plug",
         "board connector": "26", "cable": "own lead with plug"},
        [("DQ", "1-Wire data (yellow wire). On the board: connector 26, which has the 4.7 k pull-up."),
         ("VCC", "Supply, 3.0 to 5.5 V (red wire)"), ("GND", "Ground (black wire)")],
        "PORT_26", dr, dr.finish(), ["DS18B20", "temperature probe"], "ds18b20-waterproof-probe")


# ---------------------------------------------------------------- the kit, each part in its place

def kit() -> tuple[list[Part], list[Part], list[Part]]:
    """The parts of the bin in the order of the board's connectors, their rigid versions, and the
    bare modules. Places are in board millimetres and chosen so the leads reach each socket at an
    angle (leads that run along a row of pins would lie on top of each other)."""
    bare = {p.slug: p for p in modules.bare_modules()}
    flex = [
        ds18b20_flexible(),
        flexible(bare["dht11"], "PORT_25", 92.2, -17.8),
        flexible(bare["mq2-gas-sensor"], "PORT_33", 99.5, 57.1),
        flexible(bare["soil-moisture-sensor"], "PORT_32", 76.0, 68.8, turn=-90),
        flexible(bare["relay-module"], "PORT_23", -55.1, 82.26),
        servo_flexible(),
        flexible(bare["hc-sr501-pir"], "PORT_18", 41.45, 78.1),
        flexible(bare["hc-sr04"], "HCSR04", -37.75, -23.9, roots=[(19.75 + (k - 1.5) * 1.3, 21.9) for k in range(4)],
                 pin_order=[0, 3, 2, 1]),
        flexible(bare["lcd-1602-i2c"], "I2C_1", -100.0, 8.0, roots=[(84.0 + (k - 1.5) * 1.3, 37.0) for k in range(4)]),
    ]
    fixed = [
        ds18b20(),
        cabled(bare["dht11"], "PORT_25", 111, -14, l0=24, l1=8),
        cabled(bare["mq2-gas-sensor"], "PORT_33", 110, 45, l0=24, l1=7),
        cabled(bare["soil-moisture-sensor"], "PORT_32", 83, 58, turn=-90, l0=9, l1=5),
        cabled(bare["relay-module"], "PORT_23", -48, 84, l0=14, l1=9),
        servo(),
        cabled(bare["hc-sr501-pir"], "PORT_18", 48, 80, l0=7, l1=7),
        cabled(bare["hc-sr04"], "HCSR04", -62, -14, l0=18, l1=12, pin_order=[0, 3, 2, 1]),
        cabled(bare["lcd-1602-i2c"], "I2C_1", -104, 20, l0=88, l1=30),
    ]
    return flex, [as_fixed(p) for p in fixed], [module_only(p) for p in bare.values()]
