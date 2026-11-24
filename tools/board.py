"""The MakerBuddy IoT Kit V1.0 board, drawn from the Fritzing geometry of PCB V1.0
(tools/data/board_v1.json) and the October 2026 product photographs."""
from __future__ import annotations

import json
from pathlib import Path

from common import (BOLD, HOLE, HOUSING, METAL, METAL_DARK, METAL_LIGHT, MONO, PAD, SILK, Part, Pin, cid,
                    hole_pad, jst_socket, silk, silk_outline, silk_text, solder_joint)
from svgkit import circle, crect, el, g, line, n, path, rect, stroke

DATA = json.loads((Path(__file__).parent / "data" / "board_v1.json").read_text())
W, H = DATA["BOARD"]["width"], DATA["BOARD"]["height"]
M = 1.0   # room around the board: the sockets on three edges stand a little past it

MASKS = {
    "purple": {"mask": "#47195c", "edge": "#2f0f3e", "trace": "#5d2676"},
    "green": {"mask": "#12795a", "edge": "#0a5540", "trace": "#1a9370"},
}

# what each printed text measures on the photographed board, relative to its Fritzing box
SILK_SCALE = {"title": 1.26, "label": 1.26, "url": 0.71, "legend": 0.71}

COMP = {c["id"]: c for c in DATA["COMPONENTS"]}
CONN = {c["id"]: c for c in DATA["CONNECTORS"]}

# The photographed boards differ from the Fritzing file in one place: the 5V socket is soldered
# one hole to the left (on the two power traces, under the third hole of the VCC row) and "5V"
# is printed to its right.
CONN["PWR_5V"].update(x=58.78, y=13.82, pins=[["VCC", 58.78, 15.21, "VIN", True], ["GND", 58.78, 12.42, "GND"]])
for entry in DATA["SILK"]:
    if entry[0] == "5V":
        entry[1:3] = [62.4, 13.6]

# what is wired to a GPIO on the board itself
ON_BOARD = {4: "buzzer", 5: "push button", 12: "LED", 13: "RGB LED red", 14: "RGB LED green",
            27: "RGB LED blue", 34: "potentiometer", 35: "light sensor (LDR)", 26: "4.7 k pull-up to VCC"}
PORT_HOME = {26: "DS18B20 probe", 25: "DHT11", 33: "MQ-2 gas sensor", 32: "soil moisture sensor",
             23: "relay", 19: "servo", 18: "PIR motion sensor"}


def net_name(net) -> str:
    return {"VIN": "VCC", "GND": "GND", "3V3": "3V3", "EN": "EN"}.get(net, f"GPIO{net}")


