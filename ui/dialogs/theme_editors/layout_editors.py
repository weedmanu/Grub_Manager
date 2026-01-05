"""Layout-related theme element editors."""

from __future__ import annotations

from gi.repository import Gtk
from .base_editor import BaseElementEditor, _try_set_spin_suffix


class BootMenuEditor(BaseElementEditor):
    """Editor for the boot menu element."""

    def __init__(self):
        super().__init__("boot_menu", "Menu de démarrage")
        self._build_ui()

    def _build_ui(self) -> None:
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)

        config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        config_box.set_margin_top(12)
        config_box.set_margin_start(12)
        config_box.set_margin_end(12)

        # Position and size
        section = Gtk.Label()
        section.set_markup("<b>Position et taille</b>")
        section.set_halign(Gtk.Align.START)
        config_box.append(section)

        # Left
        left_spin = Gtk.SpinButton()
        left_spin.set_range(0, 100)
        left_spin.set_increments(1, 10)
        left_spin.set_value(30)
        _try_set_spin_suffix(left_spin, "%")
        config_box.append(self._create_config_row("Position gauche", left_spin))
        self.config_widgets["left"] = left_spin

        # Top
        top_spin = Gtk.SpinButton()
        top_spin.set_range(0, 100)
        top_spin.set_increments(1, 10)
        top_spin.set_value(30)
        _try_set_spin_suffix(top_spin, "%")
        config_box.append(self._create_config_row("Position haut", top_spin))
        self.config_widgets["top"] = top_spin

        # Width
        width_spin = Gtk.SpinButton()
        width_spin.set_range(10, 100)
        width_spin.set_increments(1, 10)
        width_spin.set_value(40)
        _try_set_spin_suffix(width_spin, "%")
        config_box.append(self._create_config_row("Largeur", width_spin))
        self.config_widgets["width"] = width_spin

        # Height
        height_spin = Gtk.SpinButton()
        height_spin.set_range(10, 100)
        height_spin.set_increments(1, 10)
        height_spin.set_value(40)
        _try_set_spin_suffix(height_spin, "%")
        config_box.append(self._create_config_row("Hauteur", height_spin))
        self.config_widgets["height"] = height_spin

        scroll.set_child(config_box)
        self.append(scroll)


class ProgressBarEditor(BaseElementEditor):
    """Editor for the progress bar element."""

    def __init__(self):
        super().__init__("progress_bar", "Barre de progression")
        self._build_ui()

    def _build_ui(self) -> None:
        config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        
        # Left
        left_spin = Gtk.SpinButton()
        left_spin.set_range(0, 100)
        left_spin.set_value(20)
        _try_set_spin_suffix(left_spin, "%")
        config_box.append(self._create_config_row("Position gauche", left_spin))
        self.config_widgets["left"] = left_spin

        # Top
        top_spin = Gtk.SpinButton()
        top_spin.set_range(0, 100)
        top_spin.set_value(80)
        _try_set_spin_suffix(top_spin, "%")
        config_box.append(self._create_config_row("Position haut", top_spin))
        self.config_widgets["top"] = top_spin

        self.append(config_box)


class TerminalBoxEditor(BaseElementEditor):
    """Editor for terminal box and selection elements."""

    def __init__(self, element_name: str, element_label: str, prefix: str):
        super().__init__(element_name, element_label)
        self.prefix = prefix
        self._build_ui()

    def _build_ui(self) -> None:
        config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        config_box.set_margin_top(12)
        config_box.set_margin_start(12)
        config_box.set_margin_end(12)

        # Center image
        c_entry = Gtk.Entry()
        c_entry.set_text(f"{self.prefix}_c.png")
        config_box.append(self._create_file_row("Image centre", c_entry))
        self.config_widgets[f"{self.prefix}_c"] = c_entry

        # If it's selection, add W and E
        if self.prefix == "select":
            w_entry = Gtk.Entry()
            w_entry.set_text(f"{self.prefix}_w.png")
            config_box.append(self._create_file_row("Bord gauche", w_entry))
            self.config_widgets[f"{self.prefix}_w"] = w_entry

            e_entry = Gtk.Entry()
            e_entry.set_text(f"{self.prefix}_e.png")
            config_box.append(self._create_file_row("Bord droit", e_entry))
            self.config_widgets[f"{self.prefix}_e"] = e_entry

        self.append(config_box)
