\version "2.24.0"
% Generated once from the MusicXML master by
% build/lilypond-port-2026-10-15/import_musicxml.py; edit freely from here on.
% One bar per line; the comment after each bar check is the bar number
% (the pickup is bar 1, as in the repository's documentation).

% Meter, pickup and key signatures for every non-brass staff.
global = {
  \time 3/4
  \partial 2
  \key d \minor s2 | % 1
  s2.*131 | % 2–132
  \key d \major
  s2.*76 | % 133–208
  \key d \minor
  s2.*49 | % 209–257
}

% Natural brass: written in C with no key signature throughout.
globalBrass = {
  \time 3/4
  \partial 2
  s2 | % 1
  s2.*256 | % 2–257
}
