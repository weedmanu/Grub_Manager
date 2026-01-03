"""Configuration du système de logging avec Loguru.

Fournit une configuration optimisée avec niveaux de verbosité ajustables.
En mode production, réduit la verbosité pour améliorer les performances.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

from loguru import logger

# Niveaux de logging
DEBUG: Final[str] = "DEBUG"
INFO: Final[str] = "INFO"
WARNING: Final[str] = "WARNING"
ERROR: Final[str] = "ERROR"

# Répertoire des logs
LOG_DIR: Final[Path] = Path.home() / ".config" / "grub_manager" / "logs"


def configure_logging(level: str = INFO, *, enable_file_logging: bool = True) -> None:
    """Configure le système de logging.

    Args:
        level: Niveau de logging (DEBUG, INFO, WARNING, ERROR)
        enable_file_logging: Si True, active la sortie vers fichier
    """
    # Supprimer les handlers par défaut
    logger.remove()

    # Format simplifié en production, détaillé en debug
    if level == DEBUG:
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    else:
        log_format = "<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | <level>{message}</level>"

    # Handler console
    logger.add(
        sys.stderr,
        format=log_format,
        level=level,
        colorize=True,
        backtrace=True,
        diagnose=(level == DEBUG),
    )

    # Handler fichier (optionnel)
    if enable_file_logging:
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Fichier rotatif avec compression
        logger.add(
            LOG_DIR / "grub_manager_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level=level,
            rotation="10 MB",  # Rotation à 10 MB
            retention="7 days",  # Conserver 7 jours
            compression="zip",  # Compresser les anciens logs
            encoding="utf-8",
        )

    logger.info(f"[Logging] Configuration appliquée: niveau={level}, fichier={enable_file_logging}")


def set_production_mode() -> None:
    """Configure le logging en mode production (INFO, performances optimisées)."""
    configure_logging(level=INFO, enable_file_logging=False)
    logger.info("[Logging] Mode production activé")


def set_debug_mode() -> None:
    """Configure le logging en mode debug (DEBUG, logs détaillés)."""
    configure_logging(level=DEBUG, enable_file_logging=True)
    logger.debug("[Logging] Mode debug activé")


def set_silent_mode() -> None:
    """Configure le logging en mode silencieux (WARNING uniquement)."""
    configure_logging(level=WARNING, enable_file_logging=False)
    logger.warning("[Logging] Mode silencieux activé")
