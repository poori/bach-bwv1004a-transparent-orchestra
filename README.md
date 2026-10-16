# BWV 1004a: a Leipzig orchestral Chaconne

An experimental orchestral realization of J. S. Bach's *Ciaccona* from the
Partita in D minor, BWV 1004.

The counterfactual premise is specific: **what if Bach had rescored the
Chaconne for the Leipzig Collegium Musicum around 1730?** The available
ensemble is modestly modern, but the musical logic is Baroque: a continuous
figured-bass foundation, recurring ripieno returns, functional wind doubling,
and natural D brass reserved for the festive major-mode crown.

## Listen

The recording can be streamed directly in the browser. The player below uses
GitHub's raw file delivery, so visitors can listen without downloading or
opening the MP3 first.

<audio controls preload="metadata" aria-label="Bach BWV 1004a current orchestral mock-up">
  <source src="https://raw.githubusercontent.com/poori/bach-bwv1004a-transparent-orchestra/main/audio/Bach_BWV1004a_Leipzig_orchestral_realization.mp3" type="audio/mpeg">
  Your browser does not support inline audio. <a href="audio/Bach_BWV1004a_Leipzig_orchestral_realization.mp3?raw=1">Download the current mock-up</a>.
</audio>

[Open or download the current mock-up](audio/Bach_BWV1004a_Leipzig_orchestral_realization.mp3?raw=1)
· [Read the conductor score (LilyPond)](score/Bach_BWV1004a_Leipzig_orchestral_realization_LilyPond_conductor_score.pdf)
· [Edit the LilyPond master](ly/)
· [Open the generated MusicXML](score/Bach_BWV1004a_Leipzig_orchestral_realization.musicxml)
· [Open the packaged MXL](score/Bach_BWV1004a_Leipzig_orchestral_realization.mxl)
· [Open the current MuseScore snapshot](score/Bach_BWV1004a_Leipzig_orchestral_realization.mscz)
· [Read the orchestration notes](docs/orchestration-notes.md)

## 15 October 2026: LilyPond port

The edition's source of truth is now LilyPond, in `ly/`. LilyPond engraves the
11×17-inch conductor score and a MIDI file; the MusicXML that validation and
MuseScore playback use is generated from the same source.

The port was checked by regenerating MusicXML from the new source and
comparing it with the previous master. Every note, rhythm, tuplet, slur,
articulation, dynamic, hairpin, text, rehearsal mark, tempo, continuo figure
and part setting is identical, and all existing validation passes. LilyPond's
MIDI matches it on all 5,817 notes (onsets and sounding pitches). The only
differences are deliberate:

- Natural horns and trumpets have no key signature. The old master wrote
  one sharp for them in the D-minor sections, a transposition error that was
  hidden only because the brass rest there.
- Rests in the pickup bar are ordinary half rests (LilyPond cannot start a
  whole-bar rest mid-bar).
- MuseScore's forced page break before bar 254 is gone; LilyPond lays out the
  pages itself.

The full comparison is in `build/lilypond-port-2026-10-15/roundtrip-report.txt`;
the one-time import script sits beside it.

The MuseScore snapshot, MuseScore PDF and MIDI, and MP3s were rendered from the
pre-port MusicXML. They sound the same, but `make check-artifacts` will fail
until they are re-rendered with `make render` and recorded.

## 5 September 2026 revision

This revision keeps instrumental contrast while giving the main thematic
statements a consistent voice. Violin I carries the opening and final
recollection; Violin II leads the quiet D-major opening, bars 133–140.
Existing notes are exchanged between players instead of adding a permanent
Violin I doubling.

The brass now follow the local harmony in separately shaped phrases, with
staged entries, breaths, and a softened final cadence. The second crown
responds to Bach's changing harmonies rather than repeating the opening
ground formula. Bassoon octave tripling is removed in 79 bar-parts, and the
violone rests through 76 additional bars of complete concertino units where
the remaining bass instruments cover its line.

The uploaded revision was used as an editorial proposal. Its blanket
Violin I additions and inner-voice extensions were not adopted. The source
itself leaves the inner A in bar 3 followed by silence; no B-flat resolution
has been invented there.

The original master and uploaded proposal are preserved locally under
`build/revision-2026-09-05/before/`. The replay script and editorial audit
sit beside them and are not part of the default build.

## Scoring

- Pairs of flutes, oboes, and bassoons; two natural horns in D; two natural
  trumpets in D; timpani (D–A); and strings (suggested ripieno 4.4.3.2.1).
- Double bass reinforces the larger returns; the bassoons and cello share
  the continuo, with relief for exact octave doubling. A keyboard continuo is
  indicated but not assigned its own staff.
- Sustained inner voices support Bach's single-line figuration where they do
  not contradict its chromatic motion; sparse passages are left sparse.
- Winds primarily double complete string/source lines in overlapping two-bar
  cells, with written breathing windows and a few independent color changes.
- Horns enter at bar 157, trumpets at 165, and timpani at 169; their second
  entries are staggered at 197, 201, and 205. All withdraw before D minor.
  Every brass pitch is restricted to the notated D-natural harmonic series.

The checked-in Mutopia LilyPond and MIDI are both in `source/`. Validation
checks coverage of all 3,083 source MIDI notes across the non-brass ensemble,
allowing octave redistribution and split notation. Separately, it checks the
reviewed thematic voice assignments at bars 1–8, 133–140, and 249–257.
A D4 reattack in bar 253 comes directly from the LilyPond melody: the MIDI
merges it with a held unison.

