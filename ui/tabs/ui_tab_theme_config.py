"""Onglet de configuration du thème GRUB."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from gi.repository import Gtk
from loguru import logger

from core.config.core_paths import get_all_grub_themes_dirs as _get_all_grub_themes_dirs
from core.core_exceptions import GrubCommandError, GrubScriptNotFoundError
from core.services.core_grub_script_service import GrubScriptService
from core.services.core_theme_service import ThemeService
from core.theme.core_active_theme_manager import ActiveThemeManager
from core.models.core_theme_models import GrubTheme
from core.models.core_theme_models import create_custom_theme as _create_custom_theme
from ui.components.ui_theme_config_actions import build_theme_config_right_column
from ui.components.ui_theme_simple_config import ThemeSimpleConfigPanel
from ui.components.ui_theme_scripts_list import ThemeScriptsList
from ui.dialogs.ui_interactive_theme_generator_window import (
    InteractiveThemeGeneratorWindow,
)
from ui.tabs.ui_grub_preview_dialog import GrubPreviewDialog
from ui.ui_constants import GRUB_COLORS
from ui.ui_gtk_helpers import GtkHelper
from ui.ui_widgets import create_error_dialog, create_main_box, create_success_dialog, create_two_column_layout

HORIZONTAL = Gtk.Orientation.HORIZONTAL
VERTICAL = Gtk.Orientation.VERTICAL


def get_all_grub_themes_dirs() -> list[Path]:
    """Proxy pour compatibilité avec les tests (patch du symbole dans ce module)."""
    return _get_all_grub_themes_dirs()


def create_custom_theme(name: str, **kwargs: Any) -> GrubTheme:
    """Proxy pour compatibilité avec les tests (patch du symbole dans ce module)."""
    return _create_custom_theme(name, **kwargs)


class TabThemeConfig:
    """Onglet pour sélectionner et configurer le thème GRUB."""

    # pylint: disable=too-many-instance-attributes

    def __init__(self, state_manager: Any, window: Gtk.Window | None = None) -> None:
        """Initialise l'onglet de configuration de thème.

        Args:
            state_manager: Gestionnaire d'état global.
            window: Fenêtre parente (optionnel).
        """
        self.state_manager = state_manager
        self.current_theme: GrubTheme | None = None
        self.theme_manager = ActiveThemeManager()
        self.script_service = GrubScriptService()
        self.theme_service = ThemeService()
        self.available_themes: dict[str, GrubTheme] = {}
        self.theme_paths: dict[str, Path] = {}  # Pour stocker le chemin de chaque thème
        self.parent_window: Gtk.Window | None = window
        self._updating_ui: bool = False

        # Widgets
        self.theme_list_box: Gtk.ListBox | None = None
        self.current_script: Any = None
        self.preview_btn: Gtk.Button | None = None
        self.activate_theme_btn: Gtk.Button | None = None
        self.deactivate_theme_btn: Gtk.Button | None = None
        self.edit_btn: Gtk.Button | None = None
        self.delete_btn: Gtk.Button | None = None
        self.theme_switch: Gtk.Switch | None = None

        # Compat tests (anciens attributs)
        self.scripts_list_box: Gtk.ListBox | None = None

        # Compat tests (anciens widgets de config simple)
        self.bg_image_entry: Gtk.Entry | None = None
        self.normal_fg_combo: Gtk.DropDown | None = None
        self.normal_bg_combo: Gtk.DropDown | None = None
        self.highlight_fg_combo: Gtk.DropDown | None = None
        self.highlight_bg_combo: Gtk.DropDown | None = None

        # Composants
        self.simple_config_panel: ThemeSimpleConfigPanel | None = None
        self.scripts_list: ThemeScriptsList | None = None

        # Sections à afficher/masquer avec le switch
        self.theme_sections_container: Gtk.Box | None = None
        self.simple_config_container: Gtk.Box | None = None

        logger.debug("[TabThemeConfig.__init__] Onglet initialisé")

    def _mark_dirty(self) -> None:
        """Marque l'état comme modifié."""
        save_btn = getattr(self.parent_window, "save_btn", None)
        reload_btn = getattr(self.parent_window, "reload_btn", None)
        if save_btn and reload_btn:
            self.state_manager.mark_dirty(save_btn, reload_btn)

    def build(self) -> Gtk.Box:
        """Construit l'interface utilisateur de l'onglet.

        Returns:
            Widget racine de l'onglet.
        """
        main_box = create_main_box(spacing=12, margin=12)

        self._build_header(main_box)

        switch_section = self._build_switch_section()
        main_box.append(switch_section)

        # Séparateur
        separator = Gtk.Separator(orientation=HORIZONTAL)
        main_box.append(separator)

        # === SECTION 1: Configuration Simple (Switch OFF) ===
        self.simple_config_container = self._build_simple_config_section()
        main_box.append(self.simple_config_container)

        # === SECTION 2: Gestion Complète des Thèmes (Switch ON) ===
        # Conteneur pour toutes les sections de thèmes (masquable)
        self.theme_sections_container, left_section, right_section = create_two_column_layout(main_box)

        self._build_left_column(left_section)
        self._build_right_column(right_section)

        # Initialement masqué (sera géré par _load_themes)
        self.theme_sections_container.set_visible(False)
        self.simple_config_container.set_visible(True)

        # Charger les thèmes
        self._load_themes()

        return main_box

    def refresh(self) -> None:
        """Rafraîchit l'affichage des scripts et des thèmes."""
        _scan_grub_scripts(self)
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
        list_title = Gtk.Label(xalign=0)
        list_title.set_markup("<b>Thèmes disponibles</b>")
        list_title.add_css_class("section-title")
        container.append(list_title)

        # Frame + Scrolled window pour harmoniser avec les autres onglets
        frame = Gtk.Frame()
        frame.set_vexpand(True)
        frame.set_hexpand(True)
        container.append(frame)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        self.theme_list_box = Gtk.ListBox()
        self.theme_list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.theme_list_box.add_css_class("rich-list")
        self.theme_list_box.connect("row-selected", lambda lb, row: _on_theme_selected(lb, row, self))

        scrolled.set_child(self.theme_list_box)
        frame.set_child(scrolled)

    def _build_simple_config_section(self) -> Gtk.Box:
        """Construit la section de configuration simple (couleurs et fond)."""
        container = Gtk.Box(orientation=VERTICAL, spacing=15)
        container.set_margin_top(10)
        container.set_margin_bottom(10)
        container.set_margin_start(10)
        container.set_margin_end(10)

        # Panneau de configuration simple
        self.simple_config_panel = ThemeSimpleConfigPanel(
            state_manager=self.state_manager,
            on_changed=self._mark_dirty
        )
        container.append(self.simple_config_panel)

        # Aliases attendus par certains tests/anciens appels.
        self.bg_image_entry = self.simple_config_panel.bg_image_entry
        self.normal_fg_combo = self.simple_config_panel.normal_fg_combo
        self.normal_bg_combo = self.simple_config_panel.normal_bg_combo
        self.highlight_fg_combo = self.simple_config_panel.highlight_fg_combo
        self.highlight_bg_combo = self.simple_config_panel.highlight_bg_combo

        # Séparateur
        sep = Gtk.Separator(orientation=HORIZONTAL)
        sep.set_margin_top(15)
        sep.set_margin_bottom(15)
        container.append(sep)

        # Liste des scripts
        self.scripts_list = ThemeScriptsList(
            state_manager=self.state_manager,
            script_service=self.script_service
        )
        # Expose la listbox pour compatibilité avec les tests/anciens appels.
        self.scripts_list_box = self.scripts_list.scripts_list_box
        container.append(self.scripts_list)

        return container

    def _on_select_bg_image(self, button: Gtk.Button) -> None:
        """Ouvre un sélecteur de fichier pour l'image de fond (compat tests)."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Choisir une image de fond")

        filters = Gtk.FileFilter()
        filters.set_name("Images")
        filters.add_mime_type("image/jpeg")
        filters.add_mime_type("image/png")
        filters.add_mime_type("image/tga")
        dialog.set_default_filter(filters)

        parent = GtkHelper.resolve_parent_window(button, fallback=self.parent_window)
        dialog.open(parent, None, self._on_bg_image_selected)

    def _on_bg_image_selected(self, dialog: Gtk.FileDialog, result) -> None:
        """Callback après sélection de l'image (compat tests)."""
        try:
            file = dialog.open_finish(result)
            if file and self.bg_image_entry:
                self.bg_image_entry.set_text(file.get_path())
        except (OSError, RuntimeError) as e:
            logger.warning(f"[TabThemeConfig] Sélection d'image annulée ou échouée: {e}")

    def _on_simple_config_changed(self, *_) -> None:
        """Met à jour le modèle depuis la config simple (compat tests)."""
        if self._updating_ui:
            return

        if not self.bg_image_entry or not self.normal_fg_combo or not self.normal_bg_combo:
            return

        if not self.highlight_fg_combo or not self.highlight_bg_combo:
            return

        bg_image = self.bg_image_entry.get_text()

        n_fg = GRUB_COLORS[self.normal_fg_combo.get_selected()]
        n_bg = GRUB_COLORS[self.normal_bg_combo.get_selected()]
        color_normal = f"{n_fg}/{n_bg}"

        h_fg = GRUB_COLORS[self.highlight_fg_combo.get_selected()]
        h_bg = GRUB_COLORS[self.highlight_bg_combo.get_selected()]
        color_highlight = f"{h_fg}/{h_bg}"

        current_model = self.state_manager.get_model()
        new_model = replace(
            current_model,
            grub_background=bg_image,
            grub_color_normal=color_normal,
            grub_color_highlight=color_highlight,
        )
        self.state_manager.update_model(new_model)
        self._mark_dirty()

    def _build_right_column(self, container: Gtk.Box) -> None:
        """Construit la colonne de droite (actions)."""
        parts = build_theme_config_right_column(
            on_preview=lambda: _on_preview_theme(self),
            on_activate_theme=lambda b: _on_activate_theme(b, self),
            on_deactivate_theme=lambda b: _on_deactivate_theme(b, self),
            on_edit=lambda b: _on_edit_theme(b, self.current_theme.name, self) if self.current_theme else None,
            on_delete=lambda b: _on_delete_theme(b, self.current_theme.name, self) if self.current_theme else None,
            on_open_editor=lambda b: _on_open_editor(self, b),
        )

        self.preview_btn = parts.preview_btn
        self.activate_theme_btn = parts.activate_theme_btn
        self.deactivate_theme_btn = parts.deactivate_theme_btn
        self.edit_btn = parts.edit_btn
        self.delete_btn = parts.delete_btn
        # self.activate_script_btn et self.deactivate_script_btn sont maintenant dans _build_simple_config_section

        container.append(parts.actions_title)
        container.append(parts.actions_box)
        container.append(parts.global_actions_box)

    def _build_switch_section(self) -> Gtk.Widget:
        """Construit la section de switch pour afficher/masquer les thèmes.

        Returns:
            Widget de la section.
        """
        box = Gtk.Box(orientation=HORIZONTAL, spacing=10)
        box.set_margin_bottom(10)

        # Utilisation d'un style "card" ou "box" pour le switch principal
        box.add_css_class("info-box")

        label = Gtk.Label(label="Activer la gestion des thèmes GRUB")
        label.set_markup("<b>Activer la gestion des thèmes GRUB</b>")
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        box.append(label)

        self.theme_switch = Gtk.Switch()
        self.theme_switch.set_halign(Gtk.Align.END)
        self.theme_switch.set_valign(Gtk.Align.CENTER)
        self.theme_switch.connect("notify::active", lambda sw, _p: _on_theme_switch_toggled(sw, _p, self))
        box.append(self.theme_switch)

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
            if self.theme_switch:
                self.theme_switch.set_active(theme_enabled)
                logger.debug(f"[TabThemeConfig.load_themes] Switch mis à {theme_enabled}")

                # Afficher les sections si activé
                if self.theme_sections_container:
                    self.theme_sections_container.set_visible(theme_enabled)
                if self.simple_config_container:
                    self.simple_config_container.set_visible(not theme_enabled)

            # === Charger la config simple ===
            if self.simple_config_panel:
                self.simple_config_panel.update_from_model(model)

            # Charger le thème actif s'il existe
            try:
                active_theme = self.theme_manager.load_active_theme()
                if active_theme:
                    self.current_theme = active_theme
                    logger.debug(f"[TabThemeConfig.load_themes] Thème actif: {active_theme.name}")
            except (OSError, RuntimeError) as e:
                logger.warning(f"[TabThemeConfig.load_themes] Pas de thème actif: {e}")

            # Si le switch est activé, charger les thèmes maintenant
            if theme_enabled:
                self.refresh()

                # Sélectionner le premier thème si disponible
                if self.theme_list_box and len(self.available_themes) > 0:
                    first_row = self.theme_list_box.get_row_at_index(0)
                    if first_row:
                        self.theme_list_box.select_row(first_row)

            logger.debug(f"[TabThemeConfig.load_themes] Switch état: {theme_enabled}")
        except (OSError, RuntimeError) as e:
            logger.error(f"[TabThemeConfig.load_themes] Erreur: {e}")
        finally:
            self._updating_ui = False

    def _load_themes(self) -> None:
        """Alias interne pour compatibilité."""
        self.load_themes()

    def scan_system_themes(self) -> None:
        """Scanne les répertoires système pour trouver les thèmes."""
        self.available_themes.clear()
        self.theme_paths.clear()

        if self.theme_list_box is None:
            return

        # Nettoyer la liste des thèmes dans l'UI
        while True:
            child = self.theme_list_box.get_first_child()
            if child is None:
                break
            self.theme_list_box.remove(child)

        # 1. Ajouter l'option "Aucun"
        from core.models.core_theme_models import GrubTheme
        none_theme = GrubTheme(name="Aucun (GRUB par défaut)")
        self.available_themes[none_theme.name] = none_theme
        self._add_theme_to_list(none_theme, None)

        # 2. Utiliser le service pour scanner les thèmes
        scanned_themes = self.theme_service.scan_system_themes()

        for theme_name, (theme, item) in scanned_themes.items():
            self.available_themes[theme_name] = theme
            self.theme_paths[theme_name] = item
            self._add_theme_to_list(theme, item)

        if len(self.available_themes) == 0:
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
            self.theme_list_box.append(row)

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
            is_custom = self.theme_service.is_theme_custom(theme_path)

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
        self.theme_list_box.append(row)


