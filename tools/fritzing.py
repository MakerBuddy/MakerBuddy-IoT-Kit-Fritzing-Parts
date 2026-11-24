"""Fritzing files: part definitions (.fzp), part bundles (.fzpz), the parts bin (.fzbz) and a
sketch (.fzz) that shows every part wired to its home connector."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from xml.sax.saxutils import escape, quoteattr

from common import Part

FRITZING_VERSION = "1.0.2"
DATE = "2026-11-24"
AUTHOR = "MakerBuddy (https://makerbuddy.cc)"
PX = 90 / 25.4   # Fritzing sketch units (1/90 inch) per millimetre


def image(part: Part, view: str) -> str:
    return f"{part.slug}_{view}.svg"


def fzp(part: Part) -> str:
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<module fritzingVersion="{FRITZING_VERSION}" moduleId={quoteattr(part.module_id)} '
           f'referenceFile={quoteattr(part.slug + ".fzp")}>',
           " <version>1</version>",
           f" <author>{escape(AUTHOR)}</author>",
           f" <title>{escape(part.title)}</title>",
           f" <label>{escape(part.label)}</label>",
           f" <date>{DATE}</date>",
           " <url>https://github.com/MakerBuddy/MakerBuddy-IoT-Kit-Fritzing-Parts</url>",
           " <tags>"]
    out += [f"  <tag>{escape(t)}</tag>" for t in part.tags]
    out += [" </tags>", " <properties>", f'  <property name="family">{escape(part.family)}</property>']
    out += [f"  <property name={quoteattr(k)}>{escape(v)}</property>" for k, v in part.props.items()]
    out += [" </properties>", f" <description>{escape(part.description)}</description>", " <views>"]
    for view, layers in (("icon", ["icon"]), ("breadboard", ["breadboard"]), ("schematic", ["schematic"]),
                         ("pcb", ["copper0", "silkscreen", "copper1"])):
        out.append(f'  <{view}View>')
        out.append(f'   <layers image="{view}/{image(part, view)}">')
        out += [f'    <layer layerId="{layer}"/>' for layer in layers]
        out += ["   </layers>", f"  </{view}View>"]
    out += [" </views>", " <connectors>"]
    for i, pin in enumerate(part.pins):
        out += [f'  <connector id="connector{i}" name={quoteattr(pin.name)} type="{pin.kind}">',
                f"   <description>{escape(pin.desc)}</description>",
                "   <views>",
                f'    <breadboardView><p layer="breadboard" svgId="connector{i}pin"/></breadboardView>',
                f'    <schematicView><p layer="schematic" svgId="connector{i}pin" terminalId="connector{i}terminal"/></schematicView>',
                f'    <pcbView><p layer="copper0" svgId="connector{i}pin"/><p layer="copper1" svgId="connector{i}pin"/></pcbView>',
                "   </views>",
                "  </connector>"]
    out += [" </connectors>", " <buses>"]
    nets: dict[str, list[int]] = {}
    for i, pin in enumerate(part.pins):
        if pin.net:
            nets.setdefault(pin.net, []).append(i)
    for net, members in nets.items():
        if len(members) > 1:
            out.append(f'  <bus id={quoteattr(net)}>')
            out += [f'   <nodeMember connectorId="connector{i}"/>' for i in members]
            out.append("  </bus>")
    out += [" </buses>", "</module>", ""]
    return "\n".join(out)


def bundle_files(part: Part, svgs: dict[str, str]) -> dict[str, str]:
    """The files of one part as Fritzing names them inside a bundle."""
    files = {f"part.{part.slug}.fzp": fzp(part)}
    for view in ("icon", "breadboard", "schematic", "pcb"):
        files[f"svg.{view}.{image(part, view)}"] = svgs[view]
    return files


def write_zip(path, files: dict[str, str]) -> None:
    """A zip with fixed timestamps, so a rebuild with no changes produces the same bytes."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 24, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, files[name])


def bin_file(title: str, parts: list[Part]) -> str:
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<module fritzingVersion="{FRITZING_VERSION}" icon="Custom1.png">',
           f" <title>{escape(title)}</title>", " <instances>"]
    for k, part in enumerate(parts):
        out += [f'  <instance moduleIdRef={quoteattr(part.module_id)} modelIndex="{k + 1}" path="part.{part.slug}.fzp">',
                "   <views/>", "  </instance>"]
    out += [" </instances>", "</module>", ""]
    return "\n".join(out)


# ---------------------------------------------------------------- reading the drawings back

