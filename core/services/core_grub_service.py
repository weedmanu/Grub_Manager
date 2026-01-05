"""Service centralisé pour accéder aux données GRUB (principe SOLID - Dependency Inversion)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from core.io.core_grub_default_io import read_grub_default
from core.io.core_grub_menu_parser import read_grub_default_choices_with_source


def get_simulated_os_prober_entries() -> list[object]:
    """Retourne des entrées de menu GRUB.

    Compatibilité: des tests historiques patchent ce symbole.
    Implémentation actuelle: on lit les entrées réelles depuis grub.cfg.

    Returns:
        Liste d'objets (dict-like ou objets avec attributs `title`/`id`).
    """
    choices, _ = read_grub_default_choices_with_source()
    if not choices:
        return []
    # On renvoie des dicts pour rester proche de l'API historique.
    return [{"title": c.title, "id": c.id} for c in choices]


@dataclass
class GrubConfig:  # pylint: disable=too-many-instance-attributes
    """Configuration GRUB lue depuis /etc/default/grub."""

    timeout: int = 10
    default_entry: str = "0"
    grub_color_normal: str = "white/black"
    grub_color_highlight: str = "black/white"
    grub_gfxmode: str = "auto"
    grub_theme: str | None = None
    grub_cmdline_linux: str = ""
    grub_cmdline_linux_default: str = ""
    grub_disable_recovery: str = "false"
    grub_disable_os_prober: str = "false"
    grub_init_tune: str | None = None


@dataclass
class MenuEntry:
    """Entrée du menu GRUB."""

    title: str
    id: str = ""
    is_submenu: bool = False


class GrubService:
    """Service pour accéder aux données GRUB de manière abstraite."""

    @staticmethod
    def read_current_config() -> GrubConfig:
        """Lit la configuration GRUB actuelle depuis /etc/default/grub.

        Returns:
            GrubConfig: Configuration actuelle
        """
        try:
            config_dict = read_grub_default()
            return GrubConfig(
                timeout=int(config_dict.get("timeout", 10)),
                default_entry=config_dict.get("default", "0"),
                grub_color_normal=config_dict.get("grub_color_normal", "white/black"),
                grub_color_highlight=config_dict.get("grub_color_highlight", "black/white"),
                grub_gfxmode=config_dict.get("grub_gfxmode", "auto"),
                grub_theme=config_dict.get("grub_theme"),
                grub_cmdline_linux=config_dict.get("grub_cmdline_linux", ""),
                grub_cmdline_linux_default=config_dict.get("grub_cmdline_linux_default", ""),
                grub_disable_recovery=config_dict.get("grub_disable_recovery", "false"),
                grub_disable_os_prober=config_dict.get("grub_disable_os_prober", "false"),
                grub_init_tune=config_dict.get("grub_init_tune"),
            )
        except (OSError, ValueError) as e:
            logger.error(f"[GrubService] Erreur lors de la lecture config: {e}")
            return GrubConfig()

    @staticmethod
    def get_menu_entries() -> list[MenuEntry]:
        """Récupère les entrées du menu GRUB réelles.

        Returns:
            list[MenuEntry]: Liste des entrées du menu
        """
        try:
            raw_entries = get_simulated_os_prober_entries()
            if not raw_entries:
                logger.warning(
                    "[GrubService] Aucune entrée trouvée dans grub.cfg, utilisation d'une entrée par défaut"
                )
                return [MenuEntry(title="Ubuntu", id="gnulinux")]

            entries: list[MenuEntry] = []
            for item in raw_entries:
                if isinstance(item, dict):
                    title = str(item.get("title", "") or "")
                    entry_id = str(item.get("id", "") or "")
                else:
                    title = str(getattr(item, "title", "") or "")
                    entry_id = str(getattr(item, "id", "") or "")

                if title:
                    entries.append(MenuEntry(title=title, id=entry_id))

            return entries or [MenuEntry(title="Ubuntu", id="gnulinux")]
        except (OSError, ValueError) as e:
            logger.error(f"[GrubService] Erreur lors de la lecture des entrées: {e}")
            return [MenuEntry(title="Ubuntu", id="gnulinux")]

    @staticmethod
    def get_theme_name(theme_path: str | None) -> str:
        """Extrait le nom du thème depuis son chemin.

        Args:
            theme_path: Chemin du thème

        Returns:
            str: Nom du thème ou description
        """
        if not theme_path:
            return "05_debian_theme (par défaut)"
        return Path(theme_path).name or theme_path
