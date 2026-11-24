"""The plug-in parts of the MakerBuddy IoT Kit, drawn from the October 2026 product photographs.

Each drawing is in millimetres with a 1 mm clear border. Sizes come from datasheets where a part
is a standard module and are scaled from the photographs where it is not (the green JST adapters).
"""
from __future__ import annotations

import math

from common import (BLUE_PCB, BLUE_PCB_EDGE, BOLD, GREEN_PCB, GREEN_PCB_EDGE, HOUSING, HOUSING_EDGE, HOUSING_IN,
                    METAL, METAL_DARK, METAL_LIGHT, MONO, PAD, PITCH, SILK, Part, Pin, bare_end, cid, jst_plug,
                    jst_socket, mesh, mount_hole, pcb_plate, silk, silk_outline, silk_text, solder_joint, wire)
from svgkit import circle, crect, el, ellipse, g, line, n, path, polygon, rect, stroke

SITE = "https://makerbuddy.cc"
PAD_SCREW = (1.15, 0.8)


def fp(x, y):
    """Drawing coordinates to footprint coordinates (the footprint drops 0.7 of the 1 mm border)."""
    return (x - 0.7, y - 0.7)


def footprint(w, h, name, at, size=1.6, rot_deg=0.0, boxes=()):
    """Module outline, its name and a box around each connector."""
    out = [silk_outline(w - 1.4, h - 1.4), silk_text(name, at[0] - 0.7, at[1] - 0.7, size, rot_deg)]
    for cx, cy, bw, bh in boxes:
        out.append(crect(cx - 0.7, cy - 0.7, bw, bh, "none", stroke="#ffffff", stroke_width=0.2))
    return (w - 1.4, h - 1.4), "".join(out)


def lead_footprint(count, name, labels):
    """Flying-lead parts get a pin-header footprint: a JST-XH outline with 2.54 mm holes."""
    length = PITCH * (count - 1) + 4.9
    w, h = length + 0.6, 5.75 + 3.0
    cy = 3.0 + 5.75 / 2
    out = [rect(0.3, 2.7, length, 5.75, "none", stroke="#ffffff", stroke_width=0.2),
           silk_text(name, w / 2, 1.3, 1.5 if len(name) < 8 else 1.2)]
    pads = [(0.3 + 2.45 + k * PITCH, cy) for k in range(count)]
    return (w, h), "".join(out), pads


def three_pins(sig_name, sig_desc, pads, sig_label=None, vcc="5 V supply"):
    return [Pin(sig_name, sig_desc, label=sig_label or sig_name, pcb=pads[0], kind="female"),
            Pin("VCC", vcc, pcb=pads[1], kind="female"),
            Pin("GND", "Ground", pcb=pads[2], kind="female")]


def socket_pads(cx, cy, order, vertical=False):
    """Footprint pad of each connector number for a 3- or 4-pin socket drawn at (cx, cy)."""
    pads = {}
    for k, i in enumerate(order):
        off = (k - (len(order) - 1) / 2) * PITCH
        pads[i] = fp(cx, cy + off) if vertical else fp(cx + off, cy)
    return [pads[i] for i in sorted(pads)]


def part(slug, title, label, summary, description, tags, props, pins, size, body, pcb, sch, photo) -> Part:
    # one family per kind of part, so Fritzing's Inspector never offers to swap a sensor for a relay
    return Part(slug=slug, module_id=f"makerbuddy-kit-{slug}-r1", title=title, label=label,
                family=f"MakerBuddy {props['type']}",
                summary=summary, description=description + " " + SITE, tags=["MakerBuddy", "IoT Kit"] + tags,
                props=props, pins=pins, bb_size=size, bb_body=body, pcb_size=pcb[0], pcb_silk=pcb[1],
                sch_title=sch, photo=photo)


# ---------------------------------------------------------------- DHT11

def dht11() -> Part:
    w, h = 17.6, 36.1
    ax, ay, cx = 1.0, 13.9, 8.8
    jy = ay + 16.7
    out = [pcb_plate(ax, ay, 15.6, 21.2, GREEN_PCB, GREEN_PCB_EDGE)]
    out += [solder_joint(cx + (k - 1.5) * 2.54, ay + 3.5, 0.75) for k in range(4)]
    for text, x, y in (("VCC", 3.6, 7.0), ("Data", 6.4, 7.4), ("GND", 11.6, 7.0), ("VCC", 7.9, 11.3), ("GND", 5.2, 11.5)):
        out.append(silk(text, ax + x, ay + y, 1.25, 90))
    out.append(silk("DHT", ax + 10.2, ay + 9.4, 1.7, 90))
    out.append(jst_socket(cx, jy, 3, [2, 1, 0], key=-1))
    # the sensor: light-blue grille housing standing over the top of the adapter
    out.append(rect(cx - 6.6, 7.4, 13.2, 1.9, "#4aa3df", stroke="#2f7fb8", stroke_width=0.12))
    out.append(rect(cx - 6, 1.0, 12, 15.5, "#4aa3df", rx=0.8, stroke="#2f7fb8", stroke_width=0.15))
    for r in range(5):
        for c in (-3.6, 0, 3.6):
            out.append(crect(cx + c, 3.0 + r * 2.95, 2.1, 1.9, "#1f5f94", rx=0.2))
    size, silk_art = footprint(w, h, "DHT11", (cx, ay + 9.5), boxes=[(cx, jy, 12.5, 5.75)])
    pins = three_pins("DATA", "Temperature and humidity data (one wire). On the board: connector 25.",
                      socket_pads(cx, jy, [2, 1, 0]))
    return part("dht11", "DHT11 temperature and humidity sensor (MakerBuddy)", "DHT",
                "DHT11 on the green MakerBuddy JST adapter. Home: connector 25.",
                "DHT11 temperature and humidity sensor on the MakerBuddy JST adapter board. 3-pin JST-XH socket: "
                "DATA, VCC, GND. Plugs into connector 25 of the MakerBuddy IoT Kit board with a 3-wire kit cable.",
                ["DHT11", "temperature", "humidity", "sensor"],
                {"type": "temperature and humidity sensor", "sensor": "DHT11", "interface": "single-wire digital",
                 "connector": "JST-XH 3-pin", "board connector": "25"},
                pins, (w, h), "".join(out), (size, silk_art), ["DHT11", "temperature + humidity"], "dht11-sensor")


