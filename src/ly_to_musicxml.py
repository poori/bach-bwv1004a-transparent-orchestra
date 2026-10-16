#!/usr/bin/env python3
"""Generate the MusicXML derivative from the LilyPond master in ly/.

LilyPond itself reads the source: ly/musicxml-export.ly replays the score
with an event-dump engraver (ly/tools/event-dump.ily), and this script turns
those timed events back into MusicXML for validation and MuseScore playback.

Anything in the source that this exporter does not understand is an error,
never silently dropped.

    python3 src/ly_to_musicxml.py [--out PATH] [--lilypond BIN]
"""

from __future__ import annotations

import argparse
import collections
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
STEM = "Bach_BWV1004a_Leipzig_orchestral_realization"
EXPORT_LY = ROOT / "ly" / "musicxml-export.ly"
CONFIG = ROOT / "ly" / "musicxml-export.json"

STEPS = "CDEFGAB"
STEP_SEMITONES = (0, 2, 4, 5, 7, 9, 11)
TYPES = {0: "whole", 1: "half", 2: "quarter", 3: "eighth", 4: "16th", 5: "32nd", 6: "64th"}
DYNAMIC_VELOCITY = {"pp": 38, "p": 50, "mp": 62, "mf": 76, "f": 90, "ff": 104}
# Tempo directions carry dynamics="70" in this edition's MusicXML (as before the port).
TEMPO_SOUND_DYNAMICS = "70"
ARTICULATIONS = {"staccato": "staccato", "tenuto": "tenuto", "accent": "accent"}
GM_PROGRAMS = {  # 1-based General MIDI program numbers, as MusicXML uses
    "flute": 74, "oboe": 69, "bassoon": 71, "french horn": 61, "trumpet": 57,
    "timpani": 48, "violin": 41, "viola": 42, "cello": 43, "contrabass": 44,
}
MAJOR_FIFTHS = {0: 0, 1: 2, 2: 4, 3: -1, 4: 1, 5: 3, 6: 5}  # by note name, natural tonic
IGNORED = {"skip-event", "time-signature-event"}


class ExportError(Exception):
    pass


def frac(value) -> Fraction:
    return Fraction(value) if not isinstance(value, Fraction) else value


@dataclass
class Rhythmic:
    t: Fraction
    length: Fraction
    kind: str  # note | rest | mmrest
    event: dict
    posts: list = field(default_factory=list)  # (category, payload)
    directions: list = field(default_factory=list)
    tuplet_start: dict | None = None
    tuplet_stop: bool = False
    breath: bool = False
    # Markings that fall on a later barline inside a multi-measure rest.
    inner_directions: dict = field(default_factory=lambda: collections.defaultdict(list))


class Timeline:
    """Bar arithmetic for a single meter with an optional pickup."""

    def __init__(self, measure_length: Fraction, pickup: Fraction, divisions: int):
        self.measure_length = measure_length
        self.pickup = pickup  # length of bar 1 (equal to measure_length if none)
        self.divisions = divisions

    def bar_of(self, t: Fraction) -> tuple[int, Fraction]:
        if t < self.pickup:
            return 1, t
        n, offset = divmod(t - self.pickup, self.measure_length)
        return int(n) + 2, offset

    def bar_start(self, bar: int) -> Fraction:
        return Fraction(0) if bar == 1 else self.pickup + (bar - 2) * self.measure_length

    def bar_length(self, bar: int) -> Fraction:
        return self.pickup if bar == 1 else self.measure_length

    def ticks(self, length: Fraction) -> int:
        value = length * 4 * self.divisions
        if value.denominator != 1:
            raise ExportError(f"duration {length} is not a whole number of divisions")
        return int(value)


def run_lilypond(lilypond: str, workdir: Path) -> Path:
    stem = workdir / "export"
    result = subprocess.run(
        [lilypond, "-dno-print-pages", "-o", str(stem), str(EXPORT_LY)],
        capture_output=True, text=True,
    )
    log = (result.stdout or "") + (result.stderr or "")
    (workdir / "lilypond.log").write_text(log)
    problems = [line for line in log.splitlines() if "warning:" in line or "error:" in line]
    if result.returncode != 0 or problems:
        raise ExportError("LilyPond reported problems:\n" + "\n".join(problems or log.splitlines()[-20:]))
    return stem.with_suffix(".events.jsonl")