def _on_activate_theme(_button: Gtk.Button, tab: TabThemeConfig) -> None:
    """Active le thème sélectionné dans le modèle.

    Args:
        _button: Le bouton cliqué.
        tab: L'instance de l'onglet.
    """
    if not tab.current_theme:
        return

    theme_name = tab.current_theme.name
    theme_path = tab.theme_paths.get(theme_name)
    theme_txt = ""
    if theme_path:
        theme_txt = str(theme_path / "theme.txt")

    # Mettre à jour le modèle
    current_model = tab.state_manager.get_model()
    new_model = replace(current_model, grub_theme=theme_txt)

    tab.state_manager.update_model(new_model)
    tab._mark_dirty()

    # Rafraîchir l'UI pour mettre à jour les badges et boutons
    tab.refresh()
    logger.info(f"[_on_activate_theme] Thème activé dans le modèle: {theme_name}")


def _on_deactivate_theme(_button: Gtk.Button, tab: TabThemeConfig) -> None:
    """Désactive le thème (revient à 'Aucun').

    Args:
        _button: Le bouton cliqué.
        tab: L'instance de l'onglet.
    """
    # Mettre à jour le modèle
    current_model = tab.state_manager.get_model()
    new_model = replace(current_model, grub_theme="")

    tab.state_manager.update_model(new_model)
    tab._mark_dirty()

    # Rafraîchir l'UI
    tab.refresh()
    logger.info("[_on_deactivate_theme] Thème désactivé (GRUB par défaut)")