def build_pins() -> tuple[list[Pin], dict[tuple[str, int], int]]:
    """Every pluggable pin of the board, and (connector id, pin index) -> connector number."""
    pins: list[Pin] = []
    where: dict[tuple[str, int], int] = {}

    def add(cid_, k, pin: Pin):
        x, y = CONN[cid_]["pins"][k][1], CONN[cid_]["pins"][k][2]
        pin.pcb = (x + 0.3, y + 0.3)
        where[(cid_, k)] = len(pins)
        pins.append(pin)

    def four(cid_, tag, long, names):
        for k, (short, text) in enumerate(names):
            net = CONN[cid_]["pins"][k][3]
            add(cid_, k, Pin(f"{tag} {short}", f"{long}: {text}", kind="female", net=net_name(net),
                             side="L", gap=(k == 0)))

    four("HCSR04", "HC-SR04", "HC-SR04 connector", [("VCC", "5 V"), ("GND", "ground"),
                                                  ("2", "GPIO 2, the sensor's Echo"), ("15", "GPIO 15, the sensor's Trig")])
    four("UART", "UART", "UART connector", [("VCC", "5 V"), ("GND", "ground"), ("TX", "GPIO 17, UART2 TX"),
                                            ("RX", "GPIO 16, UART2 RX")])
    for cid_, tag, note in (("I2C_3", "I2C3", "top I2C position"), ("I2C_2", "I2C2", "middle I2C position"),
                            ("I2C_1", "I2C1", "bottom I2C connector")):
        four(cid_, tag, f"I2C, {note}", [("VCC", "5 V"), ("GND", "ground"), ("SCL", "GPIO 22, I2C clock"),
                                         ("SDA", "GPIO 21, I2C data")])
    add("PWR_5V", 0, Pin("5V VCC", "5V connector: 5 V from the USB socket (the DevKit's VIN pin)",
                         kind="female", net="VCC", side="L", gap=True))
    add("PWR_5V", 1, Pin("5V GND", "5V connector: ground", kind="female", net="GND", side="L"))

    for gpio in (26, 25, 33, 32, 23, 19, 18):
        cid_ = f"PORT_{gpio}"
        extra = " with a 4.7 k pull-up to VCC" if gpio == 26 else ""
        add(cid_, 0, Pin(f"{gpio} SIG", f"Connector {gpio}: signal, GPIO {gpio}{extra}. Home of the {PORT_HOME[gpio]}.",
                         kind="female", net=f"GPIO{gpio}", side="R", gap=True))
        add(cid_, 1, Pin(f"{gpio} VCC", f"Connector {gpio}: 5 V", kind="female", net="VCC", side="R"))
        add(cid_, 2, Pin(f"{gpio} GND", f"Connector {gpio}: ground", kind="female", net="GND", side="R"))

    for cid_, row in (("BREAKOUT_J2", "left"), ("BREAKOUT_J1", "right")):
        for k, (name, _x, _y, net, *_sq) in enumerate(CONN[cid_]["pins"]):
            what = {"3V3": "3.3 V from the DevKit's regulator", "GND": "ground", "VIN": "5 V (the DevKit's VIN pin)",
                    "EN": "ESP32 enable (reset)"}.get(str(net))
            if what is None:
                what = f"GPIO {net}" + (f", also the on-board {ON_BOARD[net]}" if net in ON_BOARD else "")
            add(cid_, k, Pin(f"{name} ({row} row)", f"Breakout hole beside the DevKit's {name} pin: {what}",
                             label=name, kind="female", net=net_name(net), side="B", gap=(k == 0)))
    for cid_, tag, net, text in (("RAIL_VCC", "VCC", "VCC", "5 V"), ("RAIL_GND", "GND", "GND", "ground")):
        for k in range(4):
            add(cid_, k, Pin(f"{tag} rail {k + 1}", f"{tag} row of four holes: {text}", label=tag, kind="female",
                             net=net, side="B", gap=(k == 0)))
    return pins, where


PINS, WHERE = build_pins()


# ---------------------------------------------------------------- breadboard view

def silk_layer() -> str:
    out = []
    dk = COMP["ESP32_DEVKIT"]
    box = lambda c, dw=0.0, dh=0.0: crect(c["x"], c["y"], c["w"] + dw, c["h"] + dh, "none", stroke=SILK, stroke_width=0.18)
    out.append(box(dk, 0.6, 0.6))
    out += [box(c, -0.3, -0.3) for c in DATA["CONNECTORS"] if c["body"] is None]
    out += [box(COMP[k]) for k in ("LDR", "LED1", "RGB_LED")]
    out.append(circle(COMP["BUZZER"]["x"], COMP["BUZZER"]["y"], 6.85, "none", stroke=SILK, stroke_width=0.18))
    for text, x, y, w, _h, rot_deg, role in DATA["SILK"]:
        if role == "title":
            x, y = 37.2, 1.75
        size = SILK_SCALE[role] * w / (len(text) * 0.6)
        out.append(silk(text, x, y, size, rot_deg))
    return "".join(out)


def resistor(c, bands) -> str:
    (_, x1, y1, *_), (_, x2, y2, *_) = c["pins"]
    vertical = abs(x1 - x2) < 0.1
    bw, bh = c["body"]["w"], c["body"]["h"]
    out = [line(x1, y1, x2, y2, METAL, 0.55), solder_joint(x1, y1), solder_joint(x2, y2),
           crect(c["x"], c["y"], bw, bh, "#4c9fd8", rx=1.0, stroke="#2c6fa3", stroke_width=0.12)]
    length = bh if vertical else bw
    for k, colour in enumerate(bands):
        off = (k - (len(bands) - 1) / 2) * length * 0.16
        out.append(crect(c["x"], c["y"] + off, bw - 0.14, 0.5, colour) if vertical
                   else crect(c["x"] + off, c["y"], 0.5, bh - 0.14, colour))
    return "".join(out)


