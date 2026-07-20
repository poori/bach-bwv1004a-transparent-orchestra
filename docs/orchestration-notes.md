# Orchestration and editorial notes

Orchestral realization by **Codex (OpenAI)** using **GPT-5.6 Sol High**,
created in collaboration with the repository owner.

## What works

The arrangement's strongest feature is its architecture. Bach's four implied
voices are treated as independent orchestral lines rather than a solo melody
with accompaniment. Choir changes alter the argument without increasing its
weight, and the late arrival of trumpets and timpani gives the return to D
minor a real structural consequence.

The central D-major span deliberately avoids a generic “heavenly strings”
effect. Flutes and oboe first expose its clarity; strings then take up the
figuration; horns appear only at the crown and later joints.

## What remains open

This is a working realization rather than a performance-tested edition. A
rehearsal may suggest changes to breathing, string distribution, bassoon
register, and the balance of the climactic brass pillars. The synthetic audio
is useful for entries and architecture, but exaggerates hardness and cannot
judge real blend.

The generated edition now contains a complete first phrasing layer: dynamics
and hairpins, beat-shaped slurs in rapid figuration, breath marks at wind-relay
endings, tenuto releases for string relays, and accents reserved for structural
brass/timpani attacks. Rehearsal should still test the density of the slurring,
turn the string phrasing into practical section bowings, and adjust breath
locations to individual players. The differentiated late brass voicings also
remain rehearsal decisions rather than historical claims.

The source MIDI contains the sounding result of the violin score rather than
semantic voice labels. The build separates its maximum four simultaneous
voices by continuity and register, then assigns complete strands to
instruments. In contrapuntal spans, subordinate colors change one at a time
where practical. When the source texture contracts to a single line, the
automatic voice index is set aside and complete two- to four-bar gestures are
relayed between players. This preserves melodic continuity without forcing a
single wind player to sustain violinistic figuration outside a comfortable
register. All 3,083 source notes are retained, including the six low G3/A3
sixteenths in bars 157, 160, and 222–224.

## Structural map

| Bars | Character | Principal ownership of the four strands |
|---:|---|---|
| 1–16 | *Grave* | Violin I, Violin II, viola, cello |
| 17–32 | First opening | Oboe I, Violin I, viola, bassoon I |
| 33–52 | Figuration | Four-bar relays through Violin I, Oboe II, viola, Violin II, and cello |
| 53–56 | First return | Violin I closes the first relay cycle |
| 57–92 | Dialogue | Two- to four-bar relays among winds and strings; low arpeggiation leaves the flutes |
| 93–96 | Gathering return | Ripieno strings |
| 97–120 | First chorale | Staggered handoff to two oboes and two bassoons |
| 121–132 | Gathering motion | Strings |
| 133–148 | D major, *chiaro* | Staggered handoff to two flutes, oboe I, bassoon I |
| 149–164 | D-major flow | Paired phrase relays through oboe, viola, and violins; low inflections retained |
| 165–168 | D-major return | Violin I closes the D-major relay cycle |
| 169–176 | Crown of the major section | Violin I remains principal while flute and oboe alternate below |
| 177–196 | Second chorale | Staggered handoff to two oboes and two bassoons |
| 197–208 | Major-mode cadence | Flute I, oboe I, viola, double bass |
| 209–212 | D minor returns | Ripieno strings; first true brass/timpani pillar |
| 213–228 | Renewed motion | Four-bar relays through Oboe II and viola, then two-bar oboe/violin answers |
| 229–240 | Contrapuntal summit | Brass pillar at 229; Violin I remains principal over staggered lower colors |
| 241–248 | Subsiding | Two-bar relay: Flute I, Oboe I, viola, Violin I |
| 249–254 | Final pillars | Oboe I, Violin I, bassoon I, double bass |
| 255–257 | Coda, *morendo* | Strings |

## Editorial decisions

- The double-bass line is displaced down an octave when it owns the fourth
  strand, preserving pitch class and giving the orchestral bass a credible
  register.
- Horn sonorities occur only at bars 97, 113, 169, 177, 197, 209, 229, and
  249. The orchestra withdraws completely from Bach's final two-string unison
  D rather than completing it as a brass triad.
- Trumpets and timpani are withheld until bar 209 and occur only at 209, 229,
  and 249.
- The written dynamic arc ranges from *pp* to *ff*. Prevailing dynamics are
  restated when a player enters after a rest; 86 curated hairpins shape formal
  transitions and the short relay cells.
- Rapid wind and string figures are slurred within the beat. Nine wind-relay
  endings carry breath marks, string-relay endings use tenuto, and the former
  blanket detached-legato layer has been removed. Short playback gates remain
  separate from the written rhythm.
- At bar 209 the late brass opens from D into a D–A spacing. Bar 249 adds the
  minor third in Trumpet II. Trumpet II releases before Trumpet I at both
  pillars; bar 257 is left to the source's bare D and restored fermata.
- Source semantics absent from MIDI are restored explicitly: trills at bars
  73–74, coordinated arpeggiation at bars 89 and 201, the final fermata, and
  the two-string unison character of the last D.
- Contrapuntal strands retain stable owners within each phrase; subordinate
  choir changes are staggered where practical.
- Single-line figuration is relayed only at two- to four-bar boundaries. The
  low G3/A3 notes once classified as a disposable fourth strand are restored
  inside those gestures: Violin II owns them in 157–160 and viola in 222–224.
- Flute I and II remain at or above C4, and Oboe I and II at or above B-flat3.
  The build validates these professional-range floors on every regeneration.
- The native MuseScore file normalizes the historical D-horn and violone
  catalog identities to French horn and contrabasses for sample assignment;
  this does not alter the score's concert-pitch notation or sounding octaves.
- Tempi range from quarter note = 52 to 72. These are sectional inflections,
  not tempo changes intended to dissolve the dance.
- The score is in concert pitch.

## Instrumentation

2 flutes, 2 oboes, 2 bassoons, 2 horns in D, 2 trumpets in D, timpani (D–A),
Violin I, Violin II, viola, violoncello, and double bass.
