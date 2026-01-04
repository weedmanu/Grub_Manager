#!/bin/bash

# Quality checks and formatting script
# Usage: ./quality.sh [command] [paths]
# Commands: clean, format, lint, test, help
# Paths: core, ui, tests (defaults to core ui main.py)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Config
PYTHON="${PYTHON:-python3}"
if [ -x .venv/bin/python ]; then
    PYTHON=.venv/bin/python
fi

PYLINT_FAIL_UNDER="${PYLINT_FAIL_UNDER:-0}"
DEFAULT_PATHS="core ui main.py"
LINT_PATHS="${DEFAULT_PATHS}"
STRICT_PATHS="core ui main.py"  # For strict checks that exclude tests
TEST_PATHS="tests"

# Parse arguments
COMMAND="${1:-help}"
shift || true

# Handle path alias
if [ -n "$*" ]; then
    case "$1" in
        core|ui|tests)
            LINT_PATHS="$1"
            ;;
        *)
            LINT_PATHS="$*"
            ;;
    esac
fi

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}===== $1 =====${NC}"
}

print_success() {
    echo -e "${GREEN}✓ SUCCESS $1${NC}"
}

print_failed() {
    echo -e "${RED}✗ FAILED $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

run_command() {
    local name="$1"
    shift
    print_header "$name"
    if "$@"; then
        print_success "$name"
        return 0
    else
        print_failed "$name"
        return 1
    fi
}

# Commands
cmd_clean() {
    print_header "clean"
    rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov coverage.xml .benchmarks
    find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name '*.pyc' -delete
    find . -type f -name '*.pyo' -delete
    find . -type f -name '*~' -delete
    rm -rf build dist *.egg-info
    print_success "clean"
}

cmd_format() {
    local status=0
    
    print_header "black"
    if $PYTHON -m black $LINT_PATHS; then
        print_success "black"
    else
        print_failed "black"
        status=1
    fi
    
    print_header "isort"
    if $PYTHON -m isort $LINT_PATHS; then
        print_success "isort"
    else
        print_failed "isort"
        status=1
    fi
    
    print_header "ruff (fix)"
    if $PYTHON -m ruff check $LINT_PATHS --fix; then
        print_success "ruff"
    else
        print_failed "ruff"
        status=1
    fi
    
    if [ $status -eq 0 ]; then
        echo ""
        print_success "format"
    else
        echo ""
        print_failed "format"
        return 1
    fi
}

cmd_lint() {
    local status=0
    
    cmd_clean
    
    print_header "black"
    if $PYTHON -m black $LINT_PATHS; then
        print_success "black"
    else
        print_failed "black"
        status=1
    fi
    
    print_header "isort"
    if $PYTHON -m isort $LINT_PATHS; then
        print_success "isort"
    else
        print_failed "isort"
        status=1
    fi
    
    print_header "ruff (fix)"
    if $PYTHON -m ruff check $LINT_PATHS --fix; then
        print_success "ruff"
    else
        print_failed "ruff"
        status=1
    fi
    
    print_header "pydocstyle"
    if $PYTHON -m pydocstyle $LINT_PATHS; then
        print_success "pydocstyle"
    else
        print_failed "pydocstyle"
        status=1
    fi
    
    print_header "mypy"
    if $PYTHON -m mypy $LINT_PATHS; then
        print_success "mypy"
    else
        print_failed "mypy"
        status=1
    fi
    
    print_header "pylint"
    if $PYTHON -m pylint $LINT_PATHS; then
        print_success "pylint"
    else
        print_failed "pylint"
        status=1
    fi
    
    print_header "pylint-quality"
    if $PYTHON -m pylint $LINT_PATHS --fail-under=$PYLINT_FAIL_UNDER; then
        print_success "pylint-quality"
    else
        print_failed "pylint-quality"
        status=1
    fi
    
    print_header "vulture"
    if $PYTHON -m vulture $LINT_PATHS --min-confidence 65; then
        print_success "vulture"
    else
        print_failed "vulture"
        status=1
    fi
    
    echo ""
    if [ $status -eq 0 ]; then
        print_success "lint"
    else
        print_failed "lint"
        return 1
    fi
}

cmd_test() {
    print_header "pytest (-vv)"
    $PYTHON -m pytest -vv tests
    print_success "tests"
}

cmd_help() {
    cat <<EOF

${BLUE}Quality control script${NC}

${YELLOW}Usage:${NC}
  ./quality.sh [command] [paths]

${YELLOW}Commands:${NC}
  clean         Clean caches and artifacts
  format        Format code (black + isort + ruff --fix)
  lint          Full lint (format + pydocstyle + mypy + pylint + vulture)
  test          Run pytest with coverage
  help          Show this help

${YELLOW}Paths:${NC}
  core          Lint only core/
  ui            Lint only ui/
  tests         Format/lint only tests/
  [default]     core ui main.py (production code)

${YELLOW}Environment:${NC}
  PYLINT_FAIL_UNDER=N  Fail if pylint score < N (default: 0)

${YELLOW}Examples:${NC}
  ./quality.sh clean
  ./quality.sh format
  ./quality.sh lint
  ./quality.sh lint core
  ./quality.sh lint ui
  ./quality.sh test
  PYLINT_FAIL_UNDER=9.0 ./quality.sh lint

EOF
}

# Main
case "$COMMAND" in
    clean)
        cmd_clean
        ;;
    format)
        cmd_format
        ;;
    lint)
        cmd_lint
        ;;
    test|tests)
        cmd_test
        ;;
    help|--help|-h)
        cmd_help
        ;;
    *)
        echo "Unknown command: $COMMAND"
        cmd_help
        exit 1
        ;;
esac
