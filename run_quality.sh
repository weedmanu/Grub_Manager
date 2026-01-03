#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'EOF'
Usage: ./run_quality.sh [--clean] [--lint] [--test] [--all]

Options:
  --clean   Supprime caches (pytest/ruff/mypy/__pycache__).
  --lint    Exécute les checks CI (ruff, black --check, mypy, vulture).
  --test    Exécute pytest.
  --all     Équivaut à: --clean + auto-fix + --lint + --test.
  --help    Affiche l'aide.

Par défaut (sans option): exécute --all.
EOF
}

PYTHON_BIN=""
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
else
  PYTHON_BIN="python3"
fi

CLEAN=false
DO_LINT=false
DO_TEST=false
DO_ALL=false

if [[ $# -eq 0 ]]; then
  DO_ALL=true
fi

for arg in "$@"; do
  case "$arg" in
    --clean) CLEAN=true ;;
    --lint) DO_LINT=true ;;
    --test) DO_TEST=true ;;
    --all) DO_ALL=true ;;
    --help|-h) show_help; exit 0 ;;
    *) echo "Unknown option: $arg"; echo; show_help; exit 2 ;;
  esac
done

clean() {
  rm -rf .pytest_cache .ruff_cache .mypy_cache 2>/dev/null || true
  find . -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
  find . -name "*.pyc" -delete 2>/dev/null || true
}

autofix() {
  "$PYTHON_BIN" -m ruff check core ui main.py --fix
  "$PYTHON_BIN" -m black core ui main.py
}

lint() {
  "$PYTHON_BIN" -m ruff check core ui main.py
  "$PYTHON_BIN" -m black --check core ui main.py
  "$PYTHON_BIN" -m mypy core ui main.py
  "$PYTHON_BIN" -m vulture core ui main.py --min-confidence 65
}

test_suite() {
  "$PYTHON_BIN" -m pytest
}

if $DO_ALL; then
  clean
  autofix
  lint
  test_suite
  exit 0
fi

if $CLEAN; then
  clean
fi

if $DO_LINT; then
  lint
fi

if $DO_TEST; then
  test_suite
fi
