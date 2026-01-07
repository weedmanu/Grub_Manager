"""Onglet de configuration du thème GRUB."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Any

from gi.repository import Gtk
from loguru import logger

from core.models.core_models_grub_ui import GrubUiModel
from core.models.core_models_theme import GrubTheme
from core.services.core_services_grub_script import GrubScriptService
from core.services.core_services_theme import ThemeService
from core.theme.core_theme_active_manager import ActiveThemeManager
from ui.builders.ui_builders_widgets import (
    box_append_section_grid,
    create_info_box,
    create_main_box,
    create_tab_grid_layout,
    create_two_column_layout,
)
from ui.components.ui_components_theme_config_actions import ThemeConfigCallbacks, build_theme_config_right_column
from ui.components.ui_components_theme_scripts_list import ThemeScriptsList
from ui.components.ui_components_theme_simple_config import ThemeSimpleConfigPanel
from ui.helpers.ui_helpers_gtk import GtkHelper
from ui.tabs.theme_config import ui_tabs_theme_config_handlers as handlers


@dataclass(slots=True)
class _GrubScriptsDynamicNotes:
    bg_note: Gtk.Widget
    normal_note: Gtk.Widget
    highlight_note: Gtk.Widget
    grub_colors_note: Gtk.Widget


HORIZONTAL = Gtk.Orientation.HORIZONTAL
VERTICAL = Gtk.Orientation.VERTICAL


@dataclass(slots=True)
class _TabThemeConfigServices:
    theme_manager: ActiveThemeManager = field(default_factory=ActiveThemeManager)
    script_service: GrubScriptService = field(default_factory=GrubScriptService)
    theme_service: ThemeService = field(default_factory=ThemeService)


@dataclass(slots=True)
class _TabThemeConfigData:
    current_theme: GrubTheme | None = None
    available_themes: dict[str, GrubTheme] = field(default_factory=dict)
    theme_paths: dict[str, Path] = field(default_factory=dict)
    system_active_theme_path: str | None = None


@dataclass(slots=True)
class _TabThemeConfigPanels:
    theme_list_box: Gtk.ListBox | None = None
    current_script: Any = None
    simple_config_panel: ThemeSimpleConfigPanel | None = None
    scripts_list: ThemeScriptsList | None = None


@dataclass(slots=True)
class _TabThemeConfigActions:
    preview_btn: Gtk.Button | None = None
    activate_theme_btn: Gtk.Button | None = None
    deactivate_theme_btn: Gtk.Button | None = None
    edit_btn: Gtk.Button | None = None
    delete_btn: Gtk.Button | None = None


@dataclass(slots=True)
class _TabThemeConfigWidgets:
    panels: _TabThemeConfigPanels = field(default_factory=_TabThemeConfigPanels)
    actions: _TabThemeConfigActions = field(default_factory=_TabThemeConfigActions)
    # Les conteneurs de sections ne sont plus nécessaires depuis la scission en 2 onglets.


class TabThemeConfig:
    """Onglet pour sélectionner et configurer le thème GRUB."""

    def __init__(self, state_manager: Any, window: Gtk.Window | None = None) -> None:
        """Initialise l'onglet de configuration de thème.

        Args:
            state_manager: Gestionnaire d'état global.
            window: Fenêtre parente (optionnel).
        """
        self.state_manager = state_manager
        self.parent_window: Gtk.Window | None = window
        self._updating_ui: bool = False

        # Référence conservée sur la fenêtre du générateur interactif.
        self._interactive_theme_generator_window: Gtk.Window | None = None

        self.services = _TabThemeConfigServices()
        self.data = _TabThemeConfigData()
        self.widgets = _TabThemeConfigWidgets()

        logger.debug("[TabThemeConfig.__init__] Onglet initialisé")

    def mark_dirty(self) -> None:
        """Marque l'état comme modifié."""
        parent_mark_dirty = getattr(self.parent_window, "_mark_dirty", None)
        if callable(parent_mark_dirty):
            parent_mark_dirty()  # pylint: disable=not-callable
            return

        save_btn = getattr(self.parent_window, "save_btn", None)
        reload_btn = getattr(self.parent_window, "reload_btn", None)
        if save_btn and reload_btn:
            self.state_manager.mark_dirty(save_btn, reload_btn)

    def set_interactive_theme_generator_window(self, window: Gtk.Window) -> None:
        """Conserve une référence Python à la fenêtre du générateur."""
        self._interactive_theme_generator_window = window

    def clear_interactive_theme_generator_window(self) -> None:
        """Supprime la référence au générateur, si présente."""
        try:
            delattr(self, "_interactive_theme_generator_window")
        except AttributeError:
            pass

    def build(self) -> Gtk.Box:
        """Construit l'onglet "Thèmes".

        DEV: Conservé pour compat rétro (anciens tests/imports). L'UI principale
        utilise désormais deux onglets: `build_theme_tab()` et `build_grub_scripts_tab()`.
        """
        return self.build_theme_tab()

    def build_theme_tab(self) -> Gtk.Box:
        """Construit l'onglet de sélection des thèmes."""
        main_box = create_main_box(spacing=12, margin=12)
        self._build_header(main_box, title="Thèmes", subtitle="Sélection et aperçu via theme.txt.")

        # Proportions homogènes gauche/droite (50/50) comme Général/Affichage.
        _container, left_section, right_section = create_two_column_layout(main_box, spacing=12)

        self._build_left_column(left_section)
        self._build_right_column(right_section)

        self.load_themes()
        return main_box

    def build_grub_scripts_tab(self) -> Gtk.Box:
        """Construit l'onglet "Apparence" (configuration simple + scripts)."""
        # UI compacte: comme les onglets Général/Affichage (objectif: tenir en 700px sans scroll global).
        main_box = create_main_box(spacing=8, margin=12)
        self._build_header(
            main_box,
            title="Apparence",
            subtitle="Configuration du fond d'écran, des couleurs du menu et scripts de personnalisation.",
        )

        # Layout "comme Général/Affichage": grille 2 colonnes avec notes en face.
        # - Ligne 0: Image de fond (gauche) + note (droite)
        # - Ligne 1: Couleurs (gauche) + note (droite)
        # - Ligne 2: Scripts (gauche) + note (droite)
        main_grid = create_tab_grid_layout(main_box)
        main_grid.set_row_spacing(26)

        simple_panel = self._ensure_simple_panel()
        if simple_panel is None:
            return main_box

        bg_note = self._attach_background_row(main_grid, simple_panel)
        normal_note, highlight_note = self._attach_colors_row(main_grid, simple_panel)
        grub_colors_note = self._attach_scripts_row(main_grid)
        notes = _GrubScriptsDynamicNotes(
            bg_note=bg_note,
            normal_note=normal_note,
            highlight_note=highlight_note,
            grub_colors_note=grub_colors_note,
        )
        self._wire_grub_scripts_dynamic_notes(simple_panel=simple_panel, notes=notes)

        self.load_themes()
        return main_box

    def _ensure_simple_panel(self) -> ThemeSimpleConfigPanel | None:
        self._build_simple_config_column(Gtk.Box())
        return self.widgets.panels.simple_config_panel

    def _apply_note_layout(self, note: Gtk.Widget) -> None:
        note.set_hexpand(False)
        note.set_vexpand(False)
        note.set_valign(Gtk.Align.START)

    def _attach_background_row(self, main_grid: Gtk.Grid, simple_panel: ThemeSimpleConfigPanel) -> Gtk.Widget:
        bg_frame = Gtk.Frame()
        bg_frame.add_css_class("titled-frame")
        bg_frame.add_css_class("blue-frame")
        bg_frame.set_hexpand(True)
        bg_frame.set_vexpand(False)
        bg_frame.set_valign(Gtk.Align.START)
        bg_frame.set_child(simple_panel.build_background_block())

        bg_note = create_info_box("Image de fond:", "Définit GRUB_BACKGROUND.", css_class="info-box compact-card")
        self._apply_note_layout(bg_note)

        main_grid.attach(bg_frame, 0, 0, 1, 1)
        main_grid.attach(bg_note, 1, 0, 1, 1)
        return bg_note

    def _attach_colors_row(
        self, main_grid: Gtk.Grid, simple_panel: ThemeSimpleConfigPanel
    ) -> tuple[Gtk.Widget, Gtk.Widget]:
        colors_frame = Gtk.Frame()
        colors_frame.add_css_class("titled-frame")
        colors_frame.add_css_class("green-frame")
        colors_frame.set_hexpand(True)
        colors_frame.set_vexpand(False)
        colors_frame.set_valign(Gtk.Align.START)
        colors_frame.set_child(simple_panel.build_colors_block())

        colors_notes = Gtk.Box(orientation=VERTICAL, spacing=6)
        colors_notes.set_hexpand(True)
        colors_notes.set_vexpand(False)
        colors_notes.set_valign(Gtk.Align.START)

        normal_note = create_info_box(
            "Entrée normale:",
            "Définit GRUB_COLOR_NORMAL.",
            css_class="success-box compact-card",
        )
        self._apply_note_layout(normal_note)
        colors_notes.append(normal_note)

        highlight_note = create_info_box(
            "Entrée sélectionnée:",
            "Définit GRUB_COLOR_HIGHLIGHT.",
            css_class="success-box compact-card",
        )
        self._apply_note_layout(highlight_note)
        colors_notes.append(highlight_note)

        main_grid.attach(colors_frame, 0, 1, 1, 1)
        main_grid.attach(colors_notes, 1, 1, 1, 1)
        return normal_note, highlight_note

    def _attach_scripts_row(self, main_grid: Gtk.Grid) -> Gtk.Widget:
        scripts_container = Gtk.Box(orientation=VERTICAL, spacing=8)
        scripts_container.set_hexpand(True)
        scripts_container.set_vexpand(True)
        self._build_scripts_column(scripts_container)

        scripts_frame = Gtk.Frame()
        scripts_frame.add_css_class("titled-frame")
        scripts_frame.add_css_class("orange-frame")
        scripts_frame.set_hexpand(True)
        scripts_frame.set_vexpand(True)
        scripts_frame.set_valign(Gtk.Align.START)
        scripts_frame.set_child(scripts_container)

        scripts_notes = Gtk.Box(orientation=VERTICAL, spacing=6)
        scripts_notes.set_hexpand(True)
        scripts_notes.set_vexpand(False)
        scripts_notes.set_valign(Gtk.Align.START)

        grub_colors_note = create_info_box(
            "Scripts impactant l'apparence:",
            "Chargement…",
            css_class="warning-box compact-card",
        )
        self._apply_note_layout(grub_colors_note)
        scripts_notes.append(grub_colors_note)

        main_grid.attach(scripts_frame, 0, 2, 1, 1)
        main_grid.attach(scripts_notes, 1, 2, 1, 1)
        return grub_colors_note

    def _bg_note_text(self, simple_panel: ThemeSimpleConfigPanel) -> str:
        entry = simple_panel.widgets.bg_image_entry
        path = entry.get_text().strip() if entry is not None else ""
        if not path:
            return "GRUB_BACKGROUND vide : aucune image de fond (menu sans wallpaper)."
        return f'GRUB_BACKGROUND="{path}" : utilise cette image comme fond du menu GRUB.'

    def _color_pair(self, fg_combo: Gtk.DropDown | None, bg_combo: Gtk.DropDown | None) -> tuple[str, str] | None:
        fg = GtkHelper.dropdown_selected_text(fg_combo)
        bg = GtkHelper.dropdown_selected_text(bg_combo)
        if not fg or not bg:
            return None
        return fg, bg

    def _normal_color_note_text(self, simple_panel: ThemeSimpleConfigPanel) -> str:
        pair = self._color_pair(simple_panel.widgets.normal_fg_combo, simple_panel.widgets.normal_bg_combo)
        if pair is None:
            return "GRUB_COLOR_NORMAL : couleur du texte et du fond des entrées non sélectionnées."
        fg, bg = pair
        return f'GRUB_COLOR_NORMAL="{fg}/{bg}" : texte {fg} sur fond {bg} ' "(entrées non sélectionnées)."

    def _highlight_color_note_text(self, simple_panel: ThemeSimpleConfigPanel) -> str:
        pair = self._color_pair(simple_panel.widgets.highlight_fg_combo, simple_panel.widgets.highlight_bg_combo)
        if pair is None:
            return "GRUB_COLOR_HIGHLIGHT : couleur du texte et du fond de l'entrée sélectionnée."
        fg, bg = pair
        return f'GRUB_COLOR_HIGHLIGHT="{fg}/{bg}" : texte {fg} sur fond {bg} ' "(entrée sélectionnée)."

    def _effective_script_state(self, script: Any) -> tuple[bool, bool]:
        key = str(getattr(script, "path", ""))
        pending = getattr(self.state_manager, "pending_script_changes", {})
        if isinstance(pending, dict) and key in pending:
            return bool(pending[key]), True
        return bool(getattr(script, "is_executable", False)), False

    def _find_script_by_name(self, target: str) -> Any | None:
        try:
            scripts = self.services.script_service.scan_theme_scripts()
            scripts_list = list(scripts) if scripts else []
        except OSError:  # pragma: no cover
            scripts_list = []

        for script in scripts_list:
            name = str(getattr(script, "name", ""))
            if name == target:
                return script
        return None

    def _script_state_note_text(self, *, script_name: str, active_text: str, inactive_text: str) -> str:
        script = self._find_script_by_name(script_name)
        if script is None:
            return f"Script non trouvé : {script_name}."

        active, pending = self._effective_script_state(script)
        suffix = " (changement en attente)" if pending else ""
        state = "Actif" if active else "Inactif"
        detail = active_text if active else inactive_text
        return f"{state}{suffix} : {detail}"

    @staticmethod
    def _set_label_text(label: Gtk.Label | None, text: str) -> None:
        if label is None:
            return
        label.set_text(text)

    def _update_bg_note_label(self, simple_panel: ThemeSimpleConfigPanel, label: Gtk.Label | None, *_: object) -> None:
        self._set_label_text(label, self._bg_note_text(simple_panel))

    def _update_color_note_labels(
        self,
        simple_panel: ThemeSimpleConfigPanel,
        normal_label: Gtk.Label | None,
        highlight_label: Gtk.Label | None,
        *_: object,
    ) -> None:
        self._set_label_text(normal_label, self._normal_color_note_text(simple_panel))
        self._set_label_text(highlight_label, self._highlight_color_note_text(simple_panel))

    def _appearance_scripts_note_text(self) -> str:
        """Résume les scripts pouvant écraser les réglages d'apparence.

        On se base sur les scripts détectés (theme/colors/custom).
        """
        try:
            scripts = self.services.script_service.scan_theme_scripts()
            scripts_list = list(scripts) if scripts else []
        except OSError:  # pragma: no cover
            scripts_list = []

        if not scripts_list:
            return "Aucun script d'apparence détecté dans /etc/grub.d."  # pragma: no cover

        # Classement simple: actifs vs inactifs.
        active_names: list[str] = []
        inactive_names: list[str] = []
        for script in scripts_list:
            name = str(getattr(script, "name", ""))
            active, pending = self._effective_script_state(script)
            decorated = f"{name}{' *' if pending else ''}"
            (active_names if active else inactive_names).append(decorated)

        active_part = ", ".join(active_names) if active_names else "(aucun)"
        inactive_part = ", ".join(inactive_names) if inactive_names else "(aucun)"

        return (
            "Actifs (peuvent écraser GRUB_THEME/GRUB_BACKGROUND/GRUB_COLOR_*): "
            f"{active_part}. Inactifs: {inactive_part}."
        )

    def _update_script_note_labels(
        self,
        grub_colors_label: Gtk.Label | None,
        *_: object,
    ) -> None:
        self._set_label_text(grub_colors_label, self._appearance_scripts_note_text())

    def _wire_grub_scripts_dynamic_notes(
        self,
        *,
        simple_panel: ThemeSimpleConfigPanel,
        notes: _GrubScriptsDynamicNotes,
    ) -> None:
        bg_note_label = GtkHelper.info_box_text_label(notes.bg_note)
        normal_note_label = GtkHelper.info_box_text_label(notes.normal_note)
        highlight_note_label = GtkHelper.info_box_text_label(notes.highlight_note)
        grub_colors_note_label = GtkHelper.info_box_text_label(notes.grub_colors_note)

        update_bg = partial(self._update_bg_note_label, simple_panel, bg_note_label)
        update_colors = partial(self._update_color_note_labels, simple_panel, normal_note_label, highlight_note_label)
        update_scripts = partial(self._update_script_note_labels, grub_colors_note_label)

        if simple_panel.widgets.bg_image_entry is not None:
            simple_panel.widgets.bg_image_entry.connect("changed", update_bg)

        for combo in (
            simple_panel.widgets.normal_fg_combo,
            simple_panel.widgets.normal_bg_combo,
            simple_panel.widgets.highlight_fg_combo,
            simple_panel.widgets.highlight_bg_combo,
        ):
            if combo is not None:
                combo.connect("notify::selected", update_colors)

        scripts_list = self.widgets.panels.scripts_list
        if scripts_list is not None:
            original_on_toggle = scripts_list.on_script_switch_toggled

            def wrapped_on_toggle(sw: Any, script: Any, label: Gtk.Label | None = None) -> None:
                original_on_toggle(sw, script, label)
                update_scripts()

            scripts_list.on_script_switch_toggled = wrapped_on_toggle  # type: ignore[assignment]

        update_bg()
        update_colors()
        update_scripts()

    def refresh(self) -> None:
        """Rafraîchit l'affichage des scripts et des thèmes."""
        scripts_list = self.widgets.panels.scripts_list
        if scripts_list is not None:
            scripts_list.refresh()
        self.scan_system_themes()

    def _build_header(self, container: Gtk.Box, *, title: str, subtitle: str) -> None:
        """Construit l'en-tête d'un onglet."""
        # En-tête désactivé: l'utilisateur ne souhaite pas d'info-box en haut des onglets.
        del container, title, subtitle

    def _build_left_column(self, container: Gtk.Box) -> None:
        """Construit la colonne de gauche (liste des thèmes)."""
        panels = self.widgets.panels

        grid = box_append_section_grid(
            container,
            "Thèmes disponibles",
            row_spacing=0,
            column_spacing=0,
            title_class="blue",
            frame_class="blue-frame",
        )

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_min_content_height(400)

        panels.theme_list_box = Gtk.ListBox()
        panels.theme_list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        panels.theme_list_box.add_css_class("rich-list")
        panels.theme_list_box.add_css_class("compact-list")
        panels.theme_list_box.connect("row-selected", self._on_theme_row_selected)

        scrolled.set_child(panels.theme_list_box)
        grid.attach(scrolled, 0, 0, 1, 1)

    def _on_theme_row_selected(self, list_box: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        """Callback GTK: sélection d'une ligne de thème."""
        # En fin de process (tests/coverage), GTK peut encore émettre des signaux
        # pendant que Python finalise ses modules/objets. On ignore alors.
        try:
            if getattr(sys, "is_finalizing", lambda: False)():
                return
        except (AttributeError, ImportError):
            return

        try:
            handlers.on_theme_selected(list_box, row, self)
        except (AttributeError, TypeError, ValueError) as exc:
            # Ne jamais laisser une exception sortir d'un callback GTK: cela peut
            # provoquer des crashes natifs (SIGSEGV) côté PyGObject.
            logger.debug(f"[TabThemeConfig._on_theme_row_selected] Ignoré: {exc}")

    def _build_simple_config_column(self, container: Gtk.Box) -> None:
        """Construit la colonne de gauche avec la configuration visuelle."""
        del container
        panels = self.widgets.panels

        # Panneau de configuration simple
        panels.simple_config_panel = ThemeSimpleConfigPanel(
            state_manager=self.state_manager,
            on_changed=self.mark_dirty,
        )

        # Le placement visuel est géré par build_grub_scripts_tab (blocs séparés).
        panels.simple_config_panel.set_hexpand(True)

    def _build_scripts_column(self, container: Gtk.Box) -> None:
        """Construit la colonne de droite avec les scripts et informations."""
        panels = self.widgets.panels

        # Liste des scripts
        panels.scripts_list = ThemeScriptsList(
            state_manager=self.state_manager,
            script_service=self.services.script_service,
        )
        panels.scripts_list.set_vexpand(True)

        grid_scripts = box_append_section_grid(
            container,
            "Scripts de personnalisation",
            row_spacing=12,
            column_spacing=12,
            title_class="orange",
            frame_class="orange-frame",
        )
        grid_scripts.attach(panels.scripts_list, 0, 0, 1, 1)

    def _build_right_column(self, container: Gtk.Box) -> None:
        """Construit la colonne de droite (actions)."""
        actions = self.widgets.actions
        parts = build_theme_config_right_column(
            callbacks=ThemeConfigCallbacks(
                on_preview=lambda: handlers.on_preview_theme(self),
                on_activate_theme=lambda b: handlers.on_activate_theme(b, self),
                on_deactivate_theme=lambda b: handlers.on_deactivate_theme(b, self),
                on_edit=lambda b: (
                    handlers.on_edit_theme(b, self.data.current_theme.name, self) if self.data.current_theme else None
                ),
                on_delete=lambda b: (
                    handlers.on_delete_theme(b, self.data.current_theme.name, self) if self.data.current_theme else None
                ),
                on_open_editor=lambda b: handlers.on_open_editor(self, b),
            )
        )

        actions.preview_btn = parts.buttons.preview_btn
        actions.activate_theme_btn = parts.buttons.activate_theme_btn
        actions.deactivate_theme_btn = parts.buttons.deactivate_theme_btn
        actions.edit_btn = parts.buttons.edit_btn
        actions.delete_btn = parts.buttons.delete_btn
        # self.activate_script_btn et self.deactivate_script_btn sont maintenant dans _build_simple_config_section

        # Les composants internes (ui_components_theme_config_actions) créent déjà leurs propres
        # Frames titrées (via box_append_section_grid). On les ajoute directement pour éviter
        # une double encapsulation (Frame dans Frame).
        container.append(parts.actions_box)
        container.append(parts.global_actions_box)

    # _build_theme_list_section et _build_actions_section sont supprimés car intégrés dans build_theme_tab()

    def _load_simple_config(self, model: GrubUiModel) -> None:
        """Charge la configuration simple depuis le modèle."""
        simple_config_panel = self.widgets.panels.simple_config_panel
        if not simple_config_panel:
            return

        simple_config_panel.update_from_model(model)
        active_colors = self._find_active_color_script()

        if active_colors is not None:
            simple_config_panel.set_colors_section_enabled(False, reason=str(getattr(active_colors, "name", "")))
        else:
            simple_config_panel.set_colors_section_enabled(True)

    def _find_active_color_script(self) -> Any | None:
        """Trouve le script de couleurs actif s'il existe."""
        try:
            scripts = self.services.script_service.scan_theme_scripts()
            return next(
                (
                    s
                    for s in scripts
                    if getattr(s, "is_executable", False) and "color" in str(getattr(s, "name", "")).lower()
                ),
                None,
            )
        except (OSError, RuntimeError, ValueError):
            return None

    def _load_active_theme(self) -> None:
        """Charge le thème actif depuis le gestionnaire de thèmes."""
        try:
            active_theme = self.services.theme_manager.load_active_theme()
            if active_theme:
                self.data.current_theme = active_theme
                logger.debug(f"[TabThemeConfig] Thème actif: {active_theme.name}")
        except (OSError, RuntimeError) as e:
            logger.warning(f"[TabThemeConfig] Pas de thème actif: {e}")

    def _select_active_theme_in_list(self, model: GrubUiModel) -> None:
        """Sélectionne le thème actif dans la liste."""
        theme_list_box = self.widgets.panels.theme_list_box
        if not theme_list_box or len(self.data.available_themes) == 0:
            return

        target_index = 0  # "Aucun (GRUB par défaut)" est en premier
        if model.grub_theme:
            target_index = self._find_theme_index(model.grub_theme)

        row = theme_list_box.get_row_at_index(target_index)
        if row:
            theme_list_box.select_row(row)

    def _find_theme_index(self, grub_theme_path: str) -> int:
        """Trouve l'index du thème dans la liste."""
        for idx, (theme_name, _) in enumerate(self.data.available_themes.items()):
            theme_path = self.data.theme_paths.get(theme_name)
            if not theme_path:
                continue
            try:
                theme_txt_path = theme_path / "theme.txt"
                if str(theme_txt_path) == grub_theme_path:
                    return idx
            except (OSError, RuntimeError, TypeError, ValueError):
                continue
        return 0

    def load_themes(self) -> None:
        """Charge la configuration du thème depuis le modèle et met à jour l'UI."""
        if not self.state_manager.state_data or not self.state_manager.state_data.model:
            logger.debug("[TabThemeConfig.load_themes] Pas de modèle disponible")
            return

        self._updating_ui = True
        try:
            model = self.state_manager.state_data.model
            logger.info("[TabThemeConfig.load_themes] Chargement config thème (2 onglets, sans switch)")

            self._load_simple_config(model)
            self._load_active_theme()
            self.refresh()
            self._select_active_theme_in_list(model)
        except (OSError, RuntimeError) as e:
            logger.error(f"[TabThemeConfig.load_themes] Erreur: {e}")
        finally:
            self._updating_ui = False

    def scan_system_themes(self) -> None:
        """Scanne les répertoires système pour trouver les thèmes."""
        self.data.available_themes.clear()
        self.data.theme_paths.clear()

        theme_list_box = self.widgets.panels.theme_list_box
        if theme_list_box is None:
            return

        # Nettoyer la liste des thèmes dans l'UI
        while True:
            child = theme_list_box.get_first_child()
            if child is None:
                break
            theme_list_box.remove(child)

        # 1. Ajouter l'option "Aucun"
        none_theme = GrubTheme(name="Aucun (GRUB par défaut)")
        self.data.available_themes[none_theme.name] = none_theme
        self._add_theme_to_list(none_theme, None)

        # 2. Utiliser le service pour scanner les thèmes
        scanned_themes = self.services.theme_service.scan_system_themes()

        # Récupérer le thème actif au niveau système (grub.cfg) pour information
        raw_system_theme = self.services.theme_service.get_active_theme_path()
        self.data.system_active_theme_path = (
            raw_system_theme.replace("${prefix}", "/boot/grub") if raw_system_theme else None
        )

        for theme_name, (theme, item) in scanned_themes.items():
            self.data.available_themes[theme_name] = theme
            self.data.theme_paths[theme_name] = item
            self._add_theme_to_list(theme, item)

        if len(self.data.available_themes) == 0:
            logger.warning("[TabThemeConfig.scan_system_themes] Aucun thème valide trouvé")
            # Ajouter un placeholder
            row = Gtk.ListBoxRow()
            row.set_selectable(False)
            label = Gtk.Label(label="Aucun thème trouvé")
            label.set_halign(Gtk.Align.START)
            label.set_margin_top(4)
            label.set_margin_bottom(4)
            label.set_margin_start(6)
            row.set_child(label)
            theme_list_box.append(row)

    def _add_theme_to_list(self, theme: GrubTheme, theme_path: Path | None) -> None:
        """Ajoute un thème à la liste.

        Args:
            theme: Thème à ajouter.
            theme_path: Chemin du répertoire du thème (None pour 'Aucun').
        """
        row = Gtk.ListBoxRow()

        # Contenu de la ligne
        content_box = Gtk.Box(orientation=HORIZONTAL, spacing=8)
        content_box.set_margin_top(2)
        content_box.set_margin_bottom(2)
        content_box.set_margin_start(4)
        content_box.set_margin_end(4)

        # Nom du thème
        theme_label = Gtk.Label(label=theme.name or "Thème sans nom")
        theme_label.set_halign(Gtk.Align.START)
        theme_label.set_hexpand(True)
        # Empêche un nom de thème très long d'augmenter la largeur minimale de l'onglet.
        theme_label.set_max_width_chars(32)
        theme_label.add_css_class("title-4")
        content_box.append(theme_label)

        # Vérifier si le thème est modifiable
        is_custom = False
        if theme_path:
            is_custom = self.services.theme_service.is_theme_custom(theme_path)

        # Vérifier si le thème est actif dans le modèle
        model = self.state_manager.get_model()
        is_config_active = False
        if theme_path:
            theme_txt_path = theme_path / "theme.txt"
            is_config_active = str(theme_txt_path) == model.grub_theme
        else:
            # Cas "Aucun"
            is_config_active = not model.grub_theme

        # Vérifier si le thème est actif système (surcharge script)
        is_system_active = False
        if self.data.system_active_theme_path and theme_path:
            theme_txt_path = theme_path / "theme.txt"
            # Comparaison souple (gestion potentielle des chemins relatifs/absolus différents)
            is_system_active = str(theme_txt_path) == self.data.system_active_theme_path

        # Création et ajout du badge
        badge = self._create_theme_badge(
            is_config_active=is_config_active,
            is_system_active=is_system_active,
            is_custom=is_custom,
            has_path=theme_path is not None,
        )
        if badge:
            content_box.append(badge)

        row.set_child(content_box)
        theme_list_box = self.widgets.panels.theme_list_box
        if theme_list_box is not None:
            theme_list_box.append(row)

    def _create_theme_badge(
        self,
        *,
        is_config_active: bool,
        is_system_active: bool,
        is_custom: bool,
        has_path: bool,
    ) -> Gtk.Label | None:
        """Crée le badge de statut approprié pour un thème."""
        if is_config_active:
            badge = Gtk.Label(label="Actif")
            badge.add_css_class("success")
            badge.set_margin_end(4)
            return badge

        if is_system_active:
            badge = Gtk.Label(label="Forcé (script)")
            badge.set_tooltip_text("Ce thème est imposé par un script (ex: 05_debian_theme) malgré la configuration.")
            badge.add_css_class("warning")
            badge.set_margin_end(4)
            return badge

        if has_path and not is_custom:
            badge = Gtk.Label(label="Système")
            badge.add_css_class("dim-label")
            badge.set_margin_end(4)
            return badge

        if has_path:
            badge = Gtk.Label(label="Custom")
            badge.add_css_class("success")
            badge.set_margin_end(4)
            return badge

        return None
