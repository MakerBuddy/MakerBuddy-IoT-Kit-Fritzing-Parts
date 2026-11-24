#!/usr/bin/env python3
"""Builds everything in this repository from the drawings in tools/.

    python3 tools/build.py

Writes svg/ (breadboard, schematic and PCB drawings for any tool), fritzing/ (one .fzpz per part,
the .fzp definitions and the parts bin), examples/ (a wired sketch) and docs/ (pin tables, PCB
previews). Needs Python 3.10+ and fontTools; see README, "Rebuilding".
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import board  # noqa: E402
import modules  # noqa: E402
from common import Part, breadboard_svg, pcb_svg, schematic_svg  # noqa: E402
from fritzing import Sketch, bin_file, bundle_files, connector_centres, fzp, write_zip  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BIN_TITLE = "MakerBuddy IoT Kit"
BIN_NAME = "MakerBuddy-IoT-Kit"


def views(part: Part) -> dict[str, str]:
    return {"breadboard": breadboard_svg(part), "icon": breadboard_svg(part, "icon"),
            "schematic": schematic_svg(part), "pcb": pcb_svg(part)}


def check(part: Part, svgs: dict[str, str]) -> list[str]:
    """What Fritzing needs from a part: every pin drawn once in every view, nothing it cannot read."""
    problems = []
    names = [p.name for p in part.pins]
    if len(set(names)) != len(names):
        problems.append("pin names repeat")
    ET.fromstring(fzp(part).encode())
    layers = {"breadboard": ["breadboard"], "icon": ["icon"], "schematic": ["schematic"],
              "pcb": ["silkscreen", "copper0", "copper1"]}
    for view, svg in svgs.items():
        root = ET.fromstring(svg.encode())
        ids: dict[str, int] = {}
        for node in root.iter():
            tag = node.tag.split("}")[-1]
            if tag in ("text", "style", "use", "image", "linearGradient", "radialGradient", "clipPath", "mask", "filter"):
                problems.append(f"{view}: <{tag}> is not allowed")
            if node.get("id"):
                ids[node.get("id")] = ids.get(node.get("id"), 0) + 1
        problems += [f"{view}: layer {layer} missing" for layer in layers[view] if layer not in ids]
        problems += [f"{view}: id {k} used {v} times" for k, v in ids.items() if v > 1]
        if view == "icon":
            continue
        for i in range(len(part.pins)):
            if f"connector{i}pin" not in ids:
                problems.append(f"{view}: connector{i}pin missing")
            if view == "schematic" and f"connector{i}terminal" not in ids:
                problems.append(f"{view}: connector{i}terminal missing")
        w, h = float(root.get("width")[:-2]), float(root.get("height")[:-2])
        for ident, (x, y) in connector_centres(svg).items():
            if ident.startswith("connector") and not (0 <= x <= w and 0 <= y <= h):
                problems.append(f"{view}: {ident} is outside the drawing")
    return problems


def example(parts: dict[str, Part], svgs: dict[str, dict[str, str]]) -> Sketch:
    """Every kit part beside the purple board, each wired to its home connector."""
    sk = Sketch()
    grid = iter([(c * 400.0, r * 340.0) for r in range(4) for c in range(4)])

    def put(slug, title, bb, turned=False):
        at = next(grid)
        return sk.place(parts[slug], svgs[slug], title, bb, at, at, turned)

    b = put("makerbuddy-iot-kit-v1-purple", "MakerBuddy1", (420, 260))
    three = [("ds18b20-probe", "Probe1", (790, 20), "DQ", "26", False), ("dht11", "DHT1", (900, 120), "DATA", "25", False),
             ("mq2-gas-sensor", "MQ1", (1000, 540), "AO", "33", False),
             ("soil-moisture-sensor", "Soil1", (846.5, 740), "AOUT", "32", True),
             ("relay-module", "Relay1", (215, 610), "IN", "23", False), ("sg90-servo", "Servo1", (430, 600), "PWM", "19", False),
             ("hc-sr501-pir", "PIR1", (600, 600), "OUT", "18", False)]
    placed = {}
    for slug, title, at, sig, port, turned in three:
        m = placed[slug] = put(slug, title, at, turned)
        sk.wire(b, f"{port} SIG", m, sig, "sig")
        sk.wire(b, f"{port} VCC", m, "VCC", "vcc")
        sk.wire(b, f"{port} GND", m, "GND", "gnd")
    us = put("hc-sr04", "Distance1", (150, 110))
    for a, to, colour in (("VCC", "HC-SR04 VCC", "vcc"), ("GND", "HC-SR04 GND", "gnd"), ("Trig", "HC-SR04 15", "trig"),
                          ("Echo", "HC-SR04 2", "echo")):
        sk.wire(us, a, b, to, colour)
    lcd = put("lcd-1602-i2c", "LCD1", (50, 300), turned=True)
    for a, colour in (("VCC", "vcc"), ("GND", "gnd"), ("SCL", "scl"), ("SDA", "sda")):
        sk.wire(lcd, a, b, f"I2C1 {a}", colour)
    # the load: the board's 5V connector feeds COM, the lamp sits between NO and GND
    lamp = put("lamp", "Lamp1", (120, 560))
    relay = placed["relay-module"]
    sk.wire(lamp, "L1", relay, "NO", "load")
    sk.wire(relay, "COM", b, "5V VCC", "load", via=[(200, 722), (20, 722), (20, 232), (720, 232), (720, 300)])
    lead = sk.point(lamp, sk.pin(lamp, "L2"))
    sk.wire(lamp, "L2", b, "5V GND", "gnd", via=[(35, lead[1]), (35, 244), (705, 244)])
    put("dc-motor-fan", "Fan1", (20, 790))
    return sk


def pinout_md(parts: list[Part]) -> str:
    out = ["# Pin tables", "",
           "Generated by `tools/build.py` from the same data as the parts. The number in the first column is the",
           "Fritzing connector (`connector<n>`), which is also the `id` of the pin in every SVG (`connector<n>pin`).", ""]
    for part in parts:
        out += [f"## {part.title}", "", f"`{part.slug}` · {len(part.pins)} pins", "", "| # | Pin | What it is | Net |", "|---|---|---|---|"]
        out += [f"| {i} | {p.name} | {p.desc} | {p.net or ''} |" for i, p in enumerate(part.pins)]
        out.append("")
    return "\n".join(out)


def main() -> int:
    parts = [board.make("purple"), board.make("green")] + modules.all_modules()
    by_slug = {p.slug: p for p in parts}
    for sub in ("svg/breadboard", "svg/schematic", "svg/pcb", "fritzing/parts", "fritzing/fzp", "examples", "docs/pcb"):
        (ROOT / sub).mkdir(parents=True, exist_ok=True)
    all_svgs: dict[str, dict[str, str]] = {}
    everything: dict[str, str] = {}
    failed = False
    for part in parts:
        svgs = all_svgs[part.slug] = views(part)
        problems = check(part, svgs)
        failed |= bool(problems)
        print(f"{'FAIL' if problems else 'ok  '} {part.slug:32} {len(part.pins):3} pins  "
              f"{part.bb_size[0]:.1f} x {part.bb_size[1]:.1f} mm" + "".join(f"\n       {p}" for p in problems))
        for view in ("breadboard", "schematic", "pcb"):
            (ROOT / "svg" / view / f"{part.slug}.svg").write_text(svgs[view])
        dark = svgs["pcb"].replace('<g id="silkscreen">', '<rect width="100%" height="100%" fill="#1f5d3a"/><g id="silkscreen">', 1)
        (ROOT / "docs" / "pcb" / f"{part.slug}.svg").write_text(dark)
        (ROOT / "fritzing" / "fzp" / f"{part.slug}.fzp").write_text(fzp(part))
        files = bundle_files(part, svgs)
        write_zip(ROOT / "fritzing" / "parts" / f"{part.slug}.fzpz", files)
        everything.update(files)
    if failed:
        return 1
    write_zip(ROOT / "fritzing" / f"{BIN_NAME}.fzbz", {**everything, f"{BIN_NAME}.fzb": bin_file(BIN_TITLE, parts)})
    sketch = example(by_slug, all_svgs)
    write_zip(ROOT / "examples" / f"{BIN_NAME}-wiring.fzz", {**everything, f"{BIN_NAME}-wiring.fz": sketch.xml()})
    (ROOT / "docs" / "PINOUT.md").write_text(pinout_md(parts))
    print(f"{len(parts)} parts, {sum(len(p.pins) for p in parts)} pins, {len(sketch.wires)} wire runs in the example sketch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