# ---------------------------------------------------------------- MQ-2

def mq2() -> Part:
    w, h = 22.0, 49.7
    bx, by, gx, gy = 1.0, 16.7, 2.85, 1.0
    jx, jy = bx + 9.5, gy + 4.1
    out = [pcb_plate(gx, gy, 15.1, 16.3, GREEN_PCB, GREEN_PCB_EDGE), jst_socket(jx, jy, 3, [0, 1, 2])]
    for text, x, y, size, r in (("VCC", 9.5, 8.75, 1.2, 90), ("GND", 12.04, 8.75, 1.2, 90), ("MQ-2", 9.5, 11.5, 1.9, 0),
                                ("AD", 6.4, 13.9, 1.2, 90), ("GND", 11.1, 13.6, 1.2, 90), ("VCC", 13.75, 13.3, 1.2, 90)):
        out.append(silk(text, bx + x, gy + y, size, r))
    out.append(pcb_plate(bx, by, 20, 32, BLUE_PCB, BLUE_PCB_EDGE))
    out += [mount_hole(bx + x, by + y, 1.2) for x, y in ((2.2, 1.9), (17.8, 1.9), (2.6, 28.9), (17.6, 28.9))]
    out += [solder_joint(bx + 6.2 + k * 2.54, by + 1.5, 0.75) for k in range(4)]
    out.append(MONO.text("Flying-Fish", bx + 8.4, by + 5.6, 1.85, SILK))
    out += [circle(bx + x, by + y, 0.6, PAD) for x, y in ((16.3, 5.4), (14.0, 8.1), (16.4, 10.5))]
    cx, cy = bx + 10, by + 18.2
    out.append(circle(cx, cy, 9.9, "#c5c9ce", stroke="#7f858b", stroke_width=0.2) + circle(cx, cy, 8.7, "#9da2a8")
               + circle(cx, cy, 8.0, "#b4b8bd") + mesh(cx, cy, 8.0, 0.55, "#7b8087", 0.1)
               + stroke(f"M{n(cx - 7.6)} {n(cy - 5.2)}a9.3 9.3 0 0 1 5.0 -4.6", "#f1f3f5", 0.5))
    size, silk_art = footprint(w, h, "MQ-2", (bx + 10, by + 18), 2.0, boxes=[(jx, jy, 12.5, 5.75)])
    pins = three_pins("AO", "Analog output: rises with smoke and gas. On the board: connector 33 (GPIO 33).",
                      socket_pads(jx, jy, [0, 1, 2]), vcc="5 V supply (the heater draws about 150 mA)")
    return part("mq2-gas-sensor", "MQ-2 gas and smoke sensor (MakerBuddy)", "MQ",
                "MQ-2 module with the MakerBuddy JST adapter. Home: connector 33.",
                "MQ-2 combustible gas and smoke sensor (Flying-Fish module) with the MakerBuddy JST adapter. "
                "3-pin JST-XH socket: AO (printed AD), VCC, GND. Plugs into connector 33 of the MakerBuddy IoT Kit "
                "board. The can gets warm while it works.",
                ["MQ-2", "gas", "smoke", "sensor", "analog"],
                {"type": "gas and smoke sensor", "sensor": "MQ-2", "interface": "analog", "connector": "JST-XH 3-pin",
                 "board connector": "33"},
                pins, (w, h), "".join(out), (size, silk_art), ["MQ-2", "gas + smoke"], "mq2-gas-sensor")


# ---------------------------------------------------------------- relay

