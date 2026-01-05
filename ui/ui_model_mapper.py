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
    def _get_color_from_combos(fg_combo, bg_combo, grub_colors: list[str]) -> str:
        if not fg_combo or not bg_combo:
            return ""
        fg_idx = fg_combo.get_selected()
        bg_idx = bg_combo.get_selected()
        if fg_idx < 0 or fg_idx >= len(grub_colors):
            return ""
        if bg_idx < 0 or bg_idx >= len(grub_colors):
            return ""

        fg = grub_colors[fg_idx]
        bg = grub_colors[bg_idx]
        return f"{fg}/{bg}"

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

            # Theme Tab Update
            if window.theme_config_controller:
                # On met à jour tout l'onglet thème (switch, config simple, etc.)
                window.theme_config_controller.load_themes()

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

        # Theme Management & Simple Config
        # Default values from current model if controller not available
        current_model = window.state_manager.state_data.model if window.state_manager.state_data else None

        # Thème actif (on le prend du modèle car il est mis à jour par la sélection dans la liste)
        grub_theme = current_model.grub_theme if current_model else ""

        theme_enabled = current_model.theme_management_enabled if current_model else True
        grub_bg = current_model.grub_background if current_model else ""
        color_normal = current_model.grub_color_normal if current_model else ""
        color_highlight = current_model.grub_color_highlight if current_model else ""

        if window.theme_config_controller:
            ctrl = window.theme_config_controller
            if ctrl.theme_switch:
                theme_enabled = ctrl.theme_switch.get_active()
                logger.info(f"[ModelWidgetMapper.read_model_from_ui] Thème management enabled (UI): {theme_enabled}")

            # Simple Config
            if ctrl.bg_image_entry:
                grub_bg = ctrl.bg_image_entry.get_text()
                logger.debug(f"[ModelWidgetMapper.read_model_from_ui] Background image: {grub_bg}")

            try:
                from ui.tabs.ui_tab_theme_config import GRUB_COLORS

                # Only update if widgets are available
                if ctrl.normal_fg_combo and ctrl.normal_bg_combo:
                    color_normal = ModelWidgetMapper._get_color_from_combos(
                        ctrl.normal_fg_combo, ctrl.normal_bg_combo, GRUB_COLORS
                    )
                    logger.debug(f"[ModelWidgetMapper.read_model_from_ui] Color normal: {color_normal}")

                if ctrl.highlight_fg_combo and ctrl.highlight_bg_combo:
                    color_highlight = ModelWidgetMapper._get_color_from_combos(
                        ctrl.highlight_fg_combo, ctrl.highlight_bg_combo, GRUB_COLORS
                    )
                    logger.debug(f"[ModelWidgetMapper.read_model_from_ui] Color highlight: {color_highlight}")
            except ImportError:
                logger.warning("Impossible d'importer GRUB_COLORS pour lire la config simple")

        model = GrubUiModel(
            timeout=timeout_val,
            default=default_value,
            save_default=(default_value == "saved"),
            hidden_timeout=hidden_timeout,
            gfxmode=gfxmode,
            gfxpayload_linux=gfxpayload,
            disable_os_prober=disable_os_prober,
            grub_theme=grub_theme,
            grub_background=grub_bg,
            grub_color_normal=color_normal,
            grub_color_highlight=color_highlight,
            theme_management_enabled=theme_enabled,
            quiet=quiet,
            splash=splash,
        )
        logger.success(
            f"[ModelWidgetMapper.read_model_from_ui] Modèle extrait - theme_management_enabled={theme_enabled}"
        )
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