_TRANSLATE = re.compile(r"translate\(\s*(-?[\d.]+)[ ,]+(-?[\d.]+)\s*\)")


def connector_centres(svg: str) -> dict[str, tuple[float, float]]:
    """Centre of every element with an id, following translate() on its groups."""
    root = ET.fromstring(svg.encode())
    found: dict[str, tuple[float, float]] = {}

    def walk(node, dx, dy):
        m = _TRANSLATE.search(node.get("transform", ""))
        if m:
            dx, dy = dx + float(m.group(1)), dy + float(m.group(2))
        tag = node.tag.split("}")[-1]
        ident = node.get("id")
        if ident:
            a = lambda k: float(node.get(k, 0))
            if tag == "rect":
                found[ident] = (dx + a("x") + a("width") / 2, dy + a("y") + a("height") / 2)
            elif tag == "circle":
                found[ident] = (dx + a("cx"), dy + a("cy"))
            elif tag == "line":
                found[ident] = (dx + (a("x1") + a("x2")) / 2, dy + (a("y1") + a("y2")) / 2)
            else:
                found[ident] = (dx, dy)
        for child in node:
            walk(child, dx, dy)

    walk(root, 0.0, 0.0)
    return found


# ---------------------------------------------------------------- sketch

WIRE_COLOURS = {"sig": "#f2c230", "vcc": "#cc1414", "gnd": "#404040", "scl": "#418dd9", "sda": "#47cc79",
                "trig": "#ef6100", "echo": "#8c3ac9", "load": "#cc1414"}


