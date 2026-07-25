PYTHON ?= python3
MUSESCORE ?= mscore
STEM ?= Bach_BWV1004a_Leipzig_orchestral_realization
MASTER := score/$(STEM).musicxml
PACKAGE := score/$(STEM).mxl
RENDER_DIR := build/render

.PHONY: all score package check check-artifacts render proposal normalize-native clean

all: check package

# Compatibility alias: the score is checked, never regenerated.
score: check

package:
	$(PYTHON) src/package_mxl.py $(MASTER) $(PACKAGE)

check:
	$(PYTHON) src/validate_outputs.py --source-only

check-artifacts: package
	$(PYTHON) src/validate_outputs.py

# Review exports only. Promote them to score/ and audio/ deliberately after QA.
render: check package
	mkdir -p $(RENDER_DIR)
	"$(MUSESCORE)" -o $(RENDER_DIR)/$(STEM).mscz $(MASTER)
	"$(MUSESCORE)" -o $(RENDER_DIR)/$(STEM).pdf $(RENDER_DIR)/$(STEM).mscz
	"$(MUSESCORE)" -o $(RENDER_DIR)/$(STEM).mid $(RENDER_DIR)/$(STEM).mscz
	"$(MUSESCORE)" -o $(RENDER_DIR)/$(STEM).mp3 $(RENDER_DIR)/$(STEM).mscz

# One-shot algorithmic proposal. Output is isolated under build/proposals/.
proposal:
	$(PYTHON) src/orchestrate_chaconne.py

normalize-native:
	$(PYTHON) src/normalize_mscz.py

clean:
	rm -f build/*.wav build/*.dat
