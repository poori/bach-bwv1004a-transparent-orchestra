# Orchestration and editorial notes

This revision takes Bach's own rescoring habits—not modern timbre-painting—as
its premise. In the transformations of solo material associated with BWV 1006,
1001, and related works, Bach retains the source line while supplying bass,
inner voices, and continuously participating ensemble parts. The orchestral
Chaconne follows that model.

## Musical architecture

The realization retains the 257-bar form. Its initial source layer was audited
against 3,083 Bach notes; the September revision preserves all distinct
non-brass pitch/rhythm events of the preceding master. Four editorial layers
surround the source material:

1. **Continuo.** The repeating ground is read from Bach's opening bass:
   D–C-sharp | D–B-flat | G–A–C-sharp | D; B-flat rises to B-natural in the
   major. Double bass reinforces the ripieno pillars; Bassoons I and II alternate
   four-bar units, and cello joins selected variations. Parenthesized figures
   make the keyboard realization explicit.
2. **Ripieno harmony.** Sustained string inner voices support the source line
   only where they remain compatible with its chromatic motion.
3. **Wind doubling.** Oboes principally reinforce the upper string/source
   lines; flutes double at pitch or octave; Bassoon I reinforces the lower
   strand. Two-bar overlaps provide imitation and breathing windows rather than
   six isolated four-bar solos.
4. **D-major brass.** The opening, bars 133–156, has no brass or timpani.
   Horns enter at 157, trumpets at 165, and timpani at 169, gathering toward
   the crown at 169–176. The second ascent introduces horns at 197, trumpets
   at 201, and timpani at 205. The existing natural-D pitches are retained.
   Brass is absent from every D-minor bar.

The formal plan is concerto-grosso-like: recurring four-bar ripieno statements
alternate with concertino figuration, while continuo prevents the single-line
source passages from becoming unaccompanied orchestral solos. Bars 209–228,
229–248, and 249–256 retain Violin I and a full bass foundation at their
climaxes.

## Notation and performance

- Rehearsal marks A–Q are native MusicXML rehearsal marks.
- Sectional tempo levels are approached with written *poco accel.* or *poco
  rit.* indications and two-bar ramps in MIDI/audio playback.
- Rapid gestures are slurred by beat; recurring light staccatos clarify the
  dance; relay endings receive tenuto releases or wind breath marks.
- Pizzicato inner strings at the first concertino return to arco at the first
  ripieno. Wind re-entries after longer gaps include cue labels.
- Suggested ripieno strings are 4.4.3.2.1, with one player per concertino part.
- Horn and trumpet parts are genuinely transposing parts in D. This edition
  chooses the practical D-alto convention used by its modern natural-horn
  mock-up: written C sounds concert D (+2 semitones). The generated MIDI/audio
  retain concert pitch, while MusicXML stores written pitch with that explicit
  +2-semitone declaration; a D-basso historical edition would require a
  different written register and is intentionally not mixed into this file.
- The full score uses 11×17-inch portrait pages.

## Audit boundaries

The MusicXML score is now the checked-in editorial master, not a generated
build artifact. The rule-based orchestrator that established the initial
continuo, ripieno, wind-doubling, and natural-brass layers remains available
only as a one-shot proposal tool. Its output is isolated under `build/` and
cannot replace the master.

Validation deliberately checks constraints rather than recomposing the piece.
It rejects incomplete bars, professional-range violations, missing continuo
bars, simultaneous natural/altered forms of the same sounding letter, and horn
or trumpet notes outside the D-natural harmonic series. Density and chair use
remain report metrics rather than targets that force invented notes. Published
MXL, MuseScore, MIDI, and audio files have a separate structural-integrity
check, while MXL is checked byte-for-byte against the master. A musician can
therefore validate a MusicXML edit before refreshing the other derivatives.

The mock-up remains a synthetic proof of entries and architecture, not a
substitute for rehearsal. A live reading should refine continuo registration,
wind breath placement, desk-level bowings, and the balance of the staged brass
entries.

## Instrumentation

2 flutes, 2 oboes, 2 bassoons, 2 natural horns in D, 2 natural trumpets in D,
timpani (D–A), Violin I, Violin II, viola, violoncello, double bass, and a
notional organ or harpsichord continuo.

## Editorial revision, 4 September 2026

The compositional aim is a longer dramatic arc: a luminous major-mode
opening, a delayed ceremonial crown, and a final return heard as recollection.
The notes were edited in the authoritative MusicXML, without regenerating
the original arrangement.

- Horns now sound in 32 bars each, trumpets in 20, timpani in 12 (previously
  56 each). New entry accents and separate dynamics articulate those arrivals.
- Flute II loses 18 bars of exact doubling, Oboe II 26, around the major-mode
  threshold, the minor return, and the subsiding passage. A bar was removed
  only when all its pitch, onset, and duration events remained in another
  non-brass part, and it carried no protected words, ties, wedges, or ornaments.
- Double bass and the accompanying second bassoon receive lower dynamics.
  Existing four-bar melodic relays have explicit foreground dynamics.
- Bars 249–254 return at mf/mp, with *nobile, come un ricordo* in Violin I;
  the final continuo is pp. The existing tempo map and final fermata remain.

The revision audit verifies equality of the distinct non-brass pitch/onset/
duration event sets before and after editing. This verifies the specific
subtractions; it is not a new note-by-note provenance audit against Mutopia.
The complete pre-revision artifacts are preserved under
`build/revision-2026-09-04/before/`.

The current listening copy uses the MuseSounds profile: 13 staves use Muse
samples; the two natural-D horns and violone use MuseScore's MS Basic fallback.
The freshly exported track report records those assignments. The native
notation and transposition remain unchanged by the audio fallback. The MP3
is 11:53; a decode check measured a peak of -0.4 dBFS.

Final review: the opening cue is now *Grave — sostenuto*, reflecting the
participating oboe and continuo. The title page credits the orchestration to
Codex (OpenAI), with Johann Sebastian Bach retained as composer.
