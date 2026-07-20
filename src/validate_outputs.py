#!/usr/bin/env python3
"""Fast structural checks for generated score, MIDI, and audio artifacts."""

from pathlib import Path
from xml.etree import ElementTree as ET
from fractions import Fraction
import json
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
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


def require(path: Path, minimum: int) -> None:
    if not path.is_file() or path.stat().st_size < minimum:
        raise AssertionError(f"Missing or unexpectedly small artifact: {path}")


def validate_musicxml_rhythm(root: ET.Element) -> None:
    """Ensure written notation and raw durations agree exactly in every bar."""
    for part in root.findall("part"):
        for measure in part.findall("measure"):
            measure_number = int(measure.get("number", "0"))
            expected = TPQ * 2 if measure_number == 1 else TPQ * 3
            found = 0
            for note in measure.findall("note"):
                duration_el = note.find("duration")
                type_el = note.find("type")
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
                    found += duration
            if found != expected:
                raise AssertionError(
                    f"Incomplete measure in {part.get('id')} measure {measure_number}: "
                    f"found {found} ticks, expected {expected}"
                )


def validate_musicxml_ranges(root: ET.Element) -> None:
    """Check the wind floors that motivated the phrase-level relays."""
    names = {
        score_part.get("id"): score_part.findtext("part-name", "")
        for score_part in root.findall("./part-list/score-part")
    }
    semitones = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
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
                midi_pitch = (octave + 1) * 12 + semitones[step] + alter
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
    assert len(root.findall(".//breath-mark")) >= 8
    assert len(root.findall(".//tenuto")) >= 16
    assert len(root.findall(".//accent")) == 15
    assert len(root.findall(".//trill-mark")) == 2
    assert len(root.findall(".//fermata")) == 1
    words = [node.text or "" for node in root.findall(".//direction-type/words")]
    assert words.count("arpeggiate upward, together") == 5
    assert "on two strings" in words
    assert words.count("arco, lightly") == 1
    assert words.count("non pesante") == 1
    assert words.count("fondamento") == 1
    assert words.count("arco, non pesante") == 1
    assert words.count("sostenuto, non pesante") == 1
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


def main() -> None:
    xml_path = ROOT / "score" / "Bach_BWV1004a_transparent_orchestra.musicxml"
    mxl_path = ROOT / "score" / "Bach_BWV1004a_transparent_orchestra.mxl"
    mscz_path = ROOT / "score" / "Bach_BWV1004a_transparent_orchestra.mscz"
    midi_path = ROOT / "score" / "Bach_BWV1004a_transparent_orchestra.mid"
    mp3_path = ROOT / "audio" / "Bach_BWV1004a_transparent_orchestra.mp3"
    mscore_mp3_path = ROOT / "audio" / "Bach_BWV1004a_transparent_orchestra_MuseScore_Basic.mp3"
    muse_mp3_path = ROOT / "audio" / "Bach_BWV1004a_transparent_orchestra_MuseSounds.mp3"
    muse_tracks_path = ROOT / "score" / "Bach_BWV1004a_transparent_orchestra_MuseSounds_tracks.json"
    require(xml_path, 500_000)
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
    assert len(double_bass.findall(".//note[pitch]")) == 128
    validate_musicxml_rhythm(root)
    validate_musicxml_ranges(root)
    validate_expressive_notation(root)

    with zipfile.ZipFile(mxl_path) as zf:
        assert zf.testzip() is None
        assert "score.musicxml" in zf.namelist()
        assert zf.read("score.musicxml") == xml_path.read_bytes()
    with zipfile.ZipFile(mscz_path) as zf:
        assert zf.testzip() is None
        mscx_names = [name for name in zf.namelist() if name.endswith(".mscx")]
        assert len(mscx_names) == 1
        mscx = zf.read(mscx_names[0])
        # Fractional locations are legitimate inside imported slur spanners,
        # but nowhere else: fractions outside a Spanner would indicate a
        # compensating rhythmic repair.  Event parity also prevents a newly
        # generated XML file from being shipped beside a stale native snapshot.
        native_root = ET.fromstring(mscx)
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
                if not positions_breath:
                    raise AssertionError(
                        "Fractional native location outside expressive spanner/breath mark"
                    )
            for child in node:
                check_fraction_locations(child, in_spanner)

        check_fraction_locations(native_root)
        assert mscx.count(b"<durationType>") == len(root.findall(".//note"))
        assert mscx.count(b"<Tuplet>") * 3 == len(root.findall(".//time-modification"))
        assert mscx.count(b"<Dynamic>") == len(root.findall(".//direction-type/dynamics/*"))
        assert mscx.count(b"<HairPin>") == len(root.findall('.//wedge[@type="stop"]'))
        assert mscx.count(b"<Slur>") == len(root.findall('.//slur[@type="start"]'))
        assert mscx.count(b"<Breath>") == len(root.findall(".//breath-mark"))
        assert mscx.count(b"<Ornament>") == len(root.findall(".//trill-mark"))
        assert mscx.count(b"<Fermata>") == len(root.findall(".//fermata"))
        assert mscx.count(b"arpeggiate upward, together") == 5
        assert mscx.count(b"on two strings") == 1
        assert mscx.count(b"fondamento") == 1
        assert mscx.count(b"non pesante") == 3

    midi = midi_path.read_bytes()
    assert midi[:4] == b"MThd"
    assert int.from_bytes(midi[8:10], "big") == 1
    assert int.from_bytes(midi[10:12], "big") == 17
    assert int.from_bytes(midi[12:14], "big") == 384

    profile = json.loads(muse_tracks_path.read_text())
    score_tracks = [track for track in profile["newTracks"] if track["partId"] != "999"]
    assert len(score_tracks) == 16
    assert {track["type"] for track in score_tracks} == {"muse_sampler_sound_pack"}
    print(
        "ok: 16 parts × 257 complete, exactly spelled bars; expressive layer; "
        "valid MXL/MSCZ; 17-track MIDI; all parts use Muse Sounds"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        raise
