"""Onglet Maintenance (GTK4) - Outils de réparation GRUB."""

from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING

from gi.repository import Gtk
from loguru import logger

from core.services.core_maintenance_service import MaintenanceService
from ui.ui_dialogs import run_command_popup
from ui.ui_widgets import make_scrolled_grid

if TYPE_CHECKING:
    from ui.ui_manager import GrubConfigManager


def build_maintenance_tab(controller: GrubConfigManager, notebook: Gtk.Notebook) -> None:
    """Build Maintenance tab with repair tools.

    Provides:
    - Diagnostic commands (update-grub, check syntax, list partitions)
    - Restoration from repositories
    """
    logger.debug("[build_maintenance_tab] Construction de l'onglet Maintenance")
    scroll, grid = make_scrolled_grid()
    service = MaintenanceService()

    row = 0

    # === Titre ===
    title = Gtk.Label()
    title.set_markup("<b>Maintenance GRUB</b>")
    title.set_halign(Gtk.Align.START)
    grid.attach(title, 0, row, 2, 1)
    row += 1

    note = Gtk.Label(xalign=0)
    note.set_markup("<i>Outils de diagnostic et réparation. Nécessite les droits root.</i>")
    note.set_wrap(True)
    grid.attach(note, 0, row, 2, 1)
    row += 1

    # === Informations système ===
    section_sys = Gtk.Label()
    section_sys.set_markup("<b>Système</b>")
    section_sys.set_halign(Gtk.Align.START)
    section_sys.set_margin_top(20)
    grid.attach(section_sys, 0, row, 2, 1)
    row += 1

    boot_type = "UEFI" if os.path.exists("/sys/firmware/efi") else "Legacy BIOS"
    boot_label = Gtk.Label()
    boot_label.set_markup(f"<b>Type de boot:</b> {boot_type}")
    boot_label.set_halign(Gtk.Align.START)
    boot_label.set_margin_start(20)
    grid.attach(boot_label, 0, row, 2, 1)
    row += 1

    # === Section Commandes de consultation/vérification ===
    section_consult = Gtk.Label()
    section_consult.set_markup("<b>Consultation et Vérification</b>")
    section_consult.set_halign(Gtk.Align.START)
    section_consult.set_margin_top(20)
    grid.attach(section_consult, 0, row, 2, 1)
    row += 1

    # Liste des commandes de consultation
    consult_commands = [
        ("Voir /etc/default/grub", ["cat", "/etc/default/grub"]),
        ("Voir /boot/grub/grub.cfg", ["cat", "/boot/grub/grub.cfg"]),
        ("Lister partitions", ["lsblk", "-f"]),
        ("Vérifier syntaxe GRUB", ["grub-script-check", "/boot/grub/grub.cfg"]),
        ("Voir script du thème", "find-theme-script"),
    ]

    if boot_type == "UEFI":
        consult_commands.append(("Entrées UEFI", ["efibootmgr"]))

    if shutil.which("grub-emu"):
        consult_commands.append(("Preview GRUB (Simulation)", ["grub-emu"]))

    # ListBox pour consultation
    consult_listbox = Gtk.ListBox()
    consult_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
    consult_listbox.set_margin_start(20)
    consult_listbox.set_margin_end(20)

    for cmd_name, cmd_data in consult_commands:
        row_widget = Gtk.ListBoxRow()
        label = Gtk.Label(label=cmd_name, xalign=0)
        label.set_margin_top(8)
        label.set_margin_bottom(8)
        label.set_margin_start(10)
        row_widget.set_child(label)
        row_widget.cmd_name = cmd_name
        row_widget.cmd_data = cmd_data
        consult_listbox.append(row_widget)

    scroll_consult = Gtk.ScrolledWindow()
    scroll_consult.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll_consult.set_min_content_height(200)
    scroll_consult.set_child(consult_listbox)

    grid.attach(scroll_consult, 0, row, 2, 1)
    row += 1

    # Bouton exécuter consultation
    btn_exec_consult = Gtk.Button(label="Exécuter la commande sélectionnée")
    btn_exec_consult.set_sensitive(False)
    btn_exec_consult.set_halign(Gtk.Align.START)
    btn_exec_consult.set_margin_start(20)
    btn_exec_consult.set_margin_top(10)
    btn_exec_consult.connect("clicked", lambda b: _run_consult_command(controller, consult_listbox, service))

    def _on_consult_selected(_lb: Gtk.ListBox, row_sel: Gtk.ListBoxRow | None) -> None:
        btn_exec_consult.set_sensitive(row_sel is not None)

    consult_listbox.connect("row-selected", _on_consult_selected)

    grid.attach(btn_exec_consult, 0, row, 2, 1)
    row += 1

    # === Section Restauration/Réinstallation ===
    section_restore = Gtk.Label()
    section_restore.set_markup("<b>Restauration et Réinstallation</b>")
    section_restore.set_halign(Gtk.Align.START)
    section_restore.set_margin_top(20)
    grid.attach(section_restore, 0, row, 2, 1)
    row += 1

    # Détecter le gestionnaire de paquets disponible
    restore_cmd = service.get_restore_command()

    # Liste des commandes de restauration
    restore_commands = []

    if restore_cmd:
        cmd_name, cmd_list = restore_cmd
        restore_commands.append((f"Réinstaller GRUB ({cmd_name})", cmd_list))

    restore_commands.append(("Réinstaller script /etc/grub.d/05_debian", "reinstall-05-debian"))
    restore_commands.append(("Activer /etc/grub.d/05_debian_theme", "enable-05-theme"))
    restore_commands.append(("Regénérer grub.cfg (update-grub)", ["update-grub"]))

    if boot_type == "UEFI":
        restore_commands.append(("Réinstaller GRUB (UEFI) ⚠️", "reinstall-grub-uefi"))
    else:
        restore_commands.append(("Réinstaller GRUB (BIOS) ⚠️", "reinstall-grub-bios"))

    # ListBox pour restauration
    restore_listbox = Gtk.ListBox()
    restore_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
    restore_listbox.set_margin_start(20)
    restore_listbox.set_margin_end(20)

    for cmd_name, cmd_data in restore_commands:
        row_widget = Gtk.ListBoxRow()
        label = Gtk.Label(label=cmd_name, xalign=0)
        label.set_margin_top(8)
        label.set_margin_bottom(8)
        label.set_margin_start(10)
        row_widget.set_child(label)
        row_widget.cmd_name = cmd_name
        row_widget.cmd_data = cmd_data
        restore_listbox.append(row_widget)

    scroll_restore = Gtk.ScrolledWindow()
    scroll_restore.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll_restore.set_min_content_height(200)
    scroll_restore.set_child(restore_listbox)

    grid.attach(scroll_restore, 0, row, 2, 1)
    row += 1

    # Bouton exécuter restauration
    btn_exec_restore = Gtk.Button(label="Exécuter la commande sélectionnée")
    btn_exec_restore.set_sensitive(False)
    btn_exec_restore.add_css_class("suggested-action")
    btn_exec_restore.set_halign(Gtk.Align.START)
    btn_exec_restore.set_margin_start(20)
    btn_exec_restore.set_margin_top(10)
    btn_exec_restore.connect("clicked", lambda b: _run_restore_command(controller, restore_listbox, service))

    def _on_restore_selected(_lb: Gtk.ListBox, row_sel: Gtk.ListBoxRow | None) -> None:
        btn_exec_restore.set_sensitive(row_sel is not None)

    restore_listbox.connect("row-selected", _on_restore_selected)

    grid.attach(btn_exec_restore, 0, row, 2, 1)
    row += 1

    notebook.append_page(scroll, Gtk.Label(label="Maintenance"))
    logger.success("[build_maintenance_tab] Onglet Maintenance construit")


