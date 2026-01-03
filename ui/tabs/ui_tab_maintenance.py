"""Onglet Maintenance (GTK4) - Outils de réparation GRUB."""

from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING

from gi.repository import Gtk
from loguru import logger

from core.services.core_maintenance_service import MaintenanceService
from ui.ui_dialogs import run_command_popup
from ui.ui_widgets import (
    apply_margins,
    box_append_label,
    box_append_section_title,
    create_two_column_layout,
)

if TYPE_CHECKING:
    from ui.ui_manager import GrubConfigManager


def build_maintenance_tab(controller: GrubConfigManager, notebook: Gtk.Notebook) -> None:
    """Build Maintenance tab with repair tools.

    Provides:
    - Diagnostic commands (update-grub, check syntax, list partitions)
    - Restoration from repositories
    """
    logger.debug("[build_maintenance_tab] Construction de l'onglet Maintenance")
    service = MaintenanceService()

    # Conteneur principal avec marges harmonisées
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    apply_margins(root, 12)

    # Titre et description
    box_append_section_title(root, "Maintenance GRUB")
    box_append_label(root, "Outils de diagnostic et réparation. Nécessite les droits root.", italic=True)

    # === Informations système ===
    info_frame = Gtk.Frame()
    info_frame.set_margin_bottom(8)
    info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    apply_margins(info_box, 12)

    boot_type = "UEFI" if os.path.exists("/sys/firmware/efi") else "Legacy BIOS"
    boot_icon = "🔷" if boot_type == "UEFI" else "🔶"

    info_title = Gtk.Label(xalign=0)
    info_title.set_markup("<b>Informations système</b>")
    info_box.append(info_title)

    boot_label = Gtk.Label(xalign=0)
    boot_label.set_markup(f"{boot_icon} <b>Type de démarrage :</b> {boot_type}")
    info_box.append(boot_label)

    info_frame.set_child(info_box)
    root.append(info_frame)

    # === Titre des outils ===
    tools_title = Gtk.Label(xalign=0)
    tools_title.set_markup("<b>Outils de Diagnostic et Réparation</b>")
    tools_title.add_css_class("section-title")
    tools_title.set_margin_top(8)
    root.append(tools_title)

    # === Conteneur 2 colonnes ===
    _, consult_section, restore_section = create_two_column_layout(root)

    # === Section Commandes de consultation/vérification (COLONNE GAUCHE) ===
    # consult_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8) # Déjà créé
    # consult_section.set_hexpand(True)
    # consult_section.set_vexpand(True)

    consult_title = Gtk.Label(xalign=0)
    consult_title.set_markup("<b>Consultation</b>")
    consult_title.add_css_class("section-title")
    consult_section.append(consult_title)

    box_append_label(consult_section, "Sélectionnez un fichier pour afficher son contenu.", italic=True)

    # Détection des scripts et construction de la liste
    config_files = _get_config_files()

    # Dropdown pour sélectionner le fichier
    config_dropdown = Gtk.DropDown.new_from_strings([name for name, _ in config_files])
    config_dropdown.set_halign(Gtk.Align.FILL)
    consult_section.append(config_dropdown)

    # Bouton pour afficher le fichier sélectionné
    btn_view_config = Gtk.Button(label="📖 Afficher le fichier sélectionné")
    btn_view_config.add_css_class("suggested-action")
    btn_view_config.set_halign(Gtk.Align.END)
    btn_view_config.set_margin_top(8)

    btn_view_config.connect("clicked", lambda _b: _on_view_config(controller, config_dropdown, config_files))
    consult_section.append(btn_view_config)

    # Séparateur
    separator1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    separator1.set_margin_top(12)
    separator1.set_margin_bottom(8)
    consult_section.append(separator1)

    # Sous-section pour autres commandes de diagnostic
    diag_title = Gtk.Label(xalign=0)
    diag_title.set_markup("<b>Commandes de Diagnostic</b>")
    diag_title.add_css_class("section-title")
    consult_section.append(diag_title)

    box_append_label(consult_section, "Outils de vérification et diagnostic système.", italic=True)

    # Liste des autres commandes de diagnostic
    diag_commands = _get_diagnostic_commands(boot_type)

    # Dropdown pour sélectionner la commande de diagnostic
    diag_dropdown = Gtk.DropDown.new_from_strings([name for name, _ in diag_commands])
    diag_dropdown.set_halign(Gtk.Align.FILL)
    consult_section.append(diag_dropdown)

    # Bouton exécuter diagnostic
    btn_exec_diag = Gtk.Button(label="▶️ Exécuter la commande")
    btn_exec_diag.add_css_class("suggested-action")
    btn_exec_diag.set_halign(Gtk.Align.END)
    btn_exec_diag.set_margin_top(8)

    btn_exec_diag.connect("clicked", lambda _b: _on_exec_diag(controller, diag_dropdown, diag_commands))
    consult_section.append(btn_exec_diag)

    # two_columns.append(consult_section) # Déjà ajouté par create_two_column_layout

    # === Section Restauration/Réinstallation (COLONNE DROITE) ===
    # restore_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8) # Déjà créé
    # restore_section.set_hexpand(True)
    # restore_section.set_vexpand(True)

    restore_title = Gtk.Label(xalign=0)
    restore_title.set_markup("<b>Restauration et Réinstallation</b>")
    restore_title.add_css_class("section-title")
    restore_section.append(restore_title)

    box_append_label(restore_section, "⚠️ Ces commandes modifient le système.", italic=True)

    # Liste des commandes de restauration
    restore_commands = _get_restore_commands(service, boot_type)

    # Dropdown pour sélectionner l'action
    restore_dropdown = Gtk.DropDown.new_from_strings([name for name, _ in restore_commands])
    restore_dropdown.set_halign(Gtk.Align.FILL)
    restore_section.append(restore_dropdown)

    # Bouton exécuter restauration
    btn_exec_restore = Gtk.Button(label="⚙️ Exécuter l'action sélectionnée")
    btn_exec_restore.add_css_class("destructive-action")
    btn_exec_restore.set_halign(Gtk.Align.END)
    btn_exec_restore.set_margin_top(8)

    btn_exec_restore.connect(
        "clicked", lambda _b: _on_exec_restore(controller, restore_dropdown, restore_commands, service)
    )
    restore_section.append(btn_exec_restore)

    # two_columns.append(restore_section) # Déjà ajouté par create_two_column_layout

    # Pas de ScrolledWindow externe - tout tient dans la fenêtre
    notebook.append_page(root, Gtk.Label(label="Maintenance"))
    logger.success("[build_maintenance_tab] Onglet Maintenance construit")