def relay() -> Part:
    w, h = 56.8, 19.0
    jx, jy = 52.2, 9.74
    out = [pcb_plate(1, 1, 43, 17, BLUE_PCB, BLUE_PCB_EDGE)]
    out.append(rect(2.3, 2.1, 8.2, 14.8, "#2f6fd0", rx=0.4, stroke="#1d4a94", stroke_width=0.15))
    screws = [(6.1, 4.8), (6.1, 9.5), (6.1, 14.2)]
    for i, (sx, sy) in zip((3, 4, 5), screws):
        out.append(circle(sx, sy, 1.9, METAL_LIGHT, stroke=METAL_DARK, stroke_width=0.15, id=cid(i)))
        out.append(stroke(f"M{n(sx - 1.2)} {n(sy)}h2.4M{n(sx)} {n(sy - 1.2)}v2.4", METAL_DARK, 0.4))
    kx, ky = 10.6, 1.6
    out.append(rect(kx, ky, 19.6, 15.8, "#45a6ea", rx=0.6, stroke="#2a78b4", stroke_width=0.15))
    ink = "#1b5f98"
    out.append(BOLD.text("SONGLE", kx + 11.3, ky + 3.4, 1.7, ink) + circle(kx + 9.6, ky + 8.0, 0.45, ink)
               + MONO.text("10A 250VAC 10A 125VAC", kx + 9.8, ky + 10.3, 1.15, ink)
               + MONO.text("10A 30VDC 10A 28VDC", kx + 9.8, ky + 12.0, 1.15, ink)
               + MONO.text("SRD-05VDC-SL-C", kx + 9.8, ky + 14.0, 1.6, ink))
    for yy in (2.3, 5.4, 8.6):
        out.append(rect(32.4, yy, 4.0, 1.7, "#131316") + rect(32.4, yy, 0.8, 1.7, PAD) + rect(35.6, yy, 0.8, 1.7, PAD))
    out.append(rect(32.4, 14.7, 3.6, 1.4, "#c8452d", rx=0.5))
    out.append(circle(41.6, 3.0, 1.4, "#d83a34", stroke="#8f1d1b", stroke_width=0.12))
    out.append(circle(40.4, 17.0, 1.1, "#3fae4c", stroke="#1f6f2c", stroke_width=0.12))
    out.append(pcb_plate(36.1, 3.8, 19.7, 13.1, GREEN_PCB, GREEN_PCB_EDGE))
    for text, yy in (("IN", 7.2), ("GND", 9.74), ("VCC", 12.28)):
        out.append(solder_joint(38.8, yy, 0.8) + silk(text, 40.6, yy, 1.2, anchor="l"))
    out.append(silk("Relay", 46.2, 15.6, 1.2))
    out.append(rect(45.2, 4.3, 4.0, 9.9, "#18181b", rx=0.2))
    out.append(jst_socket(jx, jy, 3, [0, 1, 2], vertical=True, key=-1))
    size, silk_art = footprint(w, h, "RELAY", (22, 9.5), 2.2, boxes=[(jx, jy, 5.75, 12.5), (6.1, 9.5, 5.2, 14.4)])
    pins = three_pins("IN", "Coil control input, active high. On the board: connector 23 (GPIO 23).",
                      socket_pads(jx, jy, [0, 1, 2], vertical=True), vcc="5 V supply for the coil")
    for pin in pins:
        pin.side = "L"
    for (name, desc), (sx, sy), gap in zip(
            (("NO", "Normally open contact: joined to COM while the relay is on"),
             ("COM", "Common contact"),
             ("NC", "Normally closed contact: joined to COM while the relay is off")), screws, (False, False, False)):
        pins.append(Pin(name, desc, kind="female", side="R", pcb=fp(sx, sy), pad=PAD_SCREW, gap=gap))
    return part("relay-module", "5 V relay module, 1 channel (MakerBuddy)", "K",
                "One-channel 5 V relay (Songle SRD-05VDC-SL-C) with the MakerBuddy JST adapter. Home: connector 23.",
                "Single-channel 5 V relay module (Songle SRD-05VDC-SL-C) with the MakerBuddy JST adapter. "
                "3-pin JST-XH socket: IN, VCC, GND; screw terminals NO, COM, NC. Plugs into connector 23 of the "
                "MakerBuddy IoT Kit board. In the kit it switches the 5 V lamp or the fan motor, never mains.",
                ["relay", "SRD-05VDC-SL-C", "switch", "actuator"],
                {"type": "relay module", "channels": "1", "coil": "5 V", "connector": "JST-XH 3-pin + 3 screw terminals",
                 "board connector": "23"},
                pins, (w, h), "".join(out), (size, silk_art), ["Relay", "5 V, 1 channel"], "relay-module")


# ---------------------------------------------------------------- HC-SR04

