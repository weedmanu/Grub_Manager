"""Tests pour l'onglet Maintenance refactorisé."""

from unittest.mock import MagicMock, patch

import gi
import pytest

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ui.tabs.ui_tab_maintenance import (
    _on_exec_diag,
    _on_exec_restore,
    _on_view_config,
    _reinstall_grub_bios,
    _reinstall_grub_uefi,
    _run_consult_command,
    _run_restore_command,
    _show_theme_script,
    build_maintenance_tab,
)


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.get_height.return_value = 600
    return controller


@pytest.fixture
def mock_notebook():
    return MagicMock(spec=Gtk.Notebook)


@pytest.fixture
def mock_service():
    return MagicMock()


def test_build_maintenance_tab(mock_controller, mock_notebook):
    """Test la construction de l'onglet maintenance."""
    with (
        patch("ui.tabs.ui_tab_maintenance.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_maintenance.shutil.which", return_value="/usr/bin/grub-emu"),
        patch("ui.tabs.ui_tab_maintenance.MaintenanceService") as MockService,
    ):

        # Configure mock service
        mock_service_instance = MockService.return_value
        mock_service_instance.get_restore_command.return_value = ("APT", ["apt", "install"])

        build_maintenance_tab(mock_controller, mock_notebook)

        assert mock_notebook.append_page.called
        args, _ = mock_notebook.append_page.call_args
        assert isinstance(args[0], Gtk.Box)
        assert args[1].get_label() == "Maintenance"


def test_build_maintenance_tab_empty_grub_d(mock_controller, mock_notebook):
    """Test build_maintenance_tab when /etc/grub.d is empty."""
    with (
        patch("ui.tabs.ui_tab_maintenance.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_maintenance.os.listdir", return_value=[]),
        patch("ui.tabs.ui_tab_maintenance.shutil.which", return_value=None),
        patch("ui.tabs.ui_tab_maintenance.MaintenanceService") as MockService,
    ):
        mock_service_instance = MockService.return_value
        mock_service_instance.get_restore_command.return_value = None
        build_maintenance_tab(mock_controller, mock_notebook)
        # This should cover the False case of the any() generator


def test_run_consult_command_find_theme(mock_controller, mock_service):
    """Test run_consult_command avec find-theme-script."""
    listbox = MagicMock()
    row = MagicMock()
    row.cmd_name = "Voir script"
    row.cmd_data = "find-theme-script"
    listbox.get_selected_row.return_value = row

    with patch("ui.tabs.ui_tab_maintenance._show_theme_script") as mock_show:
        _run_consult_command(mock_controller, listbox, mock_service)
        mock_show.assert_called_with(mock_controller, mock_service)


def test_run_consult_command_list(mock_controller, mock_service):
    """Test run_consult_command avec une liste de commande."""
    listbox = MagicMock()
    row = MagicMock()
    row.cmd_name = "LS"
    row.cmd_data = ["ls", "-l"]
    listbox.get_selected_row.return_value = row

    with patch("ui.tabs.ui_tab_maintenance.run_command_popup") as mock_popup:
        _run_consult_command(mock_controller, listbox, mock_service)
        mock_popup.assert_called_with(mock_controller, ["ls", "-l"], "LS")


def test_run_restore_command_reinstall_05(mock_controller, mock_service):
    """Test run_restore_command avec reinstall-05-debian."""
    listbox = MagicMock()
    row = MagicMock()
    row.cmd_name = "Reinstall 05"
    row.cmd_data = "reinstall-05-debian"
    listbox.get_selected_row.return_value = row

    mock_service.get_reinstall_05_debian_command.return_value = ["apt", "install"]

    with patch("ui.tabs.ui_tab_maintenance.run_command_popup") as mock_popup:
        _run_restore_command(mock_controller, listbox, mock_service)
        mock_popup.assert_called_with(mock_controller, ["apt", "install"], "Réinstallation du script 05_debian")


