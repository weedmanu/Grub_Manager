"""Onglet Maintenance (GTK4) - Outils de réparation GRUB."""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import threading
from typing import TYPE_CHECKING

from gi.repository import GLib, Gtk
from loguru import logger

from core.io.core_grub_default_io import (
    create_grub_default_backup,
    delete_grub_default_backup,
    list_grub_default_backups,
    read_grub_default,
)
from ui.ui_widgets import (
    categorize_backup_type,
    clear_listbox,
    create_list_box_row_with_margins,
    make_scrolled_grid,
)

if TYPE_CHECKING:
    from ui.ui_manager import GrubConfigManager


def build_maintenance_tab(controller: GrubConfigManager, notebook: Gtk.Notebook) -> None:
    """Build Maintenance tab with repair tools and backup management.

    Provides:
    - Diagnostic commands (update-grub, check syntax, list partitions)
    - Restoration from repositories
    - Backup management (list, create, restore, delete)
    """
    logger.debug("[build_maintenance_tab] Construction de l'onglet Maintenance")
    scroll, grid = make_scrolled_grid()

    row = 0

    # === Titre ===
    title = Gtk.Label()
    title.set_markup("<b>Maintenance GRUB</b>")
    title.set_halign(Gtk.Align.START)
    grid.attach(title, 0, row, 2, 1)
    row += 1

    note = Gtk.Label(xalign=0)
    note.set_markup("<i>Outils de diagnostic, réparation et sauvegarde. Nécessite les droits root.</i>")
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
    btn_exec_consult.connect("clicked", lambda b: _run_consult_command(controller, consult_listbox))

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
    restore_cmd = _get_restore_command()

    # Liste des commandes de restauration
    restore_commands = []

    if restore_cmd:
        cmd_name, cmd_list = restore_cmd
        restore_commands.append((f"Réinstaller GRUB ({cmd_name})", cmd_list, 120))

    restore_commands.append(("Réinstaller script /etc/grub.d/05_debian", "reinstall-05-debian", 60))
    restore_commands.append(("Activer /etc/grub.d/05_debian_theme", "enable-05-theme", 5))
    restore_commands.append(("Regénérer grub.cfg (update-grub)", ["update-grub"], 30))

    if boot_type == "UEFI":
        restore_commands.append(("Réinstaller GRUB (UEFI) ⚠️", "reinstall-grub-uefi", 120))
    else:
        restore_commands.append(("Réinstaller GRUB (BIOS) ⚠️", "reinstall-grub-bios", 120))

    # ListBox pour restauration
    restore_listbox = Gtk.ListBox()
    restore_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
    restore_listbox.set_margin_start(20)
    restore_listbox.set_margin_end(20)

    for cmd_name, cmd_data, timeout in restore_commands:
        row_widget = Gtk.ListBoxRow()
        label = Gtk.Label(label=cmd_name, xalign=0)
        label.set_margin_top(8)
        label.set_margin_bottom(8)
        label.set_margin_start(10)
        row_widget.set_child(label)
        row_widget.cmd_name = cmd_name
        row_widget.cmd_data = cmd_data
        row_widget.cmd_timeout = timeout
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
    btn_exec_restore.connect("clicked", lambda b: _run_restore_command(controller, restore_listbox))

    def _on_restore_selected(_lb: Gtk.ListBox, row_sel: Gtk.ListBoxRow | None) -> None:
        btn_exec_restore.set_sensitive(row_sel is not None)

    restore_listbox.connect("row-selected", _on_restore_selected)

    grid.attach(btn_exec_restore, 0, row, 2, 1)
    row += 1

    # === Section Sauvegardes ===
    section_backups = Gtk.Label()
    section_backups.set_markup("<b>Sauvegardes</b>")
    section_backups.set_halign(Gtk.Align.START)
    section_backups.set_margin_top(20)
    grid.attach(section_backups, 0, row, 2, 1)
    row += 1

    backups_listbox = Gtk.ListBox()
    backups_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
    backups_listbox.set_vexpand(True)
    backups_listbox.set_hexpand(True)
    backups_listbox.set_margin_start(20)
    backups_listbox.set_margin_end(20)

    scroll_backups_list = Gtk.ScrolledWindow()
    scroll_backups_list.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll_backups_list.set_vexpand(True)
    scroll_backups_list.set_min_content_height(150)
    scroll_backups_list.set_child(backups_listbox)

    grid.attach(scroll_backups_list, 0, row, 2, 1)
    row += 1

    # Boutons de gestion des sauvegardes
    create_backup_btn = Gtk.Button(label="Créer")
    create_backup_btn.connect("clicked", lambda b: _on_create_backup(controller, backups_listbox))

    restore_backup_btn = Gtk.Button(label="Restaurer")
    restore_backup_btn.set_sensitive(False)
    restore_backup_btn.get_style_context().add_class("suggested-action")
    restore_backup_btn.connect("clicked", lambda b: _on_restore_backup(controller, backups_listbox))

    delete_backup_btn = Gtk.Button(label="Supprimer")
    delete_backup_btn.set_sensitive(False)
    delete_backup_btn.get_style_context().add_class("destructive-action")
    delete_backup_btn.connect("clicked", lambda b: _on_delete_backup(controller, backups_listbox))

    def _on_backup_selected(_lb: Gtk.ListBox, row_sel: Gtk.ListBoxRow | None) -> None:
        has_sel = row_sel is not None and getattr(row_sel, "backup_path", None) is not None
        restore_backup_btn.set_sensitive(has_sel)
        delete_backup_btn.set_sensitive(has_sel)

    backups_listbox.connect("row-selected", _on_backup_selected)

    backup_btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    backup_btns.set_halign(Gtk.Align.START)
    backup_btns.set_margin_start(20)
    backup_btns.set_margin_top(10)
    backup_btns.append(create_backup_btn)
    backup_btns.append(restore_backup_btn)
    backup_btns.append(delete_backup_btn)

    grid.attach(backup_btns, 0, row, 2, 1)
    row += 1

    # Load backups
    _refresh_backups_list(backups_listbox)

    notebook.append_page(scroll, Gtk.Label(label="Maintenance"))
    logger.success("[build_maintenance_tab] Onglet Maintenance construit")