def devkit() -> str:
    """The 30-pin ESP32 DevKit in its sockets, USB socket up."""
    c = COMP["ESP32_DEVKIT"]
    w, h = c["body"]["w"], c["body"]["h"]
    x0, y0 = c["x"] - w / 2, c["y"] - h / 2
    X = lambda v: x0 + v
    Y = lambda v: y0 + v
    black, part, white = "#17171a", "#0c0c0e", "#f1f1f1"
    out = [rect(x0, y0, w, h, black, rx=2.2, stroke="#000000", stroke_width=0.12)]
    for hx, hy in c["holes"]:
        out.append(circle(hx, hy, 1.95, "#3a3a40") + circle(hx, hy, 1.5, "#2a1038"))
    # ESP-WROOM-32 module: board, castellated pads, shield, antenna
    out.append(rect(X(4.8), Y(25.6), 18.8, 25.4, "#101013", rx=0.3, stroke="#2e2e33", stroke_width=0.1))
    for k in range(14):
        yy = Y(27.3 + k * 1.27)
        out.append(crect(X(4.75), yy, 1.0, 0.7, PAD) + crect(X(23.65), yy, 1.0, 0.7, PAD))
    for k in range(10):
        out.append(crect(X(8.5 + k * 1.27), Y(25.5), 0.7, 1.0, PAD))
    out.append(rect(X(5.95), Y(26.65), 16.6, 17.6, "#4d4f58", rx=0.5, stroke="#8d9099", stroke_width=0.2))
    out.append(circle(X(19.8), Y(28.7), 0.4, "#1d1d21"))
    cx = X(14.25)
    out.append(BOLD.text("ESP-32", cx, Y(40.0), 3.0, "#c8c9cf", rot_deg=180))
    out.append(MONO.text("WiFi+BT SoC Inside", cx, Y(34.4), 1.15, "#c8c9cf", rot_deg=180))
    out.append(MONO.text("ISM2.4G 802.11/b/g/n", cx, Y(32.2), 1.05, "#c8c9cf", rot_deg=180))
    ant = (f"M{n(X(6.2))} {n(Y(49.9))}V{n(Y(46.0))}H{n(X(9.2))}V{n(Y(49.0))}H{n(X(11.6))}V{n(Y(46.0))}"
           f"H{n(X(14.0))}V{n(Y(49.0))}H{n(X(16.4))}V{n(Y(46.0))}H{n(X(18.8))}V{n(Y(49.0))}H{n(X(22.3))}V{n(Y(45.2))}")
    out.append(stroke(ant, "#3b3b41", 0.55, cap="square", join="miter"))
    # USB socket and the two buttons
    out.append(rect(X(10.4), Y(-0.5), 7.5, 5.7, "#c3c7cc", rx=0.5, stroke=METAL_DARK, stroke_width=0.12))
    out.append(rect(X(11.3), Y(0.4), 5.7, 2.2, "#565a60", rx=0.3))
    out.append(rect(X(12.0), Y(3.9), 4.3, 0.8, METAL_DARK))
    for bx, name, tx in ((5.75, "BOOT", 8.3), (21.95, "EN", 19.3)):
        out.append(crect(X(bx), Y(3.5), 3.1, 4.3, "#c3c7cc", rx=0.3, stroke=METAL_DARK, stroke_width=0.12))
        out.append(circle(X(bx), Y(3.5), 0.95, "#55585e"))
        out.append(MONO.text(name, X(tx), Y(3.4), 1.35, white, rot_deg=90))
    # small parts, as blocks
    for a, b in ((4.3, 7.7), (7.9, 11.1), (16.0, 18.9), (19.7, 23.1)):
        out.append(rect(X(a), Y(7.5), b - a, 1.3, part, stroke=white, stroke_width=0.1))
    out.append(rect(X(12.9), Y(7.5), 2.6, 1.3, "#c08a5a", stroke=white, stroke_width=0.1))
    out.append(crect(X(8.05), Y(12.3), 5.4, 5.4, part, rx=0.2))          # USB-serial chip
    for k in range(6):
        t = -2.0 + k * 0.8
        out.append(crect(X(8.05 + t), Y(9.5), 0.35, 0.5, PAD) + crect(X(8.05 + t), Y(15.1), 0.35, 0.5, PAD)
                   + crect(X(5.25), Y(12.3 + t), 0.5, 0.35, PAD) + crect(X(10.85), Y(12.3 + t), 0.5, 0.35, PAD))
    for k in range(3):                                                 # 3.3 V regulator
        out.append(rect(X(14.7), Y(10.0 + k * 2.3), 2.3, 1.1, PAD))
    out.append(rect(X(16.9), Y(9.3), 3.7, 6.7, part, rx=0.2))
    out.append(rect(X(20.6), Y(10.6), 2.0, 4.1, "#c3c7cc"))
    out.append(rect(X(18.0), Y(16.8), 4.6, 2.1, "#e3a03c", rx=0.2, stroke="#9a6a1f", stroke_width=0.1))
    for sx in (7.7, 13.7):
        out.append(crect(X(sx), Y(17.9), 1.5, 2.6, part) + crect(X(sx - 1.2), Y(17.9), 0.9, 0.5, PAD)
                   + crect(X(sx + 1.2), Y(17.2), 0.9, 0.5, PAD) + crect(X(sx + 1.2), Y(18.6), 0.9, 0.5, PAD))
    for k in range(6):
        out.append(rect(X(8.6 + k * 1.75), Y(20.2), 1.2, 3.1, part, stroke=white, stroke_width=0.1))
    for yy in (20.4, 22.2):
        out.append(rect(X(4.3), Y(yy), 3.6, 1.2, part, stroke=white, stroke_width=0.1))
        out.append(rect(X(19.4), Y(yy), 3.7, 1.2, "#c08a5a", stroke=white, stroke_width=0.1))
    # the two pin rows with their printed names (text runs down the board, as printed)
    for k, (name, px, py, *_rest) in enumerate(c["pins"]):
        left = k < 15
        out.append(crect(px, py, 1.7, 1.7, PAD) if k in (0, 15) else circle(px, py, 0.9, PAD))
        out.append(circle(px, py, 0.5, METAL_DARK) + circle(px - 0.12, py - 0.12, 0.22, METAL_LIGHT))
        out.append(MONO.text(name, px + (1.85 if left else -1.75), py, 1.3 if len(name) > 2 else 1.4, white, rot_deg=90))
    return "".join(out)


