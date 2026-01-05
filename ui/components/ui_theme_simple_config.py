"""Composant pour la configuration simple du thème GRUB (couleurs et fond)."""

from __future__ import annotations

from typing import Any

from gi.repository import Gtk
from loguru import logger

from ui.components.ui_theme_simple_config_logic import apply_simple_theme_config_from_widgets
from ui.ui_constants import GRUB_COLORS
from ui.ui_file_dialogs import open_image_file_dialog
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
        open_image_file_dialog(
            gtk_module=Gtk,
            button=button,
            title="Choisir une image de fond",
            parent_window=GtkHelper.resolve_parent_window(button),
            on_selected=lambda path: self.bg_image_entry.set_text(path) if self.bg_image_entry else None,
        )

    def _on_config_changed(self, *_) -> None:
        """Met à jour le modèle quand la config change."""
        if self._updating_ui:
            return

        try:
            updated = apply_simple_theme_config_from_widgets(
                state_manager=self.state_manager,
                colors=list(GRUB_COLORS),
                bg_image_entry=self.bg_image_entry,
                normal_fg_combo=self.normal_fg_combo,
                normal_bg_combo=self.normal_bg_combo,
                highlight_fg_combo=self.highlight_fg_combo,
                highlight_bg_combo=self.highlight_bg_combo,
            )
        except (AttributeError, IndexError) as exc:
            logger.debug(f"[ThemeSimpleConfigPanel] Widgets incomplets/invalides: {exc}")
            return

        if updated:
            self.on_changed()
