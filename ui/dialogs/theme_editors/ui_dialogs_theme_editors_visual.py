"""Visual-related theme element editors (images, icons)."""

from __future__ import annotations

from gi.repository import Gdk, Gtk

from .ui_dialogs_theme_editors_base import BaseElementEditor, _try_set_spin_suffix


class ImageEditor(BaseElementEditor):
    """Generic editor for image elements (logo, footer)."""

    def __init__(self, element_name: str, element_label: str, default_file: str):
        """Initialise l'éditeur d'images générique."""
        super().__init__(element_name, element_label)
        self.default_file = default_file
        self._build_ui()

    def _build_ui(self) -> None:
        config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        config_box.set_margin_top(12)
        config_box.set_margin_start(12)
        config_box.set_margin_end(12)

        # File
        file_entry = Gtk.Entry()
        file_entry.set_text(self.default_file)
        config_box.append(self._create_file_row("Fichier image", file_entry, self._on_browse))
        self.config_widgets["file"] = file_entry

        # Position Top
        top_spin = Gtk.SpinButton()
        top_spin.set_range(0, 100)
        top_spin.set_value(10)
        _try_set_spin_suffix(top_spin, "%")
        config_box.append(self._create_config_row("Position haut", top_spin))
        self.config_widgets["top"] = top_spin

        # Width
        width_spin = Gtk.SpinButton()
        width_spin.set_range(16, 1024)
        width_spin.set_value(256)
        _try_set_spin_suffix(width_spin, "px")
        config_box.append(self._create_config_row("Largeur", width_spin))
        self.config_widgets["width"] = width_spin

        # Height
        height_spin = Gtk.SpinButton()
        height_spin.set_range(16, 1024)
        height_spin.set_value(128)
        _try_set_spin_suffix(height_spin, "px")
        config_box.append(self._create_config_row("Hauteur", height_spin))
        self.config_widgets["height"] = height_spin

        self.append(config_box)

    def _on_browse(self, _btn):
        # Logic for browsing files could be added here or handled by parent
        pass


class DesktopImageEditor(BaseElementEditor):
    """Editor for the desktop background image."""

    def __init__(self):
        """Initialise l'éditeur d'image de fond."""
        super().__init__("desktop_image", "Image de fond")
        self._build_ui()

    def _build_ui(self) -> None:
        config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        config_box.set_margin_top(12)
        config_box.set_margin_start(12)
        config_box.set_margin_end(12)

        # File
        file_entry = Gtk.Entry()
        file_entry.set_text("background.jpg")
        config_box.append(self._create_file_row("Image de fond", file_entry, lambda _: None))
        self.config_widgets["file"] = file_entry

        # Fallback Color
        color_button = Gtk.ColorButton()
        rgba = Gdk.RGBA()
        rgba.parse("#242424")
        color_button.set_property("rgba", rgba)
        config_box.append(self._create_config_row("Couleur de fond", color_button))
        self.config_widgets["background_color"] = color_button

        # Scale method
        scale_combo = Gtk.DropDown.new_from_strings(["stretch", "crop", "padding", "fitwidth", "fitheight"])
        scale_combo.set_selected(0)
        config_box.append(self._create_config_row("Mise à l'échelle", scale_combo))
        self.config_widgets["scale_method"] = scale_combo

        # Alignment
        h_align = Gtk.DropDown.new_from_strings(["left", "center", "right"])
        h_align.set_selected(1)
        config_box.append(self._create_config_row("Alignement horizontal", h_align))
        self.config_widgets["h_align"] = h_align

        v_align = Gtk.DropDown.new_from_strings(["top", "center", "bottom"])
        v_align.set_selected(1)
        config_box.append(self._create_config_row("Alignement vertical", v_align))
        self.config_widgets["v_align"] = v_align

        self.append(config_box)


class IconsEditor(BaseElementEditor):
    """Editor for the icons element."""

    def __init__(self):
        """Initialise l'éditeur d'icônes."""
        super().__init__("icons", "Icônes")
        self._build_ui()

    def _build_ui(self) -> None:
        config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        config_box.set_margin_top(12)
        config_box.set_margin_start(12)
        config_box.set_margin_end(12)

        # Icons folder
        icons_entry = Gtk.Entry()
        icons_entry.set_placeholder_text("Dossier contenant les icônes")
        config_box.append(self._create_file_row("Dossier d'icônes", icons_entry, lambda _: None))
        self.config_widgets["icons_path"] = icons_entry

        # Icon size
        size_spin = Gtk.SpinButton()
        size_spin.set_range(16, 128)
        size_spin.set_value(32)
        _try_set_spin_suffix(size_spin, "px")
        config_box.append(self._create_config_row("Taille des icônes", size_spin))
        self.config_widgets["icon_size"] = size_spin

        self.append(config_box)
