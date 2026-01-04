"""Onglet Entrées de menu (GTK4)."""

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
)

if TYPE_CHECKING:
    from ui.ui_manager import GrubConfigManager


def build_entries_tab(controller: GrubConfigManager, notebook: Gtk.Notebook) -> None:
    """Build Entries tab showing boot menu entries with visibility toggles.

    Lists all available boot entries from grub.cfg with checkboxes to show/hide
    entries in menu. Changes persist to entry_visibility.json.
    """
    logger.debug("[build_entries_tab] Construction de l'onglet Entrées")
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    apply_margins(box, 12)

    box_append_section_title(box, "Entrées du menu")
    box_append_label(box, "Gérez la visibilité et les options des entrées de démarrage.", italic=True)

    # === Conteneur 2 colonnes ===
    _, left_section, right_section = create_two_column_layout(box)

    # === COLONNE GAUCHE : Liste des entrées ===
    box_append_section_title(left_section, "Liste des entrées")

    box_append_label(left_section, "Décochez pour masquer une entrée.", italic=True)

    # === Liste des entrées avec toggles ===
    logger.debug("[build_entries_tab] Création scrolled listbox pour entrées")
    list_frame = Gtk.Frame()
    list_frame.set_vexpand(True)
    left_section.append(list_frame)

    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_vexpand(True)

    controller.entries_listbox = Gtk.ListBox()
    controller.entries_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
    controller.entries_listbox.add_css_class("rich-list")
    scroll.set_child(controller.entries_listbox)
    list_frame.set_child(scroll)

    # two_columns.append(left_section) # Déjà ajouté par create_two_column_layout

    # === COLONNE DROITE : Options du menu ===
    box_append_section_title(right_section, "Options globales")

    box_append_label(right_section, "Ces options s'appliquent à tout le menu.", italic=True)

    # === Options d'affichage ===
    logger.debug("[build_entries_tab] Création switches options du menu")

    # Conteneur pour les switches
    switches_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    switches_box.set_margin_top(8)

    controller.disable_os_prober_check = Gtk.Switch()
    controller.disable_os_prober_check.connect("notify::active", controller.on_menu_options_toggled)
    controller.disable_os_prober_check.option_name = "Disable OS Prober"
    _add_styled_switch(
        switches_box,
        "Désactiver OS Prober",
        controller.disable_os_prober_check,
        "Ne pas détecter les autres systèmes (Windows, etc).",
    )

    controller.hide_advanced_options_check = Gtk.Switch()
    controller.hide_advanced_options_check.connect("notify::active", controller.on_hide_category_toggled)
    controller.hide_advanced_options_check.category_name = "advanced_options"
    _add_styled_switch(
        switches_box,
        "Masquer 'Advanced options'",
        controller.hide_advanced_options_check,
        "Cache les entrées avancées (noyau/paramètres) du menu.",
    )

    controller.hide_memtest_check = Gtk.Switch()
    controller.hide_memtest_check.connect("notify::active", controller.on_hide_category_toggled)
    controller.hide_memtest_check.category_name = "memtest"
    _add_styled_switch(
        switches_box,
        "Masquer 'memtest'",
        controller.hide_memtest_check,
        "Cache les entrées de test mémoire (memtest).",
    )

    right_section.append(switches_box)

    # Info box
    info_box = create_info_box(
        "Note:",
        "L'entrée par défaut se règle dans l'onglet Général.",
        css_class="warning-box",
    )
    right_section.append(info_box)

    # two_columns.append(right_section) # Déjà ajouté par create_two_column_layout

    notebook.append_page(box, Gtk.Label(label="Menu"))
    logger.success("[build_entries_tab] Onglet Entrées construit")


def _add_styled_switch(
    container: Gtk.Box, label_text: str, switch_widget: Gtk.Switch, description: str | None = None
) -> None:
    """Ajoute un switch avec label et description optionnelle dans un conteneur."""
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    vbox.set_hexpand(True)

    lbl = Gtk.Label(xalign=0, label=label_text)
    lbl.add_css_class("title-4")
    vbox.append(lbl)

    if description:
        desc = Gtk.Label(xalign=0, label=description)
        desc.set_wrap(True)
        desc.set_justify(Gtk.Justification.LEFT)
        desc.add_css_class("dim-label")
        desc.add_css_class("subtitle-label")
        vbox.append(desc)

    row.append(vbox)

    switch_widget.set_valign(Gtk.Align.CENTER)
    row.append(switch_widget)

    container.append(row)
    container.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