def _on_theme_selected(_list_box: Gtk.ListBox, row: Gtk.ListBoxRow, tab: TabThemeConfig) -> None:
    """Appelé quand un thème est sélectionné.

    Args:
        _list_box: Le widget ListBox.
        row: La ligne sélectionnée.
        tab: L'instance de l'onglet.
    """
    if row is None:
        tab.current_theme = None
        if tab.preview_btn:
            tab.preview_btn.set_sensitive(False)
        if tab.edit_btn:
            tab.edit_btn.set_sensitive(False)
        if tab.delete_btn:
            tab.delete_btn.set_sensitive(False)
        return

    index = row.get_index()
    themes_list = list(tab.available_themes.values())

    if 0 <= index < len(themes_list):
        tab.current_theme = themes_list[index]

        # Activer les boutons d'action
        if tab.preview_btn:
            tab.preview_btn.set_sensitive(tab.current_theme.name != "Aucun (GRUB par défaut)")

        # Vérifier si c'est un thème custom pour activer Edit/Delete
        is_custom = False
        theme_path = None
        if tab.current_theme.name in tab.theme_paths:
            theme_path = tab.theme_paths[tab.current_theme.name]
            is_custom = tab.theme_service.is_theme_custom(theme_path)

        if tab.edit_btn:
            tab.edit_btn.set_sensitive(is_custom)
        if tab.delete_btn:
            tab.delete_btn.set_sensitive(is_custom)

        # Vérifier si c'est le thème actif dans le modèle
        model = tab.state_manager.get_model()
        is_active = False
        if theme_path:
            theme_txt_path = theme_path / "theme.txt"
            is_active = str(theme_txt_path) == model.grub_theme
        elif tab.current_theme.name == "Aucun (GRUB par défaut)":
            is_active = not model.grub_theme

        if tab.activate_theme_btn:
            tab.activate_theme_btn.set_sensitive(not is_active)
        if tab.deactivate_theme_btn:
            tab.deactivate_theme_btn.set_sensitive(is_active and tab.current_theme.name != "Aucun (GRUB par défaut)")

        logger.debug(f"[_on_theme_selected] Thème: {tab.current_theme.name} (Custom: {is_custom}, Active: {is_active})")


