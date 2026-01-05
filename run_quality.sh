#!/usr/bin/env bash
set -uo pipefail

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

show_help() {
  echo -e "${BLUE}Usage:${NC} ./run_quality.sh [OPTIONS] [PATHS...]"
  echo ""
  echo -e "${YELLOW}Description:${NC}"
  echo "  Script de maintenance et de qualité pour Grub_manager."
  echo "  Gère le nettoyage, le formatage, le linting et les tests."
  echo ""
  echo -e "${YELLOW}Options:${NC}"
  echo -e "  ${GREEN}--clean${NC}       Supprime les caches (.pytest, .ruff, .mypy) et __pycache__"
  echo -e "  ${GREEN}--fix${NC}         Applique les corrections automatiques (ruff, isort, black)"
  echo -e "  ${GREEN}--lint${NC}        Vérifie le code (pydocstyle, vulture, black --check, isort --check, ruff, mypy, pylint, radon)"
  echo -e "  ${GREEN}--test${NC}        Exécute la suite de tests pytest"
  echo -e "  ${GREEN}--cov${NC}         Exécute les tests avec rapport de couverture détaillé"
  echo -e "  ${GREEN}--all${NC}         Enchaîne : clean -> fix -> lint -> test (comportement par défaut)"
  echo -e "  ${GREEN}--help, -h${NC}    Affiche cette aide"
  echo ""
  echo -e "${YELLOW}Sélection par chemins:${NC}"
  echo "  - Pour --fix/--lint : les PATHS filtrent les fichiers/dossiers analysés."
  echo "  - Pour --test/--cov : les PATHS (si fournis) sont passés à pytest pour ne lancer que cette sélection."
  echo "    Sans PATHS, pytest lance toute la suite (comportement par défaut)."
  echo ""
  echo -e "${YELLOW}Exemples:${NC}"
  echo "  ./run_quality.sh --lint          # Vérifie le code source (core, ui, main.py)"
  echo "  ./run_quality.sh --lint tests    # Vérifie spécifiquement le dossier tests"
  echo "  ./run_quality.sh --fix core      # Formate uniquement le dossier core"
  echo "  ./run_quality.sh --test          # Lance toute la suite de tests"
  echo "  ./run_quality.sh --test tests/core/theme/test_core_theme_generator.py"
  echo "                                # Lance uniquement ce fichier de tests"
  echo "  ./run_quality.sh --cov           # Voir la couverture de tests"
  echo ""
  echo -e "${BLUE}Note:${NC} Sans option, le script exécute ${GREEN}--all${NC} sur les dossiers sources."
  echo "      Le dossier ${YELLOW}tests/${NC} n'est linté que s'il est explicitement mentionné."
}

# Détection de l'environnement Python
PYTHON_BIN=""
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo -e "${RED}Erreur : Python 3 n'a pas été trouvé.${NC}"
  exit 1
fi

# Variables d'état
CLEAN=false
DO_LINT=false
DO_TEST=false
DO_COV=false
DO_FIX=false
DO_ALL=false
EXIT_CODE=0

# Indique si l'utilisateur a fourni explicitement des chemins (non-option).
# Sert notamment à ne pas passer par erreur les chemins de lint (core/ui/main.py)
# à pytest lorsque l'utilisateur lance simplement --test/--cov sans argument.
USER_PROVIDED_PATHS=false

# Chemins par défaut (exclut tests par défaut pour le linting)
DEFAULT_PATHS="core ui main.py"
PATHS=""

if [[ $# -eq 0 ]]; then
  DO_ALL=true
fi

# Extraction des options et des chemins
for arg in "$@"; do
  case "$arg" in
    --clean) CLEAN=true ;;
    --lint) DO_LINT=true ;;
    --test) DO_TEST=true ;;
    --cov) DO_COV=true ;;
    --fix) DO_FIX=true ;;
    --all) DO_ALL=true ;;
    --help|-h) show_help; exit 0 ;;
    -*) echo -e "${RED}Option inconnue : $arg${NC}"; show_help; exit 2 ;;
    *)
      USER_PROVIDED_PATHS=true
      PATHS="$PATHS $arg"
      ;;
  esac
