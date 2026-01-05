"""Text and color related theme element editors."""

from __future__ import annotations

from gi.repository import Gdk, Gtk

from .base_editor import BaseElementEditor, _try_set_spin_suffix


class TextElementEditor(BaseElementEditor):
    """Generic editor for text elements (timeout, instruction)."""

    def __init__(self, element_name: str, element_label: str, default_text: str, default_top: int):
        """Initialise l'éditeur de texte générique."""
        super().__init__(element_name, element_label)
        self.default_text = default_text
        self.default_top = default_top
        self._build_ui()

    def _build_ui(self) -> None:
        config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        config_box.set_margin_top(12)
        config_box.set_margin_start(12)
        config_box.set_margin_end(12)

        # Text
        text_entry = Gtk.Entry()
        text_entry.set_text(self.default_text)
        config_box.append(self._create_config_row("Texte", text_entry))
        self.config_widgets["text"] = text_entry

        # Position Top
        top_spin = Gtk.SpinButton()
        top_spin.set_range(0, 100)
        top_spin.set_value(self.default_top)
        _try_set_spin_suffix(top_spin, "%")
        config_box.append(self._create_config_row("Position haut", top_spin))
        self.config_widgets["top"] = top_spin

        # Align
        align_combo = Gtk.DropDown.new_from_strings(["left", "center", "right"])
        align_combo.set_selected(1)
        config_box.append(self._create_config_row("Alignement", align_combo))
        self.config_widgets["align"] = align_combo

        # Color
        color_button = Gtk.ColorButton()
        rgba = Gdk.RGBA()
        rgba.parse("#ffffff")
        color_button.set_property("rgba", rgba)
        config_box.append(self._create_config_row("Couleur", color_button))
        self.config_widgets["color"] = color_button

        self.append(config_box)


class ColorsEditor(BaseElementEditor):
    """Editor for the theme colors."""

    def __init__(self):
        """Initialise l'éditeur de couleurs."""
        super().__init__("colors", "Couleurs")
        self._build_ui()

    def _build_ui(self) -> None:
        config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        config_box.set_margin_top(12)
        config_box.set_margin_start(12)
        config_box.set_margin_end(12)

        def add_color_row(label: str, key: str, default_hex: str):
            btn = Gtk.ColorButton()
            rgba = Gdk.RGBA()
            rgba.parse(default_hex)
            btn.set_property("rgba", rgba)
            config_box.append(self._create_config_row(label, btn))
            self.config_widgets[key] = btn

        add_color_row("Texte normal", "text", "#cccccc")
        add_color_row("Fond", "background", "#000000")
        add_color_row("Texte sélectionné", "selected", "#ffffff")
        add_color_row("Fond de sélection", "selected_bg", "#2980b9")
        add_color_row("Texte des étiquettes", "label", "#aaaaaa")

        self.append(config_box)


class FontsEditor(BaseElementEditor):
    """Editor for the theme fonts."""

    def __init__(self):
        """Initialise l'éditeur de polices."""
        super().__init__("fonts", "Polices")
        self._build_ui()

    def _build_ui(self) -> None:
        config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        config_box.set_margin_top(12)
        config_box.set_margin_start(12)
        config_box.set_margin_end(12)

        # Item Font
        font_entry = Gtk.Entry()
        font_entry.set_text("Unifont Regular 16")
        config_box.append(self._create_config_row("Nom de la police", font_entry))
        self.config_widgets["item_font"] = font_entry

        # Terminal font
        term_entry = Gtk.Entry()
        term_entry.set_text("Terminus Regular 14")
        config_box.append(self._create_config_row("Nom police terminal", term_entry))
        self.config_widgets["terminal_font"] = term_entry

        self.append(config_box)