def _on_theme_switch_toggled(switch: Gtk.Switch, _param: Any, tab: TabThemeConfig) -> None:
    """Appelé quand le switch d'affichage est basculé.

    Args:
        switch: Le widget Switch.
        _param: Paramètre ignoré.
        tab: L'instance de l'onglet.
    """
    if tab.state_manager.is_loading() or getattr(tab, "_updating_switch", False):
        return

    is_active = switch.get_active()
    logger.info(f"[_on_theme_switch_toggled] Switch basculé: {is_active}")

    # Mettre à jour le modèle
    current_model = tab.state_manager.get_model()
    if current_model.theme_management_enabled != is_active:
        new_model = replace(current_model, theme_management_enabled=is_active)
        tab.state_manager.update_model(new_model)
        tab._mark_dirty()

    # Afficher/masquer les sections
    if tab.theme_sections_container:
        tab.theme_sections_container.set_visible(is_active)
    if tab.simple_config_container:
        tab.simple_config_container.set_visible(not is_active)

    # Recharger l'interface pour refléter le nouveau mode et les valeurs
    # Cela gère la visibilité et le peuplement des widgets
    tab.load_themes()

    logger.debug(f"[_on_theme_switch_toggled] Sections {'affichées' if is_active else 'masquées'}, Modèle mis à jour")