done

# Si aucun chemin n'est spécifié, on utilise les chemins par défaut
if [[ -z "$PATHS" ]]; then
  PATHS=$DEFAULT_PATHS
fi

# Helper pour exécuter une commande et suivre son statut
run_check() {
  local label=$1
  shift
  echo -e "${BLUE}==> Exécution de $label...${NC}"
  if "$@"; then
    echo -e "${GREEN}✓ $label réussi${NC}"
    return 0
  else
    echo -e "${RED}✗ $label a échoué${NC}"
    EXIT_CODE=1
    return 1
  fi
}

clean() {
  echo -e "${YELLOW}Nettoyage des caches...${NC}"
  rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov 2>/dev/null || true
  find . -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
  find . -name "*.pyc" -delete 2>/dev/null || true
}

fix() {
  run_check "Ruff (fix)" "$PYTHON_BIN" -m ruff check $PATHS --fix
  run_check "Isort" "$PYTHON_BIN" -m isort $PATHS
  run_check "Black" "$PYTHON_BIN" -m black $PATHS
}

lint() {
  # Ordre demandé: pydocstyle -> vulture (50%) -> black -> isort -> ruff -> mypy -> pylint
  run_check "Pydocstyle" "$PYTHON_BIN" -m pydocstyle $PATHS
  run_check "Vulture" "$PYTHON_BIN" -m vulture $PATHS
  run_check "Black (check)" "$PYTHON_BIN" -m black --check $PATHS
  run_check "Isort (check)" "$PYTHON_BIN" -m isort --check-only --diff $PATHS
  run_check "Ruff" "$PYTHON_BIN" -m ruff check $PATHS
  run_check "Mypy" "$PYTHON_BIN" -m mypy $PATHS

  # Pylint avec gestion spécifique pour le dossier tests
  local tests_disables="redefined-outer-name,unused-argument,no-member,too-many-public-methods,too-many-lines,duplicate-code,import-outside-toplevel,wrong-import-order,invalid-name,too-many-positional-arguments,reimported,ungrouped-imports,useless-return,redefined-builtin,broad-exception-caught,pointless-statement,super-init-not-called,assignment-from-no-return,no-value-for-parameter,use-implicit-booleaness-not-comparison,unspecified-encoding"
  
  local non_test_paths=""
  local test_paths=""
  
  for p in $PATHS; do
    if [[ "$p" == "tests" || "$p" == "tests/"* ]]; then
      test_paths="$test_paths $p"
    else
      non_test_paths="$non_test_paths $p"
    fi
  done

  if [[ -n "$non_test_paths" ]]; then
    run_check "Pylint (qualité)" "$PYTHON_BIN" -m pylint $non_test_paths

    # Passes ciblées pour mieux voir les hotspots (doublons + patterns récurrents).
    # Elles n'ajoutent pas de nouvelles règles, elles filtrent l'output.
    # Seuil réglable via env: PYLINT_DUP_MIN_LINES (défaut: 8)
    local dup_min_lines=${PYLINT_DUP_MIN_LINES:-8}
    run_check "Pylint (doublons)" "$PYTHON_BIN" -m pylint \
      --disable=all --enable=R0801 --min-similarity-lines="$dup_min_lines" \
      $non_test_paths

    run_check "Pylint (patterns)" "$PYTHON_BIN" -m pylint \
      --disable=all \
      --enable=R0902,R0903,R0912,R0913,R0914,R0915,C0415,W0718 \
      $non_test_paths
  fi
  
  if [[ -n "$test_paths" ]]; then
    run_check "Pylint (tests)" "$PYTHON_BIN" -m pylint --disable="$tests_disables" $test_paths
  fi

  # Radon (complexité) - exécuté après pylint comme demandé.
  # Par défaut, échoue si une fonction/méthode dépasse le rang C.
  # Surcharge possible: RADON_MAX_RANK=A|B|C|D|E|F
  if [[ -n "$non_test_paths" ]]; then
    run_check "Radon (complexité)" "$PYTHON_BIN" - $non_test_paths <<'PY'
import os
import subprocess
import sys


def main() -> int:
  max_rank = os.environ.get("RADON_MAX_RANK", "C").strip().upper()
  order = "ABCDEF"
  if max_rank not in order:
    print(f"RADON_MAX_RANK invalide: {max_rank!r}", file=sys.stderr)
    return 2

  paths = sys.argv[1:]
  if not paths:
    return 0

  cmd = [sys.executable, "-m", "radon", "cc", "-j", *paths]
  try:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
  except FileNotFoundError as exc:
    print(f"Impossible d'exécuter radon: {exc}", file=sys.stderr)
    return 2

  if proc.returncode != 0:
    # Typiquement: radon non installé
    err = (proc.stderr or "").strip()
    if err:
      print(err, file=sys.stderr)
    else:
      print("Radon a échoué.", file=sys.stderr)
    return proc.returncode

  import json  # noqa: E402

  try:
    data = json.loads(proc.stdout or "{}")
  except json.JSONDecodeError as exc:
    print(f"Sortie radon invalide: {exc}", file=sys.stderr)
    return 2

  max_idx = order.index(max_rank)
  bad: list[tuple[str, str, str, int, int]] = []
  for file_path, blocks in data.items():
    for block in blocks or []:
      rank = str(block.get("rank", "")).strip().upper()
      if not rank or rank not in order:
        continue
      if order.index(rank) > max_idx:
        name = str(block.get("name", "<unknown>"))
        complexity = int(block.get("complexity", 0) or 0)
        lineno = int(block.get("lineno", 0) or 0)
        bad.append((file_path, name, rank, complexity, lineno))

  if not bad:
    print(f"Radon: OK (max rank {max_rank})")
    return 0

  print(f"Radon: complexité trop élevée (max rank {max_rank}).", file=sys.stderr)
  for file_path, name, rank, complexity, lineno in sorted(bad):
    loc = f"{file_path}:{lineno}" if lineno else file_path
    print(f"- {loc} {name} rank={rank} cc={complexity}", file=sys.stderr)
  return 1


if __name__ == "__main__":
  raise SystemExit(main())
PY
  fi
}

