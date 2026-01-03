"""Onglet Affichage (GTK4).

Fusion de la partie "graphique" (gfxmode/gfxpayload) et "couleurs".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gi.repository import Gtk
from loguru import logger

from ui.tabs.base import make_scrolled_grid
from ui.tabs.widgets import grid_add_check, grid_add_labeled

if TYPE_CHECKING:
    from ui.app import GrubConfigManager


_GRUB_COLORS: list[str] = [
    "black",
    "blue",
    "green",
    "cyan",
    "red",
    "magenta",
    "brown",
    "light-gray",
    "dark-gray",
    "light-blue",
    "light-green",
    "light-cyan",
    "light-red",
    "light-magenta",
    "yellow",
    "white",
]


def build_display_tab(controller: GrubConfigManager, notebook: Gtk.Notebook) -> None:
    """Build Display tab with GRUB theme options (colors, graphics mode).

    Creates dropdowns for color selection (normal/highlight foreground/background),
    text input for gfxmode and gfxpayload_linux, toggle for console terminal mode.
    """
    logger.debug("[build_display_tab] Construction de l'onglet Affichage")
    scroll, grid = make_scrolled_grid()

    row = 0

    title = Gtk.Label()
    title.set_markup("<b>Affichage</b>")
    title.set_halign(Gtk.Align.START)
    grid.attach(title, 0, row, 2, 1)
    row += 1

    note = Gtk.Label(xalign=0)
    note.set_markup("<i>Ces options influencent l'apparence du menu GRUB et l'affichage au boot.</i>")
    note.set_wrap(True)
    grid.attach(note, 0, row, 2, 1)
    row += 1

    # === Résolution graphique ===
    logger.debug("[build_display_tab] Création dropdown Gfxmode")
    controller.gfxmode_dropdown = Gtk.DropDown.new_from_strings(
        [
            "auto (défaut)",
            "640x480",
            "800x600",
            "1024x768",
            "1280x720",
            "1366x768",
            "1600x900",
            "1920x1080",
            "2560x1440",
        ]
    )
    controller.gfxmode_dropdown.connect("notify::selected", controller.on_modified)
    controller.gfxmode_dropdown.set_halign(Gtk.Align.START)
    controller.gfxmode_dropdown.set_size_request(220, -1)
    row = grid_add_labeled(grid, row, "Résolution du menu:", controller.gfxmode_dropdown)

    # === Gfxpayload (affichage du kernel) ===
    logger.debug("[build_display_tab] Création dropdown Gfxpayload")
    controller.gfxpayload_dropdown = Gtk.DropDown.new_from_strings(
        [
            "auto (défaut)",
            "keep",
            "text",
            "1024x768",
            "1280x720",
            "1366x768",
            "1600x900",
            "1920x1080",
        ]
    )
    controller.gfxpayload_dropdown.connect("notify::selected", controller.on_modified)
    controller.gfxpayload_dropdown.set_halign(Gtk.Align.START)
    controller.gfxpayload_dropdown.set_size_request(220, -1)
    row = grid_add_labeled(grid, row, "Affichage Linux (gfxpayload):", controller.gfxpayload_dropdown)

    # === Terminal couleur ===
    logger.debug("[build_display_tab] Création checkbox TerminalColor")
    controller.terminal_color_check = Gtk.CheckButton(label="Activer le terminal en couleur")
    controller.terminal_color_check.connect("toggled", controller.on_modified)
    row = grid_add_check(grid, row, controller.terminal_color_check)

    # === Couleurs ===
    sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    grid.attach(sep, 0, row, 2, 1)
    row += 1

    colors_title = Gtk.Label()
    colors_title.set_markup("<b>Couleurs du menu</b>")
    colors_title.set_halign(Gtk.Align.START)
    grid.attach(colors_title, 0, row, 2, 1)
    row += 1

    def _make_color_dropdown() -> Gtk.DropDown:
        """Create color selection dropdown with standard GRUB color palette.

        Returns dropdown populated with GRUB color names (black, red, green,
        yellow, blue, magenta, cyan, white).
        """
        dd = Gtk.DropDown.new_from_strings(["auto (défaut)", *_GRUB_COLORS])
        dd.set_halign(Gtk.Align.START)
        dd.set_size_request(220, -1)
        return dd

    # === Couleurs texte/fond pour mode normal et surlignage ===
    logger.debug("[build_display_tab] Création dropdowns couleurs")
    controller.color_normal_fg_dropdown = _make_color_dropdown()
    controller.color_normal_fg_dropdown.connect("notify::selected", controller.on_modified)
    row = grid_add_labeled(grid, row, "Texte (normal):", controller.color_normal_fg_dropdown)

    controller.color_normal_bg_dropdown = _make_color_dropdown()
    controller.color_normal_bg_dropdown.connect("notify::selected", controller.on_modified)
    row = grid_add_labeled(grid, row, "Fond (normal):", controller.color_normal_bg_dropdown)

    controller.color_highlight_fg_dropdown = _make_color_dropdown()
    controller.color_highlight_fg_dropdown.connect("notify::selected", controller.on_modified)
    row = grid_add_labeled(grid, row, "Texte (sélection):", controller.color_highlight_fg_dropdown)

    controller.color_highlight_bg_dropdown = _make_color_dropdown()
    controller.color_highlight_bg_dropdown.connect("notify::selected", controller.on_modified)
    _ = grid_add_labeled(grid, row, "Fond (sélection):", controller.color_highlight_bg_dropdown)

    notebook.append_page(scroll, Gtk.Label(label="Affichage"))
    logger.success("[build_display_tab] Onglet Affichage construit")