def _run_consult_command(controller: GrubConfigManager, listbox: Gtk.ListBox, service: MaintenanceService) -> None:
    """Exécute une commande de consultation sélectionnée."""
    row = listbox.get_selected_row()
    if not row:
        return

    cmd_name = getattr(row, "cmd_name", "")
    cmd_data = getattr(row, "cmd_data", None)

    if not cmd_data:
        return

    logger.info(f"[_run_consult_command] Exécution: {cmd_name}")

    if cmd_data == "find-theme-script":
        _show_theme_script(controller, service)
    elif isinstance(cmd_data, list):
        run_command_popup(controller, cmd_data, cmd_name)


def _run_restore_command(controller: GrubConfigManager, listbox: Gtk.ListBox, service: MaintenanceService) -> None:
    """Exécute une commande de restauration sélectionnée."""
    row = listbox.get_selected_row()
    if not row:
        return

    cmd_name = getattr(row, "cmd_name", "")
    cmd_data = getattr(row, "cmd_data", None)

    if not cmd_data:
        return

    logger.info(f"[_run_restore_command] Exécution: {cmd_name}")

    if cmd_data == "reinstall-05-debian":
        cmd = service.get_reinstall_05_debian_command()
        if cmd:
            run_command_popup(controller, cmd, "Réinstallation du script 05_debian")
        else:
            controller.show_info("Aucun gestionnaire de paquets détecté", "error")
    elif cmd_data == "enable-05-theme":
        cmd = service.get_enable_05_debian_theme_command()
        run_command_popup(controller, cmd, "Activation du script 05_debian_theme")
    elif cmd_data == "reinstall-grub-uefi":
        _reinstall_grub_uefi(controller)
    elif cmd_data == "reinstall-grub-bios":
        _reinstall_grub_bios(controller)
    elif isinstance(cmd_data, list):
        run_command_popup(controller, cmd_data, cmd_name)