def _scan_grub_scripts(tab: TabThemeConfig) -> None:
    """Scanne et affiche les scripts GRUB.

    Conservé pour compatibilité avec les tests: la logique est déléguée au composant
    `ThemeScriptsList`.

    Args:
        tab: L'instance de l'onglet.
    """
    list_box: Gtk.ListBox | None = getattr(tab, "scripts_list_box", None)
    if list_box is None and getattr(tab, "scripts_list", None):
        list_box = tab.scripts_list.scripts_list_box
        tab.scripts_list_box = list_box

    if list_box is None:
        return

    # Nettoyer l'affichage précédent (compatible mocks tests).
    while True:
        child = list_box.get_first_child()
        if child is None:
            break
        list_box.remove(child)

    # Source des scripts: soit via le service de l'onglet (tests), soit via le composant.
    script_service = getattr(tab, "script_service", None)
    if script_service is None and getattr(tab, "scripts_list", None):
        script_service = tab.scripts_list.script_service

    if script_service is None:
        return

    logger.debug("[_scan_grub_scripts] Scan des scripts GRUB")
    theme_scripts = script_service.scan_theme_scripts()

    if not theme_scripts:
        return

    for script in theme_scripts:
        row = Gtk.ListBoxRow()
        row.set_selectable(False)

        script_box = Gtk.Box(orientation=HORIZONTAL, spacing=10)
        script_box.set_margin_top(8)
        script_box.set_margin_bottom(8)
        script_box.set_margin_start(10)
        script_box.set_margin_end(10)

        is_executable = getattr(script, "is_executable", False)
        is_pending = False

        pending_changes = getattr(tab.state_manager, "pending_script_changes", {})
        script_path = getattr(script, "path", None)
        if script_path in pending_changes:
            is_executable = pending_changes[script_path]
            is_pending = True

        script_name = getattr(script, "name", "")
        if script_name in ["05_debian_theme", "05_grub_colors"]:
            script_name += " (Défaut)"
        if is_pending:
            script_name += " *"

        name_label = Gtk.Label(label=script_name)
        name_label.set_halign(Gtk.Align.START)
        name_label.set_hexpand(True)
        name_label.add_css_class("title-4")
        script_box.append(name_label)

        state_label = Gtk.Label(label="actif" if is_executable else "inactif")
        state_label.set_margin_end(10)
        if not is_executable:
            state_label.add_css_class("warning")
        script_box.append(state_label)

        switch = Gtk.Switch()
        switch.set_active(is_executable)
        switch.set_valign(Gtk.Align.CENTER)
        switch.connect(
            "notify::active",
            lambda s, _p, sc=script, lbl=state_label: _on_script_switch_toggled(s, sc, tab, lbl),
        )
        script_box.append(switch)

        row.set_child(script_box)
        list_box.append(row)


