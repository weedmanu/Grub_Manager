
import pytest
from unittest.mock import MagicMock, patch
from gi.repository import Gtk, Gio
import os
import shutil

# Set headless backend for GTK
os.environ["GDK_BACKEND"] = "headless"

from ui.tabs.ui_tab_maintenance import (
    build_maintenance_tab,
    _on_view_config,
    _on_exec_diag,
    _on_exec_restore,
    _run_restore_command_direct,
    _reinstall_grub_uefi,
    _reinstall_grub_bios,
    _get_config_files,
    _get_diagnostic_commands,
    _get_restore_commands
)

class MockController(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.show_info = MagicMock()

@pytest.fixture
def controller():
    return MockController()

@pytest.fixture
def service():
    s = MagicMock()
    s.get_restore_command.return_value = ("apt", ["sudo", "apt", "install", "--reinstall", "grub-pc"])
    s.get_reinstall_05_debian_command.return_value = ["sudo", "apt", "install", "--reinstall", "grub-common"]
    s.get_enable_05_debian_theme_command.return_value = ["sudo", "chmod", "+x", "/etc/grub.d/05_debian_theme"]
    return s

def test_build_maintenance_tab(controller, service):
    notebook = Gtk.Notebook()
    with patch("ui.tabs.ui_tab_maintenance.MaintenanceService", return_value=service), \
         patch("os.path.exists", return_value=True), \
         patch("os.listdir", return_value=["00_header", "05_debian_theme"]), \
         patch("os.path.isfile", return_value=True), \
         patch("shutil.which", return_value="/usr/bin/grub-emu"):
        
        build_maintenance_tab(controller, notebook)
        assert notebook.get_n_pages() == 1

def test_get_config_files():
    with patch("os.path.exists", side_effect=lambda p: p == "/etc/grub.d"), \
         patch("os.listdir", return_value=["00_header", "05_debian_theme", "40_custom"]), \
         patch("os.path.isfile", side_effect=lambda p: "05_debian_theme" in p):
        
        files = _get_config_files()
        # Expected: /etc/default/grub, /boot/grub/grub.cfg, 05_debian_theme
        assert len(files) == 3
        assert any("05_debian_theme" in f[0] for f in files)

def test_get_diagnostic_commands():
    with patch("shutil.which", return_value="/usr/bin/grub-emu"):
        cmds = _get_diagnostic_commands("UEFI")
        # Expected: lsblk, grub-script-check, efibootmgr, grub-emu
        assert len(cmds) == 4
        assert any("UEFI" in c[0] for c in cmds)
        assert any("Simulation" in c[0] for c in cmds)

    with patch("shutil.which", return_value=None):
        cmds = _get_diagnostic_commands("BIOS")
        # Expected: lsblk, grub-script-check
        assert len(cmds) == 2

def test_get_restore_commands(service):
    cmds = _get_restore_commands(service, "UEFI")
    assert len(cmds) == 5
    assert any("UEFI" in c[0] for c in cmds)
    
    service.get_restore_command.return_value = None
    cmds = _get_restore_commands(service, "BIOS")
    assert len(cmds) == 4
    assert any("BIOS" in c[0] for c in cmds)

def test_on_view_config(controller):
    config_files = [("File1", "/path/1"), ("File2", "/path/2")]
    dropdown = MagicMock(spec=Gtk.DropDown)
    
    # Case 1: File exists
    dropdown.get_selected.return_value = 0
    with patch("os.path.exists", return_value=True), \
         patch("ui.tabs.ui_tab_maintenance.run_command_popup") as mock_popup:
        _on_view_config(controller, dropdown, config_files)
        mock_popup.assert_called_with(controller, ["cat", "/path/1"], "Contenu de File1")
        
    # Case 2: File missing
    dropdown.get_selected.return_value = 1
    with patch("os.path.exists", return_value=False):
        _on_view_config(controller, dropdown, config_files)
        controller.show_info.assert_called_with("Fichier introuvable : /path/2", "error")

    # Case 3: Index out of bounds
    dropdown.get_selected.return_value = 5
    _on_view_config(controller, dropdown, config_files) # Should do nothing

def test_on_exec_diag(controller):
    diag_commands = [("Diag1", ["cmd1"]), ("Diag2", ["cmd2"])]
    dropdown = MagicMock(spec=Gtk.DropDown)
    
    dropdown.get_selected.return_value = 1
    with patch("ui.tabs.ui_tab_maintenance.run_command_popup") as mock_popup:
        _on_exec_diag(controller, dropdown, diag_commands)
        mock_popup.assert_called_with(controller, ["cmd2"], "Diag2")

    # Index out of bounds
    dropdown.get_selected.return_value = 5
    _on_exec_diag(controller, dropdown, diag_commands) # Should do nothing

def test_on_exec_restore(controller, service):
    restore_commands = [("Restore1", "reinstall-05-debian"), ("Restore2", ["list", "cmd"])]
    dropdown = MagicMock(spec=Gtk.DropDown)
    
    dropdown.get_selected.return_value = 0
    with patch("ui.tabs.ui_tab_maintenance._run_restore_command_direct") as mock_run:
        _on_exec_restore(controller, dropdown, restore_commands, service)
        mock_run.assert_called_with(controller, "Restore1", "reinstall-05-debian", service)

    # Index out of bounds
    dropdown.get_selected.return_value = 5
    _on_exec_restore(controller, dropdown, restore_commands, service) # Should do nothing

def test_get_config_files_with_non_file():
    with patch("os.path.exists", side_effect=lambda p: p == "/etc/grub.d"), \
         patch("os.listdir", return_value=["05_debian_theme"]), \
         patch("os.path.isfile", return_value=False):
        
        files = _get_config_files()
        # Expected: /etc/default/grub, /boot/grub/grub.cfg (05_debian_theme is NOT a file)
        assert len(files) == 2

def test_run_restore_command_direct(controller, service):
    with patch("ui.tabs.ui_tab_maintenance.run_command_popup") as mock_popup:
        # reinstall-05-debian
        _run_restore_command_direct(controller, "Name", "reinstall-05-debian", service)
        mock_popup.assert_called()
        
        # reinstall-05-debian (no manager)
        service.get_reinstall_05_debian_command.return_value = None
        _run_restore_command_direct(controller, "Name", "reinstall-05-debian", service)
        controller.show_info.assert_called_with("Aucun gestionnaire de paquets détecté", "error")
        
        # enable-05-theme
        _run_restore_command_direct(controller, "Name", "enable-05-theme", service)
        mock_popup.assert_called()
        
        # list command
        _run_restore_command_direct(controller, "Name", ["some", "cmd"], service)
        mock_popup.assert_called_with(controller, ["some", "cmd"], "Name")

        # something else (False branch of last elif)
        _run_restore_command_direct(controller, "Name", 123, service)
        # Should just exit

def test_run_restore_command_direct_reinstall_calls(controller, service):
    with patch("ui.tabs.ui_tab_maintenance._reinstall_grub_uefi") as mock_uefi, \
         patch("ui.tabs.ui_tab_maintenance._reinstall_grub_bios") as mock_bios:
        
        _run_restore_command_direct(controller, "Name", "reinstall-grub-uefi", service)
        mock_uefi.assert_called_once()
        
        _run_restore_command_direct(controller, "Name", "reinstall-grub-bios", service)
        mock_bios.assert_called_once()

def test_reinstall_grub_uefi_no_root(controller):
    with patch("os.geteuid", return_value=1000):
        _reinstall_grub_uefi(controller)
        controller.show_info.assert_called_with("Droits root nécessaires", "error")

def test_reinstall_grub_bios_no_root(controller):
    with patch("os.geteuid", return_value=1000):
        _reinstall_grub_bios(controller)
        controller.show_info.assert_called_with("Droits root nécessaires", "error")

@patch("gi.repository.Gtk.AlertDialog")
def test_reinstall_grub_uefi_root(mock_dialog_class, controller):
    mock_dialog = mock_dialog_class.return_value
    with patch("os.geteuid", return_value=0):
        _reinstall_grub_uefi(controller)
        mock_dialog.choose.assert_called_once()
        
        # Test callback (index 2 in choose(parent, cancellable, callback))
        callback = mock_dialog.choose.call_args[0][2]
        
        # Simulate "Reinstall" (index 1)
        mock_dialog.choose_finish.return_value = 1
        with patch("ui.tabs.ui_tab_maintenance.run_command_popup") as mock_popup:
            callback(mock_dialog, MagicMock(spec=Gio.AsyncResult))
            mock_popup.assert_called()
            
        # Simulate "Cancel" (index 0)
        mock_dialog.choose_finish.return_value = 0
        with patch("ui.tabs.ui_tab_maintenance.run_command_popup") as mock_popup:
            callback(mock_dialog, MagicMock(spec=Gio.AsyncResult))
            mock_popup.assert_not_called()

@patch("gi.repository.Gtk.AlertDialog")
def test_reinstall_grub_bios_root(mock_dialog_class, controller):
    mock_dialog = mock_dialog_class.return_value
    with patch("os.geteuid", return_value=0):
        _reinstall_grub_bios(controller)
        mock_dialog.choose.assert_called_once()
        
        # Test callback
        callback = mock_dialog.choose.call_args[0][2]
        
        # Simulate "Reinstall" (index 1)
        mock_dialog.choose_finish.return_value = 1
        with patch("ui.tabs.ui_tab_maintenance.run_command_popup") as mock_popup:
            callback(mock_dialog, MagicMock(spec=Gio.AsyncResult))
            mock_popup.assert_called()

        # Simulate "Cancel" (index 0)
        mock_dialog.choose_finish.return_value = 0
        with patch("ui.tabs.ui_tab_maintenance.run_command_popup") as mock_popup:
            callback(mock_dialog, MagicMock(spec=Gio.AsyncResult))
            mock_popup.assert_not_called()

def test_reinstall_grub_uefi_exception(controller):
    with patch("os.geteuid", return_value=0), \
         patch("gi.repository.Gtk.AlertDialog") as mock_dialog_class:
        mock_dialog = mock_dialog_class.return_value
        _reinstall_grub_uefi(controller)
        callback = mock_dialog.choose.call_args[0][2]
        
        mock_dialog.choose_finish.side_effect = OSError("Test Error")
        callback(mock_dialog, MagicMock(spec=Gio.AsyncResult))

        mock_dialog.choose_finish.side_effect = RuntimeError("Test Error")
        callback(mock_dialog, MagicMock(spec=Gio.AsyncResult))

def test_reinstall_grub_bios_exception(controller):
    with patch("os.geteuid", return_value=0), \
         patch("gi.repository.Gtk.AlertDialog") as mock_dialog_class:
        mock_dialog = mock_dialog_class.return_value
        _reinstall_grub_bios(controller)
        callback = mock_dialog.choose.call_args[0][2]
        
        mock_dialog.choose_finish.side_effect = OSError("Test Error")
        callback(mock_dialog, MagicMock(spec=Gio.AsyncResult))

        mock_dialog.choose_finish.side_effect = RuntimeError("Test Error")
        callback(mock_dialog, MagicMock(spec=Gio.AsyncResult))

def test_get_config_files_no_dir():
    with patch("os.path.exists", return_value=False):
        files = _get_config_files()
        assert len(files) == 2 # Only default and cfg
