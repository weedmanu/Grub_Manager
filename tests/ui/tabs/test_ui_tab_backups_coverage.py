"""Tests de couverture pour ui_tab_backups."""

import tarfile
from unittest.mock import MagicMock, patch

import pytest
from gi.repository import Gtk

import ui.tabs.ui_tab_backups as ui_backups


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.get_height.return_value = 600
    return controller

def test_get_listbox_from_frame_full_stack():
    frame = Gtk.Frame()
    scroll = Gtk.ScrolledWindow()
    viewport = Gtk.Viewport()
    listbox = Gtk.ListBox()
    viewport.set_child(listbox)
    scroll.set_child(viewport)
    frame.set_child(scroll)
    assert ui_backups._get_listbox_from_frame(frame) == listbox

def test_get_listbox_from_frame_no_child():
    frame = Gtk.Frame()
    assert ui_backups._get_listbox_from_frame(frame) is None

def test_get_listbox_from_frame_wrong_child():
    frame = Gtk.Frame()
    frame.set_child(Gtk.Label(label="Not a listbox"))
    assert ui_backups._get_listbox_from_frame(frame) is None

def test_on_create_clicked_empty_tar(mock_controller):
    mock_tar = MagicMock()
    mock_tar.getnames.return_value = []
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.create_grub_default_backup", return_value="/p"),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.tarfile.open", return_value=mock_tar),
    ):
        mock_tar.__enter__.return_value = mock_tar
        ui_backups._on_create_clicked(None, mock_controller, None)
        assert "vide" in mock_controller.show_info.call_args[0][0]

def test_refresh_list_size_formatting(mock_controller):
    list_frame = Gtk.Frame()
    # Test B, KB, MB
    for size in [500, 5000, 5000000]:
        with (
            patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/p"]),
            patch("ui.tabs.ui_tab_backups.os.path.getmtime", return_value=1234567890),
            patch("ui.tabs.ui_tab_backups.os.path.getsize", return_value=size),
        ):
            ui_backups._refresh_list(mock_controller, list_frame)
            assert isinstance(list_frame.get_child(), Gtk.ScrolledWindow)

def test_on_create_clicked_no_root(mock_controller):
    with patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=1000):
        ui_backups._on_create_clicked(None, mock_controller, None)
        assert "administrateur" in mock_controller.show_info.call_args[0][0]

def test_on_create_clicked_file_not_found(mock_controller):
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.create_grub_default_backup", return_value="/p"),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=False),
    ):
        ui_backups._on_create_clicked(None, mock_controller, None)
        assert "n'a pas été créé" in mock_controller.show_info.call_args[0][0]

def test_on_create_clicked_tar_error(mock_controller):
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.create_grub_default_backup", return_value="/p"),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.tarfile.open", side_effect=tarfile.TarError("Bad tar")),
    ):
        ui_backups._on_create_clicked(None, mock_controller, None)
        assert "Bad tar" in mock_controller.show_info.call_args[0][0]

def test_on_create_clicked_generic_exception(mock_controller):
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.create_grub_default_backup", side_effect=RuntimeError("Boom")),
    ):
        ui_backups._on_create_clicked(None, mock_controller, None)
        assert "Boom" in mock_controller.show_info.call_args[0][0]

def test_on_restore_clicked_no_root(mock_controller):
    with patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=1000):
        ui_backups._on_restore_clicked(None, mock_controller, None)
        assert "administrateur" in mock_controller.show_info.call_args[0][0]

def test_on_restore_clicked_no_listbox(mock_controller):
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups._get_listbox_from_frame", return_value=None),
    ):
        ui_backups._on_restore_clicked(None, mock_controller, MagicMock())

def test_on_restore_clicked_no_selection(mock_controller):
    listbox = MagicMock(spec=Gtk.ListBox)
    listbox.get_selected_row.return_value = None
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups._get_listbox_from_frame", return_value=listbox),
    ):
        ui_backups._on_restore_clicked(None, mock_controller, MagicMock())
        assert "sélectionner" in mock_controller.show_info.call_args[0][0]

def test_on_restore_clicked_exception(mock_controller):
    listbox = MagicMock(spec=Gtk.ListBox)
    row = MagicMock()
    row.backup_path = "/p"
    listbox.get_selected_row.return_value = row
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups._get_listbox_from_frame", return_value=listbox),
        patch("ui.tabs.ui_tab_backups.restore_grub_default_backup", side_effect=Exception("Err")),
        patch("ui.tabs.ui_tab_backups.confirm_action", side_effect=lambda cb, m, c: cb()),
    ):
        ui_backups._on_restore_clicked(None, mock_controller, MagicMock())
        assert "Err" in mock_controller.show_info.call_args[0][0]

def test_on_delete_clicked_no_root(mock_controller):
    with patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=1000):
        ui_backups._on_delete_clicked(None, mock_controller, None, None)
        assert "administrateur" in mock_controller.show_info.call_args[0][0]

