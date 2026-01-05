"""Utilities for CLI entry points.

This module centralizes shared runtime helpers used by `main.py`
(logging and minimal argument parsing).
"""

from __future__ import annotations

import sys

from loguru import logger


def configure_logging(*, debug: bool) -> None:
    """Configure Loguru for the whole process."""
    logger.remove()
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
    """Parse argv and extract the optional `--debug` flag.

    Returns:
        (debug_enabled, remaining_argv)
    """
    debug = False
    remaining: list[str] = []
    for arg in argv:
        if arg == "--debug":
            debug = True
        else:
            remaining.append(arg)
    return debug, remaining