These checks establish specific kinds of fidelity, not a claim that the
orchestration is a historically authenticated Bach rescoring or that numerical
coverage guarantees musical phrasing.

The score includes actual rehearsal marks A–Q, two-bar *poco accel.*/*poco
rit.* transitions between tempo plateaus, a first articulation/bowing layer,
wind cues and breath points, continuo figures, and an 11×17-inch portrait
conductor layout.

Listening landmarks in the current recording (approximately): 6:10 for the
quiet D-major theme, 7:13 for the first horn entry, 7:44 for the first crown,
and 11:18 for the theme's final recollection.

## Repository layout

```text
audio/   current mock-up and retained comparison renders
build/   validation reports, review renders, and one-shot proposals
docs/    orchestration and editorial notes
ly/      LilyPond master: the source of truth
score/   LilyPond conductor score and MIDI; generated MusicXML and MXL;
         MuseScore snapshot, PDF, and MIDI
source/  Mutopia LilyPond and MIDI source
src/     export, engraving, validation, packaging, and proposal tools
```

## Editing, checking, and packaging

The LilyPond files in `ly/` are the source of truth (LilyPond 2.24):

```text
ly/bwv1004a.ly              conductor score layout and MIDI
ly/score.ily                instruments, staff order, MIDI instruments and pan
ly/definitions.ily          shared helpers
ly/parts/00-global.ily      meter, pickup, key signatures
ly/parts/00-structure.ily   rehearsal marks, section tempi, poco accel./rit.
ly/parts/NN-*.ily           one file per player, one bar per line
ly/parts/15-violoncello-figures.ily   continuo figures
```

Make musical corrections in those files. Each part is written in absolute
pitch (`\fixed`), with a bar check and bar-number comment on every line; the
pickup counts as bar 1. Brass parts are written pitch, with `\transposition`
for MIDI. Two export hints, `\xmlBarEnd` and `\xmlOffset`, carry MusicXML
details LilyPond has no notion of; they do not affect the engraving.

Everything else is derived. Editing the `.musicxml`, `.mxl`, `.mscz`, `.pdf`,
`.mid` or `.mp3` files does not update the master.

The default build never composes or replaces notes:

```bash
make
make test
```

`make` regenerates the MusicXML from `ly/` (`make musicxml`), validates it
(`make check`), packages it as deterministic MXL, and engraves the conductor
score and MIDI (`make engrave`). The export reads the music through LilyPond
itself and fails on anything it cannot represent, rather than dropping it;
any LilyPond warning also fails the build. `make compare` lists the musical
differences from an earlier commit's MusicXML (`BASELINE=<commit>`).
The tests check that the checked-in MusicXML is exactly what `ly/` generates. `make check-artifacts` additionally checks the published
MuseScore, MIDI, audio, and track-profile snapshots for structural integrity;
the MXL package is also checked byte-for-byte against the master. A checksum
manifest ties the current derivatives to the master used to export them.

Validation covers exact filled duration on every staff, instrument ranges,
continuo presence, active bars and longest continuous stretch per player,
figured-bass coverage, every horn/trumpet pitch against the natural D harmonic
series, and simultaneous natural/altered forms of the same concert-pitch
letter. A reviewed, time-resolved harmony map checks every brass note, including
short notes; simultaneous bass tripling is reported with actual pitch and timing.
Density remains a report metric, not a pass condition. The
machine-readable report is written to `build/musical_metrics.json`.

`make render MUSESCORE=/path/to/mscore` creates review-only MuseScore, PDF,
MIDI, and MP3 exports under `build/render/`; it does not replace published
artifacts. The render pipeline uses MuseSounds and reserves 4 dB of master
headroom before encoding. The installed application can abort on shutdown after
writing notation files; only that specific failure is recoverable, and only
when every expected file is fresh and structurally complete. Failed audio
exports are never accepted through this recovery path. Logs remain in the
render directory. `make proposal` runs the former rule-based orchestrator once and
writes its complete proposal under `build/proposals/`. NumPy is required only
for that opt-in proposal tool. Neither target can overwrite the master. After reviewing and promoting the
exports, `python3 src/record_artifacts.py` records their checksums for
`make check-artifacts`; recording hashes itself does not perform musical QA.

The current listening render uses MuseSounds with MS Basic fallback for the
two natural-D horns and violone; see the exported track report and editorial
notes for the exact assignments. The separately named MuseScore Basic render
and the performance-preview excerpt are retained earlier comparisons, not exports
of this revision.

## Credits and license

- Original music: Johann Sebastian Bach
- Orchestral realization and build system: **Codex (OpenAI)**, created in
  collaboration with the repository owner
- Editorial feedback and provisional brass/bass revision: **Claude (Anthropic)**
- Selective source review, final editing, and validation: **Codex (OpenAI)**
- LilyPond port and MusicXML export: **Claude (Anthropic)**
- Source engraving: Hajo Dezelski / Mutopia Project, based on the
  Bach-Gesellschaft Edition (1879)

The Mutopia source is published under Creative Commons Attribution-ShareAlike
3.0. Bach's composition is public domain; this realization and repository are
shared under [CC BY-SA 3.0](LICENSE).
