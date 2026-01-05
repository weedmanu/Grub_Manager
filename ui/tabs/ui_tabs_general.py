"""Onglet Général (GTK4)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gi.repository import Gtk
from loguru import logger

from ui.builders.ui_builders_widgets import (
    LabelOptions,
    apply_margins,
    box_append_blue_section_grid,
    box_append_section_grid,
    create_info_box,
    create_tab_grid_layout,
    grid_add_labeled,
    grid_add_switch,
)

if TYPE_CHECKING:
    from ui.controllers.ui_controllers_manager import GrubConfigManager


def build_general_tab(controller: GrubConfigManager, notebook: Gtk.Notebook) -> None:
    """Build General tab with basic GRUB options (timeout, default, savedefault).

    Creates spinbox for boot delay, dropdown for default entry selection,
    and toggle switches for GRUB_SAVEDEFAULT and hidden timeout modes.
    """
    logger.debug("[build_general_tab] Construction de l'onglet Général")

    # Conteneur principal avec marges harmonisées
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    apply_margins(root, 12)

    root.append(
        create_info_box(
            "Configuration:",
            "Ces options modifient /etc/default/grub. Appliquez ensuite via update-grub.",
            css_class="info-box",
        )
    )

    # === Conteneur principal (Grid pour alignement par ligne) ===
    main_grid = create_tab_grid_layout(root)

    _build_base_options(controller, main_grid)
    _build_advanced_options(controller, main_grid)

    # ScrolledWindow pour l'ensemble
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_vexpand(True)
    scroll.set_child(root)

    notebook.append_page(scroll, Gtk.Label(label="Général"))
    logger.success("[build_general_tab] Onglet Général construit")


def _build_base_options(controller: GrubConfigManager, main_grid: Gtk.Grid) -> None:
    """Construit la section des options de base."""
    # --- LIGNE 0 : Options de base + Notes ---
    left_box_base = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    grid_left = box_append_blue_section_grid(left_box_base, "Options de base")

    row_left = 0

    # === Délai d'attente ===
    logger.debug("[build_general_tab] Création dropdown Timeout")
    controller.timeout_dropdown = Gtk.DropDown.new_from_strings(["0", "1", "2", "5", "10", "30"])
    controller.timeout_dropdown.connect("notify::selected", controller.on_modified)
    controller.timeout_dropdown.set_halign(Gtk.Align.FILL)
    controller.timeout_dropdown.set_hexpand(True)
    row_left = grid_add_labeled(
        grid_left,
        row_left,
        "Délai d'attente (s):",
        controller.timeout_dropdown,
        label=LabelOptions(css_class="label-green"),
    )

    # === Entrée par défaut ===
    logger.debug("[build_general_tab] Création dropdown Default")
    controller.default_dropdown = Gtk.DropDown.new_from_strings(["0", "saved (dernière sélection)"])
    controller.default_dropdown.connect("notify::selected", controller.on_modified)
    controller.default_dropdown.set_halign(Gtk.Align.FILL)
    controller.default_dropdown.set_hexpand(True)
    row_left = grid_add_labeled(
        grid_left,
        row_left,
        "Entrée par défaut:",
        controller.default_dropdown,
        label=LabelOptions(css_class="label-orange"),
    )

    # === Menu caché ===
    logger.debug("[build_general_tab] Création switch HiddenTimeout")
    controller.hidden_timeout_check = Gtk.Switch()
    controller.hidden_timeout_check.set_halign(Gtk.Align.START)
    controller.hidden_timeout_check.connect("notify::active", controller.on_hidden_timeout_toggled)
    row_left = grid_add_switch(
        grid_left,
        row_left,
        "Cacher le menu",
        controller.hidden_timeout_check,
        label_opts=LabelOptions(css_class="label-blue"),
    )

    main_grid.attach(left_box_base, 0, 0, 1, 1)

    # Notes pour les options de base
    right_box_base = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    right_box_base.append(
        create_info_box(
            "Délai d'attente:",
            "Le délai avant le démarrage automatique. '0' démarre instantanément.",
            css_class="success-box compact-card",
        )
    )
    right_box_base.append(
        create_info_box(
            "Entrée par défaut:",
            "Définit quel système démarre automatiquement.",
            css_class="warning-box compact-card",
        )
    )
    right_box_base.append(
        create_info_box(
            "Cacher le menu:",
            "Si activé, le menu GRUB ne s'affichera pas.",
            css_class="info-box compact-card",
        )
    )
    main_grid.attach(right_box_base, 1, 0, 1, 1)


def _build_advanced_options(controller: GrubConfigManager, main_grid: Gtk.Grid) -> None:
    """Construit la section des paramètres avancés."""
    # --- LIGNE 1 : Paramètres avancés + Note ---
    left_box_adv = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    grid_adv = box_append_section_grid(
        left_box_adv,
        "Paramètres avancés",
        row_spacing=12,
        column_spacing=12,
        title_class="orange",
        frame_class="orange-frame",
    )
    row_adv = 0

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
    controller.cmdline_dropdown.set_hexpand(True)
    row_adv = grid_add_labeled(
        grid_adv,
        row_adv,
        "Arguments Kernel:",
        controller.cmdline_dropdown,
        label=LabelOptions(css_class="label-red"),
    )

    main_grid.attach(left_box_adv, 0, 1, 1, 1)

    # Note pour les paramètres avancés
    right_box_adv = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    right_box_adv.append(
        create_info_box(
            "Arguments Kernel:",
            "Le mode 'quiet splash' affiche le logo.\nLe mode 'verbose' affiche les messages.",
            css_class="error-box compact-card",
        )
    )
    main_grid.attach(right_box_adv, 1, 1, 1, 1)
