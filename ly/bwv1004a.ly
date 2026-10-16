\version "2.24.0"

%% BWV 1004a — conductor score (11×17 in, portrait) and LilyPond MIDI.
%% Build from the repository root with `make engrave`.

\include "score.ily"

#(set-global-staff-size 15)

\paper {
  #(set-paper-size "11x17")
  top-margin = 12\mm
  bottom-margin = 12\mm
  left-margin = 14\mm
  right-margin = 12\mm
  indent = 30\mm
  short-indent = 16\mm
  system-system-spacing.basic-distance = 14
  ragged-last-bottom = ##t
  print-page-number = ##t
}

\score {
  \orchestra
  \layout {
    \context {
      \Score
      tempoHideNote = ##t
      \override MetronomeMark.font-series = #'medium
      \override RehearsalMark.font-size = #2
      barNumberVisibility = #(every-nth-bar-number-visible 5)
      \override BarNumber.break-visibility = ##(#f #t #t)
      \override BarNumber.font-size = #-1
    }
    \context {
      \Staff
      \RemoveEmptyStaves
    }
    \context {
      \FiguredBass
      \override BassFigureBracket.stencil = #parenthesized-figure-bracket
      \override BassFigure.font-size = #-1
      %% Keep staff texts above the double bass clear of the figures.
      \override VerticalAxisGroup.nonstaff-unrelatedstaff-spacing.padding = #2.5
    }
    \context {
      \Dynamics
      \override TextScript.font-size = #0
    }
  }
}

\score {
  \unfoldRepeats \orchestra
  \midi {
    \context { \Score midiChannelMapping = #'instrument }
  }
}
