"""One-time port of the MusicXML master into the LilyPond source tree under ly/.

Replay from the repository root:

    python3 build/lilypond-port-2026-10-15/import_musicxml.py [path/to/master.musicxml]

The default input is the last MusicXML master before the port (git 7730806).
This script is kept for provenance; it is not part of the build. After the
port, ly/ is the source of truth and MusicXML is generated from it.
"""

from __future__ import annotations

import collections
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STEM = "Bach_BWV1004a_Leipzig_orchestral_realization"
DIVISIONS = 384

# MusicXML part id -> (LilyPond variable / Voice id, file slug)
PARTS = {
    "P1": ("fluteOne", "01-flute-1"),
    "P2": ("fluteTwo", "02-flute-2"),
    "P3": ("oboeOne", "03-oboe-1"),
    "P4": ("oboeTwo", "04-oboe-2"),
    "P5": ("bassoonOne", "05-bassoon-1"),
    "P6": ("bassoonTwo", "06-bassoon-2"),
    "P7": ("hornOne", "07-horn-1"),
    "P8": ("hornTwo", "08-horn-2"),
    "P9": ("trumpetOne", "09-trumpet-1"),
    "P10": ("trumpetTwo", "10-trumpet-2"),
    "P11": ("timpani", "11-timpani"),
    "P12": ("violinOne", "12-violin-1"),
    "P13": ("violinTwo", "13-violin-2"),
    "P14": ("viola", "14-viola"),
    "P15": ("violoncello", "15-violoncello"),
    "P16": ("doubleBass", "16-double-bass"),
}
BRASS = {"P7", "P8", "P9", "P10"}
TYPE_DURATION = {"whole": "1", "half": "2", "quarter": "4", "eighth": "8",
                 "16th": "16", "32nd": "32", "64th": "64"}
ARTICULATIONS = {"staccato": "-.", "tenuto": "--", "accent": "->"}
STRUCTURE_WORDS = {"poco accel.", "poco rit.",
                   "Ripieno strings 4.4.3.2.1; concertino one player per part"}


def lily_string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def markup(words: ET.Element) -> str:
    text = lily_string(words.text or "")
    if words.get("font-style") == "italic":
        return f"\\markup \\italic {text}"
    return f"\\markup {text}"


def pitch_name(step: str, alter: int) -> str:
    name = step.lower()
    if alter > 0:
        return name + "is" * alter
    if alter < 0:
        if name in ("e", "a"):
            return name + "s" + "es" * (-alter - 1)
        return name + "es" * -alter
    return name


def octave_marks(offset: int) -> str:
    return "'" * offset if offset > 0 else "," * -offset


def base_octave(part: ET.Element) -> int:
    octaves = collections.Counter(
        int(p.findtext("octave")) for p in part.iter("pitch"))
    return octaves.most_common(1)[0][0] if octaves else 4


def fixed_base(octave: int) -> str:
    return "c" + octave_marks(octave - 3)


def duration_string(note: ET.Element) -> str:
    return TYPE_DURATION[note.findtext("type")] + "." * len(note.findall("dot"))


def bar_length(number: int) -> int:
    return DIVISIONS * 2 if number == 1 else DIVISIONS * 3


def measure_rest_duration(number: int) -> str:
    return "2" if number == 1 else "2."


def direction_posts(direction: ET.Element, at_bar_end: bool = False) -> list[str]:
    """LilyPond post-events for one MusicXML <direction>."""
    posts: list[str] = []
    offset = direction.findtext("offset")
    for kind in direction.find("direction-type"):
        if kind.tag == "dynamics":
            posts.append("\\" + kind[0].tag)
        elif kind.tag == "wedge":
            wedge = {"crescendo": "\\<", "diminuendo": "\\>", "stop": "\\!"}[kind.get("type")]
            posts.append(("\\xmlBarEnd " if at_bar_end else "") + wedge)
        elif kind.tag == "words":
            text = markup(kind)
            if offset:
                posts.append(f"-\\xmlOffset #{offset} ^{text}")
            else:
                posts.append("^" + text)
        else:
            raise ValueError(f"unexpected direction type {kind.tag}")
    if at_bar_end and any(not p.startswith("\\xmlBarEnd") for p in posts):
        raise ValueError("only hairpin endings are expected at a barline")
    return posts


