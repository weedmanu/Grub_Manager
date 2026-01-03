"""Onglet Général (GTK4)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gi.repository import Gtk
from loguru import logger

from ui.ui_widgets import grid_add_check, grid_add_labeled, make_scrolled_grid

if TYPE_CHECKING:
    from ui.ui_manager import GrubConfigManager


def build_general_tab(controller: GrubConfigManager, notebook: Gtk.Notebook) -> None:
    """Build General tab with basic GRUB options (timeout, default, savedefault).

    Creates spinbox for boot delay, dropdown for default entry selection,
    and toggle switches for GRUB_SAVEDEFAULT and hidden timeout modes.
    """
    logger.debug("[build_general_tab] Construction de l'onglet Général")
    scroll, grid = make_scrolled_grid()

    row = 0

    title = Gtk.Label()
    title.set_markup("<b>Paramètres généraux</b>")
    title.set_halign(Gtk.Align.START)
    grid.attach(title, 0, row, 2, 1)
    row += 1

    note = Gtk.Label(xalign=0)
    note.set_markup("<i>Ces options modifient /etc/default/grub. Appliquez ensuite via update-grub.</i>")
    note.set_wrap(True)
    grid.attach(note, 0, row, 2, 1)
    row += 1

    # === Délai d'attente ===
    logger.debug("[build_general_tab] Création dropdown Timeout")
    controller.timeout_dropdown = Gtk.DropDown.new_from_strings(["0", "1", "2", "5", "10", "30"])
    controller.timeout_dropdown.connect("notify::selected", controller.on_modified)
    controller.timeout_dropdown.set_halign(Gtk.Align.START)
    controller.timeout_dropdown.set_size_request(220, -1)
    row = grid_add_labeled(grid, row, "Délai d'attente (secondes):", controller.timeout_dropdown)

    # === Entrée par défaut ===
    logger.debug("[build_general_tab] Création dropdown Default")
    controller.default_dropdown = Gtk.DropDown.new_from_strings(["0", "saved (dernière sélection)"])
    controller.default_dropdown.connect("notify::selected", controller.on_modified)
    controller.default_dropdown.set_halign(Gtk.Align.START)
    controller.default_dropdown.set_size_request(320, -1)
    row = grid_add_labeled(grid, row, "Entrée par défaut:", controller.default_dropdown)

    # === Menu caché ===
    logger.debug("[build_general_tab] Création checkbox HiddenTimeout")
    controller.hidden_timeout_check = Gtk.CheckButton(label="Cacher le menu (démarrage direct)")
    controller.hidden_timeout_check.connect("toggled", controller.on_hidden_timeout_toggled)
    row = grid_add_check(grid, row, controller.hidden_timeout_check)

    notebook.append_page(scroll, Gtk.Label(label="Général"))
    logger.success("[build_general_tab] Onglet Général construit")
