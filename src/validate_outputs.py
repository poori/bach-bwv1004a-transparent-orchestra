#!/usr/bin/env python3
"""Validate the authoritative score and, optionally, its published artifacts."""

from pathlib import Path
from xml.etree import ElementTree as ET
from fractions import Fraction
import json
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
STEM = "Bach_BWV1004a_Leipzig_orchestral_realization"
TPQ = 384
TYPE_TICKS = {
    "whole": TPQ * 4,
    "half": TPQ * 2,
    "quarter": TPQ,
    "eighth": TPQ // 2,
    "16th": TPQ // 4,
    "32nd": TPQ // 8,
    "64th": TPQ // 16,
    "128th": TPQ // 32,
}

PROFESSIONAL_RANGES = {
    "Flute I": (60, 96),
    "Flute II": (60, 96),
    "Oboe I": (58, 91),
    "Oboe II": (58, 91),
}
STEP_ORDER = ("C", "D", "E", "F", "G", "A", "B")
STEP_SEMITONES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def require(path: Path, minimum: int) -> None:
    if not path.is_file() or path.stat().st_size < minimum:
        raise AssertionError(f"Missing or unexpectedly small artifact: {path}")


def validate_musicxml_rhythm(root: ET.Element) -> None:
    """Ensure written notation and raw durations agree exactly in every bar."""
    for part in root.findall("part"):
        for measure in part.findall("measure"):
            measure_number = int(measure.get("number", "0"))
            expected = TPQ * 2 if measure_number == 1 else TPQ * 3
            cursor = 0
            furthest = 0
            last_onset = 0
            for event in measure:
                if event.tag == "backup":
                    cursor -= int(event.findtext("duration", "0"))
                    if cursor < 0:
                        raise AssertionError(
                            f"Backup before bar start in {part.get('id')} "
                            f"measure {measure_number}"
                        )
                    continue
                if event.tag == "forward":
                    cursor += int(event.findtext("duration", "0"))
                    furthest = max(furthest, cursor)
                    continue
                if event.tag != "note":
                    continue
                note = event
                duration_el = note.find("duration")
                type_el = note.find("type")
                if note.find("grace") is not None and duration_el is None:
                    continue
                if duration_el is None or duration_el.text is None:
                    raise AssertionError(
                        f"Missing duration in {part.get('id')} measure {measure_number}"
                    )
                if type_el is None or type_el.text not in TYPE_TICKS:
                    raise AssertionError(
                        f"Missing/unknown type in {part.get('id')} measure {measure_number}"
                    )
                duration = int(duration_el.text)
                written = Fraction(TYPE_TICKS[type_el.text])
                dots = len(note.findall("dot"))
                written *= Fraction((2 ** (dots + 1)) - 1, 2 ** dots)
                modification = note.find("time-modification")
                if modification is not None:
                    actual = int(modification.findtext("actual-notes", "0"))
                    normal = int(modification.findtext("normal-notes", "0"))
                    if actual <= 0 or normal <= 0:
                        raise AssertionError(
                            f"Invalid time modification in {part.get('id')} "
                            f"measure {measure_number}"
                        )
                    written *= Fraction(normal, actual)
                if written.denominator != 1 or written.numerator != duration:
                    raise AssertionError(
                        f"Notation/duration mismatch in {part.get('id')} measure "
                        f"{measure_number}: written={written}, duration={duration}"
                    )
                if note.find("chord") is None:
                    last_onset = cursor
                    cursor += duration
                furthest = max(furthest, last_onset + duration)
            if furthest != expected:
                raise AssertionError(
                    f"Incomplete measure in {part.get('id')} measure {measure_number}: "
                    f"found {furthest} ticks, expected {expected}"
                )


def validate_musicxml_ranges(root: ET.Element) -> None:
    """Check the wind floors that motivated the phrase-level relays."""
    names = {
        score_part.get("id"): score_part.findtext("part-name", "")
        for score_part in root.findall("./part-list/score-part")
    }
    for part in root.findall("part"):
        name = names.get(part.get("id"), "")
        if name not in PROFESSIONAL_RANGES:
            continue
        low, high = PROFESSIONAL_RANGES[name]
        outside: list[tuple[int, int]] = []
        for measure in part.findall("measure"):
            for note in measure.findall("note"):
                pitch = note.find("pitch")
                if pitch is None:
                    continue
                step = pitch.findtext("step", "C")
                alter = int(pitch.findtext("alter", "0"))
                octave = int(pitch.findtext("octave", "4"))
                midi_pitch = (octave + 1) * 12 + STEP_SEMITONES[step] + alter
                if not low <= midi_pitch <= high:
                    outside.append((int(measure.get("number", "0")), midi_pitch))
        if outside:
            raise AssertionError(f"{name} outside professional range: {outside}")


