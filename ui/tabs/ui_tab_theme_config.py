"""Onglet de configuration du thème GRUB."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gi.repository import Gtk
from loguru import logger

from core.config.core_paths import get_all_grub_themes_dirs as _get_all_grub_themes_dirs
from core.core_exceptions import GrubCommandError, GrubScriptNotFoundError
from core.services.core_grub_script_service import GrubScriptService
from core.services.core_theme_service import ThemeService
from core.theme.core_active_theme_manager import ActiveThemeManager
from core.theme.core_theme_generator import GrubTheme
from core.theme.core_theme_generator import create_custom_theme as _create_custom_theme
from ui.components.ui_theme_config_actions import build_theme_config_right_column
from ui.tabs.ui_grub_preview_dialog import GrubPreviewDialog
from ui.tabs.ui_theme_editor_dialog import ThemeEditorDialog
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

    def __init__(self, state_manager: Any) -> None:
        """Initialise l'onglet de configuration de thème.

        Args:
            state_manager: Gestionnaire d'état global.
        """
        self.state_manager = state_manager
        self.current_theme: GrubTheme | None = None
        self.theme_manager = ActiveThemeManager()
        self.script_service = GrubScriptService()
        self.theme_service = ThemeService()
        self.available_themes: dict[str, GrubTheme] = {}
        self.theme_paths: dict[str, Path] = {}  # Pour stocker le chemin de chaque thème
        self.parent_window: Gtk.Window | None = None
        self._ignore_switch_signal = False

        # Widgets
        self.theme_list_box: Gtk.ListBox | None = None
        self.activate_btn: Gtk.Button | None = None
        self.preview_btn: Gtk.Button | None = None
        self.edit_btn: Gtk.Button | None = None
        self.delete_btn: Gtk.Button | None = None
        self.theme_switch: Gtk.Switch | None = None
        self.scripts_info_box: Gtk.Box | None = None

        # Sections à afficher/masquer avec le switch
        self.theme_sections_container: Gtk.Box | None = None

        logger.debug("[TabThemeConfig.__init__] Onglet initialisé")

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

        # Conteneur pour toutes les sections de thèmes (masquable)
        self.theme_sections_container, left_section, right_section = create_two_column_layout(main_box)

        self._build_left_column(left_section)
        self._build_right_column(right_section)

        # Initialement masqué
        self.theme_sections_container.set_visible(False)

        # Charger les thèmes
        self._load_themes()

        return main_box

    def refresh(self) -> None:
        """Rafraîchit l'affichage des scripts et des thèmes."""
        _scan_grub_scripts(self)
        self._scan_system_themes()

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

        self.scripts_info_box = Gtk.Box(orientation=VERTICAL, spacing=8)
        container.append(self.scripts_info_box)

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

    def _build_right_column(self, container: Gtk.Box) -> None:
        """Construit la colonne de droite (actions)."""
        parts = build_theme_config_right_column(
            on_activate=lambda: _on_activate_theme(self),
            on_preview=lambda: _on_preview_theme(self),
            on_edit=lambda b: _on_edit_theme(b, self.current_theme.name, self) if self.current_theme else None,
            on_delete=lambda b: _on_delete_theme(b, self.current_theme.name, self) if self.current_theme else None,
            on_open_editor=lambda b: _on_open_editor(self, b),
        )

        self.activate_btn = parts.activate_btn
        self.preview_btn = parts.preview_btn
        self.edit_btn = parts.edit_btn
        self.delete_btn = parts.delete_btn

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

    def _load_themes(self) -> None:
        """Charge la liste des thèmes disponibles."""
        try:
            # Vérifier d'abord si un thème est réellement configuré dans GRUB
            grub_theme_enabled = self.theme_service.is_theme_enabled_in_grub()

            # Définir l'état du switch selon la configuration GRUB réelle
            if self.theme_switch:
                # Bloquer temporairement le signal pour éviter de déclencher le scan
                # Note: On ne peut plus utiliser handler_block_by_func avec une lambda
                # On va utiliser une propriété temporaire pour ignorer le signal
                self._ignore_switch_signal = True
                self.theme_switch.set_active(grub_theme_enabled)
                self._ignore_switch_signal = False

                # Afficher les sections si un thème est configuré
                if self.theme_sections_container:
                    self.theme_sections_container.set_visible(grub_theme_enabled)

            # Charger le thème actif s'il existe
            try:
                active_theme = self.theme_manager.load_active_theme()
                if active_theme:
                    self.current_theme = active_theme
                    logger.debug(f"[TabThemeConfig._load_themes] Thème actif: {active_theme.name}")
            except (OSError, RuntimeError) as e:
                logger.warning(f"[TabThemeConfig._load_themes] Pas de thème actif: {e}")

            # Si le switch est activé, charger les thèmes maintenant
            if grub_theme_enabled:
                self.refresh()

                # Sélectionner le premier thème si disponible
                if self.theme_list_box and len(self.available_themes) > 0:
                    first_row = self.theme_list_box.get_row_at_index(0)
                    if first_row:
                        self.theme_list_box.select_row(first_row)

            logger.debug(f"[TabThemeConfig._load_themes] Switch état: {grub_theme_enabled}")

        except (OSError, RuntimeError) as e:
            logger.error(f"[TabThemeConfig._load_themes] Erreur: {e}")

    def _scan_system_themes(self) -> None:
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

        # Utiliser le service pour scanner les thèmes
        scanned_themes = self.theme_service.scan_system_themes()

        for theme_name, (theme, item) in scanned_themes.items():
            self.available_themes[theme_name] = theme
            self.theme_paths[theme_name] = item
            self._add_theme_to_list(theme, item)

        if len(self.available_themes) == 0:
            logger.warning("[TabThemeConfig._scan_system_themes] Aucun thème valide trouvé")
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

    def _add_theme_to_list(self, theme: GrubTheme, theme_path: Path) -> None:
        """Ajoute un thème à la liste.

        Args:
            theme: Thème à ajouter.
            theme_path: Chemin du répertoire du thème.
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
        icon_label.set_margin_end(8)
        content_box.append(icon_label)

        # Nom du thème
        theme_label = Gtk.Label(label=theme.name or "Thème sans nom")
        theme_label.set_halign(Gtk.Align.START)
        theme_label.set_hexpand(True)
        theme_label.add_css_class("title-4")
        content_box.append(theme_label)

        # Vérifier si le thème est modifiable
        is_custom = self.theme_service.is_theme_custom(theme_path)

        # Badge pour les thèmes système
        if not is_custom:
            system_badge = Gtk.Label(label="Système")
            system_badge.add_css_class("dim-label")
            system_badge.set_margin_end(10)
            content_box.append(system_badge)
        else:
            custom_badge = Gtk.Label(label="Custom")
            custom_badge.add_css_class("success")
            custom_badge.set_margin_end(10)
            content_box.append(custom_badge)

        row.set_child(content_box)
        self.theme_list_box.append(row)


def _on_theme_selected(_list_box: Gtk.ListBox, row: Gtk.ListBoxRow, tab: TabThemeConfig) -> None:
    """Appelé quand un thème est sélectionné.

    Args:
        _list_box: Le widget ListBox.
        row: La ligne sélectionnée.
        tab: L'instance de l'onglet.
    """
    if row is None:
        tab.current_theme = None
        if tab.activate_btn:
            tab.activate_btn.set_sensitive(False)
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
        if tab.activate_btn:
            tab.activate_btn.set_sensitive(True)
        if tab.preview_btn:
            tab.preview_btn.set_sensitive(tab.current_theme.name != "Aucun (GRUB par défaut)")

        # Vérifier si c'est un thème custom pour activer Edit/Delete
        is_custom = False
        if tab.current_theme.name in tab.theme_paths:
            theme_path = tab.theme_paths[tab.current_theme.name]
            is_custom = tab.theme_service.is_theme_custom(theme_path)

        if tab.edit_btn:
            tab.edit_btn.set_sensitive(is_custom)
        if tab.delete_btn:
            tab.delete_btn.set_sensitive(is_custom)

        logger.debug(f"[_on_theme_selected] Thème: {tab.current_theme.name} (Custom: {is_custom})")


def _on_theme_switch_toggled(switch: Gtk.Switch, _param: Any, tab: TabThemeConfig) -> None:
    """Appelé quand le switch d'affichage est basculé.

    Args:
        switch: Le widget Switch.
        _param: Paramètre ignoré.
        tab: L'instance de l'onglet.
    """
    is_active = switch.get_active()

    # Afficher/masquer les sections de configuration des thèmes
    if tab.theme_sections_container:
        tab.theme_sections_container.set_visible(is_active)

    if is_active:
        # Quand on affiche, rafraîchir les données
        tab.refresh()

        # Sélectionner le premier thème si disponible
        if tab.theme_list_box and len(tab.available_themes) > 0:
            first_row = tab.theme_list_box.get_row_at_index(0)
            if first_row:
                tab.theme_list_box.select_row(first_row)

    logger.debug(f"[_on_theme_switch_toggled] Sections {'affichées' if is_active else 'masquées'}")


def _scan_grub_scripts(tab: TabThemeConfig) -> None:
    """Scanne /etc/grub.d/ pour détecter les scripts de thème.

    Args:
        tab: L'instance de l'onglet.
    """
    if tab.scripts_info_box is None:
        return

    # Nettoyer l'affichage précédent
    while True:
        child = tab.scripts_info_box.get_first_child()
        if child is None:
            break
        tab.scripts_info_box.remove(child)

    logger.debug("[_scan_grub_scripts] Scan des scripts GRUB")

    # Utiliser le service pour scanner les scripts
    theme_scripts = tab.script_service.scan_theme_scripts()

    if theme_scripts:
        logger.info(f"[_scan_grub_scripts] {len(theme_scripts)} script(s) de thème trouvé(s)")

        # Afficher les scripts dans l'interface
        for script in theme_scripts:
            script_row = Gtk.Box(orientation=HORIZONTAL, spacing=10)
            script_row.set_margin_start(10)
            script_row.set_margin_bottom(5)

            # Icône de statut
            status_icon = "✓" if script.is_executable else "⚠"
            status_label = Gtk.Label(label=status_icon)
            script_row.append(status_label)

            # Nom du script
            name_label = Gtk.Label(label=script.name)
            name_label.set_halign(Gtk.Align.START)
            name_label.set_hexpand(True)
            script_row.append(name_label)

            # État
            state_text = "actif" if script.is_executable else "inactif"
            state_label = Gtk.Label(label=state_text)
            state_label.set_halign(Gtk.Align.END)
            if not script.is_executable:
                state_label.add_css_class("warning")
            script_row.append(state_label)

            # Bouton d'activation si inactif
            if not script.is_executable:
                activate_script_btn = Gtk.Button(label="Activer")
                activate_script_btn.connect("clicked", lambda b, p=str(script.path): _on_activate_script(b, p, tab))
                script_row.append(activate_script_btn)

            tab.scripts_info_box.append(script_row)


def _on_activate_script(_button: Gtk.Button, script_path: str, tab: TabThemeConfig) -> None:
    """Active un script GRUB en le rendant exécutable.

    Args:
        _button: Le bouton cliqué.
        script_path: Chemin du script à activer.
        tab: L'instance de l'onglet.
    """
    try:
        # Utiliser le service au lieu de subprocess direct
        success = tab.script_service.make_executable(Path(script_path))

        if success:
            logger.info(f"[_on_activate_script] Script activé: {script_path}")
            create_success_dialog(
                f"Script activé: {Path(script_path).name}\nRelancez le scan pour voir les changements."
            )

            # Relancer le scan
            tab.refresh()
        else:
            logger.error(f"[_on_activate_script] Échec de l'activation: {script_path}")
            create_error_dialog(f"Impossible d'activer le script:\n{Path(script_path).name}")

    except GrubCommandError as e:
        logger.error(f"[_on_activate_script] Erreur commande: {e}")
        create_error_dialog(f"Erreur lors de l'activation:\n{e}")

    except GrubScriptNotFoundError as e:
        logger.error(f"[_on_activate_script] Script introuvable: {e}")
        create_error_dialog(f"Script introuvable:\n{e}")

    except PermissionError as e:
        logger.error(f"[_on_activate_script] Permission refusée: {e}")
        create_error_dialog(f"Permission refusée:\n{e}\nNécessite les privilèges root")

    except OSError as e:
        logger.error(f"[_on_activate_script] Erreur inattendue: {e}")
        create_error_dialog(f"Erreur inattendue:\n{e}")


def _on_open_editor(tab: TabThemeConfig, button: Gtk.Button | None = None) -> None:
    """Ouvre l'éditeur de thème dans une fenêtre séparée.

    Args:
        tab: L'instance de l'onglet.
        button: Le bouton cliqué (optionnel).
    """
    try:
        # On cherche la fenêtre parente si elle n'est pas définie
        if not tab.parent_window:
            tab.parent_window = GtkHelper.resolve_parent_window(button, fallback=tab.parent_window)

        if tab.parent_window:
            editor_dialog = ThemeEditorDialog(tab.parent_window, tab.state_manager)
            editor_dialog.present()
            logger.info("[_on_open_editor] Éditeur de thème ouvert")
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
    if tab.current_theme is None:
        create_error_dialog("Veuillez sélectionner un thème")
        return

    try:
        dialog = GrubPreviewDialog(tab.current_theme)
        dialog.show()
        logger.debug(f"[_on_preview_theme] Aperçu: {tab.current_theme.name}")
    except (OSError, RuntimeError) as e:
        logger.error(f"[_on_preview_theme] Erreur: {e}")
        create_error_dialog(f"Erreur lors de l'aperçu:\n{e}")


def _on_activate_theme(tab: TabThemeConfig) -> None:
    """Marque le thème sélectionné comme actif (sera appliqué avec le bouton global).

    Args:
        tab: L'instance de l'onglet.
    """
    if tab.current_theme is None:
        create_error_dialog("Veuillez sélectionner un thème")
        return

    try:
        logger.debug(f"[_on_activate_theme] Sélection: {tab.current_theme.name}")

        # Assigner et sauvegarder le thème actif (en cache local)
        tab.theme_manager.active_theme = tab.current_theme
        tab.theme_manager.save_active_theme()

        # Marquer comme modifié pour activer le bouton "Appliquer" global
        if hasattr(tab.state_manager, "mark_dirty"):
            tab.state_manager.mark_dirty()
            logger.debug("[_on_activate_theme] État marqué comme modifié")

        create_success_dialog(
            f"Thème '{tab.current_theme.name}' sélectionné.\n\n"
            f"Cliquez sur 'Appliquer' pour appliquer les changements."
        )
        logger.info(f"[_on_activate_theme] ✓ Thème sélectionné: {tab.current_theme.name}")
    except (OSError, RuntimeError) as e:
        logger.error(f"[_on_activate_theme] Erreur: {e}")
        create_error_dialog(f"Erreur lors de la sélection:\n{e}")


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
            # Ouvrir l'éditeur avec le thème chargé
            editor_dialog = ThemeEditorDialog(tab.parent_window, tab.state_manager)
            # Note: Chargement du thème dans l'éditeur se fait via state_manager
            editor_dialog.present()
            logger.info(f"[_on_edit_theme] Éditeur ouvert pour '{theme_name}'")
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
        parent = tab.parent_window
        if not parent and _button:
            parent = _button.get_root()

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
            tab._scan_system_themes()

    except (OSError, RuntimeError) as e:
        logger.error(f"[_on_delete_confirmed] Erreur: {e}")
        create_error_dialog(f"Erreur lors de la suppression:\n{e}")
