"""Onglet Sauvegardes (GTK4)."""

# pylint: disable=too-many-statements

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING

from gi.repository import Gtk
from loguru import logger

from core.grub_default import create_grub_default_backup, delete_grub_default_backup, list_grub_default_backups
from ui.tabs.base import apply_margins
from ui.tabs.widgets import box_append_label, box_append_section_title, clear_listbox

if TYPE_CHECKING:
    from ui.app import GrubConfigManager


def build_backups_tab(controller: GrubConfigManager, notebook: Gtk.Notebook) -> None:
    """Build the Backups tab (list/create/delete).

    DEV: Complete backup management with create, restore, delete.
    """
    logger.debug("[build_backups_tab] Construction de l'onglet Sauvegardes")
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    apply_margins(root, 12)

    box_append_section_title(root, "Sauvegardes")
    box_append_label(root, "Gère les sauvegardes de /etc/default/grub.", italic=True)

    listbox = Gtk.ListBox()
    listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
    listbox.set_vexpand(True)

    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_vexpand(True)
    scroll.set_child(listbox)

    buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    buttons.set_halign(Gtk.Align.END)

    create_btn = Gtk.Button(label="Créer une sauvegarde")
    restore_btn = Gtk.Button(label="Restaurer")
    restore_btn.set_sensitive(False)
    restore_btn.get_style_context().add_class("suggested-action")
    delete_btn = Gtk.Button(label="Supprimer")
    delete_btn.set_sensitive(False)
    delete_btn.get_style_context().add_class("destructive-action")

    buttons.append(create_btn)
    buttons.append(restore_btn)
    buttons.append(delete_btn)

    root.append(scroll)
    root.append(buttons)

    def _refresh() -> None:
        """Rafraîchit la liste des sauvegardes affichées."""
        logger.debug("[_refresh] Rafraîchissement de la liste des sauvegardes")
        clear_listbox(listbox)

        try:
            backups = list_grub_default_backups()
            logger.debug(f"[_refresh] {len(backups)} sauvegarde(s) trouvée(s)")
        except OSError as e:
            logger.error(f"[_refresh] ERREUR: Impossible de lister les sauvegardes - {e}")
            controller.show_info(f"Impossible de lister les sauvegardes: {e}", "error")
            backups = []

        if not backups:
            logger.debug("[_refresh] Aucune sauvegarde disponible")
            row = Gtk.ListBoxRow()
            row.set_selectable(False)
            row.set_child(Gtk.Label(label="Aucune sauvegarde trouvée", xalign=0))
            listbox.append(row)
            delete_btn.set_sensitive(False)
            return

        def _backup_type(p: str) -> str:
            """Catégorise le type de sauvegarde."""
            if p.endswith(".backup.initial"):
                return "Initiale"
            if ".backup.manual." in p:
                return "Manuelle"
            if p.endswith(".backup"):
                return "Auto (enregistrement)"
            return "Backup"

        for p in backups:
            row = Gtk.ListBoxRow()
            row.set_selectable(True)
            row.backup_path = p

            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            hbox.set_margin_top(6)
            hbox.set_margin_bottom(6)
            hbox.set_margin_start(8)
            hbox.set_margin_end(8)

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            vbox.set_hexpand(True)

            title = Gtk.Label(label=os.path.basename(p), xalign=0)
            title.set_hexpand(True)
            title.set_ellipsize(3)  # Pango.EllipsizeMode.END (évite import)
            vbox.append(title)

            try:
                ts = datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M:%S")
            except OSError:
                ts = ""
            subtitle = Gtk.Label(xalign=0)
            subtitle.set_markup(f"<i>{ts}</i>")
            subtitle.set_tooltip_text(p)
            subtitle.set_hexpand(True)
            vbox.append(subtitle)

            kind = Gtk.Label(label=_backup_type(p), xalign=1)
            kind.set_halign(Gtk.Align.END)
            kind.set_valign(Gtk.Align.CENTER)

            hbox.append(vbox)
            hbox.append(kind)
            row.set_child(hbox)
            listbox.append(row)

        delete_btn.set_sensitive(False)
        logger.success("[_refresh] Liste rafraîchie")

    def _on_row_selected(_lb: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        """Handle backup selection."""
        has_selection = row is not None and getattr(row, "backup_path", None) is not None
        if has_selection:
            path = getattr(row, "backup_path", None)
            logger.debug(f"[_on_row_selected] Sauvegarde sélectionnée: {os.path.basename(path) if path else 'N/A'}")
        delete_btn.set_sensitive(has_selection)
        restore_btn.set_sensitive(has_selection)

    def _on_create(_btn: Gtk.Button) -> None:
        """Créer une nouvelle sauvegarde."""
        logger.info("[_on_create] Création d'une nouvelle sauvegarde")
        if os.geteuid() != 0:
            logger.warning("[_on_create] ERREUR: Droits root nécessaires")
            controller.show_info("Droits administrateur requis pour créer une sauvegarde", "error")
            return

        logger.debug("[_on_create] Vérification des conditions préalables")
        from core.paths import GRUB_DEFAULT_PATH  # pylint: disable=import-outside-toplevel

        # Vérifier que le fichier source existe et a du contenu
        if not os.path.isfile(GRUB_DEFAULT_PATH):
            logger.error(f"[_on_create] ERREUR: {GRUB_DEFAULT_PATH} n'existe pas")
            controller.show_info(f"Erreur: {GRUB_DEFAULT_PATH} introuvable", "error")
            return

        try:
            source_size = os.path.getsize(GRUB_DEFAULT_PATH)
            if source_size == 0:
                logger.error(f"[_on_create] ERREUR: {GRUB_DEFAULT_PATH} est vide")
                controller.show_info(f"Erreur: {GRUB_DEFAULT_PATH} est vide", "error")
                return
            logger.debug(f"[_on_create] Fichier source valide: {source_size} bytes")
        except OSError as e:
            logger.error(f"[_on_create] ERREUR: Impossible de vérifier le fichier source - {e}")
            controller.show_info(f"Erreur: Impossible de lire {GRUB_DEFAULT_PATH}: {e}", "error")
            return

        try:
            logger.debug("[_on_create] Appel de create_grub_default_backup()")
            p = create_grub_default_backup()

            # Vérifier que le backup a été créé
            if not os.path.isfile(p):
                logger.error(f"[_on_create] ERREUR: Backup créé mais introuvable - {p}")
                controller.show_info("Erreur: Le backup n'a pas pu être créé", "error")
                return

            backup_size = os.path.getsize(p)
            if backup_size != source_size:
                logger.error(f"[_on_create] ERREUR: Backup incomplet ({backup_size} vs {source_size})")
                controller.show_info(f"Erreur: Le backup est incomplet ({backup_size} vs {source_size} bytes)", "error")
                return

            logger.success(f"[_on_create] Sauvegarde créée avec succès: {p} ({backup_size} bytes)")
            controller.show_info(f"Sauvegarde créée: {os.path.basename(p)}", "info")
            _refresh()
        except OSError as e:
            logger.error(f"[_on_create] ERREUR: {e}")
            controller.show_info(f"Erreur lors de la création: {e}", "error")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.exception(f"[_on_create] ERREUR inattendue: {e}")
            controller.show_info(f"Erreur inattendue: {e}", "error")

    def _on_restore(_btn: Gtk.Button) -> None:
        """Restaurer une sauvegarde sélectionnée."""
        logger.info("[_on_restore] Demande de restauration")
        if os.geteuid() != 0:
            logger.warning("[_on_restore] ERREUR: Droits root nécessaires")
            controller.show_info("Droits administrateur requis pour restaurer une sauvegarde", "error")
            return
        row = listbox.get_selected_row()
        if row is None:
            logger.warning("[_on_restore] Aucune sauvegarde sélectionnée")
            return
        p = getattr(row, "backup_path", None)
        if not p:
            return

        logger.info(f"[_on_restore] Restauration de: {p}")
        # Dialogue de confirmation
        dialog = Gtk.AlertDialog()
        dialog.set_message("Restaurer cette sauvegarde ?")
        dialog.set_detail(
            f"Cela va :\n"
            f"1. Créer un backup de la config actuelle\n"
            f"2. Restaurer: {os.path.basename(str(p))}\n"
            f"3. Regénérer grub.cfg avec update-grub\n\n"
            f"Cette opération est réversible."
        )
        dialog.set_buttons(["Annuler", "Restaurer"])
        dialog.set_cancel_button(0)
        dialog.set_default_button(1)

        def _on_confirm(dlg, result):
            try:
                idx = dlg.choose_finish(result)
            except Exception:  # pylint: disable=broad-exception-caught
                logger.debug("[_on_confirm] Restauration annulée par utilisateur")
                return

            if idx != 1:
                logger.debug("[_on_confirm] Utilisateur a cliqué sur Annuler")
                return

            # === Restauration sécurisée ===
            try:
                import shutil  # pylint: disable=import-outside-toplevel
                import subprocess  # pylint: disable=import-outside-toplevel

                from core.paths import GRUB_DEFAULT_PATH  # pylint: disable=import-outside-toplevel

                logger.info("[_on_confirm] Démarrage du workflow de restauration à 3 étapes")

                # === ÉTAPE 1: Backup de sécurité de la config actuelle ===
                logger.debug("[_on_confirm] Étape 1/3: Création du backup de sécurité")
                if not os.path.exists(GRUB_DEFAULT_PATH):
                    logger.error("[_on_confirm] ERREUR: Fichier source inexistant")
                    controller.show_info("Erreur: Fichier /etc/default/grub introuvable", "error")
                    return

                safety_backup = f"{GRUB_DEFAULT_PATH}.backup.pre-restore"
                try:
                    # Vérifier que le fichier source a du contenu
                    source_size = os.path.getsize(GRUB_DEFAULT_PATH)
                    if source_size == 0:
                        logger.error("[_on_confirm] ERREUR ÉTAPE 1: Fichier source vide")
                        controller.show_info("Erreur: Le fichier /etc/default/grub est vide", "error")
                        return

                    shutil.copy2(GRUB_DEFAULT_PATH, safety_backup)
                    backup_size = os.path.getsize(safety_backup)
                    if backup_size != source_size:
                        logger.error(f"[_on_confirm] ERREUR ÉTAPE 1: Backup incomplet ({backup_size} vs {source_size})")
                        controller.show_info(
                            "Erreur: Création du backup de sécurité échouée (fichier incomplet)", "error"
                        )
                        return

                    logger.success(f"[_on_confirm] Étape 1 OK: Backup de sécurité créé ({backup_size} bytes)")
                except OSError as e:
                    logger.error(f"[_on_confirm] ERREUR ÉTAPE 1: {e}")
                    controller.show_info(f"Erreur lors du backup de sécurité: {e}", "error")
                    return

                # === ÉTAPE 2: Validation et restauration du backup sélectionné ===
                logger.debug("[_on_confirm] Étape 2/3: Restauration du backup sélectionné")
                try:
                    # Vérifier que le backup source existe et a du contenu
                    if not os.path.isfile(str(p)):
                        logger.error(f"[_on_confirm] ERREUR ÉTAPE 2: Backup source introuvable - {p}")
                        controller.show_info(f"Erreur: Fichier de sauvegarde introuvable - {p}", "error")
                        return

                    backup_source_size = os.path.getsize(str(p))
                    if backup_source_size == 0:
                        logger.error(f"[_on_confirm] ERREUR ÉTAPE 2: Backup source vide - {p}")
                        controller.show_info(f"Erreur: Le backup est vide ou corrompu - {p}", "error")
                        return

                    logger.debug(f"[_on_confirm] Vérification backup source: {backup_source_size} bytes")

                    # Restaurer le fichier
                    shutil.copy2(str(p), GRUB_DEFAULT_PATH)

                    # Vérifier que la restauration a réussi
                    restored_size = os.path.getsize(GRUB_DEFAULT_PATH)
                    if restored_size != backup_source_size:
                        logger.error(
                            f"[_on_confirm] ERREUR ÉTAPE 2: Restauration incomplète "
                            f"({restored_size} vs {backup_source_size})"
                        )
                        # ROLLBACK immédiat
                        logger.warning("[_on_confirm] ROLLBACK: Restauration du backup de sécurité")
                        shutil.copy2(safety_backup, GRUB_DEFAULT_PATH)
                        controller.show_info("Erreur: Restauration incomplète, rollback effectué", "error")
                        return

                    # Vérifier que le fichier restauré contient de la configuration
                    try:
                        restored_content = open(  # pylint: disable=consider-using-with
                            GRUB_DEFAULT_PATH, encoding="utf-8", errors="replace"
                        ).read()
                        lines = [
                            line for line in restored_content.splitlines() if line.strip() and not line.startswith("#")
                        ]
                        if len(lines) == 0:
                            logger.error("[_on_confirm] ERREUR ÉTAPE 2: Fichier restauré n'a pas de configuration")
                            logger.warning("[_on_confirm] ROLLBACK: Restauration du backup de sécurité")
                            shutil.copy2(safety_backup, GRUB_DEFAULT_PATH)
                            controller.show_info("Erreur: Configuration restaurée invalide, rollback effectué", "error")
                            return
                        logger.debug(f"[_on_confirm] Configuration restaurée validée: {len(lines)} lignes")
                    except OSError as e:
                        logger.error(f"[_on_confirm] ERREUR ÉTAPE 2: Impossible de valider le contenu - {e}")
                        logger.warning("[_on_confirm] ROLLBACK: Restauration du backup de sécurité")
                        shutil.copy2(safety_backup, GRUB_DEFAULT_PATH)
                        return

                    logger.success("[_on_confirm] Étape 2 OK: Configuration restaurée et validée")
                except OSError as e:
                    logger.error(f"[_on_confirm] ERREUR ÉTAPE 2: {e}")
                    logger.warning("[_on_confirm] ROLLBACK: Restauration du backup de sécurité")
                    try:
                        shutil.copy2(safety_backup, GRUB_DEFAULT_PATH)
                        logger.success("[_on_confirm] ROLLBACK réussi")
                    except OSError as rollback_error:
                        logger.critical(f"[_on_confirm] ERREUR ROLLBACK: {rollback_error}")
                    controller.show_info(f"Erreur lors de la restauration: {e}. Rollback effectué.", "error")
                    return

                # === ÉTAPE 3: Regénération de grub.cfg ===
                logger.debug("[_on_confirm] Étape 3/3: Regénération de grub.cfg")
                update_cmd = shutil.which("update-grub")
                if update_cmd:
                    logger.debug(f"[_on_confirm] Exécution de {update_cmd}")
                    result = subprocess.run([update_cmd], capture_output=True, text=True, check=False)

                    if result.returncode == 0:
                        logger.success("[_on_confirm] Étape 3 OK: Grub.cfg regénéré avec succès")
                        controller.show_info("✓ Restauration réussie ! Le système GRUB a été regénéré.", "info")
                        # Recharger l'interface
                        logger.debug("[_on_confirm] Rechargement de l'interface")
                        controller.load_config()
                        _refresh()
                    else:
                        # Étape 3 échouée - on alerte mais la config est déjà restaurée
                        logger.warning(
                            f"[_on_confirm] AVERTISSEMENT ÉTAPE 3: update-grub échoué - {result.stderr[:100]}"
                        )
                        controller.show_info(
                            f"Configuration restaurée, mais update-grub a échoué:\n"
                            f"{result.stderr[:200]}\n\nLe système peut ne pas démarrer "
                            f"correctement.",
                            "warning",
                        )
                        controller.load_config()
                        _refresh()
                else:
                    logger.warning("[_on_confirm] update-grub non trouvé sur le système")
                    controller.show_info(
                        "Configuration restaurée, mais update-grub n'a pas pu être exécuté.\n"
                        "Le système GRUB peut ne pas démarrer correctement.",
                        "warning",
                    )
                    controller.load_config()
                    _refresh()

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.exception(f"[_on_confirm] ERREUR inattendue lors de la restauration: {e}")
                controller.show_info(
                    f"Erreur critique lors de la restauration: {e}\n\nVérifiez manuellement l'état du système GRUB.",
                    "error",
                )

        dialog.choose(controller, None, _on_confirm)

    def _on_delete(_btn: Gtk.Button) -> None:
        """Supprimer la sauvegarde sélectionnée."""
        logger.info("[_on_delete] Demande de suppression")
        if os.geteuid() != 0:
            logger.warning("[_on_delete] ERREUR: Droits root nécessaires")
            controller.show_info("Droits administrateur requis pour supprimer une sauvegarde", "error")
            return

        row = listbox.get_selected_row()
        if row is None:
            logger.warning("[_on_delete] ERREUR: Aucune sauvegarde sélectionnée")
            return

        p = getattr(row, "backup_path", None)
        if not p:
            logger.warning("[_on_delete] ERREUR: Propriété backup_path manquante")
            return

        logger.debug(f"[_on_delete] Vérification du chemin: {p}")

        # Sécurité: Vérifications du chemin
        from core.paths import GRUB_DEFAULT_PATH  # pylint: disable=import-outside-toplevel

        if not str(p).startswith(f"{GRUB_DEFAULT_PATH}.backup"):
            logger.error(f"[_on_delete] ERREUR SÉCURITÉ: Chemin invalide - {p}")
            controller.show_info("Erreur sécurité: Chemin invalide", "error")
            return

        if str(p) == GRUB_DEFAULT_PATH:
            logger.error("[_on_delete] ERREUR: Tentative de suppression du fichier canonique")
            controller.show_info("Erreur: Impossible de supprimer le fichier de configuration principal", "error")
            return

        if not os.path.isfile(str(p)):
            logger.warning(f"[_on_delete] ERREUR: Fichier introuvable - {p}")
            controller.show_info(f"Erreur: Le fichier n'existe plus - {os.path.basename(str(p))}", "error")
            _refresh()
            return

        # Dialogue de confirmation pour supression destructive
        dialog = Gtk.AlertDialog()
        dialog.set_message("Supprimer cette sauvegarde ?")
        dialog.set_detail(f"Suppression définitive de:\n{os.path.basename(str(p))}\n\nCette action est irréversible.")
        dialog.set_buttons(["Annuler", "Supprimer"])
        dialog.set_cancel_button(0)
        dialog.set_default_button(0)  # Annuler par défaut (sécurité)

        def _on_confirm_delete(dlg, result):
            try:
                idx = dlg.choose_finish(result)
            except Exception:  # pylint: disable=broad-exception-caught
                logger.debug("[_on_confirm_delete] Suppression annulée par utilisateur")
                return

            if idx != 1:
                logger.debug("[_on_confirm_delete] Utilisateur a cliqué sur Annuler")
                return

            logger.info(f"[_on_confirm_delete] Suppression confirmée: {p}")
            try:
                # Vérification finale avant suppression
                if not os.path.isfile(str(p)):
                    logger.error(f"[_on_confirm_delete] ERREUR: Fichier disparu avant suppression - {p}")
                    controller.show_info("Erreur: Le fichier a disparu", "error")
                    _refresh()
                    return

                delete_grub_default_backup(str(p))
                logger.success(f"[_on_confirm_delete] Sauvegarde supprimée: {p}")
                controller.show_info(f"Sauvegarde supprimée: {os.path.basename(str(p))}", "info")
                _refresh()
            except ValueError as e:
                logger.error(f"[_on_confirm_delete] ERREUR SÉCURITÉ: {e}")
                controller.show_info(f"Erreur sécurité: {e}", "error")
            except OSError as e:
                logger.error(f"[_on_confirm_delete] ERREUR: Impossible de supprimer - {e}")
                controller.show_info(f"Erreur lors de la suppression: {e}", "error")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.exception(f"[_on_confirm_delete] ERREUR inattendue: {e}")
                controller.show_info(f"Erreur inattendue: {e}", "error")

        dialog.choose(controller, None, _on_confirm_delete)

    listbox.connect("row-selected", _on_row_selected)
    create_btn.connect("clicked", _on_create)
    restore_btn.connect("clicked", _on_restore)
    delete_btn.connect("clicked", _on_delete)

    _refresh()

    notebook.append_page(root, Gtk.Label(label="Sauvegardes"))
    logger.success("[build_backups_tab] Onglet Sauvegardes construit")