def _run_consult_command(controller: GrubConfigManager, listbox: Gtk.ListBox) -> None:
    """Exécute une commande de consultation sélectionnée.

    Args:
        controller: GrubConfigManager instance
        listbox: ListBox avec les commandes
    """
    row = listbox.get_selected_row()
    if not row:
        return

    cmd_name = getattr(row, "cmd_name", "")
    cmd_data = getattr(row, "cmd_data", None)

    if not cmd_data:
        return

    logger.info(f"[_run_consult_command] Exécution: {cmd_name}")

    if cmd_data == "find-theme-script":
        _show_theme_script(controller)
    elif isinstance(cmd_data, list):
        _run_command_popup(controller, cmd_data, cmd_name)


def _run_restore_command(controller: GrubConfigManager, listbox: Gtk.ListBox) -> None:
    """Exécute une commande de restauration sélectionnée.

    Args:
        controller: GrubConfigManager instance
        listbox: ListBox avec les commandes
    """
    row = listbox.get_selected_row()
    if not row:
        return

    cmd_name = getattr(row, "cmd_name", "")
    cmd_data = getattr(row, "cmd_data", None)

    if not cmd_data:
        return

    logger.info(f"[_run_restore_command] Exécution: {cmd_name}")

    if cmd_data == "reinstall-05-debian":
        _reinstall_05_debian(controller)
    elif cmd_data == "enable-05-theme":
        _enable_05_debian_theme(controller)
    elif cmd_data == "reinstall-grub-uefi":
        _reinstall_grub_uefi(controller)
    elif cmd_data == "reinstall-grub-bios":
        _reinstall_grub_bios(controller)
    elif isinstance(cmd_data, list):
        _run_command_popup(controller, cmd_data, cmd_name)


