"""Onglet de configuration du thème GRUB."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
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
    create_titled_frame,
    create_two_column_layout,
)
from ui.components.ui_components_theme_config_actions import ThemeConfigCallbacks, build_theme_config_right_column
from ui.components.ui_components_theme_scripts_list import ThemeScriptsList
from ui.components.ui_components_theme_simple_config import ThemeSimpleConfigPanel
from ui.tabs.theme_config import ui_tabs_theme_config_handlers as handlers

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

        _container, left_section, right_section = create_two_column_layout(main_box, spacing=12)
        self._build_left_column(left_section)
        self._build_right_column(right_section)

        self.load_themes()
        return main_box

    def build_grub_scripts_tab(self) -> Gtk.Box:
        """Construit l'onglet "Apparence" (configuration simple + scripts)."""
        main_box = create_main_box(spacing=12, margin=12)
        self._build_header(
            main_box,
            title="Apparence",
            subtitle="Configuration du fond d'écran, des couleurs du menu et scripts de personnalisation.",
        )

        _container, left_section, right_section = create_two_column_layout(main_box, spacing=12)

        # Colonne gauche: Configuration simple
        self._build_simple_config_column(left_section)

        # Colonne droite: Scripts et informations
        self._build_scripts_column(right_section)

        self.load_themes()
        return main_box

    def refresh(self) -> None:
        """Rafraîchit l'affichage des scripts et des thèmes."""
        scripts_list = self.widgets.panels.scripts_list
        if scripts_list is not None:
            scripts_list.refresh()
        self.scan_system_themes()

    def _build_header(self, container: Gtk.Box, *, title: str, subtitle: str) -> None:
        """Construit l'en-tête d'un onglet."""
        container.append(
            create_info_box(
                f"{title}:",
                subtitle,
                css_class="info-box",
            )
        )

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
        except Exception:  # pylint: disable=broad-exception-caught
            return

        try:
            handlers.on_theme_selected(list_box, row, self)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Ne jamais laisser une exception sortir d'un callback GTK: cela peut
            # provoquer des crashes natifs (SIGSEGV) côté PyGObject.
            logger.debug(f"[TabThemeConfig._on_theme_row_selected] Ignoré: {exc}")

    def _build_simple_config_column(self, container: Gtk.Box) -> None:
        """Construit la colonne de gauche avec la configuration visuelle."""
        panels = self.widgets.panels

        # Panneau de configuration simple
        panels.simple_config_panel = ThemeSimpleConfigPanel(
            state_manager=self.state_manager,
            on_changed=self.mark_dirty,
        )

        grid_simple = box_append_section_grid(
            container,
            "Personnalisation visuelle",
            row_spacing=12,
            column_spacing=12,
            title_class="blue",
            frame_class="blue-frame",
        )
        grid_simple.attach(panels.simple_config_panel, 0, 0, 1, 1)

    def _build_scripts_column(self, container: Gtk.Box) -> None:
        """Construit la colonne de droite avec les scripts et informations."""
        panels = self.widgets.panels

        # Liste des scripts
        panels.scripts_list = ThemeScriptsList(
            state_manager=self.state_manager,
            script_service=self.services.script_service,
        )

        grid_scripts = box_append_section_grid(
            container,
            "Scripts de personnalisation",
            row_spacing=12,
            column_spacing=12,
            title_class="orange",
            frame_class="orange-frame",
        )
        grid_scripts.attach(panels.scripts_list, 0, 0, 1, 1)

        # Informations additionnelles
        info_text = (
            "<b>Configuration visuelle</b>\n"
            "• <b>Image de fond</b> : Définit GRUB_BACKGROUND\n"
            "• <b>Couleurs</b> : Définit GRUB_COLOR_NORMAL et GRUB_COLOR_HIGHLIGHT\n\n"
            "<b>Scripts de personnalisation</b>\n"
            "Les scripts dans /etc/grub.d/ peuvent redéfinir les couleurs ou ajouter "
            "des entrées personnalisées au menu GRUB.\n\n"
            "Les scripts activés (exécutables) sont exécutés lors de 'update-grub'."
        )

        info_box = create_info_box(
            "Informations",
            info_text,
            css_class="info-box",
        )
        container.append(info_box)

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

        container.append(create_titled_frame("Actions sur le thème", parts.actions_box))

        # Le builder inclut déjà un titre interne "Outils"; on le retire pour éviter
        # une double ligne de titre une fois dans un frame titré.
        try:
            first = parts.global_actions_box.get_first_child()
            if isinstance(first, Gtk.Label):
                parts.global_actions_box.remove(first)
        except (AttributeError, TypeError, RuntimeError):
            pass
        container.append(create_titled_frame("Outils", parts.global_actions_box))

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
        theme_label.add_css_class("title-4")
        content_box.append(theme_label)

        # Vérifier si le thème est modifiable
        is_custom = False
        if theme_path:
            is_custom = self.services.theme_service.is_theme_custom(theme_path)

        # Vérifier si le thème est actif dans le modèle
        model = self.state_manager.get_model()
        is_active = False
        if theme_path:
            theme_txt_path = theme_path / "theme.txt"
            is_active = str(theme_txt_path) == model.grub_theme
        else:
            # Cas "Aucun"
            is_active = not model.grub_theme

        # Badge pour l'état actif
        if is_active:
            active_badge = Gtk.Label(label="Actif")
            active_badge.add_css_class("success")
            active_badge.set_margin_end(4)
            content_box.append(active_badge)
        # Badge pour les thèmes système
        elif theme_path and not is_custom:
            system_badge = Gtk.Label(label="Système")
            system_badge.add_css_class("dim-label")
            system_badge.set_margin_end(4)
            content_box.append(system_badge)
        elif theme_path:
            custom_badge = Gtk.Label(label="Custom")
            custom_badge.add_css_class("success")
            custom_badge.set_margin_end(4)
            content_box.append(custom_badge)

        row.set_child(content_box)
        theme_list_box = self.widgets.panels.theme_list_box
        if theme_list_box is not None:
            theme_list_box.append(row)
