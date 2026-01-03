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
  _c_cyan=$'\033[36m'
  _c_magenta=$'\033[35m'
else
  _c_reset=''
  _c_dim=''
  _c_bold=''
  _c_green=''
  _c_red=''
  _c_yellow=''
  _c_blue=''
  _c_cyan=''
  _c_magenta=''
fi

_step=0
_passed=0
_failed=0
_skipped=0
declare -a _results=()

say() {
  # shellcheck disable=SC2059
  printf "%b\n" "$*"
}

run_step() {
  local label="$1"
  shift
  _step=$((_step + 1))
  
  printf "${_c_bold}[%2d]${_c_reset} ${_c_cyan}●${_c_reset} %-50s " "$_step" "$label"
  
  set +e
  local output
  output=$("$@" 2>&1)
  local rc=$?
  set -e

  if [[ $rc -ne 0 ]]; then
    say "${_c_red}✗ FAIL${_c_reset} (code=$rc)"
    _results+=("${_c_red}✗${_c_reset} $label")
    _failed=$((_failed + 1))
    return "$rc"
  fi

  say "${_c_green}✓ PASS${_c_reset}"
  _results+=("${_c_green}✓${_c_reset} $label")
  _passed=$((_passed + 1))
}

skip_step() {
  local label="$1"
  _step=$((_step + 1))
  
  printf "${_c_bold}[%2d]${_c_reset} ${_c_cyan}●${_c_reset} %-50s " "$_step" "$label"
  say "${_c_yellow}⊘ SKIP${_c_reset}"
  _results+=("${_c_yellow}⊘${_c_reset} $label")
  _skipped=$((_skipped + 1))
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
  ./run_quality.sh --clean    # Clean caches then fix all
  ./run_quality.sh --test     # Only run tests (no fixes)

Individual phases:
  ./run_quality.sh --ruff     # Run ruff auto-fix only
  ./run_quality.sh --black    # Run black formatting only
  ./run_quality.sh --isort    # Run isort import sorting only
  ./run_quality.sh --mypy     # Run type checking only
  ./run_quality.sh --pydoc    # Run docstring validation only
  ./run_quality.sh --pylint   # Run static analysis only
  ./run_quality.sh --vulture  # Run unused code detection only

Combinations:
  ./run_quality.sh --clean --ruff          # Clean then ruff
  ./run_quality.sh --clean --test          # Clean then test
  ./run_quality.sh --clean --all           # Clean then all phases

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
  
  # Python caches - exclude .venv properly
  find "$ROOT_DIR" \! -path "$ROOT_DIR/.venv" -prune -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
  find "$ROOT_DIR" \! -path "$ROOT_DIR/.venv/*" -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '*.pyd' \) -delete 2>/dev/null || true
  
  # Test caches  
  find "$ROOT_DIR/tests" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

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
    "$ROOT_DIR"/*.egg-info \
    2>/dev/null || true
  
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
  
  if [[ "$DO_RUFF" == "1" ]]; then
    run_step "Ruff auto-fix (linting)" "$PY" -m ruff check . --fix --unsafe-fixes
  fi
  
  if [[ "$DO_ISORT" == "1" ]]; then
    run_step "isort (tri imports)" "$PY" -m isort --skip .venv "${TARGETS[@]}"
  fi
  
  if [[ "$DO_BLACK" == "1" ]]; then
    run_step "Black (formatage)" "$PY" -m black "${TARGETS[@]}"
  fi
  
  say ""
  say "${_c_bold}═══════════════════════════════════════${_c_reset}"
  say "${_c_bold}PHASE 2: VÉRIFICATION POST-FIX${_c_reset}"
  say "${_c_bold}═══════════════════════════════════════${_c_reset}"
  
  # Verify fixes worked
  if [[ "$DO_BLACK" == "1" ]]; then
    run_step "Black verification" "$PY" -m black --check "${TARGETS[@]}"
  fi
  
  if [[ "$DO_ISORT" == "1" ]]; then
    run_step "isort verification" "$PY" -m isort --check-only --skip .venv "${TARGETS[@]}"
  fi
  
  if [[ "$DO_RUFF" == "1" ]]; then
    run_step "Ruff verification" "$PY" -m ruff check .
  fi
  
  say ""
  say "${_c_bold}═══════════════════════════════════════${_c_reset}"
  say "${_c_bold}PHASE 3: ANALYSE COMPLÈTE${_c_reset}"
  say "${_c_bold}═══════════════════════════════════════${_c_reset}"
  
  if [[ "$DO_MYPY" == "1" ]]; then
    run_step "Type checking (mypy)" "$PY" -m mypy "${TARGETS[@]}"
  fi
  
  if [[ "$DO_PYDOC" == "1" ]]; then
    run_step "Docstring validation (pydocstyle)" "$PY" -m pydocstyle "${TARGETS[@]}"
  fi
  
  if [[ "$DO_PYLINT" == "1" ]]; then
    run_step "Static analysis (pylint)" "$PY" -m pylint --score=n --enable=duplicate-code "${TARGETS[@]}"
  fi
  
  if [[ "$DO_VULTURE" == "1" ]]; then
    run_step "Unused code detection (vulture)" "$PY" -m vulture "$ROOT_DIR" --min-confidence 60 --exclude ".venv,.mypy_cache,.ruff_cache,.pytest_cache"
  fi
  
  say ""
  say "${_c_bold}═══════════════════════════════════════${_c_reset}"
  say "${_c_bold}PHASE 4: TESTS${_c_reset}"
  say "${_c_bold}═══════════════════════════════════════${_c_reset}"
  
  if [[ "$DO_TESTS" == "1" ]]; then
    run_tests
  fi
}

print_summary() {
  local elapsed="${1:-0}"
  say ""
  say "${_c_bold}═══════════════════════════════════════════════════════════${_c_reset}"
  say "${_c_bold}SYNTHÈSE FINALE${_c_reset}"
  say "${_c_bold}═══════════════════════════════════════════════════════════${_c_reset}"
  say ""
  
  # Résultats détaillés
  if [[ ${#_results[@]} -gt 0 ]]; then
    for result in "${_results[@]}"; do
      say "  $result"
    done
    say ""
  fi
  
  # Statistiques
  local total=$((_passed + _failed + _skipped))
  say "${_c_bold}Statistiques:${_c_reset}"
  say "  ${_c_green}✓ Réussis${_c_reset}:    $_passed"
  
  if [[ $_failed -gt 0 ]]; then
    say "  ${_c_red}✗ Échoués${_c_reset}:     $_failed"
  fi
  
  if [[ $_skipped -gt 0 ]]; then
    say "  ${_c_yellow}⊘ Ignorés${_c_reset}:     $_skipped"
  fi
  
  say "  ${_c_bold}Total${_c_reset}:      $total"
  
  if [[ "$elapsed" != "0" ]]; then
    say ""
    say "  ${_c_cyan}⏱ Temps:${_c_reset}     ${elapsed}s"
  fi
  
  say ""
  
  # Statut final
  if [[ $_failed -eq 0 ]]; then
    say "${_c_bold}${_c_green}╔════════════════════════════════════════════════════════╗${_c_reset}"
    say "${_c_bold}${_c_green}║   ✓ QUALITY ASSURANCE RÉUSSIE                         ║${_c_reset}"
    say "${_c_bold}${_c_green}╚════════════════════════════════════════════════════════╝${_c_reset}"
  else
    say "${_c_bold}${_c_red}╔════════════════════════════════════════════════════════╗${_c_reset}"
    say "${_c_bold}${_c_red}║   ✗ QUALITY ASSURANCE ÉCHOUÉE ($_failed erreur(s))       ║${_c_reset}"
    say "${_c_bold}${_c_red}╚════════════════════════════════════════════════════════╝${_c_reset}"
    exit 1
  fi
}

DO_CLEAN=0
DO_RUFF=0
DO_BLACK=0
DO_ISORT=0
DO_MYPY=0
DO_PYDOC=0
DO_PYLINT=0
DO_VULTURE=0
DO_TESTS=0
DO_ALL=0
TEST_ONLY=0

# Default: enable all if no options specified
DEFAULT_MODE=1

for arg in "$@"; do
  case "$arg" in
    --clean)
      DO_CLEAN=1
      DEFAULT_MODE=0
      ;;
    --ruff)
      DO_RUFF=1
      DEFAULT_MODE=0
      ;;
    --black)
      DO_BLACK=1
      DEFAULT_MODE=0
      ;;
    --isort)
      DO_ISORT=1
      DEFAULT_MODE=0
      ;;
    --mypy)
      DO_MYPY=1
      DEFAULT_MODE=0
      ;;
    --pydoc)
      DO_PYDOC=1
      DEFAULT_MODE=0
      ;;
    --pylint)
      DO_PYLINT=1
      DEFAULT_MODE=0
      ;;
    --vulture)
      DO_VULTURE=1
      DEFAULT_MODE=0
      ;;
    --test)
      DO_TESTS=1
      TEST_ONLY=1
      DEFAULT_MODE=0
      ;;
    --all)
      DO_ALL=1
      DEFAULT_MODE=0
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

# If no options specified, enable everything
if [[ "$DEFAULT_MODE" == "1" ]]; then
  DO_RUFF=1
  DO_BLACK=1
  DO_ISORT=1
  DO_MYPY=1
  DO_PYDOC=1
  DO_PYLINT=1
  DO_VULTURE=1
  DO_TESTS=1
fi

# If --all flag set, enable everything (except --clean which needs explicit flag)
if [[ "$DO_ALL" == "1" ]]; then
  DO_RUFF=1
  DO_BLACK=1
  DO_ISORT=1
  DO_MYPY=1
  DO_PYDOC=1
  DO_PYLINT=1
  DO_VULTURE=1
  DO_TESTS=1
fi

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
  say "${_c_bold}${_c_cyan}Tests uniquement (pas de fixes)${_c_reset}"
  say ""
  run_tests
  print_summary
else
  start_ts=$SECONDS
  apply_all_fixes
  elapsed=$((SECONDS - start_ts))
  
  print_summary "$elapsed"
fi

say ""
