"""Onglet Affichage (GTK4).

Fusion de la partie "graphique" (gfxmode/gfxpayload) et "couleurs".
"""

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
)

if TYPE_CHECKING:
    from ui.controllers.ui_controllers_manager import GrubConfigManager


def build_display_tab(controller: GrubConfigManager, notebook: Gtk.Notebook) -> None:
    """Build Display tab with basic GRUB display options.

    Inclut résolution graphique et mode terminal.
    """
    logger.debug("[build_display_tab] Construction de l'onglet Affichage")

    # Conteneur principal avec marges harmonisées
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    apply_margins(root, 12)

    root.append(
        create_info_box(
            "Affichage:",
            "Options de résolution et mode terminal GRUB.",
            css_class="info-box",
        )
    )

    # === Conteneur principal (Grid pour alignement par ligne) ===
    main_grid = create_tab_grid_layout(root)

    _build_menu_options(controller, main_grid)
    _build_kernel_options(controller, main_grid)

    # ScrolledWindow pour l'ensemble
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_vexpand(True)
    scroll.set_child(root)

    notebook.append_page(scroll, Gtk.Label(label="Affichage"))
    logger.success("[build_display_tab] Onglet Affichage construit")


def _build_menu_options(controller: GrubConfigManager, main_grid: Gtk.Grid) -> None:
    """Construit la section des options du menu GRUB."""
    # --- LIGNE 0 : Section Menu GRUB ---
    left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    grid_menu = box_append_blue_section_grid(left_box, "Menu GRUB")

    row = 0

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
    controller.gfxmode_dropdown.set_hexpand(True)
    row = grid_add_labeled(
        grid_menu,
        row,
        "Résolution:",
        controller.gfxmode_dropdown,
        label=LabelOptions(css_class="label-blue"),
    )

    # === Mode Terminal ===
    logger.debug("[build_display_tab] Création dropdown Terminal")
    controller.grub_terminal_dropdown = Gtk.DropDown.new_from_strings(
        [
            "gfxterm (graphique)",
            "console (texte)",
            "serial (série)",
            "gfxterm console",
        ]
    )
    controller.grub_terminal_dropdown.connect("notify::selected", controller.on_modified)
    controller.grub_terminal_dropdown.connect("notify::selected", lambda _w, _: _on_terminal_mode_changed(controller))
    controller.grub_terminal_dropdown.set_halign(Gtk.Align.FILL)
    controller.grub_terminal_dropdown.set_hexpand(True)
    row = grid_add_labeled(
        grid_menu,
        row,
        "Mode terminal:",
        controller.grub_terminal_dropdown,
        label=LabelOptions(css_class="label-blue"),
    )

    main_grid.attach(left_box, 0, 0, 1, 1)


def _build_kernel_options(controller: GrubConfigManager, main_grid: Gtk.Grid) -> None:
    """Construit la section des options du kernel."""
    # --- LIGNE 1 : Section Kernel (sous Menu GRUB) ---
    left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    grid_kernel = box_append_section_grid(
        left_box,
        "Système (Kernel)",
        row_spacing=12,
        column_spacing=12,
        title_class="orange",
        frame_class="orange-frame",
    )

    row = 0

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
    controller.gfxpayload_dropdown.set_hexpand(True)
    row = grid_add_labeled(
        grid_kernel,
        row,
        "Résolution:",
        controller.gfxpayload_dropdown,
        label=LabelOptions(css_class="label-orange"),
    )

    main_grid.attach(left_box, 0, 1, 1, 1)

    # --- COLONNE DROITE : Notes ---
    right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

    right_box.append(
        create_info_box(
            "Menu:",
            "Définit la résolution et le mode d'affichage du menu GRUB.\n"
            "• gfxterm : Mode graphique (thèmes, images)\n"
            "• console : Mode texte simple\n"
            "• serial : Sortie série",
            css_class="info-box compact-card",
        )
    )

    right_box.append(
        create_info_box(
            "Kernel:",
            "Résolution transmise au kernel Linux après le démarrage.\n"
            "• keep : Garde la résolution du menu GRUB\n"
            "• text : Force le mode texte\n"
            "• auto : Laisse le système décider",
            css_class="info-box compact-card",
        )
    )

    main_grid.attach(right_box, 1, 0, 1, 2)


def _on_terminal_mode_changed(controller: GrubConfigManager) -> None:
    """Gère le changement de mode terminal pour activer/désactiver les options graphiques et masquer l'onglet Thèmes.

    En mode texte (console/serial):
    - Désactive la résolution graphique (gfxmode)
    - Masque l'onglet "Thèmes" (thèmes graphiques)
    - Garde l'onglet "Apparence" visible (couleurs disponibles en mode texte)

    En mode graphique (gfxterm):
    - Active toutes les options
    - Affiche tous les onglets
    """
    if controller.grub_terminal_dropdown is None:
        return

    selected_text = controller.grub_terminal_dropdown.get_selected_item()
    if selected_text is not None:
        mode = selected_text.get_string().lower()
    else:
        mode = "gfxterm"

    # En mode console (texte pur), la résolution graphique et les thèmes graphiques n'ont pas de sens
    # Mais les couleurs (GRUB_COLOR_*) sont disponibles en mode texte
    is_graphical_mode = "gfxterm" in mode

    # Désactiver/activer le dropdown de résolution graphique
    if controller.gfxmode_dropdown is not None:
        controller.gfxmode_dropdown.set_sensitive(is_graphical_mode)

    # Masquer/afficher l'onglet "Thèmes" (pas "Apparence" qui gère les couleurs)
    if controller.notebook is not None:
        _toggle_theme_tabs_visibility(controller.notebook, is_graphical_mode)

    logger.debug(f"[_on_terminal_mode_changed] Mode: {mode}, Graphique activé: {is_graphical_mode}")


def _toggle_theme_tabs_visibility(notebook: Gtk.Notebook, show: bool) -> None:
    """Masque ou affiche l'onglet Thèmes selon le mode terminal.

    Note: L'onglet "Apparence" reste visible dans tous les modes car les couleurs
          sont configurables en mode texte. Seul "Thèmes" (thèmes graphiques) est masqué.

    Args:
        notebook: Le notebook GTK contenant les onglets
        show: True pour afficher l'onglet Thèmes (mode graphique), False pour le masquer (mode texte)
    """
    n_pages = notebook.get_n_pages()

    for i in range(n_pages):
        page = notebook.get_nth_page(i)
        if page is None:
            continue

        label_text = notebook.get_tab_label_text(page)
        # Seul l'onglet "Thèmes" (thèmes graphiques) est masqué en mode texte
        # "Apparence" reste visible car les couleurs sont disponibles en mode texte
        if label_text == "Thèmes":
            # Masquer/afficher la page
            notebook.get_page(page).set_property("tab-expand", show)
            page.set_visible(show)
            logger.debug(f"[_toggle_theme_tabs_visibility] Onglet '{label_text}': visible={show}")
