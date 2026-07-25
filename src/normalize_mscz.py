#!/usr/bin/env python3
"""Give the native MuseScore document a stable, descriptive internal name."""

from pathlib import Path
import os
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MSCZ = ROOT / "score" / "Bach_BWV1004a_Leipzig_orchestral_realization.mscz"
INTERNAL = "Bach_BWV1004a_Leipzig_orchestral_realization.mscx"


def main() -> None:
    with zipfile.ZipFile(MSCZ) as source:
        old_names = [name for name in source.namelist() if name.endswith(".mscx")]
        if len(old_names) != 1:
            raise ValueError(f"Expected one internal MSCX, found {old_names}")
        old = old_names[0]
        fd, temporary_name = tempfile.mkstemp(
            prefix="bwv1004a-", suffix=".mscz", dir=MSCZ.parent
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
                    target.writestr(name, data)
            os.replace(temporary, MSCZ)
        finally:
            temporary.unlink(missing_ok=True)
    print(f"normalized internal score name: {INTERNAL}")


if __name__ == "__main__":
    main()