def _on_script_switch_toggled(
    switch: Gtk.Switch,
    script: Any,
    tab: TabThemeConfig,
    label: Gtk.Label | None = None,
) -> None:
    """Callback switch script (compat tests).

    Args:
        switch: Le switch basculé.
        script: Objet script (doit exposer `path`, `name`, `is_executable`).
        tab: L'instance de l'onglet.
        label: Label d'état optionnel.
    """
    if tab.scripts_list:
        tab.scripts_list._on_script_switch_toggled(switch, script, label)  # pylint: disable=protected-access
        return

    # Fallback minimal si le composant n'est pas initialisé.
    if tab.state_manager.is_loading():
        return

    is_active = switch.get_active()
    if label:
        label.set_label("actif" if is_active else "inactif")
        if is_active:
            label.remove_css_class("warning")
        else:
            label.add_css_class("warning")

    tab.state_manager.pending_script_changes[script.path] = is_active
    if getattr(script, "is_executable", None) == is_active:
        tab.state_manager.pending_script_changes.pop(script.path, None)

    model = tab.state_manager.get_model() if hasattr(tab.state_manager, "get_model") else None
    try:
        if model is not None:
            tab.state_manager.update_model(model)
        else:
            tab.state_manager.update_model()
    except TypeError:
        tab.state_manager.update_model()