class Sketch:
    """A Fritzing sketch with parts placed in all three views and wires in the breadboard view."""

    def __init__(self):
        self.items: list[dict] = []
        self.wires: list[dict] = []
        self.index = 5000

    def _next(self) -> int:
        self.index += 1
        return self.index

    @staticmethod
    def turned_point(part: Part, cx: float, cy: float, turn: int) -> tuple[float, float]:
        """A point of a part's drawing (millimetres) after Fritzing turns the part clockwise about
        its centre by `turn` degrees: 0, 90 or 180. The part's corner stays where it was."""
        w, h = part.bb_size
        if turn == 90:
            return (w + h) / 2 - cy, (h - w) / 2 + cx
        if turn == 180:
            return w - cx, h - cy
        return cx, cy

    def place(self, part: Part, svgs: dict[str, str], title: str, bb, sch, pcb, turn: int = 0) -> dict:
        """`turn` puts the part in the breadboard view turned clockwise by 0, 90 or 180 degrees."""
        item = {"part": part, "title": title, "bb": bb, "sch": sch, "pcb": pcb, "index": self._next(),
                "centres": connector_centres(svgs["breadboard"]), "links": {}, "turn": turn}
        self.items.append(item)
        return item

    def pin(self, item: dict, name: str) -> int:
        for i, p in enumerate(item["part"].pins):
            if p.name == name:
                return i
        raise KeyError(f"{item['part'].slug} has no pin {name}")

    def point(self, item: dict, i: int) -> tuple[float, float]:
        cx, cy = self.turned_point(item["part"], *item["centres"][f"connector{i}pin"], item["turn"])
        return item["bb"][0] + cx * PX, item["bb"][1] + cy * PX

    def wire(self, a: dict, a_pin: str, b: dict, b_pin: str, colour: str, via=()) -> None:
        """A wire from pin to pin, bent at each point in `via` (one Fritzing wire per straight run)."""
        ia, ib = self.pin(a, a_pin), self.pin(b, b_pin)
        points = [self.point(a, ia), *via, self.point(b, ib)]
        runs = [{"index": self._next(), "p1": points[k], "p2": points[k + 1], "colour": WIRE_COLOURS[colour],
                 "ends": [None, None]} for k in range(len(points) - 1)]
        for k, run in enumerate(runs):
            run["ends"][0] = ((f"connector{ia}", a["index"], "breadboard") if k == 0
                              else ("connector1", runs[k - 1]["index"], "breadboardWire"))
            run["ends"][1] = ((f"connector{ib}", b["index"], "breadboard") if k == len(runs) - 1
                              else ("connector0", runs[k + 1]["index"], "breadboardWire"))
        a["links"].setdefault(ia, []).append(("connector0", runs[0]["index"], "breadboardWire"))
        b["links"].setdefault(ib, []).append(("connector1", runs[-1]["index"], "breadboardWire"))
        self.wires += runs

    def plug(self, a: dict, ia: int, b: dict, ib: int) -> None:
        """Pin `ia` of part a sits on pin `ib` of part b: joined with no wire, as a plug in a socket."""
        a["links"].setdefault(ia, []).append((f"connector{ib}", b["index"], "breadboard"))
        b["links"].setdefault(ib, []).append((f"connector{ia}", a["index"], "breadboard"))

    def xml(self) -> str:
        out = ['<?xml version="1.0" encoding="UTF-8"?>', f'<module fritzingVersion="{FRITZING_VERSION}">',
               " <views>",
               '  <view name="breadboardView" backgroundColor="#ffffff" gridSize="0.1in" showGrid="1" alignToGrid="0" viewFromBelow="0"/>',
               '  <view name="schematicView" backgroundColor="#ffffff" gridSize="0.1in" showGrid="1" alignToGrid="1" viewFromBelow="0"/>',
               '  <view name="pcbView" backgroundColor="#333333" gridSize="0.1in" showGrid="1" alignToGrid="1" viewFromBelow="0"/>',
               " </views>", " <instances>"]
        for z, item in enumerate(self.items):
            part = item["part"]
            out += [f'  <instance moduleIdRef={quoteattr(part.module_id)} modelIndex="{item["index"]}" path="part.{part.slug}.fzp">',
                    f"   <title>{escape(item['title'])}</title>", "   <views>",
                    '    <breadboardView layer="breadboard">']
            geometry = f'<geometry z="{2.5 + z * 0.001:.4f}" x="{item["bb"][0]:.3f}" y="{item["bb"][1]:.3f}"'
            if item["turn"]:
                w, h = part.bb_size[0] * PX, part.bb_size[1] * PX
                m = ((0, 1, -1, 0, (w + h) / 2, (h - w) / 2) if item["turn"] == 90 else (-1, 0, 0, -1, w, h))
                out += [f"     {geometry}>",
                        f'      <transform m11="{m[0]}" m12="{m[1]}" m13="0" m21="{m[2]}" m22="{m[3]}" m23="0" '
                        f'm31="{m[4]:.3f}" m32="{m[5]:.3f}" m33="1"/>',
                        "     </geometry>"]
            else:
                out.append(f"     {geometry}/>")
            if item["links"]:
                out.append("     <connectors>")
                for i, links in sorted(item["links"].items()):
                    out += [f'      <connector connectorId="connector{i}" layer="breadboard">', '       <geometry x="0" y="0"/>',
                            "       <connects>"]
                    out += [f'        <connect connectorId="{end}" modelIndex="{mi}" layer="{layer}"/>' for end, mi, layer in links]
                    out += ["       </connects>", "      </connector>"]
                out.append("     </connectors>")
            out += ["    </breadboardView>",
                    '    <schematicView layer="schematic">',
                    f'     <geometry z="{2.5 + z * 0.001:.4f}" x="{item["sch"][0]:.3f}" y="{item["sch"][1]:.3f}"/>',
                    "    </schematicView>",
                    '    <pcbView layer="copper0" bottom="false">',
                    f'     <geometry z="{5.5 + z * 0.001:.4f}" x="{item["pcb"][0]:.3f}" y="{item["pcb"][1]:.3f}"/>',
                    "    </pcbView>", "   </views>", "  </instance>"]
        for k, w in enumerate(self.wires):
            (x1, y1), (x2, y2) = w["p1"], w["p2"]
            out += [f'  <instance moduleIdRef="WireModuleID" modelIndex="{w["index"]}" path=":/resources/parts/core/wire.fzp">',
                    f"   <title>Wire{k + 1}</title>", "   <views>", '    <breadboardView layer="breadboardWire">',
                    f'     <geometry z="{3.5 + k * 0.001:.4f}" x="{x1:.3f}" y="{y1:.3f}" x1="0" y1="0" x2="{x2 - x1:.3f}" y2="{y2 - y1:.3f}" wireFlags="64"/>',
                    f'     <wireExtras mils="22.2222" color="{w["colour"]}" opacity="1" banded="0"/>',
                    "     <connectors>"]
            for end, (other, index, layer) in zip(("connector0", "connector1"), w["ends"]):
                out += [f'      <connector connectorId="{end}" layer="breadboardWire">', '       <geometry x="0" y="0"/>',
                        "       <connects>",
                        f'        <connect connectorId="{other}" modelIndex="{index}" layer="{layer}"/>',
                        "       </connects>", "      </connector>"]
            out += ["     </connectors>", "    </breadboardView>", "   </views>", "  </instance>"]
        out += [" </instances>", "</module>", ""]
        return "\n".join(out)
