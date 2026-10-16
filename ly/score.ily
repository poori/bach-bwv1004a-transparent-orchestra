\version "2.24.0"

%% The full ensemble: instruments, staff order and grouping. Included by the
%% engraved score (bwv1004a.ly) and by the MusicXML export (musicxml-export.ly).
%% Voice and context names are the stable keys the export maps to MusicXML
%% parts (see musicxml-export.json).

\include "definitions.ily"
\include "parts/00-global.ily"
\include "parts/00-structure.ily"
\include "parts/01-flute-1.ily"
\include "parts/02-flute-2.ily"
\include "parts/03-oboe-1.ily"
\include "parts/04-oboe-2.ily"
\include "parts/05-bassoon-1.ily"
\include "parts/06-bassoon-2.ily"
\include "parts/07-horn-1.ily"
\include "parts/08-horn-2.ily"
\include "parts/09-trumpet-1.ily"
\include "parts/10-trumpet-2.ily"
\include "parts/11-timpani.ily"
\include "parts/12-violin-1.ily"
\include "parts/13-violin-2.ily"
\include "parts/14-viola.ily"
\include "parts/15-violoncello.ily"
\include "parts/15-violoncello-figures.ily"
\include "parts/16-double-bass.ily"

\header {
  title = "Chaconne in D minor, BWV 1004a (Leipzig orchestral realization)"
  composer = "Johann Sebastian Bach"
  copyright = "Source engraving: Hajo Dezelski / Mutopia Project, CC BY-SA 3.0. Arrangement shared under CC BY-SA 3.0."
  tagline = ##f
}

%% Stereo position is MusicXML pan / 90 (MuseScore's mixer degrees).
orchestra = <<
  \new Dynamics = "structure" \structure
  \new StaffGroup = "woodwinds" <<
    \new Staff = "fluteOne" \with {
      instrumentName = "Flute I" shortInstrumentName = "Fl. I"
      midiInstrument = "flute" midiPanPosition = #(/ -37 90)
    } \new Voice = "fluteOne" << \global \fluteOne >>
    \new Staff = "fluteTwo" \with {
      instrumentName = "Flute II" shortInstrumentName = "Fl. II"
      midiInstrument = "flute" midiPanPosition = #(/ -20 90)
    } \new Voice = "fluteTwo" << \global \fluteTwo >>
    \new Staff = "oboeOne" \with {
      instrumentName = "Oboe I" shortInstrumentName = "Ob. I"
      midiInstrument = "oboe" midiPanPosition = #(/ -26 90)
    } \new Voice = "oboeOne" << \global \oboeOne >>
    \new Staff = "oboeTwo" \with {
      instrumentName = "Oboe II" shortInstrumentName = "Ob. II"
      midiInstrument = "oboe" midiPanPosition = #(/ -9 90)
    } \new Voice = "oboeTwo" << \global \oboeTwo >>
    \new Staff = "bassoonOne" \with {
      instrumentName = "Bassoon I" shortInstrumentName = "Bsn. I"
      midiInstrument = "bassoon" midiPanPosition = #(/ -17 90)
    } \new Voice = "bassoonOne" << \global \clef bass \bassoonOne >>
    \new Staff = "bassoonTwo" \with {
      instrumentName = "Bassoon II" shortInstrumentName = "Bsn. II"
      midiInstrument = "bassoon" midiPanPosition = #(/ 3 90)
    } \new Voice = "bassoonTwo" << \global \clef bass \bassoonTwo >>
  >>
  \new StaffGroup = "brass" <<
    \new Staff = "hornOne" \with {
      instrumentName = "Horn I in D" shortInstrumentName = "Hn. I in D"
      midiInstrument = "french horn" midiPanPosition = #(/ -40 90)
    } \new Voice = "hornOne" << \globalBrass \hornOne >>
    \new Staff = "hornTwo" \with {
      instrumentName = "Horn II in D" shortInstrumentName = "Hn. II in D"
      midiInstrument = "french horn" midiPanPosition = #(/ 9 90)
    } \new Voice = "hornTwo" << \globalBrass \hornTwo >>
    \new Staff = "trumpetOne" \with {
      instrumentName = "Trumpet I in D" shortInstrumentName = "Tpt. I in D"
      midiInstrument = "trumpet" midiPanPosition = #(/ -49 90)
    } \new Voice = "trumpetOne" << \globalBrass \trumpetOne >>
    \new Staff = "trumpetTwo" \with {
      instrumentName = "Trumpet II in D" shortInstrumentName = "Tpt. II in D"
      midiInstrument = "trumpet" midiPanPosition = #(/ 17 90)
    } \new Voice = "trumpetTwo" << \globalBrass \trumpetTwo >>
  >>
  \new Staff = "timpani" \with {
    instrumentName = "Timpani (D–A)" shortInstrumentName = "Timp."
    midiInstrument = "timpani" midiPanPosition = 0
  } \new Voice = "timpani" << \global \clef bass \timpani >>
  \new StaffGroup = "strings" \with {
    %% Repeat rehearsal marks above the strings for the conductor.
    \consists Mark_engraver
    \consists Staff_collecting_engraver
  } <<
    \new Staff = "violinOne" \with {
      instrumentName = "Violin I" shortInstrumentName = "Vln. I"
      midiInstrument = "violin" midiPanPosition = #(/ -51 90)
    } \new Voice = "violinOne" << \global \violinOne >>
    \new Staff = "violinTwo" \with {
      instrumentName = "Violin II" shortInstrumentName = "Vln. II"
      midiInstrument = "violin" midiPanPosition = #(/ -29 90)
    } \new Voice = "violinTwo" << \global \violinTwo >>
    \new Staff = "viola" \with {
      instrumentName = "Viola" shortInstrumentName = "Vla."
      midiInstrument = "viola" midiPanPosition = #(/ 6 90)
    } \new Voice = "viola" << \global \clef alto \viola >>
    \new Staff = "violoncello" \with {
      instrumentName = "Violoncello" shortInstrumentName = "Vc."
      midiInstrument = "cello" midiPanPosition = #(/ 20 90)
    } \new Voice = "violoncello" << \global \clef bass \violoncello >>
    \new FiguredBass = "violoncelloFigures" \violoncelloFigures
    \new Staff = "doubleBass" \with {
      instrumentName = "Double Bass" shortInstrumentName = "Cb."
      midiInstrument = "contrabass" midiPanPosition = #(/ 29 90)
    } \new Voice = "doubleBass" << \global \clef bass \doubleBass >>
  >>
>>