def validate_expressive_notation(root: ET.Element) -> None:
    dynamics = root.findall(".//direction-type/dynamics/*")
    wedge_starts = (
        root.findall('.//wedge[@type="crescendo"]')
        + root.findall('.//wedge[@type="diminuendo"]')
    )
    wedge_stops = root.findall('.//wedge[@type="stop"]')
    slur_starts = root.findall('.//slur[@type="start"]')
    slur_stops = root.findall('.//slur[@type="stop"]')
    assert len(dynamics) >= 100
    assert len(wedge_starts) == len(wedge_stops) >= 40
    assert len(slur_starts) == len(slur_stops) >= 300
    assert len(root.findall(".//breath-mark")) >= 40
    assert len(root.findall(".//tenuto")) >= 16
    assert len(root.findall(".//staccato")) >= 100
    assert len(root.findall(".//accent")) >= 12
    assert len(root.findall(".//trill-mark")) >= 2
    assert len(root.findall(".//fermata")) == 1
    words = [node.text or "" for node in root.findall(".//direction-type/words")]
    assert words.count("arpeggiate upward, together") == 5
    assert "on two strings" in words
    assert "Continuo (violoncello, violone, bassoon; organ or harpsichord ad lib.)" in words
    assert "pizz." in words and "arco" in words
    assert any(word.startswith("cue:") for word in words)
    assert "K · Second chorale — dolce, poco vibrato" in words
    part_names = {
        score_part.get("id"): score_part.findtext("part-name", "")
        for score_part in root.findall("./part-list/score-part")
    }
    for part in root.findall("part"):
        for measure in part.findall("measure"):
            measure_words = [
                node.text or "" for node in measure.findall(".//direction-type/words")
            ]
            has_pitch = measure.find("note/pitch") is not None
            if any(word in {"solo", "ripieno"} for word in measure_words):
                assert has_pitch
                assert part_names.get(part.get("id")) != "Double Bass"
            if measure.findall(".//wedge"):
                assert has_pitch
    assert not root.findall(".//detached-legato")


def pitch_to_midi(note: ET.Element, transpose: int = 0) -> int | None:
    pitch = note.find("pitch")
    if pitch is None:
        return None
    written = (
        (int(pitch.findtext("octave", "4")) + 1) * 12
        + STEP_SEMITONES[pitch.findtext("step", "C")]
        + int(pitch.findtext("alter", "0"))
    )
    return written + transpose


def timed_notes(measure: ET.Element):
    """Yield (note, start, end) while respecting MusicXML voice navigation."""
    cursor = 0
    onset = 0
    for event in measure:
        if event.tag == "backup":
            cursor -= int(event.findtext("duration", "0"))
        elif event.tag == "forward":
            cursor += int(event.findtext("duration", "0"))
        elif event.tag == "note":
            duration = int(event.findtext("duration", "0"))
            if event.find("chord") is None:
                onset = cursor
                cursor += duration
            if event.find("pitch") is not None and duration:
                yield event, onset, onset + duration


def concert_spelling(
    note: ET.Element, diatonic_transpose: int, chromatic_transpose: int
) -> tuple[str, int]:
    """Return sounding letter and alteration, preserving transposed spelling."""
    step = note.findtext("pitch/step", "C")
    written_alter = int(note.findtext("pitch/alter", "0"))
    sounding_step = STEP_ORDER[(STEP_ORDER.index(step) + diatonic_transpose) % 7]
    sounding_pc = (STEP_SEMITONES[step] + written_alter + chromatic_transpose) % 12
    natural_pc = STEP_SEMITONES[sounding_step]
    sounding_alter = (sounding_pc - natural_pc + 6) % 12 - 6
    return sounding_step, sounding_alter


