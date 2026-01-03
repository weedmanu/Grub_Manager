"""Façade rétro-compatible.

Le core a été découpé en modules pour respecter SOLID. On conserve ce fichier
pour ne pas casser les imports existants.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass

from loguru import logger

from ..config.core_paths import GRUB_CFG_PATH, GRUB_DEFAULT_PATH
from ..io.core_grub_default_io import (
    format_grub_default,
    parse_grub_default,
    read_grub_default,
    write_grub_default,
)
from ..io.core_grub_menu_parser import (
    GrubDefaultChoice,
    read_grub_default_choices,
    read_grub_default_choices_with_source,
)
from ..models.core_grub_ui_model import (
    GrubUiModel,
    GrubUiState,
    load_grub_ui_state,
    save_grub_ui_state,
)

__all__ = [
    "GRUB_CFG_PATH",
    "GRUB_DEFAULT_PATH",
    "CommandResult",
    "GrubDefaultChoice",
    "GrubUiModel",
    "GrubUiState",
    "format_grub_default",
    "load_grub_ui_state",
    "parse_grub_default",
    "read_grub_default",
    "read_grub_default_choices",
    "read_grub_default_choices_with_source",
    "run_update_grub",
    "save_grub_ui_state",
    "write_grub_default",
]


@dataclass(frozen=True)
class CommandResult:
    """Résultat d'une commande système lancée par le core."""

    returncode: int
    stdout: str
    stderr: str


def run_update_grub() -> CommandResult:
    """Execute `update-grub` and return stdout/stderr + return code.

    DEV: Wrapper for executing the GRUB update system command.
    Note: Under pkexec, environment is often cleared and PATH may not
    contain /usr/sbin (where update-grub is often located). Absolute
    path is resolved with expanded PATH.
    """
    logger.info("[run_update_grub] Début")

    base_path = os.environ.get("PATH", "")
    search_path = f"{base_path}:/usr/sbin:/sbin:/usr/bin:/bin"
    cmd = shutil.which("update-grub", path=search_path) or "update-grub"

    logger.debug(f"[run_update_grub] Commande trouvée: {cmd}")
    logger.info(f"[run_update_grub] Exécution: {cmd}")
    try:
        res = subprocess.run([cmd], capture_output=True, text=True, check=False)
        logger.debug(
            f"[run_update_grub] Résultat: returncode={res.returncode}, "
            f"stdout_len={len(res.stdout)}, stderr_len={len(res.stderr)}"
        )
        if res.returncode == 0:
            logger.success("[run_update_grub] Succès")
        else:
            logger.error(f"[run_update_grub] ERREUR: returncode={res.returncode}")
            if res.stderr:
                logger.error(f"[run_update_grub] Stderr: {res.stderr[:200]}")
        return CommandResult(res.returncode, res.stdout, res.stderr)
    except FileNotFoundError as e:
        logger.error(f"[run_update_grub] ERREUR: Commande 'update-grub' introuvable - {e}")
        return CommandResult(
            127,
            "",
            "Commande 'update-grub' introuvable. Sur pkexec, le PATH peut être restreint. "
            "Vérifiez que le paquet grub est installé, ou exécutez update-grub manuellement en root.",
        )