def test_run_restore_command_reinstall_05_none(mock_controller, mock_service):
    """Test run_restore_command avec reinstall-05-debian sans gestionnaire."""
    listbox = MagicMock()
    row = MagicMock()
    row.cmd_name = "Reinstall 05"
    row.cmd_data = "reinstall-05-debian"
    listbox.get_selected_row.return_value = row

    mock_service.get_reinstall_05_debian_command.return_value = None

    _run_restore_command(mock_controller, listbox, mock_service)
    mock_controller.show_info.assert_called_with("Aucun gestionnaire de paquets détecté", "error")


def test_run_restore_command_enable_05(mock_controller, mock_service):
    """Test run_restore_command avec enable-05-theme."""
    listbox = MagicMock()
    row = MagicMock()
    row.cmd_name = "Enable 05"
    row.cmd_data = "enable-05-theme"
    listbox.get_selected_row.return_value = row

    mock_service.get_enable_05_debian_theme_command.return_value = ["chmod"]

    with patch("ui.tabs.ui_tab_maintenance.run_command_popup") as mock_popup:
        _run_restore_command(mock_controller, listbox, mock_service)
        mock_popup.assert_called_with(mock_controller, ["chmod"], "Activation du script 05_debian_theme")


def test_show_theme_script_found(mock_controller, mock_service):
    """Test show_theme_script quand le thème est trouvé."""
    mock_service.find_theme_script_path.return_value = "/boot/grub/themes/starfield/theme.txt"

    with patch("ui.tabs.ui_tab_maintenance.run_command_popup") as mock_popup:
        _show_theme_script(mock_controller, mock_service)
        mock_popup.assert_called()
        assert "/boot/grub/themes/starfield/theme.txt" in mock_popup.call_args[0][1]


def test_show_theme_script_not_found(mock_controller, mock_service):
    """Test show_theme_script quand le thème n'est pas trouvé."""
    mock_service.find_theme_script_path.return_value = None

    _show_theme_script(mock_controller, mock_service)
    mock_controller.show_info.assert_called_with("Aucun script de thème GRUB trouvé", "error")


def test_reinstall_grub_uefi_success(mock_controller):
    """Test reinstall_grub_uefi avec confirmation."""
    with (
        patch("ui.tabs.ui_tab_maintenance.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_maintenance.Gtk.AlertDialog") as mock_dialog_class,
        patch("ui.tabs.ui_tab_maintenance.run_command_popup") as mock_popup,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, _, callback):
            mock_result = MagicMock()
            mock_dialog.choose_finish.return_value = 1
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose

        _reinstall_grub_uefi(mock_controller)
        mock_popup.assert_called()
        assert "grub-install" in mock_popup.call_args[0][1]


def test_reinstall_grub_bios_success(mock_controller):
    """Test reinstall_grub_bios avec confirmation."""
    with (
        patch("ui.tabs.ui_tab_maintenance.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_maintenance.Gtk.AlertDialog") as mock_dialog_class,
        patch("ui.tabs.ui_tab_maintenance.run_command_popup") as mock_popup,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, _, callback):
            mock_result = MagicMock()
            mock_dialog.choose_finish.return_value = 1
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose

        _reinstall_grub_bios(mock_controller)
        mock_popup.assert_called()
        assert "grub-install" in mock_popup.call_args[0][1]


def test_build_maintenance_tab_bios(mock_controller, mock_notebook):
    """Test build_maintenance_tab for BIOS system."""
    with (
        patch("ui.tabs.ui_tab_maintenance.os.path.exists", return_value=False),
        patch("ui.tabs.ui_tab_maintenance.shutil.which", return_value=None),
        patch("ui.tabs.ui_tab_maintenance.MaintenanceService") as MockService,
    ):

        mock_service_instance = MockService.return_value
        mock_service_instance.get_restore_command.return_value = None

        build_maintenance_tab(mock_controller, mock_notebook)
        assert mock_notebook.append_page.called


def test_run_consult_command_no_selection(mock_controller, mock_service):
    """Test run_consult_command with no selection."""
    listbox = MagicMock()
    listbox.get_selected_row.return_value = None
    _run_consult_command(mock_controller, listbox, mock_service)
    # Should just return without error


def test_run_consult_command_no_data(mock_controller, mock_service):
    """Test run_consult_command with row having no data."""
    listbox = MagicMock()
    row = MagicMock()
    row.cmd_data = None
    listbox.get_selected_row.return_value = row
    _run_consult_command(mock_controller, listbox, mock_service)


