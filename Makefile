.PHONY: setup validate test install-preview

setup:
	python -m venv .venv
	. .venv/bin/activate && pip install -e . pytest

validate:
	pap validate

install-preview:
	python scripts/install_agents.py

test:
	pytest -q
