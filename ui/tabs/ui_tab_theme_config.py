"""Onglet de configuration du thème GRUB."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gi.repository import Gtk
from loguru import logger

from core.config.core_paths import get_all_grub_themes_dirs
from core.core_exceptions import GrubCommandError, GrubScriptNotFoundError
from core.services.core_grub_script_service import GrubScriptService
from core.theme.core_active_theme_manager import ActiveThemeManager
from core.theme.core_theme_generator import GrubTheme, create_custom_theme
from ui.tabs.ui_grub_preview_dialog import GrubPreviewDialog
from ui.tabs.ui_theme_editor_dialog import ThemeEditorDialog
from ui.ui_widgets import create_error_dialog, create_main_box, create_success_dialog

HORIZONTAL = Gtk.Orientation.HORIZONTAL
VERTICAL = Gtk.Orientation.VERTICAL


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
        self.available_themes: dict[str, GrubTheme] = {}
        self.parent_window: Gtk.Window | None = None

        # Widgets
        self.theme_list_box: Gtk.ListBox | None = None
        self.activate_btn: Gtk.Button | None = None
        self.preview_btn: Gtk.Button | None = None
        self.theme_switch: Gtk.Switch | None = None
        self.scripts_info_box: Gtk.Box | None = None

        logger.debug("[TabThemeConfig.__init__] Onglet initialisé")

    def build(self) -> Gtk.Box:
        """Construit l'interface utilisateur de l'onglet.

        Returns:
            Widget racine de l'onglet.
        """
        main_box = create_main_box(spacing=15, margin=15)

        # En-tête
        header = Gtk.Label(label="Configuration des thèmes GRUB")
        header.add_css_class("title-2")
        header.set_halign(Gtk.Align.START)
        main_box.append(header)

        # Section: Switch activation thème
        switch_section = self._build_switch_section()
        main_box.append(switch_section)

        # Séparateur
        separator = Gtk.Separator(orientation=HORIZONTAL)
        main_box.append(separator)

        # Section: Info scripts
        self.scripts_info_box = Gtk.Box(orientation=VERTICAL, spacing=8)
        main_box.append(self.scripts_info_box)

        # Section: Liste des thèmes
        list_section = self._build_theme_list_section()
        main_box.append(list_section)

        # Section: Actions
        actions_section = self._build_actions_section()
        main_box.append(actions_section)

        # Charger les thèmes
        self._load_themes()

        return main_box

    def _build_switch_section(self) -> Gtk.Widget:
        """Construit la section de switch pour activer/désactiver les thèmes.

        Returns:
            Widget de la section.
        """
        box = Gtk.Box(orientation=HORIZONTAL, spacing=10)
        box.set_margin_bottom(10)

        label = Gtk.Label(label="Utiliser un thème GRUB personnalisé :")
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        box.append(label)

        self.theme_switch = Gtk.Switch()
        self.theme_switch.set_halign(Gtk.Align.END)
        self.theme_switch.connect("notify::active", self._on_theme_switch_toggled)
        box.append(self.theme_switch)

        return box

    def _build_theme_list_section(self) -> Gtk.Widget:
        """Construit la section de liste des thèmes.

        Returns:
            Widget de la section.
        """
        box = create_main_box(spacing=10, margin=0)

        label = Gtk.Label(label="Thèmes disponibles :")
        label.set_halign(Gtk.Align.START)
        box.append(label)

        # Scrolled window pour la liste
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_min_content_height(250)

        self.theme_list_box = Gtk.ListBox()
        self.theme_list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.theme_list_box.connect("row-selected", self._on_theme_selected)

        scrolled.set_child(self.theme_list_box)
        box.append(scrolled)

        return box

    def _build_actions_section(self) -> Gtk.Widget:
        """Construit la section des actions (boutons).

        Returns:
            Widget de la section.
        """
        box = create_main_box(spacing=10, margin=0)
        box.set_orientation(HORIZONTAL)
        box.set_halign(Gtk.Align.END)

        # Bouton Éditeur de thème
        editor_btn = Gtk.Button(label="Éditeur de thème")
        editor_btn.connect("clicked", self._on_open_editor)
        box.append(editor_btn)

        self.preview_btn = Gtk.Button(label="Aperçu")
        self.preview_btn.set_sensitive(False)
        self.preview_btn.connect("clicked", self._on_preview_theme)
        box.append(self.preview_btn)

        self.activate_btn = Gtk.Button(label="Activer")
        self.activate_btn.set_sensitive(False)
        self.activate_btn.add_css_class("suggested-action")
        self.activate_btn.connect("clicked", self._on_activate_theme)
        box.append(self.activate_btn)

        return box

    def _load_themes(self) -> None:
        """Charge la liste des thèmes disponibles."""
        try:
            # Charger le thème actif s'il existe
            try:
                active_theme = self.theme_manager.load_active_theme()
                if active_theme:
                    self.current_theme = active_theme
                    self.theme_switch.set_active(True)
                    logger.debug(f"[TabThemeConfig._load_themes] Thème actif: {active_theme.name}")
                    # Scanner les thèmes et scripts quand le switch est actif
                    self._scan_system_themes()
                else:
                    self.theme_switch.set_active(False)
            except (OSError, RuntimeError) as e:
                logger.warning(f"[TabThemeConfig._load_themes] Pas de thème actif: {e}")
                self.theme_switch.set_active(False)

            logger.debug(f"[TabThemeConfig._load_themes] {len(self.available_themes)} thèmes trouvés")

        except (OSError, RuntimeError) as e:
            logger.error(f"[TabThemeConfig._load_themes] Erreur: {e}")

    def _scan_system_themes(self) -> None:
        """Scanne les répertoires système pour trouver les thèmes."""
        self.available_themes.clear()

        if self.theme_list_box is None:
            return

        # Nettoyer la liste des thèmes dans l'UI
        while True:
            child = self.theme_list_box.get_first_child()
            if child is None:
                break
            self.theme_list_box.remove(child)

        # Scanner uniquement les répertoires de thèmes système
        for theme_dir in get_all_grub_themes_dirs():
            if not theme_dir.exists():
                logger.debug(f"[TabThemeConfig._scan_system_themes] Répertoire inexistant: {theme_dir}")
                continue

            logger.debug(f"[TabThemeConfig._scan_system_themes] Scan de {theme_dir}")
            for item in theme_dir.iterdir():
                if item.is_dir() and (item / "theme.txt").exists():
                    # Uniquement les répertoires avec theme.txt
                    theme_name = item.name
                    try:
                        # Créer un thème minimal avec les paramètres du répertoire
                        theme = create_custom_theme(theme_name)
                        self.available_themes[theme_name] = theme
                        self._add_theme_to_list(theme)
                        logger.debug(f"[TabThemeConfig._scan_system_themes] Thème trouvé: {theme_name}")
                    except (OSError, ValueError) as e:
                        logger.warning(f"[TabThemeConfig._scan_system_themes] Erreur pour {theme_name}: {e}")

        if len(self.available_themes) == 0:
            logger.warning("[TabThemeConfig._scan_system_themes] Aucun thème système trouvé")
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

    def _add_theme_to_list(self, theme: GrubTheme) -> None:
        """Ajoute un thème à la liste avec bouton Aperçu.

        Args:
            theme: Thème à ajouter.
        """
        row = Gtk.ListBoxRow()

        # Contenu de la ligne
        content_box = Gtk.Box(orientation=HORIZONTAL, spacing=10)
        content_box.set_margin_top(8)
        content_box.set_margin_bottom(8)
        content_box.set_margin_start(10)
        content_box.set_margin_end(10)

        # Nom du thème
        theme_label = Gtk.Label(label=theme.name or "Thème sans nom")
        theme_label.set_halign(Gtk.Align.START)
        theme_label.set_hexpand(True)
        content_box.append(theme_label)

        row.set_child(content_box)
        self.theme_list_box.append(row)

    def _on_theme_selected(self, _list_box: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        """Appelé quand un thème est sélectionné.

        Args:
            _list_box: Le widget ListBox.
            row: La ligne sélectionnée.
        """
        if row is None:
            self.current_theme = None
            self.activate_btn.set_sensitive(False)
            self.preview_btn.set_sensitive(False)
            return

        index = row.get_index()
        themes_list = list(self.available_themes.values())

        if 0 <= index < len(themes_list):
            self.current_theme = themes_list[index]
            self.activate_btn.set_sensitive(True)
            self.preview_btn.set_sensitive(self.current_theme.name != "Aucun (GRUB par défaut)")
            logger.debug(f"[TabThemeConfig._on_theme_selected] Thème: {self.current_theme.name}")

    def _on_theme_switch_toggled(self, switch: Gtk.Switch, _param: Any) -> None:
        """Appelé quand le switch thème est basculé.

        Args:
            switch: Le widget Switch.
            _param: Paramètre ignoré.
        """
        is_active = switch.get_active()

        if is_active:
            # Quand on active, scanner les scripts et les thèmes
            self._scan_grub_scripts()
            self._scan_system_themes()

        # Activer/désactiver la liste et les boutons
        if self.theme_list_box:
            self.theme_list_box.set_sensitive(is_active)
        if self.activate_btn:
            self.activate_btn.set_sensitive(is_active and self.current_theme is not None)
        if self.preview_btn:
            self.preview_btn.set_sensitive(is_active and self.current_theme is not None)

        logger.debug(f"[TabThemeConfig._on_theme_switch_toggled] Thème {'activé' if is_active else 'désactivé'}")

    def _scan_grub_scripts(self) -> None:
        """Scanne /etc/grub.d/ pour détecter les scripts de thème."""
        if self.scripts_info_box is None:
            return

        # Nettoyer l'affichage précédent
        while True:
            child = self.scripts_info_box.get_first_child()
            if child is None:
                break
            self.scripts_info_box.remove(child)

        logger.debug("[TabThemeConfig._scan_grub_scripts] Scan des scripts GRUB")

        # Utiliser le service pour scanner les scripts
        theme_scripts = self.script_service.scan_theme_scripts()

        if theme_scripts:
            logger.info(f"[TabThemeConfig._scan_grub_scripts] {len(theme_scripts)} script(s) de thème trouvé(s)")

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
                    activate_script_btn.connect("clicked", self._on_activate_script, str(script.path))
                    script_row.append(activate_script_btn)

                self.scripts_info_box.append(script_row)

    def _on_activate_script(self, _button: Gtk.Button, script_path: str) -> None:
        """Active un script GRUB en le rendant exécutable.

        Args:
            _button: Le bouton cliqué.
            script_path: Chemin du script à activer.
        """
        try:
            # Utiliser le service au lieu de subprocess direct
            success = self.script_service.make_executable(Path(script_path))

            if success:
                logger.info(f"[TabThemeConfig._on_activate_script] Script activé: {script_path}")
                create_success_dialog(
                    f"Script activé: {Path(script_path).name}\nRelancez le scan pour voir les changements."
                )

                # Relancer le scan
                self._scan_grub_scripts()
            else:
                logger.error(f"[TabThemeConfig._on_activate_script] Échec de l'activation: {script_path}")
                create_error_dialog(f"Impossible d'activer le script:\n{Path(script_path).name}")

        except GrubCommandError as e:
            logger.error(f"[TabThemeConfig._on_activate_script] Erreur commande: {e}")
            create_error_dialog(f"Erreur lors de l'activation:\n{e}")

        except GrubScriptNotFoundError as e:
            logger.error(f"[TabThemeConfig._on_activate_script] Script introuvable: {e}")
            create_error_dialog(f"Script introuvable:\n{e}")

        except PermissionError as e:
            logger.error(f"[TabThemeConfig._on_activate_script] Permission refusée: {e}")
            create_error_dialog(f"Permission refusée:\n{e}\nNécessite les privilèges root")

        except OSError as e:
            logger.error(f"[TabThemeConfig._on_activate_script] Erreur inattendue: {e}")
            create_error_dialog(f"Erreur inattendue:\n{e}")

    def _on_open_editor(self, button: Gtk.Button) -> None:
        """Ouvre l'éditeur de thème dans une fenêtre séparée.

        Args:
            button: Le bouton cliqué.
        """
        try:
            # Obtenir la fenêtre parente
            if self.parent_window is None:
                widget = button
                while widget is not None:
                    widget = widget.get_parent()
                    if isinstance(widget, Gtk.Window):
                        self.parent_window = widget
                        break

            if self.parent_window:
                editor_dialog = ThemeEditorDialog(self.parent_window, self.state_manager)
                editor_dialog.present()
                logger.info("[TabThemeConfig._on_open_editor] Éditeur de thème ouvert")
            else:
                logger.error("[TabThemeConfig._on_open_editor] Fenêtre parente introuvable")
                create_error_dialog("Impossible d'ouvrir l'éditeur")
        except (OSError, RuntimeError) as e:
            logger.error(f"[TabThemeConfig._on_open_editor] Erreur: {e}")
            create_error_dialog(f"Erreur lors de l'ouverture de l'éditeur:\n{e}")

    def _on_preview_theme(self, _button: Gtk.Button) -> None:
        """Ouvre le dialog de prévisualisation du thème.

        Args:
            _button: Le bouton cliqué.
        """
        if self.current_theme is None:
            create_error_dialog("Veuillez sélectionner un thème")
            return

        try:
            dialog = GrubPreviewDialog(self.current_theme)
            dialog.show()
            logger.debug(f"[TabThemeConfig._on_preview_theme] Aperçu: {self.current_theme.name}")
        except (OSError, RuntimeError) as e:
            logger.error(f"[TabThemeConfig._on_preview_theme] Erreur: {e}")
            create_error_dialog(f"Erreur lors de l'aperçu:\n{e}")

    def _on_activate_theme(self, _button: Gtk.Button) -> None:
        """Applique le thème sélectionné.

        Args:
            _button: Le bouton cliqué.
        """
        if self.current_theme is None:
            create_error_dialog("Veuillez sélectionner un thème")
            return

        try:
            logger.debug(f"[TabThemeConfig._on_activate_theme] Activation: {self.current_theme.name}")

            # Assigner et sauvegarder le thème actif
            self.theme_manager.active_theme = self.current_theme
            self.theme_manager.save_active_theme()

            create_success_dialog(f"Thème '{self.current_theme.name}' activé avec succès")
            logger.info(f"[TabThemeConfig._on_activate_theme] ✓ Succès: {self.current_theme.name}")
        except (OSError, RuntimeError) as e:
            logger.error(f"[TabThemeConfig._on_activate_theme] Erreur: {e}")
            create_error_dialog(f"Erreur lors de l'activation:\n{e}")
