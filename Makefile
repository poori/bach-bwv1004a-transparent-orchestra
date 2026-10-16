PYTHON ?= python3
LILYPOND ?= lilypond
MUSESCORE ?= mscore
STEM ?= Bach_BWV1004a_Leipzig_orchestral_realization
MUSICXML := score/$(STEM).musicxml
PACKAGE := score/$(STEM).mxl
# The MusicXML master from before the LilyPond port, for `make compare`.
BASELINE ?= 7730806

.PHONY: all musicxml score engrave package check test check-artifacts compare render proposal normalize-native clean

# The LilyPond files in ly/ are the source of truth. Everything else is derived.
all: check package engrave

# Regenerate the MusicXML derivative from ly/ (used by validation and MuseScore).
musicxml:
	$(PYTHON) src/ly_to_musicxml.py --lilypond "$(LILYPOND)"

# Compatibility alias.
score: musicxml

# Conductor score PDF and MIDI, engraved by LilyPond. Warnings fail the build.
engrave:
	$(PYTHON) src/engrave_score.py --lilypond "$(LILYPOND)"

package: musicxml
	$(PYTHON) src/package_mxl.py $(MUSICXML) $(PACKAGE)

check: musicxml
	$(PYTHON) src/validate_outputs.py --source-only

test:
	$(PYTHON) -m unittest discover -s src -p 'test_*.py'

check-artifacts: package
	$(PYTHON) src/validate_outputs.py

# Musical diff of the generated MusicXML against an earlier commit's MusicXML.
# Informational: lists every difference and never fails the build.
compare: musicxml
	git show $(BASELINE):$(MUSICXML) > build/baseline.musicxml
	-$(PYTHON) src/compare_musicxml.py build/baseline.musicxml $(MUSICXML)

# MuseScore review exports from the generated MusicXML. Promote them to score/
# and audio/ deliberately after QA.
render: check package
	$(PYTHON) src/render_score.py --mscore "$(MUSESCORE)" --stem "$(STEM)"

# One-shot algorithmic proposal. Output is isolated under build/proposals/.
proposal:
	$(PYTHON) src/orchestrate_chaconne.py

normalize-native:
	$(PYTHON) src/normalize_mscz.py

clean:
	rm -f build/*.wav build/*.dat build/baseline.musicxml
	rm -rf build/lilypond build/musicxml-export