def hcsr04() -> Part:
    w, h = 47.0, 22.9
    out = [rect(16.5, 20.6, 6.5, 1.3, GREEN_PCB, stroke=GREEN_PCB_EDGE, stroke_width=0.12),
           pcb_plate(1, 1, 45, 20, BLUE_PCB, BLUE_PCB_EDGE)]
    out += [mount_hole(x, y, 0.85) for x, y in ((2.3, 2.4), (44.6, 2.4), (44.7, 19.6))]
    for cx in (10.1, 36.6):
        cy = 9.7
        out.append(circle(cx, cy, 8.0, "#cdd1d5", stroke="#868c92", stroke_width=0.2) + circle(cx, cy, 6.7, "#34373c")
                   + circle(cx, cy, 3.3, "#6f757b") + mesh(cx, cy, 6.7, 0.75, "#9aa0a6", 0.1))
    out.append(crect(23.5, 3.6, 10.8, 3.6, "#bfc3c8", rx=1.8, stroke="#868c92", stroke_width=0.15))
    out.append(silk("HC-SR04", 23.5, 7.9, 2.0))
    xs = [19.69 + k * 2.54 for k in range(4)]
    for i, (x, name) in enumerate(zip(xs, ("Vcc", "Trig", "Echo", "Gnd"))):
        out.append(circle(x, 19.4, 0.95, PAD))
        out.append(crect(x, 19.4, 0.9, 0.9, METAL, stroke=METAL_DARK, stroke_width=0.1, id=cid(i)))
        out.append(silk(name, x, 17.6, 1.2, 270, anchor="l"))
    out.append(silk("T", 4.6, 18.9, 2.6) + silk("R", 42.4, 18.9, 2.6))
    size, silk_art = footprint(w, h, "HC-SR04", (23.5, 8.0), 2.0, boxes=[(23.5, 19.4, 10.6, 2.6)])
    pins = [Pin("VCC", "5 V supply. Board HC-SR04 connector: VCC.", pcb=fp(xs[0], 19.4)),
            Pin("Trig", "Trigger input: a 10 µs pulse starts a measurement. Board HC-SR04 connector: 15.", pcb=fp(xs[1], 19.4)),
            Pin("Echo", "Echo output: high for as long as the sound travels. Board HC-SR04 connector: 2.", pcb=fp(xs[2], 19.4)),
            Pin("GND", "Ground. Board HC-SR04 connector: GND.", pcb=fp(xs[3], 19.4))]
    return part("hc-sr04", "HC-SR04 ultrasonic distance sensor (MakerBuddy)", "US",
                "HC-SR04 distance sensor, 45 × 20 mm. Home: the HC-SR04 connector (Trig 15, Echo 2).",
                "HC-SR04 ultrasonic distance sensor, 2 cm to 4 m. Pins left to right: Vcc, Trig, Echo, Gnd. On the "
                "MakerBuddy IoT Kit board it uses the HC-SR04 connector, printed VCC GND 2 15: Trig goes to 15 and "
                "Echo to 2, so the two middle wires cross. The kit part carries a 4-pin JST adapter on its back.",
                ["HC-SR04", "ultrasonic", "distance", "sensor"],
                {"type": "distance sensor", "sensor": "HC-SR04", "interface": "trigger + echo", "connector": "4 pins, 2.54 mm",
                 "board connector": "HC-SR04"},
                pins, (w, h), "".join(out), (size, silk_art), ["HC-SR04", "distance"], "hc-sr04-ultrasonic")


# ---------------------------------------------------------------- HC-SR501 PIR

def pir() -> Part:
    w, h = 34.4, 39.0
    by = 14.96
    jx, jy = 16.55, 4.1
    out = [pcb_plate(8.33, 1.0, 14.4, 14.6, GREEN_PCB, GREEN_PCB_EDGE), jst_socket(jx, jy, 3, [0, 1, 2])]
    for text, x, y in (("VCC", 16.55, 8.7), ("GND", 19.09, 8.7), ("VCC", 14.0, 13.4), ("Out", 16.55, 13.4), ("GND", 19.1, 13.4)):
        out.append(silk(text, x, y, 1.2, 90))
    out.append(silk("HC-SR501", 16.55, 11.0, 1.7))
    out.append(rect(1.0, by, 32.4, 23.0, "#f2eee1", rx=0.6, stroke="#3d9a5c", stroke_width=0.25))
    out.append(rect(2.2, by + 1.6, 3.6, 19.8, GREEN_PCB) + rect(28.6, by + 1.6, 3.6, 19.8, GREEN_PCB))
    out += [circle(x, by + 11.3, 1.3, "#f2eee1") + circle(x, by + 11.3, 0.9, "#ffffff") for x in (3.1, 32.0)]
    for x, y in ((3.1, 0.9), (3.1, 2.5), (3.1, 20.4), (3.3, 22.2), (30.4, 1.5), (32.4, 1.5), (31.3, 16.8), (32.0, 18.4), (32.2, 21.7)):
        out.append(circle(x, by + y, 0.45, METAL))
    cx, cy = 17.25, by + 11.5
    out.append(crect(cx, cy, 23.0, 22.4, "#f8f8f6", rx=1.2, stroke="#d5d5cf", stroke_width=0.15))
    out.append(circle(cx, cy, 11.4, "#fcfcfb", stroke="#cfcfc8", stroke_width=0.2))
    facets = [(0.0, 0.0, 2.6)]
    facets += [(5.2 * math.cos(k * math.pi / 3), 5.2 * math.sin(k * math.pi / 3), 2.5) for k in range(6)]
    facets += [(9.1 * math.cos(k * math.pi / 6 + math.pi / 12), 9.1 * math.sin(k * math.pi / 6 + math.pi / 12), 2.2)
               for k in range(12)]
    out += [circle(cx + fx, cy + fy, fr, "#f1f1ee", stroke="#dcdcd6", stroke_width=0.15) for fx, fy, fr in facets]
    size, silk_art = footprint(w, h, "PIR", (cx, cy), 2.4, boxes=[(jx, jy, 12.5, 5.75)])
    pins = three_pins("OUT", "Digital output: high while it sees movement. On the board: connector 18 (GPIO 18).",
                      socket_pads(jx, jy, [0, 1, 2]))
    return part("hc-sr501-pir", "HC-SR501 PIR motion sensor (MakerBuddy)", "PIR",
                "HC-SR501 motion sensor with the MakerBuddy JST adapter. Home: connector 18.",
                "HC-SR501 passive-infrared motion sensor with the MakerBuddy JST adapter. 3-pin JST-XH socket: OUT, "
                "VCC, GND. Plugs into connector 18 of the MakerBuddy IoT Kit board.",
                ["HC-SR501", "PIR", "motion", "sensor"],
                {"type": "motion sensor", "sensor": "HC-SR501", "interface": "digital", "connector": "JST-XH 3-pin",
                 "board connector": "18"},
                pins, (w, h), "".join(out), (size, silk_art), ["HC-SR501", "PIR motion"], "hc-sr501-pir")