def post_order(posts: list[str]) -> list[str]:
    """Hairpin stops before new hairpin starts; text last."""
    def rank(post: str) -> int:
        if post.endswith("\\!"):
            return 0
        if post.startswith("\\") and post[1:] in ("pp", "p", "mp", "mf", "f", "ff"):
            return 1
        if post in ("\\<", "\\>"):
            return 2
        return 3
    return sorted(posts, key=rank)


class PartWriter:
    def __init__(self, part: ET.Element, pid: str, is_brass: bool):
        self.part = part
        self.pid = pid
        self.octave = base_octave(part)
        self.is_brass = is_brass

    def note_token(self, note: ET.Element, posts: list[str], with_duration: bool) -> tuple[str, list[str]]:
        rest = note.find("rest")
        duration = duration_string(note)
        if rest is not None:
            # LilyPond multi-measure rests cannot start mid-bar, so the
            # pickup's whole-bar rest becomes an ordinary half rest.
            whole_bar = rest.get("measure") == "yes" and note.findtext("duration") != str(2 * DIVISIONS)
            head = "R" if whole_bar else "r"
        else:
            pitch = note.find("pitch")
            head = pitch_name(pitch.findtext("step"), int(pitch.findtext("alter", "0")))
            head += octave_marks(int(pitch.findtext("octave")) - self.octave)
        token = head + (duration if with_duration else "")
        notation_posts: list[str] = []
        after: list[str] = []
        notations = note.find("notations")
        if notations is not None:
            for art in notations.iter():
                if art.tag in ARTICULATIONS:
                    notation_posts.append(ARTICULATIONS[art.tag])
                elif art.tag == "trill-mark":
                    notation_posts.append("\\trill")
                elif art.tag == "fermata":
                    notation_posts.append("\\fermata")
                elif art.tag == "breath-mark":
                    after.append("\\breathe")
            for slur in notations.findall("slur"):
                notation_posts.append("(" if slur.get("type") == "start" else ")")
        return token + "".join(notation_posts + post_order(posts)), after

    def measures(self):
        for measure in self.part.findall("measure"):
            yield int(measure.get("number")), measure

    def is_plain_rest_bar(self, measure: ET.Element) -> bool:
        notes = measure.findall("note")
        return (len(notes) == 1 and notes[0].find("rest") is not None
                and notes[0].find("rest").get("measure") == "yes"
                and measure.find("direction") is None
                and notes[0].find("notations") is None)

    def bar_tokens(self, number: int, measure: ET.Element) -> list[str]:
        tokens: list[str] = []
        pending: list[ET.Element] = []
        last_duration = None
        cursor = 0
        in_tuplet = False
        for element in measure:
            if element.tag == "direction":
                pending.append(element)
            elif element.tag == "note":
                posts = [p for d in pending for p in direction_posts(d)]
                pending = []
                duration = duration_string(element)
                notations = element.find("notations")
                tuplet = notations.find("tuplet") if notations is not None else None
                if tuplet is not None and tuplet.get("type") == "start":
                    prefix = "\\hideTuplet " if tuplet.get("bracket") == "no" else ""
                    tokens.append(prefix + "\\tuplet 3/2 {")
                    in_tuplet = True
                token, after = self.note_token(element, posts, duration != last_duration)
                last_duration = duration
                tokens.append(token)
                tokens.extend(after)
                if tuplet is not None and tuplet.get("type") == "stop":
                    tokens.append("}")
                    in_tuplet = False
                cursor += int(element.findtext("duration"))
            elif element.tag in ("attributes", "figured-bass", "print"):
                continue
            else:
                raise ValueError(f"unexpected element {element.tag}")
        if in_tuplet:
            raise ValueError(f"{self.pid} bar {number}: tuplet crosses barline")
        if cursor != bar_length(number):
            raise ValueError(f"{self.pid} bar {number}: incomplete")
        if pending:
            posts = [p for d in pending for p in direction_posts(d, at_bar_end=True)]
            tokens.append("<>" + "".join(posts))
        return tokens

    def body(self, skip_structure: bool = False) -> list[str]:
        if skip_structure:
            for _, measure in self.measures():
                self.strip_structure(measure)
        lines: list[str] = []
        bars = list(self.measures())
        index = 0
        if self.is_brass:
            lines.append("  \\transposition d'")
        while index < len(bars):
            number, measure = bars[index]
            if number > 1 and self.is_plain_rest_bar(measure):
                run = 1
                while (index + run < len(bars)
                       and self.is_plain_rest_bar(bars[index + run][1])):
                    run += 1
                last = number + run - 1
                label = f"{number}" if run == 1 else f"{number}–{last}"
                multiplier = "" if run == 1 else f"*{run}"
                lines.append(f"  R2.{multiplier} | % {label}")
                index += run
                continue
            tokens = self.bar_tokens(number, measure)
            lines.append("  " + " ".join(tokens) + f" | % {number}")
            index += 1
        return lines

    @staticmethod
    def strip_structure(measure: ET.Element) -> None:
        for direction in list(measure.findall("direction")):
            if is_structure(direction):
                measure.remove(direction)


