"""Onglet Affichage (GTK4).

Fusion de la partie "graphique" (gfxmode/gfxpayload) et "couleurs".
"""

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


def build_display_tab(controller: GrubConfigManager, notebook: Gtk.Notebook) -> None:
    """Build Display tab with basic GRUB display options.

    Inclut résolution graphique et mode terminal.
    """
    logger.debug("[build_display_tab] Construction de l'onglet Affichage")

    # Conteneur principal avec marges harmonisées
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    apply_margins(root, 12)

    # === Conteneur principal (Grid pour alignement par ligne) ===
    main_grid = create_tab_grid_layout(root)
    main_grid.set_row_spacing(26)

    # Utilisé par _on_terminal_mode_changed pour masquer/afficher l'onglet Thèmes.
    controller.notebook = notebook

    _build_display_options(controller, main_grid)

    # ScrolledWindow pour l'ensemble
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_vexpand(True)
    scroll.set_child(root)

    notebook.append_page(scroll, Gtk.Label(label="Affichage"))
    logger.success("[build_display_tab] Onglet Affichage construit")


def _build_display_options(controller: GrubConfigManager, main_grid: Gtk.Grid) -> None:
    """Construit les options d'affichage, 1 option = 1 ligne (note en face, hors bloc)."""
    row = 0

    gfxmode_frame, gfxmode_note = _build_gfxmode_row(controller)
    main_grid.attach(gfxmode_frame, 0, row, 1, 1)
    main_grid.attach(gfxmode_note, 1, row, 1, 1)
    row += 1

    terminal_frame, terminal_note = _build_terminal_row(controller)
    main_grid.attach(terminal_frame, 0, row, 1, 1)
    main_grid.attach(terminal_note, 1, row, 1, 1)
    row += 1

    payload_frame, payload_note = _build_payload_row(controller)
    main_grid.attach(payload_frame, 0, row, 1, 1)
    main_grid.attach(payload_note, 1, row, 1, 1)

    _wire_display_dynamic_notes(
        controller=controller,
        gfxmode_note=gfxmode_note,
        terminal_note=terminal_note,
        payload_note=payload_note,
    )


def _build_gfxmode_row(controller: GrubConfigManager) -> tuple[Gtk.Frame, Gtk.Widget]:
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
    controller.gfxmode_dropdown.set_valign(Gtk.Align.START)

    frame = GtkHelper.build_option_frame(
        frame_css_class="blue-frame",
        label_markup="<b>Résolution (menu):</b>",
        widget=controller.gfxmode_dropdown,
    )

    note = create_info_box(
        "Résolution (menu):",
        "Définit GRUB_GFXMODE.",
        css_class="success-box compact-card",
    )
    note.set_valign(Gtk.Align.START)
    note.set_vexpand(False)
    note.set_hexpand(False)
    return frame, note


def _build_terminal_row(controller: GrubConfigManager) -> tuple[Gtk.Frame, Gtk.Widget]:
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
    controller.grub_terminal_dropdown.connect("notify::selected", lambda *_: _on_terminal_mode_changed(controller))
    controller.grub_terminal_dropdown.set_halign(Gtk.Align.FILL)
    controller.grub_terminal_dropdown.set_hexpand(True)
    controller.grub_terminal_dropdown.set_valign(Gtk.Align.START)

    frame = GtkHelper.build_option_frame(
        frame_css_class="blue-frame",
        label_markup="<b>Mode terminal:</b>",
        widget=controller.grub_terminal_dropdown,
    )

    note = create_info_box(
        "Mode terminal:",
        "Définit GRUB_TERMINAL.",
        css_class="warning-box compact-card",
    )
    note.set_valign(Gtk.Align.START)
    note.set_vexpand(False)
    note.set_hexpand(False)
    return frame, note


def _build_payload_row(controller: GrubConfigManager) -> tuple[Gtk.Frame, Gtk.Widget]:
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
    controller.gfxpayload_dropdown.set_valign(Gtk.Align.START)

    frame = GtkHelper.build_option_frame(
        frame_css_class="orange-frame",
        label_markup="<b>Résolution (kernel):</b>",
        widget=controller.gfxpayload_dropdown,
    )

    note = create_info_box(
        "Résolution (kernel):",
        "Définit GRUB_GFXPAYLOAD_LINUX.",
        css_class="info-box compact-card",
    )
    note.set_valign(Gtk.Align.START)
    note.set_vexpand(False)
    note.set_hexpand(False)
    return frame, note


