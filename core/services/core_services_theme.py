"""Service de gestion des thèmes GRUB sur le système."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from core.config.core_config_paths import GRUB_CFG_PATHS, get_all_grub_themes_dirs
from core.io.core_io_grub_default import read_grub_default
from core.models.core_models_theme import create_custom_theme

if TYPE_CHECKING:
    from core.models.core_models_theme import GrubTheme


class ThemeService:
    """Service pour gérer la collection de thèmes GRUB sur le système."""

    def __init__(self) -> None:
        """Initialise le service de thèmes."""
        logger.debug("[ThemeService] Initialisé")

    def is_theme_enabled_in_grub(self) -> bool:
        """Vérifie si un thème est configuré dans GRUB.

        Vérifie d'abord /etc/default/grub, puis le fichier grub.cfg généré.

        Returns:
            True si un thème est configuré, False sinon
        """
        # 1. Vérifier /etc/default/grub
        try:
            grub_config = read_grub_default()
            theme_value = grub_config.get("GRUB_THEME", "").strip().strip('"').strip("'")
            if theme_value:
                logger.debug(f"[ThemeService] Thème trouvé dans /etc/default/grub: {theme_value}")
                return True
        except (OSError, ValueError) as e:
            logger.warning(f"[ThemeService] Erreur lecture /etc/default/grub: {e}")

        # 2. Vérifier grub.cfg
        for grub_cfg_path in GRUB_CFG_PATHS:
            try:
                grub_cfg = Path(grub_cfg_path)
                if not grub_cfg.exists():
                    continue
                content = grub_cfg.read_text(encoding="utf-8", errors="ignore")
                for line in content.split("\n"):
                    if "set theme=" in line.lower() or "theme=" in line.lower():
                        theme_path = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if theme_path:
                            logger.debug(f"[ThemeService] Thème trouvé dans {grub_cfg_path}: {theme_path}")
                            return True
            except (OSError, PermissionError) as e:
                logger.debug(f"[ThemeService] Impossible de lire {grub_cfg_path}: {e}")

        logger.debug("[ThemeService] Aucun thème détecté")
        return False

    def scan_system_themes(self) -> dict[str, tuple[GrubTheme, Path]]:
        """Scanne les répertoires système pour trouver les thèmes valides.

        Returns:
            Dictionnaire {nom_theme: (GrubTheme, Path)}
        """
        themes: dict[str, tuple[GrubTheme, Path]] = {}

        for theme_dir in get_all_grub_themes_dirs():
            if not theme_dir.exists():
                continue

            logger.debug(f"[ThemeService] Scan de {theme_dir}")
            for item in theme_dir.iterdir():
                if item.is_dir() and (item / "theme.txt").exists():
                    theme_name = item.name
                    try:
                        theme = create_custom_theme(theme_name)
                        themes[theme_name] = (theme, item)
                        logger.debug(f"[ThemeService] Thème trouvé: {theme_name}")
                    except (OSError, ValueError) as e:
                        logger.warning(f"[ThemeService] Erreur pour {theme_name}: {e}")

        return themes

    def is_theme_custom(self, theme_path: Path) -> bool:
        """Vérifie si un thème est modifiable (custom) ou système (origine).

        Args:
            theme_path: Chemin du répertoire du thème

        Returns:
            True si le thème est modifiable, False s'il s'agit d'un thème système
        """
        theme_path_str = str(theme_path)
        # Les thèmes dans /usr/share/grub/themes sont considérés comme des thèmes système.
        return "/usr/share/grub/themes" not in theme_path_str

    def delete_theme(self, theme_path: Path) -> bool:
        """Supprime un répertoire de thème.

        Args:
            theme_path: Chemin du répertoire à supprimer

        Returns:
            True si succès, False sinon
        """
        if not self.is_theme_custom(theme_path):
            logger.error(f"[ThemeService] Refus de supprimer un thème système: {theme_path}")
            return False

        try:
            if theme_path.exists():
                shutil.rmtree(theme_path)
                logger.info(f"[ThemeService] Thème supprimé: {theme_path}")
                return True
            return False
        except (OSError, PermissionError) as e:
            logger.error(f"[ThemeService] Erreur lors de la suppression de {theme_path}: {e}")
            return False
