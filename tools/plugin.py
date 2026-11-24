"""The kit parts as they are used: each part with its cable and plug.

The kit has no loose wires. A sensor reaches the board through a JST cable, and the whole plug
goes into one socket. Fritzing joins a plug to a socket the same way when the plug's pins are
dropped onto the socket's pins: every pin connects at once. Two sets of parts use that.

fixed (the parts in the bin): the part, a drawn cable and a drawn plug as one rigid piece, drawn
where it lies when it is plugged into its home connector. Drop the plug on the socket and the
part is connected. The part cannot be moved away from its plug.

flexible (the starter sketch, fritzing/parts/flexible-cable/): the plug is a part of its own and
the cable is ordinary Fritzing wires from the plug to the sensor. Drag the plug and the wires
follow; drop it on a socket and every pin connects. Fritzing cannot keep wires inside a part of
the bin, so this set lives in a sketch where the wires are already drawn.

Fritzing has no cable whose plug moves as one piece of the same part: a part moves as a whole.
"""
from __future__ import annotations

import dataclasses
import re

import modules
from board import CONN
from common import (HOUSING, HOUSING_EDGE, HOUSING_IN, KIT_CABLE_3, KIT_CABLE_4, METAL, METAL_DARK, PITCH, WIRE,
                    WIRE_EDGE, Part, Pin, cid, silk_text, wire)
from modules import PAD_SCREW, SITE, lead_footprint
from svgkit import circle, crect, g, n, path, polygon, rect, stroke  # noqa: F401

SPACING = 1.25    # between the wires of a cable
FLEX_REV = "r2"   # the same for the -flex parts
PLUG_REV = "r2"   # and for the separate plugs
REV = "r4"        # last part of every module id here; raise it when a drawing or a pin changes (see README)
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


def add(p, d, k=1.0):
    return (p[0] + d[0] * k, p[1] + d[1] * k)


def left_of(d):
    """The direction a quarter turn from d; wires of a cable are counted along it."""
    return (-d[1], d[0])


class Leg:
    """One wire's way through a plug, from its pin to where it joins the cable. It can be written
    in either direction, so a cable can be drawn as one line from plug to plug."""

    def __init__(self, start):
        self.start = start
        self.segs: list[tuple] = []

    def to(self, p):
        self.segs.append(("L", p))
        return self

    def quad(self, c, p):
        self.segs.append(("Q", c, p))
        return self

    def cubic(self, c1, c2, p):
        self.segs.append(("C", c1, c2, p))
        return self

    @property
    def end(self):
        return self.segs[-1][-1] if self.segs else self.start

    def out(self) -> str:
        """From the pin outward, starting a new line."""
        return f"M{pt(self.start)}" + "".join(seg[0] + " ".join(pt(q) for q in seg[1:]) for seg in self.segs)

    def back(self) -> str:
        """From the cable end to the pin, carrying on a line that has reached the cable end."""
        ends = [self.start] + [seg[-1] for seg in self.segs]
        return "".join(seg[0] + " ".join(pt(q) for q in list(seg[1:-1])[::-1] + [ends[i]])
                       for i, seg in reversed(list(enumerate(self.segs))))


PLUG, PLUG_EDGE = "#fbfaf7", "#a8a294"
PIN_ART = 1.4     # the coloured square where a wire enters a plug
HIT = 0.6         # the connector itself: a spot at the centre of that square (see README, "Selecting a plug")


def wire_entry(p, colour) -> str:
    return crect(p[0], p[1], PIN_ART, PIN_ART, WIRE[colour], stroke=WIRE_EDGE[colour], stroke_width=0.12)


def spot(p, colour, i) -> str:
    """A connector: a small spot in the wire's own colour, so it does not show."""
    return crect(p[0], p[1], HIT, HIT, WIRE[colour], id=cid(i))


