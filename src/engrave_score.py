#!/usr/bin/env python3
"""Engrave the LilyPond master: conductor score PDF and LilyPond MIDI.

Any LilyPond warning fails the build, so problems are fixed rather than
shipped. Outputs are written to score/ under the edition's stem.

    python3 src/engrave_score.py [--lilypond BIN]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEM = "Bach_BWV1004a_Leipzig_orchestral_realization"
SOURCE = ROOT / "ly" / "bwv1004a.ly"
WORK = ROOT / "build" / "lilypond"
PDF = ROOT / "score" / f"{STEM}_LilyPond_conductor_score.pdf"
MIDI = ROOT / "score" / f"{STEM}_LilyPond.mid"


def engrave(lilypond: str = "lilypond") -> tuple[Path, Path]:
    WORK.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [lilypond, "-dno-point-and-click", "-o", str(WORK / "bwv1004a"), str(SOURCE)],
        capture_output=True, text=True,
    )
    log = (result.stdout or "") + (result.stderr or "")
    (WORK / "engrave.log").write_text(log)
    problems = [line for line in log.splitlines() if "warning:" in line or "error:" in line]
    if result.returncode != 0 or problems:
        raise SystemExit("LilyPond engraving failed:\n" + "\n".join(problems or log.splitlines()[-20:]))
    shutil.copyfile(WORK / "bwv1004a.pdf", PDF)
    shutil.copyfile(WORK / "bwv1004a.midi", MIDI)
    return PDF, MIDI


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lilypond", default="lilypond")
    args = parser.parse_args()
    for path in engrave(args.lilypond):
        print(f"engraved {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
