#!/usr/bin/env python3
"""Package an authoritative MusicXML file as a deterministic MXL archive."""

from __future__ import annotations

from pathlib import Path
import argparse
import zipfile


MIMETYPE = "application/vnd.recordare.musicxml"
CONTAINER = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="score.musicxml" media-type="application/vnd.recordare.musicxml+xml"/>
  </rootfiles>
</container>
"""
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def member(name: str, compression: int) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_TIME)
    info.compress_type = compression
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def package(source: Path, destination: Path) -> None:
    if source.resolve() == destination.resolve():
        raise ValueError("source and destination must differ")
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with zipfile.ZipFile(temporary, "w") as archive:
        archive.writestr(member("mimetype", zipfile.ZIP_STORED), MIMETYPE)
        archive.writestr(
            member("META-INF/container.xml", zipfile.ZIP_DEFLATED), CONTAINER
        )
        archive.writestr(
            member("score.musicxml", zipfile.ZIP_DEFLATED), source.read_bytes()
        )
    temporary.replace(destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    package(args.source, args.destination)
    print(f"packaged {args.source} -> {args.destination}")


if __name__ == "__main__":
    main()