def _run_restore_command_direct(
    controller: GrubConfigManager, cmd_name: str, cmd_data, service: MaintenanceService
) -> None:
    """Exécute directement une commande de restauration."""
    logger.info(f"[_run_restore_command_direct] Exécution: {cmd_name}")

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


def _on_view_config(controller: GrubConfigManager, dropdown: Gtk.DropDown, config_files: list[tuple[str, str]]) -> None:
    """Affiche le contenu du fichier sélectionné."""
    selected_idx = dropdown.get_selected()
    if selected_idx < len(config_files):
        file_name, file_path = config_files[selected_idx]
        if os.path.exists(file_path):
            run_command_popup(controller, ["cat", file_path], f"Contenu de {file_name}")
        else:
            controller.show_info(f"Fichier introuvable : {file_path}", "error")


def _on_exec_diag(
    controller: GrubConfigManager, dropdown: Gtk.DropDown, diag_commands: list[tuple[str, list[str]]]
) -> None:
    """Execute selected diagnostic command."""
    selected_idx = dropdown.get_selected()
    if selected_idx < len(diag_commands):
        cmd_name, cmd_data = diag_commands[selected_idx]
        run_command_popup(controller, cmd_data, cmd_name)


def _on_exec_restore(
    controller: GrubConfigManager,
    dropdown: Gtk.DropDown,
    restore_commands: list[tuple[str, any]],
    service: MaintenanceService,
) -> None:
    """Execute selected restore command."""
    selected_idx = dropdown.get_selected()
    if selected_idx < len(restore_commands):
        cmd_name, cmd_data = restore_commands[selected_idx]
        _run_restore_command_direct(controller, cmd_name, cmd_data, service)


def _get_config_files() -> list[tuple[str, str]]:
    """Détecte les fichiers de configuration GRUB consultables."""
    grub_d_scripts = []
    if os.path.exists("/etc/grub.d"):
        for script_name in os.listdir("/etc/grub.d"):
            script_path = f"/etc/grub.d/{script_name}"
            if any(keyword in script_name.lower() for keyword in ["theme", "color", "05_debian"]):
                if os.path.isfile(script_path):
                    grub_d_scripts.append((script_name, script_path))

    config_files = [
        ("📄 /etc/default/grub", "/etc/default/grub"),
        ("📄 /boot/grub/grub.cfg", "/boot/grub/grub.cfg"),
    ]

    for script_name, script_path in sorted(grub_d_scripts):
        config_files.append((f"🎨 {script_name}", script_path))

    return config_files


def _get_diagnostic_commands(boot_type: str) -> list[tuple[str, list[str]]]:
    """Retourne la liste des commandes de diagnostic disponibles."""
    diag_commands = [
        ("💾 Lister partitions", ["lsblk", "-f"]),
        ("✓ Vérifier syntaxe GRUB", ["grub-script-check", "/boot/grub/grub.cfg"]),
    ]

    if boot_type == "UEFI":
        diag_commands.append(("⚡ Entrées UEFI", ["efibootmgr"]))

    if shutil.which("grub-emu"):
        diag_commands.append(("🖥️  Preview GRUB (Simulation)", ["grub-emu"]))

    return diag_commands


def _get_restore_commands(service: MaintenanceService, boot_type: str) -> list[tuple[str, any]]:
    """Retourne la liste des commandes de restauration disponibles."""
    restore_cmd = service.get_restore_command()
    restore_commands = []

    if restore_cmd:
        cmd_name, cmd_list = restore_cmd
        restore_commands.append((f"📦 Réinstaller GRUB ({cmd_name})", cmd_list))

    restore_commands.append(("🔧 Réinstaller script /etc/grub.d/05_debian", "reinstall-05-debian"))
    restore_commands.append(("🎨 Activer /etc/grub.d/05_debian_theme", "enable-05-theme"))
    restore_commands.append(("🔄 Regénérer grub.cfg (update-grub)", ["update-grub"]))

    if boot_type == "UEFI":
        restore_commands.append(("⚡ Réinstaller GRUB (UEFI)", "reinstall-grub-uefi"))
    else:
        restore_commands.append(("🔶 Réinstaller GRUB (BIOS)", "reinstall-grub-bios"))

    return restore_commands
