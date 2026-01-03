.PHONY: lint format typecheck deadcode test

PYTHON ?= $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else command -v python3; fi)

# CI-ready single entry point
lint:
	$(PYTHON) -m ruff check core ui main.py
	$(PYTHON) -m black --check core ui main.py
	$(PYTHON) -m mypy core ui main.py
	$(PYTHON) -m vulture core ui main.py --min-confidence 65

format:
	$(PYTHON) -m ruff check core ui main.py --fix
	$(PYTHON) -m black core ui main.py

typecheck:
	$(PYTHON) -m mypy core ui main.py

deadcode:
	$(PYTHON) -m vulture core ui main.py --min-confidence 65

test:
	$(PYTHON) -m pytest
