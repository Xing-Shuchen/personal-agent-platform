.PHONY: setup validate test install-preview

PYTHON ?= python3

setup:
	$(PYTHON) -m venv .venv
	. .venv/bin/activate && pip install -e . pytest

validate:
	.venv/bin/pap validate

install-preview:
	$(PYTHON) scripts/install_agents.py

test:
	.venv/bin/python -m pytest -q