def bodies() -> str:
    out = []
    c = COMP["C_BULK"]
    out.append(circle(c["x"], c["y"], 4.0, "#1d1d21", stroke="#000000", stroke_width=0.12)
               + path(f"M{n(c['x'] - 3.9)} {n(c['y'] - 0.9)}A4 4 0 0 0 {n(c['x'] - 3.9)} {n(c['y'] + 0.9)}", "none",
                      stroke="#c9ccd0", stroke_width=0.5)
               + circle(c["x"], c["y"], 3.0, "#c5c9ce")
               + stroke(f"M{n(c['x'] - 2.1)} {n(c['y'])}h4.2M{n(c['x'])} {n(c['y'] - 2.1)}v4.2", "#8e9399", 0.25))
    out.append(resistor(COMP["R_1WIRE"], ["#f2c230", "#7d3fb5", "#1b1b1b", "#7a4a25", "#7a4a25"]))
    out.append(resistor(COMP["R_LDR"], ["#7a4a25", "#1b1b1b", "#1b1b1b", "#d6322f", "#7a4a25"]))
    c = COMP["RGB_LED"]
    for _nm, px, py, *_r in c["pins"]:
        out.append(solder_joint(px, py, 0.7))
    out.append(circle(c["x"], c["y"], 2.5, "#f2f0ea", stroke="#c5c0b4", stroke_width=0.15)
               + circle(c["x"] - 0.7, c["y"] - 0.7, 0.8, "#ffffff"))
    c = COMP["LDR"]
    for _nm, px, py, *_r in c["pins"]:
        out.append(solder_joint(px, py, 0.7))
    lx, ly = c["x"], c["y"]
    zig = f"M{n(lx - 1.5)} {n(ly - 1.4)}" + "".join(
        f"h3v0.56h-3v0.56" for _ in range(2)) + "h3v0.56h-3"
    out.append(circle(lx, ly, 2.5, "#eadfc4", stroke="#b4a482", stroke_width=0.15) + stroke(zig, "#c0483a", 0.24, join="miter"))
    c = COMP["LED1"]
    for _nm, px, py, *_r in c["pins"]:
        out.append(solder_joint(px, py, 0.7))
    out.append(circle(c["x"], c["y"], 2.5, "#2b63d9", stroke="#1b3f94", stroke_width=0.15)
               + circle(c["x"], c["y"], 1.7, "#3f79ea") + circle(c["x"] - 0.7, c["y"] - 0.7, 0.6, "#a9c4fb"))
    c = COMP["RV_POT"]
    out.append(crect(c["x"], c["y"], 7.0, 6.5, "#cfd3d7", rx=0.4, stroke=METAL_DARK, stroke_width=0.12)
               + crect(c["x"], c["y"], 5.6, 5.2, "#f4f2ec", rx=0.3)
               + circle(c["x"] - 0.3, c["y"], 2.45, "#f08a1c", stroke="#b25f0c", stroke_width=0.12)
               + stroke(f"M{n(c['x'] - 2.1)} {n(c['y'])}h3.6M{n(c['x'] - 0.3)} {n(c['y'] - 1.8)}v3.6", "#ffffff", 0.6))
    c = COMP["BUZZER"]
    out.append(circle(c["x"], c["y"], 6.0, "#1f1f24", stroke="#000000", stroke_width=0.12)
               + circle(c["x"], c["y"], 5.2, "#2b2b31") + circle(c["x"], c["y"], 0.95, "#08080a")
               + circle(c["x"] + 1.9, c["y"] - 3.4, 0.85, "none", stroke="#55555c", stroke_width=0.15)
               + stroke(f"M{n(c['x'] + 1.4)} {n(c['y'] - 3.4)}h1M{n(c['x'] + 1.9)} {n(c['y'] - 3.9)}v1", "#55555c", 0.15))
    c = COMP["SW_BUTTON"]
    out.append(crect(c["x"], c["y"], 6.0, 6.0, "#cdd1d5", rx=0.4, stroke=METAL_DARK, stroke_width=0.12))
    for sx in (-2.15, 2.15):
        for sy in (-2.15, 2.15):
            out.append(circle(c["x"] + sx, c["y"] + sy, 0.55, "#1b1b1f"))
    out.append(circle(c["x"], c["y"], 1.8, "#f6f4ee", stroke="#b9b4a8", stroke_width=0.15))
    return "".join(out)


