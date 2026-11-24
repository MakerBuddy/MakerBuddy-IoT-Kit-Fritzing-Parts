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
from fritzing import PX, Sketch, bin_file, bundle_files, connector_centres, fzp, write_zip  # noqa: E402

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
            if view == "breadboard" and part.pins[i].leg and f"connector{i}leg" not in ids:
                problems.append(f"{view}: connector{i}leg missing")
            if view == "schematic" and f"connector{i}terminal" not in ids:
                problems.append(f"{view}: connector{i}terminal missing")
        w, h = float(root.get("width")[:-2]), float(root.get("height")[:-2])
        for ident, (x, y) in connector_centres(svg).items():
            if ident.startswith("connector") and not (0 <= x <= w and 0 <= y <= h):
                problems.append(f"{view}: {ident} is outside the drawing")
    return problems


def example(parts: dict[str, Part], svgs: dict[str, dict[str, str]]) -> Sketch:
    """The whole kit on the purple board: every cable in its home socket, and the lamp on the
    relay. One wire is drawn: 5 V to the relay's COM terminal."""
    sk = Sketch()
    grid = iter([(c * 420.0, r * 360.0) for r in range(4) for c in range(4)])
    ox, oy = 480.0, 300.0                         # the board's corner on the breadboard page
    mm = lambda x, y: (ox + x * PX, oy + y * PX)  # board millimetres to page units

    def put(slug, title, x, y):
        at = next(grid)
        return sk.place(parts[slug], svgs[slug], title, mm(x, y), at, at)

    b = put("makerbuddy-iot-kit-v1-purple", "MakerBuddy1", -board.M, -board.M)
    placed = {}
    for part in parts.values():
        if not part.home or not part.in_bin:
            continue
        item = placed[part.slug] = put(part.slug, part.label + "1", -part.origin[0], -part.origin[1])
        for k in range(len(board.CONN[part.home]["pins"])):       # lead k ends on socket pin k
            sk.plug(item, k, b, board.WHERE[(part.home, k)])
    # the load: the lamp's orange lead sits in the relay's NO terminal, its black lead goes to GND,
    # and the 5V connector feeds COM
    relay = placed["relay-module"]
    no = sk.point(relay, sk.pin(relay, "NO"))
    lamp_part = parts["lamp"]
    lead = connector_centres(svgs["lamp"]["breadboard"])["connector0end"]
    lamp = sk.place(lamp_part, svgs["lamp"], "Lamp1", (no[0] - lead[0] * PX, no[1] - lead[1] * PX), next(grid), (0, 0))
    sk.plug(lamp, 0, relay, sk.pin(relay, "NO"))
    put("dc-motor-fan", "Fan1", -112, 118)
    l2, com = sk.point(lamp, 1), sk.point(relay, sk.pin(relay, "COM"))
    sk.wire(b, "5V GND", lamp, "L2", "gnd",
            via=[mm(63.2, 9.4), mm(63.2, -52), mm(-106.5, -52), (mm(-106.5, 0)[0], l2[1])])
    sk.wire(b, "5V VCC", relay, "COM", "load",
            via=[mm(64.5, 10.4), mm(64.5, -53.6), mm(-108, -53.6), (mm(-108, 0)[0], com[1])])
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
    flex, fixed, bare = plugin.kit()
    parts = [board.make("purple"), board.make("green")] + flex + modules.loads() + fixed + bare
    by_slug = {p.slug: p for p in parts}
    for sub in ("svg/breadboard", "svg/schematic", "svg/pcb", "fritzing/parts/module-only", "fritzing/parts/fixed-cable",
                "fritzing/fzp", "examples", "docs/pcb"):
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
        folder = ROOT / "fritzing" / "parts" / part.folder
        write_zip(folder / f"{part.slug}.fzpz", files)
        if part.in_bin:
            everything.update(files)
    if failed:
        return 1
    in_bin = [p for p in parts if p.in_bin]
    write_zip(ROOT / "fritzing" / f"{BIN_NAME}.fzbz", {**everything, f"{BIN_NAME}.fzb": bin_file(BIN_TITLE, in_bin)})
    sketch = example(by_slug, all_svgs)
    write_zip(ROOT / "examples" / f"{BIN_NAME}-wiring.fzz", {**everything, f"{BIN_NAME}-wiring.fz": sketch.xml()})
    (ROOT / "docs" / "PINOUT.md").write_text(pinout_md(parts))
    print(f"{len(parts)} parts, {sum(len(p.pins) for p in parts)} pins, {len(sketch.wires)} wire runs in the example sketch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