def _on_open_editor(tab: TabThemeConfig, button: Gtk.Button | None = None) -> None:
    """Ouvre le générateur interactif de thème dans une fenêtre séparée.

    Args:
        tab: L'instance de l'onglet.
        button: Le bouton cliqué (optionnel).
    """
    try:
        # On cherche la fenêtre parente si elle n'est pas définie
        if not tab.parent_window:
            tab.parent_window = GtkHelper.resolve_parent_window(button, fallback=tab.parent_window)

        if tab.parent_window:
            def _on_theme_created(name: str, package: dict[str, Any]) -> None:
                """Callback appelé quand un thème est créé."""
                try:
                    import shutil
                    from core.config.core_paths import get_grub_themes_dir  # pylint: disable=import-outside-toplevel
                    
                    themes_dir = get_grub_themes_dir()
                    theme_path = themes_dir / name
                    
                    # Créer le dossier du thème
                    theme_path.mkdir(parents=True, exist_ok=True)
                    
                    # Écrire le fichier theme.txt
                    (theme_path / "theme.txt").write_text(package["theme.txt"], encoding="utf-8")
                    
                    # Copier les assets
                    assets = package.get("assets", {})
                    for target_name, source_path in assets.items():
                        try:
                            src = Path(source_path)
                            if not src.exists():
                                logger.warning(f"Asset non trouvé: {source_path}")
                                continue
                                
                            dst = theme_path / target_name
                            if src.is_dir():
                                if dst.exists():
                                    shutil.rmtree(dst)
                                shutil.copytree(src, dst)
                            else:
                                shutil.copy(src, dst)
                            logger.debug(f"Asset copié: {target_name}")
                        except Exception as e:
                            logger.error(f"Erreur lors de la copie de l'asset {target_name}: {e}")

                    logger.info(f"Thème '{name}' créé avec succès dans {theme_path}")
                    
                    # Rafraîchir la liste des thèmes
                    tab.scan_system_themes()
                    
                except (OSError, PermissionError) as e:
                    logger.error(f"Erreur lors de la création du thème: {e}")
                    create_error_dialog(f"Erreur lors de la création du thème:\n{e}")

            win = InteractiveThemeGeneratorWindow(
                parent_window=tab.parent_window,
                on_theme_created=_on_theme_created
            )

            # Conserver une référence Python pour éviter une destruction prématurée (fermeture immédiate).
            tab._interactive_theme_generator_window = win  # type: ignore[attr-defined]

            def _on_close(_widget) -> bool:
                try:
                    delattr(tab, "_interactive_theme_generator_window")
                except Exception:
                    pass
                return False

            win.connect("close-request", _on_close)
            win.present()
            logger.info("[_on_open_editor] Générateur de thème ouvert")
        else:
            logger.error("[_on_open_editor] Fenêtre parente introuvable")
            create_error_dialog("Impossible d'ouvrir l'éditeur")
    except (OSError, RuntimeError) as e:
        logger.error(f"[_on_open_editor] Erreur: {e}")
        create_error_dialog(f"Erreur lors de l'ouverture de l'éditeur:\n{e}")


def _on_preview_theme(tab: TabThemeConfig) -> None:
    """Ouvre le dialog de prévisualisation du thème.

    Args:
        tab: L'instance de l'onglet.
    """
    model = tab.state_manager.get_model()
    theme = tab.current_theme
    
    # Si pas de thème sélectionné mais qu'on est en mode thème, erreur
    if theme is None and model.theme_management_enabled:
        create_error_dialog("Veuillez sélectionner un thème")
        return

    # Si pas de thème (mode simple), on crée un objet thème vide pour le dialog
    if theme is None:
        theme = GrubTheme(name="Configuration Simple")

    try:
        dialog = GrubPreviewDialog(theme, model=model)
        dialog.show()
        logger.debug(f"[_on_preview_theme] Aperçu: {theme.name}")
    except (OSError, RuntimeError) as e:
        logger.error(f"[_on_preview_theme] Erreur: {e}")
        create_error_dialog(f"Erreur lors de l'aperçu:\n{e}")


