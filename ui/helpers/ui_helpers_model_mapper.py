"""Mapper pour synchroniser le modèle de données avec les widgets de l'UI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from core.config.core_config_paths import get_grub_themes_dir
from core.system.core_system_grub_commands import GrubUiModel
from core.theme.core_theme_active_manager import ActiveThemeManager
from ui.config.ui_config_constants import GRUB_COLORS
from ui.helpers.ui_helpers_gtk import GtkHelper
from ui.tabs.ui_tabs_display import _on_terminal_mode_changed

if TYPE_CHECKING:
    from core.system.core_system_grub_commands import GrubDefaultChoice
    from ui.controllers.ui_controllers_manager import GrubConfigManager


class ModelWidgetMapper:
    """Gère la synchronisation bidirectionnelle entre GrubUiModel et les widgets GTK."""

    @staticmethod
    def _get_color_from_combos(fg_combo, bg_combo, grub_colors: list[str]) -> str:
        if not fg_combo or not bg_combo:
            return ""
        fg_idx = fg_combo.get_selected()
        bg_idx = bg_combo.get_selected()
        if not isinstance(fg_idx, int) or not isinstance(bg_idx, int):
            return ""
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
            if window.grub_terminal_dropdown is not None:
                GtkHelper.dropdown_set_value(window.grub_terminal_dropdown, model.grub_terminal)
                # Mettre à jour la visibilité des onglets thème selon le mode terminal
                _on_terminal_mode_changed(window)

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

        def _menu_id(entry: GrubDefaultChoice) -> str:
            return (getattr(entry, "menu_id", "") or "").strip()

        def _title(entry: GrubDefaultChoice) -> str:
            return (getattr(entry, "title", "") or "").lower()

        def _source(entry: GrubDefaultChoice) -> str:
            return (getattr(entry, "source", "") or "").lower()

        def _id_matches_memtest(mid: str) -> bool:
            return "memtest" in (mid or "").lower()

        def _id_matches_advanced(mid: str) -> bool:
            low = (mid or "").lower()
            return ("-advanced-" in low) or ("-recovery-" in low)

        def _collect_ids(predicate) -> set[str]:
            ids: set[str] = set()
            for entry in entries or []:
                mid = _menu_id(entry)
                if not mid:
                    continue
                if predicate(entry):
                    ids.add(mid)
            return ids

        hide_adv = getattr(window, "hide_advanced_options_check", None)
        if hide_adv is not None:
            # 1) IDs trouvés dans grub.cfg (si visibles)
            adv_ids = _collect_ids(
                lambda e: ("advanced options" in _title(e))
                or ("options avanc" in _title(e))
                or _id_matches_advanced(_menu_id(e))
            )
            # 2) Fallback: si les entrées sont déjà masquées dans grub.cfg, elles ne
            # sont plus parsables; on déduit alors la catégorie depuis hidden_entry_ids.
            hidden_adv = {mid for mid in (window.state_manager.hidden_entry_ids or set()) if _id_matches_advanced(mid)}
            any_hidden = bool((adv_ids | hidden_adv) & window.state_manager.hidden_entry_ids)
            hide_adv.set_active(any_hidden)

        hide_mem = getattr(window, "hide_memtest_check", None)
        if hide_mem is not None:
            mem_ids = _collect_ids(
                lambda e: ("memtest" in _title(e)) or ("memtest" in _source(e)) or _id_matches_memtest(_menu_id(e))
            )
            hidden_mem = {mid for mid in (window.state_manager.hidden_entry_ids or set()) if _id_matches_memtest(mid)}
            any_hidden = bool((mem_ids | hidden_mem) & window.state_manager.hidden_entry_ids)
            hide_mem.set_active(any_hidden)

    @staticmethod
    def _read_simple_config_from_controller(
        controller,
        *,
        default_bg: str,
        default_color_normal: str,
        default_color_highlight: str,
    ) -> tuple[str, str, str]:
        panels = getattr(controller, "widgets", None)
        panel = getattr(getattr(panels, "panels", None), "simple_config_panel", None)
        if panel is None:
            return default_bg, default_color_normal, default_color_highlight

        widgets = getattr(panel, "widgets", None)
        if widgets is None:
            return default_bg, default_color_normal, default_color_highlight

        bg = default_bg
        if getattr(widgets, "bg_image_entry", None) is not None:
            bg = widgets.bg_image_entry.get_text()

        color_normal = default_color_normal
        if (
            getattr(widgets, "normal_fg_combo", None) is not None
            and getattr(widgets, "normal_bg_combo", None) is not None
        ):
            color_normal = ModelWidgetMapper._get_color_from_combos(
                widgets.normal_fg_combo, widgets.normal_bg_combo, GRUB_COLORS
            )

        color_highlight = default_color_highlight
        if (
            getattr(widgets, "highlight_fg_combo", None) is not None
            and getattr(widgets, "highlight_bg_combo", None) is not None
        ):
            color_highlight = ModelWidgetMapper._get_color_from_combos(
                widgets.highlight_fg_combo,
                widgets.highlight_bg_combo,
                GRUB_COLORS,
            )

        return bg, color_normal, color_highlight

    @staticmethod
    def _read_graphics_from_ui(window: GrubConfigManager) -> tuple[str, str, str]:
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
        grub_terminal = (
            (GtkHelper.dropdown_get_value(window.grub_terminal_dropdown) or "").strip()
            if window.grub_terminal_dropdown is not None
            else ""
        )
        return gfxmode, gfxpayload, grub_terminal

    @staticmethod
    def _read_kernel_params_from_ui(window: GrubConfigManager) -> tuple[bool, bool]:
        cmdline_value = window.get_cmdline_value()
        return ("quiet" in cmdline_value), ("splash" in cmdline_value)

    @staticmethod
    def _read_theme_config_from_ui(window: GrubConfigManager) -> tuple[str, bool, str, str, str]:
        current_model = window.state_manager.state_data.model if window.state_manager.state_data else None

        grub_theme = current_model.grub_theme if current_model else ""
        theme_enabled = current_model.theme_management_enabled if current_model else True
        grub_bg = current_model.grub_background if current_model else ""
        color_normal = current_model.grub_color_normal if current_model else ""
        color_highlight = current_model.grub_color_highlight if current_model else ""

        ctrl = window.theme_config_controller
        if ctrl:
            grub_bg, color_normal, color_highlight = ModelWidgetMapper._read_simple_config_from_controller(
                ctrl,
                default_bg=grub_bg,
                default_color_normal=color_normal,
                default_color_highlight=color_highlight,
            )

        return grub_theme, theme_enabled, grub_bg, color_normal, color_highlight

    @staticmethod
    def _read_general_from_ui(window: GrubConfigManager) -> tuple[str, str, bool]:
        """Lit les paramètres généraux de l'UI."""
        default_value = window.get_default_choice()
        timeout_val = window.get_timeout_value()
        hidden_timeout = (
            bool(window.hidden_timeout_check.get_active()) if window.hidden_timeout_check is not None else False
        )
        return default_value, timeout_val, hidden_timeout

    @staticmethod
    def read_model_from_ui(window: GrubConfigManager) -> GrubUiModel:
        """Extrait les valeurs des widgets vers un GrubUiModel.

        Args:
            window: Instance de la fenêtre principale contenant les widgets.

        Returns:
            Un nouvel objet GrubUiModel avec les valeurs actuelles de l'UI.
        """
        logger.debug("[ModelWidgetMapper.read_model_from_ui] Début lecture")

        default_value, timeout_val, hidden_timeout = ModelWidgetMapper._read_general_from_ui(window)
        gfxmode, gfxpayload, grub_terminal = ModelWidgetMapper._read_graphics_from_ui(window)
        quiet, splash = ModelWidgetMapper._read_kernel_params_from_ui(window)
        theme_data = ModelWidgetMapper._read_theme_config_from_ui(window)

        disable_os_prober = (
            bool(window.disable_os_prober_check.get_active()) if window.disable_os_prober_check is not None else False
        )

        model = GrubUiModel(
            timeout=timeout_val,
            default=default_value,
            save_default=(default_value == "saved"),
            hidden_timeout=hidden_timeout,
            gfxmode=gfxmode,
            gfxpayload_linux=gfxpayload,
            grub_terminal=grub_terminal,
            disable_os_prober=disable_os_prober,
            grub_theme=theme_data[0],
            grub_background=theme_data[2],
            grub_color_normal=theme_data[3],
            grub_color_highlight=theme_data[4],
            theme_management_enabled=theme_data[1],
            quiet=quiet,
            splash=splash,
        )
        logger.success(
            f"[ModelWidgetMapper.read_model_from_ui] Modèle extrait - theme_management_enabled={theme_data[1]}"
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
