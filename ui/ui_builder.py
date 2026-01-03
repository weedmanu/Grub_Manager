"""Construction de l'interface utilisateur GTK4.

Responsable de la création et configuration de tous les widgets GTK4.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gi.repository import Gtk
from loguru import logger

from ui.tabs.ui_tab_backups import build_backups_tab
from ui.tabs.ui_tab_display import build_display_tab
from ui.tabs.ui_tab_entries import build_entries_tab
from ui.tabs.ui_tab_general import build_general_tab
from ui.tabs.ui_tab_maintenance import build_maintenance_tab
from ui.tabs.ui_tab_theme_config import TabThemeConfig

if TYPE_CHECKING:
    from ui.ui_manager import GrubConfigManager


class UIBuilder:
    """Constructeur centralisé de l'interface GTK4.

    Responsabilités:
    - Création des widgets GTK4
    - Configuration de l'interface principale
    - Construction des onglets
    - Configuration des boutons d'action
    """

    @staticmethod
    def create_main_ui(window: GrubConfigManager) -> None:
        """Construit l'interface principale complète.

        Args:
            window: Fenêtre principale de l'application
        """
        logger.debug("[UIBuilder.create_main_ui] Début de la construction de l'interface")
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_top(10)
        main_box.set_margin_bottom(10)
        main_box.set_margin_start(10)
        main_box.set_margin_end(10)
        window.set_child(main_box)

        # === Notebook avec onglets ===
        UIBuilder._create_notebook(window, main_box)

        # === Séparateur ===
        main_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # === Zone d'information (en bas) et Boutons d'action ===
        UIBuilder._create_bottom_bar(window, main_box)

        logger.success("[UIBuilder.create_main_ui] Interface construite complètement")

    @staticmethod
    def _create_bottom_bar(window: GrubConfigManager, container: Gtk.Box) -> None:
        """Crée la barre du bas avec la zone d'information à gauche et les boutons à droite.

        Args:
            window: Fenêtre principale de l'application
            container: Container GTK où ajouter la barre
        """
        logger.debug("[UIBuilder._create_bottom_bar] Construction de la barre du bas")

        # Container horizontal pour zone info (gauche) + boutons (droite)
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bottom_box.set_hexpand(True)
        container.append(bottom_box)

        # === Zone d'information à gauche ===
        window.info_revealer = Gtk.Revealer()
        window.info_revealer.set_reveal_child(False)
        window.info_revealer.set_hexpand(True)

        info_frame = Gtk.Frame()
        window.info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        window.info_box.set_margin_top(8)
        window.info_box.set_margin_bottom(8)
        window.info_box.set_margin_start(10)
        window.info_box.set_margin_end(10)
        window.info_box.set_hexpand(True)

        window.info_label = Gtk.Label(xalign=0)
        window.info_label.set_wrap(True)
        window.info_label.set_hexpand(True)
        window.info_box.append(window.info_label)

        info_frame.set_child(window.info_box)
        window.info_revealer.set_child(info_frame)
        bottom_box.append(window.info_revealer)

        # === Boutons d'action à droite ===
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_halign(Gtk.Align.END)
        bottom_box.append(button_box)

        window.reload_btn = Gtk.Button(label="Recharger")
        window.reload_btn.connect("clicked", window.on_reload)
        button_box.append(window.reload_btn)

        window.save_btn = Gtk.Button(label="Appliquer")
        window.save_btn.add_css_class("suggested-action")
        window.save_btn.connect("clicked", window.on_save)
        button_box.append(window.save_btn)

        logger.debug("[UIBuilder._create_bottom_bar] Barre du bas créée")

    @staticmethod
    def _create_notebook(window: GrubConfigManager, container: Gtk.Box) -> Gtk.Notebook:
        """Crée le notebook avec tous les onglets.

        Args:
            window: Fenêtre principale de l'application
            container: Container GTK où ajouter le notebook

        Returns:
            Le notebook GTK créé
        """
        logger.debug("[UIBuilder._create_notebook] Construction des onglets")
        notebook = Gtk.Notebook()
        notebook.set_hexpand(True)
        notebook.set_vexpand(True)
        container.append(notebook)

        # DEV: Chaque builder remplit les références de widgets déclarés dans __init__
        build_general_tab(window, notebook)
        build_entries_tab(window, notebook)
        build_display_tab(window, notebook)

        # Onglet de configuration de thème (activation)
        theme_config = TabThemeConfig(window.state_manager)
        theme_config_tab = theme_config.build()
        notebook.append_page(theme_config_tab, Gtk.Label(label="Thèmes"))

        build_backups_tab(window, notebook)
        build_maintenance_tab(window, notebook)

        # === Connect tab switch signal ===
        def _on_switch_page(nb, page, page_num):
            """Handle tab switch - trace which tab is now active."""
            tab_label = nb.get_tab_label_text(page)
            logger.info(f"[_on_switch_page] User switched to tab #{page_num}: '{tab_label}'")

        notebook.connect("switch-page", _on_switch_page)
        logger.debug("[UIBuilder._create_notebook] Tab switch signal connected")

        logger.debug("[UIBuilder._create_notebook] Onglets construits")
        return notebook

    @staticmethod
    def _create_info_area(_window: GrubConfigManager, _container: Gtk.Box) -> None:
        """Crée la zone d'information pour les messages temporaires (OBSOLÈTE - voir _create_bottom_bar).

        Args:
            _window: Fenêtre principale de l'application
            _container: Container GTK où ajouter la zone d'info
        """
        # Cette fonction est maintenant intégrée dans _create_bottom_bar
        # Conservée pour compatibilité si utilisée ailleurs
        logger.debug("[UIBuilder._create_info_area] OBSOLÈTE - utiliser _create_bottom_bar")

    @staticmethod
    def _create_action_buttons(_window: GrubConfigManager, _container: Gtk.Box) -> None:
        """Crée les boutons d'action (OBSOLÈTE - voir _create_bottom_bar).

        Args:
            _window: Fenêtre principale de l'application
            container: Container GTK où ajouter les boutons
        """
        # Cette fonction est maintenant intégrée dans _create_bottom_bar
        # Conservée pour compatibilité si utilisée ailleurs
        logger.debug("[UIBuilder._create_action_buttons] OBSOLÈTE - utiliser _create_bottom_bar")
