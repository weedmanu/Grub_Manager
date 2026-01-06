"""Onglet Sauvegardes (GTK4)."""

from __future__ import annotations

import os
import tarfile
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from gi.repository import Gtk
from loguru import logger

from core.core_exceptions import GrubBackupError
from core.io.core_io_grub_default import (
    create_grub_default_backup,
    delete_grub_default_backup,
    list_grub_default_backups,
    restore_grub_default_backup,
)
from ui.builders.ui_builders_widgets import (
    apply_margins,
    box_append_section_grid,
    create_info_box,
    create_tab_grid_layout,
    create_titled_frame,
)
from ui.dialogs.ui_dialogs_index import confirm_action
from ui.helpers.ui_helpers_gtk import GtkHelper


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def _format_backup_label(backup_path: str) -> str:
    basename = os.path.basename(backup_path)
    try:
        mtime = os.path.getmtime(backup_path)
        size = os.path.getsize(backup_path)
        date_str = datetime.fromtimestamp(mtime).strftime("%d/%m/%Y")
        size_str = _format_size(size)
        return f"{basename} — {date_str} — {size_str}"
    except OSError:
        return basename


def _on_create_clicked(_btn, controller, refresh_callback):
    """Callback pour créer une sauvegarde."""
    logger.info("[_on_create_clicked] Création d'une nouvelle sauvegarde")

    # Vérifier les droits root
    if os.geteuid() != 0:
        controller.show_info("Droits administrateur requis pour créer une sauvegarde", "error")
        return

    try:
        backup_path = create_grub_default_backup()

        # Vérifier que le fichier existe et est valide
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Le fichier de sauvegarde n'a pas été créé: {backup_path}")

        # Vérifier que c'est un fichier tar.gz valide
        try:
            with tarfile.open(backup_path, "r:gz") as tar:
                members = tar.getnames()
                if not members:
                    raise ValueError("L'archive tar.gz est vide")
        except tarfile.TarError as e:
            raise ValueError(f"Archive tar.gz invalide: {e}") from e

        controller.show_info(f"Sauvegarde créée avec succès:\n{os.path.basename(backup_path)}", "info")
        refresh_callback()
    except (OSError, ValueError, RuntimeError, GrubBackupError) as e:
        logger.error(f"[_on_create_clicked] ERREUR: {e}")
        controller.show_info(f"Échec de la création:\n{e}", "error")


def _on_restore_clicked(_btn, controller, dropdown: Gtk.DropDown | None):
    """Callback pour restaurer une sauvegarde."""
    # Vérifier les droits root
    if os.geteuid() != 0:
        controller.show_info("Droits administrateur requis pour restaurer une sauvegarde", "error")
        return

    if dropdown is None:
        return

    selected = dropdown.get_selected()
    backup_paths = getattr(controller, "backup_paths", [])
    if selected == Gtk.INVALID_LIST_POSITION or selected >= len(backup_paths):
        controller.show_info("Veuillez sélectionner une sauvegarde à restaurer.", "warning")
        return

    backup_path = backup_paths[selected]
    basename = os.path.basename(backup_path)

    logger.info(f"[_on_restore_clicked] Restauration de {basename}")

    def do_restore():
        try:
            restore_grub_default_backup(backup_path)
            logger.info(f"[_on_restore_clicked] Restauration réussie de {basename}")
            msg = f"Sauvegarde restaurée avec succès:\n{basename}" "\n\nRedémarrez pour appliquer les changements."
            controller.show_info(msg, "info")
            controller.load_config()
        except (FileNotFoundError, OSError, PermissionError, ValueError, RuntimeError, GrubBackupError) as e:
            logger.error(f"[_on_restore_clicked] ERREUR: {e}")
            controller.show_info(f"Échec de la restauration:\n{e}", "error")

    confirm_action(
        do_restore,
        f"Restaurer la sauvegarde '{basename}' ?\n\nToutes les modifications non enregistrées seront perdues.",
        controller,
    )


