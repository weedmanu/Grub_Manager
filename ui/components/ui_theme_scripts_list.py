"""Composant pour la liste des scripts de thème GRUB."""

from __future__ import annotations

from typing import Any

from gi.repository import Gtk
from loguru import logger

from ui.components.ui_theme_scripts_renderer import clear_list_box, populate_theme_scripts_list

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
        clear_list_box(self.scripts_list_box)

        logger.debug("[ThemeScriptsList] Scan des scripts GRUB")

        # Utiliser le service pour scanner les scripts
        theme_scripts = self.script_service.scan_theme_scripts()

        if not theme_scripts:
            return

        logger.info(f"[ThemeScriptsList] {len(theme_scripts)} script(s) de thème trouvé(s)")
        populate_theme_scripts_list(
            gtk_module=Gtk,
            list_box=self.scripts_list_box,
            theme_scripts=list(theme_scripts),
            pending_changes=getattr(self.state_manager, "pending_script_changes", {}),
            on_toggle=self.on_script_switch_toggled,
        )

    def on_script_switch_toggled(self, switch: Gtk.Switch, script: Any, label: Gtk.Label | None = None) -> None:
        """API publique: appelée quand le switch d'un script est basculé."""
        self._on_script_switch_toggled(switch, script, label)

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

        script_path = getattr(script, "path", "")
        key_str = str(script_path)
        self.state_manager.pending_script_changes[key_str] = is_active

        if script.is_executable == is_active:
            self.state_manager.pending_script_changes.pop(key_str, None)

        # AppStateManager.update_model attend un modèle; on repasse le modèle courant
        # pour déclencher la synchronisation des états UI (boutons, etc.).
        model = self.state_manager.get_model()
        self.state_manager.update_model(model)
