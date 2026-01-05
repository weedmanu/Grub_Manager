"""Composant pour la liste des scripts de thème GRUB."""

from __future__ import annotations

from typing import Any

from gi.repository import Gtk
from loguru import logger

HORIZONTAL = Gtk.Orientation.HORIZONTAL
VERTICAL = Gtk.Orientation.VERTICAL


class ThemeScriptsList(Gtk.Box):
    """Composant affichant la liste des scripts GRUB (/etc/grub.d/)."""

    def __init__(self, state_manager: Any, script_service: Any) -> None:
        """Initialise le composant.

        Args:
            state_manager: Gestionnaire d'état global.
            script_service: Service pour scanner les scripts.
        """
        super().__init__(orientation=VERTICAL, spacing=10)
        self.state_manager = state_manager
        self.script_service = script_service

        # Widgets
        self.scripts_list_box = Gtk.ListBox()
        self.scripts_list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.scripts_list_box.add_css_class("rich-list")

        self._build_ui()

    def _build_ui(self) -> None:
        """Construit l'interface du composant."""
        # Titre
        scripts_title = Gtk.Label(xalign=0)
        scripts_title.set_markup("<b>Scripts de thème</b>")
        scripts_title.add_css_class("section-title")
        self.append(scripts_title)

        scripts_desc = Gtk.Label(xalign=0, label="Gérez les scripts de génération (ex: 05_debian_theme).")
        scripts_desc.add_css_class("dim-label")
        self.append(scripts_desc)

        # Box horizontale pour liste + actions
        scripts_container = Gtk.Box(orientation=HORIZONTAL, spacing=15)
        scripts_container.set_margin_top(10)
        self.append(scripts_container)

        scrolled_scripts = Gtk.ScrolledWindow()
        scrolled_scripts.set_child(self.scripts_list_box)
        scrolled_scripts.set_min_content_height(120)
        scrolled_scripts.set_hexpand(True)
        scripts_container.append(scrolled_scripts)

    def refresh(self) -> None:
        """Scanne et affiche les scripts GRUB."""
        # Nettoyer l'affichage précédent
        while True:
            child = self.scripts_list_box.get_first_child()
            if child is None:
                break
            self.scripts_list_box.remove(child)

        logger.debug("[ThemeScriptsList] Scan des scripts GRUB")

        # Utiliser le service pour scanner les scripts
        theme_scripts = self.script_service.scan_theme_scripts()

        if theme_scripts:
            logger.info(f"[ThemeScriptsList] {len(theme_scripts)} script(s) de thème trouvé(s)")

            for script in theme_scripts:
                row = Gtk.ListBoxRow()
                row.set_selectable(False)

                script_box = Gtk.Box(orientation=HORIZONTAL, spacing=10)
                script_box.set_margin_top(8)
                script_box.set_margin_bottom(8)
                script_box.set_margin_start(10)
                script_box.set_margin_end(10)

                # Déterminer l'état effectif (en attente ou actuel)
                is_executable = script.is_executable
                is_pending = False
                
                if script.path in self.state_manager.pending_script_changes:
                    is_executable = self.state_manager.pending_script_changes[script.path]
                    is_pending = True

                # Nom du script
                script_name = script.name
                if script_name in ["05_debian_theme", "05_grub_colors"]:
                    script_name += " (Défaut)"
                
                if is_pending:
                    script_name += " *"

                name_label = Gtk.Label(label=script_name)
                name_label.set_halign(Gtk.Align.START)
                name_label.set_hexpand(True)
                name_label.add_css_class("title-4")
                script_box.append(name_label)

                # Label d'état
                state_text = "actif" if is_executable else "inactif"
                state_label = Gtk.Label(label=state_text)
                state_label.set_margin_end(10)
                if not is_executable:
                    state_label.add_css_class("warning")
                script_box.append(state_label)

                # Switch d'activation
                switch = Gtk.Switch()
                switch.set_active(is_executable)
                switch.set_valign(Gtk.Align.CENTER)
                
                switch.connect("notify::active", lambda s, p, sc=script, lbl=state_label: self._on_script_switch_toggled(s, sc, lbl))
                
                script_box.append(switch)

                row.set_child(script_box)
                self.scripts_list_box.append(row)

    def _on_script_switch_toggled(self, switch: Gtk.Switch, script: Any, label: Gtk.Label | None = None) -> None:
        """Appelé quand le switch d'un script est basculé."""
        if self.state_manager.is_loading():
            return

        is_active = switch.get_active()
        logger.debug(f"[ThemeScriptsList] Script {script.name} -> {is_active}")
        
        if label:
            label.set_label("actif" if is_active else "inactif")
            if is_active:
                label.remove_css_class("warning")
            else:
                label.add_css_class("warning")
        
        self.state_manager.pending_script_changes[script.path] = is_active
        
        if script.is_executable == is_active:
            if script.path in self.state_manager.pending_script_changes:
                del self.state_manager.pending_script_changes[script.path]

        # AppStateManager.update_model attend un modèle; on repasse le modèle courant
        # pour déclencher la synchronisation des états UI (boutons, etc.).
        model = self.state_manager.get_model() if hasattr(self.state_manager, "get_model") else None
        try:
            if model is not None:
                self.state_manager.update_model(model)
            else:
                # Fallback pour d'éventuels mocks/implémentations anciennes.
                self.state_manager.update_model()
        except TypeError:
            # Compat: certains doubles de test peuvent avoir une signature différente.
            self.state_manager.update_model()
