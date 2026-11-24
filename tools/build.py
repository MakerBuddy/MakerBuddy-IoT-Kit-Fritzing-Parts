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
import plugin  # noqa: E402
from common import Part, breadboard_svg, pcb_svg, schematic_svg  # noqa: E402
from fritzing import (PX, WIRE_COLOURS, Sketch, bin_file, bundle_files, connector_boxes, connector_centres, fzp,  # noqa: E402
                      write_zip)

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
    problems += solid(part, svgs["breadboard"])
    return problems


MAX_HIT = 0.8     # millimetres: the largest spot on a plug-in part that may start a wire when pressed


def solid(part: Part, breadboard: str) -> list[str]:
    """A part with a plug must move as one piece. Fritzing starts a wire when the mouse is pressed
    inside a connector's box and moves the part when it is pressed anywhere else on it. So on these
    parts a pin that goes into a socket takes no mouse at all (hybrid), and a wire end is a small
    spot. Screw terminals (female) are meant to be wired by hand and stay as they are."""
    if not (part.home or part.folder == "flexible-cable"):
        return []
    problems = []
    boxes = connector_boxes(breadboard)
    plug_pins = (range(len(part.pins) // 2) if part.label == "P" else
                 [i for i, pin in enumerate(part.pins) if pin.kind == "male"] if part.in_bin else [])
    for i in plug_pins:
        if not part.pins[i].hybrid:
            problems.append(f"breadboard: plug pin {part.pins[i].name} would start a wire when pressed (not hybrid)")
    for i, pin in enumerate(part.pins):
        _x, _y, w, h = boxes.get(f"connector{i}pin", (0, 0, 0, 0))
        if pin.kind == "male" and not pin.hybrid and max(w, h) > MAX_HIT:
            problems.append(f"breadboard: {pin.name} is a {w:.2f} x {h:.2f} mm wire target, more than {MAX_HIT}")
    return problems


PLUG_FOR = {"sg90-servo-flex": "servo-lead-plug", "ds18b20-probe-flex": "probe-lead-plug"}
PARKED = 14.0     # millimetres a waiting plug lies in front of its socket


def kit_sketch(parts: dict[str, Part], svgs: dict[str, dict[str, str]], plugged: bool) -> Sketch:
    """The whole kit around the purple board, every sensor cabled to its own plug with Fritzing
    wires. plugged=False leaves each plug lying in front of its socket, to be dragged in;
    plugged=True puts every plug in its socket."""
    sk = Sketch()
    grid = iter([(c * 300.0, r * 300.0) for r in range(6) for c in range(5)])
    ox, oy = 480.0, 300.0                         # the board's corner on the breadboard page
    mm = lambda x, y: (ox + x * PX, oy + y * PX)  # board millimetres to page units

    def put(slug, title, x, y, turn=0):
        at = next(grid)
        return sk.place(parts[slug], svgs[slug], title, mm(x, y), at, at, turn)

    b = put("makerbuddy-iot-kit-v1-purple", "MakerBuddy1", -board.M, -board.M)
    sockets = {k: v for k, v in connector_boxes(svgs[b["part"].slug]["breadboard"]).items() if k.startswith("connector")}
    flex = [p for p in parts.values() if p.home and p.slug.endswith("-flex")]
    items = {p.slug: put(p.slug, p.label + "1", -p.origin[0], -p.origin[1]) for p in flex}
    lamp = put("lamp", "Lamp1", -76, 47)
    put("dc-motor-fan", "Fan1", -118, 118)
    # The plugs go in last, so they lie on top of everything: a press on a plug always reaches
    # the plug, never a sensor or the board that happens to lie under it.
    for part in flex:
        item = items[part.slug]
        pins, d0 = plugin.home(part.home)
        count = len(pins)
        plug = parts[PLUG_FOR.get(part.slug, "cable-plug-3-wire" if count == 3 else "cable-plug-4-wire")]
        turn = 90 if d0 == plugin.DOWN else 0     # the 3-wire plug is drawn for the right-hand row
        shift = 0.0 if plugged else PARKED
        first = connector_centres(svgs[plug.slug]["breadboard"])["connector0pin"]
        fx, fy = Sketch.turned_point(plug, *first, turn)
        p = put(plug.slug, f"Plug {board.CONN[part.home]['label']}", pins[0][0] + d0[0] * shift - fx, pins[0][1] + d0[1] * shift - fy,
                turn)
        colours = plug.props["wires"].split(", ")
        # the plug's own box, which is what Fritzing takes a press on the plug by: seated, it must
        # hide every pin of its socket, so that no press there can pull a wire out of the board
        w, h = (plug.bb_size[::-1] if turn == 90 else plug.bb_size)
        cx, cy = ((v - o) / PX + s / 2 for v, o, s in zip(p["bb"], b["bb"], plug.bb_size))
        for k in range(count if plugged else 0):
            bx, by, bw, bh = sockets[f"connector{board.WHERE[(part.home, k)]}pin"]
            if not (cx - w / 2 <= bx and bx + bw <= cx + w / 2 and cy - h / 2 <= by and by + bh <= cy + h / 2):
                raise SystemExit(f"{plug.slug} at {part.home}: socket pin {k} shows beside the plug")
        for k in range(count):
            # where Fritzing looks when the plug is dropped: the centre of the plug pin. Seated,
            # it must lie inside its own socket pin and no other; waiting, inside none.
            x, y = ((v - o) / PX for v, o in zip(sk.point(p, k), b["bb"]))
            under = [c for c, (bx, by, bw, bh) in sockets.items() if bx <= x <= bx + bw and by <= y <= by + bh]
            want = [f"connector{board.WHERE[(part.home, k)]}pin"] if plugged else []
            if under != want:
                raise SystemExit(f"{plug.slug} at {part.home}: pin {k} lies on {under}, expected {want}")
            if plugged:
                sk.plug(p, k, b, board.WHERE[(part.home, k)])
            WIRE_COLOURS[colours[k]] = {"white": "#f4f4f1", "black": "#404040"}.get(colours[k], plugin.WIRE[colours[k]])
            sk.wire(item, part.pins[k].name, p, plug.pins[count + k].name, colours[k])
    # the load, with plain wires as in the kit: 5 V to COM, the lamp between NO and GND
    relay = items["relay-module-flex"]
    l2, com = sk.point(lamp, sk.pin(lamp, "L2")), sk.point(relay, sk.pin(relay, "COM"))
    sk.wire(lamp, "L1", relay, "NO", "load")
    sk.wire(b, "5V GND", lamp, "L2", "gnd",
            via=[mm(63.2, 9.4), mm(63.2, -52), mm(-120, -52), (mm(-120, 0)[0], l2[1])])
    sk.wire(b, "5V VCC", relay, "COM", "load",
            via=[mm(64.5, 10.4), mm(64.5, -53.6), mm(-121.6, -53.6), (mm(-121.6, 0)[0], com[1])])
    return sk


def pinout_md(parts: list[Part]) -> str:
    out = ["# Pin tables", "",
           "Generated by `tools/build.py` from the same data as the parts. The number in the first column is the",
           "Fritzing connector (`connector<n>`), which is also the `id` of the pin in every SVG (`connector<n>pin`).", ""]
    for part in parts:
        home = f" · plugs into `{board.CONN[part.home]['label']}`" if part.home else ""
        out += [f"## {part.title}", "", f"`{part.slug}` · {len(part.pins)} pins{home}", "",
                "| # | Pin | What it is | Net |", "|---|---|---|---|"]
        out += [f"| {i} | {p.name} | {p.desc} | {p.net or ''} |" for i, p in enumerate(part.pins)]
        out.append("")
    return "\n".join(out)


def main() -> int:
    fixed, flex = plugin.kit()
    parts = [board.make("purple"), board.make("green")] + fixed + modules.loads() + flex
    by_slug = {p.slug: p for p in parts}
    for sub in ("svg/breadboard", "svg/schematic", "svg/pcb", "fritzing/parts/flexible-cable", "fritzing/fzp",
                "examples", "docs/pcb"):
        (ROOT / sub).mkdir(parents=True, exist_ok=True)
    all_svgs: dict[str, dict[str, str]] = {}
    everything: dict[str, str] = {}
    kit_files: dict[str, str] = {}
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
        folder = ROOT / "fritzing" / "parts" / part.folder
        write_zip(folder / f"{part.slug}.fzpz", files)
        if part.in_bin:
            everything.update(files)
        if part.in_bin or part.folder == "flexible-cable" or part.slug.startswith("makerbuddy"):
            kit_files.update(files)
    if failed:
        return 1
    in_bin = [p for p in parts if p.in_bin]
    write_zip(ROOT / "fritzing" / f"{BIN_NAME}.fzbz", {**everything, f"{BIN_NAME}.fzb": bin_file(BIN_TITLE, in_bin)})
    starter = kit_sketch(by_slug, all_svgs, plugged=False)
    write_zip(ROOT / "examples" / f"{BIN_NAME}-starter.fzz", {**kit_files, f"{BIN_NAME}-starter.fz": starter.xml()})
    sketch = kit_sketch(by_slug, all_svgs, plugged=True)
    write_zip(ROOT / "examples" / f"{BIN_NAME}-wiring.fzz", {**kit_files, f"{BIN_NAME}-wiring.fz": sketch.xml()})
    (ROOT / "docs" / "PINOUT.md").write_text(pinout_md(parts))
    print(f"{len(parts)} parts, {sum(len(p.pins) for p in parts)} pins, {len(sketch.wires)} wire runs in the example sketch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