# ---------------------------------------------------------------- flying-lead parts

def flying(count, name, labels):
    size, silk_art, pads = lead_footprint(count, name, labels)
    return (size, silk_art), pads


def servo() -> Part:
    w, h = 34.3, 25.4
    cx, cy = 17.15, 18.1
    sx = cx + 5.35
    plug, entries = jst_plug(7.5, 4.3, 3, [0, 1, 2], ["orange", "red", "brown"], up=False)
    out = []
    for k, ((ex, ey), colour) in enumerate(zip(entries, ("orange", "red", "brown"))):
        x0 = 2.6 + k * 1.1
        out.append(wire(f"M{n(ex)} {n(ey - 0.3)}C{n(ex)} 11 {n(x0)} 10 {n(x0)} 13.4", colour))
    out.append(plug)
    out.append(rect(1.0, 12.0, 32.3, 12.2, "#1f4fbf", rx=0.8, stroke="#16388a", stroke_width=0.15))
    for hx in (3.25, 31.05):
        out.append(circle(hx, cy, 1.1, "#ffffff") + rect(hx - 0.4, cy - 0.3, 0.8, 0.6, "#ffffff"))
    out.append(rect(5.9, 11.6, 22.5, 13.0, "#2f6ae0", rx=1.0, stroke="#1c3f96", stroke_width=0.15))
    out.append(circle(sx - 6.6, cy, 2.9, "#3f7bf0", stroke="#1c3f96", stroke_width=0.12)
               + circle(sx, cy, 5.9, "#3f7bf0", stroke="#1c3f96", stroke_width=0.12))
    arm = [(sx, cy - 3.0), (sx - 15.0, cy - 1.7), (sx - 15.0, cy + 1.7), (sx, cy + 3.0)]
    out.append(polygon(arm, "#f6f4ee", stroke="#c2bdb1", stroke_width=0.15, stroke_linejoin="round")
               + circle(sx - 15.0, cy, 1.7, "#f6f4ee", stroke="#c2bdb1", stroke_width=0.15)
               + circle(sx, cy, 3.2, "#f6f4ee", stroke="#c2bdb1", stroke_width=0.15))
    out += [circle(sx - d, cy, 0.4, "#b9b4a8") for d in (5.5, 7.5, 9.5, 11.5, 13.5)]
    out.append(circle(sx, cy, 1.0, METAL, stroke=METAL_DARK, stroke_width=0.12)
               + stroke(f"M{n(sx - 0.6)} {n(cy)}h1.2M{n(sx)} {n(cy - 0.6)}v1.2", METAL_DARK, 0.2))
    pcb, pads = flying(3, "SERVO", ["S", "+", "-"])
    pins = [Pin("PWM", "Control signal (orange wire). On the board: connector 19 (GPIO 19).", label="PWM", pcb=pads[0]),
            Pin("VCC", "5 V supply (red wire)", pcb=pads[1]), Pin("GND", "Ground (brown wire)", pcb=pads[2])]
    return part("sg90-servo", "SG90 micro servo with JST plug (MakerBuddy)", "M",
                "SG90 9 g servo with its lead ending in a 3-pin JST plug. Home: connector 19.",
                "SG90 9 g micro servo, 0 to 180 degrees, with its three-wire lead ending in a JST-XH plug: PWM "
                "(orange), VCC (red), GND (brown). Plugs straight into connector 19 of the MakerBuddy IoT Kit board.",
                ["SG90", "servo", "motor", "actuator"],
                {"type": "micro servo", "model": "SG90", "interface": "PWM", "connector": "JST-XH 3-pin plug",
                 "board connector": "19"},
                pins, (w, h), "".join(out), pcb, ["SG90", "servo"], "sg90-servo-with-horns")


