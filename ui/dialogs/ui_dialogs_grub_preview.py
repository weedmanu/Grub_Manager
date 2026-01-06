"""Dialog pour afficher un aperçu réaliste du menu GRUB (Native)."""

import re
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, Gtk  # noqa: E402


class GrubPreviewDialog(Gtk.Window):
    """Dialogue pour afficher un aperçu réaliste du menu GRUB."""

    def __init__(self, grub_config: str, model=None) -> None:
        """Initialise le dialogue d'aperçu.

        Args:
            grub_config: Contenu du fichier grub.cfg
            model: Modèle de configuration UI actuel
        """
        super().__init__(title="Aperçu GRUB")
        self.set_default_size(1500, 900)
        self.model = model

        # Parse the GRUB config
        self.entries = self.parse_grub_config(grub_config)
        self.timeout = self.get_timeout(grub_config)
        self.selected_index = 0

        # Main container
        overlay = Gtk.Overlay()
        self.set_child(overlay)

        # Background
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_draw_func(self.draw_background)
        overlay.set_child(self.drawing_area)

        # Content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content_box.set_valign(Gtk.Align.FILL)
        content_box.set_halign(Gtk.Align.FILL)
        content_box.set_margin_start(0)
        content_box.set_margin_end(0)
        content_box.set_margin_top(60)
        content_box.set_margin_bottom(60)
        overlay.add_overlay(content_box)

        # Title
        title_label = Gtk.Label()
        title_label.set_markup('<span foreground="white" size="small">GNU GRUB  version 2.12</span>')
        title_label.set_halign(Gtk.Align.CENTER)
        title_label.set_margin_bottom(20)
        content_box.append(title_label)

        # Menu frame
        frame = Gtk.Frame()
        frame.set_vexpand(True)
        frame.set_hexpand(False)
        frame.set_halign(Gtk.Align.CENTER)
        frame.set_size_request(1450, -1)
        frame.add_css_class("grub-frame")
        content_box.append(frame)

        # Menu box
        menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        menu_box.set_margin_start(5)
        menu_box.set_margin_end(5)
        menu_box.set_margin_top(15)
        menu_box.set_margin_bottom(15)
        frame.set_child(menu_box)

        # Add menu entries
        for i, entry in enumerate(self.entries):
            label = Gtk.Label(label=entry)
            label.set_xalign(0)
            label.set_margin_top(3)
            label.set_margin_bottom(3)
            label.set_margin_start(10)

            if i == self.selected_index:
                label.add_css_class("grub-selected")
            else:
                label.add_css_class("grub-normal")

            menu_box.append(label)

        # Bottom instructions
        instructions = Gtk.Label()
        instructions.set_markup(
            '<span foreground="white" size="x-small">'
            "Utilisez les touches ↑ et ↓ pour sélectionner une entrée.\n"
            "Appuyez sur Entrée pour démarrer le système sélectionné, e o p pour éditer les commandes avant de démarrer ou c b p pour obtenir une invite de commandes. Échap pour revenir au menu précédent.\n"
            "Appuyez sur Entrée pour démarrer le système sélectionné."
            "</span>"
        )
        instructions.set_halign(Gtk.Align.START)
        instructions.set_margin_start(25)
        instructions.set_margin_top(30)
        instructions.set_wrap(True)
        instructions.set_justify(Gtk.Justification.LEFT)
        content_box.append(instructions)

        # Apply CSS
        self.apply_css()

        # Key press handling
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_controller)

    def get_timeout(self, config: str) -> int:
        """Extrait le timeout de la configuration GRUB."""
        match = re.search(r"GRUB_TIMEOUT=(\d+)", config)
        return int(match.group(1)) if match else 10

    def parse_grub_config(self, config: str) -> list[str]:
        """Extrait les entrées de menu de la config GRUB."""
        entries = []
        if not config:
            return entries

        lines = config.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check if previous line marks this as hidden
            if i > 0 and "### GRUB_MANAGER_HIDDEN" in lines[i - 1]:
                i += 1
                continue

            # Match menuentry
            if line.startswith("menuentry "):
                match = re.match(r"menuentry\s+'([^']+)'", line)
                if match:
                    title = match.group(1)
                    entries.append(title)

            # Match submenu
            elif line.startswith("submenu "):
                match = re.match(r"submenu\s+'([^']+)'", line)
                if match:
                    title = match.group(1)
                    entries.append(title)

            i += 1

        return entries

    def draw_background(self, _area: Gtk.DrawingArea, cr, width: int, height: int) -> None:
        """Dessine l'arrière-plan."""
        # 1. Background Image from Model (GRUB_BACKGROUND)
        if self.model and self.model.grub_background:
            bg_path = Path(self.model.grub_background)
            if bg_path.exists() and bg_path.is_file():
                try:
                    # Load pixbuf scaled to window size
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(bg_path), width, height, False)

                    # Draw pixbuf using Cairo
                    Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
                    cr.paint()
                    return
                except Exception as e:
                    print(f"Error loading background image: {e}")

        # 2. Fallback to Background Color (Black)
        # Note: GRUB defaults to black if no image is set
        cr.set_source_rgb(0, 0, 0)
        cr.rectangle(0, 0, width, height)
        cr.fill()

    def apply_css(self) -> None:
        """Applique le style CSS personnalisé."""
        # Default colors
        normal_color = "white"
        selected_bg = "white"
        selected_fg = "black"

        # Helper to map GRUB color names to CSS
        def map_color(grub_color_name):
            mapping = {
                "black": "black",
                "blue": "blue",
                "brown": "brown",
                "cyan": "cyan",
                "dark-gray": "darkgray",
                "green": "green",
                "light-blue": "lightblue",
                "light-cyan": "lightcyan",
                "light-gray": "lightgray",
                "light-green": "lightgreen",
                "light-magenta": "violet",
                "light-red": "pink",
                "magenta": "magenta",
                "red": "red",
                "white": "white",
                "yellow": "yellow",
            }
            return mapping.get(grub_color_name, grub_color_name)

        # Override from model if available
        if self.model:
            if self.model.grub_color_normal:
                # "fg/bg" -> "white/black"
                parts = self.model.grub_color_normal.split("/")
                if len(parts) >= 1:
                    normal_color = map_color(parts[0])

            if self.model.grub_color_highlight:
                # "fg/bg" -> "black/white"
                parts = self.model.grub_color_highlight.split("/")
                if len(parts) >= 1:
                    selected_fg = map_color(parts[0])
                if len(parts) >= 2:
                    selected_bg = map_color(parts[1])

        css_provider = Gtk.CssProvider()
        css = f"""
            .grub-frame {{
                border: 2px solid rgba(255, 255, 255, 0.9);
                background-color: rgba(0, 0, 0, 0.85);
                border-radius: 0px;
            }}

            .grub-normal {{
                color: {normal_color};
                font-family: monospace;
                font-size: 11pt;
                padding: 4px;
            }}

            .grub-selected {{
                color: {selected_fg};
                background-color: {selected_bg};
                font-family: monospace;
                font-size: 11pt;
                font-weight: bold;
                padding: 4px;
            }}
        """
        css_provider.load_from_data(css.encode())

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def on_key_pressed(self, _controller, keyval, _keycode, _state) -> bool | None:
        """Gère la navigation au clavier."""
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        elif keyval == Gdk.KEY_Up:
            # Move selection up (visual only for now)
            return True
        elif keyval == Gdk.KEY_Down:
            # Move selection down (visual only for now)
            return True
        return False
