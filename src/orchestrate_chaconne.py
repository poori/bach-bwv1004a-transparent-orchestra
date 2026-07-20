#!/usr/bin/env python3
"""Create a transparent orchestral realization of Bach's BWV 1004 Chaconne.

The source is the Mutopia Project MIDI corresponding to Hajo Dezelski's
LilyPond engraving (CC BY-SA 3.0).  This script separates its four sounding
voices, hands complete strands between instrumental choirs, adds only a few
structural brass/timpani pillars, and writes MusicXML, MIDI, and a simple audio
mock-up.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
from pathlib import Path
import math
import os
import struct
import wave
import zipfile
from xml.etree import ElementTree as ET

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MIDI = ROOT / "source" / "bwv-1004_5.mid"
OUT = ROOT / "score"
BUILD = ROOT / "build"
TPQ = 384
PICKUP = 2 * TPQ
BAR = 3 * TPQ


@dataclass
class Note:
    start: int
    end: int
    pitch: int
    velocity: int = 72
    tie_start: bool = False
    tie_stop: bool = False


@dataclass(frozen=True)
class WrittenDuration:
    """One conventional MusicXML spelling for an exact tick duration."""

    ticks: int
    note_type: str
    dots: int = 0
    actual_notes: int | None = None
    normal_notes: int | None = None


@dataclass(frozen=True)
class Instrument:
    key: str
    name: str
    abbreviation: str
    program: int
    channel: int
    clef: str
    pan: int
    family: str


INSTRUMENTS = [
    Instrument("fl1", "Flute I", "Fl. I", 73, 0, "G", 38, "flute"),
    Instrument("fl2", "Flute II", "Fl. II", 73, 0, "G", 50, "flute"),
    Instrument("ob1", "Oboe I", "Ob. I", 68, 1, "G", 46, "oboe"),
    Instrument("ob2", "Oboe II", "Ob. II", 68, 1, "G", 58, "oboe"),
    Instrument("bn1", "Bassoon I", "Bsn. I", 70, 2, "F", 52, "bassoon"),
    Instrument("bn2", "Bassoon II", "Bsn. II", 70, 2, "F", 66, "bassoon"),
    Instrument("hn1", "Horn I in D (concert pitch)", "Hn. I", 60, 3, "G", 36, "horn"),
    Instrument("hn2", "Horn II in D (concert pitch)", "Hn. II", 60, 3, "G", 70, "horn"),
    Instrument("tpt1", "Trumpet I in D (concert pitch)", "Tpt. I", 56, 4, "G", 30, "trumpet"),
    Instrument("tpt2", "Trumpet II in D (concert pitch)", "Tpt. II", 56, 4, "G", 76, "trumpet"),
    Instrument("timp", "Timpani (D–A)", "Timp.", 47, 5, "F", 64, "timpani"),
    Instrument("vln1", "Violin I", "Vln. I", 40, 6, "G", 28, "strings"),
    Instrument("vln2", "Violin II", "Vln. II", 40, 6, "G", 44, "strings"),
    Instrument("vla", "Viola", "Vla.", 41, 7, "C", 68, "strings"),
    Instrument("vc", "Violoncello", "Vc.", 42, 8, "F", 78, "strings"),
    Instrument("cb", "Double Bass", "Cb.", 43, 11, "F", 84, "strings"),
]
INST = {x.key: x for x in INSTRUMENTS}


def read_vlq(data: bytes, pos: int) -> tuple[int, int]:
    value = 0
    while True:
        byte = data[pos]
        pos += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, pos


def parse_midi_notes(path: Path) -> list[Note]:
    data = path.read_bytes()
    if data[:4] != b"MThd":
        raise ValueError("Not a Standard MIDI file")
    ntracks = int.from_bytes(data[10:12], "big")
    division = int.from_bytes(data[12:14], "big")
    if division != TPQ:
        raise ValueError(f"Expected {TPQ} ticks/quarter, got {division}")
    pos = 14
    notes: list[Note] = []
    for _ in range(ntracks):
        if data[pos:pos + 4] != b"MTrk":
            raise ValueError("Malformed MIDI track")
        length = int.from_bytes(data[pos + 4:pos + 8], "big")
        track = data[pos + 8:pos + 8 + length]
        pos += 8 + length
        t = p = 0
        running = 0
        active: dict[tuple[int, int], list[tuple[int, int]]] = {}
        while p < len(track):
            delta, p = read_vlq(track, p)
            t += delta
            status = track[p]
            if status < 0x80:
                status = running
            else:
                p += 1
                running = status
            if status == 0xFF:
                p += 1
                size, p = read_vlq(track, p)
                p += size
                continue
            if status in (0xF0, 0xF7):
                size, p = read_vlq(track, p)
                p += size
                continue
            kind, channel = status & 0xF0, status & 0x0F
            size = 1 if kind in (0xC0, 0xD0) else 2
            values = track[p:p + size]
            p += size
            if kind == 0x90 and values[1] > 0:
                active.setdefault((channel, values[0]), []).append((t, values[1]))
            elif kind == 0x80 or (kind == 0x90 and values[1] == 0):
                stack = active.get((channel, values[0]))
                if stack:
                    start, velocity = stack.pop(0)
                    notes.append(Note(start, t, values[0], velocity))
    return sorted(notes, key=lambda n: (n.start, -n.pitch, n.end))


def score_bar(tick: int) -> int:
    """LilyPond source bar number: its first, incomplete bar is numbered 1."""
    if tick < PICKUP:
        return 1
    return 2 + (tick - PICKUP) // BAR


def bar_start(number: int) -> int:
    if number <= 1:
        return 0
    return PICKUP + (number - 2) * BAR


def separate_voices(notes: list[Note]) -> list[list[Note]]:
    """Colour the four-voice interval graph, preferring stable registral lines."""
    groups: dict[int, list[Note]] = {}
    for n in notes:
        groups.setdefault(n.start, []).append(n)
    voices: list[list[Note]] = [[] for _ in range(4)]
    ends = [-1] * 4
    last = [79, 69, 60, 50]
    targets = [78, 69, 60, 50]
    for start in sorted(groups):
        group = sorted(groups[start], key=lambda n: -n.pitch)
        available = [i for i in range(4) if ends[i] <= start]
        if len(available) < len(group):
            raise ValueError(f"More than four simultaneous voices at tick {start}")
        best: tuple[float, tuple[int, ...]] | None = None
        for chosen in combinations(available, len(group)):
            cost = 0.0
            for note, voice in zip(group, chosen):
                cost += abs(note.pitch - last[voice]) * 0.75
                cost += abs(note.pitch - targets[voice]) * 0.18
                if voice > 0 and note.pitch > last[voice - 1] + 3:
                    cost += 12
                if voice < 3 and note.pitch < last[voice + 1] - 3:
                    cost += 12
            if best is None or cost < best[0]:
                best = (cost, chosen)
        assert best is not None
        for note, voice in zip(group, best[1]):
            voices[voice].append(note)
            ends[voice] = note.end
            last[voice] = note.pitch
    return voices


SECTIONS = [
    (1, 16, ("vln1", "vln2", "vla", "vc"), 62, "A · Grave — strings alone"),
    (17, 32, ("ob1", "vln1", "vla", "bn1"), 64, "B · Oboe enters as a voice"),
    (33, 56, ("vln1", "vln2", "vla", "vc"), 66, "C · Figuration — violin-led"),
    (57, 76, ("fl1", "ob1", "vla", "bn1"), 68, "D · Flute-led dialogue"),
    (77, 96, ("vln1", "ob1", "vla", "vc"), 64, "E · Dialogue — gathering to strings"),
    (97, 120, ("ob1", "ob2", "bn1", "bn2"), 60, "F · Chorale, senza vibrato"),
    (121, 132, ("vln1", "vln2", "vla", "vc"), 66, "G · Gathering motion"),
    (133, 148, ("fl1", "fl2", "ob1", "bn1"), 68, "H · D major — chiaro"),
    (149, 168, ("vln1", "vln2", "vla", "vc"), 70, "I · D major — violin-led flow"),
    (169, 176, ("vln1", "fl1", "vla", "vc"), 72, "J · Crown of the major section"),
    (177, 196, ("ob1", "ob2", "bn1", "bn2"), 64, "K · Second chorale"),
    (197, 208, ("fl1", "ob1", "vla", "cb"), 68, "L · Major-mode cadence"),
    (209, 228, ("vln1", "vln2", "vla", "vc"), 66, "M · D minor returns — ripieno, then relays"),
    (229, 240, ("vln1", "ob1", "vla", "bn1"), 72, "N · Contrapuntal summit — staggered colors"),
    (241, 248, ("fl1", "ob1", "vla", "vc"), 66, "O · Subsiding"),
    (249, 254, ("ob1", "vln1", "bn1", "cb"), 60, "P · Final pillars"),
    (255, 257, ("vln1", "vln2", "vla", "vc"), 52, "Q · Coda — morendo"),
]


# Keep actual simultaneous strands stable within each contrapuntal cell.
# Subordinate colors change one at a time where practical.  Single-line
# passages use the separate phrase-relay map below.  Each mapping here runs
# from the highest to the lowest strand.
MOTIVE_HANDOFFS = [
    (33, 36, ("vln1", "vln2", "vla", "vc")),
    (37, 40, ("vln1", "ob1", "vla", "vc")),
    (41, 44, ("vln1", "ob1", "vla", "bn1")),
    (45, 48, ("vln1", "vln2", "vla", "bn1")),
    (49, 52, ("vln1", "vln2", "vla", "vc")),
    (53, 56, ("vln1", "vln2", "vla", "vc")),
    (57, 60, ("fl1", "ob1", "vla", "bn1")),
    (61, 64, ("fl1", "vln2", "vla", "bn1")),
    (65, 68, ("fl1", "vln2", "vla", "vc")),
    (69, 72, ("fl1", "ob1", "vla", "vc")),
    (73, 76, ("fl1", "ob1", "vla", "bn1")),
    (77, 80, ("vln1", "ob1", "vla", "bn1")),
    (81, 84, ("vln1", "vln2", "vla", "bn1")),
    (85, 88, ("vln1", "vln2", "vla", "vc")),
    (89, 92, ("vln1", "ob1", "vla", "vc")),
    (93, 96, ("vln1", "vln2", "vla", "vc")),
    (149, 152, ("vln1", "vln2", "vla", "vc")),
    (153, 156, ("vln1", "ob1", "vla", "vc")),
    (157, 160, ("vln1", "ob1", "vla", "vc")),
    (161, 164, ("vln1", "ob1", "vla", "bn1")),
    (165, 168, ("vln1", "vln2", "vla", "vc")),
    (169, 172, ("vln1", "fl1", "vla", "vc")),
    (173, 176, ("vln1", "ob1", "vla", "vc")),
    (209, 212, ("vln1", "vln2", "vla", "vc")),
    (213, 216, ("vln1", "ob1", "vla", "vc")),
    (217, 220, ("vln1", "ob1", "vla", "vc")),
    (221, 224, ("vln1", "vln2", "vla", "bn1")),
    (225, 228, ("vln1", "vln2", "vla", "vc")),
    (229, 232, ("vln1", "ob1", "vla", "bn1")),
    (233, 236, ("vln1", "vln2", "vla", "bn1")),
    (237, 240, ("vln1", "vln2", "vla", "vc")),
]

# When Bach's notation contracts to a single sounding line, the automatic
# voice index no longer describes a true contrapuntal strand.  Assign those
# notes in complete two- to four-bar cells instead: the resulting relays keep
# whole gestures intact, provide natural wind breaths, and avoid asking a
# flute or oboe to inherit the violin's low arpeggiation note by note.
MONOPHONIC_RELAYS = (
    (31, 32, "vla"),
    (33, 36, "vln1"),
    (37, 40, "ob2"),
    (41, 44, "vla"),
    (45, 48, "vln2"),
    (49, 52, "vc"),
    (53, 56, "vln1"),
    (57, 60, "ob1"),
    (61, 64, "vln2"),
    (65, 68, "vla"),
    (69, 70, "fl2"),
    (71, 72, "vln1"),
    (73, 74, "vla"),
    (75, 76, "vln2"),
    (77, 80, "vla"),
    (81, 84, "vln2"),
    (85, 89, "vln1"),
    (153, 154, "ob1"),
    (155, 156, "vla"),
    (157, 160, "vln2"),
    (161, 162, "vla"),
    (163, 164, "ob1"),
    (165, 168, "vln1"),
    (217, 220, "ob2"),
    (221, 224, "vla"),
    (225, 226, "ob1"),
    (227, 228, "vln1"),
    (241, 242, "fl1"),
    (243, 244, "ob1"),
    (245, 246, "vla"),
    (247, 248, "vln1"),
)

PROFESSIONAL_RANGES = {
    "fl1": (60, 96),
    "fl2": (60, 96),
    "ob1": (58, 91),
    "ob2": (58, 91),
}

REFINED_RANGES = ((33, 96), (149, 176), (209, 240))
RIPIENO_RANGES = ((53, 56), (93, 96), (165, 168), (209, 212), (229, 232))
STRING_TEXTURE_MARKS = {
    33: "solo", 53: "ripieno", 57: "solo", 93: "ripieno",
    149: "solo", 165: "ripieno", 169: "solo",
    209: "ripieno", 213: "solo", 229: "ripieno", 233: "solo",
    249: "ripieno", 255: "solo",
}

# Semantic notation that is not represented by the source MIDI.  The source
# LilyPond engraving marks trills on these exact notes, arpeggiation at the
# two distributed chords, and a fermata on the final D.  Keeping these events
# separate from the automatic phrasing layer prevents a sounding MIDI event
# list from silently replacing the notated musical text.
SOURCE_TRILLS = {
    (73, 960, 60),
    (74, 960, 58),
}
SOURCE_FERMATAS = {
    (257, 0, 62),
}
ARPEGGIO_DIRECTIONS = {
    ("ob1", 89): (384, "arpeggiate upward, together"),
    ("vln1", 89): (384, "arpeggiate upward, together"),
    ("vla", 89): (384, "arpeggiate upward, together"),
    ("fl1", 201): (0, "arpeggiate upward, together"),
    ("vla", 201): (0, "arpeggiate upward, together"),
}
FINAL_UNISON_DIRECTION = "two-string unison"

# A restrained but fully visible dynamic architecture.  Every player receives
# the prevailing mark on entry after a rest, while these change bars restate
# the large-scale curve for players already sounding.
DYNAMIC_CHANGES = {
    1: "p", 17: "mp", 33: "mf", 53: "f", 57: "mf", 77: "mp",
    89: "mf", 97: "p", 113: "mp", 121: "mp", 133: "p",
    141: "mp", 149: "mf", 165: "f", 177: "p", 189: "mp",
    197: "mp", 209: "f", 213: "mf", 229: "f", 237: "ff",
    241: "mp", 249: "f", 255: "p", 257: "pp",
}

DYNAMIC_LEVELS = {
    "pp": 38, "p": 50, "mp": 62, "mf": 76, "f": 90, "ff": 104,
}

# Curated spans rather than automatic note-by-note shaping.  Short entries get
# their own echo/swell; the chorales and formal transitions receive longer
# ensemble hairpins.
HAIRPIN_SPANS = (
    (9, 16, "crescendo", ("vln1", "vln2", "vla", "vc")),
    (25, 32, "crescendo", ("ob1", "vln1", "vla", "bn1")),
    (37, 40, "crescendo", ("ob2",)),
    (41, 44, "diminuendo", ("vla",)),
    (45, 48, "crescendo", ("vln2",)),
    (49, 52, "crescendo", ("vc",)),
    (53, 56, "diminuendo", ("vln1",)),
    (57, 60, "diminuendo", ("ob1",)),
    (61, 64, "crescendo", ("vln2",)),
    (65, 68, "crescendo", ("vla",)),
    (69, 70, "diminuendo", ("fl2",)),
    (71, 72, "crescendo", ("vln1",)),
    (73, 74, "diminuendo", ("vla",)),
    (75, 76, "crescendo", ("vln2",)),
    (77, 80, "diminuendo", ("vla",)),
    (81, 84, "crescendo", ("vln2",)),
    (85, 89, "crescendo", ("vln1",)),
    (113, 120, "diminuendo", ("ob1", "ob2", "bn1", "bn2")),
    (121, 132, "crescendo", ("vln1", "vln2", "vla", "vc")),
    (133, 140, "crescendo", ("fl1", "fl2", "ob1", "bn1")),
    (141, 148, "diminuendo", ("fl1", "fl2", "ob1", "bn1")),
    (153, 154, "crescendo", ("ob1",)),
    (155, 156, "diminuendo", ("vla",)),
    (157, 160, "crescendo", ("vln2",)),
    (161, 162, "diminuendo", ("vla",)),
    (163, 164, "crescendo", ("ob1",)),
    (165, 168, "crescendo", ("vln1",)),
    (177, 188, "crescendo", ("ob1", "ob2", "bn1", "bn2")),
    (189, 196, "diminuendo", ("ob1", "ob2", "bn1", "bn2")),
    (197, 208, "crescendo", ("fl1", "ob1", "vla", "cb")),
    (209, 212, "diminuendo", ("vln1", "vln2", "vla", "vc", "hn1", "hn2")),
    (217, 220, "crescendo", ("ob2",)),
    (221, 224, "diminuendo", ("vla",)),
    (225, 226, "crescendo", ("ob1",)),
    (227, 228, "crescendo", ("vln1",)),
    (229, 240, "crescendo", ("vln1", "vln2", "vla", "bn1", "ob1")),
    (241, 242, "diminuendo", ("fl1",)),
    (243, 244, "diminuendo", ("ob1",)),
    (245, 246, "diminuendo", ("vla",)),
    (247, 248, "diminuendo", ("vln1",)),
    (249, 254, "diminuendo", ("ob1", "vln1", "bn1", "cb", "hn1", "hn2")),
    (255, 257, "diminuendo", ("vln1", "vln2", "vla", "vc")),
)

# The late pillars at 209 and 249 are opened into fifth/minor spacings.
# Bar 257 is deliberately excluded: Bach's final two-string unison D is more
# telling than a completed orchestral triad.
PILLAR_VOICINGS = {
    209: {"hn1": 69, "hn2": 62, "tpt1": 74, "tpt2": 69},
    249: {"hn1": 69, "hn2": 62, "tpt1": 74, "tpt2": 65},
}


def bar_in_ranges(bar: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(first <= bar <= last for first, last in ranges)


def prevailing_dynamic(bar: int) -> str:
    return DYNAMIC_CHANGES[max(change for change in DYNAMIC_CHANGES if change <= bar)]


def hairpins_for(inst_key: str, bar: int, edge: str) -> list[str]:
    """Return wedge types beginning or ending in this bar for one part."""
    result = []
    for first, last, kind, targets in HAIRPIN_SPANS:
        boundary = first if edge == "start" else last
        if bar == boundary and inst_key in targets:
            result.append(kind if edge == "start" else "stop")
    return result


def section_for(bar: int):
    for section in SECTIONS:
        if section[0] <= bar <= section[1]:
            return section
    return SECTIONS[-1]


def ownership_for(bar: int) -> tuple[str, str, str, str]:
    """Return the four instrumental owners, with staggered choir handoffs.

    The formal sections remain clear, but changing two strands before the
    other two avoids the mechanical impression of an organ registration stop.
    """
    for first, last, mapping in MOTIVE_HANDOFFS:
        if first <= bar <= last:
            return mapping
    transitions = [
        (97, 98, ("ob1", "vln2", "bn1", "vc")),
        (133, 136, ("fl1", "vln2", "ob1", "bn1")),
        (177, 180, ("ob1", "vln2", "bn1", "vc")),
    ]
    for first, last, mapping in transitions:
        if first <= bar <= last:
            return mapping
    return section_for(bar)[2]


def monophonic_owner_for(bar: int) -> str:
    """Return the phrase-level owner for an isolated source note."""
    for first, last, owner in MONOPHONIC_RELAYS:
        if first <= bar <= last:
            return owner
    return ownership_for(bar)[0]


def dynamic_velocity(bar: int, family: str, original: int) -> int:
    base = 67
    if 97 <= bar <= 120 or 177 <= bar <= 196:
        base = 57
    elif 133 <= bar <= 168:
        base = 65
    elif 209 <= bar <= 228:
        base = 72
    elif 229 <= bar <= 240:
        base = 84
    elif 241 <= bar <= 248:
        base = 68
    elif bar >= 249:
        base = max(48, 72 - (bar - 249) * 3)
    family_offset = {"flute": -2, "oboe": 0, "bassoon": -1, "strings": 0}.get(family, 0)
    return max(36, min(104, int(base + family_offset + (original - 64) * 0.12)))


def monophonic_note_ids(voices: list[list[Note]]) -> set[int]:
    """Return notes that never overlap another source note.

    The separated voice index is meaningful during simultaneous counterpoint,
    but can jump registral lanes in a single-line passage.  Treating those
    isolated notes as separate orchestral strands creates note-by-note timbral
    flicker, so they are consolidated onto the principal owner instead.
    """
    by_start: dict[int, list[Note]] = {}
    for voice in voices:
        for note in voice:
            by_start.setdefault(note.start, []).append(note)
    overlapping: set[int] = set()
    active: list[Note] = []
    for start in sorted(by_start):
        active = [note for note in active if note.end > start]
        entering = by_start[start]
        if active or len(entering) > 1:
            overlapping.update(id(note) for note in active)
            overlapping.update(id(note) for note in entering)
        active.extend(entering)
    return {
        id(note)
        for voice in voices
        for note in voice
        if id(note) not in overlapping
    }


def orchestrate(voices: list[list[Note]]) -> dict[str, list[Note]]:
    parts: dict[str, list[Note]] = {i.key: [] for i in INSTRUMENTS}
    monophonic = monophonic_note_ids(voices)
    for voice_idx, voice in enumerate(voices):
        for n in voice:
            bar = score_bar(n.start)
            owners = ownership_for(bar)
            target = monophonic_owner_for(bar) if id(n) in monophonic else owners[voice_idx]
            inst = INST[target]
            pitch = n.pitch - 12 if target == "cb" else n.pitch
            parts[target].append(Note(n.start, n.end, pitch,
                                      dynamic_velocity(bar, inst.family, n.velocity)))

    # Sustained brass sonorities exist only at large joints in the architecture.
    horn_bars = [97, 113, 169, 177, 197, 209, 229, 249]
    trumpet_bars = [209, 229, 249]
    timpani_bars = [209, 229, 249]
    source = [n for v in voices for n in v]

    def harmony_at(bar: int) -> list[int]:
        t = bar_start(bar)
        near = [n.pitch for n in source if n.start <= t < n.end]
        if not near:
            near = [n.pitch for n in source if t <= n.start < t + TPQ // 2]
        pcs = sorted(set(p % 12 for p in near))
        return pcs or [2, 9]

    def place_in_range(pc: int, low: int, high: int, prefer: int) -> int:
        choices = [p for p in range(low, high + 1) if p % 12 == pc]
        return min(choices, key=lambda p: abs(p - prefer))

    for bar in horn_bars:
        pcs = harmony_at(bar)
        low_pc, high_pc = pcs[0], pcs[-1]
        start = bar_start(bar)
        duration = BAR * (2 if bar in (97, 177) else 1)
        voicing = PILLAR_VOICINGS.get(bar, {})
        parts["hn1"].append(Note(start, start + duration,
                                  voicing.get("hn1", place_in_range(high_pc, 55, 74, 67)),
                                  64 if bar < 209 else 78))
        parts["hn2"].append(Note(start, start + duration,
                                  voicing.get("hn2", place_in_range(low_pc, 48, 67, 57)),
                                  61 if bar < 209 else 75))
    for bar in trumpet_bars:
        pcs = harmony_at(bar)
        start = bar_start(bar)
        dur = TPQ * 2
        voicing = PILLAR_VOICINGS.get(bar, {})
        parts["tpt1"].append(Note(start, start + dur,
                                   voicing.get("tpt1", place_in_range(pcs[-1], 62, 82, 74)),
                                   82 if bar < 249 else 88))
        second_dur = TPQ * 3 // 2
        parts["tpt2"].append(Note(start, start + second_dur,
                                   voicing.get("tpt2", place_in_range(pcs[0], 57, 76, 66)),
                                   78 if bar < 249 else 84))
    for bar in timpani_bars:
        start = bar_start(bar)
        tonic = 38  # D2
        dominant = 45  # A2
        parts["timp"].append(Note(start, start + TPQ, tonic, 78 if bar < 249 else 90))
        parts["timp"].append(Note(start + TPQ * 2, start + BAR, dominant, 68))

    for key in parts:
        parts[key].sort(key=lambda n: (n.start, n.end, n.pitch))
    return parts


def vlq(value: int) -> bytes:
    buf = [value & 0x7F]
    value >>= 7
    while value:
        buf.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(buf))


def meta(kind: int, payload: bytes) -> bytes:
    return bytes([0xFF, kind]) + vlq(len(payload)) + payload


def midi_track(events: list[tuple[int, int, bytes]]) -> bytes:
    # priority 0 events (note-offs) precede note-ons at the same tick
    body = bytearray()
    last = 0
    for tick, _priority, payload in sorted(events, key=lambda e: (e[0], e[1])):
        body += vlq(max(0, tick - last)) + payload
        last = tick
    body += vlq(0) + meta(0x2F, b"")
    return b"MTrk" + len(body).to_bytes(4, "big") + body


def performance_end(note: Note, inst: Instrument) -> int:
    """Gate sustained wind/string notes without changing the written rhythm."""
    bar = score_bar(note.start)
    duration = note.end - note.start
    # Structural releases belong to playback, not to the written rhythm.  The
    # previous MusicXML encoded these tiny gaps literally (20/384 and 24/384
    # of a quarter), leaving importers to invent invalid note values.
    if inst.family == "horn":
        return note.end - 24
    if inst.family == "timpani":
        return note.end - 20
    if (inst.family not in {"flute", "oboe", "bassoon", "strings"}
            or not bar_in_ranges(bar, REFINED_RANGES)
            or bar_in_ranges(bar, RIPIENO_RANGES)
            or duration < TPQ // 2):
        return note.end
    gap = min(TPQ // 10, duration // 8)
    return max(note.start + TPQ // 4, note.end - gap)


def write_midi(parts: dict[str, list[Note]], path: Path) -> None:
    tempo_events: list[tuple[int, int, bytes]] = [
        (0, 0, meta(0x03, b"BWV 1004a - control track")),
        (0, 0, meta(0x58, bytes([3, 2, 24, 8]))),
        (0, 0, meta(0x59, bytes([0xFF, 0]))),  # one flat, minor
        (bar_start(133), 0, meta(0x59, bytes([2, 0]))),
        (bar_start(209), 0, meta(0x59, bytes([0xFF, 0]))),
    ]
    for start, _end, _mapping, bpm, label in SECTIONS:
        use_bpm = bpm
        mpqn = round(60_000_000 / use_bpm)
        tempo_events.append((bar_start(start), 0, meta(0x51, mpqn.to_bytes(3, "big"))))
        tempo_events.append((bar_start(start), 0, meta(0x06, label.encode("utf-8"))))
    tracks = [midi_track(tempo_events)]
    for inst in INSTRUMENTS:
        events: list[tuple[int, int, bytes]] = [
            (0, 0, meta(0x03, inst.name.encode("utf-8"))),
            (0, 0, bytes([0xC0 | inst.channel, inst.program])),
            (0, 0, bytes([0xB0 | inst.channel, 10, inst.pan])),
            (0, 0, bytes([0xB0 | inst.channel, 7, 104])),
        ]
        for note in parts[inst.key]:
            events.append((note.start, 1, bytes([0x90 | inst.channel, note.pitch, note.velocity])))
            events.append((performance_end(note, inst), 0,
                           bytes([0x80 | inst.channel, note.pitch, 40])))
        tracks.append(midi_track(events))
    header = b"MThd" + (6).to_bytes(4, "big") + (1).to_bytes(2, "big")
    header += len(tracks).to_bytes(2, "big") + TPQ.to_bytes(2, "big")
    path.write_bytes(header + b"".join(tracks))


MINOR_NAMES = {
    0: ("C", 0), 1: ("C", 1), 2: ("D", 0), 3: ("E", -1),
    4: ("E", 0), 5: ("F", 0), 6: ("F", 1), 7: ("G", 0),
    8: ("A", -1), 9: ("A", 0), 10: ("B", -1), 11: ("B", 0),
}
MAJOR_NAMES = {
    0: ("C", 0), 1: ("C", 1), 2: ("D", 0), 3: ("D", 1),
    4: ("E", 0), 5: ("F", 0), 6: ("F", 1), 7: ("G", 0),
    8: ("G", 1), 9: ("A", 0), 10: ("A", 1), 11: ("B", 0),
}


def add_text(parent, tag: str, text: str, **attrs):
    node = ET.SubElement(parent, tag, attrs)
    node.text = text
    return node


def _duration_vocabulary() -> tuple[WrittenDuration, ...]:
    bases = (
        ("whole", TPQ * 4),
        ("half", TPQ * 2),
        ("quarter", TPQ),
        ("eighth", TPQ // 2),
        ("16th", TPQ // 4),
        ("32nd", TPQ // 8),
        ("64th", TPQ // 16),
        ("128th", TPQ // 32),
    )
    values: dict[tuple[int, int | None, int | None], WrittenDuration] = {}
    for note_type, base in bases:
        for dots in range(4):
            numerator = (2 ** (dots + 1)) - 1
            denominator = 2 ** dots
            if (base * numerator) % denominator:
                continue
            ticks = base * numerator // denominator
            values[(ticks, None, None)] = WrittenDuration(ticks, note_type, dots)
        # Ordinary triplets: three values in the time of two.  Dotted
        # tuplets are deliberately omitted; tied ordinary values are clearer.
        if (base * 2) % 3 == 0:
            ticks = base * 2 // 3
            values[(ticks, 3, 2)] = WrittenDuration(
                ticks, note_type, actual_notes=3, normal_notes=2
            )
    return tuple(sorted(
        values.values(),
        key=lambda item: (-item.ticks, item.actual_notes is not None, item.dots),
    ))


DURATION_VOCABULARY = _duration_vocabulary()


@lru_cache(maxsize=None)
def spell_duration(ticks: int) -> tuple[WrittenDuration, ...]:
    """Decompose a span into the fewest exact, conventional note values."""
    if ticks <= 0:
        raise ValueError(f"Duration must be positive, got {ticks}")
    candidates: list[tuple[WrittenDuration, ...]] = []
    for value in DURATION_VOCABULARY:
        if value.ticks > ticks:
            continue
        if value.ticks == ticks:
            candidates.append((value,))
            continue
        try:
            tail = spell_duration(ticks - value.ticks)
        except ValueError:
            continue
        candidates.append((value,) + tail)
    if not candidates:
        raise ValueError(
            f"Cannot spell {ticks} ticks using standard values or 3:2 tuplets"
        )
    return min(candidates, key=lambda result: (
        len(result),
        sum(value.actual_notes is not None for value in result),
        sum(value.dots for value in result),
    ))


def append_written_duration(note_el, value: WrittenDuration) -> None:
    add_text(note_el, "type", value.note_type)
    for _ in range(value.dots):
        ET.SubElement(note_el, "dot")
    if value.actual_notes is not None:
        modification = ET.SubElement(note_el, "time-modification")
        add_text(modification, "actual-notes", str(value.actual_notes))
        add_text(modification, "normal-notes", str(value.normal_notes))
        add_text(modification, "normal-type", value.note_type)


def append_rest_events(measure, ticks: int, *, measure_rest: bool = False) -> None:
    values = spell_duration(ticks)
    if measure_rest and len(values) != 1:
        raise ValueError(f"Full-measure rest unexpectedly needs {len(values)} values")
    for value in values:
        rest_el = ET.SubElement(measure, "note")
        ET.SubElement(rest_el, "rest", measure="yes" if measure_rest else "no")
        add_text(rest_el, "duration", str(value.ticks))
        add_text(rest_el, "voice", "1")
        append_written_duration(rest_el, value)


def append_direction(
    measure,
    words: str,
    bpm: int | None = None,
    rehearsal: str | None = None,
    offset: int | None = None,
):
    direction = ET.SubElement(measure, "direction", placement="above")
    dtype = ET.SubElement(direction, "direction-type")
    if rehearsal:
        add_text(dtype, "rehearsal", rehearsal, enclosure="rectangle")
    add_text(dtype, "words", words, **{"font-style": "italic"})
    if offset:
        add_text(direction, "offset", str(offset))
    if bpm:
        sound = ET.SubElement(direction, "sound", tempo=str(bpm))
        sound.set("dynamics", "70")


def append_dynamic(measure, mark: str) -> None:
    direction = ET.SubElement(measure, "direction", placement="below")
    dtype = ET.SubElement(direction, "direction-type")
    dynamics = ET.SubElement(dtype, "dynamics")
    ET.SubElement(dynamics, mark)
    ET.SubElement(direction, "sound", dynamics=str(DYNAMIC_LEVELS[mark]))


def append_wedge(measure, wedge_type: str, number: int) -> None:
    direction = ET.SubElement(measure, "direction", placement="below")
    dtype = ET.SubElement(direction, "direction-type")
    ET.SubElement(dtype, "wedge", type=wedge_type, number=str(number))


def beat_slur_plan(notes: list[Note]) -> tuple[set[int], set[int]]:
    """Slur contiguous short-note gestures within each notated beat."""
    starts: set[int] = set()
    stops: set[int] = set()
    by_beat: dict[int, list[Note]] = {}
    for note in notes:
        beat = (note.start - bar_start(score_bar(note.start))) // TPQ
        by_beat.setdefault(beat, []).append(note)
    for beat_notes in by_beat.values():
        run: list[Note] = []
        for note in sorted(beat_notes, key=lambda item: item.start):
            short = note.end - note.start <= TPQ // 2
            contiguous = not run or run[-1].end == note.start
            if short and contiguous:
                run.append(note)
                continue
            if len(run) >= 2:
                starts.add(id(run[0]))
                stops.add(id(run[-1]))
            run = [note] if short else []
        if len(run) >= 2:
            starts.add(id(run[0]))
            stops.add(id(run[-1]))
    return starts, stops


def split_at_barlines(notes: list[Note]) -> list[Note]:
    result: list[Note] = []
    for note in notes:
        cursor = note.start
        first = True
        while cursor < note.end:
            bar = score_bar(cursor)
            boundary = PICKUP if bar == 1 else bar_start(bar) + BAR
            end = min(note.end, boundary)
            result.append(Note(cursor, end, note.pitch, note.velocity,
                               tie_start=end < note.end,
                               tie_stop=not first))
            cursor = end
            first = False
    return result


def write_musicxml(parts: dict[str, list[Note]], path: Path) -> None:
    root = ET.Element("score-partwise", version="4.0")
    work = ET.SubElement(root, "work")
    add_text(work, "work-title", "Chaconne in D minor, BWV 1004a (imaginary orchestral version)")
    identification = ET.SubElement(root, "identification")
    add_text(identification, "creator", "Johann Sebastian Bach", type="composer")
    add_text(identification, "creator", "Codex (OpenAI; GPT-5.6 Sol High)", type="arranger")
    add_text(identification, "creator", "Created in collaboration with the repository owner", type="other")
    add_text(identification, "rights", "Source engraving: Hajo Dezelski / Mutopia Project, CC BY-SA 3.0. Arrangement shared under CC BY-SA 3.0.")
    encoding = ET.SubElement(identification, "encoding")
    add_text(encoding, "software", "Codex transparent-orchestra generator")
    defaults = ET.SubElement(root, "defaults")
    scaling = ET.SubElement(defaults, "scaling")
    add_text(scaling, "millimeters", "7.0")
    add_text(scaling, "tenths", "40")
    part_list = ET.SubElement(root, "part-list")
    for idx, inst in enumerate(INSTRUMENTS, 1):
        sp = ET.SubElement(part_list, "score-part", id=f"P{idx}")
        add_text(sp, "part-name", inst.name)
        add_text(sp, "part-abbreviation", inst.abbreviation)
        si = ET.SubElement(sp, "score-instrument", id=f"P{idx}-I1")
        add_text(si, "instrument-name", inst.name)
        mi = ET.SubElement(sp, "midi-instrument", id=f"P{idx}-I1")
        add_text(mi, "midi-channel", str(inst.channel + 1))
        add_text(mi, "midi-program", str(inst.program + 1))
        add_text(mi, "volume", "82")
        add_text(mi, "pan", str(round((inst.pan - 64) / 63 * 90)))

    section_starts = {s[0]: s for s in SECTIONS}
    letters = "ABCDEFGHIJKLMNOPQ"
    for idx, inst in enumerate(INSTRUMENTS, 1):
        part = ET.SubElement(root, "part", id=f"P{idx}")
        split = split_at_barlines(parts[inst.key])
        by_bar: dict[int, list[Note]] = {}
        for n in split:
            by_bar.setdefault(score_bar(n.start), []).append(n)
        for bar in range(1, 258):
            measure = ET.SubElement(part, "measure", number=str(bar), implicit="yes" if bar == 1 else "no")
            if bar in (1, 133, 209):
                attrs = ET.SubElement(measure, "attributes")
                if bar == 1:
                    add_text(attrs, "divisions", str(TPQ))
                key = ET.SubElement(attrs, "key")
                add_text(key, "fifths", "2" if 133 <= bar < 209 else "-1")
                add_text(key, "mode", "major" if 133 <= bar < 209 else "minor")
                if bar == 1:
                    time = ET.SubElement(attrs, "time")
                    add_text(time, "beats", "3")
                    add_text(time, "beat-type", "4")
                    clef = ET.SubElement(attrs, "clef")
                    add_text(clef, "sign", inst.clef)
                    add_text(clef, "line", "3" if inst.clef == "C" else ("4" if inst.clef == "F" else "2"))
            if idx == 1 and bar in section_starts:
                section = section_starts[bar]
                letter = letters[list(section_starts).index(bar)]
                append_direction(measure, section[4], section[3], letter)
            if inst.family == "strings" and bar in STRING_TEXTURE_MARKS:
                append_direction(measure, STRING_TEXTURE_MARKS[bar])
            arpeggio = ARPEGGIO_DIRECTIONS.get((inst.key, bar))
            if arpeggio:
                offset, words = arpeggio
                append_direction(measure, words, offset=offset)
            if inst.key == "vln1" and bar == 257:
                append_direction(measure, FINAL_UNISON_DIRECTION)
            bar_notes = sorted(by_bar.get(bar, []), key=lambda x: (x.start, x.pitch))
            previous_bar_sounds = bool(by_bar.get(bar - 1, []))
            if bar_notes and (bar in DYNAMIC_CHANGES or not previous_bar_sounds):
                append_dynamic(measure, prevailing_dynamic(bar))
            for wedge_number, wedge_type in enumerate(
                hairpins_for(inst.key, bar, "start"), 1
            ):
                append_wedge(measure, wedge_type, wedge_number)
            if inst.family in {"flute", "oboe", "bassoon", "strings"}:
                slur_starts, slur_stops = beat_slur_plan(bar_notes)
            else:
                slur_starts, slur_stops = set(), set()
            relay_ending = any(
                last == bar and owner == inst.key
                for _first, last, owner in MONOPHONIC_RELAYS
            )
            cursor = bar_start(bar)
            end_bar = PICKUP if bar == 1 else cursor + BAR
            for note_index, n in enumerate(bar_notes):
                if n.start > cursor:
                    append_rest_events(measure, n.start - cursor)
                if n.start < cursor:
                    # Should not occur in the separated monophonic material.
                    continue
                values = spell_duration(n.end - n.start)
                for value_index, value in enumerate(values):
                    note_el = ET.SubElement(measure, "note")
                    pitch = ET.SubElement(note_el, "pitch")
                    names = MAJOR_NAMES if 133 <= bar < 209 else MINOR_NAMES
                    step, alter = names[n.pitch % 12]
                    add_text(pitch, "step", step)
                    if alter:
                        add_text(pitch, "alter", str(alter))
                    add_text(pitch, "octave", str(n.pitch // 12 - 1))
                    add_text(note_el, "duration", str(value.ticks))
                    tie_stop = n.tie_stop or value_index > 0
                    tie_start = n.tie_start or value_index < len(values) - 1
                    if tie_stop:
                        ET.SubElement(note_el, "tie", type="stop")
                    if tie_start:
                        ET.SubElement(note_el, "tie", type="start")
                    add_text(note_el, "voice", "1")
                    append_written_duration(note_el, value)
                    slur_start = id(n) in slur_starts and value_index == 0
                    slur_stop = id(n) in slur_stops and value_index == len(values) - 1
                    source_event = (bar, n.start - bar_start(bar), n.pitch)
                    source_trill = source_event in SOURCE_TRILLS and value_index == 0
                    source_fermata = (
                        source_event in SOURCE_FERMATAS
                        and value_index == len(values) - 1
                    )
                    phrase_end = (
                        relay_ending
                        and note_index == len(bar_notes) - 1
                        and value_index == len(values) - 1
                        and not tie_start
                    )
                    structural_accent = (
                        bar in {209, 229, 249}
                        and note_index == 0
                        and value_index == 0
                        and inst.family in {"horn", "trumpet", "timpani"}
                    )
                    if (tie_start or tie_stop or slur_start or slur_stop
                            or source_trill or source_fermata
                            or phrase_end or structural_accent):
                        notations = ET.SubElement(note_el, "notations")
                        if tie_stop:
                            ET.SubElement(notations, "tied", type="stop")
                        if tie_start:
                            ET.SubElement(notations, "tied", type="start")
                        if slur_start:
                            ET.SubElement(notations, "slur", type="start", number="1")
                        if slur_stop:
                            ET.SubElement(notations, "slur", type="stop", number="1")
                        if source_trill:
                            ornaments = ET.SubElement(notations, "ornaments")
                            ET.SubElement(ornaments, "trill-mark")
                        if source_fermata:
                            fermata = ET.SubElement(notations, "fermata", type="upright")
                            fermata.text = "normal"
                        if phrase_end or structural_accent:
                            articulations = ET.SubElement(notations, "articulations")
                            if phrase_end and inst.family in {"flute", "oboe", "bassoon"}:
                                ET.SubElement(articulations, "breath-mark")
                            elif phrase_end:
                                ET.SubElement(articulations, "tenuto")
                            if structural_accent:
                                ET.SubElement(articulations, "accent")
                cursor = n.end
            if cursor < end_bar:
                append_rest_events(
                    measure,
                    end_bar - cursor,
                    measure_rest=cursor == bar_start(bar),
                )
            for wedge_number, wedge_type in enumerate(
                hairpins_for(inst.key, bar, "stop"), 1
            ):
                append_wedge(measure, wedge_type, wedge_number)
    ET.indent(root, space="  ")
    xml = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
    xml += '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">\n'
    xml += ET.tostring(root, encoding="unicode")
    path.write_text(xml, encoding="utf-8")


def write_mxl(xml_path: Path, mxl_path: Path) -> None:
    container = """<?xml version="1.0" encoding="UTF-8"?>