def board_plug(pins, d0, colours, first=0):
    """A JST-XH plug seen from above, pushed into a socket whose pins are at `pins`, the wires
    leaving along the row of pins. Returns its body, its pins (the connectors), per wire its leg
    with where it joins the cable and its place in the cable, and its corners. The wire of the pin
    nearest the way out runs down the middle; the others pass it on either side, so no wire lies
    over another pin."""
    count = len(pins)
    cx, cy = sum(p[0] for p in pins) / count, sum(p[1] for p in pins) / count
    along, across = PITCH * (count - 1) + 3.7, 4.4
    w, h = (along, across) if d0[0] else (across, along)
    body = crect(cx, cy, w, h, PLUG, rx=0.4, stroke=PLUG_EDGE, stroke_width=0.2)
    n0 = left_of(d0)
    lane_c = add((cx, cy), d0, along / 2 + 1.2)
    by_exit = sorted(range(count), key=lambda k: -(pins[k][0] * d0[0] + pins[k][1] * d0[1]))
    legs = [None] * count
    for rank, k in enumerate(by_exit):
        o = (0, 1, -1, 2, -2)[rank] * SPACING
        leg = Leg(pins[k])
        if o:
            side = add(pins[k], n0, o)
            leg.quad(side, add(side, d0, 1.3))
        lane = add(lane_c, n0, o)
        legs[k] = (leg.to(lane), lane, o)
    entries = "".join(wire_entry(p, c) + spot(p, c, first + k) for k, (p, c) in enumerate(zip(pins, colours)))
    corners = [(cx - w / 2, cy - h / 2), (cx + w / 2, cy + h / 2)]
    return body, entries, legs, corners


def cross_plug(pins, e, along=None, across=4.4, centre=None):
    """The same plug with its wires leaving across the row of pins, as on a module's socket.
    Returns body, legs and corners as board_plug does; the caller colours the wire entries."""
    count = len(pins)
    cx, cy = centre or (sum(p[0] for p in pins) / count, sum(p[1] for p in pins) / count)
    along = along or PITCH * (count - 1) + 3.7
    w, h = (across, along) if e[0] else (along, across)
    body = crect(cx, cy, w, h, PLUG, rx=0.4, stroke=PLUG_EDGE, stroke_width=0.2)
    n0 = left_of(e)
    lane_c = add((cx, cy), e, across / 2 + 2.8)
    in_row = sorted(range(count), key=lambda k: pins[k][0] * n0[0] + pins[k][1] * n0[1])
    legs = [None] * count
    for rank, k in enumerate(in_row):
        o = (rank - (count - 1) / 2) * SPACING
        depth = (pins[k][0] - cx) * e[0] + (pins[k][1] - cy) * e[1]
        edge = add(pins[k], e, across / 2 - depth + 0.4)
        lane = add(lane_c, n0, o)
        legs[k] = (Leg(pins[k]).to(edge).cubic(add(edge, e, 1.1), add(lane, e, -1.1), lane), lane, o)
    corners = [(cx - w / 2, cy - h / 2), (cx + w / 2, cy + h / 2)]
    return body, legs, corners


def socket_pins(sock):
    """Pin centres of a module's socket, in the module's own coordinates."""
    cx, cy = sock["c"]
    if sock.get("side"):                         # the plug stands out of the side of the socket
        return [(cx + 4.3, cy + (k - 1) * 2.5) for k in range(3)]
    offs = [(k - (sock["n"] - 1) / 2) * PITCH for k in range(sock["n"])]
    return [(cx, cy + o) for o in offs] if sock["vertical"] else [(cx + o, cy) for o in offs]


def module_plug(sock, at, e):
    """The cable's plug sitting in a module's socket, drawn where the module lies: `at` maps the
    module's coordinates to the page and `e` is the way the cable leaves. Returns the body, the
    legs (in the order of the socket's pins; not coloured yet) and the corners."""
    pins = [at(*p) for p in socket_pins(sock)]
    if sock.get("inline"):
        body, _entries, legs, corners = board_plug(pins, e, ["white"] * len(pins))
        return body, legs, corners
    if sock.get("side"):
        cx, cy = at(sock["c"][0] + 4.5, sock["c"][1])
        return cross_plug(pins, e, along=9.2, across=5.8, centre=(cx, cy))
    return cross_plug(pins, e)