def ds18b20() -> Part:
    w, h = 26.0, 60.0
    tube = "M17 34V4a3 3 0 0 1 6 0V34Z"
    out = [path(tube, "#c9cdd2", stroke="#868c92", stroke_width=0.2), stroke("M18.6 5V32", "#f1f3f5", 0.7)]
    cable = "M20 45V51Q20 57 13 57Q6 57 6 51V26.5"
    plug, entries = jst_plug(6, 12, 3, [0, 1, 2], ["yellow", "red", "black"], up=False)
    for k, ((ex, ey), colour) in enumerate(zip(entries, ("yellow", "red", "black"))):
        x0 = 6 + (k - 1) * 1.0
        out.append(wire(f"M{n(x0)} 28C{n(x0)} 22 {n(ex)} 22 {n(ex)} {n(ey - 0.3)}", colour))
    out.append(stroke(cable, "#000000", 4.3, cap="butt") + stroke(cable, "#222226", 3.8, cap="butt"))
    out.append(rect(16.4, 32, 7.2, 14, "#19191c", rx=0.8, stroke="#000000", stroke_width=0.15))
    out.append(plug)
    pcb, pads = flying(3, "DS18B20", ["D", "+", "-"])
    pins = [Pin("DQ", "1-Wire data (yellow wire). On the board: connector 26, which has the 4.7 k pull-up.", pcb=pads[0]),
            Pin("VCC", "Supply, 3.0 to 5.5 V (red wire)", pcb=pads[1]), Pin("GND", "Ground (black wire)", pcb=pads[2])]
    return part("ds18b20-probe", "DS18B20 waterproof temperature probe with JST plug (MakerBuddy)", "T",
                "Waterproof DS18B20 probe on a 1 m lead with a 3-pin JST plug. Home: connector 26.",
                "DS18B20 digital temperature sensor in a waterproof stainless-steel tube on a lead ending in a JST-XH "
                "plug: DQ (yellow), VCC (red), GND (black). Plugs into connector 26 of the MakerBuddy IoT Kit board, "
                "the connector with the 4.7 k 1-Wire pull-up. Drawn with the lead shortened.",
                ["DS18B20", "temperature", "probe", "1-Wire", "sensor"],
                {"type": "temperature probe", "sensor": "DS18B20", "interface": "1-Wire", "connector": "JST-XH 3-pin plug",
                 "board connector": "26"},
                pins, (w, h), "".join(out), pcb, ["DS18B20", "temperature probe"], "ds18b20-waterproof-probe")


def soil() -> Part:
    w, h = 106.2, 25.0
    out = [path("M1 12.5L13 1H99V24H13Z", "#141416", stroke="#000000", stroke_width=0.2, stroke_linejoin="round"),
           circle(4.4, 12.5, 0.9, "#8d9297")]
    out.append(MONO.text("Capacitive  Soil", 8.0, 8.6, 4.9, SILK, anchor="l"))
    out.append(MONO.text("Moisture Sensor v2.0", 9.4, 16.4, 4.9, SILK, anchor="l"))
    out.append(line(71.2, 2.4, 71.2, 22.6, SILK, 0.3, cap="butt"))
    tan, dark = "#b98d5f", "#232327"
    passive = lambda x, y, c=tan, pw=2.4, ph=1.2: (crect(x, y, pw + 0.9, ph + 0.5, "none", stroke=SILK, stroke_width=0.12)
                                                   + crect(x, y, pw, ph, c) + crect(x - pw / 2 + 0.3, y, 0.6, ph, PAD)
                                                   + crect(x + pw / 2 - 0.3, y, 0.6, ph, PAD))
    for x, y, c in ((82.2, 3.0, tan), (82.2, 5.9, tan), (82.2, 9.4, dark), (82.2, 12.4, "#c0392b"), (82.2, 18.2, tan),
                    (87.2, 21.2, tan), (92.4, 2.6, tan), (92.4, 5.6, tan), (87.6, 17.6, dark), (92.6, 17.6, dark),
                    (92.6, 21.0, dark)):
        out.append(passive(x, y, c))
    out.append(crect(89.6, 11.6, 3.9, 4.9, "#2a2a2f"))
    for k in range(4):
        yy = 9.7 + k * 1.27
        out.append(crect(87.1, yy, 1.3, 0.6, PAD) + crect(92.1, yy, 1.3, 0.6, PAD))
    for text, yy in (("GND", 10.0), ("VCC", 12.5), ("AOUT", 15.0)):
        out.append(silk(text, 97.2, yy, 1.05, anchor="r"))
    out.append(rect(98.0, 7.5, 7.2, 10.0, HOUSING, rx=0.4, stroke=HOUSING_EDGE, stroke_width=0.14))
    for i, yy in zip((2, 1, 0), (10.0, 12.5, 15.0)):
        out.append(rect(100.2, yy - 0.75, 5.0, 1.5, HOUSING_IN))
        out.append(crect(102.4, yy, 3.0, 0.74, METAL, stroke=METAL_DARK, stroke_width=0.1, id=cid(i)))
    size, silk_art = footprint(w, h, "SOIL MOISTURE", (45, 12.5), 2.4, boxes=[(101.6, 12.5, 7.2, 10.0)])
    pads = [fp(101.6, 15.04), fp(101.6, 12.5), fp(101.6, 9.96)]
    pins = three_pins("AOUT", "Analog output: falls as the soil gets wetter. On the board: connector 32 (GPIO 32).",
                      pads, vcc="Supply, 3.3 to 5.5 V")
    return part("soil-moisture-sensor", "Capacitive soil moisture sensor v2.0 (MakerBuddy)", "SM",
                "Capacitive soil moisture blade, 98 × 23 mm, 3-pin JST socket. Home: connector 32.",
                "Capacitive soil moisture sensor v2.0: a corrosion-free blade with its electronics at the top end and "
                "a 3-pin JST socket: GND, VCC, AOUT. Plugs into connector 32 of the MakerBuddy IoT Kit board. Push it "
                "into the soil only as far as the printed line and keep the top end dry.",
                ["soil moisture", "capacitive", "sensor", "analog"],
                {"type": "soil moisture sensor", "sensor": "capacitive v2.0", "interface": "analog",
                 "connector": "JST 3-pin", "board connector": "32"},
                pins, (w, h), "".join(out), (size, silk_art), ["Soil moisture", "capacitive"], "soil-moisture-sensor")


