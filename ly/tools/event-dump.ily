\version "2.24.0"

%% Event dump for the MusicXML export (src/ly_to_musicxml.py).
%%
%% LilyPond does the parsing; this engraver writes every music event it hears,
%% with its moment and context, as one JSON object per line to
%% <output-name>.events.jsonl. Python then rebuilds MusicXML from those
%% events, so any valid LilyPond input is read exactly as LilyPond reads it.

#(define mx-port #f)
#(define (mx-out)
   (if (not mx-port)
       (begin
        (set! mx-port (open-output-file
                       (string-append (ly:parser-output-name) ".events.jsonl")))
        (set-port-encoding! mx-port "UTF-8")))
   mx-port)

#(define (mx-escape s)
   (call-with-output-string
    (lambda (p)
      (string-for-each
       (lambda (c)
         (cond ((char=? c #\") (display "\\\"" p))
               ((char=? c #\\) (display "\\\\" p))
               ((char=? c #\newline) (display "\\n" p))
               ((char<? c #\space) (display " " p))
               (else (display c p))))
       s))))

#(define (mx-json v)
   (cond ((string? v) (string-append "\"" (mx-escape v) "\""))
         ((eq? v #t) "true")
         ((eq? v #f) "false")
         ((null? v) "[]")
         ((and (number? v) (exact? v) (integer? v)) (number->string v))
         ((and (number? v) (exact? v)) (string-append "\"" (number->string v) "\""))
         ((number? v) (number->string v))
         ((symbol? v) (mx-json (symbol->string v)))
         ((and (pair? v) (symbol? (car v)) (eq? (car v) 'obj))
          (string-append
           "{"
           (string-join
            (map (lambda (kv)
                   (string-append (mx-json (symbol->string (car kv))) ":" (mx-json (cdr kv))))
                 (filter (lambda (kv) (not (eq? (cdr kv) '*none*))) (cdr v)))
            ",")
           "}"))
         ((list? v) (string-append "[" (string-join (map mx-json v) ",") "]"))
         (else (mx-json (format #f "~a" v)))))

#(define (mx-emit . alist)
   (let ((port (mx-out)))
     (display (mx-json (cons 'obj (filter (lambda (kv) (not (eq? (cdr kv) '*none*))) alist))) port)
     (newline port)))

#(define (mx-markup-has? m proc)
   (cond ((not (pair? m)) #f)
         ((eq? (car m) proc) #t)
         (else (any (lambda (x) (mx-markup-has? x proc))
                    (filter pair? (if (procedure? (car m)) (cdr m) m))))))

#(define (mx-markup m)
   (if (or (string? m) (pair? m))
       (list 'obj
             (cons 'string (markup->string m))
             (cons 'italic (mx-markup-has? m italic-markup))
             (cons 'box (mx-markup-has? m box-markup)))
       '*none*))

#(define (mx-pitch p)
   (if (ly:pitch? p)
       (list 'obj
             (cons 'step (ly:pitch-notename p))
             (cons 'alter (* 2 (ly:pitch-alteration p)))
             (cons 'octave (+ 4 (ly:pitch-octave p))))
       '*none*))

#(define (mx-duration d)
   (if (ly:duration? d)
       (list 'obj
             (cons 'log (ly:duration-log d))
             (cons 'dots (ly:duration-dot-count d))
             (cons 'scale (ly:duration-scale d))
             (cons 'length (ly:moment-main (ly:duration-length d))))
       '*none*))

#(define (mx-or v) (if (null? v) '*none* v))

#(define (mx-location ev)
   (let ((origin (ly:event-property ev 'origin)))
     (if (ly:input-location? origin)
         (let ((loc (ly:input-file-line-char-column origin)))
           (format #f "~a:~a:~a" (car loc) (cadr loc) (cadddr loc)))
         '*none*)))

#(define mx-watched-properties
   '(instrumentName shortInstrumentName midiInstrument midiPanPosition
     instrumentTransposition clefGlyph clefPosition clefTransposition
     timeSignatureFraction))

#(define (mx-property-value v)
   (cond ((ly:pitch? v) (mx-pitch v))
         ((pair? v) (if (and (number? (car v)) (number? (cdr v)))
                        (list (car v) (cdr v))
                        (mx-markup v)))
         ((null? v) '*none*)
         (else v)))

musicxmlEventDump =
#(lambda (context)
   (let ((last-properties '())
         (first #t))
     (define (now) (ly:context-current-moment context))
     (define (base . rest)
       (append
        (list (cons 'context (ly:context-name context))
              (cons 'id (ly:context-id context))
              (cons 't (ly:moment-main (now)))
              (cons 'grace (ly:moment-grace (now))))
        rest))
     (make-engraver
      (listeners
       ((music-event engraver ev)
        (apply mx-emit
               (base
                (cons 'class (car (ly:event-property ev 'class)))
                (cons 'at (mx-location ev))
                (cons 'pitch (mx-pitch (ly:event-property ev 'pitch)))
                (cons 'duration (mx-duration (ly:event-property ev 'duration)))
                (cons 'span (mx-or (ly:event-property ev 'span-direction)))
                (cons 'articulation (mx-or (ly:event-property ev 'articulation-type)))
                (cons 'text (let ((t (ly:event-property ev 'text)))
                              (if (null? t) '*none*
                                  (if (and (string? t) (eq? (car (ly:event-property ev 'class)) 'absolute-dynamic-event))
                                      t
                                      (mx-markup t)))))
                (cons 'direction (mx-or (ly:event-property ev 'direction)))
                (cons 'xmlBarEnd (mx-or (ly:event-property ev 'xml-bar-end)))
                (cons 'xmlOffset (mx-or (ly:event-property ev 'xml-offset)))
                (cons 'figure (mx-or (ly:event-property ev 'figure)))
                (cons 'bracketStart (mx-or (ly:event-property ev 'bracket-start)))
                (cons 'bracketStop (mx-or (ly:event-property ev 'bracket-stop)))
                (cons 'tonic (mx-pitch (ly:event-property ev 'tonic)))
                (cons 'keyAlterations
                      (let ((alist (ly:event-property ev 'pitch-alist)))
                        (if (null? alist) '*none*
                            (map (lambda (entry) (* 2 (cdr entry))) alist))))
                (cons 'numerator (mx-or (ly:event-property ev 'numerator)))
                (cons 'denominator (mx-or (ly:event-property ev 'denominator)))
                (cons 'tempoUnit (mx-duration (ly:event-property ev 'tempo-unit)))
                (cons 'metronome (mx-or (ly:event-property ev 'metronome-count)))))))
      (acknowledgers
       ((tuplet-bracket-interface engraver grob source)
        (apply mx-emit (base (cons 'grob "TupletBracket")
                             (cons 'shown (if (ly:grob-property-data grob 'stencil) #t #f)))))
       ((tuplet-number-interface engraver grob source)
        (apply mx-emit (base (cons 'grob "TupletNumber")
                             (cons 'shown (if (ly:grob-property-data grob 'stencil) #t #f))))))
      ((stop-translation-timestep engraver)
       (let ((changed
              (filter-map
               (lambda (key)
                 (let ((value (ly:context-property context key)))
                   (if (equal? value (assq-ref last-properties key))
                       #f
                       (begin
                         (set! last-properties (assq-set! last-properties key value))
                         (cons key (mx-property-value value))))))
               mx-watched-properties)))
         (if first
             (set! changed
                   (append changed
                           (list (cons 'measurePosition
                                       (ly:moment-main (ly:context-property context 'measurePosition)))
                                 (cons 'measureLength
                                       (ly:moment-main (ly:context-property context 'measureLength)))))))
         (set! first #f)
         (if (pair? changed)
             (apply mx-emit (base (cons 'properties (cons 'obj changed))))))))))

#(define (musicxml-dump-header)
   (let ((get (lambda (key)
                (let ((v (ly:modules-lookup (list $defaultheader) key)))
                  (cond ((string? v) v)
                        ((pair? v) (markup->string v))
                        (else '*none*))))))
     (mx-emit (cons 'header
                    (list 'obj
                          (cons 'title (get 'title))
                          (cons 'composer (get 'composer))
                          (cons 'copyright (get 'copyright)))))))
