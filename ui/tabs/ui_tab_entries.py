"""Onglet Entrées de menu (GTK4)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gi.repository import Gtk
from loguru import logger

from ui.ui_widgets import apply_margins, box_append_label, box_append_section_title

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
    box_append_label(box, "Activez le switch pour masquer une entrée.", italic=True)

    # === Liste des entrées avec toggles ===
    logger.debug("[build_entries_tab] Création scrolled listbox pour entrées")
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    scroll.set_vexpand(True)

    controller.entries_listbox = Gtk.ListBox()
    controller.entries_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
    scroll.set_child(controller.entries_listbox)
    box.append(scroll)

    box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

    box_append_section_title(box, "Options du menu")
    box_append_label(box, "Ces options influencent les entrées générées par GRUB.", italic=True)

    # === Options d'affichage ===
    logger.debug("[build_entries_tab] Création checkboxes options du menu")
    controller.disable_recovery_check = Gtk.CheckButton(label="Masquer les entrées de récupération")
    controller.disable_recovery_check.connect("toggled", controller.on_menu_options_toggled)
    controller.disable_recovery_check._option_name = "Disable Recovery"  # DEV: Pour logging
    box.append(controller.disable_recovery_check)

    controller.disable_os_prober_check = Gtk.CheckButton(label="Désactiver os-prober (ne pas détecter d'autres OS)")
    controller.disable_os_prober_check.connect("toggled", controller.on_menu_options_toggled)
    controller.disable_os_prober_check._option_name = "Disable OS Prober"  # DEV: Pour logging
    box.append(controller.disable_os_prober_check)

    controller.disable_submenu_check = Gtk.CheckButton(label="Désactiver les sous-menus")
    controller.disable_submenu_check.connect("toggled", controller.on_menu_options_toggled)
    controller.disable_submenu_check._option_name = "Disable Submenu"  # DEV: Pour logging
    box.append(controller.disable_submenu_check)

    box_append_label(box, "L'entrée par défaut se règle dans l'onglet Général.", italic=True)

    notebook.append_page(box, Gtk.Label(label="Menu"))
    logger.success("[build_entries_tab] Onglet Entrées construit")
