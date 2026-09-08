#!/usr/bin/env python3
"""Give the native MuseScore document a stable, descriptive internal name."""

from pathlib import Path
import os
import sys
import json
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MSCZ = ROOT / "score" / "Bach_BWV1004a_Leipzig_orchestral_realization.mscz"
INTERNAL = "Bach_BWV1004a_Leipzig_orchestral_realization.mscx"


def main() -> None:
    if len(sys.argv) > 2:
        raise SystemExit("usage: normalize_mscz.py [score.mscz]")
    path = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else MSCZ
    with zipfile.ZipFile(path) as source:
        old_names = [name for name in source.namelist() if name.endswith(".mscx")]
        if len(old_names) != 1:
            raise ValueError(f"Expected one internal MSCX, found {old_names}")
        old = old_names[0]
        fd, temporary_name = tempfile.mkstemp(
            prefix="bwv1004a-", suffix=".mscz", dir=path.parent
        )
        os.close(fd)
        temporary = Path(temporary_name)
        try:
            with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as target:
                for info in source.infolist():
                    data = source.read(info.filename)
                    name = INTERNAL if info.filename == old else info.filename
                    if info.filename == "META-INF/container.xml":
                        data = data.replace(old.encode(), INTERNAL.encode())
                    if info.filename == "score_style.mss":
                        # MuseScore's vertical page-fill can push the first
                        # staff of a one-system final page above the trim box.
                        data = data.replace(
                            b"<enableVerticalSpread>1</enableVerticalSpread>",
                            b"<enableVerticalSpread>0</enableVerticalSpread>",
                        )
                        # The imported title frame can place its text on the trim
                        # edge despite MusicXML's top margin. Keep it inside the frame.
                        data = data.replace(
                            b'<titleOffset x="0" y="0"/>',
                            b'<titleOffset x="0" y="5"/>',
                        )
                        data = data.replace(b'<titleOffset x="0" y="10"/>', b'<titleOffset x="0" y="5"/>')
                    if info.filename == "audiosettings.json":
                        settings = json.loads(data)
                        settings["activeSoundProfile"] = "MuseSounds"
                        # Leave summing headroom before encoding, not after clipping.
                        settings.setdefault("master", {})["volumeDb"] = -4
                        data = json.dumps(settings).encode()
                    target.writestr(name, data)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    print(f"normalized internal score name: {INTERNAL}")


if __name__ == "__main__":
    main()
