"""Onglet de configuration du thème GRUB."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gi.repository import Gtk
from loguru import logger

from core.models.core_theme_models import GrubTheme
from core.services.core_grub_script_service import GrubScriptService
from core.services.core_theme_service import ThemeService
from core.theme.core_active_theme_manager import ActiveThemeManager
from ui.components.ui_theme_config_actions import ThemeConfigCallbacks, build_theme_config_right_column
from ui.components.ui_theme_scripts_list import ThemeScriptsList
from ui.components.ui_theme_simple_config import ThemeSimpleConfigPanel
from ui.tabs.theme_config import ui_theme_config_handlers as handlers
from ui.ui_widgets import create_main_box, create_two_column_layout

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
    theme_switch: Gtk.Switch | None = None
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
class _TabThemeConfigContainers:
    theme_sections_container: Gtk.Box | None = None
    simple_config_container: Gtk.Box | None = None


@dataclass(slots=True)
class _TabThemeConfigWidgets:
    panels: _TabThemeConfigPanels = field(default_factory=_TabThemeConfigPanels)
    actions: _TabThemeConfigActions = field(default_factory=_TabThemeConfigActions)
    containers: _TabThemeConfigContainers = field(default_factory=_TabThemeConfigContainers)


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
        """Construit l'interface utilisateur de l'onglet.

        Returns:
            Widget racine de l'onglet.
        """
        main_box = create_main_box(spacing=12, margin=12)

        widgets = self.widgets
        containers = widgets.containers

        self._build_header(main_box)

        switch_section = self._build_switch_section()
        main_box.append(switch_section)

        # Séparateur
        separator = Gtk.Separator(orientation=HORIZONTAL)
        main_box.append(separator)

        # === SECTION 1: Configuration Simple (Switch OFF) ===
        containers.simple_config_container = self._build_simple_config_section()
        main_box.append(containers.simple_config_container)

        # === SECTION 2: Gestion Complète des Thèmes (Switch ON) ===
        # Conteneur pour toutes les sections de thèmes (masquable)
        containers.theme_sections_container, left_section, right_section = create_two_column_layout(main_box)

        self._build_left_column(left_section)
        self._build_right_column(right_section)

        # Initialement masqué (sera géré par _load_themes)
        containers.theme_sections_container.set_visible(False)
        containers.simple_config_container.set_visible(True)

        # Charger les thèmes
        self.load_themes()

        return main_box

    def refresh(self) -> None:
        """Rafraîchit l'affichage des scripts et des thèmes."""
        scripts_list = self.widgets.panels.scripts_list
        if scripts_list is not None:
            scripts_list.refresh()
        self.scan_system_themes()

    def _build_header(self, container: Gtk.Box) -> None:
        """Construit l'en-tête de l'onglet."""
        header_label = Gtk.Label(xalign=0)
        header_label.set_markup("<b>Configuration du Thème</b>")
        header_label.add_css_class("section-title")
        container.append(header_label)

        desc_label = Gtk.Label(xalign=0, label="Gérez l'apparence du menu de démarrage GRUB.")
        desc_label.add_css_class("dim-label")
        desc_label.add_css_class("subtitle-label")
        desc_label.set_margin_bottom(12)
        container.append(desc_label)

    def _build_left_column(self, container: Gtk.Box) -> None:
        """Construit la colonne de gauche (liste des thèmes)."""
        panels = self.widgets.panels

        title = Gtk.Label(xalign=0)
        title.set_markup("<b>Thèmes disponibles</b>")
        title.add_css_class("section-title")
        container.append(title)

        frame = Gtk.Frame()
        frame.set_hexpand(True)
        frame.set_vexpand(True)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        panels.theme_list_box = Gtk.ListBox()
        panels.theme_list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        panels.theme_list_box.add_css_class("rich-list")
        panels.theme_list_box.connect("row-selected", lambda lb, row: handlers.on_theme_selected(lb, row, self))

        scrolled.set_child(panels.theme_list_box)

        frame.set_child(scrolled)
        container.append(frame)

    def _build_simple_config_section(self) -> Gtk.Box:
        """Construit la section de configuration simple (couleurs et fond)."""
        panels = self.widgets.panels
        container = Gtk.Box(orientation=VERTICAL, spacing=15)
        container.set_margin_top(10)
        container.set_margin_bottom(10)
        container.set_margin_start(10)
        container.set_margin_end(10)

        # Panneau de configuration simple
        panels.simple_config_panel = ThemeSimpleConfigPanel(
            state_manager=self.state_manager,
            on_changed=self.mark_dirty,
        )
        container.append(panels.simple_config_panel)

        # Séparateur
        sep = Gtk.Separator(orientation=HORIZONTAL)
        sep.set_margin_top(15)
        sep.set_margin_bottom(15)
        container.append(sep)

        # Liste des scripts
        panels.scripts_list = ThemeScriptsList(
            state_manager=self.state_manager,
            script_service=self.services.script_service,
        )
        container.append(panels.scripts_list)

        return container

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

        container.append(parts.actions_title)
        container.append(parts.actions_box)
        container.append(parts.global_actions_box)

    def _build_switch_section(self) -> Gtk.Widget:
        """Construit la section de switch pour afficher/masquer les thèmes.

        Returns:
            Widget de la section.
        """
        panels = self.widgets.panels
        box = Gtk.Box(orientation=HORIZONTAL, spacing=10)
        box.set_margin_bottom(10)

        # Utilisation d'un style "card" ou "box" pour le switch principal
        box.add_css_class("info-box")

        label = Gtk.Label(label="Activer la gestion des thèmes GRUB")
        label.set_markup("<b>Activer la gestion des thèmes GRUB</b>")
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        box.append(label)

        panels.theme_switch = Gtk.Switch()
        panels.theme_switch.set_halign(Gtk.Align.END)
        panels.theme_switch.set_valign(Gtk.Align.CENTER)
        panels.theme_switch.connect(
            "notify::active",
            lambda sw, _p: handlers.on_theme_switch_toggled(sw, _p, self),
        )
        box.append(panels.theme_switch)

        return box

    # _build_theme_list_section et _build_actions_section sont supprimés car intégrés dans build()

    def load_themes(self) -> None:
        """Charge la configuration du thème depuis le modèle et met à jour l'UI."""
        # Utiliser l'état du modèle chargé (basé sur les scripts)
        if not self.state_manager.state_data or not self.state_manager.state_data.model:
            logger.debug("[TabThemeConfig.load_themes] Pas de modèle disponible")
            return

        # On bloque les mises à jour de l'UI vers le modèle pendant le chargement
        self._updating_ui = True
        try:
            model = self.state_manager.state_data.model
            theme_enabled = model.theme_management_enabled
            logger.info(
                f"[TabThemeConfig.load_themes] Chargement config thème - theme_management_enabled={theme_enabled}"
            )

            # Définir l'état du switch
            theme_switch = self.widgets.panels.theme_switch
            if theme_switch:
                theme_switch.set_active(theme_enabled)
                logger.debug(f"[TabThemeConfig.load_themes] Switch mis à {theme_enabled}")

                # Afficher les sections si activé
                containers = self.widgets.containers
                if containers.theme_sections_container:
                    containers.theme_sections_container.set_visible(theme_enabled)
                if containers.simple_config_container:
                    containers.simple_config_container.set_visible(not theme_enabled)

            # === Charger la config simple ===
            simple_config_panel = self.widgets.panels.simple_config_panel
            if simple_config_panel:
                simple_config_panel.update_from_model(model)

            # Charger le thème actif s'il existe
            try:
                active_theme = self.services.theme_manager.load_active_theme()
                if active_theme:
                    data = self.data
                    data.current_theme = active_theme
                    logger.debug(f"[TabThemeConfig.load_themes] Thème actif: {active_theme.name}")
            except (OSError, RuntimeError) as e:
                logger.warning(f"[TabThemeConfig.load_themes] Pas de thème actif: {e}")

            # Si le switch est activé, charger les thèmes maintenant
            if theme_enabled:
                self.refresh()

                # Sélectionner le premier thème si disponible
                theme_list_box = self.widgets.panels.theme_list_box
                if theme_list_box and len(self.data.available_themes) > 0:
                    first_row = theme_list_box.get_row_at_index(0)
                    if first_row:
                        theme_list_box.select_row(first_row)

            logger.debug(f"[TabThemeConfig.load_themes] Switch état: {theme_enabled}")
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
            label.set_margin_top(8)
            label.set_margin_bottom(8)
            label.set_margin_start(10)
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
        content_box = Gtk.Box(orientation=HORIZONTAL, spacing=10)
        content_box.set_margin_top(8)
        content_box.set_margin_bottom(8)
        content_box.set_margin_start(10)
        content_box.set_margin_end(10)

        # Icône
        icon_label = Gtk.Label(label="🎨")
        if theme_path is None:
            icon_label.set_label("🚫")
        icon_label.set_margin_end(8)
        content_box.append(icon_label)

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
            active_badge = Gtk.Label(label="✅ Actif")
            active_badge.add_css_class("success")
            active_badge.set_margin_end(10)
            content_box.append(active_badge)
        # Badge pour les thèmes système
        elif theme_path and not is_custom:
            system_badge = Gtk.Label(label="Système")
            system_badge.add_css_class("dim-label")
            system_badge.set_margin_end(10)
            content_box.append(system_badge)
        elif theme_path:
            custom_badge = Gtk.Label(label="Custom")
            custom_badge.add_css_class("success")
            custom_badge.set_margin_end(10)
            content_box.append(custom_badge)

        row.set_child(content_box)
        theme_list_box = self.widgets.panels.theme_list_box
        if theme_list_box is not None:
            theme_list_box.append(row)
