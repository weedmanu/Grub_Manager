"""Composant pour la configuration simple du thème GRUB (couleurs et fond)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from gi.repository import Gtk
from loguru import logger

from ui.ui_constants import GRUB_COLORS
from ui.ui_gtk_helpers import GtkHelper

HORIZONTAL = Gtk.Orientation.HORIZONTAL
VERTICAL = Gtk.Orientation.VERTICAL


class ThemeSimpleConfigPanel(Gtk.Box):
    """Panneau de configuration simple (couleurs et image de fond)."""

    def __init__(self, state_manager: Any, on_changed: callable) -> None:
        """Initialise le panneau.

        Args:
            state_manager: Gestionnaire d'état global.
            on_changed: Callback appelé quand une valeur change.
        """
        super().__init__(orientation=VERTICAL, spacing=15)
        self.state_manager = state_manager
        self.on_changed = on_changed
        self._updating_ui = False

        # Widgets
        self.bg_image_entry: Gtk.Entry | None = None
        self.normal_fg_combo: Gtk.DropDown | None = None
        self.normal_bg_combo: Gtk.DropDown | None = None
        self.highlight_fg_combo: Gtk.DropDown | None = None
        self.highlight_bg_combo: Gtk.DropDown | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Construit l'interface du panneau."""
        self.set_margin_top(10)
        self.set_margin_bottom(10)
        self.set_margin_start(10)
        self.set_margin_end(10)

        # Titre
        title = Gtk.Label(xalign=0)
        title.set_markup("<b>Configuration Simple</b>")
        title.add_css_class("section-title")
        self.append(title)

        desc = Gtk.Label(xalign=0, label="Configurez l'apparence de base sans utiliser de thème complet.")
        desc.add_css_class("dim-label")
        self.append(desc)

        # Grid pour l'alignement
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(15)
        self.append(grid)

        # --- Image de fond ---
        bg_label = Gtk.Label(label="Image de fond :", xalign=0)
        grid.attach(bg_label, 0, 0, 1, 1)

        bg_box = Gtk.Box(orientation=HORIZONTAL, spacing=5)
        self.bg_image_entry = Gtk.Entry()
        self.bg_image_entry.set_hexpand(True)
        self.bg_image_entry.set_placeholder_text("/chemin/vers/image.jpg")
        self.bg_image_entry.connect("changed", self._on_config_changed)
        bg_box.append(self.bg_image_entry)

        bg_btn = Gtk.Button(label="...")
        bg_btn.connect("clicked", self._on_select_bg_image)
        bg_box.append(bg_btn)

        grid.attach(bg_box, 1, 0, 3, 1)

        # --- Couleurs Normales ---
        normal_label = Gtk.Label(label="Couleur Menu (Normal) :", xalign=0)
        grid.attach(normal_label, 0, 1, 1, 1)

        self.normal_fg_combo = Gtk.DropDown.new_from_strings(GRUB_COLORS)
        self.normal_fg_combo.connect("notify::selected", self._on_config_changed)
        grid.attach(self.normal_fg_combo, 1, 1, 1, 1)

        sep1 = Gtk.Label(label="sur")
        grid.attach(sep1, 2, 1, 1, 1)

        self.normal_bg_combo = Gtk.DropDown.new_from_strings(GRUB_COLORS)
        self.normal_bg_combo.connect("notify::selected", self._on_config_changed)
        grid.attach(self.normal_bg_combo, 3, 1, 1, 1)

        # --- Couleurs Sélection ---
        highlight_label = Gtk.Label(label="Couleur Menu (Sélection) :", xalign=0)
        grid.attach(highlight_label, 0, 2, 1, 1)

        self.highlight_fg_combo = Gtk.DropDown.new_from_strings(GRUB_COLORS)
        self.highlight_fg_combo.connect("notify::selected", self._on_config_changed)
        grid.attach(self.highlight_fg_combo, 1, 2, 1, 1)

        sep2 = Gtk.Label(label="sur")
        grid.attach(sep2, 2, 2, 1, 1)

        self.highlight_bg_combo = Gtk.DropDown.new_from_strings(GRUB_COLORS)
        self.highlight_bg_combo.connect("notify::selected", self._on_config_changed)
        grid.attach(self.highlight_bg_combo, 3, 2, 1, 1)

    def update_from_model(self, model: Any) -> None:
        """Met à jour les widgets depuis le modèle.

        Args:
            model: Le modèle de données.
        """
        self._updating_ui = True
        try:
            if self.bg_image_entry:
                self.bg_image_entry.set_text(model.grub_background or "")

            def set_combo_color(combo: Gtk.DropDown | None, color_pair: str, index: int) -> None:
                if not combo or not color_pair or "/" not in color_pair:
                    return
                color = color_pair.split("/")[index].strip()
                if color in GRUB_COLORS:
                    combo.set_selected(GRUB_COLORS.index(color))

            set_combo_color(self.normal_fg_combo, model.grub_color_normal, 0)
            set_combo_color(self.normal_bg_combo, model.grub_color_normal, 1)
            set_combo_color(self.highlight_fg_combo, model.grub_color_highlight, 0)
            set_combo_color(self.highlight_bg_combo, model.grub_color_highlight, 1)
        finally:
            self._updating_ui = False

    def _on_select_bg_image(self, button: Gtk.Button) -> None:
        """Ouvre un sélecteur de fichier pour l'image de fond."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Choisir une image de fond")

        filters = Gtk.FileFilter()
        filters.set_name("Images")
        filters.add_mime_type("image/jpeg")
        filters.add_mime_type("image/png")
        filters.add_mime_type("image/tga")
        dialog.set_default_filter(filters)

        parent = GtkHelper.resolve_parent_window(button)
        dialog.open(parent, None, self._on_bg_image_selected)

    def _on_bg_image_selected(self, dialog: Gtk.FileDialog, result) -> None:
        """Callback après sélection de l'image."""
        try:
            file = dialog.open_finish(result)
            if file and self.bg_image_entry:
                self.bg_image_entry.set_text(file.get_path())
        except (OSError, RuntimeError) as e:
            logger.warning(f"[ThemeSimpleConfigPanel] Sélection d'image annulée ou échouée: {e}")

    def _on_config_changed(self, *_) -> None:
        """Met à jour le modèle quand la config change."""
        if self._updating_ui:
            return

        # Récupérer les valeurs
        bg_image = self.bg_image_entry.get_text()

        n_fg = GRUB_COLORS[self.normal_fg_combo.get_selected()]
        n_bg = GRUB_COLORS[self.normal_bg_combo.get_selected()]
        color_normal = f"{n_fg}/{n_bg}"

        h_fg = GRUB_COLORS[self.highlight_fg_combo.get_selected()]
        h_bg = GRUB_COLORS[self.highlight_bg_combo.get_selected()]
        color_highlight = f"{h_fg}/{h_bg}"

        # Mettre à jour le modèle
        current_model = self.state_manager.get_model()
        new_model = replace(
            current_model,
            grub_background=bg_image,
            grub_color_normal=color_normal,
            grub_color_highlight=color_highlight,
        )

        self.state_manager.update_model(new_model)
        self.on_changed()
