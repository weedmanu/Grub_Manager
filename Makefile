.PHONY: help h lint format typecheck deadcode test tests clean black black-check isort isort-check ruff ruff-fix mypy pydocstyle pylint pylint-quality vulture

SHELL := /bin/bash

PYTHON ?= $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else command -v python3; fi)

# Chemins à analyser/formater. Override exemple:
#   make lint PATHS=ui/ui_manager.py
#   make ruff PATHS=tests/ui
PATHS ?= core ui tests main.py

# Si PATHS est passé en ligne de commande, on l'utilise.
# Sinon, chaque outil garde son scope par défaut (souvent plus strict/rapide).
define effective_paths
$(if $(filter command line,$(origin PATHS)),$(PATHS),$(1))
endef

# pylint score threshold (optional)
PYLINT_FAIL_UNDER ?= 0

help:
	@echo "Usage: make <cible> [PATHS=...] [PYLINT_FAIL_UNDER=...]"; \
	echo ""; \
	echo "Cibles:"; \
	echo "  lint            Clean + black/isort/ruff --fix + pydocstyle + mypy + pylint(+qualité) + vulture (sans pytest)"; \
	echo "  format          black + isort + ruff --fix"; \
	echo "  black           Formate (black)"; \
	echo "  isort           Trie les imports (isort)"; \
	echo "  ruff            Lint (ruff)"; \
	echo "  ruff-fix        Lint + auto-fix (ruff --fix)"; \
	echo "  pydocstyle      Docstrings (pydocstyle)"; \
	echo "  mypy            Typage (mypy)"; \
	echo "  pylint          Lint (pylint)"; \
	echo "  pylint-quality  Lint (pylint) + seuil via PYLINT_FAIL_UNDER"; \
	echo "  vulture         Dead code (vulture --min-confidence 65)"; \
	echo "  clean           Nettoie caches et artefacts"; \
	echo "  test            pytest + coverage"; \
	echo "  tests           alias de test"; \
	echo ""; \
	echo "Variables:"; \
	echo "  PATHS=...            Cible un fichier/dossier (ex: PATHS=ui/ui_manager.py ou PATHS=tests/ui)"; \
	echo "  PYLINT_FAIL_UNDER=.. Seuil pylint (ex: 9.5)"; \
	echo ""; \
	echo "Exemples:"; \
	echo "  make lint"; \
	echo "  make lint PATHS=ui/ui_workflow_controller.py"; \
	echo "  make ruff PATHS=tests/ui"; \
	echo "  make tests PATHS=tests/ui/test_ui_manager.py"; \
	echo "  make pylint-quality PYLINT_FAIL_UNDER=9.0";

h: help

# Lint complet (sans pytest) : exécute tout puis échoue à la fin si une étape a échoué.
lint:
	@status=0; \
	$(MAKE) -s clean || status=1; \
	$(MAKE) -s black || status=1; \
	$(MAKE) -s isort || status=1; \
	$(MAKE) -s ruff-fix || status=1; \
	$(MAKE) -s pydocstyle || status=1; \
	$(MAKE) -s mypy || status=1; \
	$(MAKE) -s pylint || status=1; \
	$(MAKE) -s pylint-quality || status=1; \
	$(MAKE) -s vulture || status=1; \
	exit $$status

format:
	$(MAKE) black
	$(MAKE) isort
	$(MAKE) ruff-fix

black:
	$(PYTHON) -m black $(PATHS)

black-check:
	$(PYTHON) -m black --check $(PATHS)

isort:
	$(PYTHON) -m isort $(PATHS)

isort-check:
	$(PYTHON) -m isort --check-only $(PATHS)

ruff:
	$(PYTHON) -m ruff check $(PATHS)

ruff-fix:
	$(PYTHON) -m ruff check $(PATHS) --fix

pydocstyle:
	$(PYTHON) -m pydocstyle $(call effective_paths,core ui main.py)

mypy:
	$(PYTHON) -m mypy $(call effective_paths,core ui main.py)

pylint:
	$(PYTHON) -m pylint $(call effective_paths,core ui main.py tests)

pylint-quality:
	$(PYTHON) -m pylint $(call effective_paths,core ui main.py tests) --fail-under=$(PYLINT_FAIL_UNDER)

vulture:
	$(PYTHON) -m vulture $(call effective_paths,core ui main.py) --min-confidence 65

typecheck:
	$(MAKE) mypy

deadcode:
	$(MAKE) vulture

test:
	$(PYTHON) -m pytest $(call effective_paths,tests)

tests: test

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov coverage.xml .benchmarks
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	find . -type f -name '*~' -delete
	rm -rf build dist *.egg-info
