#!/usr/bin/env python3
"""Export review derivatives using MuseScore batch import and a consistent profile."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def fresh_complete_outputs(paths, started_ns):
    """Recognize completed notation exports after the observed shutdown abort.

    This never accepts stale outputs, truncated containers, or failed audio.
    Musical round-trip and publication checks remain separate requirements.
    """
    if not paths:
        return False
    try:
        for path in paths:
            if path.stat().st_mtime_ns < started_ns:
                return False
            data = path.read_bytes()
            if path.suffix == '.mscz':
                with zipfile.ZipFile(path) as archive:
                    if archive.testzip() is not None:
                        return False
                    names = [n for n in archive.namelist() if n.endswith('.mscx')]
                    if len(names) != 1:
                        return False
                    root = ET.fromstring(archive.read(names[0]))
                    if sum(len(staff.findall('Measure')) == 257 for staff in root.findall('.//Staff')) != 16:
                        return False
            elif path.suffix == '.musicxml':
                root = ET.fromstring(data)
                if len(root.findall('part')) != 16 or any(len(p.findall('measure')) != 257 for p in root.findall('part')):
                    return False
            elif path.suffix == '.pdf':
                if not data.startswith(b'%PDF-') or b'%%EOF' not in data[-1024:]:
                    return False
            elif path.suffix == '.mid':
                if not data.startswith(b'MThd'):
                    return False
                pos = 8 + int.from_bytes(data[4:8], 'big')
                for _ in range(int.from_bytes(data[10:12], 'big')):
                    if data[pos:pos+4] != b'MTrk':
                        return False
                    pos += 8 + int.from_bytes(data[pos+4:pos+8], 'big')
                if pos != len(data):
                    return False
            else:
                return False
    except (OSError, ValueError, zipfile.BadZipFile, ET.ParseError):
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mscore', required=True)
    parser.add_argument('--stem', default='Bach_BWV1004a_Leipzig_orchestral_realization')
    args = parser.parse_args()
    out = ROOT / 'build' / 'render'
    out.mkdir(parents=True, exist_ok=True)
    native = out / f'{args.stem}.mscz'

    def run(label, command, outputs=()):
        log = out / f'{label}.log'
        started_ns = time.time_ns()
        with log.open('w') as stream:
            result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode and 'mutex lock failed: Invalid argument' in log.read_text() and fresh_complete_outputs(outputs, started_ns):
            print(f'{label}: fresh complete notation files verified after MuseScore shutdown abort; see {log}', flush=True)
            return
        if result.returncode:
            raise SystemExit(f'{label} failed ({result.returncode}); see {log}')
        print(f'{label}: complete', flush=True)

    job = out / 'import-job.json'
    job.write_text(json.dumps([{'in': str(ROOT / 'score' / f'{args.stem}.musicxml'),
                                'out': str(native)}]))
    # Batch import avoids the shutdown crash observed with direct -o XML import.
    run('import', [args.mscore, '-j', str(job)], [native])
    run('normalize', [sys.executable, str(ROOT / 'src' / 'normalize_mscz.py'), str(native)])
    job = out / 'export-job.json'
    job.write_text(json.dumps([{'in': str(native), 'out': [
        str(out / f'{args.stem}.pdf'), str(out / f'{args.stem}.mid'),
        str(out / 'roundtrip.musicxml')]}]))
    run('notation', [args.mscore, '-j', str(job)], [out / f'{args.stem}.pdf', out / f'{args.stem}.mid', out / 'roundtrip.musicxml'])
    run('audio', [args.mscore, '--sound-profile', 'MuseSounds', '--tracks-diff',
                  str(out / f'{args.stem}_MuseSounds_tracks.json'), '-o',
                  str(out / f'{args.stem}.mp3'), str(native)])
    print(f'Review exports are in {out}; promote and record hashes only after QA.')


if __name__ == '__main__':
    main()
