PYTHON ?= python3
FFMPEG ?= ffmpeg
STEM ?= Bach_BWV1004a_Leipzig_orchestral_realization

.PHONY: all score audio check normalize-native clean

all: score audio check

score:
	$(PYTHON) src/orchestrate_chaconne.py

audio: score
	$(FFMPEG) -y -hide_banner -loglevel error \
		-i build/$(STEM).wav \
		-codec:a libmp3lame -q:a 2 \
		audio/$(STEM).mp3

check:
	$(PYTHON) src/validate_outputs.py

normalize-native:
	$(PYTHON) src/normalize_mscz.py

clean:
	rm -f build/*.wav build/*.dat
