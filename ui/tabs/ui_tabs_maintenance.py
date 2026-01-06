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
    create_info_box,
    create_tab_grid_layout,
    create_titled_frame,
)
from ui.dialogs.ui_dialogs_index import run_command_popup
from ui.helpers.ui_helpers_gtk import GtkHelper

if TYPE_CHECKING:
    from ui.controllers.ui_controllers_manager import GrubConfigManager


def _get_boot_info() -> str:
    return "UEFI" if os.path.exists("/sys/firmware/efi") else "BIOS"


def _update_consultation_note(
    dropdown: Gtk.DropDown,
    config_files: list[tuple[str, str]],
    note_label: Gtk.Label | None,
) -> None:
    if note_label is None:
        return
    selected_idx = dropdown.get_selected()
    if selected_idx == Gtk.INVALID_LIST_POSITION or selected_idx >= len(config_files):
        note_label.set_label("Sélectionnez un fichier GRUB à afficher.")
        return
    file_name, file_path = config_files[selected_idx]

    # Éviter un doublon visuel quand le "nom" est déjà le chemin.
    display_name = str(file_name)
    display_path = str(file_path)
    if display_name.strip() == display_path.strip():
        display = display_path
    else:
        display = f"{display_name}\n{display_path}"

    note_label.set_label("Fichier sélectionné :\n" f"{display}\n\n" 'Cliquez sur "Afficher le fichier" pour l\'ouvrir.')


def _update_diag_note(
    dropdown: Gtk.DropDown,
    diag_commands: list[tuple[str, list[str]]],
    note_label: Gtk.Label | None,
) -> None:
    if note_label is None:
        return
    selected_idx = dropdown.get_selected()
    if selected_idx == Gtk.INVALID_LIST_POSITION or selected_idx >= len(diag_commands):
        note_label.set_label("Choisissez une commande de diagnostic.")
        return
    cmd_name, cmd_data = diag_commands[selected_idx]
    cmd_str = " ".join(cmd_data)
    note_label.set_label(
        "Commande sélectionnée :\n"
        f"{cmd_name}\n\n"
        f"{cmd_str}\n\n"
        'Cliquez sur "Exécuter la commande" pour la lancer.'
    )


def _update_restore_note(
    dropdown: Gtk.DropDown,
    restore_commands: list[tuple[str, any]],
    note_label: Gtk.Label | None,
) -> None:
    if note_label is None:
        return
    selected_idx = dropdown.get_selected()
    if selected_idx == Gtk.INVALID_LIST_POSITION or selected_idx >= len(restore_commands):
        note_label.set_label("Choisissez une action de restauration/réinstallation.")
        return
    cmd_name, cmd_data = restore_commands[selected_idx]

    if isinstance(cmd_data, list):
        cmd_str = " ".join(str(x) for x in cmd_data)
    else:
        cmd_str = str(cmd_data)

    note_label.set_label(
        "Action sélectionnée :\n"
        f"{cmd_name}\n\n"
        f"{cmd_str}\n\n"
        "Attention : certaines actions nécessitent les droits root et peuvent affecter le démarrage."
    )


def _build_system_info_block(*, boot_type: str) -> Gtk.Frame:
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    apply_margins(content, 12)

    boot_label = Gtk.Label(xalign=0)
    boot_label.set_markup(f"<b>Type de démarrage :</b> {boot_type}")
    content.append(boot_label)

    return create_titled_frame(
        "Informations système",
        content,
        title_class="green",
        frame_class="green-frame",
    )


def _build_consultation_block(
    *,
    controller: GrubConfigManager,
) -> tuple[Gtk.Frame, Gtk.DropDown, list[tuple[str, str]]]:
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    apply_margins(content, 12)

    config_files = _get_config_files()
    config_dropdown = Gtk.DropDown.new_from_strings([name for name, _ in config_files])
    config_dropdown.set_halign(Gtk.Align.FILL)
    config_dropdown.set_hexpand(True)
    content.append(config_dropdown)

    btn_view_config = Gtk.Button(label="Afficher le fichier")
    btn_view_config.add_css_class("suggested-action")
    btn_view_config.set_halign(Gtk.Align.FILL)
    btn_view_config.connect("clicked", lambda _b: _on_view_config(controller, config_dropdown, config_files))
    content.append(btn_view_config)

    return (
        create_titled_frame(
            "Consultation",
            content,
            title_class="blue",
            frame_class="blue-frame",
        ),
        config_dropdown,
        config_files,
    )


def _build_diagnostic_block(
    *,
    controller: GrubConfigManager,
    boot_type: str,
) -> tuple[Gtk.Frame, Gtk.DropDown, list[tuple[str, list[str]]]]:
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    apply_margins(content, 12)

    diag_commands = _get_diagnostic_commands(boot_type)
    diag_dropdown = Gtk.DropDown.new_from_strings([name for name, _ in diag_commands])
    diag_dropdown.set_halign(Gtk.Align.FILL)
    diag_dropdown.set_hexpand(True)
    content.append(diag_dropdown)

    btn_exec_diag = Gtk.Button(label="Exécuter la commande")
    btn_exec_diag.add_css_class("suggested-action")
    btn_exec_diag.set_halign(Gtk.Align.FILL)
    btn_exec_diag.connect("clicked", lambda _b: _on_exec_diag(controller, diag_dropdown, diag_commands))
    content.append(btn_exec_diag)

    return (
        create_titled_frame(
            "Commandes de diagnostic",
            content,
            title_class="orange",
            frame_class="orange-frame",
        ),
        diag_dropdown,
        diag_commands,
    )


