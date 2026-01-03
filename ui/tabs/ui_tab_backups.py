"""Onglet Sauvegardes (GTK4)."""

# pylint: disable=too-many-statements

from __future__ import annotations

import os
import tarfile
from datetime import datetime
from typing import TYPE_CHECKING

from gi.repository import GLib, Gtk
from loguru import logger

from core.io.core_grub_default_io import (
    create_grub_default_backup,
    delete_grub_default_backup,
    list_grub_default_backups,
    restore_grub_default_backup,
)
from ui.ui_dialogs import confirm_action
from ui.ui_widgets import (
    apply_margins,
    box_append_label,
    box_append_section_title,
    categorize_backup_type,
    create_list_box_row_with_margins,
    create_two_column_layout,
)


def _get_listbox_from_frame(frame: Gtk.Frame) -> Gtk.ListBox | None:
    """Récupère la ListBox contenue dans la frame, gérant le ScrolledWindow et Viewport."""
    child = frame.get_child()
    if not child:
        return None

    if isinstance(child, Gtk.ScrolledWindow):
        child = child.get_child()

    if isinstance(child, Gtk.Viewport):
        child = child.get_child()

    if isinstance(child, Gtk.ListBox):
        return child

    return None


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
    except (OSError, ValueError, RuntimeError) as e:
        logger.error(f"[_on_create_clicked] ERREUR: {e}")
        controller.show_info(f"❌ Échec de la création:\n{e}", "error")
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"[_on_create_clicked] ERREUR: {e}")
        controller.show_info(f"❌ Échec de la création:\n{e}", "error")


def _on_restore_clicked(_btn, controller, list_frame):
    """Callback pour restaurer une sauvegarde."""
    # Vérifier les droits root
    if os.geteuid() != 0:
        controller.show_info("Droits administrateur requis pour restaurer une sauvegarde", "error")
        return

    listbox = _get_listbox_from_frame(list_frame)
    if not listbox:
        return

    selected = listbox.get_selected_row()

    if not selected or not hasattr(selected, "backup_path"):
        controller.show_info("Veuillez sélectionner une sauvegarde à restaurer.", "warning")
        return

    backup_path = selected.backup_path
    basename = os.path.basename(backup_path)

    logger.info(f"[_on_restore_clicked] Restauration de {basename}")

    def do_restore():
        try:
            restore_grub_default_backup(backup_path)
            logger.info(f"[_on_restore_clicked] Restauration réussie de {basename}")
            msg = f"✅ Sauvegarde restaurée avec succès:\n{basename}" "\n\nRedémarrez pour appliquer les changements."
            controller.show_info(msg, "info")
            controller.reload_from_disk()
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


def _on_delete_clicked(_btn, controller, list_frame, refresh_callback):
    """Callback pour supprimer une sauvegarde."""
    # Vérifier les droits root
    if os.geteuid() != 0:
        controller.show_info("Droits administrateur requis pour supprimer une sauvegarde", "error")
        return

    listbox = _get_listbox_from_frame(list_frame)
    if not listbox:
        return

    selected = listbox.get_selected_row()
    if not selected or not hasattr(selected, "backup_path"):
        controller.show_info("Veuillez sélectionner une sauvegarde à supprimer.", "warning")
        return

    backup_path = selected.backup_path
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


def _on_selection_changed(_listbox_widget, row, restore_btn, delete_btn):
    """Active/désactive les boutons selon la sélection."""
    has_selection = row is not None and hasattr(row, "backup_path")
    restore_btn.set_sensitive(has_selection)
    delete_btn.set_sensitive(has_selection)


