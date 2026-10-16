\version "2.24.0"

%% Not an engraving: replays the score through LilyPond with the event dump
%% attached, for src/ly_to_musicxml.py. Build with `make musicxml`.

\include "score.ily"
\include "tools/event-dump.ily"

#(musicxml-dump-header)

\paper { page-breaking = #ly:one-page-breaking }

\score {
  \orchestra
  \layout {
    \context { \Voice \consists \musicxmlEventDump }
    \context { \Dynamics \consists \musicxmlEventDump }
    \context { \FiguredBass \consists \musicxmlEventDump }
  }
}