def connectors_layer() -> str:
    out = []
    for c in DATA["CONNECTORS"]:
        idx = [WHERE[(c["id"], k)] for k in range(len(c["pins"]))]
        if c["body"] is None:
            out += [hole_pad(p[1], p[2], idx[k], square=len(p) > 4) for k, p in enumerate(c["pins"])]
            continue
        vertical = abs(c["pins"][0][1] - c["pins"][-1][1]) < 0.1
        order = sorted(range(len(idx)), key=lambda k: c["pins"][k][2 if vertical else 1])
        # signal, VCC, GND read left to right with the keyed wall below; turned, the wall is on the left
        key = -1 if (vertical and len(idx) == 3) else 1
        out.append(jst_socket(c["x"], c["y"], len(idx), [idx[k] for k in order], vertical=vertical, key=key))
    return "".join(out)


def breadboard(mask: str) -> tuple[tuple[float, float], str]:
    col = MASKS[mask]
    traces = "".join(stroke(t["d"], col["trace"], t["w"], join="miter") for t in DATA["TRACES"])
    body = (rect(0, 0, W, H, col["mask"], stroke=col["edge"], stroke_width=0.2) + traces + silk_layer()
            + devkit() + bodies() + connectors_layer())
    return (W + 2 * M, H + 2 * M), g(body, transform=f"translate({n(M)},{n(M)})")


