"""Onglet Affichage (GTK4).

Fusion de la partie "graphique" (gfxmode/gfxpayload) et "couleurs".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gi.repository import Gtk
from loguru import logger

from ui.ui_widgets import grid_add_check, grid_add_labeled, make_scrolled_grid

if TYPE_CHECKING:
    from ui.ui_manager import GrubConfigManager


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
    """Build Display tab with basic GRUB display options.

    Note: Les couleurs et thèmes sont maintenant gérés dans l'onglet "Thèmes".
    Cet onglet ne contient que les options de base d'affichage.
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
    note.set_markup(
        "<i>Options de résolution graphique. "
        "Pour personnaliser les couleurs et l'apparence, utilisez l'onglet <b>Thèmes</b>.</i>"
    )
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

    # Espacement
    spacer = Gtk.Label(label="")
    spacer.set_vexpand(True)
    grid.attach(spacer, 0, row, 2, 1)
    row += 1

    # Information sur les thèmes
    info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    info_box.set_margin_top(20)

    info_title = Gtk.Label()
    info_title.set_markup("<b>Personnalisation visuelle</b>")
    info_title.set_xalign(0)
    info_box.append(info_title)

    info_text = Gtk.Label(xalign=0)
    info_text.set_markup(
        "Pour personnaliser l'apparence complète de GRUB (couleurs, images de fond, "
        "polices, mise en page), utilisez les onglets:\n\n"
        "• <b>Thèmes</b> - Sélectionner et activer un thème existant\n"
        "• <b>Éditeur de thèmes</b> - Créer un thème personnalisé"
    )
    info_text.set_wrap(True)
    info_box.append(info_text)

    grid.attach(info_box, 0, row, 2, 1)

    notebook.append_page(scroll, Gtk.Label(label="Affichage"))
    logger.success("[build_display_tab] Onglet Affichage construit")