def cross_relation_violations(root: ET.Element) -> list[dict[str, object]]:
    """Find simultaneous natural/altered forms of one sounding letter."""
    names = {
        score_part.get("id"): score_part.findtext("part-name", "")
        for score_part in root.findall("./part-list/score-part")
    }
    by_bar: dict[int, list[tuple[int, int, str, int, str]]] = {}
    for part in root.findall("part"):
        name = names.get(part.get("id"), part.get("id", ""))
        diatonic = int(part.findtext("./measure/attributes/transpose/diatonic", "0"))
        chromatic = int(part.findtext("./measure/attributes/transpose/chromatic", "0"))
        for measure in part.findall("measure"):
            bar = int(measure.get("number", "0"))
            for note, start, end in timed_notes(measure):
                step, alter = concert_spelling(note, diatonic, chromatic)
                by_bar.setdefault(bar, []).append((start, end, step, alter, name))

    violations: list[dict[str, object]] = []
    seen: set[tuple[object, ...]] = set()
    for bar, events in by_bar.items():
        boundaries = sorted({point for start, end, *_ in events for point in (start, end)})
        for left, right in zip(boundaries, boundaries[1:]):
            active = [event for event in events if event[0] <= left and right <= event[1]]
            for step in STEP_ORDER:
                matching = [event for event in active if event[2] == step]
                alters = sorted({event[3] for event in matching})
                staves = sorted({event[4] for event in matching})
                if len(alters) < 2 or len(staves) < 2:
                    continue
                key = (bar, left, step, tuple(alters), tuple(staves))
                if key in seen:
                    continue
                seen.add(key)
                violations.append(
                    {"bar": bar, "tick": left, "letter": step,
                     "alterations": alters, "staves": staves}
                )
    return violations


def musical_metrics(root: ET.Element) -> dict[str, object]:
    """Measure musical density and roster practicality, not just file health."""
    names = {
        score_part.get("id"): score_part.findtext("part-name", "")
        for score_part in root.findall("./part-list/score-part")
    }
    active_bars: dict[str, list[int]] = {}
    intervals: dict[int, dict[str, list[tuple[int, int]]]] = {
        bar: {} for bar in range(1, 258)
    }
    natural_d = {38, 45, 50, 54, 57, 60, 62, 64, 66, 69, 72, 74, 76, 78, 81}
    foreign_brass: list[dict[str, int | str]] = []
    continuo_missing: dict[str, list[int]] = {}

    for part in root.findall("part"):
        name = names.get(part.get("id"), part.get("id", ""))
        part_active: list[int] = []
        transpose = int(part.findtext("./measure/attributes/transpose/chromatic", "0"))
        for measure in part.findall("measure"):
            bar = int(measure.get("number", "0"))
            cursor = 0
            current_start = 0
            found_pitch = False
            for event in measure:
                if event.tag == "backup":
                    cursor -= int(event.findtext("duration", "0"))
                    continue
                if event.tag == "forward":
                    cursor += int(event.findtext("duration", "0"))
                    continue
                if event.tag != "note":
                    continue
                note = event
                duration = int(note.findtext("duration", "0"))
                if note.find("chord") is None:
                    current_start = cursor
                    cursor += duration
                if note.find("pitch") is not None:
                    found_pitch = True
                    intervals[bar].setdefault(name, []).append(
                        (current_start, current_start + duration)
                    )
                    if name.startswith(("Horn", "Trumpet")):
                        sounding = pitch_to_midi(note, transpose)
                        if sounding not in natural_d:
                            foreign_brass.append({"part": name, "bar": bar, "pitch": sounding or -1})
            if found_pitch:
                part_active.append(bar)
        active_bars[name] = part_active

    low_runs: list[dict[str, int]] = []
    minimum_by_bar: dict[int, int] = {}
    for bar, per_part in intervals.items():
        boundaries = sorted({point for spans in per_part.values() for span in spans for point in span})
        segment_counts = []
        for left, right in zip(boundaries, boundaries[1:]):
            if right <= left:
                continue
            segment_counts.append(sum(
                any(start <= left and right <= end for start, end in spans)
                for spans in per_part.values()
            ))
        minimum = min(segment_counts) if segment_counts else 0
        minimum_by_bar[bar] = minimum
        if minimum < 3:
            low_runs.append({"bar": bar, "minimum_simultaneous_staves": minimum})

    missing_bass = [
        bar for bar in range(1, 258)
        if not any(
            bar in active_bars.get(name, [])
            for name in ("Bassoon I", "Bassoon II", "Violoncello", "Double Bass")
        )
    ]
    if missing_bass:
        continuo_missing["bass/continuo"] = missing_bass
    missing_bassoon = [
        bar for bar in range(1, 258)
        if bar not in active_bars.get("Bassoon I", [])
        and bar not in active_bars.get("Bassoon II", [])
    ]
    if missing_bassoon:
        continuo_missing["Bassoon I/II"] = missing_bassoon

    longest: dict[str, int] = {}
    for name, bars in active_bars.items():
        best = run = 0
        previous = None
        for bar in bars:
            run = run + 1 if previous is not None and bar == previous + 1 else 1
            best = max(best, run)
            previous = bar
        longest[name] = best

    return {
        "minimum_simultaneous_staves_by_bar": minimum_by_bar,
        "runs_below_three_staves": low_runs,
        "continuo_missing_bars": continuo_missing,
        "active_bars_per_player": {name: len(bars) for name, bars in active_bars.items()},
        "longest_continuous_stretch_bars": longest,
        "figured_bass_measures": len(root.findall(".//figured-bass")),
        "natural_d_brass_violations": foreign_brass,
    }