# ---------------------------------------------------------------- footprint

def footprint() -> tuple[tuple[float, float], str]:
    o = 0.3
    out = [silk_outline(W + 2 * o, H + 2 * o)]
    out.append(silk_text("MakerBuddy IoT Kit V1.0", o + 37.2, o + 2.0, 2.4))
    dk = COMP["ESP32_DEVKIT"]
    out.append(crect(o + dk["x"], o + dk["y"], dk["w"] + 0.6, dk["h"] + 0.6, "none", stroke="#ffffff", stroke_width=0.2))
    out.append(silk_text("ESP32 DevKit", o + dk["x"], o + dk["y"], 2.0, rot_deg=90))
    for c in DATA["CONNECTORS"]:
        b = c["body"] or {"w": c["w"], "h": c["h"]}
        if c["kind"] != "breakout":
            out.append(crect(o + c["x"], o + c["y"], b["w"], b["h"], "none", stroke="#ffffff", stroke_width=0.2))
    for hole in DATA["HOLES"]:
        out.append(circle(o + hole["x"], o + hole["y"], hole["drill"] / 2, "none", stroke="#ffffff", stroke_width=0.2))
    for text, x, y, w, _h, rot_deg, role in DATA["SILK"]:
        if role == "label" and text not in ("Push BTN", "RGB", "Cap", "34-Potentio", "35-LDR", "12-LED", "10K", "4.7K",
                                            "4-Buzzer", "5V"):
            out.append(silk_text(text, o + x, o + y, SILK_SCALE[role] * w / (len(text) * 0.6), rot_deg))
    return (W + 2 * o, H + 2 * o), "".join(out)


def make(mask: str) -> Part:
    size, body = breadboard(mask)
    pcb_size, pcb_silk = footprint()
    other = "green" if mask == "purple" else "purple"
    return Part(
        slug=f"makerbuddy-iot-kit-v1-{mask}",
        module_id=f"makerbuddy-iot-kit-v1-0-{mask}-r1",
        title=f"MakerBuddy IoT Kit V1.0 ({mask})",
        label="MB",
        family="MakerBuddy IoT Kit board",
        summary="The kit's ESP32 carrier board, 76 × 72.3 mm, with every connector as a Fritzing pin.",
        photo=f"{mask}-board-top + the V1.0 Fritzing PCB",
        description=(
            f"MakerBuddy IoT Kit V1.0 learning board, {mask} soldermask (the {other} board is the same design). "
            "A 30-pin ESP32 DevKit sits in the middle of a 76 × 72.3 mm carrier with seven 3-pin connectors "
            "(26, 25, 33, 32, 23, 19, 18: signal, VCC, GND), an HC-SR04 connector (VCC, GND, 2, 15), a UART connector "
            "(VCC, GND, TX 17, RX 16), three I2C positions (VCC, GND, SCL 22, SDA 21), a 5V connector, VCC and GND rows, "
            "and a row of breakout holes beside each DevKit pin row. VCC is the DevKit's VIN pin: 5 V from USB. "
            "On the board itself: push button (GPIO 5), LED (12), RGB LED (13, 14, 27), potentiometer (34), "
            "light sensor (35), buzzer (4) and a 4.7 k pull-up on connector 26. https://makerbuddy.cc"),
        tags=["MakerBuddy", "IoT Kit", "ESP32", "ESP32 DevKit", "learning board", "JST-XH", "microcontroller"],
        props={"type": "ESP32 carrier board", "soldermask": mask, "revision": "PCB V1.0", "size": "76 x 72.3 mm",
               "processor": "ESP32 (30-pin DevKit)", "supply": "5 V over USB"},
        pins=PINS,
        bb_size=size, bb_body=body, pcb_size=pcb_size, pcb_silk=pcb_silk,
        sch_title=["MakerBuddy IoT Kit V1.0", "ESP32 DevKit carrier"],
    )