def test_run_restore_command_no_selection(mock_controller, mock_service):
    """Test run_restore_command with no selection."""
    listbox = MagicMock()
    listbox.get_selected_row.return_value = None
    _run_restore_command(mock_controller, listbox, mock_service)


def test_run_restore_command_no_data(mock_controller, mock_service):
    """Test run_restore_command with row having no data."""
    listbox = MagicMock()
    row = MagicMock()
    row.cmd_data = None
    listbox.get_selected_row.return_value = row
    _run_restore_command(mock_controller, listbox, mock_service)


def test_run_restore_command_uefi(mock_controller, mock_service):
    """Test run_restore_command with reinstall-grub-uefi."""
    listbox = MagicMock()
    row = MagicMock()
    row.cmd_name = "UEFI"
    row.cmd_data = "reinstall-grub-uefi"
    listbox.get_selected_row.return_value = row

    with patch("ui.tabs.ui_tab_maintenance._reinstall_grub_uefi") as mock_reinstall:
        _run_restore_command(mock_controller, listbox, mock_service)
        mock_reinstall.assert_called_with(mock_controller)


def test_run_restore_command_bios(mock_controller, mock_service):
    """Test run_restore_command with reinstall-grub-bios."""
    listbox = MagicMock()
    row = MagicMock()
    row.cmd_name = "BIOS"
    row.cmd_data = "reinstall-grub-bios"
    listbox.get_selected_row.return_value = row

    with patch("ui.tabs.ui_tab_maintenance._reinstall_grub_bios") as mock_reinstall:
        _run_restore_command(mock_controller, listbox, mock_service)
        mock_reinstall.assert_called_with(mock_controller)


def test_run_restore_command_list(mock_controller, mock_service):
    """Test run_restore_command with generic list command."""
    listbox = MagicMock()
    row = MagicMock()
    row.cmd_name = "Generic"
    row.cmd_data = ["echo", "test"]
    listbox.get_selected_row.return_value = row

    with patch("ui.tabs.ui_tab_maintenance.run_command_popup") as mock_popup:
        _run_restore_command(mock_controller, listbox, mock_service)
        mock_popup.assert_called_with(mock_controller, ["echo", "test"], "Generic")


def test_show_theme_script_custom_cfg(mock_controller, mock_service):
    """Test show_theme_script with custom.cfg (not ending in theme.txt)."""
    mock_service.find_theme_script_path.return_value = "/boot/grub/custom.cfg"

    with patch("ui.tabs.ui_tab_maintenance.run_command_popup") as mock_popup:
        _show_theme_script(mock_controller, mock_service)
        mock_popup.assert_called()
        assert "Script de génération" in mock_popup.call_args[0][2]


def test_reinstall_grub_uefi_non_root(mock_controller):
    """Test reinstall_grub_uefi as non-root."""
    with patch("ui.tabs.ui_tab_maintenance.os.geteuid", return_value=1000):
        _reinstall_grub_uefi(mock_controller)
        mock_controller.show_info.assert_called_with("Droits root nécessaires", "error")


