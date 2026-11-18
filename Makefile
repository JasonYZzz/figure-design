.DEFAULT_GOAL := help
PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
SKILL := skills/figure-design
VERSION := $(shell $(PYTHON) -c "import sys; sys.path.insert(0, '$(SKILL)/scripts'); from figure_common import VERSION; print(VERSION)")
DIST ?= dist
OUT ?= build/runs

.PHONY: help setup doctor test check benchmark demo package package-private
help:
	@echo 'setup | doctor | test | check | benchmark | demo | package | package-private'
	@echo 'Override PYTHON, OUT or DIST as needed. Existing output directories/packages are never overwritten.'
setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r $(SKILL)/requirements.txt
	.venv/bin/python -m playwright install chromium
doctor:
	$(PYTHON) $(SKILL)/scripts/figure.py doctor
test:
	FIGURE_RENDER_TESTS=1 $(PYTHON) -m unittest discover -s $(SKILL)/tests -v
check:
	$(PYTHON) scripts/check_repository.py
benchmark:
	$(PYTHON) $(SKILL)/scripts/benchmark.py --out $(OUT)/benchmark
demo:
	$(PYTHON) $(SKILL)/scripts/demo.py --out $(OUT)/demo
package:
	$(PYTHON) $(SKILL)/scripts/figure.py pack --out $(DIST)/$(notdir $(SKILL))-$(VERSION).zip
package-private:
	$(PYTHON) $(SKILL)/scripts/figure.py pack --out $(DIST)/$(notdir $(SKILL))-$(VERSION)-private.zip --references $(SKILL)/assets/reference-library/images
