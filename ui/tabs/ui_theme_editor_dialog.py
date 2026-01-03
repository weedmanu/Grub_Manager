"""Dialogue d'édition de thème GRUB (fenêtre séparée)."""

from __future__ import annotations

from gi.repository import Gtk
from loguru import logger

from core.theme.core_theme_generator import (
    GrubTheme,
)
from ui.tabs.ui_tab_theme_editor import TabThemeEditor


class ThemeEditorDialog(Gtk.Window):
    """Dialogue d'édition de thème GRUB dans une fenêtre séparée."""

    def __init__(self, parent_window: Gtk.Window, state_manager) -> None:
        """Initialise le dialogue d'édition de thèmes.

        Args:
            parent_window: Fenêtre parente
            state_manager: Gestionnaire d'état de l'application
        """
        super().__init__(title="Éditeur de thèmes GRUB")
        self.set_transient_for(parent_window)
        self.set_modal(False)
        self.set_default_size(900, 700)

        self.state_manager = state_manager
        self.current_theme: GrubTheme | None = None
        self._updating_ui = False

        # Widgets de couleurs
        self.title_color_btn: Gtk.ColorButton | None = None
        self.bg_color_btn: Gtk.ColorButton | None = None
        self.menu_fg_btn: Gtk.ColorButton | None = None
        self.menu_bg_btn: Gtk.ColorButton | None = None
        self.highlight_fg_btn: Gtk.ColorButton | None = None
        self.highlight_bg_btn: Gtk.ColorButton | None = None

        # Widgets d'image
        self.bg_image_entry: Gtk.Entry | None = None
        self.bg_image_scale_combo: Gtk.DropDown | None = None

        # Widgets de mise en page
        self.show_boot_menu_check: Gtk.CheckButton | None = None
        self.show_progress_check: Gtk.CheckButton | None = None
        self.show_timeout_check: Gtk.CheckButton | None = None
        self.show_scrollbar_check: Gtk.CheckButton | None = None

        # Widget de nom
        self.theme_name_entry: Gtk.Entry | None = None

        # Widgets de titre et paramètres GRUB
        self.title_text_entry: Gtk.Entry | None = None
        self.grub_timeout_spin: Gtk.SpinButton | None = None
        self.grub_gfxmode_entry: Gtk.Entry | None = None

        # Zone de prévisualisation du code
        self.preview_buffer: Gtk.TextBuffer | None = None

        self._build_ui()
        self._load_default_theme()

        logger.info("[ThemeEditorDialog] Dialogue initialisé")

    def _build_ui(self) -> None:
        """Construit l'interface du dialogue."""
        # Réutiliser le code de TabThemeEditor
        editor = TabThemeEditor(self.state_manager)

        # Copier les références de widgets
        content = editor.build()

        # Copier toutes les références de widgets
        self.title_color_btn = editor.title_color_btn
        self.bg_color_btn = editor.bg_color_btn
        self.menu_fg_btn = editor.menu_fg_btn
        self.menu_bg_btn = editor.menu_bg_btn
        self.highlight_fg_btn = editor.highlight_fg_btn
        self.highlight_bg_btn = editor.highlight_bg_btn
        self.bg_image_entry = editor.bg_image_entry
        self.bg_image_scale_combo = editor.bg_image_scale_combo
        self.show_boot_menu_check = editor.show_boot_menu_check
        self.show_progress_check = editor.show_progress_check
        self.show_timeout_check = editor.show_timeout_check
        self.show_scrollbar_check = editor.show_scrollbar_check
        self.theme_name_entry = editor.theme_name_entry
        self.title_text_entry = editor.title_text_entry
        self.grub_timeout_spin = editor.grub_timeout_spin
        self.grub_gfxmode_entry = editor.grub_gfxmode_entry
        self.preview_buffer = editor.preview_buffer

        # Garder une référence à l'éditeur
        self._editor = editor

        self.set_child(content)
        logger.success("[ThemeEditorDialog] Interface construite")

    def _load_default_theme(self) -> None:
        """Délègue au TabThemeEditor."""
        if hasattr(self, "_editor"):
            self._editor._load_default_theme()