def lcd1602() -> Part:
    w, h = 92.4, 38.0
    px, py = 11.4, 1.0
    out = [rect(1.0, 1.9, 10.9, 15.1, "#176b3a", rx=0.4, stroke=GREEN_PCB_EDGE, stroke_width=0.15)]
    ys = [5.44 + k * 2.54 for k in range(4)]
    for i, yy in zip((1, 0, 3, 2), ys):     # GND, VCC, SDA, SCL from the top, as on a PCF8574 backpack
        out.append(circle(5.06, yy, 0.85, METAL, stroke=METAL_DARK, stroke_width=0.1, id=cid(i))
                   + circle(4.9, yy - 0.15, 0.35, METAL_LIGHT))
    out.append(pcb_plate(px, py, 80, 36, GREEN_PCB, GREEN_PCB_EDGE))
    for hx in (2.5, 77.5):
        for hy in (2.5, 33.5):
            out.append(mount_hole(px + hx, py + hy, 1.5, "#d7a046"))
    names = ["VSS", "VDD", "V0", "RS", "RW", "E", "D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "A", "K"]
    for k, name in enumerate(names):
        x = px + 8.0 + k * 2.54
        out.append(solder_joint(x, py + 2.55, 0.8) + silk(name, x, py + 4.9, 0.8))
    out.append(silk("1", px + 5.9, py + 2.55, 1.5) + silk("16", px + 48.9, py + 2.55, 1.5))
    out.append(rect(px + 4.5, py + 7.3, 71.0, 25.0, "#141416", rx=0.8, stroke="#000000", stroke_width=0.15))
    out.append(rect(px + 5.4, py + 8.3, 69.2, 1.0, "#26262a") + rect(px + 5.4, py + 30.3, 69.2, 1.0, "#26262a"))
    sx, sy = px + 7.75, py + 11.8
    out.append(rect(sx, sy, 64.5, 16.0, "#2231a6"))
    x0, y0 = sx + (64.5 - 56.2) / 2, sy + (16.0 - 11.5) / 2
    for r in range(2):
        for c in range(16):
            out.append(rect(x0 + c * 3.55, y0 + r * 5.95, 2.95, 5.55, "#2c3fc0"))
    size, silk_art = footprint(w, h, "LCD 16x2 I2C", (px + 40, py + 19), 2.6, boxes=[(5.06, 9.25, 2.8, 10.4)])
    pads = {i: fp(5.06, yy) for i, yy in zip((1, 0, 3, 2), ys)}
    pins = [Pin("VCC", "5 V supply", pcb=pads[0], kind="female"), Pin("GND", "Ground", pcb=pads[1], kind="female"),
            Pin("SCL", "I2C clock. On the board: any I2C connector (GPIO 22).", pcb=pads[2], kind="female"),
            Pin("SDA", "I2C data. On the board: any I2C connector (GPIO 21).", pcb=pads[3], kind="female")]
    return part("lcd-1602-i2c", "LCD 16x2 with I2C backpack (MakerBuddy)", "LCD",
                "16 × 2 character LCD, 80 × 36 mm, with a PCF8574 I2C backpack at address 0x27. Home: any I2C connector.",
                "16 x 2 character LCD (HD44780) with a PCF8574 I2C backpack at address 0x27 and the MakerBuddy JST "
                "adapter on its left edge. Four wires: VCC, GND, SCL, SDA. Plugs into any of the three I2C positions "
                "of the MakerBuddy IoT Kit board. The order of the four joints on the adapter tab is taken from the "
                "standard backpack (GND, VCC, SDA, SCL from the top); the names are what matter in Fritzing.",
                ["LCD", "1602", "16x2", "I2C", "PCF8574", "HD44780", "display"],
                {"type": "character LCD", "characters": "16 x 2", "interface": "I2C (PCF8574, 0x27)",
                 "connector": "JST-XH 4-pin", "board connector": "I2C"},
                pins, (w, h), "".join(out), (size, silk_art), ["LCD 16x2", "I2C 0x27"], "lcd-1602-front")


def dc_motor() -> Part:
    w, h = 62.0, 46.0
    fx, fy = 20.5, 21.0
    out = []
    for k in range(4):
        a = 20 + 90 * k
        out.append(ellipse(fx + 10.6, fy - 2.2, 8.6, 6.6, "#ffe11a", stroke="#d6b800", stroke_width=0.2,
                           transform=f"rotate({a} {n(fx)} {n(fy)})"))
    out.append(circle(fx, fy, 5.4, "#ffd400", stroke="#d6b800", stroke_width=0.2) + circle(fx - 1.4, fy - 1.6, 1.6, "#fff08a"))
    mx = 44.0
    out.append(rect(mx + 6.9, 3.0, 1.4, 5.4, METAL, stroke=METAL_DARK, stroke_width=0.1))
    out.append(rect(mx + 5.6, 7.2, 4.0, 1.4, "#e7e9eb", stroke=METAL_DARK, stroke_width=0.1))
    out.append(rect(mx, 8.4, 15.2, 23.6, "#c5c9ce", rx=1.2, stroke="#7f858b", stroke_width=0.2))
    out.append(rect(mx + 1.2, 9.4, 2.2, 21.6, "#e4e7ea") + rect(mx + 11.6, 9.4, 1.4, 21.6, "#a9aeb4"))
    out.append(rect(mx + 1.0, 31.0, 13.2, 2.4, "#f3f1ea", rx=0.4, stroke="#b9b4a8", stroke_width=0.12))
    ends = [(mx + 2.4, "black"), (mx + 12.8, "red")]
    for i, (x, colour) in zip((1, 0), ends):
        out.append(rect(x - 0.5, 33.2, 1.0, 1.8, "#d1b25a"))
        bend = 2.2 if colour == "red" else -2.2
        out.append(wire(f"M{n(x)} 34.6C{n(x)} 38 {n(x + bend)} 38 {n(x + bend)} 41.6", colour, 1.1))
        out.append(bare_end(x + bend, 41.4, i))
    pcb, pads = flying(2, "MOTOR", ["+", "-"])
    pins = [Pin("M+", "Motor lead, red. To the relay's NO terminal; the relay's COM goes to the board's 5V connector.",
                pcb=pads[0]),
            Pin("M-", "Motor lead, black. To GND.", pcb=pads[1])]
    return part("dc-motor-fan", "DC motor with fan (MakerBuddy)", "M",
                "Small 130-size DC motor with a four-blade propeller and two leads. Switched by the relay.",
                "Small brushed DC motor (130 size) with the kit's yellow four-blade propeller and two flying leads. "
                "It is switched by the relay module and powered from the 5V connector of the MakerBuddy IoT Kit "
                "board, never straight from a GPIO pin. Swapping the leads reverses it.",
                ["DC motor", "fan", "propeller", "actuator"],
                {"type": "DC motor with fan", "size": "130", "supply": "3 to 6 V", "connector": "2 flying leads",
                 "board connector": "relay + 5V"},
                pins, (w, h), "".join(out), pcb, ["DC motor", "with fan"], "dc-motor-with-fan")


def lamp() -> Part:
    w, h = 16.0, 43.6
    out = [circle(8, 6.6, 5.4, "#fbfbf4", stroke="#c9c9bd", stroke_width=0.2),
           stroke("M7 10.4V6.6l1 -1.6l1 1.6V10.4", "#a0a39c", 0.25, join="miter"),
           circle(6.2, 4.6, 1.3, "#ffffff"),
           rect(4.6, 10.4, 6.8, 2.6, "#c9cdd2", stroke="#868c92", stroke_width=0.15),
           rect(3.2, 12.8, 9.6, 11.2, "#caa24c", rx=0.6, stroke="#8f6f24", stroke_width=0.15)]
    out += [line(3.3, yy, 12.7, yy, "#8f6f24", 0.2, cap="butt") for yy in (15.0, 17.0, 19.0, 21.0)]
    out.append(rect(2.4, 23.7, 11.2, 1.5, "#a8742f", rx=0.3))
    for i, x, colour, bend in ((1, 6.6, "black", -1.6), (0, 9.4, "orange", 1.6)):
        out.append(rect(x - 0.8, 25.2, 1.6, 3.0, "#caa24c", stroke="#8f6f24", stroke_width=0.12))
        out.append(wire(f"M{n(x)} 27.6C{n(x)} 33 {n(x + bend)} 33 {n(x + bend)} 39.2", colour, 1.1))
        out.append(bare_end(x + bend, 39.0, i))
    pcb, pads = flying(2, "LAMP", ["1", "2"])
    pins = [Pin("L1", "Lamp lead, orange. To the relay's NO terminal; the relay's COM goes to the board's 5V connector.",
                pcb=pads[0]),
            Pin("L2", "Lamp lead, black. To GND.", pcb=pads[1])]
    return part("lamp", "6 V lamp in a holder with leads (MakerBuddy)", "L",
                "Small filament lamp in a brass screw holder with two leads. Switched by the relay.",
                "Small 6 V filament lamp in a brass E10 screw holder with two flying leads. It is switched by the "
                "relay module and powered from the 5V connector of the MakerBuddy IoT Kit board. A filament lamp "
                "works either way round.",
                ["lamp", "bulb", "light", "actuator"],
                {"type": "filament lamp", "rating": "6 V", "holder": "E10 screw", "connector": "2 flying leads",
                 "board connector": "relay + 5V"},
                pins, (w, h), "".join(out), pcb, ["Lamp", "6 V"], "lamp-bulb-with-leads")


def all_modules() -> list[Part]:
    return [dht11(), ds18b20(), mq2(), soil(), hcsr04(), pir(), relay(), servo(), lcd1602(), dc_motor(), lamp()]