def load(path: Path):
    header = {}
    by_context: dict[str, list[dict]] = collections.defaultdict(list)
    properties: dict[str, dict] = collections.defaultdict(dict)
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if "header" in record:
            header = record["header"]
            continue
        if frac(record["grace"]) != 0:
            raise ExportError(f"grace notes are not supported ({record.get('at')})")
        record["t"] = frac(record["t"])
        key = record["id"]
        if "properties" in record:
            if record["t"] != 0 and set(record["properties"]) & {"clefGlyph", "instrumentTransposition", "timeSignatureFraction"}:
                raise ExportError(f"mid-piece clef, transposition or meter change in {key} at {record['t']}")
            properties[key].update(record["properties"])
            continue
        by_context[key].append(record)
    return header, by_context, properties


def written_type(duration: dict, where: str) -> tuple[str, int, Fraction]:
    if duration["log"] not in TYPES:
        raise ExportError(f"unsupported note value at {where}")
    return TYPES[duration["log"]], duration["dots"], frac(duration["scale"])


def direction_element(placement: str) -> tuple[ET.Element, ET.Element]:
    direction = ET.Element("direction", placement=placement)
    return direction, ET.SubElement(direction, "direction-type")


def words_direction(text: dict, placement: str, offset=None, tempo=None) -> ET.Element:
    direction, kind = direction_element(placement)
    attributes = {"font-style": "italic"} if text["italic"] else {}
    ET.SubElement(kind, "words", attributes).text = text["string"]
    if offset is not None:
        ET.SubElement(direction, "offset").text = str(offset)
    if tempo is not None:
        ET.SubElement(direction, "sound", tempo=str(tempo), dynamics=TEMPO_SOUND_DYNAMICS)
    return direction


def text_placement(record: dict, default: str = "above") -> str:
    direction = record.get("direction")
    if direction == 1:
        return "above"
    if direction == -1:
        return "below"
    return default