def _show_theme_script(controller: GrubConfigManager, service: MaintenanceService) -> None:
    """Find and display GRUB theme script (theme.txt)."""
    logger.info("[_show_theme_script] Recherche du script du thème GRUB")

    theme_path = service.find_theme_script_path()

    if not theme_path:
        logger.warning("[_show_theme_script] Aucun script de thème trouvé")
        controller.show_info("Aucun script de thème GRUB trouvé", "error")
        return

    logger.info(f"[_show_theme_script] Affichage du thème: {theme_path}")

    # Déterminer le titre selon le type de fichier
    if theme_path.endswith("theme.txt"):
        title = f"Script du thème: {os.path.basename(os.path.dirname(theme_path))}"
    else:
        title = f"Script de génération: {os.path.basename(theme_path)}"

    run_command_popup(controller, ["cat", theme_path], title)


def _reinstall_grub_uefi(controller: GrubConfigManager) -> None:
    """Reinstall GRUB for UEFI systems."""
    if os.geteuid() != 0:
        controller.show_info("Droits root nécessaires", "error")
        return

    dialog = Gtk.AlertDialog()
    dialog.set_modal(True)
    dialog.set_message("Réinstaller GRUB (UEFI)?")
    dialog.set_detail("Cela va réinstaller le bootloader.\n\nAssurez-vous que /boot/efi est monté.")
    dialog.set_buttons(["Annuler", "Réinstaller"])
    dialog.set_default_button(0)

    def on_response(d: Gtk.AlertDialog, result: Gtk.AsyncResult) -> None:
        try:
            if d.choose_finish(result) == 1:  # Index 1 = Réinstaller
                cmd = ["grub-install", "--target=x86_64-efi", "--efi-directory=/boot/efi", "--recheck"]
                run_command_popup(controller, cmd, "Réinstaller GRUB (UEFI)")
        except (OSError, RuntimeError):
            pass

    dialog.choose(controller, None, on_response)


def _reinstall_grub_bios(controller: GrubConfigManager) -> None:
    """Reinstall GRUB for BIOS systems."""
    if os.geteuid() != 0:
        controller.show_info("Droits root nécessaires", "error")
        return

    dialog = Gtk.AlertDialog()
    dialog.set_modal(True)
    dialog.set_message("Réinstaller GRUB (BIOS)?")
    dialog.set_detail("Cela va réinstaller le bootloader sur le MBR.\n\nDisque: /dev/sda")
    dialog.set_buttons(["Annuler", "Réinstaller"])
    dialog.set_default_button(0)

    def on_response(d: Gtk.AlertDialog, result: Gtk.AsyncResult) -> None:
        try:
            if d.choose_finish(result) == 1:  # Index 1 = Réinstaller
                cmd = ["grub-install", "/dev/sda"]
                run_command_popup(controller, cmd, "Réinstaller GRUB (BIOS)")
        except (OSError, RuntimeError):
            pass

    dialog.choose(controller, None, on_response)
