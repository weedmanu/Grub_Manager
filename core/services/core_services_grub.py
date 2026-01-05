"""Service centralisé pour accéder aux données GRUB (principe SOLID - Dependency Inversion)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from core.core_exceptions import GrubManagerError
from core.io.core_io_grub_default import read_grub_default
from core.io.core_io_grub_menu_parser import read_grub_default_choices_with_source


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

            # /etc/default/grub utilise des clés en MAJUSCULES (GRUB_*).
            # On supporte aussi d'anciens tests qui injectent des clés en minuscules.
            def _get(key_upper: str, key_legacy: str, default: str | None = None) -> str | None:
                if key_upper in config_dict:
                    return config_dict.get(key_upper)
                return config_dict.get(key_legacy, default)

            return GrubConfig(
                timeout=int(_get("GRUB_TIMEOUT", "timeout", "10") or "10"),
                default_entry=str(_get("GRUB_DEFAULT", "default", "0") or "0"),
                grub_color_normal=str(_get("GRUB_COLOR_NORMAL", "grub_color_normal", "white/black") or "white/black"),
                grub_color_highlight=str(
                    _get("GRUB_COLOR_HIGHLIGHT", "grub_color_highlight", "black/white") or "black/white"
                ),
                grub_gfxmode=str(_get("GRUB_GFXMODE", "grub_gfxmode", "auto") or "auto"),
                grub_theme=_get("GRUB_THEME", "grub_theme"),
                grub_cmdline_linux=str(_get("GRUB_CMDLINE_LINUX", "grub_cmdline_linux", "") or ""),
                grub_cmdline_linux_default=str(
                    _get("GRUB_CMDLINE_LINUX_DEFAULT", "grub_cmdline_linux_default", "") or ""
                ),
                grub_disable_recovery=str(_get("GRUB_DISABLE_RECOVERY", "grub_disable_recovery", "false") or "false"),
                grub_disable_os_prober=str(
                    _get("GRUB_DISABLE_OS_PROBER", "grub_disable_os_prober", "false") or "false"
                ),
                grub_init_tune=_get("GRUB_INIT_TUNE", "grub_init_tune"),
            )
        except (GrubManagerError, OSError, ValueError) as e:
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
                logger.warning("[GrubService] Aucune entrée trouvée dans grub.cfg, utilisation d'une entrée par défaut")
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
        except (GrubManagerError, OSError, ValueError) as e:
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