def _on_delete_clicked(_btn, controller, dropdown: Gtk.DropDown | None, refresh_callback):
    """Callback pour supprimer une sauvegarde."""
    # Vérifier les droits root
    if os.geteuid() != 0:
        controller.show_info("Droits administrateur requis pour supprimer une sauvegarde", "error")
        return

    if dropdown is None:
        return

    selected = dropdown.get_selected()
    backup_paths = getattr(controller, "backup_paths", [])
    if selected == Gtk.INVALID_LIST_POSITION or selected >= len(backup_paths):
        controller.show_info("Veuillez sélectionner une sauvegarde à supprimer.", "warning")
        return

    backup_path = backup_paths[selected]
    basename = os.path.basename(backup_path)

    logger.info(f"[_on_delete_clicked] Suppression de {basename}")

    def do_delete():
        try:
            delete_grub_default_backup(backup_path)
            logger.info(f"[_on_delete_clicked] Suppression réussie de {basename}")
            controller.show_info(f"Sauvegarde supprimée:\n{basename}", "info")
            refresh_callback()
        except (FileNotFoundError, OSError, PermissionError, ValueError, RuntimeError, GrubBackupError) as e:
            logger.error(f"[_on_delete_clicked] ERREUR: {e}")
            controller.show_info(f"Échec de la suppression:\n{e}", "error")

    confirm_action(do_delete, f"Supprimer définitivement la sauvegarde '{basename}' ?", controller)


if TYPE_CHECKING:
    from ui.controllers.ui_controllers_manager import GrubConfigManager


@dataclass(slots=True)
class _BackupsUiRefs:
    dropdown: Gtk.DropDown
    empty_label: Gtk.Label
    restore_btn: Gtk.Button
    delete_btn: Gtk.Button
    selection_note_label: Gtk.Label | None


@dataclass(slots=True)
class _ActionRowSpec:
    row: int
    title: str
    button: Gtk.Button
    title_class: str
    frame_class: str
    note: tuple[str, str, str]


def _update_selection_note(*, controller, ui: _BackupsUiRefs) -> None:
    if ui.selection_note_label is None:
        return

    selected = ui.dropdown.get_selected()
    backup_paths = getattr(controller, "backup_paths", [])
    if not backup_paths or selected == Gtk.INVALID_LIST_POSITION or selected >= len(backup_paths):
        ui.selection_note_label.set_label("Aucune sauvegarde sélectionnée.")
        return

    backup_path = backup_paths[selected]
    ui.selection_note_label.set_label("Sauvegarde sélectionnée :\n" f"{_format_backup_label(backup_path)}")


def _on_selection_changed_impl(
    dropdown: Gtk.DropDown,
    _pspec,
    controller,
    ui: _BackupsUiRefs,
):
    """Active/désactive les boutons et met à jour la note de sélection."""
    selected = dropdown.get_selected()
    backup_paths = getattr(controller, "backup_paths", [])
    has_selection = selected != Gtk.INVALID_LIST_POSITION and selected < len(backup_paths)
    ui.restore_btn.set_sensitive(has_selection)
    ui.delete_btn.set_sensitive(has_selection)
    _update_selection_note(controller=controller, ui=ui)


def _on_selection_changed(
    dropdown: Gtk.DropDown,
    pspec,
    controller,
    restore_btn_or_ui,
    delete_btn=None,
):
    """Compat + impl.

    - Ancien appel tests: `_on_selection_changed(dropdown, pspec, controller, btn_restore, btn_delete)`
    - Nouvel appel interne: `_on_selection_changed(dropdown, pspec, controller, ui)`
    """
    if isinstance(restore_btn_or_ui, _BackupsUiRefs):
        _on_selection_changed_impl(dropdown, pspec, controller, restore_btn_or_ui)
        return

    ui = _BackupsUiRefs(
        dropdown=dropdown,
        empty_label=Gtk.Label(),
        restore_btn=restore_btn_or_ui,
        delete_btn=delete_btn or Gtk.Button(),
        selection_note_label=None,
    )
    _on_selection_changed_impl(dropdown, pspec, controller, ui)


