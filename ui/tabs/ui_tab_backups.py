"""Onglet Sauvegardes (GTK4)."""

# pylint: disable=too-many-statements

from __future__ import annotations

import os
import tarfile
from datetime import datetime
from typing import TYPE_CHECKING

from gi.repository import Gtk
from loguru import logger

from core.core_exceptions import GrubBackupError
from core.io.core_grub_default_io import (
    create_grub_default_backup,
    delete_grub_default_backup,
    list_grub_default_backups,
    restore_grub_default_backup,
)
from ui.ui_dialogs import confirm_action
from ui.ui_widgets import apply_margins, box_append_label, box_append_section_title, create_two_column_layout


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
        controller.show_info(f"❌ Échec de la création:\n{e}", "error")


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
            msg = f"✅ Sauvegarde restaurée avec succès:\n{basename}" "\n\nRedémarrez pour appliquer les changements."
            controller.show_info(msg, "info")
            controller.load_config()
        except (OSError, PermissionError, ValueError, RuntimeError) as e:
            logger.error(f"[_on_restore_clicked] ERREUR: {e}")
            controller.show_info(f"❌ Échec de la restauration:\n{e}", "error")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[_on_restore_clicked] ERREUR: {e}")
            controller.show_info(f"❌ Échec de la restauration:\n{e}", "error")

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
            controller.show_info(f"✅ Sauvegarde supprimée:\n{basename}", "info")
            refresh_callback()
        except (OSError, PermissionError, ValueError, RuntimeError) as e:
            logger.error(f"[_on_delete_clicked] ERREUR: {e}")
            controller.show_info(f"❌ Échec de la suppression:\n{e}", "error")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[_on_delete_clicked] ERREUR: {e}")
            controller.show_info(f"❌ Échec de la suppression:\n{e}", "error")

    confirm_action(do_delete, f"Supprimer définitivement la sauvegarde '{basename}' ?", controller)


if TYPE_CHECKING:
    from ui.ui_manager import GrubConfigManager


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


def build_backups_tab(controller: GrubConfigManager, notebook: Gtk.Notebook) -> None:
    """Build the Backups tab (list/create/delete)."""
    # pylint: disable=too-many-locals
    logger.debug("[build_backups_tab] Construction de l'onglet Sauvegardes")
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    apply_margins(root, 12)

    box_append_section_title(root, "Sauvegardes")
    box_append_label(root, "Gestion des sauvegardes de la configuration GRUB.", italic=True)

    # === Conteneur 2 colonnes ===
    _, left_section, right_section = create_two_column_layout(root)

    # === COLONNE GAUCHE : Liste des sauvegardes ===
    box_append_section_title(left_section, "Sauvegardes Disponibles")

    box_append_label(left_section, "Sélectionnez une sauvegarde pour la restaurer ou la supprimer.", italic=True)

    # Sélecteur de sauvegardes (liste définie / DropDown)
    list_frame = Gtk.Frame()
    list_frame.set_hexpand(True)
    left_section.append(list_frame)

    selector_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    apply_margins(selector_box, 12)
    list_frame.set_child(selector_box)

    backups_dropdown = Gtk.DropDown.new_from_strings([])
    backups_dropdown.set_hexpand(True)
    selector_box.append(backups_dropdown)

    empty_label = Gtk.Label(label="📭 Aucune sauvegarde trouvée")
    empty_label.add_css_class("dim-label")
    empty_label.set_visible(False)
    selector_box.append(empty_label)

    controller.backups_dropdown = backups_dropdown

    # === COLONNE DROITE : Actions ===
    create_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

    box_append_section_title(create_box, "Créer une Sauvegarde")

    box_append_label(create_box, "Crée une nouvelle sauvegarde complète.", italic=True)

    # --- Actions sur la sélection ---
    selection_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

    box_append_section_title(selection_box, "Actions sur la sélection")

    box_append_label(selection_box, "Sélectionnez une sauvegarde pour activer ces actions.", italic=True)

    # Bouton Restaurer
    restore_btn = Gtk.Button(label="🔄 Restaurer la sélection")
    restore_btn.set_halign(Gtk.Align.FILL)
    restore_btn.add_css_class("suggested-action")
    restore_btn.set_sensitive(False)
    restore_btn.connect("clicked", lambda b: _on_restore_clicked(b, controller, backups_dropdown))
    selection_box.append(restore_btn)

    # Bouton Supprimer
    delete_btn = Gtk.Button(label="🗑️ Supprimer la sélection")
    delete_btn.set_halign(Gtk.Align.FILL)
    delete_btn.add_css_class("destructive-action")
    delete_btn.set_sensitive(False)
    delete_btn.set_margin_top(4)
    delete_btn.connect(
        "clicked",
        lambda b: _on_delete_clicked(
            b,
            controller,
            backups_dropdown,
            lambda: _refresh_list(controller, backups_dropdown, empty_label, restore_btn, delete_btn),
        ),
    )
    selection_box.append(delete_btn)

    # Bouton Créer (déplacé après pour avoir accès à _refresh_list avec les boutons)
    create_btn = Gtk.Button(label="➕ Créer une sauvegarde")  # noqa: RUF001
    create_btn.set_halign(Gtk.Align.FILL)
    create_btn.add_css_class("suggested-action")
    create_btn.connect(
        "clicked",
        lambda b: _on_create_clicked(
            b,
            controller,
            lambda: _refresh_list(controller, backups_dropdown, empty_label, restore_btn, delete_btn),
        ),
    )
    create_box.append(create_btn)

    right_section.append(create_box)

    # Séparateur
    separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    separator.set_margin_top(12)
    separator.set_margin_bottom(8)
    right_section.append(separator)

    right_section.append(selection_box)

    backups_dropdown.connect("notify::selected", _on_selection_changed, controller, restore_btn, delete_btn)

    # Chargement immédiat : affiche la liste sans attendre la boucle GTK
    _refresh_list(controller, backups_dropdown, empty_label, restore_btn, delete_btn)

    # === Ajout à l'onglet ===
    label = Gtk.Label(label="Sauvegardes")
    notebook.append_page(root, label)
    logger.debug("[build_backups_tab] Onglet Sauvegardes construit avec succès")