class PartBuilder:
    def __init__(self, spec: dict, records: list[dict], props: dict, timeline: Timeline,
                 natural_brass: bool, where: str):
        self.spec = spec
        self.records = records
        self.props = props
        self.timeline = timeline
        self.natural_brass = natural_brass
        self.where = where
        self.rhythm: list[Rhythmic] = []
        self.bar_end_directions: dict[int, list[ET.Element]] = collections.defaultdict(list)
        self.key_changes: dict[int, tuple[int, str]] = {}
        self.figures: list[tuple[Fraction, Fraction, list[str], bool]] = []

    # -- collection -------------------------------------------------------
    def collect(self) -> None:
        at = collections.defaultdict(list)
        for record in self.records:
            if "grob" in record:
                at[record["t"]].append(record)
                continue
            cls = record["class"]
            if cls in ("note-event", "rest-event", "multi-measure-rest-event"):
                kind = {"note-event": "note", "rest-event": "rest", "multi-measure-rest-event": "mmrest"}[cls]
                length = frac(record["duration"]["length"])
                if self.rhythm and self.rhythm[-1].t == record["t"]:
                    raise ExportError(f"chords or simultaneous notes are not supported ({record['at']})")
                self.rhythm.append(Rhythmic(record["t"], length, kind, record))
            elif cls in IGNORED:
                if cls == "time-signature-event" and (record["numerator"], record["denominator"]) != (3, 4):
                    raise ExportError("only 3/4 is supported")
            else:
                at[record["t"]].append(record)
        starts = {r.t: r for r in self.rhythm}
        ends = {r.t + r.length: r for r in self.rhythm}
        expected = Fraction(0)
        for item in self.rhythm:
            if item.t != expected:
                raise ExportError(f"{self.where}: gap or overlap at {item.t}")
            expected = item.t + item.length
        self.end = expected

        for t, items in sorted(at.items()):
            for record in items:
                self.attach(t, record, starts, ends)

    def attach(self, t: Fraction, record: dict, starts, ends) -> None:
        if "grob" in record:
            target = starts.get(t)
            if target is None or target.tuplet_start is None:
                return  # grob from a tuplet started at this moment; checked below
            target.tuplet_start.setdefault("shown", set())
            if record["shown"]:
                target.tuplet_start["shown"].add(record["grob"])
            target.tuplet_start.setdefault("seen", set()).add(record["grob"])
            return
        cls = record["class"]
        where = record.get("at", self.where)
        if cls == "key-change-event":
            bar, offset = self.timeline.bar_of(t)
            if offset:
                raise ExportError(f"key change inside a bar ({where})")
            self.key_changes[bar] = key_signature(record)
            return
        if cls == "breathing-event":
            target = ends.get(t)
            if target is None:
                raise ExportError(f"breath mark not after a note ({where})")
            target.breath = True
            return
        if cls == "tuplet-span-event":
            if record["span"] == -1:
                target = starts.get(t)
                if target is None:
                    raise ExportError(f"tuplet without a first note ({where})")
                target.tuplet_start = {"numerator": record.get("numerator"), "denominator": record.get("denominator")}
            else:
                target = ends.get(t)
                if target is None:
                    raise ExportError(f"tuplet without a last note ({where})")
                target.tuplet_stop = True
            return
        if cls == "bass-figure-event":
            raise ExportError(f"figure outside the figured-bass context ({where})")

        direction = self.direction_for(record, where)
        if direction is not None:
            if record.get("xmlBarEnd"):
                bar, offset = self.timeline.bar_of(t)
                if offset or bar == 1:
                    raise ExportError(f"\\xmlBarEnd must sit on a barline ({where})")
                self.bar_end_directions[bar - 1].append(direction)
                return
            target = starts.get(t)
            if target is not None:
                target.directions.append(direction)
                return
            bar, offset = self.timeline.bar_of(t)
            holder = next((r for r in self.rhythm if r.kind == "mmrest" and r.t < t < r.t + r.length), None)
            if holder is None or offset:
                raise ExportError(f"marking at {t} does not start with a note or rest ({where})")
            holder.inner_directions[bar].append(direction)
            return

        target = starts.get(t)
        if target is None:
            raise ExportError(f"{cls} at {t} does not start with a note ({where})")
        if cls == "articulation-event":
            name = record["articulation"]
            if name in ARTICULATIONS:
                target.posts.append(("articulation", ARTICULATIONS[name]))
            elif name == "trill":
                target.posts.append(("ornament", "trill-mark"))
            elif name == "fermata":
                target.posts.append(("fermata", None))
            else:
                raise ExportError(f"unsupported articulation {name} ({where})")
        elif cls == "slur-event":
            target.posts.append(("slur", "start" if record["span"] == -1 else "stop"))
        else:
            raise ExportError(f"unsupported event {cls} ({where})")

    def direction_for(self, record: dict, where: str) -> ET.Element | None:
        cls = record["class"]
        if cls == "absolute-dynamic-event":
            mark = record["text"]
            if mark not in DYNAMIC_VELOCITY:
                raise ExportError(f"unsupported dynamic {mark} ({where})")
            direction, kind = direction_element(text_placement(record, "below"))
            ET.SubElement(ET.SubElement(kind, "dynamics"), mark)
            ET.SubElement(direction, "sound", dynamics=str(DYNAMIC_VELOCITY[mark]))
            return direction
        if cls in ("crescendo-event", "decrescendo-event"):
            direction, kind = direction_element(text_placement(record, "below"))
            if record["span"] == -1:
                wedge_type = "crescendo" if cls == "crescendo-event" else "diminuendo"
            else:
                wedge_type = "stop"
            ET.SubElement(kind, "wedge", type=wedge_type, number="1")
            return direction
        if cls in ("text-script-event", "multi-measure-text-event"):
            return words_direction(record["text"], text_placement(record), record.get("xmlOffset"))
        if cls in ("ad-hoc-mark-event", "rehearsal-mark-event"):
            text = record.get("text") or {}
            label = text.get("string", "")
            if text.get("box") and label.startswith("[") and label.endswith("]"):
                label = label[1:-1]
            direction, kind = direction_element("above")
            ET.SubElement(kind, "rehearsal", enclosure="rectangle" if text.get("box") else "none").text = label
            return direction
        if cls == "tempo-change-event":
            unit = record.get("tempoUnit")
            if not unit or frac(unit["length"]) != Fraction(1, 4) or "text" not in record:
                raise ExportError(f"tempo marks need text and a quarter-note unit ({where})")
            return words_direction(record["text"], "above", tempo=record["metronome"])
        return None

    def collect_figures(self, records: list[dict]) -> None:
        groups: dict[Fraction, list[dict]] = collections.defaultdict(list)
        for record in records:
            if record.get("class") == "bass-figure-event":
                groups[record["t"]].append(record)
            elif record.get("class") not in ("skip-event", None) and "grob" not in record:
                raise ExportError(f"unsupported event in figured bass: {record['class']} ({record.get('at')})")
        for t, figures in sorted(groups.items()):
            length = frac(figures[0]["duration"]["length"])
            numbers = [str(f["figure"]) for f in figures]
            bracketed = bool(figures[0].get("bracketStart")) and bool(figures[-1].get("bracketStop"))
            partial = any(f.get("bracketStart") or f.get("bracketStop") for f in figures) and not bracketed
            if partial:
                raise ExportError(f"only whole figure groups can be bracketed ({figures[0].get('at')})")
            self.figures.append((t, length, numbers, bracketed))

    # -- output -------------------------------------------------------------
    def note_element(self, item: Rhythmic, length: Fraction, measure_rest: bool) -> ET.Element:
        note = ET.Element("note")
        event = item.event
        if item.kind == "note":
            pitch = ET.SubElement(note, "pitch")
            p = event["pitch"]
            if frac(p["alter"]).denominator != 1:
                raise ExportError(f"quarter-tone pitch at {event['at']}")
            ET.SubElement(pitch, "step").text = STEPS[p["step"]]
            alter = int(frac(p["alter"]))
            if alter:
                ET.SubElement(pitch, "alter").text = str(alter)
            ET.SubElement(pitch, "octave").text = str(p["octave"])
        else:
            ET.SubElement(note, "rest", measure="yes" if measure_rest else "no")
        ET.SubElement(note, "duration").text = str(self.timeline.ticks(length))
        ET.SubElement(note, "voice").text = "1"
        if measure_rest:
            type_, dots, scale = rest_type(length)
        else:
            type_, dots, scale = written_type(event["duration"], event["at"])
        ET.SubElement(note, "type").text = type_
        for _ in range(dots):
            ET.SubElement(note, "dot")
        if scale != 1:
            modification = ET.SubElement(note, "time-modification")
            ET.SubElement(modification, "actual-notes").text = str(scale.denominator)
            ET.SubElement(modification, "normal-notes").text = str(scale.numerator)
            ET.SubElement(modification, "normal-type").text = type_
        notations = []
        if item.tuplet_start is not None:
            attributes = {"type": "start", "number": "1"}
            seen = item.tuplet_start.get("seen", set())
            shown = item.tuplet_start.get("shown", set())
            if "TupletBracket" in seen and "TupletBracket" not in shown:
                attributes["bracket"] = "no"
            if "TupletNumber" in seen and "TupletNumber" not in shown:
                attributes["show-number"] = "none"
            notations.append(ET.Element("tuplet", attributes))
        if item.tuplet_stop:
            notations.append(ET.Element("tuplet", type="stop", number="1"))
        for category, payload in item.posts:
            if category == "slur":
                notations.append(ET.Element("slur", type=payload, number="1"))
        articulations = [ET.Element(p) for c, p in item.posts if c == "articulation"]
        if item.breath:
            articulations.append(ET.Element("breath-mark"))
        ornaments = [ET.Element(p) for c, p in item.posts if c == "ornament"]
        fermata = any(c == "fermata" for c, _ in item.posts)
        if notations or articulations or ornaments or fermata:
            parent = ET.SubElement(note, "notations")
            for element in notations:
                parent.append(element)
            if articulations:
                group = ET.SubElement(parent, "articulations")
                for element in articulations:
                    group.append(element)
            if ornaments:
                group = ET.SubElement(parent, "ornaments")
                for element in ornaments:
                    group.append(element)
            if fermata:
                ET.SubElement(parent, "fermata", type="upright")
        return note

    def measures(self, total_bars: int) -> list[ET.Element]:
        tl = self.timeline
        measures = {bar: [] for bar in range(1, total_bars + 1)}
        onsets: dict[int, dict[Fraction, int]] = collections.defaultdict(dict)
        for item in self.rhythm:
            if item.kind == "mmrest":
                if item.posts or item.tuplet_start or item.tuplet_stop or item.breath:
                    raise ExportError(f"articulations on a multi-measure rest ({item.event['at']})")
                bar, offset = tl.bar_of(item.t)
                remaining = item.length
                first = True
                while remaining > 0:
                    length = tl.bar_length(bar)
                    if offset or remaining < length:
                        raise ExportError(f"multi-measure rest not aligned to bars ({item.event['at']})")
                    measures[bar].extend(item.directions if first else item.inner_directions.get(bar, []))
                    onsets[bar][Fraction(0)] = len(measures[bar])
                    piece = Rhythmic(tl.bar_start(bar), length, "rest", item.event)
                    measures[bar].append(self.note_element(piece, length, measure_rest=True))
                    remaining -= length
                    bar += 1
                    first = False
                continue
            bar, offset = tl.bar_of(item.t)
            if offset + item.length > tl.bar_length(bar):
                raise ExportError(f"note crosses a barline; ties are not supported ({item.event['at']})")
            measures[bar].extend(item.directions)
            onsets[bar][offset] = len(measures[bar])
            measures[bar].append(self.note_element(item, item.length, measure_rest=False))

        # Figured bass: each contiguous run goes before the note where it starts.
        runs: list[list] = []
        for figure in self.figures:
            if runs and runs[-1][-1][0] + runs[-1][-1][1] == figure[0] \
                    and tl.bar_of(figure[0])[0] == tl.bar_of(runs[-1][0][0])[0]:
                runs[-1].append(figure)
            else:
                runs.append([figure])
        inserts: dict[int, list[tuple[int, list]]] = collections.defaultdict(list)
        for run in runs:
            bar, offset = tl.bar_of(run[0][0])
            if offset not in onsets[bar]:
                raise ExportError(f"figure at bar {bar} does not start with a note")
            end_bar, end_offset = tl.bar_of(run[-1][0] + run[-1][1])
            if end_bar != bar and not (end_bar == bar + 1 and end_offset == 0):
                raise ExportError(f"figure crosses a barline at bar {bar}")
            inserts[bar].append((onsets[bar][offset], run))
        for bar, items in inserts.items():
            for index, run in sorted(items, key=lambda x: -x[0]):
                elements = []
                for _, length, numbers, bracketed in run:
                    element = ET.Element("figured-bass", {"parentheses": "yes"} if bracketed else {})
                    for number in numbers:
                        ET.SubElement(ET.SubElement(element, "figure"), "figure-number").text = number
                    ET.SubElement(element, "duration").text = str(tl.ticks(length))
                    elements.append(element)
                # Directions at the same onset stay before the figures.
                while index < len(measures[bar]) and measures[bar][index].tag == "direction":
                    index += 1
                measures[bar][index:index] = elements

        result = []
        for bar in range(1, total_bars + 1):
            measure = ET.Element("measure", number=str(bar), implicit="yes" if bar == 1 and tl.pickup != tl.measure_length else "no")
            attributes = self.attributes(bar)
            if attributes is not None:
                measure.append(attributes)
            for element in measures[bar]:
                measure.append(element)
            for element in self.bar_end_directions.get(bar, []):
                measure.append(element)
            result.append(measure)
        return result

    def attributes(self, bar: int) -> ET.Element | None:
        if bar == 1:
            attributes = ET.Element("attributes")
            ET.SubElement(attributes, "divisions").text = str(self.timeline.divisions)
            if self.natural_brass:
                if self.key_changes:
                    raise ExportError(f"natural brass part {self.where} has a key signature")
                fifths, mode = 0, "major"
            else:
                fifths, mode = self.key_changes.get(1, (0, "major"))
            key = ET.SubElement(attributes, "key")
            ET.SubElement(key, "fifths").text = str(fifths)
            ET.SubElement(key, "mode").text = mode
            time = ET.SubElement(attributes, "time")
            numerator, denominator = self.props.get("timeSignatureFraction", [3, 4])
            ET.SubElement(time, "beats").text = str(numerator)
            ET.SubElement(time, "beat-type").text = str(denominator)
            clef = ET.SubElement(attributes, "clef")
            sign = {"clefs.G": "G", "clefs.F": "F", "clefs.C": "C"}.get(self.props.get("clefGlyph"))
            if sign is None:
                raise ExportError(f"unsupported clef in {self.where}")
            ET.SubElement(clef, "sign").text = sign
            ET.SubElement(clef, "line").text = str(self.props["clefPosition"] // 2 + 3)
            if self.props.get("clefTransposition"):
                ET.SubElement(clef, "clef-octave-change").text = str(self.props["clefTransposition"] // 7)
            transposition = self.props.get("instrumentTransposition")
            if transposition and (transposition["step"], transposition["alter"], transposition["octave"]) != (0, 0, 4):
                steps = transposition["step"] + 7 * (transposition["octave"] - 4)
                semitones = (STEP_SEMITONES[transposition["step"]] + int(frac(transposition["alter"]))
                             + 12 * (transposition["octave"] - 4))
                transpose = ET.SubElement(attributes, "transpose")
                ET.SubElement(transpose, "diatonic").text = str(steps)
                ET.SubElement(transpose, "chromatic").text = str(semitones)
            return attributes
        if bar in self.key_changes:
            attributes = ET.Element("attributes")
            fifths, mode = self.key_changes[bar]
            key = ET.SubElement(attributes, "key")
            ET.SubElement(key, "fifths").text = str(fifths)
            ET.SubElement(key, "mode").text = mode
            return attributes
        return None


def rest_type(length: Fraction) -> tuple[str, int, Fraction]:
    for log, name in TYPES.items():
        base = Fraction(1, 2 ** log)
        for dots in range(3):
            if base * (2 - Fraction(1, 2 ** dots)) == length:
                return name, dots, Fraction(1)
    raise ExportError(f"cannot write a whole-bar rest of length {length}")


def key_signature(record: dict) -> tuple[int, str]:
    alterations = record.get("keyAlterations") or []
    alterations = [frac(a) for a in alterations]
    if any(abs(a) > 1 for a in alterations):
        raise ExportError("key signatures with double accidentals are not supported")
    fifths = sum(1 for a in alterations if a > 0) - sum(1 for a in alterations if a < 0)
    tonic = record["tonic"]
    major = MAJOR_FIFTHS[tonic["step"]] + 7 * int(frac(tonic["alter"]))
    if fifths == major:
        return fifths, "major"
    if fifths == major - 3:
        return fifths, "minor"
    raise ExportError(f"unsupported key mode ({record.get('at')})")


def build(header: dict, by_context: dict, properties: dict, config: dict) -> ET.Element:
    divisions = config["divisions"]
    first = config["parts"][0]["voice"]
    props = properties[first]
    measure_length = frac(props["measureLength"])
    position = frac(props["measurePosition"])
    pickup = -position if position < 0 else measure_length
    timeline = Timeline(measure_length, pickup, divisions)

    known = {spec["voice"] for spec in config["parts"]}
    known |= {spec.get("structure") for spec in config["parts"]} | {spec.get("figures") for spec in config["parts"]}
    unknown = set(by_context) - known
    if unknown:
        raise ExportError(f"contexts not mapped in musicxml-export.json: {sorted(unknown)}")

    builders = []
    for spec in config["parts"]:
        voice = spec["voice"]
        records = list(by_context.get(voice, []))
        if spec.get("structure"):
            # Score-level layer: its markings land on this part, ahead of the part's own.
            structure = [r for r in by_context.get(spec["structure"], [])
                         if r.get("class") not in IGNORED]
            records = structure + records
        builder = PartBuilder(spec, records, properties[voice], timeline,
                              voice in config.get("naturalBrass", []), voice)
        builder.collect()
        if spec.get("figures"):
            builder.collect_figures(by_context.get(spec["figures"], []))
        builders.append(builder)
    ends = {b.end for b in builders}
    if len(ends) != 1:
        raise ExportError(f"parts end at different moments: { {b.where: str(b.end) for b in builders} }")
    total_bars, offset = timeline.bar_of(ends.pop())
    if offset:
        raise ExportError("the score does not end on a barline")
    total_bars -= 1

    root = ET.Element("score-partwise", version="4.0")
    ET.SubElement(ET.SubElement(root, "work"), "work-title").text = header["title"]
    identification = ET.SubElement(root, "identification")
    ET.SubElement(identification, "creator", type="composer").text = header["composer"]
    ET.SubElement(identification, "creator", type="other").text = config["identification"]["other"]
    ET.SubElement(identification, "rights").text = header["copyright"]
    encoding = ET.SubElement(identification, "encoding")
    ET.SubElement(encoding, "software").text = "LilyPond via src/ly_to_musicxml.py"
    ET.SubElement(encoding, "encoding-description").text = config["identification"]["encodingDescription"]
    defaults_cfg = config["defaults"]
    defaults = ET.SubElement(root, "defaults")
    scaling = ET.SubElement(defaults, "scaling")
    ET.SubElement(scaling, "millimeters").text = defaults_cfg["millimeters"]
    ET.SubElement(scaling, "tenths").text = defaults_cfg["tenths"]
    layout = ET.SubElement(defaults, "page-layout")
    ET.SubElement(layout, "page-height").text = defaults_cfg["pageHeight"]
    ET.SubElement(layout, "page-width").text = defaults_cfg["pageWidth"]
    margins = ET.SubElement(layout, "page-margins", type="both")
    for side in ("left", "right", "top", "bottom"):
        ET.SubElement(margins, f"{side}-margin").text = defaults_cfg["margin"]
    for kind, text in (("title", header["title"]), ("composer", header["composer"])):
        credit = ET.SubElement(root, "credit", page="1")
        ET.SubElement(credit, "credit-type").text = kind
        ET.SubElement(credit, "credit-words", config["credits"][kind]).text = text

    part_list = ET.SubElement(root, "part-list")
    for spec, builder in zip(config["parts"], builders):
        pid = spec["id"]
        props = builder.props
        name = props.get("instrumentName")
        if not isinstance(name, str):
            raise ExportError(f"{builder.where} needs a plain-text instrumentName")
        score_part = ET.SubElement(part_list, "score-part", id=pid)
        ET.SubElement(score_part, "part-name").text = name
        ET.SubElement(score_part, "part-abbreviation").text = props.get("shortInstrumentName", name)
        instrument = ET.SubElement(score_part, "score-instrument", id=f"{pid}-I1")
        ET.SubElement(instrument, "instrument-name").text = name
        midi = ET.SubElement(score_part, "midi-instrument", id=f"{pid}-I1")
        ET.SubElement(midi, "midi-channel").text = str(spec["midiChannel"])
        program = GM_PROGRAMS.get(props.get("midiInstrument"))
        if program is None:
            raise ExportError(f"no General MIDI program for {props.get('midiInstrument')!r}")
        ET.SubElement(midi, "midi-program").text = str(program)
        ET.SubElement(midi, "volume").text = str(spec["volume"])
        pan = frac(props.get("midiPanPosition", 0)) * 90
        if pan.denominator != 1:
            raise ExportError(f"midiPanPosition of {builder.where} is not a whole number of degrees / 90")
        ET.SubElement(midi, "pan").text = str(int(pan))

    for spec, builder in zip(config["parts"], builders):
        part = ET.SubElement(root, "part", id=spec["id"])
        for measure in builder.measures(total_bars):
            part.append(measure)
    return root


def serialize(root: ET.Element) -> bytes:
    ET.indent(root, space="  ")
    body = ET.tostring(root, encoding="unicode")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
        '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" '
        '"http://www.musicxml.org/dtds/partwise.dtd">\n' + body + "\n"
    ).encode("utf-8")


def export(out: Path, lilypond: str = "lilypond", workdir: Path | None = None) -> Path:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if workdir is None:
        workdir = Path(tempfile.mkdtemp(prefix="ly-musicxml-"))
    workdir.mkdir(parents=True, exist_ok=True)
    events = run_lilypond(lilypond, workdir)
    header, by_context, properties = load(events)
    root = build(header, by_context, properties, config)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(serialize(root))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "score" / f"{STEM}.musicxml")
    parser.add_argument("--lilypond", default="lilypond")
    parser.add_argument("--workdir", type=Path, default=ROOT / "build" / "musicxml-export")
    args = parser.parse_args()
    try:
        path = export(args.out, args.lilypond, args.workdir)
    except ExportError as error:
        raise SystemExit(f"MusicXML export failed: {error}")
    print(f"exported {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")


if __name__ == "__main__":
    main()
