# BWV 1004a: a Leipzig orchestral Chaconne

An experimental orchestral realization of J. S. Bach's *Ciaccona* from the
Partita in D minor, BWV 1004.

The counterfactual premise is specific: **what if Bach had rescored the
Chaconne for the Leipzig Collegium Musicum around 1730?** The available
ensemble is modestly modern, but the musical logic is Baroque: a continuous
figured-bass foundation, recurring ripieno returns, functional wind doubling,
and natural D brass reserved for the festive major-mode crown.

[Listen to the current mock-up](audio/Bach_BWV1004a_Leipzig_orchestral_realization.mp3?raw=1)
· [Edit the authoritative MusicXML](score/Bach_BWV1004a_Leipzig_orchestral_realization.musicxml)
· [Open the packaged MXL](score/Bach_BWV1004a_Leipzig_orchestral_realization.mxl)
· [Open the current MuseScore snapshot](score/Bach_BWV1004a_Leipzig_orchestral_realization.mscz)
· [Read the orchestration notes](docs/orchestration-notes.md)

## September 2026 revision

The D-major opening now unfolds without brass. Staged horn, trumpet, and
timpani entries give the two crowns a stronger sense of arrival; lighter
continuo dynamics and 44 fewer bars of exact wind doubling expose the
concertino lines. The final return is marked *nobile, come un ricordo*, with
a gentler dynamic than the preceding summit. All distinct non-brass sounding
pitch/rhythm events in the previous master are preserved.

The pre-revision files are retained locally in
`build/revision-2026-09-04/before/`; the editorial audit and one-time revision
script sit beside them. They are not part of the default build.

## Scoring

- Pairs of flutes, oboes, and bassoons; two natural horns in D; two natural
  trumpets in D; timpani (D–A); and strings (suggested ripieno 4.4.3.2.1).
- Double bass reinforces the ripieno pillars; the bassoons alternate
  four-bar units and cello joins selected variations. A keyboard continuo is
  indicated but not assigned its own staff.
- Sustained inner voices support Bach's single-line figuration where they do
  not contradict its chromatic motion; sparse passages are left sparse.
- Winds primarily double complete string/source lines in overlapping two-bar
  cells, with written breathing windows and a few independent color changes.
- Horns enter at bar 157, trumpets at 165, and timpani at 169; their second
  entries are staggered at 197, 201, and 205. All withdraw before D minor.
  Every brass pitch is restricted to the notated D-natural harmonic series.

The frozen 257-bar realization was produced from an audited layer containing
all 3,083 source notes and their pitch classes, rhythms, ornaments, and final
fermata. From this revision forward, note-level changes are editorial decisions
made directly in the score and reviewed as ordinary diffs.

The score includes actual rehearsal marks A–Q, two-bar *poco accel.*/*poco
rit.* transitions between tempo plateaus, a first articulation/bowing layer,
wind cues and breath points, continuo figures, and an 11×17-inch portrait
conductor layout.

## Repository layout

```text
audio/   current mock-up and retained comparison renders
build/   validation reports, review renders, and one-shot proposals
docs/    orchestration and editorial notes
score/   authoritative MusicXML plus published MXL, MuseScore, PDF, and MIDI
source/  Mutopia LilyPond and MIDI source
src/     validation, packaging, and opt-in proposal tools
```

## Editing, checking, and packaging

The checked-in `.musicxml` file is the source of truth. Open that file in
MuseScore, make musical corrections there, and export back to the same
MusicXML path. The `.mxl`, `.mscz`, `.pdf`, `.mid`, and `.mp3` files are
published derivatives; editing one of them does not update the master.

The default build never composes or replaces notes:

```bash
make
```

That validates the master and packages its exact bytes as deterministic MXL.
`make check` checks the editable master alone, so it is useful immediately
after a hand edit. `make check-artifacts` additionally checks the published
MuseScore, MIDI, audio, and track-profile snapshots for structural integrity;
the MXL package is also checked byte-for-byte against the master.

Validation covers exact filled duration on every staff, instrument ranges,
continuo presence, active bars and longest continuous stretch per player,
figured-bass coverage, every horn/trumpet pitch against the natural D harmonic
series, and simultaneous natural/altered forms of the same concert-pitch
letter. Density remains a report metric, not a pass condition. The
machine-readable report is written to `build/musical_metrics.json`.

`make render MUSESCORE=/path/to/mscore` creates review-only MuseScore, PDF,
MIDI, and MP3 exports under `build/render/`; it does not replace published
artifacts. `make proposal` runs the former rule-based orchestrator once and
writes its complete proposal under `build/proposals/`. NumPy is required only
for that opt-in proposal tool. Neither target can overwrite the master.

The current listening render uses MuseSounds with MS Basic fallback for the
two natural-D horns and violone; see the exported track report and editorial
notes for the exact assignments.

## Credits and license

- Original music: Johann Sebastian Bach
- Orchestral realization and build system: **Codex (OpenAI)**, created in
  collaboration with the repository owner
- Source engraving: Hajo Dezelski / Mutopia Project, based on the
  Bach-Gesellschaft Edition (1879)

The Mutopia source is published under Creative Commons Attribution-ShareAlike
3.0. Bach's composition is public domain; this realization and repository are
shared under [CC BY-SA 3.0](LICENSE).