test_suite() {
  local pytest_paths=()
  if $USER_PROVIDED_PATHS; then
    # shellcheck disable=SC2206
    pytest_paths=($PATHS)
  fi

  if $DO_COV; then
    run_check "Pytest (coverage)" "$PYTHON_BIN" -m pytest \
      --cov=core --cov=ui --cov-report=term-missing --cov-fail-under=100 \
      "${pytest_paths[@]}"
  else
    run_check "Pytest" "$PYTHON_BIN" -m pytest "${pytest_paths[@]}"
  fi
}

# Exécution des étapes
# Toujours nettoyer en premier si on exécute une action qualité.
if $DO_ALL || $CLEAN || $DO_FIX || $DO_LINT || $DO_TEST || $DO_COV; then
  run_check "Clean" clean
fi

if $DO_ALL || $DO_FIX; then
  fix
fi

if $DO_ALL || $DO_LINT; then
  lint
fi

if $DO_ALL || $DO_TEST || $DO_COV; then
  test_suite
fi

# Résumé final
echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
  echo -e "${GREEN}=======================================${NC}"
  echo -e "${GREEN}   TOUS LES CHECKS ONT RÉUSSI ! ✨${NC}"
  echo -e "${GREEN}=======================================${NC}"
else
  echo -e "${RED}=======================================${NC}"
  echo -e "${RED}   CERTAINS CHECKS ONT ÉCHOUÉ. ❌${NC}"
  echo -e "${RED}=======================================${NC}"
fi

exit $EXIT_CODE