def test_on_delete_clicked_no_listbox(mock_controller):
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups._get_listbox_from_frame", return_value=None),
    ):
        ui_backups._on_delete_clicked(None, mock_controller, MagicMock(), None)

def test_on_delete_clicked_no_selection(mock_controller):
    listbox = MagicMock(spec=Gtk.ListBox)
    listbox.get_selected_row.return_value = None
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups._get_listbox_from_frame", return_value=listbox),
    ):
        ui_backups._on_delete_clicked(None, mock_controller, MagicMock(), None)
        assert "sélectionner" in mock_controller.show_info.call_args[0][0]

def test_on_delete_clicked_exception(mock_controller):
    listbox = MagicMock(spec=Gtk.ListBox)
    row = MagicMock()
    row.backup_path = "/p"
    listbox.get_selected_row.return_value = row
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups._get_listbox_from_frame", return_value=listbox),
        patch("ui.tabs.ui_tab_backups.delete_grub_default_backup", side_effect=Exception("Err")),
        patch("ui.tabs.ui_tab_backups.confirm_action", side_effect=lambda cb, m, c: cb()),
    ):
        ui_backups._on_delete_clicked(None, mock_controller, MagicMock(), None)
        assert "Err" in mock_controller.show_info.call_args[0][0]

def test_on_create_clicked_success(mock_controller):
    refresh_callback = MagicMock()
    mock_tar = MagicMock()
    mock_tar.getnames.return_value = ["file1"]
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.create_grub_default_backup", return_value="/p"),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.tarfile.open", return_value=mock_tar),
    ):
        mock_tar.__enter__.return_value = mock_tar
        ui_backups._on_create_clicked(None, mock_controller, refresh_callback)
        assert refresh_callback.called

def test_on_restore_clicked_success(mock_controller):
    listbox = MagicMock(spec=Gtk.ListBox)
    row = MagicMock()
    row.backup_path = "/p"
    listbox.get_selected_row.return_value = row
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups._get_listbox_from_frame", return_value=listbox),
        patch("ui.tabs.ui_tab_backups.restore_grub_default_backup"),
        patch("ui.tabs.ui_tab_backups.confirm_action", side_effect=lambda cb, m, c: cb()),
    ):
        ui_backups._on_restore_clicked(None, mock_controller, MagicMock())
        assert mock_controller.reload_from_disk.called

def test_on_delete_clicked_success(mock_controller):
    listbox = MagicMock(spec=Gtk.ListBox)
    row = MagicMock()
    row.backup_path = "/p"
    listbox.get_selected_row.return_value = row
    refresh_callback = MagicMock()
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups._get_listbox_from_frame", return_value=listbox),
        patch("ui.tabs.ui_tab_backups.delete_grub_default_backup"),
        patch("ui.tabs.ui_tab_backups.confirm_action", side_effect=lambda cb, m, c: cb()),
    ):
        ui_backups._on_delete_clicked(None, mock_controller, MagicMock(), refresh_callback)
        assert refresh_callback.called

def test_on_selection_changed():
    btn_restore = MagicMock()
    btn_delete = MagicMock()
    ui_backups._on_selection_changed(None, None, btn_restore, btn_delete)
    btn_restore.set_sensitive.assert_called_with(False)

    row = MagicMock()
    row.backup_path = "/p"
    ui_backups._on_selection_changed(None, row, btn_restore, btn_delete)
    btn_restore.set_sensitive.assert_called_with(True)

def test_refresh_list_os_error(mock_controller):
    list_frame = Gtk.Frame()
    with patch("ui.tabs.ui_tab_backups.list_grub_default_backups", side_effect=OSError("Err")):
        ui_backups._refresh_list(mock_controller, list_frame)
        assert "Impossible" in mock_controller.show_info.call_args[0][0]

def test_refresh_list_os_error_in_loop(mock_controller):
    list_frame = Gtk.Frame()
    with (
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/p"]),
        patch("ui.tabs.ui_tab_backups.os.path.getmtime", side_effect=OSError),
    ):
        ui_backups._refresh_list(mock_controller, list_frame)
        assert isinstance(list_frame.get_child(), Gtk.ScrolledWindow)

def test_build_backups_tab(mock_controller):
    notebook = MagicMock(spec=Gtk.Notebook)
    with patch("ui.tabs.ui_tab_backups.GLib.idle_add", side_effect=lambda f: f()):
        ui_backups.build_backups_tab(mock_controller, notebook)
        assert notebook.append_page.called

def test_refresh_list_no_backups(mock_controller):
    list_frame = Gtk.Frame()
    btn_restore = Gtk.Button()
    btn_delete = Gtk.Button()
    with patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]):
        ui_backups._refresh_list(mock_controller, list_frame, btn_restore, btn_delete)
        assert not btn_restore.get_sensitive()