def _run_diagnostic(controller: GrubConfigManager, dropdown: Gtk.DropDown, commands: list[tuple[str, str]]) -> None:
    """Run a diagnostic command.

    Executes selected diagnostic command and displays output in a popup window.

    Args:
        controller: GrubConfigManager instance
        dropdown: Dropdown widget with diagnostic commands
        commands: List of (label, command) tuples
    """
    idx = dropdown.get_selected()
    logger.debug(f"[_run_diagnostic] Selected index: {idx}")

    if idx < 0 or idx >= len(commands) or commands[idx][1] == "":
        logger.warning(f"[_run_diagnostic] Invalid selection or empty command at index {idx}")
        return

    _cmd_name, cmd_string = commands[idx]
    logger.info(f"[_run_diagnostic] Running diagnostic: {_cmd_name} (cmd={cmd_string})")

    if cmd_string == "update-grub":
        _run_command_popup(controller, ["update-grub"], "Regénérer grub.cfg")
    elif cmd_string == "grub-script-check":
        _run_command_popup(controller, ["grub-script-check", "/boot/grub/grub.cfg"], "Vérifier syntaxe GRUB")
    elif cmd_string == "lsblk -f":
        _run_command_popup(controller, ["lsblk", "-f"], "Lister partitions")
    elif cmd_string == "cat /etc/default/grub":
        _run_command_popup(controller, ["cat", "/etc/default/grub"], "Voir /etc/default/grub")
    elif cmd_string == "cat /boot/grub/grub.cfg":
        _run_command_popup(controller, ["cat", "/boot/grub/grub.cfg"], "Voir /boot/grub/grub.cfg")
    elif cmd_string == "find-theme-script":
        _show_theme_script(controller)
    elif cmd_string == "efibootmgr":
        _run_command_popup(controller, ["efibootmgr"], "Entrées UEFI")
    elif cmd_string == "grub-emu":
        _run_command_popup(controller, ["grub-emu"], "Preview GRUB (Simulation)")


def _run_restore(controller: GrubConfigManager, dropdown: Gtk.DropDown, commands: list[tuple[str, str]]) -> None:
    """Run a restoration command from repository.

    Executes selected package manager restoration command and shows result in popup.

    Args:
        controller: GrubConfigManager instance
        dropdown: Dropdown widget with restoration commands
        commands: List of (label, command) tuples
    """
    idx = dropdown.get_selected()
    logger.debug(f"[_run_restore] Selected index: {idx}")

    if idx < 0 or idx >= len(commands) or commands[idx][1] == "":
        logger.warning(f"[_run_restore] Invalid selection or empty command at index {idx}")
        return

    cmd_name, cmd_string = commands[idx]
    logger.info(f"[_run_restore] Running restore: {cmd_name}")

    cmd_list = cmd_string.split()
    _run_command_popup(controller, cmd_list, cmd_name)