def match(legs, wanted):
    """Which wire takes which leg of a plug so that the wires do not cross: `wanted` is, per wire,
    its place across the cable where it arrives (counted along left_of(the way out))."""
    by_place = sorted(range(len(legs)), key=lambda j: legs[j][2])
    return dict(zip(sorted(range(len(wanted)), key=lambda k: wanted[k]), by_place))


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


# ---------------------------------------------------------------- modules on a kit cable

def cabled(bare: Part, conn_id: str, x, y, turn=0, l0=14.0, l1=8.0, pin_order=None, summary="", square=False) -> Part:
    sock = modules.SOCKETS[bare.slug]
    pins, d0 = home(conn_id)
    colours = KIT_CABLE_3 if len(pins) == 3 else KIT_CABLE_4
    tf, at, turn_dir, corners = placed(bare, x, y, turn)
    keep = {3: 3, 4: 4, 5: 5} if bare.slug == "relay-module" else {}
    body, entries, legs, plug_corners = board_plug(pins, d0, colours)
    e = turn_dir(sock["exit"])
    far_body, far_legs, far_corners = module_plug(sock, at, e)
    dr = Drawing()
    dr.pts += corners + plug_corners + far_corners
    dr.add(g(strip_pins(bare.bb_body, keep), transform=tf))
    dr.add(body + far_body)
    # one line per wire, from its pin in the board plug to its place in the plug on the module;
    # a cable that leaves one way arrives turned over, hence the minus
    takes = match(far_legs, [-o for _leg, _lane, o in legs])
    inside = max(-(lane[0] * e[0] + lane[1] * e[1]) for _leg, lane, _o in legs)
    far_entries = ""
    for k, (leg, lane, _o) in enumerate(legs):
        far_leg, far_lane, _ = far_legs[takes[k]]
        if square:      # straight out of the board plug, one quarter turn, straight into the module's plug
            turn = (far_lane[0] if d0[0] else lane[0], lane[1] if d0[0] else far_lane[1])
            r = 2.2 + inside + (lane[0] * e[0] + lane[1] * e[1])
            way = f"L{pt(add(turn, d0, -r))}Q{pt(turn)} {pt(add(turn, e, -r))}L{pt(far_lane)}"
            dr.pts += [turn]
        else:
            c1, c2 = add(lane, d0, l0), add(far_lane, e, l1)
            way = f"C{pt(c1)} {pt(c2)} {pt(far_lane)}"
            dr.pts += [c1, c2]
        dr.add(wire(leg.out() + way + far_leg.back(), colours[k], 0.95), lane, far_lane)
        far_entries += wire_entry(far_leg.start, colours[k])
    dr.add(far_entries + entries)
    size, art_all, origin = dr.finish()

    order = pin_order or list(range(len(pins)))
    count = len(order)
    (pcb_size, pcb_silk, pads) = lead_footprint(count, bare.sch_title[0].upper()[:13], None)
    out_pins = [dataclasses.replace(bare.pins[i], kind="male", pcb=pads[k], pad=(0.74, 0.5), side="L", gap=False,
                                    hybrid=True)
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
        bare, module_id=f"makerbuddy-kit-{bare.slug}-{REV}",
        title=bare.title.replace(" (MakerBuddy)", " with its cable (MakerBuddy)"),
        summary=summary or bare.summary,
        description=(bare.description.replace(" " + SITE, "")
                     + f" This part comes with the kit's {count}-wire cable and its plug: drop the plug on {where} of "
                       f"the MakerBuddy IoT Kit board and all {count} pins connect at once. " + SITE),
        props={**bare.props, "cable": "kit cable with plug"},
        pins=out_pins, bb_size=size, bb_body=art_all, pcb_size=pcb_size, pcb_silk=pcb_silk,
        home=conn_id, origin=origin, in_bin=True)