def test_reinstall_grub_uefi_exception(mock_controller):
    """Test reinstall_grub_uefi with exception during dialog."""
    with (
        patch("ui.tabs.ui_tab_maintenance.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_maintenance.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, _, callback):
            mock_result = MagicMock()
            mock_dialog.choose_finish.side_effect = OSError("Fail")
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose

        _reinstall_grub_uefi(mock_controller)
        # Should catch exception and do nothing


def test_reinstall_grub_bios_non_root(mock_controller):
    """Test reinstall_grub_bios as non-root."""
    with patch("ui.tabs.ui_tab_maintenance.os.geteuid", return_value=1000):
        _reinstall_grub_bios(mock_controller)
        mock_controller.show_info.assert_called_with("Droits root nécessaires", "error")


def test_reinstall_grub_bios_exception(mock_controller):
    """Test reinstall_grub_bios with exception during dialog."""
    with (
        patch("ui.tabs.ui_tab_maintenance.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_maintenance.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, _, callback):
            mock_result = MagicMock()
            mock_dialog.choose_finish.side_effect = RuntimeError("Fail")
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose

        _reinstall_grub_bios(mock_controller)
        # Should catch exception and do nothing


def test_reinstall_grub_uefi_cancel(mock_controller):
    """Test reinstall_grub_uefi with cancel."""
    with (
        patch("ui.tabs.ui_tab_maintenance.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_maintenance.Gtk.AlertDialog") as mock_dialog_class,
        patch("ui.tabs.ui_tab_maintenance.run_command_popup") as mock_popup,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, _, callback):
            mock_result = MagicMock()
            mock_dialog.choose_finish.return_value = 0  # Cancel
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose

        _reinstall_grub_uefi(mock_controller)
        mock_popup.assert_not_called()


def test_reinstall_grub_bios_cancel(mock_controller):
    """Test reinstall_grub_bios with cancel."""
    with (
        patch("ui.tabs.ui_tab_maintenance.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_maintenance.Gtk.AlertDialog") as mock_dialog_class,
        patch("ui.tabs.ui_tab_maintenance.run_command_popup") as mock_popup,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, _, callback):
            mock_result = MagicMock()
            mock_dialog.choose_finish.return_value = 0  # Cancel
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose

        _reinstall_grub_bios(mock_controller)
        mock_popup.assert_not_called()


def test_run_consult_command_no_cmd_data():
    """Test _run_consult_command with row having no cmd_data."""
    controller = MagicMock()
    listbox = MagicMock()
    service = MagicMock()

    row = MagicMock()
    row.cmd_data = None
    listbox.get_selected_row.return_value = row

    from ui.tabs.ui_tab_maintenance import _run_consult_command

    _run_consult_command(controller, listbox, service)
    # Should return early, no calls on controller or service
    assert not service.method_calls


def test_run_restore_command_no_cmd_data():
    """Test _run_restore_command with row having no cmd_data."""
    controller = MagicMock()
    listbox = MagicMock()
    service = MagicMock()

    row = MagicMock()
    row.cmd_data = None
    listbox.get_selected_row.return_value = row

    from ui.tabs.ui_tab_maintenance import _run_restore_command

    _run_restore_command(controller, listbox, service)
    # Should return early
    assert not service.method_calls


def test_show_theme_script_none():
    """Test _show_theme_script when no path is found."""
    controller = MagicMock()
    service = MagicMock()
    service.find_theme_script_path.return_value = None

    from ui.tabs.ui_tab_maintenance import _show_theme_script

    _show_theme_script(controller, service)

    controller.show_info.assert_called_with("Aucun script de thème GRUB trouvé", "error")


def test_reinstall_grub_uefi_response_exception():
    """Test _reinstall_grub_uefi response callback with exception."""
    controller = MagicMock()

    # Mock os.geteuid to return 0 (root)
    with patch("os.geteuid", return_value=0):
        from ui.tabs.ui_tab_maintenance import _reinstall_grub_uefi

        # Mock Gtk.AlertDialog
        with patch("gi.repository.Gtk.AlertDialog") as MockDialog:
            mock_dialog_instance = MockDialog.return_value

            # Capture the callback
            _reinstall_grub_uefi(controller)
            args, _ = mock_dialog_instance.choose.call_args
            callback = args[2]

            # Simulate exception in callback
            mock_dialog_instance.choose_finish.side_effect = OSError("Fail")
            callback(mock_dialog_instance, MagicMock())
            # Should pass silently


def test_reinstall_grub_bios_response_exception():
    """Test _reinstall_grub_bios response callback with exception."""
    controller = MagicMock()

    # Mock os.geteuid to return 0 (root)
    with patch("os.geteuid", return_value=0):
        from ui.tabs.ui_tab_maintenance import _reinstall_grub_bios

        # Mock Gtk.AlertDialog
        with patch("gi.repository.Gtk.AlertDialog") as MockDialog:
            mock_dialog_instance = MockDialog.return_value

            # Capture the callback
            _reinstall_grub_bios(controller)
            args, _ = mock_dialog_instance.choose.call_args
            callback = args[2]

            # Simulate exception in callback
            mock_dialog_instance.choose_finish.side_effect = OSError("Fail")
            callback(mock_dialog_instance, MagicMock())
            # Should pass silently


def test_run_consult_command_unhandled_data(mock_controller, mock_service):
    """Test _run_consult_command with unhandled data."""
    listbox = MagicMock()
    row = MagicMock()
    row.cmd_name = "Unknown"
    row.cmd_data = "unknown-command"
    listbox.get_selected_row.return_value = row

    _run_consult_command(mock_controller, listbox, mock_service)
    # Should do nothing


def test_run_restore_command_unhandled_data(mock_controller, mock_service):
    """Test _run_restore_command with unhandled data."""
    listbox = MagicMock()
    row = MagicMock()
    row.cmd_name = "Unknown"
    row.cmd_data = "unknown-command"
    listbox.get_selected_row.return_value = row

    _run_restore_command(mock_controller, listbox, mock_service)
    # Should do nothing


def test_button_clicks(mock_controller, mock_service):
    """Test that the buttons are created with correct labels."""
    notebook = MagicMock()
    build_maintenance_tab(mock_controller, notebook)

    assert notebook.append_page.called
    root = notebook.append_page.call_args[0][0]

    # Find all buttons in the hierarchy
    buttons = []

    def find_buttons(widget):
        if isinstance(widget, Gtk.Button):
            buttons.append(widget)
        child = widget.get_first_child()
        while child:
            find_buttons(child)
            child = child.get_next_sibling()

    find_buttons(root)

    # We expect at least 3 buttons: View Config, Exec Diag, Exec Restore
    assert len(buttons) >= 3

    labels = [btn.get_label() for btn in buttons if btn.get_label() is not None]
    assert any("Afficher" in l for l in labels)
    assert any("Exécuter la commande" in l for l in labels)
    assert any("Exécuter l'action" in l for l in labels)


def test_dropdown_selections(mock_controller, mock_service):
    """Test that dropdown selections work."""
    notebook = MagicMock()
    build_maintenance_tab(mock_controller, notebook)

    root = notebook.append_page.call_args[0][0]

    # Find all dropdowns
    dropdowns = []

    def find_dropdowns(widget):
        if isinstance(widget, Gtk.DropDown):
            dropdowns.append(widget)
        child = widget.get_first_child()
        while child:
            find_dropdowns(child)
            child = child.get_next_sibling()

    find_dropdowns(root)
    assert len(dropdowns) >= 3

    for dd in dropdowns:
        dd.set_selected(0)
        assert dd.get_selected() == 0


def test_on_view_config_success(mock_controller):
    dropdown = MagicMock()
    dropdown.get_selected.return_value = 0
    config_files = [("Test", "/path/to/file")]

    with (
        patch("ui.tabs.ui_tab_maintenance.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_maintenance.run_command_popup") as mock_popup,
    ):
        _on_view_config(mock_controller, dropdown, config_files)
        mock_popup.assert_called_once()


def test_on_view_config_not_found(mock_controller):
    dropdown = MagicMock()
    dropdown.get_selected.return_value = 0
    config_files = [("Test", "/path/to/file")]

    with patch("ui.tabs.ui_tab_maintenance.os.path.exists", return_value=False):
        _on_view_config(mock_controller, dropdown, config_files)
        mock_controller.show_info.assert_called_once()


def test_on_exec_diag(mock_controller):
    dropdown = MagicMock()
    dropdown.get_selected.return_value = 0
    diag_commands = [("Test", ["cmd"])]

    with patch("ui.tabs.ui_tab_maintenance.run_command_popup") as mock_popup:
        _on_exec_diag(mock_controller, dropdown, diag_commands)
        mock_popup.assert_called_once_with(mock_controller, ["cmd"], "Test")


def test_on_exec_restore(mock_controller, mock_service):
    dropdown = MagicMock()
    dropdown.get_selected.return_value = 0
    restore_commands = [("Test", ["cmd"])]

    with patch("ui.tabs.ui_tab_maintenance._run_restore_command_direct") as mock_restore:
        _on_exec_restore(mock_controller, dropdown, restore_commands, mock_service)
        mock_restore.assert_called_once_with(mock_controller, "Test", ["cmd"], mock_service)
