#!/bin/bash
# Script de nettoyage professionnel du projet Grub Manager
# Usage: ./clean_project.sh [--dry-run]

set -e

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "🔍 MODE DRY-RUN: Simulation sans suppression"
fi

echo "🧹 Nettoyage du projet Grub Manager..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Fonction pour supprimer avec confirmation
safe_remove() {
    local pattern=$1
    local description=$2
    
    echo ""
    echo "📁 $description"
    
    if [[ "$pattern" == *"-type d"* ]]; then
        # Recherche de répertoires
        local count=$(eval "find . $pattern ! -path '*/.venv/*' 2>/dev/null | wc -l")
    else
        # Recherche de fichiers
        local count=$(eval "find . $pattern ! -path '*/.venv/*' 2>/dev/null | wc -l")
    fi
    
    if [ "$count" -eq 0 ]; then
        echo "   ✓ Aucun fichier trouvé"
        return
    fi
    
    echo "   Trouvés: $count élément(s)"
    
    if [ "$DRY_RUN" = true ]; then
        echo "   [DRY-RUN] Serait supprimé"
    else
        if [[ "$pattern" == *"-type d"* ]]; then
            eval "find . $pattern ! -path '*/.venv/*' -exec rm -rf {} + 2>/dev/null || true"
        else
            eval "find . $pattern ! -path '*/.venv/*' -delete 2>/dev/null || true"
        fi
        echo "   ✓ Supprimé"
    fi
}

# 1. Caches Python
safe_remove "-type d -name '__pycache__'" "Caches Python (__pycache__)"
safe_remove "-name '*.pyc'" "Bytecode compilé (*.pyc)"
safe_remove "-name '*.pyo'" "Bytecode optimisé (*.pyo)"

# 2. Caches outils de développement
safe_remove "-type d -name '.pytest_cache'" "Cache pytest"
safe_remove "-type d -name '.ruff_cache'" "Cache Ruff"
safe_remove "-type d -name '.mypy_cache'" "Cache mypy"
safe_remove "-type d -name '.tox'" "Cache tox"

# 3. Fichiers de coverage
safe_remove "-name '.coverage'" "Fichiers coverage principal"
safe_remove "-name '.coverage.*'" "Fichiers coverage multiples"
safe_remove "-name 'coverage.json'" "Rapports coverage JSON"
safe_remove "-name 'coverage.xml'" "Rapports coverage XML"
safe_remove "-type d -name 'htmlcov'" "Rapports coverage HTML"

# 4. Benchmarks
safe_remove "-type d -name '.benchmarks'" "Dossiers benchmarks"

# 5. IDE et éditeurs
safe_remove "-name '.DS_Store'" "Fichiers macOS"
safe_remove "-name 'Thumbs.db'" "Fichiers Windows"
safe_remove "-name '*.swp'" "Fichiers Vim swap"
safe_remove "-name '*.swo'" "Fichiers Vim swap old"
safe_remove "-name '*~'" "Fichiers backup éditeurs"

# 6. Builds et distributions
safe_remove "-type d -name 'build'" "Dossiers build"
safe_remove "-type d -name 'dist'" "Dossiers distribution"
safe_remove "-type d -name '*.egg-info'" "Métadonnées egg"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Statistiques finales"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Compter les fichiers Python
PY_FILES=$(find . -name "*.py" ! -path "*/.venv/*" ! -path "*/__pycache__/*" | wc -l)
echo "   Fichiers Python: $PY_FILES"

# Compter les tests
TEST_FILES=$(find tests -name "test_*.py" 2>/dev/null | wc -l)
echo "   Fichiers de tests: $TEST_FILES"

# Taille du projet (sans .venv)
PROJECT_SIZE=$(du -sh . --exclude=.venv --exclude=.git 2>/dev/null | cut -f1)
echo "   Taille projet: $PROJECT_SIZE"

# Lignes de code Python
LOC=$(find . -name "*.py" ! -path "*/.venv/*" ! -path "*/__pycache__/*" -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}')
echo "   Lignes de code: $LOC"

echo ""
if [ "$DRY_RUN" = true ]; then
    echo "🔍 Simulation terminée (aucune modification)"
    echo "   Exécutez sans --dry-run pour appliquer"
else
    echo "✅ Nettoyage terminé avec succès"
fi