# ---------------------------------------------------------------- the flexible set

TAIL = 1.6   # how far a wire stub runs past the plug before the Fritzing wire takes over


def wire_end(tip, colour, i) -> str:
    """The end of a wire stub: a small cap, and in its middle the connector a Fritzing wire holds."""
    return (crect(tip[0], tip[1], 1.1, 1.1, WIRE[colour], stroke=WIRE_EDGE[colour], stroke_width=0.12)
            + spot(tip, colour, i))


def plug_tails(pins, d0, colours):
    """Where the wire stubs of a plug end, per pin."""
    _body, _entries, legs, _corners = board_plug(pins, d0, colours)
    return [add(lane, d0, TAIL) for _leg, lane, _o in legs]


def plug_part(slug, title, names, colours, d0, fits) -> Part:
    """A cable plug on its own: pins that go into a socket, and a short stub of each wire for a
    Fritzing wire to start from. Pin and stub of one wire are joined inside the part."""
    count = len(names)
    pins = [(k * PITCH, 0.0) for k in range(count)]
    body, entries, legs, corners = board_plug(pins, d0, colours)
    dr = Drawing()
    dr.add(body, *corners)
    tips = plug_tails(pins, d0, colours)
    for (leg, lane, _o), tip, colour in zip(legs, tips, colours):
        dr.add(wire(leg.out() + f"L{pt(tip)}", colour, 0.95), lane, tip)
    dr.add(entries)
    for k, (tip, colour) in enumerate(zip(tips, colours)):
        dr.add(wire_end(tip, colour, count + k), tip)
    size, art, origin = dr.finish(margin=0.9)
    (w, h), silk_art, pads = lead_footprint(count, "PLUG", None)
    silk_art += rect(0.3, h + 0.2, w - 0.6, 3.0, "none", stroke="#ffffff", stroke_width=0.2)
    out = [Pin(name, f"Plug pin: {text}. Goes into the socket.", net=f"wire{k}", side="L", pcb=pads[k], hybrid=True)
           for k, (name, text) in enumerate(names)]
    out += [Pin(f"{name} wire", f"The {colours[k]} wire of this pin. A Fritzing wire to the sensor starts here.", label=name,
                net=f"wire{k}", side="R", pcb=(pads[k][0], h + 1.7), pad=(0.6, 0.4)) for k, (name, _t) in enumerate(names)]
    return Part(
        slug=slug, module_id=f"makerbuddy-kit-{slug}-{PLUG_REV}", title=title, label="P", family="MakerBuddy cable plug",
        summary=f"{count}-pin plug with a stub of each wire. {fits}",
        description=(f"JST-XH cable plug with {count} pins ({', '.join(nm for nm, _ in names)}) and a short stub of each "
                     f"wire. Press anywhere on the plug to move it as one piece. Drop it on a socket of the MakerBuddy "
                     f"IoT Kit board and every pin connects at once. Draw Fritzing wires from the stub ends to the part "
                     f"at the other end of the cable; they follow the plug when it is dragged. {fits} " + SITE),
        tags=["MakerBuddy", "IoT Kit", "JST-XH", "plug", "cable"],
        props={"type": "cable plug", "pins": str(count), "wires": ", ".join(colours)},
        pins=out, bb_size=size, bb_body=art, pcb_size=(w, h + 3.5), pcb_silk=silk_art, sch_title=["Plug", f"{count} wires"],
        photo="jst-cable", origin=origin, in_bin=False, folder="flexible-cable")


