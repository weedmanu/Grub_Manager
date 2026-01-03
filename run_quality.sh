#!/usr/bin/env bash
# Quality Assurance Script - Fixes issues automatically
# No checking, only corrections and auto-fixes

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Affichage plus lisible (couleurs uniquement si TTY et NO_COLOR non défini).
if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
  _c_reset=$'\033[0m'
  _c_dim=$'\033[2m'
  _c_bold=$'\033[1m'
  _c_green=$'\033[32m'
  _c_red=$'\033[31m'
  _c_yellow=$'\033[33m'
  _c_blue=$'\033[34m'
else
  _c_reset=''
  _c_dim=''
  _c_bold=''
  _c_green=''
  _c_red=''
  _c_yellow=''
  _c_blue=''
fi

_step=0

say() {
  # shellcheck disable=SC2059
  printf "%b\n" "$*"
}

run_step() {
  local label="$1"
  shift
  _step=$((_step + 1))
  say "${_c_bold}[${_step}]${_c_reset} ${_c_blue}FIX${_c_reset} ${label}${_c_dim}  ->${_c_reset} $*"

  set +e
  "$@"
  local rc=$?
  set -e

  if [[ $rc -ne 0 ]]; then
    say "${_c_red}FAIL${_c_reset} ${label} (code=$rc)"
    exit "$rc"
  fi

  say "${_c_green}✓${_c_reset}   ${label}"
}

PY="$ROOT_DIR/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="python3"
fi

TARGETS=("$ROOT_DIR/main.py" "$ROOT_DIR/core" "$ROOT_DIR/ui")

usage() {
  cat <<'USAGE'
Quality Assurance Script - Auto-fixes all issues

Usage:
  ./run_quality.sh            # Fix all quality issues
  ./run_quality.sh --clean    # Clean caches then fix
  ./run_quality.sh --test     # Only run tests (no fixes)
  ./run_quality.sh --clean --test

Features:
  ✓ Auto-format code (black, isort)
  ✓ Auto-fix linting issues (ruff)
  ✓ No checks, only corrections
  ✓ Comprehensive test coverage

Exit codes:
  0 = Success
  1 = Fix/test failure
  2 = Invalid arguments
USAGE
}

clean_caches() {
  say "${_c_bold}[clean]${_c_reset} Suppression des caches et fichiers temporaires"
  
  # Python caches
  find "$ROOT_DIR" -path "$ROOT_DIR/.venv" -prune -o -type d -name '__pycache__' -print0 | xargs -0 -r rm -rf || true
  find "$ROOT_DIR" -path "$ROOT_DIR/.venv" -prune -o -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '*.pyd' \) -print0 | xargs -0 -r rm -f || true

  # Tool caches
  rm -rf \
    "$ROOT_DIR/.pytest_cache" \
    "$ROOT_DIR/.mypy_cache" \
    "$ROOT_DIR/.ruff_cache" \
    "$ROOT_DIR/.coverage" \
    "$ROOT_DIR/htmlcov" \
    "$ROOT_DIR/.eggs" \
    "$ROOT_DIR/build" \
    "$ROOT_DIR/dist" \
    "$ROOT_DIR/*.egg-info" || true
  
  # Find and remove all .pyc/.pyo recursively (hors .venv)
  find "$ROOT_DIR" -path "$ROOT_DIR/.venv" -prune -o -name "*.egg-info" -type d -print0 | xargs -0 -r rm -rf || true
  
  say "${_c_green}✓${_c_reset}   Caches nettoyés"
}

run_tests() {
  local has_tests=0

  if [[ -d "$ROOT_DIR/tests" ]]; then
    has_tests=1
  fi

  if find "$ROOT_DIR" -path "$ROOT_DIR/.venv" -prune -o -type f -name 'test_*.py' -print -quit | grep -q .; then
    has_tests=1
  fi

  if [[ "$has_tests" == "0" ]]; then
    say "${_c_yellow}⊘${_c_reset}   Tests introuvables"
    return 0
  fi

  run_step "Tests unitaires (pytest)" "$PY" -m pytest tests/ -q
}

apply_all_fixes() {
  say "${_c_bold}═══════════════════════════════════════${_c_reset}"
  say "${_c_bold}PHASE 1: AUTO-FIX (Corrections automatiques)${_c_reset}"
  say "${_c_bold}═══════════════════════════════════════${_c_reset}"
  
  run_step "Ruff auto-fix (linting)" "$PY" -m ruff check . --fix --unsafe-fixes
  run_step "isort (tri imports)" "$PY" -m isort --skip .venv "${TARGETS[@]}"
  run_step "Black (formatage)" "$PY" -m black "${TARGETS[@]}"
  
  say ""
  say "${_c_bold}═══════════════════════════════════════${_c_reset}"
  say "${_c_bold}PHASE 2: VÉRIFICATION POST-FIX${_c_reset}"
  say "${_c_bold}═══════════════════════════════════════${_c_reset}"
  
  # Verify fixes worked
  run_step "Black verification" "$PY" -m black --check "${TARGETS[@]}"
  run_step "isort verification" "$PY" -m isort --check-only --skip .venv "${TARGETS[@]}"
  run_step "Ruff verification" "$PY" -m ruff check .
  
  say ""
  say "${_c_bold}═══════════════════════════════════════${_c_reset}"
  say "${_c_bold}PHASE 3: ANALYSE COMPLÈTE${_c_reset}"
  say "${_c_bold}═══════════════════════════════════════${_c_reset}"
  
  run_step "Type checking (mypy)" "$PY" -m mypy "${TARGETS[@]}"
  run_step "Docstring validation (pydocstyle)" "$PY" -m pydocstyle "${TARGETS[@]}"
  run_step "Static analysis (pylint)" "$PY" -m pylint --score=n --enable=duplicate-code "${TARGETS[@]}"
  run_step "Unused code detection (vulture)" "$PY" -m vulture "$ROOT_DIR" --min-confidence 60 --exclude ".venv,.mypy_cache,.ruff_cache,.pytest_cache"
  
  say ""
  say "${_c_bold}═══════════════════════════════════════${_c_reset}"
  say "${_c_bold}PHASE 4: TESTS${_c_reset}"
  say "${_c_bold}═══════════════════════════════════════${_c_reset}"
  
  run_tests
}

DO_CLEAN=0
TEST_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --clean)
      DO_CLEAN=1
      ;;
    --test)
      TEST_ONLY=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      say "${_c_red}✗${_c_reset}   Argument inconnu: $arg"
      usage
      exit 2
      ;;
  esac
done

say ""
say "${_c_bold}╔══════════════════════════════════════════╗${_c_reset}"
say "${_c_bold}║   QUALITY ASSURANCE - Auto-Fix Mode      ║${_c_reset}"
say "${_c_bold}╚══════════════════════════════════════════╝${_c_reset}"
say ""

if [[ "$DO_CLEAN" == "1" ]]; then
  clean_caches
  say ""
fi

if [[ "$TEST_ONLY" == "1" ]]; then
  say "${_c_bold}Tests uniquement (pas de fixes)${_c_reset}"
  say ""
  run_tests
else
  start_ts=$SECONDS
  apply_all_fixes
  elapsed=$((SECONDS - start_ts))
  
  say ""
  say "${_c_bold}╔══════════════════════════════════════════╗${_c_reset}"
  say "${_c_bold}║   ✓ QUALITY ASSURANCE TERMINÉE          ║${_c_reset}"
  say "${_c_bold}║   Temps: ${elapsed}s                              ║${_c_reset}"
  say "${_c_bold}╚══════════════════════════════════════════╝${_c_reset}"
fi

say ""