def _refresh_list(controller, list_frame, restore_btn=None, delete_btn=None):
    """Rafraîchit l'affichage de la liste."""
    try:
        backups = list_grub_default_backups()
        logger.debug(f"[_load_backups] {len(backups)} sauvegarde(s) trouvée(s)")
    except OSError as e:
        logger.error(f"[_load_backups] ERREUR: {e}")
        controller.show_info(f"Impossible de lister les sauvegardes: {e}", "error")
        backups = []

    if not backups:
        # Afficher un message si aucune sauvegarde
        empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        apply_margins(empty_box, 20)
        empty_label = Gtk.Label(label="📭 Aucune sauvegarde trouvée")
        empty_label.add_css_class("dim-label")
        empty_box.append(empty_label)
        list_frame.set_child(empty_box)
        if restore_btn:
            restore_btn.set_sensitive(False)
        if delete_btn:
            delete_btn.set_sensitive(False)
        return

    # Créer listbox avec les sauvegardes
    listbox = Gtk.ListBox()
    listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
    listbox.add_css_class("rich-list")

    for backup_path in backups:
        row, hbox = create_list_box_row_with_margins()
        row.backup_path = backup_path

        # --- Icône à gauche ---
        backup_type = categorize_backup_type(backup_path)
        is_initial = "initial" in backup_path
        icon_char = "⭐" if is_initial else "📦"

        icon_label = Gtk.Label(label=icon_char)
        icon_label.set_markup(f"<span size='x-large'>{icon_char}</span>")
        icon_label.set_margin_end(12)
        hbox.append(icon_label)

        # --- Contenu central (Nom + Type) ---
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_hexpand(True)
        vbox.set_valign(Gtk.Align.CENTER)

        # Nom du fichier
        title = Gtk.Label(label=os.path.basename(backup_path), xalign=0)
        title.set_markup(f"<b>{os.path.basename(backup_path)}</b>")
        title.add_css_class("title-4")
        vbox.append(title)

        # Type (sous-titre)
        type_label = Gtk.Label(xalign=0)
        type_label.set_markup(f"<small>{backup_type}</small>")
        type_label.add_css_class("dim-label")
        vbox.append(type_label)

        hbox.append(vbox)

        # --- Métadonnées à droite (Date + Taille) ---
        meta_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        meta_box.set_valign(Gtk.Align.CENTER)
        meta_box.set_halign(Gtk.Align.END)

        try:
            mtime = os.path.getmtime(backup_path)
            size = os.path.getsize(backup_path)
            date_str = datetime.fromtimestamp(mtime).strftime("%d/%m/%Y")

            # Taille formatée
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"

            date_label = Gtk.Label(label=date_str)
            date_label.set_markup(f"<small>{date_str}</small>")
            date_label.set_halign(Gtk.Align.END)
            date_label.add_css_class("dim-label")

            size_label = Gtk.Label(label=size_str)
            size_label.set_markup(f"<small><b>{size_str}</b></small>")
            size_label.set_halign(Gtk.Align.END)
            size_label.add_css_class("caption")

            meta_box.append(date_label)
            meta_box.append(size_label)
        except OSError:
            pass

        hbox.append(meta_box)
        row.set_child(hbox)
        listbox.append(row)

    if restore_btn and delete_btn:
        listbox.connect("row-selected", _on_selection_changed, restore_btn, delete_btn)

    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_vexpand(True)
    scroll.set_child(listbox)
    list_frame.set_child(scroll)


def build_backups_tab(controller: GrubConfigManager, notebook: Gtk.Notebook) -> None:
    """Build the Backups tab (list/create/delete)."""
    logger.debug("[build_backups_tab] Construction de l'onglet Sauvegardes")
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    apply_margins(root, 12)

    box_append_section_title(root, "Sauvegardes")
    box_append_label(root, "Gestion des sauvegardes de la configuration GRUB.", italic=True)

    # === Conteneur 2 colonnes ===
    _, left_section, right_section = create_two_column_layout(root)

    # === COLONNE GAUCHE : Liste des sauvegardes ===
    left_title = Gtk.Label(xalign=0)
    left_title.set_markup("<b>Sauvegardes Disponibles</b>")
    left_title.add_css_class("section-title")
    left_section.append(left_title)

    box_append_label(left_section, "Sélectionnez une sauvegarde pour la restaurer ou la supprimer.", italic=True)

    # Frame pour la liste
    list_frame = Gtk.Frame()
    left_section.append(list_frame)

    # === COLONNE DROITE : Actions ===
    create_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

    create_title = Gtk.Label(xalign=0)
    create_title.set_markup("<b>Créer une Sauvegarde</b>")
    create_title.add_css_class("section-title")
    create_box.append(create_title)

    box_append_label(create_box, "Crée une nouvelle sauvegarde complète.", italic=True)

    # --- Actions sur la sélection ---
    selection_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

    selection_title = Gtk.Label(xalign=0)
    selection_title.set_markup("<b>Actions sur la sélection</b>")
    selection_title.add_css_class("section-title")
    selection_box.append(selection_title)

    box_append_label(selection_box, "Sélectionnez une sauvegarde pour activer ces actions.", italic=True)

    # Bouton Restaurer
    restore_btn = Gtk.Button(label="🔄 Restaurer la sélection")
    restore_btn.set_halign(Gtk.Align.FILL)
    restore_btn.add_css_class("suggested-action")
    restore_btn.set_sensitive(False)
    restore_btn.connect("clicked", lambda b: _on_restore_clicked(b, controller, list_frame))
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
            b, controller, list_frame, lambda: _refresh_list(controller, list_frame, restore_btn, delete_btn)
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
            b, controller, lambda: _refresh_list(controller, list_frame, restore_btn, delete_btn)
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

    # Premier chargement
    GLib.idle_add(lambda: _refresh_list(controller, list_frame, restore_btn, delete_btn))

    # === Ajout à l'onglet ===
    label = Gtk.Label(label="Sauvegardes")
    notebook.append_page(root, label)
    logger.debug("[build_backups_tab] Onglet Sauvegardes construit avec succès")