def plugs() -> dict[str, Part]:
    three = [("SIG", "signal"), ("VCC", "5 V"), ("GND", "ground")]
    return {p.slug: p for p in (
        plug_part("cable-plug-3-wire", "Kit cable plug, 3 wires (MakerBuddy)", three, KIT_CABLE_3, RIGHT,
                  "For connectors 26, 25, 33, 32, 23, 19 and 18; turn it to fit the bottom row."),
        plug_part("cable-plug-4-wire", "Kit cable plug, 4 wires (MakerBuddy)",
                  [("VCC", "5 V"), ("GND", "ground"), ("S1", "first signal: SCL on I2C, 2 on HC-SR04"),
                   ("S2", "second signal: SDA on I2C, 15 on HC-SR04")], KIT_CABLE_4, LEFT,
                  "For the HC-SR04, UART and I2C connectors."),
        plug_part("servo-lead-plug", "Servo lead plug (MakerBuddy)",
                  [("PWM", "control signal"), ("VCC", "5 V"), ("GND", "ground")], ["orange", "red", "brown"], RIGHT,
                  "The plug on the SG90's own lead. Home: connector 19."),
        plug_part("probe-lead-plug", "DS18B20 probe lead plug (MakerBuddy)",
                  [("DQ", "1-Wire data"), ("VCC", "supply"), ("GND", "ground")], ["yellow", "red", "black"], RIGHT,
                  "The plug on the probe's own lead. Home: connector 26."),
    )}


def tails(dr: Drawing, roots, colours, toward) -> None:
    """The wire ends of a part: one small cap per pin for a Fritzing wire to start from. They
    are put in the order that keeps the wires to the plug (`toward`, per pin) from crossing."""
    for slot, k in uncrossed(roots, toward):
        dr.add(wire_end(slot, colours[k], k), slot)


def uncrossed(roots, toward):
    """Pairs (root, wire) that keep straight wires from `roots` to `toward` from crossing."""
    mid = lambda ps: (sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps))
    (ax, ay), (bx, by) = mid(roots), mid(toward)
    across = lambda p: -(by - ay) * p[0] + (bx - ax) * p[1]
    return list(zip(sorted(roots, key=across), sorted(range(len(toward)), key=lambda k: across(toward[k]))))


def round_the_corner(lane, o, e, turn, down, along, radius=2.7):
    """A wire stub that runs on from `lane` the way e, turns a quarter turn toward `turn` and
    stops; the stubs of one cable stay side by side. Returns the rest of its line and its tip."""
    n0 = left_of(e)
    s = 1 if turn == n0 else -1
    lane_c = add(lane, n0, -o)
    corner = add(add(lane_c, e, down - s * o), n0, o)
    r = radius - s * o
    tip = add(corner, turn, along - s * o)
    return f"L{pt(add(corner, e, -r))}Q{pt(corner)} {pt(add(corner, turn, r))}L{pt(tip)}", tip