def _wire_display_dynamic_notes(
    *,
    controller: GrubConfigManager,
    gfxmode_note: Gtk.Widget,
    terminal_note: Gtk.Widget,
    payload_note: Gtk.Widget,
) -> None:
    gfxmode_note_label = GtkHelper.info_box_text_label(gfxmode_note)
    terminal_note_label = GtkHelper.info_box_text_label(terminal_note)
    payload_note_label = GtkHelper.info_box_text_label(payload_note)

    def _is_graphical_terminal_mode() -> bool:
        mode = GtkHelper.dropdown_selected_text(getattr(controller, "grub_terminal_dropdown", None)).lower()
        return "gfxterm" in mode

    def _update_terminal_note() -> None:
        if terminal_note_label is None:
            return
        selected = GtkHelper.dropdown_selected_text(getattr(controller, "grub_terminal_dropdown", None)).lower()
        if selected.startswith("gfxterm") and "console" not in selected:
            terminal_note_label.set_text("GRUB_TERMINAL=gfxterm : menu graphique (thèmes/images possibles).")
        elif selected.startswith("console"):
            terminal_note_label.set_text("GRUB_TERMINAL=console : menu texte (thèmes/images désactivés).")
        elif selected.startswith("serial"):
            terminal_note_label.set_text("GRUB_TERMINAL=serial : menu sur port série (utile pour dépannage).")
        elif "gfxterm" in selected and "console" in selected:
            terminal_note_label.set_text('GRUB_TERMINAL="gfxterm console" : menu graphique + console disponible.')
        else:
            terminal_note_label.set_text("Définit GRUB_TERMINAL : mode d'affichage du menu.")

    def _update_gfxmode_note() -> None:
        if gfxmode_note_label is None:
            return
        if not _is_graphical_terminal_mode():
            gfxmode_note_label.set_text(
                "Désactivé : en mode terminal texte, la résolution graphique du menu ne s'applique pas."
            )
            return

        selected = GtkHelper.dropdown_selected_text(getattr(controller, "gfxmode_dropdown", None))
        if selected.startswith("auto"):
            gfxmode_note_label.set_text(
                "GRUB_GFXMODE=auto : GRUB choisit automatiquement la meilleure résolution pour le menu."
            )
        else:
            gfxmode_note_label.set_text(f"GRUB_GFXMODE={selected} : affiche le menu GRUB en {selected}.")

    def _update_payload_note() -> None:
        if payload_note_label is None:
            return
        selected = GtkHelper.dropdown_selected_text(getattr(controller, "gfxpayload_dropdown", None))
        if selected.startswith("auto"):
            payload_note_label.set_text("Auto : laisse le kernel décider du mode d'affichage pendant le démarrage.")
        elif selected == "keep":
            payload_note_label.set_text(
                "GRUB_GFXPAYLOAD_LINUX=keep : conserve la résolution du menu pour le démarrage du kernel."
            )
        elif selected == "text":
            payload_note_label.set_text("GRUB_GFXPAYLOAD_LINUX=text : force le mode texte pendant le démarrage.")
        else:
            payload_note_label.set_text(
                f"GRUB_GFXPAYLOAD_LINUX={selected} : force la résolution {selected} pendant le démarrage."
            )

    if getattr(controller, "gfxmode_dropdown", None) is not None:
        controller.gfxmode_dropdown.connect("notify::selected", lambda *_: _update_gfxmode_note())
    if getattr(controller, "grub_terminal_dropdown", None) is not None:
        controller.grub_terminal_dropdown.connect("notify::selected", lambda *_: _update_terminal_note())
        controller.grub_terminal_dropdown.connect("notify::selected", lambda *_: _update_gfxmode_note())
    if getattr(controller, "gfxpayload_dropdown", None) is not None:
        controller.gfxpayload_dropdown.connect("notify::selected", lambda *_: _update_payload_note())

    _on_terminal_mode_changed(controller)
    _update_terminal_note()
    _update_gfxmode_note()
    _update_payload_note()


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
            # Masquer/afficher la page (sans altérer le layout des tabs)
            page.set_visible(show)
            logger.debug(f"[_toggle_theme_tabs_visibility] Onglet '{label_text}': visible={show}")