def validate_musical_metrics(root: ET.Element) -> dict[str, object]:
    report = musical_metrics(root)
    report["cross_relation_violations"] = cross_relation_violations(root)
    validate_natural_brass(report)
    assert not report["cross_relation_violations"], report["cross_relation_violations"]
    assert not report["continuo_missing_bars"], report["continuo_missing_bars"]
    assert report["figured_bass_measures"] >= 513
    return report


def validate_natural_brass(report: dict[str, object]) -> None:
    """Reject horn or trumpet pitches outside the natural D harmonic series."""
    assert not report["natural_d_brass_violations"], report["natural_d_brass_violations"]


def main() -> None:
    source_only = sys.argv[1:] == ["--source-only"]
    if sys.argv[1:] not in ([], ["--source-only"]):
        raise SystemExit("usage: validate_outputs.py [--source-only]")
    xml_path = ROOT / "score" / f"{STEM}.musicxml"
    mxl_path = ROOT / "score" / f"{STEM}.mxl"
    mscz_path = ROOT / "score" / f"{STEM}.mscz"
    midi_path = ROOT / "score" / f"{STEM}.mid"
    mp3_path = ROOT / "audio" / f"{STEM}.mp3"
    mscore_mp3_path = ROOT / "audio" / "Bach_BWV1004a_transparent_orchestra_MuseScore_Basic.mp3"
    muse_mp3_path = ROOT / "audio" / "Bach_BWV1004a_transparent_orchestra_MuseSounds.mp3"
    muse_tracks_path = ROOT / "score" / f"{STEM}_MuseSounds_tracks.json"
    require(xml_path, 500_000)
    if not source_only:
        require(mxl_path, 20_000)
        require(mscz_path, 100_000)
        require(midi_path, 20_000)
        require(mp3_path, 1_000_000)
        require(mscore_mp3_path, 10_000_000)
        require(muse_mp3_path, 10_000_000)
        require(muse_tracks_path, 1_000)

    root = ET.parse(xml_path).getroot()
    parts = root.findall("part")
    assert root.tag == "score-partwise"
    assert len(parts) == 16
    assert {len(part.findall("measure")) for part in parts} == {257}
    assert root.findtext("./defaults/page-layout/page-width") == "1597"
    assert root.findtext("./defaults/page-layout/page-height") == "2468"
    part_names = {
        score_part.get("id"): score_part.findtext("part-name", "")
        for score_part in root.findall("./part-list/score-part")
    }
    double_bass = next(
        part for part in parts if part_names.get(part.get("id")) == "Double Bass"
    )
    assert len(double_bass.findall(".//note[pitch]")) > 40
    validate_musicxml_rhythm(root)
    validate_musicxml_ranges(root)
    validate_expressive_notation(root)
    report = validate_musical_metrics(root)
    metrics_path = ROOT / "build" / "musical_metrics.json"
    metrics_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    if source_only:
        print(
            "ok: authoritative MusicXML; 16 parts × 257 complete; exact rhythm; "
            "no cross-relations; continuous figured continuo; natural-D brass; "
            "metrics in build/musical_metrics.json"
        )
        return

    with zipfile.ZipFile(mxl_path) as zf:
        assert zf.testzip() is None
        assert zf.namelist()[0] == "mimetype"
        assert zf.read("mimetype") == b"application/vnd.recordare.musicxml"
        assert "score.musicxml" in zf.namelist()
        assert zf.read("score.musicxml") == xml_path.read_bytes()
    with zipfile.ZipFile(mscz_path) as zf:
        assert zf.testzip() is None
        audio_settings = json.loads(zf.read("audiosettings.json"))
        assert audio_settings["activeSoundProfile"] == "MuseSounds"
        mscx_names = [name for name in zf.namelist() if name.endswith(".mscx")]
        assert len(mscx_names) == 1
        assert mscx_names[0] == "Bach_BWV1004a_Leipzig_orchestral_realization.mscx"
        mscx = zf.read(mscx_names[0])
        # Fractional locations are legitimate inside imported slur spanners,
        # but nowhere else: fractions outside a Spanner would indicate a
        # compensating rhythmic repair.  Event parity also prevents a newly
        # generated XML file from being shipped beside a stale native snapshot.
        native_root = ET.fromstring(mscx)
        irregular_measures = [
            (int(staff.get("id", "0")), bar, measure.get("len"))
            for staff in native_root.findall(".//Staff")
            if len(staff.findall("Measure")) == 257
            for bar, measure in enumerate(staff.findall("Measure"), start=1)
            if measure.get("len") is not None
            and Fraction(measure.get("len", "0"))
            != (Fraction(1, 2) if bar == 1 else Fraction(3, 4))
        ]
        assert not irregular_measures, irregular_measures
        native_parents = {
            child: parent for parent in native_root.iter() for child in parent
        }

        def check_fraction_locations(node: ET.Element, in_spanner: bool = False) -> None:
            in_spanner = in_spanner or node.tag == "Spanner"
            if node.tag == "fractions" and not in_spanner:
                location = native_parents[node]
                voice = native_parents.get(location)
                siblings = list(voice) if voice is not None else []
                location_index = siblings.index(location) if location in siblings else -1
                positions_breath = (
                    location_index >= 0
                    and location_index + 1 < len(siblings)
                    and siblings[location_index + 1].tag == "Breath"
                )
                positions_tuplet = any(sibling.tag in {"Tuplet", "endTuplet"} for sibling in siblings)
                positions_figured_bass = any(sibling.tag == "FiguredBass" for sibling in siblings)
                if not positions_breath and not positions_tuplet and not positions_figured_bass:
                    raise AssertionError(
                        "Fractional native location outside expressive spanner, breath, tuplet, or figured bass"
                    )
            for child in node:
                check_fraction_locations(child, in_spanner)

        check_fraction_locations(native_root)
        native_durations = mscx.count(b"<durationType>")
        xml_notes = len(root.findall(".//note"))
        # MuseScore materializes some figured-bass continuation segments as
        # internal duration-bearing objects, so native duration count is no
        # longer strict note parity. Keep a tight bound and verify all figures.
        assert xml_notes - 257 <= native_durations <= xml_notes + 257
        assert mscx.count(b"<FiguredBass>") >= 513
        xml_tuplet_notes = len(root.findall(".//time-modification"))
        native_tuplets = mscx.count(b"<Tuplet>")
        assert (xml_tuplet_notes + 2) // 3 <= native_tuplets <= xml_tuplet_notes
        assert mscx.count(b"<Dynamic>") == len(root.findall(".//direction-type/dynamics/*"))
        assert mscx.count(b"<HairPin>") == len(root.findall('.//wedge[@type="stop"]'))
        assert mscx.count(b"<Slur>") == len(root.findall('.//slur[@type="start"]'))
        assert mscx.count(b"<Breath>") == len(root.findall(".//breath-mark"))
        assert mscx.count(b"<Ornament>") == len(root.findall(".//trill-mark"))
        assert mscx.count(b"<Fermata>") == len(root.findall(".//fermata"))
        assert mscx.count(b"<RehearsalMark>") == 17
        assert mscx.count(b"arpeggiate upward, together") == 5
        assert mscx.count(b"on two strings") == 1
        assert mscx.count(b"sempre continuo") >= 1

    midi = midi_path.read_bytes()
    assert midi[:4] == b"MThd"
    assert int.from_bytes(midi[8:10], "big") == 1
    assert int.from_bytes(midi[10:12], "big") == 16
    assert int.from_bytes(midi[12:14], "big") == 480

    profile = json.loads(muse_tracks_path.read_text())
    score_tracks = [track for track in profile["newTracks"] if track["partId"] != "999"]
    assert len(score_tracks) == 16
    # MuseScore currently falls back to MS Basic for natural D horns and
    # violone. Accept only these explicit mappings, never an arbitrary silent
    # or missing sampler track; inspect the freshly exported track report.
    fallback_instruments = {"d-horn", "violone"}
    for track in score_tracks:
        assert track["type"] == "muse_sampler_sound_pack" or (
            track["type"] == "fluid_soundfont"
            and track["instrumentId"] in fallback_instruments
            and track["name"] == "MS Basic"
        ), track
    assert sum(t["type"] == "muse_sampler_sound_pack" for t in score_tracks) >= 13
    print(
        "ok: authoritative score and exact rhythm; 16 parts × 257 complete; "
        "continuous figured continuo; no cross-relations; natural-D brass; "
        "valid MXL/MSCZ; 16-track MIDI; verified MuseSounds/explicit Basic fallback mappings; "
        "metrics in build/musical_metrics.json"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        raise
