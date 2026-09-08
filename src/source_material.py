"""Read the checked-in Mutopia MIDI without optional numerical dependencies."""
from dataclasses import dataclass
from pathlib import Path

TPQ = 384
PICKUP = 2 * TPQ
BAR = 3 * TPQ

@dataclass(frozen=True)
class Note:
    start: int
    end: int
    pitch: int
    velocity: int = 72


def read_vlq(data: bytes, pos: int) -> tuple[int, int]:
    value = 0
    while True:
        byte = data[pos]
        pos += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, pos


def parse_midi_notes(path: Path) -> list[Note]:
    data = path.read_bytes()
    if data[:4] != b"MThd":
        raise ValueError("Not a Standard MIDI file")
    ntracks = int.from_bytes(data[10:12], "big")
    division = int.from_bytes(data[12:14], "big")
    if division != TPQ:
        raise ValueError(f"Expected {TPQ} ticks/quarter, got {division}")
    pos = 14
    notes: list[Note] = []
    for _ in range(ntracks):
        if data[pos:pos + 4] != b"MTrk":
            raise ValueError("Malformed MIDI track")
        length = int.from_bytes(data[pos + 4:pos + 8], "big")
        track = data[pos + 8:pos + 8 + length]
        pos += 8 + length
        t = p = 0
        running = 0
        active: dict[tuple[int, int], list[tuple[int, int]]] = {}
        while p < len(track):
            delta, p = read_vlq(track, p)
            t += delta
            status = track[p]
            if status < 0x80:
                status = running
            else:
                p += 1
                running = status
            if status == 0xFF:
                p += 1
                size, p = read_vlq(track, p)
                p += size
                continue
            if status in (0xF0, 0xF7):
                size, p = read_vlq(track, p)
                p += size
                continue
            kind, channel = status & 0xF0, status & 0x0F
            size = 1 if kind in (0xC0, 0xD0) else 2
            values = track[p:p + size]
            p += size
            if kind == 0x90 and values[1] > 0:
                active.setdefault((channel, values[0]), []).append((t, values[1]))
            elif kind == 0x80 or (kind == 0x90 and values[1] == 0):
                stack = active.get((channel, values[0]))
                if stack:
                    start, velocity = stack.pop(0)
                    notes.append(Note(start, t, values[0], velocity))
    return sorted(notes, key=lambda n: (n.start, -n.pitch, n.end))


def score_bar(tick: int) -> int:
    """LilyPond source bar number: its first, incomplete bar is numbered 1."""
    if tick < PICKUP:
        return 1
    return 2 + (tick - PICKUP) // BAR


def bar_start(number: int) -> int:
    if number <= 1:
        return 0
    return PICKUP + (number - 2) * BAR
