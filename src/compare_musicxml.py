#!/usr/bin/env python3
"""Compare two MusicXML scores by musical content, not by bytes.

Notes, rests, rhythm, tuplets, articulations, slurs, dynamics, hairpins,
text, rehearsal marks, tempo, figured bass, clefs, keys, transposition and
part-list settings are compared measure by measure. Element order inside a
measure, whitespace and empty <notations/> are ignored. Figured-bass
elements are compared at the time they apply, so equivalent placements match.

    python3 src/compare_musicxml.py OLD.musicxml NEW.musicxml [--allow KIND ...]

Exit status is 0 only if every difference is of an allowed kind.
"""

from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


def canon(element: ET.Element) -> tuple:
    """Order-preserving canonical form of an element subtree."""
    text = (element.text or "").strip()
    return (element.tag, tuple(sorted(element.attrib.items())), text,
            tuple(canon(child) for child in element))


def note_key(note: ET.Element) -> tuple:
    rest = note.find("rest")
    if rest is not None:
        sound = ("rest", rest.get("measure", "no"))
    else:
        pitch = note.find("pitch")
        sound = ("pitch", pitch.findtext("step"), int(pitch.findtext("alter", "0")),
                 int(pitch.findtext("octave")))
    modification = note.find("time-modification")
    notations = note.find("notations")
    marks = []
    if notations is not None:
        for child in notations.iter():
            if child is notations or child.tag in ("articulations", "ornaments"):
                continue
            marks.append((child.tag, tuple(sorted(child.attrib.items()))))
    return (
        sound,
        int(note.findtext("duration")),
        note.findtext("type"),
        len(note.findall("dot")),
        canon(modification) if modification is not None else None,
        note.find("chord") is not None,
        note.find("grace") is not None,
        tuple(sorted(marks)),
        tuple(canon(t) for t in note.findall("tie")),
    )


def direction_key(direction: ET.Element) -> tuple:
    kinds = tuple(sorted(canon(kind) for kind in direction.find("direction-type")))
    sound = direction.find("sound")
    return (
        direction.get("placement"),
        kinds,
        direction.findtext("offset"),
        tuple(sorted(sound.attrib.items())) if sound is not None else None,
    )


def measure_model(measure: ET.Element) -> dict:
    cursor = 0
    events = collections.Counter()
    figures = []
    run_position = None
    attributes = []
    layout = []
    for element in measure:
        if element.tag == "note":
            events[("note", cursor, note_key(element))] += 1
            if element.find("chord") is None:
                cursor += int(element.findtext("duration"))
            run_position = None
        elif element.tag == "direction":
            events[("direction", cursor, direction_key(element))] += 1
        elif element.tag == "figured-bass":
            position = cursor if run_position is None else run_position
            duration = int(element.findtext("duration", "0"))
            figures.append((position, duration, element.get("parentheses"),
                            tuple(canon(f) for f in element.findall("figure"))))
            run_position = position + duration
        elif element.tag == "attributes":
            attributes.append(canon(element))
        elif element.tag in ("backup", "forward"):
            raise SystemExit("multi-voice measures are not supported by this comparison")
        elif element.tag == "print":
            layout.append(canon(element))
        else:
            events[("other", cursor, canon(element))] += 1
    for position, duration, parentheses, numbers in figures:
        events[("figure", position, (duration, parentheses, numbers))] += 1
    return {"events": events, "attributes": attributes, "layout": layout,
            "implicit": measure.get("implicit")}


def score_model(path: Path) -> dict:
    root = ET.parse(path).getroot()
    model = {
        "header": {
            "work-title": root.findtext("work/work-title"),
            "composer": root.findtext("identification/creator[@type='composer']"),
            "rights": root.findtext("identification/rights"),
            "defaults": canon(root.find("defaults")) if root.find("defaults") is not None else None,
            "credits": tuple(canon(c) for c in root.findall("credit")),
        },
        "identification": canon(root.find("identification")),
        "part-list": [canon(p) for p in root.findall("part-list/score-part")],
        "parts": {},
    }
    for part in root.findall("part"):
        model["parts"][part.get("id")] = {
            int(m.get("number")): measure_model(m) for m in part.findall("measure")}
    return model


def describe(event: tuple) -> str:
    kind, position, key = event
    return f"{kind} @{position}: {key}"


def compare(old: dict, new: dict) -> dict[str, list[str]]:
    diffs: dict[str, list[str]] = collections.defaultdict(list)
    for field, value in old["header"].items():
        if new["header"][field] != value:
            diffs["header"].append(f"{field}: {value!r} -> {new['header'][field]!r}")
    if old["identification"] != new["identification"]:
        diffs["identification"].append("creator/encoding metadata differs")
    if old["part-list"] != new["part-list"]:
        for a, b in zip(old["part-list"], new["part-list"]):
            if a != b:
                diffs["part-list"].append(f"{a[1]}: {a} -> {b}")
    if set(old["parts"]) != set(new["parts"]):
        diffs["parts"].append(f"{sorted(old['parts'])} -> {sorted(new['parts'])}")
    for pid in old["parts"]:
        a_measures, b_measures = old["parts"][pid], new["parts"].get(pid, {})
        if set(a_measures) != set(b_measures):
            diffs["measures"].append(f"{pid}: measure numbers differ")
        for number in sorted(set(a_measures) & set(b_measures)):
            a, b = a_measures[number], b_measures[number]
            if a["implicit"] != b["implicit"]:
                diffs["measures"].append(f"{pid} m{number}: implicit {a['implicit']} -> {b['implicit']}")
            if a["attributes"] != b["attributes"]:
                diffs["attributes"].append(f"{pid} m{number}: {a['attributes']} -> {b['attributes']}")
            if a["layout"] != b["layout"]:
                diffs["layout"].append(f"{pid} m{number}: {a['layout']} -> {b['layout']}")
            missing = a["events"] - b["events"]
            extra = b["events"] - a["events"]
            for event in missing.elements():
                diffs[event[0]].append(f"{pid} m{number} only in old: {describe(event)}")
            for event in extra.elements():
                diffs[event[0]].append(f"{pid} m{number} only in new: {describe(event)}")
    return diffs


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare MusicXML scores by musical content.")
    parser.add_argument("old", type=Path)
    parser.add_argument("new", type=Path)
    parser.add_argument("--allow", action="append", default=[],
                        help="difference kind that does not fail the comparison")
    parser.add_argument("--show", type=int, default=8, help="examples to print per kind")
    args = parser.parse_args()
    diffs = compare(score_model(args.old), score_model(args.new))
    if not diffs:
        print("identical musical content")
        return
    failing = False
    for kind, items in sorted(diffs.items()):
        allowed = kind in args.allow
        failing |= not allowed
        print(f"{kind}: {len(items)} difference(s){' (allowed)' if allowed else ''}")
        for item in items[: args.show]:
            print("   ", item)
    sys.exit(1 if failing else 0)


if __name__ == "__main__":
    main()
