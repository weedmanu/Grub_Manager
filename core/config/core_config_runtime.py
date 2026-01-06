"""Utilities for CLI entry points.

This module centralizes shared runtime helpers used by `main.py`
(logging and minimal argument parsing).
"""

from __future__ import annotations

import sys

from loguru import logger


def configure_logging(*, debug: bool, verbose: bool = False) -> None:
    """Configure Loguru for the whole process.

    Politique:
    - Sans flag: aucun handler -> pas de logs.
    - --verbose: INFO.
    - --debug: DEBUG (+ backtrace/diagnose).
    """
    logger.remove()

    if not debug and not verbose:
        return

    logger.add(
        sys.stderr,
        level="DEBUG" if debug else "INFO",
        backtrace=debug,
        diagnose=debug,
        enqueue=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> " "<level>{level: <8}</level> " "<level>{message}</level>"
        ),
    )


def parse_debug_flag(argv: list[str]) -> tuple[bool, list[str]]:
    """Compat: conserve l'ancienne API.

    DEV: équivalent à parse_verbosity_flags(argv)[0,2].
    """
    debug, _verbose, remaining = parse_verbosity_flags(argv)
    return debug, remaining


def parse_verbosity_flags(argv: list[str]) -> tuple[bool, bool, list[str]]:
    """Parse argv et extrait `--verbose` et `--debug`.

    Returns:
        (debug_enabled, verbose_enabled, remaining_argv)
    """
    debug = False
    verbose = False
    remaining: list[str] = []
    for arg in argv:
        if arg == "--debug":
            debug = True
        elif arg == "--verbose":
            verbose = True
        else:
            remaining.append(arg)
    return debug, verbose, remaining