def _refresh_list_impl(*, controller, ui: _BackupsUiRefs):
    """Rafraîchit l'affichage de la liste."""
    try:
        backups = list_grub_default_backups()
        logger.debug(f"[_load_backups] {len(backups)} sauvegarde(s) trouvée(s)")
    except OSError as e:
        logger.error(f"[_load_backups] ERREUR: {e}")
        controller.show_info(f"Impossible de lister les sauvegardes: {e}", "error")
        backups = []

    controller.backup_paths = backups

    if not backups:
        ui.dropdown.set_sensitive(False)
        ui.dropdown.set_model(Gtk.StringList.new([]))
        ui.dropdown.set_selected(Gtk.INVALID_LIST_POSITION)
        ui.empty_label.set_visible(True)
        ui.restore_btn.set_sensitive(False)
        ui.delete_btn.set_sensitive(False)
        if ui.selection_note_label is not None:
            ui.selection_note_label.set_label("Aucune sauvegarde disponible.")
        return

    ui.empty_label.set_visible(False)
    ui.dropdown.set_sensitive(True)
    ui.dropdown.set_model(Gtk.StringList.new([_format_backup_label(p) for p in backups]))
    ui.dropdown.set_selected(0)
    ui.restore_btn.set_sensitive(True)
    ui.delete_btn.set_sensitive(True)
    _update_selection_note(controller=controller, ui=ui)


def _refresh_list(
    controller=None,
    dropdown: Gtk.DropDown | None = None,
    empty_label: Gtk.Label | None = None,
    restore_btn=None,
    delete_btn=None,
    *,
    ui: _BackupsUiRefs | None = None,
) -> None:
    # pylint: disable=too-many-arguments
    """Compat + impl.

    - Ancien appel tests: `_refresh_list(controller, dropdown, empty_label, btn_restore, btn_delete)`
    - Nouvel appel interne: `_refresh_list(controller=..., ui=...)`
    """
    if controller is None:
        raise TypeError("_refresh_list() missing required argument: controller")

    if ui is None:
        if dropdown is None or empty_label is None:
            raise TypeError("_refresh_list() requires either ui=... or (dropdown, empty_label)")
        ui = _BackupsUiRefs(
            dropdown=dropdown,
            empty_label=empty_label,
            restore_btn=restore_btn or Gtk.Button(),
            delete_btn=delete_btn or Gtk.Button(),
            selection_note_label=None,
        )

    _refresh_list_impl(controller=controller, ui=ui)


def _build_selection_row(
    *,
    controller: GrubConfigManager,
    main_grid: Gtk.Grid,
    row: int,
) -> tuple[Gtk.DropDown, Gtk.Label, Gtk.Label | None]:
    left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    left.set_hexpand(True)
    left.set_vexpand(False)
    left.set_valign(Gtk.Align.START)
    main_grid.attach(left, 0, row, 1, 1)

    dropdown, empty_label = _build_backups_selector(controller, left)

    selection_note = create_info_box(
        "Sélection:",
        "Choisissez une sauvegarde dans la liste.",
        css_class="info-box compact-card",
    )
    selection_note.set_hexpand(False)
    selection_note.set_vexpand(False)
    selection_note.set_valign(Gtk.Align.START)
    selection_note_label = GtkHelper.info_box_text_label(selection_note)
    main_grid.attach(selection_note, 1, row, 1, 1)
    return dropdown, empty_label, selection_note_label


def _build_action_row(
    *,
    main_grid: Gtk.Grid,
    spec: _ActionRowSpec,
) -> None:
    left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    apply_margins(left, 12)
    left.set_hexpand(True)
    left.set_vexpand(False)
    left.set_valign(Gtk.Align.START)
    left.append(spec.button)

    block = create_titled_frame(
        spec.title,
        left,
        title_class=spec.title_class,
        frame_class=spec.frame_class,
    )
    block.set_vexpand(False)
    block.set_valign(Gtk.Align.START)
    main_grid.attach(block, 0, spec.row, 1, 1)

    note_title, note_text, note_css = spec.note
    note = create_info_box(note_title, note_text, css_class=note_css)
    note.set_hexpand(False)
    note.set_vexpand(False)
    note.set_valign(Gtk.Align.START)
    main_grid.attach(note, 1, spec.row, 1, 1)


