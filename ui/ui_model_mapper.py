"""Mapper pour synchroniser le modèle de données avec les widgets de l'UI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from core.config.core_paths import get_grub_themes_dir
from core.system.core_grub_system_commands import GrubUiModel
from core.theme.core_active_theme_manager import ActiveThemeManager
from ui.ui_gtk_helpers import GtkHelper

if TYPE_CHECKING:
    from core.system.core_grub_system_commands import GrubDefaultChoice
    from ui.ui_manager import GrubConfigManager


class ModelWidgetMapper:
    """Gère la synchronisation bidirectionnelle entre GrubUiModel et les widgets GTK."""

    @staticmethod
    def apply_model_to_ui(
        window: GrubConfigManager,
        model: GrubUiModel,
        entries: list[GrubDefaultChoice],
    ) -> None:
        """Synchronise le modèle de données vers les widgets GTK4.

        Args:
            window: Instance de la fenêtre principale contenant les widgets.
            model: Le modèle de données à appliquer.
            entries: Liste des entrées GRUB disponibles.
        """
        logger.debug("[ModelWidgetMapper.apply_model_to_ui] Début synchronisation")

        window.state_manager.set_loading(True)
        try:
            # Timeout
            window.sync_timeout_choices(int(model.timeout))

            # Hidden Timeout
            if window.hidden_timeout_check is not None:
                window.hidden_timeout_check.set_active(bool(model.hidden_timeout))

            # Cmdline (quiet/splash)
            cmdline_dropdown = getattr(window, "cmdline_dropdown", None)
            if cmdline_dropdown is not None:
                if model.quiet and model.splash:
                    cmdline_dropdown.set_selected(0)  # quiet splash
                elif model.quiet:
                    cmdline_dropdown.set_selected(1)  # quiet
                elif model.splash:
                    cmdline_dropdown.set_selected(2)  # splash
                else:
                    cmdline_dropdown.set_selected(3)  # verbose

            # Graphics
            if window.gfxmode_dropdown is not None:
                GtkHelper.dropdown_set_value(window.gfxmode_dropdown, model.gfxmode)
            if window.gfxpayload_dropdown is not None:
                GtkHelper.dropdown_set_value(window.gfxpayload_dropdown, model.gfxpayload_linux)

            # OS Prober
            if window.disable_os_prober_check is not None:
                window.disable_os_prober_check.set_active(bool(model.disable_os_prober))

            # Masquage global (Advanced options / memtest)
            ModelWidgetMapper._sync_global_hiding_switches(window, entries)

            # Default choice
            window.refresh_default_choices(entries)
            window.set_default_choice(model.default)

            logger.success(f"[ModelWidgetMapper.apply_model_to_ui] Terminé ({len(entries)} entrées)")
        finally:
            window.state_manager.set_loading(False)

    @staticmethod
    def _sync_global_hiding_switches(window: GrubConfigManager, entries: list[GrubDefaultChoice]) -> None:
        """Synchronise les switches de masquage global basés sur les IDs masqués."""
        hide_adv = getattr(window, "hide_advanced_options_check", None)
        if hide_adv is not None:
            adv_ids = {
                (e.menu_id or "").strip()
                for e in (entries or [])
                if (e.menu_id or "").strip() and ("advanced options" in (e.title or "").lower())
            }
            hide_adv.set_active(bool(adv_ids) and adv_ids.issubset(window.state_manager.hidden_entry_ids))

        hide_mem = getattr(window, "hide_memtest_check", None)
        if hide_mem is not None:
            mem_ids = {
                (e.menu_id or "").strip()
                for e in (entries or [])
                if (e.menu_id or "").strip()
                and (("memtest" in (e.title or "").lower()) or ("memtest" in ((e.source or "").lower())))
            }
            hide_mem.set_active(bool(mem_ids) and mem_ids.issubset(window.state_manager.hidden_entry_ids))

    @staticmethod
    def read_model_from_ui(window: GrubConfigManager) -> GrubUiModel:
        """Extrait les valeurs des widgets vers un GrubUiModel.

        Args:
            window: Instance de la fenêtre principale contenant les widgets.

        Returns:
            Un nouvel objet GrubUiModel avec les valeurs actuelles de l'UI.
        """
        logger.debug("[ModelWidgetMapper.read_model_from_ui] Début lecture")

        default_value = window.get_default_choice()
        timeout_val = window.get_timeout_value()
        hidden_timeout = (
            bool(window.hidden_timeout_check.get_active()) if window.hidden_timeout_check is not None else False
        )

        gfxmode = (
            (GtkHelper.dropdown_get_value(window.gfxmode_dropdown) or "").strip()
            if window.gfxmode_dropdown is not None
            else ""
        )
        gfxpayload = (
            (GtkHelper.dropdown_get_value(window.gfxpayload_dropdown) or "").strip()
            if window.gfxpayload_dropdown is not None
            else ""
        )

        disable_os_prober = (
            bool(window.disable_os_prober_check.get_active()) if window.disable_os_prober_check is not None else False
        )

        # Paramètres kernel
        cmdline_value = window.get_cmdline_value()
        quiet = "quiet" in cmdline_value
        splash = "splash" in cmdline_value

        # Thème actif
        grub_theme = ModelWidgetMapper._get_active_theme_path()

        model = GrubUiModel(
            timeout=timeout_val,
            default=default_value,
            save_default=(default_value == "saved"),
            hidden_timeout=hidden_timeout,
            gfxmode=gfxmode,
            gfxpayload_linux=gfxpayload,
            disable_os_prober=disable_os_prober,
            grub_theme=grub_theme,
            quiet=quiet,
            splash=splash,
        )
        logger.success("[ModelWidgetMapper.read_model_from_ui] Modèle extrait")
        return model

    @staticmethod
    def _get_active_theme_path() -> str:
        """Récupère le chemin du fichier theme.txt du thème actif."""
        try:
            theme_manager = ActiveThemeManager()
            active_theme = theme_manager.get_active_theme()
            if active_theme and active_theme.name:
                theme_dir = get_grub_themes_dir()
                return str(theme_dir / active_theme.name / "theme.txt")
        except (OSError, RuntimeError) as e:
            logger.debug(f"[ModelWidgetMapper] Pas de thème actif: {e}")
        return ""
