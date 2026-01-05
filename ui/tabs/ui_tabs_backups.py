"""Onglet Sauvegardes (GTK4)."""

from __future__ import annotations

import os
import tarfile
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
    create_two_column_layout,
)
from ui.dialogs.ui_dialogs_index import confirm_action


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


def _on_selection_changed(dropdown: Gtk.DropDown, _pspec, controller, restore_btn, delete_btn):
    """Active/désactive les boutons selon la sélection."""
    selected = dropdown.get_selected()
    backup_paths = getattr(controller, "backup_paths", [])
    has_selection = selected != Gtk.INVALID_LIST_POSITION and selected < len(backup_paths)
    restore_btn.set_sensitive(has_selection)
    delete_btn.set_sensitive(has_selection)


def _refresh_list(controller, dropdown: Gtk.DropDown, empty_label: Gtk.Label, restore_btn=None, delete_btn=None):
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
        dropdown.set_sensitive(False)
        dropdown.set_model(Gtk.StringList.new([]))
        dropdown.set_selected(Gtk.INVALID_LIST_POSITION)
        empty_label.set_visible(True)
        if restore_btn:
            restore_btn.set_sensitive(False)
        if delete_btn:
            delete_btn.set_sensitive(False)
        return

    empty_label.set_visible(False)
    dropdown.set_sensitive(True)
    dropdown.set_model(Gtk.StringList.new([_format_backup_label(p) for p in backups]))
    dropdown.set_selected(0)
    if restore_btn:
        restore_btn.set_sensitive(True)
    if delete_btn:
        delete_btn.set_sensitive(True)


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

    left_section.append(
        create_info_box(
            "Restauration:",
            "La restauration remplace votre configuration actuelle par celle de la sauvegarde sélectionnée.",
            css_class="info-box compact-card",
        )
    )

    controller.backups_dropdown = backups_dropdown
    return backups_dropdown, empty_label


def _build_backups_actions(
    right_section: Gtk.Box,
    *,
    controller,
    dropdown: Gtk.DropDown,
    empty_label: Gtk.Label,
) -> tuple[Gtk.Button, Gtk.Button]:
    # --- Section Création ---
    grid_create = box_append_section_grid(
        right_section,
        "Créer une sauvegarde",
        row_spacing=12,
        column_spacing=12,
        title_class="green",
        frame_class="green-frame",
    )

    create_btn = Gtk.Button(label="Créer une sauvegarde")
    create_btn.set_halign(Gtk.Align.FILL)
    create_btn.add_css_class("suggested-action")

    def refresh_cb() -> None:
        _refresh_list(controller, dropdown, empty_label, restore_btn, delete_btn)

    create_btn.connect("clicked", lambda b: _on_create_clicked(b, controller, refresh_cb))
    grid_create.attach(create_btn, 0, 0, 2, 1)

    right_section.append(
        create_info_box(
            "Sécurité:",
            "Il est recommandé de créer une sauvegarde avant toute modification importante.",
            css_class="success-box compact-card",
        )
    )

    # --- Section Actions ---
    grid_actions = box_append_section_grid(
        right_section,
        "Actions sur la sélection",
        row_spacing=12,
        column_spacing=12,
        title_class="orange",
        frame_class="orange-frame",
    )

    restore_btn = Gtk.Button(label="Restaurer la sélection")
    restore_btn.set_halign(Gtk.Align.FILL)
    restore_btn.add_css_class("suggested-action")
    restore_btn.set_sensitive(False)
    restore_btn.connect("clicked", lambda b: _on_restore_clicked(b, controller, dropdown))
    grid_actions.attach(restore_btn, 0, 0, 2, 1)

    delete_btn = Gtk.Button(label="Supprimer la sélection")
    delete_btn.set_halign(Gtk.Align.FILL)
    delete_btn.add_css_class("destructive-action")
    delete_btn.set_sensitive(False)
    delete_btn.connect("clicked", lambda b: _on_delete_clicked(b, controller, dropdown, refresh_cb))
    grid_actions.attach(delete_btn, 0, 1, 2, 1)

    return restore_btn, delete_btn


def build_backups_tab(controller: GrubConfigManager, notebook: Gtk.Notebook) -> None:
    """Build the Backups tab (list/create/delete)."""
    logger.debug("[build_backups_tab] Construction de l'onglet Sauvegardes")
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    apply_margins(root, 12)

    root.append(
        create_info_box(
            "Sauvegardes:",
            "Gestion des sauvegardes de la configuration GRUB.",
            css_class="info-box",
        )
    )

    # === Conteneur 2 colonnes ===
    _, left_section, right_section = create_two_column_layout(root, spacing=12)

    backups_dropdown, empty_label = _build_backups_selector(controller, left_section)
    restore_btn, delete_btn = _build_backups_actions(
        right_section,
        controller=controller,
        dropdown=backups_dropdown,
        empty_label=empty_label,
    )

    backups_dropdown.connect("notify::selected", _on_selection_changed, controller, restore_btn, delete_btn)
    _refresh_list(controller, backups_dropdown, empty_label, restore_btn, delete_btn)

    # === Ajout à l'onglet ===
    label = Gtk.Label(label="Sauvegardes")
    notebook.append_page(root, label)
    logger.debug("[build_backups_tab] Onglet Sauvegardes construit avec succès")