def flexible(bare: Part, conn_id: str, x, y, turn=0, pin_order=None, corner=None) -> Part:
    """A module ready for a flexible cable: the cable's plug sits in its socket, a short stub of
    each wire leaves it, and the stub ends are its pins. (x, y) is where its drawing goes in
    board millimetres. corner=(turn, down, along) takes the stubs round a corner of the module
    first, where straight wires to the plug would cross the module."""
    sock = modules.SOCKETS[bare.slug]
    pins, d0 = home(conn_id)
    count = len(pins)
    colours = KIT_CABLE_3 if count == 3 else KIT_CABLE_4
    tf, at, turn_dir, corners = placed(bare, x, y, turn)
    keep = {3: 3, 4: 4, 5: 5} if bare.slug == "relay-module" else {}
    dr = Drawing()
    dr.add(g(strip_pins(bare.bb_body, keep), transform=tf), *corners)
    e = turn_dir(sock["exit"])
    far_body, far_legs, far_corners = module_plug(sock, at, e)
    dr.add(far_body, *far_corners)
    stubs = {}                                   # tip of a stub: its leg in the plug and its whole line
    for leg, lane, o in far_legs:
        rest, tip = round_the_corner(lane, o, e, *corner) if corner else (f"L{pt(add(lane, e, TAIL))}", add(lane, e, TAIL))
        stubs[tip] = (leg, leg.out() + rest)
    entries = ends = ""
    for tip, k in uncrossed(list(stubs), plug_tails(pins, d0, colours)):
        leg, line = stubs[tip]
        dr.add(wire(line, colours[k], 0.95), tip)
        entries += wire_entry(leg.start, colours[k])
        ends += wire_end(tip, colours[k], k)
    dr.add(entries + ends)
    size, art_all, origin = dr.finish()
    fixed = cabled(bare, conn_id, x, y, turn, pin_order=pin_order)   # for its pins and footprint only
    return dataclasses.replace(
        fixed, slug=bare.slug + "-flex", module_id=f"makerbuddy-kit-{bare.slug}-flex-{FLEX_REV}",
        title=bare.title.replace(" (MakerBuddy)", ", for a flexible cable (MakerBuddy)"),
        pins=[dataclasses.replace(pin, hybrid=False) for pin in fixed.pins],
        bb_size=size, bb_body=art_all, origin=origin,
        description=(bare.description.replace(" " + SITE, "")
                     + f" This version is for a flexible cable: the cable's plug sits in its socket and its pins are "
                       f"the ends of the {count} wire stubs that leave the plug. Draw Fritzing wires from them to a "
                       "MakerBuddy cable plug, then drag the plug onto the board. " + SITE),
        props={**bare.props, "cable": "flexible (wires to a plug part)"}, in_bin=False, folder="flexible-cable")


def own_lead_flex(fixed: Part, dr: Drawing, roots, colours, what) -> Part:
    pins, d0 = home(fixed.home)
    tails(dr, roots, colours, plug_tails(pins, d0, colours))
    size, body, origin = dr.finish()
    return dataclasses.replace(
        fixed, slug=fixed.slug + "-flex", module_id=f"makerbuddy-kit-{fixed.slug}-flex-{FLEX_REV}",
        title=fixed.title.replace(" on its lead (MakerBuddy)", ", for a flexible lead (MakerBuddy)"),
        pins=[dataclasses.replace(pin, hybrid=False) for pin in fixed.pins],
        bb_size=size, bb_body=body, origin=origin,
        description=(f"{what} This version is for a flexible lead: its pins are the three wire ends of its lead. Draw "
                     "Fritzing wires from them to its lead plug, then drag the plug onto the board. " + SITE),
        props={**fixed.props, "cable": "flexible (wires to a plug part)"}, in_bin=False, folder="flexible-cable")


def servo_flexible() -> Part:
    dr = Drawing()
    fx, fy = 7.0, 96.5
    dr.add(servo_body(fx, fy), (fx, fy - 0.4), (fx + 32.3, fy + 12.6))
    return own_lead_flex(servo(), dr, [(fx + 1.4 + k * 1.25, fy - 0.2) for k in range(3)], ["orange", "red", "brown"],
                         "SG90 9 g micro servo, 0 to 180 degrees: PWM (orange), VCC (red), GND (brown).")


def ds18b20_flexible() -> Part:
    dr = Drawing()
    stub = "M84 1V7"
    dr.add(stroke(stub, "#000000", 4.3, cap="butt") + stroke(stub, "#222226", 3.8, cap="butt"), (82, 1), (86, 7))
    dr.add(path("M81 -12V-42a3 3 0 0 1 6 0V-12Z", "#c9cdd2", stroke="#868c92", stroke_width=0.2)
           + stroke("M82.6 -41V-14", "#f1f3f5", 0.7), (81, -45), (87, -12))
    dr.add(rect(80.4, -13, 7.2, 14.5, "#19191c", rx=0.8, stroke="#000000", stroke_width=0.15), (80.4, -13), (87.6, 1.5))
    return own_lead_flex(ds18b20(), dr, [(84 + (k - 1) * 1.25, 7.5) for k in range(3)], ["yellow", "red", "black"],
                         "DS18B20 digital temperature sensor in a waterproof stainless-steel tube: DQ (yellow), VCC "
                         "(red), GND (black). Drawn with the 1 m lead shortened.")


