# Orchestration and editorial notes

This is an experimental orchestral realization of the Chaconne, imagined
for a Leipzig ensemble around 1730. It is an editorial interpretation, not
a reconstruction of a lost Bach score. The aim is to make the dance, bass
motion, and changing scale of Bach's writing audible through contrasting
instrumental groups.

## Musical architecture

The 257-bar form, minor–major–minor trajectory, sectional tempo map, and
final fermata are retained. Strings, winds, and continuo exchange foreground
roles; a quiet major-mode opening precedes two staged brass crowns.

Violin I carries the opening theme (1–8) and its final recollection (249–257).
Violin II carries the opening major-mode phrase (133–140), with a light wind
color around it. Elsewhere, the established phrase relays remain. These are
local decisions about thematic identity, not a requirement that the first
violins play continuously.

The continuo is shared by cello and bassoons. Violone reinforces the larger
returns and withdraws for complete concertino units at 33–52, 77–92,
133–156, and 213–228. Every removed violone interval remains covered in
pitch class and duration by the remaining bass instruments. An additional
79 bassoon bar-parts lose exact simultaneous octave tripling with cello and
violone; independent bassoon material remains.

Horns enter at 157 and 197, trumpets at 165 and 201, and timpani at 169 and
205. The brass are written as local statements and answers, with space for
the string figuration. Their harmony is reviewed against the source within
each bar, including the more varied progressions of 197–208. They do not
repeat a four-bar harmonic template.

In bar 176, the brass acknowledge the D/F-sharp resolution on beat two and
move to dominant support on beat three. In 208, the dominant gives way to
an open D at the end of the bar, softened to mp before the minor return.
Cadence bars are therefore not categorically silent. Timpani mark selected
arrivals and dominant preparations rather than repeating D–A every bar.
No brass or timpani sound in the minor sections.

## Selective review, 5 September 2026

The browser-produced proposal correctly drew attention to repetitive brass,
bass weight, and the difference between source-note coverage and audible
phrase continuity. It informed the revision, but was not promoted wholesale.

- The 136 blanket Violin I additions were discarded. Source strands were
  instead exchanged in the three thematic windows above. Violin I remains
  active in 123 bars, rather than being required to play in all 257.
- The brass were rewritten against local source harmony, retaining the idea
  of staged entries and phrase-shaped writing.
- Bass thinning uses simultaneous pitches and durations, not just equal
  numbers of notes or the fact that three instruments are active.
- The proposed inner-voice extensions were discarded. In the source,
  melodyTwo itself has A followed by a skip in bar 3. Extending every
  interrupted inner voice can obscure intentional releases; the proposal's
  extended F-natural in bar 215 also collided with the melody's F-sharp.
- The closing theme includes melodyOne's D4 sixteenth-note reattack in bar
  253, which the source MIDI merges with another voice's sustained unison.
- The first bowing layer is rebuilt only in bars whose source ownership
  changes. It remains a starting point for a player's bowing decisions.
- Tool credits are kept in repository documentation and encoding metadata,
  rather than on the performance title page.

Both the previous master and the uploaded proposal are preserved locally in
`build/revision-2026-09-05/before/`. The one-time replay script and change
audit remain beside them.

## Notation and performance

Rehearsal marks A–Q, the two-bar tempo transitions, ornaments, and the final
fermata remain. The suggested string complement is 4.4.3.2.1, with one player
per concertino part. A notional organ or harpsichord may realize the
parenthesized continuo figures; it has no dedicated playback staff.

Natural horns and trumpets are notated in D using this edition's D-alto
convention: written C sounds concert D, two semitones higher. MIDI and audio
use sounding pitch. This convention is consistent within the edition;
another historical horn register would require a separate transposition
decision.

The conductor score uses 11×17-inch portrait pages. Listen for the quiet
second-violin phrase at the major entrance, the answering brass rather than
a continuously busy fanfare, and the opening theme returning in Violin I.
The mock-up is useful for timing and balance decisions; breath placement,
bowing, and live continuo registration still benefit from rehearsal.

## Validation and reproducibility

MusicXML is the editorial master. The proposal generator is opt-in and
cannot overwrite it. MXL packages the master's exact bytes; MuseScore, PDF,
MIDI, and the current MP3 are regenerated derivatives.

The validator checks bar duration and written rhythm, selected instrumental
ranges, continuo presence, natural-D brass pitches, and simultaneous
natural/altered forms of the same sounding letter. It also checks:

- Coverage of all 3,083 source MIDI notes by the non-brass ensemble, allowing
  octave redistribution and split notation.
- The reviewed source melody assignments in the three thematic windows.
- Every brass interval against `brass-harmony.json`, including short notes
  and changes of harmony within a bar.
- Actual simultaneous bass tripling as a report metric.
- Current derivative checksums against the exported master.

The harmony map is an explicit editorial analysis, not an automatic proof of
all harmony or counterpoint in the score. Source-note coverage does not
certify balance, phrasing, or the correctness of every added inner voice.
Regression tests demonstrate that the checks catch a missing source note,
an active violin playing accompaniment instead of the theme, a short brass
tonic over the dominant, the bar 215 collision, and a three-beat pickup.

The revised conductor PDF has 53 pages. The full recording is approximately
11:52, with a decoded peak of -2.4 dBFS after reserving headroom before export.
The current full-length listening copy uses MuseSounds with explicit
MS Basic fallback for the two natural-D horns and violone. The exported
track report records those assignments. The separately named MuseScore
Basic recording and bars 125–156 performance-preview study are earlier
comparisons; they are not current-score exports.

## Credits and source

Original music: Johann Sebastian Bach. Source engraving: Hajo Dezelski /
Mutopia Project, based on the Bach-Gesellschaft Edition. Orchestral
realization and build system: Codex (OpenAI), in collaboration with the
repository owner. Editorial feedback and provisional revisions: Claude
(Anthropic). Selective integration and source review: Codex (OpenAI).

The source engraving and this project are shared under CC BY-SA 3.0.