def _show_theme_script(controller: GrubConfigManager) -> None:
    """Find and display GRUB theme script (theme.txt).

    Searches common GRUB theme locations and displays the theme configuration.

    Args:
        controller: GrubConfigManager instance
    """
    logger.info("[_show_theme_script] Recherche du script du thème GRUB")

    # Lire GRUB_THEME depuis /etc/default/grub
    theme_path = None
    try:
        config = read_grub_default()
        theme_setting = config.get("GRUB_THEME", "")
        if theme_setting:
            # Nettoyer les guillemets
            theme_path = theme_setting.strip('"').strip("'")
            logger.debug(f"[_show_theme_script] GRUB_THEME={theme_path}")
    except OSError as e:
        logger.warning(f"[_show_theme_script] Impossible de lire GRUB_THEME: {e}")

    # Chemins de recherche pour le thème
    theme_locations = []

    if theme_path and os.path.exists(theme_path):
        theme_locations.append(theme_path)

    # Chercher dans les emplacements standards
    common_paths = [
        "/boot/grub/themes/*/theme.txt",
        "/boot/grub2/themes/*/theme.txt",
        "/usr/share/grub/themes/*/theme.txt",
    ]

    for pattern in common_paths:
        theme_locations.extend(glob.glob(pattern))

    # Chercher tous les scripts de génération du thème dans /etc/grub.d/
    # qui contiennent "theme" dans leur nom
    if os.path.exists("/etc/grub.d"):
        for filename in os.listdir("/etc/grub.d"):
            filepath = os.path.join("/etc/grub.d", filename)
            # Chercher les fichiers contenant "theme" et qui sont exécutables
            if "theme" in filename.lower() and os.path.isfile(filepath):
                theme_locations.append(filepath)
                logger.debug(f"[_show_theme_script] Trouvé script de génération: {filepath}")

    # Chercher aussi des fichiers de config dans /boot/grub/ et /boot/grub2/
    grub_config_patterns = [
        "/boot/grub/custom.cfg",
        "/boot/grub2/custom.cfg",
        "/boot/grub/grub.cfg.d/*.cfg",
        "/boot/grub2/grub.cfg.d/*.cfg",
    ]

    for pattern in grub_config_patterns:
        matches = glob.glob(pattern)
        for match in matches:
            # Vérifier si le fichier contient des références au thème
            try:
                with open(match, encoding="utf-8", errors="ignore") as f:
                    content = f.read(500)  # Lire les premiers 500 caractères
                    if "theme" in content.lower():
                        theme_locations.append(match)
                        logger.debug(f"[_show_theme_script] Trouvé config avec thème: {match}")
            except OSError:
                pass

    if not theme_locations:
        logger.warning("[_show_theme_script] Aucun script de thème trouvé")
        controller.show_info("Aucun script de thème GRUB trouvé", "error")
        return

    # Utiliser le premier thème trouvé
    selected_theme = theme_locations[0]
    logger.info(f"[_show_theme_script] Affichage du thème: {selected_theme}")

    # Déterminer le titre selon le type de fichier
    if selected_theme.endswith("theme.txt"):
        title = f"Script du thème: {os.path.basename(os.path.dirname(selected_theme))}"
    else:
        title = f"Script de génération: {os.path.basename(selected_theme)}"

    _run_command_popup(controller, ["cat", selected_theme], title)


