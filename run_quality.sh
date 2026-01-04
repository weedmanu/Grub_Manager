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
  echo -e "  ${GREEN}--fix${NC}         Applique les corrections automatiques (ruff, black, isort)"
  echo -e "  ${GREEN}--lint${NC}        Vérifie le code (ruff, black --check, mypy, vulture, pydocstyle, pylint)"
  echo -e "  ${GREEN}--test${NC}        Exécute la suite de tests pytest"
  echo -e "  ${GREEN}--cov${NC}         Exécute les tests avec rapport de couverture détaillé"
  echo -e "  ${GREEN}--all${NC}         Enchaîne : clean -> fix -> lint -> test (comportement par défaut)"
  echo -e "  ${GREEN}--help, -h${NC}    Affiche cette aide"
  echo ""
  echo -e "${YELLOW}Exemples:${NC}"
  echo "  ./run_quality.sh --lint          # Vérifie tout le projet (core, ui, tests, main.py)"
  echo "  ./run_quality.sh --lint tests    # Vérifie uniquement le dossier tests"
  echo "  ./run_quality.sh --fix core      # Formate uniquement le dossier core"
  echo "  ./run_quality.sh --cov           # Voir la couverture de tests"
  echo ""
  echo -e "${BLUE}Note:${NC} Sans option, le script exécute ${GREEN}--all${NC} sur tous les dossiers."
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

# Chemins par défaut
DEFAULT_PATHS="core ui tests main.py"
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
    *) PATHS="$PATHS $arg" ;;
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
  run_check "Black" "$PYTHON_BIN" -m black $PATHS
}

lint() {
  run_check "Ruff" "$PYTHON_BIN" -m ruff check $PATHS
  run_check "Black (check)" "$PYTHON_BIN" -m black --check $PATHS
  run_check "Mypy" "$PYTHON_BIN" -m mypy $PATHS
  run_check "Vulture" "$PYTHON_BIN" -m vulture $PATHS --min-confidence 65
  run_check "Pydocstyle" "$PYTHON_BIN" -m pydocstyle $PATHS
  run_check "Pylint" "$PYTHON_BIN" -m pylint $PATHS
}

test_suite() {
  if $DO_COV; then
    run_check "Pytest (coverage)" "$PYTHON_BIN" -m pytest --cov=core --cov=ui --cov-report=term-missing
  else
    run_check "Pytest" "$PYTHON_BIN" -m pytest
  fi
}

# Exécution des étapes
if $DO_ALL || $CLEAN; then
  clean
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
