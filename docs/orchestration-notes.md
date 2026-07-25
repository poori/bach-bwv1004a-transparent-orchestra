# Orchestration and editorial notes

This revision takes Bach's own rescoring habits—not modern timbre-painting—as
its premise. In the transformations of solo material associated with BWV 1006,
1001, and related works, Bach retains the source line while supplying bass,
inner voices, and continuously participating ensemble parts. The orchestral
Chaconne follows that model.

## Musical architecture

The 257 source bars and all 3,083 source notes remain intact. Four editorial
layers surround them:

1. **Continuo.** The repeating ground is read from Bach's opening bass:
   D–C-sharp | D–B-flat | G–A–C-sharp | D; B-flat rises to B-natural in the
   major. Double bass sustains it in every bar; Bassoons I and II alternate
   four-bar units, and cello joins selected variations. Parenthesized figures
   make the keyboard realization explicit.
2. **Ripieno harmony.** Sustained string inner voices establish a minimum
   melody–harmony–bass texture. Formal pillars use divisi or double stops.
3. **Wind doubling.** Oboes principally reinforce the upper string/source
   lines; flutes double at pitch or octave; Bassoon I reinforces the lower
   strand. Two-bar overlaps provide imitation and breathing windows rather than
   six isolated four-bar solos.
4. **D-major brass.** Natural horns and trumpets in D, with D–A timpani, crown
   bars 133–176 and 197–208. The clarino figures use only members of the
   D-natural harmonic series. Brass is absent from every D-minor bar.

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
  Divisi and double stops are explicitly allowed at the major and final
  pillars.
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
It rejects incomplete bars, professional-range violations, bars with fewer
than three simultaneous staves, missing continuo bars, underused chairs,
insufficient chord writing, and horn or trumpet notes outside the D-natural
harmonic series. Published MXL, MuseScore, MIDI, and audio files have a separate
structural-integrity check, while MXL is checked byte-for-byte against the
master. A musician can therefore validate a MusicXML edit before refreshing the
other derivatives.

The mock-up remains a synthetic proof of entries and architecture, not a
substitute for rehearsal. A live reading should refine continuo registration,
wind breath placement, desk-level bowings, and the balance of the 56-bar brass
plan.

## Instrumentation

2 flutes, 2 oboes, 2 bassoons, 2 natural horns in D, 2 natural trumpets in D,
timpani (D–A), Violin I, Violin II, viola, violoncello, double bass, and a
notional organ or harpsichord continuo.