def is_structure(direction: ET.Element) -> bool:
    if direction.find("direction-type/rehearsal") is not None:
        return True
    sound = direction.find("sound")
    if sound is not None and sound.get("tempo"):
        return True
    words = direction.find("direction-type/words")
    return words is not None and (words.text or "") in STRUCTURE_WORDS


def structure_lines(part: ET.Element) -> list[str]:
    """Score-level layer: rehearsal marks, tempo headings, tempo transitions."""
    lines: list[str] = []
    events: dict[int, list[tuple[int, list[str]]]] = {}
    for measure in part.findall("measure"):
        number = int(measure.get("number"))
        cursor = 0
        items: dict[int, list[str]] = collections.defaultdict(list)
        for element in measure:
            if element.tag == "note":
                cursor += int(element.findtext("duration"))
            elif element.tag == "direction" and is_structure(element):
                rehearsal = element.find("direction-type/rehearsal")
                sound = element.find("sound")
                words = element.find("direction-type/words")
                if rehearsal is not None:
                    items[cursor].insert(0, f"\\mark \\markup \\box {lily_string(rehearsal.text)}")
                elif sound is not None and sound.get("tempo"):
                    if sound.get("dynamics") != "70":
                        raise ValueError("unexpected tempo playback dynamics")
                    items[cursor].append(f"\\tempo {markup(words)} 4 = {sound.get('tempo')}")
                else:
                    items[cursor].append("<>^" + markup(words))
        if items:
            events[number] = sorted(items.items())
    run = 0
    total = len(part.findall("measure"))
    for number in range(1, total + 1):
        if number not in events:
            run += 1
            continue
        if run:
            first = number - run
            lines.append(f"  s2.*{run} | % {first}–{number - 1}" if run > 1 else f"  s2. | % {first}")
            run = 0
        length = bar_length(number)
        tokens: list[str] = []
        cursor = 0
        for onset, commands in events[number]:
            if onset > cursor:
                tokens.append(f"s{skip_duration(onset - cursor)}")
            tokens.extend(commands)
            cursor = onset
        tokens.append(f"s{skip_duration(length - cursor)}")
        lines.append("  " + " ".join(tokens) + f" | % {number}")
        if number == 1:
            lines.append("  \\set Score.currentBarNumber = #2 % the pickup counts as bar 1")
    if run:
        lines.append(f"  s2.*{run} | % {total - run + 1}–{total}")
    return lines


def skip_duration(divisions: int) -> str:
    table = {48: "32", 96: "16", 144: "16.", 192: "8", 288: "8.", 384: "4",
             576: "4.", 768: "2", 1152: "2."}
    if divisions in table:
        return table[divisions]
    return f"16*{Fraction(divisions, 96)}"


