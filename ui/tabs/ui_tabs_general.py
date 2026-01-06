"""Onglet Général (GTK4)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gi.repository import Gtk
from loguru import logger

from ui.builders.ui_builders_widgets import (
    apply_margins,
    create_info_box,
    create_tab_grid_layout,
)
from ui.helpers.ui_helpers_gtk import GtkHelper

if TYPE_CHECKING:
    from ui.controllers.ui_controllers_manager import GrubConfigManager


def _build_note(*, title: str, text: str, css_class: str) -> Gtk.Widget:
    note = create_info_box(title, text, css_class=css_class)
    note.set_valign(Gtk.Align.START)
    note.set_vexpand(False)
    note.set_hexpand(False)
    return note


def _attach_row(*, main_grid: Gtk.Grid, row: int, left: Gtk.Widget, right: Gtk.Widget) -> None:
    main_grid.attach(left, 0, row, 1, 1)
    main_grid.attach(right, 1, row, 1, 1)


def _timeout_note_text(controller: GrubConfigManager) -> str:
    value = GtkHelper.dropdown_selected_text(getattr(controller, "timeout_dropdown", None))
    if value.isdigit():
        seconds = int(value)
        if seconds == 0:
            return "GRUB_TIMEOUT=0 : aucun délai au menu GRUB, " "démarrage immédiat de l'entrée par défaut."
        return (
            f"GRUB_TIMEOUT={seconds} : délai de {seconds}s au menu GRUB. "
            "Sans action, l'entrée par défaut démarre automatiquement."
        )
    return "Définit GRUB_TIMEOUT : délai avant démarrage automatique."


def _default_note_text(controller: GrubConfigManager) -> str:
    value = GtkHelper.dropdown_selected_text(getattr(controller, "default_dropdown", None))
    if value.startswith("saved"):
        return "GRUB_DEFAULT=saved : démarre la dernière entrée choisie dans GRUB (mémorisation)."
    if value.isdigit():
        return f"GRUB_DEFAULT={value} : démarre l'entrée d'index {value} " "(0 = première entrée du menu)."
    return "Définit GRUB_DEFAULT : entrée démarrée automatiquement."


def _hidden_note_text(controller: GrubConfigManager) -> str:
    sw = getattr(controller, "hidden_timeout_check", None)
    active = bool(sw.get_active()) if sw is not None else False
    if active:
        return (
            "Masque le menu : le PC démarre automatiquement sauf si vous maintenez "
            "une touche (ex: Shift/Esc) pour forcer l'affichage."
        )
    return "Menu visible : vous pouvez choisir l'entrée au démarrage."


def _update_label_text(label: Gtk.Label | None, text: str) -> None:
    if label is None:
        return
    label.set_text(text)


def _wire_base_dynamic_notes(
    *,
    controller: GrubConfigManager,
    timeout_note: Gtk.Widget,
    default_note: Gtk.Widget,
    hidden_note: Gtk.Widget,
) -> None:
    timeout_note_label = GtkHelper.info_box_text_label(timeout_note)
    default_note_label = GtkHelper.info_box_text_label(default_note)
    hidden_note_label = GtkHelper.info_box_text_label(hidden_note)

    def update_timeout(*_: object) -> None:
        _update_label_text(timeout_note_label, _timeout_note_text(controller))

    def update_default(*_: object) -> None:
        _update_label_text(default_note_label, _default_note_text(controller))

    def update_hidden(*_: object) -> None:
        _update_label_text(hidden_note_label, _hidden_note_text(controller))

    if getattr(controller, "timeout_dropdown", None) is not None:
        controller.timeout_dropdown.connect("notify::selected", update_timeout)
    if getattr(controller, "default_dropdown", None) is not None:
        controller.default_dropdown.connect("notify::selected", update_default)
    if getattr(controller, "hidden_timeout_check", None) is not None:
        controller.hidden_timeout_check.connect("notify::active", update_hidden)

    update_timeout()
    update_default()
    update_hidden()


def _cmdline_note_text(controller: GrubConfigManager) -> str:
    value = GtkHelper.dropdown_selected_text(getattr(controller, "cmdline_dropdown", None))
    if value.startswith("quiet splash"):
        args = "quiet splash"
        return f'GRUB_CMDLINE_LINUX_DEFAULT="{args}" : boot plus silencieux + écran de splash (logo).'
    if value == "quiet":
        args = "quiet"
        return f'GRUB_CMDLINE_LINUX_DEFAULT="{args}" : réduit les messages au boot (sans splash).'
    if value == "splash":
        args = "splash"
        return f'GRUB_CMDLINE_LINUX_DEFAULT="{args}" : active l\'écran splash ' "(messages possibles)."
    if value.startswith("verbose"):
        return (
            'GRUB_CMDLINE_LINUX_DEFAULT="" : aucun paramètre ' "(affiche davantage de messages, utile pour dépannage)."
        )
    return "Définit GRUB_CMDLINE_LINUX_DEFAULT : paramètres kernel au démarrage."


def _wire_cmdline_dynamic_note(*, controller: GrubConfigManager, cmdline_note: Gtk.Widget) -> None:
    cmdline_note_label = GtkHelper.info_box_text_label(cmdline_note)

    def update_cmdline(*_: object) -> None:
        _update_label_text(cmdline_note_label, _cmdline_note_text(controller))

    if getattr(controller, "cmdline_dropdown", None) is not None:
        controller.cmdline_dropdown.connect("notify::selected", update_cmdline)
    update_cmdline()


def _attach_timeout_option(*, controller: GrubConfigManager, main_grid: Gtk.Grid, row: int) -> Gtk.Widget:
    logger.debug("[build_general_tab] Création dropdown Timeout")
    controller.timeout_dropdown = Gtk.DropDown.new_from_strings(["0", "1", "2", "5", "10", "30"])
    controller.timeout_dropdown.connect("notify::selected", controller.on_modified)
    controller.timeout_dropdown.set_halign(Gtk.Align.FILL)
    controller.timeout_dropdown.set_hexpand(True)

    frame = GtkHelper.build_option_frame(
        frame_css_class="green-frame",
        label_markup="<b>Délai d'attente (s):</b>",
        widget=controller.timeout_dropdown,
    )
    note = _build_note(
        title="Délai d'attente:",
        text="Le délai avant le démarrage automatique. '0' démarre instantanément.",
        css_class="success-box compact-card",
    )
    _attach_row(main_grid=main_grid, row=row, left=frame, right=note)
    return note


def _attach_default_option(*, controller: GrubConfigManager, main_grid: Gtk.Grid, row: int) -> Gtk.Widget:
    logger.debug("[build_general_tab] Création dropdown Default")
    controller.default_dropdown = Gtk.DropDown.new_from_strings(["0", "saved (dernière sélection)"])
    controller.default_dropdown.connect("notify::selected", controller.on_modified)
    controller.default_dropdown.set_halign(Gtk.Align.FILL)
    controller.default_dropdown.set_hexpand(True)

    frame = GtkHelper.build_option_frame(
        frame_css_class="orange-frame",
        label_markup="<b>Entrée par défaut:</b>",
        widget=controller.default_dropdown,
    )
    note = _build_note(
        title="Entrée par défaut:",
        text="Définit quel système démarre automatiquement.",
        css_class="warning-box compact-card",
    )
    _attach_row(main_grid=main_grid, row=row, left=frame, right=note)
    return note


def _attach_hidden_option(*, controller: GrubConfigManager, main_grid: Gtk.Grid, row: int) -> Gtk.Widget:
    logger.debug("[build_general_tab] Création switch HiddenTimeout")
    controller.hidden_timeout_check = Gtk.Switch()
    controller.hidden_timeout_check.set_halign(Gtk.Align.START)
    controller.hidden_timeout_check.connect("notify::active", controller.on_hidden_timeout_toggled)

    frame = GtkHelper.build_option_frame(
        frame_css_class="blue-frame",
        label_markup="<b>Cacher le menu</b>",
        widget=controller.hidden_timeout_check,
    )
    note = _build_note(
        title="Cacher le menu:",
        text="Si activé, le menu GRUB ne s'affichera pas.",
        css_class="info-box compact-card",
    )
    _attach_row(main_grid=main_grid, row=row, left=frame, right=note)
    return note


def _attach_cmdline_option(*, controller: GrubConfigManager, main_grid: Gtk.Grid, row: int) -> Gtk.Widget:
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
    controller.cmdline_dropdown.set_hexpand(True)

    frame = GtkHelper.build_option_frame(
        frame_css_class="red-frame",
        label_markup="<b>Arguments Kernel:</b>",
        widget=controller.cmdline_dropdown,
    )
    note = _build_note(
        title="Arguments Kernel:",
        text="Le mode 'quiet splash' affiche le logo.\nLe mode 'verbose' affiche les messages.",
        css_class="error-box compact-card",
    )
    _attach_row(main_grid=main_grid, row=row, left=frame, right=note)
    return note


def build_general_tab(controller: GrubConfigManager, notebook: Gtk.Notebook) -> None:
    """Build General tab with basic GRUB options (timeout, default, savedefault).

    Creates spinbox for boot delay, dropdown for default entry selection,
    and toggle switches for GRUB_SAVEDEFAULT and hidden timeout modes.
    """
    logger.debug("[build_general_tab] Construction de l'onglet Général")

    # Conteneur principal avec marges harmonisées
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    apply_margins(root, 12)

    # === Conteneur principal (Grid pour alignement par ligne) ===
    main_grid = create_tab_grid_layout(root)
    # UX: plus d'espace entre les options (une option = une ligne).
    main_grid.set_row_spacing(26)

    next_row = _build_base_options(controller, main_grid, start_row=0)
    _build_advanced_options(controller, main_grid, start_row=next_row)

    # ScrolledWindow pour l'ensemble
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_vexpand(True)
    scroll.set_child(root)

    notebook.append_page(scroll, Gtk.Label(label="Général"))
    logger.success("[build_general_tab] Onglet Général construit")


def _build_base_options(controller: GrubConfigManager, main_grid: Gtk.Grid, *, start_row: int) -> int:
    """Construit les options de base, 1 option = 1 ligne (note en face, hors bloc)."""
    timeout_note = _attach_timeout_option(controller=controller, main_grid=main_grid, row=start_row)
    default_note = _attach_default_option(controller=controller, main_grid=main_grid, row=start_row + 1)
    hidden_note = _attach_hidden_option(controller=controller, main_grid=main_grid, row=start_row + 2)
    _wire_base_dynamic_notes(
        controller=controller,
        timeout_note=timeout_note,
        default_note=default_note,
        hidden_note=hidden_note,
    )
    return start_row + 3


def _build_advanced_options(controller: GrubConfigManager, main_grid: Gtk.Grid, *, start_row: int) -> None:
    """Construit les options avancées, 1 option = 1 ligne (note en face, hors bloc)."""
    cmdline_note = _attach_cmdline_option(controller=controller, main_grid=main_grid, row=start_row)
    _wire_cmdline_dynamic_note(controller=controller, cmdline_note=cmdline_note)
