"""Vérification de synchronisation entre /etc/default/grub et /boot/grub/grub.cfg."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from ..config.core_paths import GRUB_CFG_PATH, GRUB_DEFAULT_PATH


@dataclass
class SyncStatus:
    """État de synchronisation entre les fichiers GRUB."""

    in_sync: bool
    grub_default_exists: bool
    grub_cfg_exists: bool
    grub_default_mtime: float
    grub_cfg_mtime: float
    message: str


def check_grub_sync() -> SyncStatus:
    """Vérifie si /etc/default/grub et /boot/grub/grub.cfg sont synchronisés.

    Compare les timestamps de modification pour détecter si grub.cfg doit être
    régénéré avec update-grub.

    Returns:
        SyncStatus avec les détails de synchronisation
    """
    grub_default_path = Path(GRUB_DEFAULT_PATH)
    grub_cfg_path = Path(GRUB_CFG_PATH)

    logger.debug("[check_grub_sync] Vérification de la synchronisation GRUB")

    # Vérifier existence des fichiers
    grub_default_exists = grub_default_path.exists()
    grub_cfg_exists = grub_cfg_path.exists()

    if not grub_default_exists:
        logger.warning(f"[check_grub_sync] {GRUB_DEFAULT_PATH} n'existe pas")
        return SyncStatus(
            in_sync=False,
            grub_default_exists=False,
            grub_cfg_exists=grub_cfg_exists,
            grub_default_mtime=0,
            grub_cfg_mtime=0,
            message=f"{GRUB_DEFAULT_PATH} introuvable",
        )

    if not grub_cfg_exists:
        logger.warning(f"[check_grub_sync] {GRUB_CFG_PATH} n'existe pas")
        return SyncStatus(
            in_sync=False,
            grub_default_exists=True,
            grub_cfg_exists=False,
            grub_default_mtime=0,
            grub_cfg_mtime=0,
            message=f"{GRUB_CFG_PATH} introuvable - Exécutez update-grub",
        )

    # Comparer les timestamps
    try:
        grub_default_mtime = grub_default_path.stat().st_mtime
        grub_cfg_mtime = grub_cfg_path.stat().st_mtime

        # grub.cfg doit être plus récent que /etc/default/grub
        time_diff = grub_cfg_mtime - grub_default_mtime

        logger.debug(
            f"[check_grub_sync] Timestamps: "
            f"grub_default={grub_default_mtime}, grub_cfg={grub_cfg_mtime}, "
            f"diff={time_diff:.1f}s"
        )

        if time_diff < 0:
            # grub.cfg est plus ancien que /etc/default/grub
            logger.warning(
                f"[check_grub_sync] DÉSYNCHRONISÉ: {GRUB_CFG_PATH} est plus ancien "
                f"que {GRUB_DEFAULT_PATH} de {abs(time_diff):.1f} secondes"
            )
            return SyncStatus(
                in_sync=False,
                grub_default_exists=True,
                grub_cfg_exists=True,
                grub_default_mtime=grub_default_mtime,
                grub_cfg_mtime=grub_cfg_mtime,
                message=f"Configuration GRUB désynchronisée ({abs(time_diff):.0f}s). Exécutez update-grub.",
            )

        logger.success(
            f"[check_grub_sync] SYNCHRONISÉ: {GRUB_CFG_PATH} est à jour " f"({time_diff:.1f}s plus récent)"
        )
        return SyncStatus(
            in_sync=True,
            grub_default_exists=True,
            grub_cfg_exists=True,
            grub_default_mtime=grub_default_mtime,
            grub_cfg_mtime=grub_cfg_mtime,
            message="Configuration GRUB synchronisée",
        )

    except OSError as e:
        logger.error(f"[check_grub_sync] Erreur lors de la lecture des timestamps: {e}")
        return SyncStatus(
            in_sync=False,
            grub_default_exists=grub_default_exists,
            grub_cfg_exists=grub_cfg_exists,
            grub_default_mtime=0,
            grub_cfg_mtime=0,
            message=f"Erreur de vérification: {e}",
        )