def _run_command_popup(controller: GrubConfigManager, command: list[str], title: str, _timeout: int = 30) -> None:
    """Execute a system command and display output in a popup window.

    Runs command with timeout, captures stdout/stderr, and shows in modal dialog.

    Args:
        controller: GrubConfigManager instance
        command: List of command and arguments
        title: Dialog window title
        timeout: Command timeout in seconds
    """
    if os.geteuid() != 0:
        logger.warning("[_run_command_popup] Not running as root")
        controller.show_info("Droits root nécessaires", "error")
        return

    logger.info(f"[_run_command_popup] Executing: {' '.join(command)}")

    # Create popup dialog
    dialog = Gtk.Window()
    dialog.set_transient_for(controller)
    dialog.set_modal(True)
    dialog.set_title(title)

    # Match parent window height, fixed width
    parent_height = controller.get_height()
    dialog.set_default_size(700, parent_height if parent_height > 0 else 500)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    box.set_margin_top(12)
    box.set_margin_bottom(12)
    box.set_margin_start(12)
    box.set_margin_end(12)

    # ScrolledWindow with TextView
    scroll = Gtk.ScrolledWindow()
    scroll.set_vexpand(True)
    scroll.set_hexpand(True)

    textview = Gtk.TextView()
    textview.set_editable(False)
    textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    textview.set_monospace(True)
    textview.set_margin_top(8)
    textview.set_margin_bottom(8)
    textview.set_margin_start(8)
    textview.set_margin_end(8)

    # Helper to append text to buffer
    def append_text(text: str, tag: str | None = None) -> bool:
        """Append text to TextView buffer (called from main thread via GLib.idle_add)."""
        buf = textview.get_buffer()
        end_iter = buf.get_end_iter()
        if tag:
            buf.insert_with_tags_by_name(end_iter, text, tag)
        else:
            buf.insert(end_iter, text)

        # Auto-scroll to bottom
        mark = buf.get_insert()
        textview.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
        return False

    # Setup text tags for colored output
    buf = textview.get_buffer()
    buf.create_tag("error", foreground="red")
    buf.create_tag("success", foreground="green")

    scroll.set_child(textview)
    box.append(scroll)

    # Close button
    close_btn = Gtk.Button(label="Fermer")
    close_btn.set_halign(Gtk.Align.END)
    close_btn.connect("clicked", lambda b: dialog.close())
    box.append(close_btn)

    dialog.set_child(box)
    dialog.present()

    # Exécuter la commande en arrière-plan pour ne pas geler l'UI
    def run_in_thread():
        try:
            # Cas spécial pour grub-emu qui est interactif/graphique
            if command[0] == "grub-emu":
                GLib.idle_add(append_text, "Lancement de la simulation GRUB...\n")

                # Vérifier si grub-emu est installé
                if not shutil.which("grub-emu"):
                    GLib.idle_add(append_text, "Erreur: 'grub-emu' n'est pas installé.\n", "error")
                    GLib.idle_add(append_text, "Installez-le avec: sudo apt install grub-emu\n")
                    return

                # grub-emu ouvre sa propre fenêtre, on attend juste qu'il finisse
                with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as process:
                    process.wait()
                    GLib.idle_add(append_text, "Simulation terminée.\n", "success")
                return

            with subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            ) as process:
                # Lire la sortie ligne par ligne
                for line in process.stdout:
                    GLib.idle_add(append_text, line)

                process.wait()
                logger.info(f"[_run_command_popup] Commande terminée avec le code de retour {process.returncode}")

            if process.returncode == 0:
                GLib.idle_add(append_text, "\nSuccès\n", "success")
            else:
                GLib.idle_add(append_text, f"\nErreur (code {process.returncode})\n", "error")

        except (OSError, subprocess.SubprocessError) as e:
            logger.error(f"[_run_command_popup] Erreur: {e}")
            GLib.idle_add(append_text, f"ERREUR: {e}\n", "error")

    # Démarrer l'exécution de la commande dans un thread en arrière-plan
    logger.debug("[_run_command_popup] Starting command execution in background thread")

    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()


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
                _run_command_popup(controller, cmd, "Réinstaller GRUB (UEFI)")
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
                _run_command_popup(controller, cmd, "Réinstaller GRUB (BIOS)")
        except (OSError, RuntimeError):
            pass

    dialog.choose(controller, None, on_response)


def _on_create_backup(controller: GrubConfigManager, listbox: Gtk.ListBox) -> None:
    """Create a new backup of current GRUB configuration.

    Args:
        controller: GrubConfigManager instance
        listbox: ListBox widget showing backups
    """
    if os.geteuid() != 0:
        logger.warning("[_on_create_backup] Not running as root")
        controller.show_info("Droits administrateur requis", "error")
        return

    try:
        logger.info("[_on_create_backup] Creating new backup")
        backup_path = create_grub_default_backup()
        logger.success(f"[_on_create_backup] Backup created: {backup_path}")
        controller.show_info(f"Sauvegarde: {os.path.basename(backup_path)}", "info")
        _refresh_backups_list(listbox)
    except (OSError, RuntimeError) as e:
        logger.error(f"[_on_create_backup] Failed to create backup: {e}")
        controller.show_info(f"Erreur: {e}", "error")