def _on_edit_theme(_button: Gtk.Button | None, theme_name: str, tab: TabThemeConfig) -> None:
    """Ouvre l'éditeur pour modifier un thème custom.

    Args:
        _button: Le bouton cliqué (optionnel).
        theme_name: Nom du thème à modifier.
        tab: L'instance de l'onglet.
    """
    try:
        tab.parent_window = GtkHelper.resolve_parent_window(_button, fallback=tab.parent_window)

        if theme_name not in tab.available_themes:
            create_error_dialog(f"Thème '{theme_name}' introuvable")
            return

        theme_path = tab.theme_paths.get(theme_name)
        if not theme_path or not tab.theme_service.is_theme_custom(theme_path):
            create_error_dialog("Ce thème système ne peut pas être modifié")
            return

        if tab.parent_window:
            # Ouvrir le nouveau générateur interactif
            
            # Pour l'instant, on ouvre le générateur vide (le nouveau générateur ne supporte pas encore l'édition)
            # Mais on respecte la demande de l'utilisateur d'utiliser le nouveau générateur.
            win = InteractiveThemeGeneratorWindow(
                parent_window=tab.parent_window,
                on_theme_created=lambda name, pkg: tab.scan_system_themes()
            )
            
            # Conserver une référence
            tab._interactive_theme_generator_window = win  # type: ignore[attr-defined]
            win.present()
            logger.info(f"[_on_edit_theme] Nouveau générateur ouvert pour '{theme_name}'")
        else:
            logger.error("[_on_edit_theme] Fenêtre parente introuvable")
            create_error_dialog("Impossible d'ouvrir l'éditeur")

    except (OSError, RuntimeError) as e:
        logger.error(f"[_on_edit_theme] Erreur: {e}")
        create_error_dialog(f"Erreur lors de l'ouverture de l'éditeur:\n{e}")


def _on_delete_theme(_button: Gtk.Button | None, theme_name: str, tab: TabThemeConfig) -> None:
    """Supprime un thème custom après confirmation.

    Args:
        _button: Le bouton cliqué (optionnel).
        theme_name: Nom du thème à supprimer.
        tab: L'instance de l'onglet.
    """
    try:
        tab.parent_window = GtkHelper.resolve_parent_window(_button, fallback=tab.parent_window)

        if theme_name not in tab.available_themes:
            create_error_dialog(f"Thème '{theme_name}' introuvable")
            return

        theme_path = tab.theme_paths.get(theme_name)
        if not theme_path or not tab.theme_service.is_theme_custom(theme_path):
            create_error_dialog("Les thèmes système ne peuvent pas être supprimés")
            return

        # Demander confirmation
        dialog = Gtk.AlertDialog()
        dialog.set_message(f"Supprimer le thème '{theme_name}' ?")
        dialog.set_detail(
            f"Cette action supprimera définitivement le répertoire:\n{theme_path}\n\n" "Cette action est irréversible."
        )
        dialog.set_buttons(["Annuler", "Supprimer"])
        dialog.set_default_button(0)
        dialog.set_cancel_button(0)

        # On a besoin d'un parent pour le dialogue
        parent = GtkHelper.resolve_parent_window(_button, fallback=tab.parent_window)

        dialog.choose(
            parent=parent,
            cancellable=None,
            callback=_on_delete_confirmed,
            user_data=(theme_name, theme_path, tab),
        )

    except (OSError, RuntimeError) as e:
        logger.error(f"[_on_delete_theme] Erreur: {e}")
        create_error_dialog(f"Erreur lors de la suppression:\n{e}")


def _on_delete_confirmed(dialog: Gtk.AlertDialog, result, user_data: tuple) -> None:
    """Appelé après la confirmation de suppression.

    Args:
        dialog: Le dialogue de confirmation.
        result: Résultat du dialogue.
        user_data: Tuple (theme_name, theme_path, tab).
    """
    try:
        choice = dialog.choose_finish(result)

        if choice == 1:  # Supprimer
            theme_name, theme_path, tab = user_data

            # Utiliser le service pour supprimer le thème
            if tab.theme_service.delete_theme(theme_path):
                logger.info(f"[_on_delete_confirmed] Thème supprimé: {theme_name}")
                create_success_dialog(f"Thème '{theme_name}' supprimé avec succès")
            else:
                logger.error(f"[_on_delete_confirmed] Échec suppression: {theme_name}")
                create_error_dialog(f"Impossible de supprimer le thème '{theme_name}'")

            # Recharger la liste des thèmes
            tab.scan_system_themes()

    except (OSError, RuntimeError) as e:
        logger.error(f"[_on_delete_confirmed] Erreur: {e}")
        create_error_dialog(f"Erreur lors de la suppression:\n{e}")
