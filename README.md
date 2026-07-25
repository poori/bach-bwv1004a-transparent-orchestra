# BWV 1004a: a Leipzig orchestral Chaconne

An experimental orchestral realization of J. S. Bach's *Ciaccona* from the
Partita in D minor, BWV 1004.

The counterfactual premise is specific: **what if Bach had rescored the
Chaconne for the Leipzig Collegium Musicum around 1730?** The available
ensemble is modestly modern, but the musical logic is Baroque: a continuous
figured-bass foundation, recurring ripieno returns, functional wind doubling,
and natural D brass reserved for the festive major-mode crown.

[Listen to the current mock-up](audio/Bach_BWV1004a_Leipzig_orchestral_realization.mp3?raw=1)
· [Open the native MuseScore score](score/Bach_BWV1004a_Leipzig_orchestral_realization.mscz)
· [Open the editable score](score/Bach_BWV1004a_Leipzig_orchestral_realization.mxl)
· [Read the orchestration notes](docs/orchestration-notes.md)

## Scoring

- Pairs of flutes, oboes, and bassoons; two natural horns in D; two natural
  trumpets in D; timpani (D–A); and strings (suggested ripieno 4.4.3.2.1).
- Double bass states the four-bar ground throughout; the bassoons alternate
  four-bar units and cello joins selected variations. A keyboard continuo is
  indicated but not assigned its own staff.
- Sustained inner voices, explicitly notated divisi, and double stops keep the
  ensemble texture harmonically complete through Bach's single-line figuration.
- Winds primarily double complete string/source lines in overlapping two-bar
  cells, with written breathing windows and a few independent color changes.
- Horns, trumpets, and timpani play only in the D-major span, bars 133–208.
  Every brass pitch is restricted to the notated D-natural harmonic series.

The 257-bar realization preserves all 3,083 source notes and their pitch
classes, rhythms, ornaments, and final fermata. Added notes are explicitly
tagged in the generator as continuo, ripieno harmony, wind doubling, or natural
brass, so source identity remains mechanically auditable.

The score includes actual rehearsal marks A–Q, two-bar *poco accel.*/*poco
rit.* transitions between tempo plateaus, a first articulation/bowing layer,
wind cues and breath points, continuo figures, and an 11×17-inch portrait
conductor layout.

## Repository layout

```text
audio/   current mock-up and retained comparison renders
build/   WAV and generated musical-metrics report
docs/    orchestration and editorial notes
score/   MusicXML, compressed MXL, native MuseScore, PDF, and MIDI
source/  Mutopia LilyPond and MIDI source
src/     reproducible orchestration and validation scripts
```

## Rebuilding and checking

Requirements: Python 3.11+, NumPy, and FFmpeg.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make
```

`make check` validates file structure and musical properties. Its report covers
simultaneous sounding staves per bar, continuo presence, active bars and longest
continuous stretch per player, chord/divisi count, figured-bass coverage, and
brass notes outside the natural D harmonic series. The machine-readable report
is written to `build/musical_metrics.json`.

## Credits and license

- Original music: Johann Sebastian Bach
- Orchestral realization and build system: **Codex (OpenAI)**, created in
  collaboration with the repository owner
- Source engraving: Hajo Dezelski / Mutopia Project, based on the
  Bach-Gesellschaft Edition (1879)

The Mutopia source is published under Creative Commons Attribution-ShareAlike
3.0. Bach's composition is public domain; this realization and repository are
shared under [CC BY-SA 3.0](LICENSE).
