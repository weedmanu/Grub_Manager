"""Onglet Affichage (GTK4).

Fusion de la partie "graphique" (gfxmode/gfxpayload) et "couleurs".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gi.repository import Gtk
from loguru import logger

from ui.ui_widgets import (
    apply_margins,
    box_append_label,
    box_append_section_grid,
    box_append_section_title,
    create_two_column_layout,
    grid_add_labeled,
)

if TYPE_CHECKING:
    from ui.ui_manager import GrubConfigManager


def build_display_tab(controller: GrubConfigManager, notebook: Gtk.Notebook) -> None:
    """Build Display tab with basic GRUB display options.

    Note: Les options de mode terminal/graphique sont gérées dans l'onglet "Thèmes".
    Cet onglet ne contient que les options de résolution graphique.
    """
    logger.debug("[build_display_tab] Construction de l'onglet Affichage")

    # Conteneur principal avec marges harmonisées
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    apply_margins(root, 12)

    # Titre et description
    box_append_section_title(root, "Affichage")
    box_append_label(root, "Options de résolution graphique.", italic=True)

    # === Conteneur 2 colonnes ===
    _, left_section, right_section = create_two_column_layout(root)

    # === COLONNE GAUCHE : Résolution Menu ===
    grid_left = box_append_section_grid(left_section, "Résolution du Menu GRUB")

    row_left = 0

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
    controller.gfxmode_dropdown.set_halign(Gtk.Align.FILL)
    row_left = grid_add_labeled(grid_left, row_left, "Résolution:", controller.gfxmode_dropdown)

    # Explication gfxmode
    gfxmode_info = Gtk.Label(xalign=0)
    gfxmode_info.set_markup(
        "<small><i>Définit la résolution d'affichage du menu de sélection GRUB au démarrage.</i></small>"
    )
    gfxmode_info.set_wrap(True)
    gfxmode_info.set_margin_top(8)
    gfxmode_info.add_css_class("dim-label")
    left_section.append(gfxmode_info)

    # Checkbox couleur terminal
    controller.terminal_color_check = Gtk.CheckButton(label="Forcer le terminal en noir et blanc")
    controller.terminal_color_check.set_margin_top(12)
    controller.terminal_color_check.connect("toggled", controller.on_modified)
    left_section.append(controller.terminal_color_check)

    # === COLONNE DROITE : Résolution Kernel ===
    grid_right = box_append_section_grid(right_section, "Résolution du Système (Kernel)")

    row_right = 0

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
    controller.gfxpayload_dropdown.set_halign(Gtk.Align.FILL)
    row_right = grid_add_labeled(grid_right, row_right, "Résolution:", controller.gfxpayload_dropdown)

    # Explication gfxpayload
    gfxpayload_info = Gtk.Label(xalign=0)
    gfxpayload_info.set_markup(
        "<small><i>Résolution transmise au kernel Linux après le démarrage.\n"
        "• <b>keep</b> : Garde la résolution du menu GRUB\n"
        "• <b>text</b> : Force le mode texte\n"
        "• <b>auto</b> : Laisse le système décider</i></small>"
    )
    gfxpayload_info.set_wrap(True)
    gfxpayload_info.set_margin_top(8)
    gfxpayload_info.add_css_class("dim-label")
    right_section.append(gfxpayload_info)

    # two_columns.append(right_section) # Déjà ajouté par create_two_column_layout

    # ScrolledWindow pour l'ensemble
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_vexpand(True)
    scroll.set_child(root)

    notebook.append_page(scroll, Gtk.Label(label="Affichage"))
    logger.success("[build_display_tab] Onglet Affichage construit")