def _build_backups_selector(controller, left_section: Gtk.Box) -> tuple[Gtk.DropDown, Gtk.Label]:
    grid = box_append_section_grid(
        left_section,
        "Sauvegardes disponibles",
        row_spacing=12,
        column_spacing=12,
        title_class="blue",
        frame_class="blue-frame",
    )

    backups_dropdown = Gtk.DropDown.new_from_strings([])
    backups_dropdown.set_hexpand(True)
    grid.attach(backups_dropdown, 0, 0, 2, 1)

    empty_label = Gtk.Label(label="📭 Aucune sauvegarde trouvée")
    empty_label.add_css_class("dim-label")
    empty_label.set_visible(False)
    grid.attach(empty_label, 0, 1, 2, 1)

    controller.backups_dropdown = backups_dropdown
    return backups_dropdown, empty_label


def build_backups_tab(controller: GrubConfigManager, notebook: Gtk.Notebook) -> None:
    """Build the Backups tab (list/create/delete)."""
    logger.debug("[build_backups_tab] Construction de l'onglet Sauvegardes")
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    apply_margins(root, 12)

    # === Template comme Général/Affichage: grille 2 colonnes (options à gauche, notes à droite) ===
    main_grid = create_tab_grid_layout(root)

    backups_dropdown, empty_label, selection_note_label = _build_selection_row(
        controller=controller,
        main_grid=main_grid,
        row=0,
    )

    create_btn = Gtk.Button(label="Créer une sauvegarde")
    create_btn.set_halign(Gtk.Align.FILL)
    create_btn.add_css_class("suggested-action")
    _build_action_row(
        main_grid=main_grid,
        spec=_ActionRowSpec(
            row=1,
            title="Créer une sauvegarde",
            button=create_btn,
            title_class="green",
            frame_class="green-frame",
            note=(
                "Créer:",
                "Crée une nouvelle sauvegarde de /etc/default/grub.",
                "success-box compact-card",
            ),
        ),
    )

    restore_btn = Gtk.Button(label="Restaurer la sélection")
    restore_btn.set_halign(Gtk.Align.FILL)
    restore_btn.add_css_class("suggested-action")
    restore_btn.set_sensitive(False)
    _build_action_row(
        main_grid=main_grid,
        spec=_ActionRowSpec(
            row=2,
            title="Restaurer",
            button=restore_btn,
            title_class="blue",
            frame_class="blue-frame",
            note=(
                "Restaurer:",
                "Restaure la sauvegarde sélectionnée (droits administrateur requis).",
                "info-box compact-card",
            ),
        ),
    )

    delete_btn = Gtk.Button(label="Supprimer la sélection")
    delete_btn.set_halign(Gtk.Align.FILL)
    delete_btn.add_css_class("destructive-action")
    delete_btn.set_sensitive(False)
    _build_action_row(
        main_grid=main_grid,
        spec=_ActionRowSpec(
            row=3,
            title="Supprimer",
            button=delete_btn,
            title_class="red",
            frame_class="red-frame",
            note=(
                "Supprimer:",
                "Supprime définitivement la sauvegarde sélectionnée (droits administrateur requis).",
                "error-box compact-card",
            ),
        ),
    )

    ui = _BackupsUiRefs(
        dropdown=backups_dropdown,
        empty_label=empty_label,
        restore_btn=restore_btn,
        delete_btn=delete_btn,
        selection_note_label=selection_note_label,
    )

    def refresh_cb() -> None:
        _refresh_list(controller=controller, ui=ui)

    create_btn.connect("clicked", lambda b: _on_create_clicked(b, controller, refresh_cb))
    restore_btn.connect("clicked", lambda b: _on_restore_clicked(b, controller, backups_dropdown))
    delete_btn.connect("clicked", lambda b: _on_delete_clicked(b, controller, backups_dropdown, refresh_cb))

    backups_dropdown.connect(
        "notify::selected",
        _on_selection_changed,
        controller,
        ui,
    )
    _refresh_list(controller=controller, ui=ui)

    # === Ajout à l'onglet ===
    label = Gtk.Label(label="Sauvegardes")
    notebook.append_page(root, label)
    logger.debug("[build_backups_tab] Onglet Sauvegardes construit avec succès")