def _on_restore_backup(controller: GrubConfigManager, listbox: Gtk.ListBox) -> None:
    """Restore a backup of GRUB configuration.

    Args:
        controller: GrubConfigManager instance
        listbox: ListBox widget showing backups
    """
    if os.geteuid() != 0:
        logger.warning("[_on_restore_backup] Not running as root")
        controller.show_info("Droits administrateur requis", "error")
        return

    row = listbox.get_selected_row()
    if row is None or not hasattr(row, "backup_path"):
        logger.warning("[_on_restore_backup] No backup selected")
        return

    backup_path = row.backup_path
    logger.debug(f"[_on_restore_backup] Selected backup: {backup_path}")

    dialog = Gtk.AlertDialog()
    dialog.set_modal(True)
    dialog.set_message("Restaurer la sauvegarde?")
    dialog.set_detail(f"Restaurer: {os.path.basename(backup_path)}")
    dialog.set_buttons(["Annuler", "Restaurer"])
    dialog.set_default_button(0)

    def on_response(d: Gtk.AlertDialog, result: Gtk.AsyncResult) -> None:
        try:
            if d.choose_finish(result) == 1:  # Index 1 = Restaurer
                logger.info(f"[_on_restore_backup] User confirmed restore of {backup_path}")
                shutil.copy2(backup_path, "/etc/default/grub")
                controller.show_info("Configuration restaurée", "info")
                _refresh_backups_list(listbox)
        except (OSError, RuntimeError) as e:
            logger.error(f"[_on_restore_backup] Error during restore: {e}")
            controller.show_info(f"Erreur: {e}", "error")

    dialog.choose(controller, None, on_response)


def _on_delete_backup(controller: GrubConfigManager, _listbox: Gtk.ListBox) -> None:
    """Delete a backup file.

    Args:
        controller: GrubConfigManager instance
        _listbox: ListBox widget showing backups
    """
    if os.geteuid() != 0:
        logger.warning("[_on_delete_backup] Not running as root")
        controller.show_info("Droits administrateur requis", "error")
        return

    row = _listbox.get_selected_row()
    if row is None or not hasattr(row, "backup_path"):
        logger.warning("[_on_delete_backup] No backup selected")
        return

    backup_path = row.backup_path
    logger.debug(f"[_on_delete_backup] Selected backup for deletion: {backup_path}")

    dialog = Gtk.AlertDialog()
    dialog.set_modal(True)
    dialog.set_message("Supprimer cette sauvegarde?")
    dialog.set_detail(f"Supprimé définitivement: {os.path.basename(backup_path)}")
    dialog.set_buttons(["Annuler", "Supprimer"])
    dialog.set_default_button(0)

    def on_response(d: Gtk.AlertDialog, result: Gtk.AsyncResult) -> None:
        try:
            if d.choose_finish(result) == 1:  # Index 1 = Supprimer
                logger.info(f"[_on_delete_backup] User confirmed deletion of {backup_path}")
                delete_grub_default_backup(backup_path)
                logger.info(f"[_on_delete_backup] Suppression: {backup_path}")
                controller.show_info("Sauvegarde supprimée", "info")
                _refresh_backups_list(_listbox)
        except OSError as e:
            logger.error(f"[_on_delete_backup] Erreur: {e}")
            controller.show_info(f"Erreur: {e}", "error")

    dialog.choose(controller, None, on_response)


def _refresh_backups_list(listbox: Gtk.ListBox) -> None:
    """Refresh backup list display.

    Args:
        listbox: ListBox widget to update with backup list
    """
    logger.debug("[_refresh_backups_list] Refreshing backup list display")
    clear_listbox(listbox)
    try:
        backups = list_grub_default_backups()
        logger.debug(f"[_refresh_backups_list] Found {len(backups)} backups")
    except OSError as e:
        logger.error(f"[_refresh_backups_list] Failed to list backups: {e}")
        backups = []

    if not backups:
        logger.debug("[_refresh_backups_list] No backups found")
        row = Gtk.ListBoxRow()
        row.set_selectable(False)
        row.set_child(Gtk.Label(label="Aucune sauvegarde", xalign=0))
        listbox.append(row)
        return

    for p in backups:
        logger.debug(f"[_refresh_backups_list] Adding backup: {os.path.basename(p)} ({categorize_backup_type(p)})")
        row, hbox = create_list_box_row_with_margins()
        row.backup_path = p

        title_label = Gtk.Label(label=os.path.basename(p), xalign=0)
        title_label.set_hexpand(True)
        title_label.set_ellipsize(3)

        kind = Gtk.Label(label=categorize_backup_type(p), xalign=1)
        kind.set_halign(Gtk.Align.END)

        hbox.append(title_label)
        hbox.append(kind)
        row.set_child(hbox)
        listbox.append(row)


