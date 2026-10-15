# Performance preview: bars 125–156

- **Shaped_preview.mp3**: 90-second REAPER performance-and-balance study.
- **Reference.mp3**: the same isolated source renders with the score's
  sectional tempo levels and no added track-volume phrasing.

Both are gain-matched to approximately -20 LUFS integrated. Only constant gain
was used for loudness matching, preserving each version's dynamic range.
The reference is rebuilt from the same stems, not cropped from the published
full-score MP3; instrument loading and independent stem rendering can differ
from the original full-ensemble export.

Listen at roughly 0:22 for the D-major arrival, 1:06 for violin-led flow,
and 1:16 for the oboe handoff in the shaped version.

## Production

Codex (OpenAI), 5 September 2026. Original music: Johann Sebastian Bach.
The authoritative score and published full-length recording are unchanged.

Eleven active instrument tracks were exported from the score at a fixed
quarter-note = 68 source grid, using MuseScore's MuseSounds profile and its
available fallback sounds. REAPER 7.79 rendered the final mixes with
pitch-preserving stretch markers and independent volume automation. The
brass and timpani are silent in this excerpt.

The shaped mix eases toward the mode change, broadens the major opening,
then recovers motion in the next variation. Gentle phrase envelopes and
foreground/accompaniment balancing expose the violin and oboe handoffs.
This is an audio-stem performance study, not a new orchestral sample library
or a full MIDI articulation reprogramming. Source attacks, vibrato, and much
of the instrumental phrasing are still baked into the samples.

Editable local sessions and their source stems are in
`build/performance-preview/Shaped_preview.rpp` and `Reference.rpp`.
Scripts, timing maps, and numerical audio QA are in the same directory.
The approved REAPER evaluation copy is local to
`build/performance-preview/tools/REAPER.app`; it has not replaced any installed
application. REAPER provides a 60-day evaluation: https://www.reaper.fm/download.php

The local production directory is excluded from Git because it includes the
application binary, raw stems, and intermediate renders. Only the two MP3s
and this note are published; the matching lossless WAV masters are kept
locally beside them and are ignored by Git.