def figure_lines(part: ET.Element) -> list[str]:
    lines: list[str] = []
    for measure in part.findall("measure"):
        number = int(measure.get("number"))
        cursor = 0
        tokens: list[str] = []
        figured_until = 0
        # MusicXML: a run of <figured-bass> elements starts at the following
        # note; each later figure in the run follows the previous one's duration.
        run_position = None
        for element in measure:
            if element.tag == "figured-bass":
                position = cursor if run_position is None else run_position
                if position < figured_until:
                    raise ValueError(f"overlapping figures in bar {number}")
                if position > figured_until:
                    tokens.append(f"s{skip_duration(position - figured_until)}")
                if element.get("parentheses") != "yes":
                    raise ValueError("all continuo figures are expected to be parenthesized")
                figures = " ".join(f.findtext("figure-number") for f in element.findall("figure"))
                length = int(element.findtext("duration"))
                tokens.append(f"<[{figures}]>{skip_duration(length)}")
                figured_until = position + length
                run_position = figured_until
            elif element.tag == "note":
                run_position = None
                cursor += int(element.findtext("duration"))
        if figured_until > bar_length(number):
            raise ValueError(f"figures overrun bar {number}")
        length = bar_length(number)
        if length > figured_until:
            tokens.append(f"s{skip_duration(length - figured_until)}")
        lines.append("  " + " ".join(tokens) + f" | % {number}")
    return lines


def key_changes(part: ET.Element) -> list[tuple[int, str]]:
    changes = []
    for measure in part.findall("measure"):
        key = measure.find("attributes/key")
        if key is None:
            continue
        fifths = int(key.findtext("fifths"))
        mode = key.findtext("mode")
        tonic = {(-1, "minor"): "d", (2, "major"): "d"}[(fifths, mode)]
        changes.append((int(measure.get("number")), f"\\key {tonic} \\{mode}"))
    return changes


def global_lines(part: ET.Element, total: int) -> list[str]:
    lines = ["  \\time 3/4", "  \\partial 2"]
    changes = dict(key_changes(part))
    lines.append(f"  {changes.pop(1)} s2 | % 1")
    bar = 2
    for number, command in sorted(changes.items()):
        lines.append(f"  s2.*{number - bar} | % {bar}–{number - 1}")
        lines.append(f"  {command}")
        bar = number
    lines.append(f"  s2.*{total - bar + 1} | % {bar}–{total}")
    return lines


HEADER = """\\version "2.24.0"
% Generated once from the MusicXML master by
% build/lilypond-port-2026-10-15/import_musicxml.py; edit freely from here on.
% One bar per line; the comment after each bar check is the bar number
% (the pickup is bar 1, as in the repository's documentation).
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "score" / f"{STEM}.musicxml"
    root = ET.parse(source).getroot()
    parts = {part.get("id"): part for part in root.findall("part")}
    total = len(parts["P1"].findall("measure"))
    out = ROOT / "ly"

    write(out / "parts" / "00-global.ily", HEADER + "\n% Meter, pickup and key signatures for every non-brass staff.\n"
          "global = {\n" + "\n".join(global_lines(parts["P1"], total)) + "\n}\n\n"
          "% Natural brass: written in C with no key signature throughout.\n"
          "globalBrass = {\n  \\time 3/4\n  \\partial 2\n  s2 | % 1\n"
          f"  s2.*{total - 1} | % 2–{total}\n}}\n")
    write(out / "parts" / "00-structure.ily", HEADER + "\n% Score-level layer: rehearsal marks, section tempi and tempo transitions.\n"
          "% Exported to MusicXML on the first staff (Flute I), as before the port.\n"
          "structure = {\n" + "\n".join(structure_lines(parts["P1"])) + "\n}\n")

    for pid, (variable, slug) in PARTS.items():
        writer = PartWriter(parts[pid], pid, pid in BRASS)
        body = writer.body(skip_structure=(pid == "P1"))
        base = fixed_base(writer.octave)
        name = parts[pid].get("id")
        part_name = root.find(f"part-list/score-part[@id='{name}']/part-name").text
        note = "% Written pitch; \\transposition d' makes MIDI sound in D.\n" if pid in BRASS else ""
        write(out / "parts" / f"{slug}.ily", HEADER + f"\n% {part_name}\n" + note +
              f"{variable} = \\fixed {base} {{\n" + "\n".join(body) + "\n}\n")
    write(out / "parts" / "15-violoncello-figures.ily", HEADER +
          "\n% Continuo figures under the violoncello. [ ] marks an ad-lib figure group;\n"
          "% the score prints it in parentheses and the MusicXML export sets parentheses=\"yes\".\n"
          "violoncelloFigures = \\figuremode {\n" + "\n".join(figure_lines(parts["P15"])) + "\n}\n")
    print(f"wrote {len(PARTS) + 3} files under {out.relative_to(ROOT)}/parts")


if __name__ == "__main__":
    main()