def _reinstall_05_debian(controller: GrubConfigManager) -> None:
    """Réinstalle le script /etc/grub.d/05_debian depuis les dépôts.

    Args:
        controller: GrubConfigManager instance
    """
    logger.info("[_reinstall_05_debian] Réinstallation du script 05_debian")

    # Déterminer le gestionnaire de paquets
    cmd = None
    if shutil.which("apt-get"):
        # Debian/Ubuntu - réinstaller le paquet grub-common qui contient 05_debian
        cmd = ["apt-get", "install", "--reinstall", "grub-common"]
    elif shutil.which("pacman"):
        # Arch Linux
        cmd = ["pacman", "-S", "--noconfirm", "grub"]
    elif shutil.which("dnf"):
        # Fedora/RHEL
        cmd = ["dnf", "reinstall", "-y", "grub2-common"]
    elif shutil.which("zypper"):
        # openSUSE
        cmd = ["zypper", "install", "--force", "grub2"]

    if cmd:
        _run_command_popup(controller, cmd, "Réinstallation du script 05_debian")
    else:
        logger.error("[_reinstall_05_debian] Gestionnaire de paquets non trouvé")
        controller.show_info(
            "error",
            "Erreur",
            "Aucun gestionnaire de paquets détecté.\n"
            "Veuillez réinstaller manuellement le paquet contenant /etc/grub.d/05_debian",
        )


def _get_restore_command() -> tuple[str, list[str]] | None:
    """Détecte le gestionnaire de paquets et retourne la commande de réinstallation.

    Returns:
        Tuple (nom_du_gestionnaire, liste_commande) ou None si aucun n'est trouvé
    """
    logger.debug("[_get_restore_command] Détection du gestionnaire de paquets")

    # Vérifier Debian/Ubuntu
    if shutil.which("apt-get"):
        logger.debug("[_get_restore_command] APT détecté")
        return ("APT", ["apt-get", "install", "--reinstall", "grub-common"])

    # Vérifier Arch Linux
    if shutil.which("pacman"):
        logger.debug("[_get_restore_command] Pacman détecté")
        return ("Pacman", ["pacman", "-S", "--noconfirm", "grub"])

    # Vérifier Fedora/RHEL
    if shutil.which("dnf"):
        logger.debug("[_get_restore_command] DNF détecté")
        return ("DNF", ["dnf", "reinstall", "-y", "grub2-common"])

    # Vérifier openSUSE
    if shutil.which("zypper"):
        logger.debug("[_get_restore_command] Zypper détecté")
        return ("Zypper", ["zypper", "install", "--force", "grub2"])

    logger.warning("[_get_restore_command] Aucun gestionnaire de paquets détecté")
    return None


def _enable_05_debian_theme(controller: GrubConfigManager) -> None:
    """Active le script /etc/grub.d/05_debian_theme en le rendant exécutable.

    Args:
        controller: GrubConfigManager instance
    """
    logger.info("[_enable_05_debian_theme] Activation du script 05_debian_theme")

    script_path = "/etc/grub.d/05_debian_theme"

    # Vérifier si le fichier existe
    if not os.path.exists(script_path):
        logger.error(f"[_enable_05_debian_theme] Fichier non trouvé: {script_path}")
        controller.show_info(
            "error",
            "Erreur",
            f"Le fichier {script_path} n'existe pas.\n" "Utilisez 'Réinstaller script' pour le créer.",
        )
        return

    # Rendre exécutable
    cmd = ["chmod", "+x", script_path]
    _run_command_popup(controller, cmd, "Activation du script 05_debian_theme")