# ---------------------------------------------------------------- parts with their own lead

def own_lead(slug, title, label, summary, description, tags, props, names, conn_id, dr, origin_size, sch, photo) -> Part:
    size, body, origin = origin_size
    pcb_size, pcb_silk, pads = lead_footprint(3, sch[0].upper()[:9], None)
    pins = [Pin(name, desc, pcb=pads[k], hybrid=True) for k, (name, desc) in enumerate(names)]
    return Part(slug=slug, module_id=f"makerbuddy-kit-{slug}-{REV}", title=title, label=label,
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
    body, entries, legs, corners = board_plug(pins, d0, colours)
    dr = Drawing()
    dr.add(body, *corners)
    fx, fy = 14.0, 106.0                      # the servo's mounting flange, top-left corner
    for (leg, lane, o), colour in zip(legs, colours):
        ex = fx + 3.0 - o * 0.9
        dr.add(wire(leg.out() + f"C{n(lane[0])} {n(lane[1] + 12)} {n(ex)} {n(fy - 11)} {n(ex)} {n(fy + 0.6)}", colour, 0.95))
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
    body, entries, legs, corners = board_plug(pins, d0, colours)
    dr = Drawing()
    dr.add(body, *corners)
    y0 = pins[0][1]
    for (leg, lane, o), colour in zip(legs, colours):
        dr.add(wire(leg.out() + f"C{n(lane[0] + 3)} {n(lane[1])} {n(81)} {n(y0 - o * 0.7)} {n(84)} {n(y0 - o * 0.7)}", colour, 0.95))
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

def kit() -> tuple[list[Part], list[Part]]:
    """The parts of the bin in the order of the board's connectors, and the flexible set (plugs,
    then the parts that take them). Places are in board millimetres."""
    bare = {p.slug: p for p in modules.bare_modules()}
    fixed = [
        ds18b20(),
        cabled(bare["dht11"], "PORT_25", 111, -14, l0=24, l1=8),
        cabled(bare["mq2-gas-sensor"], "PORT_33", 110, 45, l0=24, l1=7),
        cabled(bare["soil-moisture-sensor"], "PORT_32", 83, 58, turn=-90, l0=9, l1=5),
        cabled(bare["relay-module"], "PORT_23", -48, 84, l0=14, l1=9),
        servo(),
        cabled(bare["hc-sr501-pir"], "PORT_18", 48, 80, l0=7, l1=7),
        cabled(bare["hc-sr04"], "HCSR04", -58, -29, l0=12, l1=9, pin_order=[0, 3, 2, 1]),
        cabled(bare["lcd-1602-i2c"], "I2C_1", -104, 20, square=True),
    ]
    flex = [
        ds18b20_flexible(),
        flexible(bare["dht11"], "PORT_25", 92.2, -17.8),
        flexible(bare["mq2-gas-sensor"], "PORT_33", 102.8, 57.1),
        flexible(bare["soil-moisture-sensor"], "PORT_32", 77.3, 68.8, turn=-90),
        flexible(bare["relay-module"], "PORT_23", -55.1, 82.26),
        servo_flexible(),
        flexible(bare["hc-sr501-pir"], "PORT_18", 41.45, 96.0),
        flexible(bare["hc-sr04"], "HCSR04", -40.0, -34.5, pin_order=[0, 3, 2, 1]),
        flexible(bare["lcd-1602-i2c"], "I2C_1", -114.0, 3.5, corner=(RIGHT, 23.6, 77.0)),
    ]
    return fixed, list(plugs().values()) + flex
