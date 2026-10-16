\version "2.24.0"

%% Shared helpers for the BWV 1004a LilyPond master.

%% --- MusicXML export hints ------------------------------------------------
%% These change nothing in the engraving or LilyPond MIDI. They carry two
%% MusicXML details that LilyPond has no native notion of, so that the
%% generated MusicXML (used for MuseScore playback) matches the edition.

%% A hairpin that ends at the barline, not on the next note:
%%   d'4 e' f' <>\xmlBarEnd \! |
xmlBarEnd =
#(define-event-function (ev) (ly:event?)
   (ly:music-set-property! ev 'xml-bar-end #t)
   ev)

%% Text drawn later than the note it belongs to, in MusicXML divisions
%% (384 = one quarter note). Visual only; playback position is unchanged.
%%   r16 -\xmlOffset #384 ^\markup \italic "arpeggiate upward, together"
xmlOffset =
#(define-event-function (divisions ev) (integer? ly:event?)
   (ly:music-set-property! ev 'xml-offset divisions)
   ev)

%% --- Notation helpers -----------------------------------------------------

%% Triplet with neither bracket nor number (used where the grouping is
%% obvious from the beaming).
hideTuplet = { \once \omit TupletBracket \once \omit TupletNumber }

%% Continuo figures in [ ] are ad lib.; print the bracket as parentheses.
#(define (parenthesized-figure-bracket grob)
   (let* ((bracket (ly:enclosing-bracket::print grob))
          (x (ly:stencil-extent bracket X))
          (y (ly:stencil-extent bracket Y))
          (inner (ly:make-stencil '()
                                  (cons 0 (- (interval-length x) 1.0))
                                  (cons (+ (car y) 0.15) (- (cdr y) 0.15)))))
     (ly:stencil-translate-axis
      (parenthesize-stencil inner 0.07 0.3 0 0.12)
      (+ (car x) 0.5)
      X)))
