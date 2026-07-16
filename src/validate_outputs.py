#!/usr/bin/env python3
"""Fast structural checks for generated score, MIDI, and audio artifacts."""

from pathlib import Path
from xml.etree import ElementTree as ET
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def require(path: Path, minimum: int) -> None:
    if not path.is_file() or path.stat().st_size < minimum:
        raise AssertionError(f"Missing or unexpectedly small artifact: {path}")


def main() -> None:
    xml_path = ROOT / "score" / "Bach_BWV1004a_transparent_orchestra.musicxml"
    mxl_path = ROOT / "score" / "Bach_BWV1004a_transparent_orchestra.mxl"
    midi_path = ROOT / "score" / "Bach_BWV1004a_transparent_orchestra.mid"
    mp3_path = ROOT / "audio" / "Bach_BWV1004a_transparent_orchestra.mp3"
    require(xml_path, 500_000)
    require(mxl_path, 20_000)
    require(midi_path, 20_000)
    require(mp3_path, 1_000_000)

    root = ET.parse(xml_path).getroot()
    parts = root.findall("part")
    assert root.tag == "score-partwise"
    assert len(parts) == 16
    assert {len(part.findall("measure")) for part in parts} == {257}

    with zipfile.ZipFile(mxl_path) as zf:
        assert zf.testzip() is None
        assert "score.musicxml" in zf.namelist()

    midi = midi_path.read_bytes()
    assert midi[:4] == b"MThd"
    assert int.from_bytes(midi[8:10], "big") == 1
    assert int.from_bytes(midi[10:12], "big") == 17
    assert int.from_bytes(midi[12:14], "big") == 384
    print("ok: 16 parts × 257 bars; valid MXL; 17-track MIDI; audio present")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        raise