<container>
  <rootfiles>
    <rootfile full-path="score.musicxml" media-type="application/vnd.recordare.musicxml+xml"/>
  </rootfiles>
</container>
"""
    with zipfile.ZipFile(mxl_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("META-INF/container.xml", container)
        zf.write(xml_path, "score.musicxml")


def tempo_map():
    return [(bar_start(s[0]), s[3]) for s in SECTIONS]


def tick_to_seconds(tick: int) -> float:
    points = tempo_map()
    seconds = 0.0
    previous_tick, bpm = points[0]
    for next_tick, next_bpm in points[1:]:
        if tick <= next_tick:
            break
        seconds += (next_tick - previous_tick) / TPQ * 60.0 / bpm
        previous_tick, bpm = next_tick, next_bpm
    seconds += (tick - previous_tick) / TPQ * 60.0 / bpm
    return seconds


def synth_wave(family: str, frequency: float, t: np.ndarray) -> np.ndarray:
    phase = 2 * np.pi * frequency * t
    if family == "flute":
        y = np.sin(phase) + 0.16 * np.sin(2 * phase) + 0.06 * np.sin(3 * phase)
    elif family == "oboe":
        y = np.sin(phase) + 0.44 * np.sin(2 * phase) + 0.30 * np.sin(3 * phase) + 0.12 * np.sin(4 * phase)
    elif family == "bassoon":
        y = np.sin(phase) + 0.38 * np.sin(2 * phase) + 0.18 * np.sin(3 * phase)
    elif family == "horn":
        y = np.sin(phase) + 0.28 * np.sin(2 * phase) + 0.13 * np.sin(3 * phase)
    elif family == "trumpet":
        y = np.sin(phase) + 0.50 * np.sin(2 * phase) + 0.28 * np.sin(3 * phase) + 0.16 * np.sin(4 * phase)
    elif family == "timpani":
        y = np.sin(phase) + 0.45 * np.sin(1.51 * phase) + 0.16 * np.sin(2.03 * phase)
    else:
        y = np.sin(phase) + 0.32 * np.sin(2 * phase) + 0.16 * np.sin(3 * phase) + 0.08 * np.sin(4 * phase)
    return y.astype(np.float32)


def render_audio(parts: dict[str, list[Note]], wav_path: Path, sample_rate: int = 22050) -> None:
    last_tick = max(n.end for notes in parts.values() for n in notes)
    duration = tick_to_seconds(last_tick) + 2.0
    frames = int(duration * sample_rate)
    mmap_path = BUILD / "chaconne_audio_mix.dat"
    audio = np.memmap(mmap_path, dtype=np.float32, mode="w+", shape=(frames, 2))
    audio[:] = 0
    for inst in INSTRUMENTS:
        pan = (inst.pan - 64) / 64
        left = math.sqrt((1 - pan) / 2)
        right = math.sqrt((1 + pan) / 2)
        for note in parts[inst.key]:
            start_s = tick_to_seconds(note.start)
            end_s = tick_to_seconds(performance_end(note, inst))
            dur = max(0.03, end_s - start_s)
            start = int(start_s * sample_rate)
            count = min(frames - start, int((dur + 0.10) * sample_rate))
            if count <= 0:
                continue
            t = np.arange(count, dtype=np.float32) / sample_rate
            freq = 440.0 * 2 ** ((note.pitch - 69) / 12)
            y = synth_wave(inst.family, freq, t)
            attack = 0.018 if inst.family in ("strings", "flute") else 0.028
            if inst.family == "timpani":
                env = np.exp(-t * 2.8)
            else:
                release = 0.10
                env = np.minimum(1.0, t / attack)
                env *= np.minimum(1.0, np.maximum(0.0, (dur + release - t) / release))
                env *= (0.95 + 0.05 * np.sin(2 * np.pi * 5.1 * t))
            amp = (note.velocity / 127) ** 1.7 * 0.065
            signal = y * env.astype(np.float32) * amp
            audio[start:start + count, 0] += signal * left
            audio[start:start + count, 1] += signal * right
    # A short, restrained room response keeps the contrapuntal attacks legible.
    for delay_s, gain in ((0.075, 0.16), (0.145, 0.09)):
        delay = int(delay_s * sample_rate)
        audio[delay:] += audio[:-delay] * gain
    peak = float(np.max(np.abs(audio)))
    scale = 0.92 / peak if peak > 0 else 1.0
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        chunk = sample_rate * 10
        for start in range(0, frames, chunk):
            block = np.asarray(audio[start:start + chunk] * scale)
            wf.writeframes((np.clip(block, -1, 1) * 32767).astype("<i2").tobytes())
    del audio
    mmap_path.unlink(missing_ok=True)


def validate(parts: dict[str, list[Note]], original: list[Note], voices: list[list[Note]]) -> None:
    structural = {"hn1", "hn2", "tpt1", "tpt2", "timp"}
    owned_notes = [n for key, notes in parts.items() if key not in structural for n in notes]
    expected = [n for voice in voices for n in voice]
    owned = len(owned_notes)
    if owned != len(expected):
        raise AssertionError(
            f"Unexpected source-note count: {owned} orchestrated vs {len(expected)} expected"
        )
    source_identity = sorted((n.start, n.end, n.pitch % 12) for n in expected)
    arranged_identity = sorted((n.start, n.end, n.pitch % 12) for n in owned_notes)
    if arranged_identity != source_identity:
        raise AssertionError("The orchestration altered source rhythms or pitch classes")
    for key, (low, high) in PROFESSIONAL_RANGES.items():
        outside = [n for n in parts[key] if not low <= n.pitch <= high]
        if outside:
            bars = sorted({score_bar(n.start) for n in outside})
            raise AssertionError(
                f"{INST[key].name} outside professional range {low}-{high} "
                f"in bars {bars}"
            )
    for bar, voicing in PILLAR_VOICINGS.items():
        for key, expected_pitch in voicing.items():
            notes = [n for n in parts[key] if score_bar(n.start) == bar]
            if len(notes) != 1 or notes[0].pitch != expected_pitch:
                raise AssertionError(
                    f"Unexpected {key} voicing at bar {bar}: {notes}"
                )
        trumpet_one = next(n for n in parts["tpt1"] if score_bar(n.start) == bar)
        trumpet_two = next(n for n in parts["tpt2"] if score_bar(n.start) == bar)
        if trumpet_two.end >= trumpet_one.end:
            raise AssertionError(f"Trumpet II must release first at bar {bar}")
    # The exposed violinistic spans may remain transparent, but no one player
    # should carry more than a four-bar unaccompanied cell there.
    relay_ranges = ((31, 89), (153, 168), (217, 228), (241, 248))
    sounding_by_bar = {bar: set() for bar in range(1, 258)}
    for key, notes in parts.items():
        if key in structural:
            continue
        for note in notes:
            sounding_by_bar[score_bar(note.start)].add(key)
    for first, last in relay_ranges:
        previous_owner = None
        run = 0
        for bar in range(first, last + 1):
            owners = sounding_by_bar[bar]
            sole_owner = next(iter(owners)) if len(owners) == 1 else None
            run = run + 1 if sole_owner == previous_owner and sole_owner else int(bool(sole_owner))
            previous_owner = sole_owner
            if run > 4:
                raise AssertionError(
                    f"Unaccompanied {sole_owner} phrase exceeds four bars at bar {bar}"
                )
    for key, notes in parts.items():
        if key in {"hn1", "hn2", "tpt1", "tpt2", "timp"}:
            continue
        for a, b in zip(notes, notes[1:]):
            if b.start < a.end:
                raise AssertionError(f"Overlapping notes in {key} at {b.start}")
    final_structural = [
        (key, note.pitch)
        for key in structural
        for note in parts[key]
        if score_bar(note.start) == 257
    ]
    if final_structural:
        raise AssertionError(
            f"Bach's final unison D must remain unbrassed: {final_structural}"
        )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    original = parse_midi_notes(SOURCE_MIDI)
    voices = separate_voices(original)
    parts = orchestrate(voices)
    validate(parts, original, voices)
    midi_path = OUT / "Bach_BWV1004a_transparent_orchestra.mid"
    xml_path = OUT / "Bach_BWV1004a_transparent_orchestra.musicxml"
    mxl_path = OUT / "Bach_BWV1004a_transparent_orchestra.mxl"
    wav_path = BUILD / "Bach_BWV1004a_transparent_orchestra.wav"
    write_midi(parts, midi_path)
    write_musicxml(parts, xml_path)
    write_mxl(xml_path, mxl_path)
    render_audio(parts, wav_path)
    print(f"source_notes={len(original)}")
    print("voices=" + ",".join(str(len(v)) for v in voices))
    structural = {"hn1", "hn2", "tpt1", "tpt2", "timp"}
    owned_count = sum(len(notes) for key, notes in parts.items() if key not in structural)
    print(f"source_note_omissions={len(original) - owned_count}")
    print("parts=" + ",".join(f"{k}:{len(v)}" for k, v in parts.items()))
    print(f"duration_seconds={tick_to_seconds(max(n.end for n in original)):.2f}")
    print(wav_path)


if __name__ == "__main__":
    main()
