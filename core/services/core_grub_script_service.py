"""Service de gestion des scripts GRUB.

Centralise la logique métier de scan et manipulation des scripts /etc/grub.d/.
Séparation claire entre UI et logique métier (SOLID principles).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from loguru import logger

from core.core_exceptions import GrubCommandError, GrubScriptNotFoundError

# Constantes
GRUB_SCRIPT_DIR: Final[Path] = Path("/etc/grub.d")
THEME_SCRIPT_PATTERN: Final[str] = "*theme*"
EXECUTABLE_PERMISSION: Final[int] = 0o111


@dataclass
class GrubScript:
    """Représente un script GRUB détecté."""

    name: str
    path: Path
    is_executable: bool

    def __str__(self) -> str:
        """Représentation textuelle."""
        status = "actif" if self.is_executable else "inactif"
        return f"{self.name} ({status})"


class GrubScriptService:
    """Service de gestion des scripts GRUB."""

    def __init__(self, script_dir: Path | None = None) -> None:
        """Initialise le service.

        Args:
            script_dir: Répertoire des scripts (défaut: /etc/grub.d)
        """
        self.script_dir = script_dir or GRUB_SCRIPT_DIR
        logger.debug(f"[GrubScriptService] Initialisé avec dir: {self.script_dir}")

    def scan_theme_scripts(self) -> list[GrubScript]:
        """Scanne /etc/grub.d/ pour détecter les scripts de thème.

        Returns:
            Liste des scripts trouvés
        """
        logger.debug(f"[GrubScriptService] Scan de {self.script_dir}")

        if not self.script_dir.exists():
            logger.warning(f"[GrubScriptService] Répertoire inexistant: {self.script_dir}")
            return []

        scripts: list[GrubScript] = []

        for script_path in self.script_dir.glob(THEME_SCRIPT_PATTERN):
            if not script_path.is_file():
                continue

            is_exec = bool(script_path.stat().st_mode & EXECUTABLE_PERMISSION)

            script = GrubScript(
                name=script_path.name,
                path=script_path,
                is_executable=is_exec,
            )

            scripts.append(script)
            logger.debug(f"[GrubScriptService] Trouvé: {script}")

        logger.info(f"[GrubScriptService] {len(scripts)} script(s) de thème trouvé(s)")
        return scripts

    def make_executable(self, script_path: Path) -> bool:
        """Rend un script exécutable via chmod +x.

        Args:
            script_path: Chemin du script à activer

        Returns:
            True si succès, False sinon
        """
        try:
            logger.info(f"[GrubScriptService] Activation de {script_path}")

            subprocess.run(
                ["chmod", "+x", str(script_path)],
                capture_output=True,
                text=True,
                check=True,
            )

            logger.success(f"[GrubScriptService] Script activé: {script_path.name}")
            return True

        except subprocess.CalledProcessError as e:
            error_msg = f"Échec chmod +x sur {script_path.name}: {e.stderr}"
            logger.error(f"[GrubScriptService] {error_msg}")
            raise GrubCommandError(error_msg, command="chmod +x", returncode=e.returncode, stderr=e.stderr) from e

        except PermissionError as e:
            error_msg = f"Permission refusée pour {script_path}: {e}"
            logger.error(f"[GrubScriptService] {error_msg}")
            raise

        except FileNotFoundError as e:
            logger.error(f"[GrubScriptService] Script introuvable: {script_path}")
            raise GrubScriptNotFoundError(f"Script introuvable: {script_path}") from e

    def make_non_executable(self, script_path: Path) -> bool:
        """Rend un script non-exécutable via chmod -x.

        Args:
            script_path: Chemin du script à désactiver

        Returns:
            True si succès, False sinon
        """
        try:
            logger.info(f"[GrubScriptService] Désactivation de {script_path}")

            subprocess.run(
                ["chmod", "-x", str(script_path)],
                capture_output=True,
                text=True,
                check=True,
            )

            logger.success(f"[GrubScriptService] Script désactivé: {script_path.name}")
            return True

        except subprocess.CalledProcessError as e:
            error_msg = f"Échec chmod -x sur {script_path.name}: {e.stderr}"
            logger.error(f"[GrubScriptService] {error_msg}")
            raise GrubCommandError(error_msg, command="chmod -x", returncode=e.returncode, stderr=e.stderr) from e

        except PermissionError as e:
            error_msg = f"Permission refusée pour {script_path}: {e}"
            logger.error(f"[GrubScriptService] {error_msg}")
            raise

        except FileNotFoundError as e:
            logger.error(f"[GrubScriptService] Script introuvable: {script_path}")
            raise GrubScriptNotFoundError(f"Script introuvable: {script_path}") from e

    def is_executable(self, script_path: Path) -> bool:
        """Vérifie si un script est exécutable.

        Args:
            script_path: Chemin du script

        Returns:
            True si exécutable
        """
        if not script_path.exists():
            return False

        return bool(script_path.stat().st_mode & EXECUTABLE_PERMISSION)