def _build_restore_block(
    *,
    controller: GrubConfigManager,
    boot_type: str,
    service: MaintenanceService,
) -> tuple[Gtk.Frame, Gtk.DropDown, list[tuple[str, any]]]:
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    apply_margins(content, 12)

    restore_commands = _get_restore_commands(service, boot_type)
    restore_dropdown = Gtk.DropDown.new_from_strings([name for name, _ in restore_commands])
    restore_dropdown.set_halign(Gtk.Align.FILL)
    restore_dropdown.set_hexpand(True)
    content.append(restore_dropdown)

    btn_exec_restore = Gtk.Button(label="Exécuter l'action")
    btn_exec_restore.add_css_class("destructive-action")
    btn_exec_restore.set_halign(Gtk.Align.FILL)
    btn_exec_restore.connect(
        "clicked", lambda _b: _on_exec_restore(controller, restore_dropdown, restore_commands, service)
    )
    content.append(btn_exec_restore)

    return (
        create_titled_frame(
            "Restauration et réinstallation",
            content,
            title_class="red",
            frame_class="red-frame",
        ),
        restore_dropdown,
        restore_commands,
    )


def _attach_system_row(*, main_grid: Gtk.Grid, boot_type: str) -> None:
    system_block = _build_system_info_block(boot_type=boot_type)
    system_block.set_valign(Gtk.Align.START)
    system_block.set_vexpand(False)
    main_grid.attach(system_block, 0, 0, 1, 1)

    system_note = create_info_box(
        "Démarrage détecté:",
        f"Votre système semble démarrer en mode {boot_type}.",
        css_class="success-box compact-card",
    )
    system_note.set_valign(Gtk.Align.START)
    system_note.set_vexpand(False)
    system_note.set_hexpand(False)
    main_grid.attach(system_note, 1, 0, 1, 1)


def _attach_consultation_row(*, controller: GrubConfigManager, main_grid: Gtk.Grid, row: int) -> None:
    consult_block, config_dropdown, config_files = _build_consultation_block(controller=controller)
    consult_block.set_valign(Gtk.Align.START)
    consult_block.set_vexpand(False)
    main_grid.attach(consult_block, 0, row, 1, 1)

    consult_note = create_info_box(
        "Consultation:",
        "Sélectionnez un fichier GRUB à afficher.",
        css_class="info-box compact-card",
    )
    consult_note.set_valign(Gtk.Align.START)
    consult_note.set_vexpand(False)
    consult_note.set_hexpand(False)
    consult_note_label = GtkHelper.info_box_text_label(consult_note)
    main_grid.attach(consult_note, 1, row, 1, 1)

    _update_consultation_note(config_dropdown, config_files, consult_note_label)
    config_dropdown.connect(
        "notify::selected",
        lambda dd, _ps: _update_consultation_note(dd, config_files, consult_note_label),
    )


def _attach_diagnostic_row(
    *,
    controller: GrubConfigManager,
    main_grid: Gtk.Grid,
    row: int,
    boot_type: str,
) -> None:
    diag_block, diag_dropdown, diag_commands = _build_diagnostic_block(
        controller=controller,
        boot_type=boot_type,
    )
    diag_block.set_valign(Gtk.Align.START)
    diag_block.set_vexpand(False)
    main_grid.attach(diag_block, 0, row, 1, 1)

    diag_note = create_info_box(
        "Diagnostic:",
        "Choisissez une commande de diagnostic.",
        css_class="warning-box compact-card",
    )
    diag_note.set_valign(Gtk.Align.START)
    diag_note.set_vexpand(False)
    diag_note.set_hexpand(False)
    main_grid.attach(diag_note, 1, row, 1, 1)

    diag_note_label = GtkHelper.info_box_text_label(diag_note)
    _update_diag_note(diag_dropdown, diag_commands, diag_note_label)
    diag_dropdown.connect(
        "notify::selected",
        lambda dd, _ps: _update_diag_note(dd, diag_commands, diag_note_label),
    )


def _attach_restore_row(
    *,
    controller: GrubConfigManager,
    main_grid: Gtk.Grid,
    row: int,
    boot_type: str,
    service: MaintenanceService,
) -> None:
    restore_block, restore_dropdown, restore_commands = _build_restore_block(
        controller=controller,
        boot_type=boot_type,
        service=service,
    )
    restore_block.set_valign(Gtk.Align.START)
    restore_block.set_vexpand(False)
    main_grid.attach(restore_block, 0, row, 1, 1)

    restore_note = create_info_box(
        "Restauration:",
        "Choisissez une action de restauration/réinstallation.",
        css_class="error-box compact-card",
    )
    restore_note.set_valign(Gtk.Align.START)
    restore_note.set_vexpand(False)
    restore_note.set_hexpand(False)
    main_grid.attach(restore_note, 1, row, 1, 1)

    restore_note_label = GtkHelper.info_box_text_label(restore_note)
    _update_restore_note(restore_dropdown, restore_commands, restore_note_label)
    restore_dropdown.connect(
        "notify::selected",
        lambda dd, _ps: _update_restore_note(dd, restore_commands, restore_note_label),
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

    # Template comme Général/Affichage: grille 2 colonnes (outils à gauche, notes à droite)
    main_grid = create_tab_grid_layout(root)
    main_grid.set_row_spacing(26)

    boot_type = _get_boot_info()

    _attach_system_row(main_grid=main_grid, boot_type=boot_type)
    _attach_consultation_row(controller=controller, main_grid=main_grid, row=1)
    _attach_diagnostic_row(controller=controller, main_grid=main_grid, row=2, boot_type=boot_type)
    _attach_restore_row(
        controller=controller,
        main_grid=main_grid,
        row=3,
        boot_type=boot_type,
        service=service,
    )

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

    # Éviter les doublons (observé sur certaines distros / montages)
    unique: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in config_files:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)

    return unique


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
