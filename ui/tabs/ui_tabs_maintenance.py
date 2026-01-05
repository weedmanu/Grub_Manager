"""Onglet Maintenance (GTK4) - Outils de réparation GRUB."""

from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING

from gi.repository import Gtk
from loguru import logger

from core.services.core_services_maintenance import MaintenanceService
from ui.builders.ui_builders_widgets import (
    apply_margins,
    box_append_section_grid,
    create_info_box,
    create_titled_frame,
    create_two_column_layout,
)
from ui.dialogs.ui_dialogs_index import run_command_popup

if TYPE_CHECKING:
    from ui.controllers.ui_controllers_manager import GrubConfigManager


def _get_boot_info() -> str:
    return "UEFI" if os.path.exists("/sys/firmware/efi") else "BIOS"


def _build_system_info(root: Gtk.Box, *, boot_type: str) -> None:
    grid = box_append_section_grid(
        root,
        "Informations système",
        row_spacing=8,
        column_spacing=12,
        title_class="orange",
        frame_class="orange-frame",
    )

    boot_label = Gtk.Label(xalign=0)
    boot_label.set_markup(f"<b>Type de démarrage :</b> {boot_type}")
    grid.attach(boot_label, 0, 0, 2, 1)


def _build_consultation_section(
    consult_section: Gtk.Box,
    *,
    controller: GrubConfigManager,
    boot_type: str,
) -> None:
    # --- Consultation ---
    grid_consult = box_append_section_grid(
        consult_section,
        "Consultation",
        row_spacing=12,
        column_spacing=12,
        title_class="blue",
        frame_class="blue-frame",
    )

    config_files = _get_config_files()
    config_dropdown = Gtk.DropDown.new_from_strings([name for name, _ in config_files])
    config_dropdown.set_halign(Gtk.Align.FILL)
    config_dropdown.set_hexpand(True)
    grid_consult.attach(config_dropdown, 0, 0, 2, 1)

    btn_view_config = Gtk.Button(label="Afficher le fichier")
    btn_view_config.add_css_class("suggested-action")
    btn_view_config.set_halign(Gtk.Align.FILL)
    btn_view_config.connect("clicked", lambda _b: _on_view_config(controller, config_dropdown, config_files))
    grid_consult.attach(btn_view_config, 0, 1, 2, 1)

    # --- Diagnostic ---
    grid_diag = box_append_section_grid(
        consult_section,
        "Commandes de diagnostic",
        row_spacing=12,
        column_spacing=12,
        title_class="orange",
        frame_class="orange-frame",
    )

    diag_commands = _get_diagnostic_commands(boot_type)
    diag_dropdown = Gtk.DropDown.new_from_strings([name for name, _ in diag_commands])
    diag_dropdown.set_halign(Gtk.Align.FILL)
    diag_dropdown.set_hexpand(True)
    grid_diag.attach(diag_dropdown, 0, 0, 2, 1)

    btn_exec_diag = Gtk.Button(label="Exécuter la commande")
    btn_exec_diag.add_css_class("suggested-action")
    btn_exec_diag.set_halign(Gtk.Align.FILL)
    btn_exec_diag.connect("clicked", lambda _b: _on_exec_diag(controller, diag_dropdown, diag_commands))
    grid_diag.attach(btn_exec_diag, 0, 1, 2, 1)


def _build_restore_section(
    restore_section: Gtk.Box,
    *,
    controller: GrubConfigManager,
    boot_type: str,
    service: MaintenanceService,
) -> None:
    grid_restore = box_append_section_grid(
        restore_section,
        "Restauration et réinstallation",
        row_spacing=12,
        column_spacing=12,
        title_class="red",
        frame_class="red-frame",
    )

    restore_commands = _get_restore_commands(service, boot_type)
    restore_dropdown = Gtk.DropDown.new_from_strings([name for name, _ in restore_commands])
    restore_dropdown.set_halign(Gtk.Align.FILL)
    restore_dropdown.set_hexpand(True)
    grid_restore.attach(restore_dropdown, 0, 0, 2, 1)

    btn_exec_restore = Gtk.Button(label="Exécuter l'action")
    btn_exec_restore.add_css_class("destructive-action")
    btn_exec_restore.set_halign(Gtk.Align.FILL)
    btn_exec_restore.connect(
        "clicked", lambda _b: _on_exec_restore(controller, restore_dropdown, restore_commands, service)
    )
    grid_restore.attach(btn_exec_restore, 0, 1, 2, 1)

    restore_section.append(
        create_info_box(
            "Attention:",
            "La réinstallation de GRUB peut affecter le démarrage d'autres systèmes.",
            css_class="error-box compact-card",
        )
    )


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

    root.append(
        create_info_box(
            "Maintenance:",
            "Outils de diagnostic et réparation. Nécessite les droits root.",
            css_class="info-box",
        )
    )

    boot_type = _get_boot_info()
    _build_system_info(root, boot_type=boot_type)

    tools_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    _, consult_section, restore_section = create_two_column_layout(tools_box, spacing=12)
    root.append(create_titled_frame("Outils de diagnostic et réparation", tools_box))

    _build_consultation_section(consult_section, controller=controller, boot_type=boot_type)
    _build_restore_section(restore_section, controller=controller, boot_type=boot_type, service=service)

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
        ("/etc/default/grub", "/etc/default/grub"),
        ("/boot/grub/grub.cfg", "/boot/grub/grub.cfg"),
    ]

    for script_name, script_path in sorted(grub_d_scripts):
        config_files.append((f"{script_name}", script_path))

    return config_files


def _get_diagnostic_commands(boot_type: str) -> list[tuple[str, list[str]]]:
    """Retourne la liste des commandes de diagnostic disponibles."""
    diag_commands = [
        ("Lister partitions", ["lsblk", "-f"]),
        ("Vérifier syntaxe GRUB", ["grub-script-check", "/boot/grub/grub.cfg"]),
    ]

    if boot_type == "UEFI":
        diag_commands.append(("Entrées UEFI", ["efibootmgr"]))

    if shutil.which("grub-emu"):
        diag_commands.append(("Preview GRUB (Simulation)", ["grub-emu"]))

    return diag_commands


def _get_restore_commands(service: MaintenanceService, boot_type: str) -> list[tuple[str, any]]:
    """Retourne la liste des commandes de restauration disponibles."""
    restore_cmd = service.get_restore_command()
    restore_commands = []

    if restore_cmd:
        cmd_name, cmd_list = restore_cmd
        restore_commands.append((f"Réinstaller GRUB ({cmd_name})", cmd_list))

    restore_commands.append(("Réinstaller script /etc/grub.d/05_debian", "reinstall-05-debian"))
    restore_commands.append(("Activer /etc/grub.d/05_debian_theme", "enable-05-theme"))
    restore_commands.append(("Regénérer grub.cfg (update-grub)", ["update-grub"]))

    if boot_type == "UEFI":
        restore_commands.append(("Réinstaller GRUB (UEFI)", "reinstall-grub-uefi"))
    else:
        restore_commands.append(("Réinstaller GRUB (BIOS)", "reinstall-grub-bios"))

    return restore_commands
