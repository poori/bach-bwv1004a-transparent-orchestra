# BWV 1004a: a transparent orchestral Chaconne

An experimental full orchestral realization of J. S. Bach's *Ciaccona* from
the Partita in D minor, BWV 1004.

The premise is deliberately counterfactual: **what if Bach had written the
Chaconne for the Leipzig Collegium Musicum, with a modest modern orchestra at
his disposal but a Baroque ear still governing the result?**

[Listen to the MP3 mock-up](audio/Bach_BWV1004a_transparent_orchestra.mp3?raw=1)
· [Listen to the Muse Sounds render](audio/Bach_BWV1004a_transparent_orchestra_MuseSounds.mp3?raw=1)
· [Listen to the MuseScore Basic render](audio/Bach_BWV1004a_transparent_orchestra_MuseScore_Basic.mp3?raw=1)
· [Open the native MuseScore score](score/Bach_BWV1004a_transparent_orchestra.mscz)
· [Open the editable score](score/Bach_BWV1004a_transparent_orchestra.mxl)
· [Read the orchestration notes](docs/orchestration-notes.md)

## The sound I was after

This is closer to *Brandenburg Concerto No. 6* meeting the *St. Matthew
Passion* than to a Romantic tone poem:

- a modest orchestra: pairs of flutes, oboes, and bassoons; two horns; two
  trumpets; timpani; and strings;
- four audible contrapuntal strands, normally owned by one instrument each;
- winds inheriting complete lines rather than coloring a permanent string pad;
- brass and timpani reserved for formal pillars;
- a bright but largely unbrassed D-major center;
- a persistent dance pulse.

The 257-bar score is complete. The current release is best understood as a
public **v0.1 realization**: ranges, source-note identity, and file integrity
are checked, but the orchestration has not yet been rehearsed by a live
orchestra.

The MuseScore file is a native import snapshot of the generated MusicXML,
normalized so all sixteen orchestral parts resolve to installed Muse Sounds.
Both Muse Sounds and MuseScore Basic renders are retained for comparison.

## Credits

- Original music: Johann Sebastian Bach
- Orchestral realization and build system: **Codex (OpenAI)**
- Model: **GPT-5.6 Sol High**
- Created in collaboration with the repository owner
- Source engraving: Hajo Dezelski / Mutopia Project

## Repository layout

```text
audio/   listening mock-up
docs/    orchestration and editorial notes
score/   MusicXML, compressed MXL, native MuseScore, and MIDI
source/  Mutopia LilyPond and MIDI source
src/     reproducible orchestration/build script
```

## Rebuilding

Requirements: Python 3.11+, NumPy, and FFmpeg.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make
```

The build regenerates the MusicXML, MXL, MIDI, WAV, and MP3. Run `make check`
for structural validation.

## Source and license

The note source is Hajo Dezelski's [Mutopia Project engraving of BWV
1004](https://www.ibiblio.org/mutopia/cgibin/piece-info.cgi?id=1426), based on
the Bach-Gesellschaft Edition (1879), published under Creative Commons
Attribution-ShareAlike 3.0. The source files are retained in `source/` with
their original attribution metadata.

Bach's composition is public domain. This realization and repository are
shared under [CC BY-SA 3.0](LICENSE).
