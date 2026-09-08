#!/usr/bin/env python3
"""Record hashes after deliberate QA and promotion of current score exports."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
STEM = 'Bach_BWV1004a_Leipzig_orchestral_realization'


def main():
    master = ROOT / 'score' / f'{STEM}.musicxml'
    paths = [f'score/{STEM}.{ext}' for ext in ('mxl', 'mscz', 'pdf', 'mid')]
    paths += [f'audio/{STEM}.mp3',
              'audio/Bach_BWV1004a_transparent_orchestra_MuseSounds.mp3',
              f'score/{STEM}_MuseSounds_tracks.json']
    report = {
        'master_sha256': hashlib.sha256(master.read_bytes()).hexdigest(),
        'artifacts': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
    }
    path = ROOT / 'score' / 'artifact-manifest.json'
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(f'Recorded current derivative hashes: {path}')


if __name__ == '__main__':
    main()
