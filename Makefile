PYTHON ?= python3
FFMPEG ?= ffmpeg

.PHONY: all score audio check clean

all: score audio check

score:
	$(PYTHON) src/orchestrate_chaconne.py

audio: score
	$(FFMPEG) -y -hide_banner -loglevel error \
		-i build/Bach_BWV1004a_transparent_orchestra.wav \
		-codec:a libmp3lame -q:a 2 \
		audio/Bach_BWV1004a_transparent_orchestra.mp3

check:
	$(PYTHON) src/validate_outputs.py

clean:
	rm -f build/*.wav build/*.dat
