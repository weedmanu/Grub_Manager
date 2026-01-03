"""Onglet Général (GTK4)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gi.repository import Gtk
from loguru import logger

from ui.ui_widgets import (
    apply_margins,
    box_append_label,
    box_append_section_title,
    create_info_box,
    create_two_column_layout,
    grid_add_labeled,
    grid_add_switch,
    make_scrolled_grid,
)

if TYPE_CHECKING:
    from ui.ui_manager import GrubConfigManager


def build_general_tab(controller: GrubConfigManager, notebook: Gtk.Notebook) -> None:
    """Build General tab with basic GRUB options (timeout, default, savedefault).

    Creates spinbox for boot delay, dropdown for default entry selection,
    and toggle switches for GRUB_SAVEDEFAULT and hidden timeout modes.
    """
    logger.debug("[build_general_tab] Construction de l'onglet Général")
    scroll, grid = make_scrolled_grid()

    # Conteneur principal avec marges harmonisées
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    apply_margins(root, 12)

    # Titre et description
    box_append_section_title(root, "Paramètres généraux")
    box_append_label(root, "Ces options modifient /etc/default/grub. Appliquez ensuite via update-grub.", italic=True)

    # === Conteneur 2 colonnes ===
    _, left_section, right_section = create_two_column_layout(root)

    # === COLONNE GAUCHE : Paramètres de base ===
    left_title = Gtk.Label(xalign=0)
    left_title.set_markup("<b>Options de base</b>")
    left_title.add_css_class("section-title")
    left_section.append(left_title)

    # Grid pour les formulaires de gauche
    grid_left = Gtk.Grid()
    grid_left.set_row_spacing(12)
    grid_left.set_column_spacing(12)
    left_section.append(grid_left)

    row_left = 0

    # === Délai d'attente ===
    logger.debug("[build_general_tab] Création dropdown Timeout")
    controller.timeout_dropdown = Gtk.DropDown.new_from_strings(["0", "1", "2", "5", "10", "30"])
    controller.timeout_dropdown.connect("notify::selected", controller.on_modified)
    controller.timeout_dropdown.set_halign(Gtk.Align.FILL)
    row_left = grid_add_labeled(grid_left, row_left, "Délai d'attente (s):", controller.timeout_dropdown)

    # === Entrée par défaut ===
    logger.debug("[build_general_tab] Création dropdown Default")
    controller.default_dropdown = Gtk.DropDown.new_from_strings(["0", "saved (dernière sélection)"])
    controller.default_dropdown.connect("notify::selected", controller.on_modified)
    controller.default_dropdown.set_halign(Gtk.Align.FILL)
    row_left = grid_add_labeled(grid_left, row_left, "Entrée par défaut:", controller.default_dropdown)

    # === Menu caché ===
    logger.debug("[build_general_tab] Création switch HiddenTimeout")
    controller.hidden_timeout_check = Gtk.Switch()
    controller.hidden_timeout_check.set_halign(Gtk.Align.START)
    controller.hidden_timeout_check.connect("notify::active", controller.on_hidden_timeout_toggled)
    row_left = grid_add_switch(grid_left, row_left, "Cacher le menu", controller.hidden_timeout_check)

    # two_columns.append(left_section) # Déjà ajouté par create_two_column_layout

    # === COLONNE DROITE : Paramètres avancés ===
    right_title = Gtk.Label(xalign=0)
    right_title.set_markup("<b>Paramètres avancés</b>")
    right_title.add_css_class("section-title")
    right_section.append(right_title)

    # Grid pour les formulaires de droite
    grid_right = Gtk.Grid()
    grid_right.set_row_spacing(12)
    grid_right.set_column_spacing(12)
    right_section.append(grid_right)

    row_right = 0

    # === Paramètres kernel ===
    kernel_label = Gtk.Label(xalign=0)
    kernel_label.set_markup("<b>Mode de démarrage (Kernel)</b>")
    grid_right.attach(kernel_label, 0, row_right, 2, 1)
    row_right += 1

    # Dropdown pour GRUB_CMDLINE_LINUX_DEFAULT
    logger.debug("[build_general_tab] Création dropdown Cmdline")
    controller.cmdline_dropdown = Gtk.DropDown.new_from_strings(
        [
            "quiet splash (recommandé)",
            "quiet",
            "splash",
            "verbose (aucun paramètre)",
        ]
    )
    controller.cmdline_dropdown.connect("notify::selected", controller.on_modified)
    controller.cmdline_dropdown.set_halign(Gtk.Align.FILL)
    row_right = grid_add_labeled(grid_right, row_right, "Arguments:", controller.cmdline_dropdown)

    # Info box
    info_box = create_info_box(
        "Note:",
        "Le mode 'quiet splash' affiche le logo de chargement.\nLe mode 'verbose' affiche tous les messages du noyau.",
    )
    right_section.append(info_box)

    # two_columns.append(right_section) # Déjà ajouté par create_two_column_layout

    # ScrolledWindow pour l'ensemble
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_vexpand(True)
    scroll.set_child(root)

    notebook.append_page(scroll, Gtk.Label(label="Général"))
    logger.success("[build_general_tab] Onglet Général construit")
