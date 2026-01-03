"""Tests de couverture supplémentaires pour ui_tab_backups."""

from unittest.mock import MagicMock, patch

import pytest
from gi.repository import Gtk

from ui.tabs.ui_tab_backups import (
    _get_listbox_from_frame,
    _on_create_clicked,
    _on_delete_clicked,
    _on_restore_clicked,
    build_backups_tab,
)


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.get_height.return_value = 600
    return controller


@pytest.fixture
def mock_notebook():
    return MagicMock(spec=Gtk.Notebook)


def test_get_listbox_from_frame_none():
    """Test _get_listbox_from_frame avec une frame vide."""
    frame = Gtk.Frame()
    assert _get_listbox_from_frame(frame) is None


def test_get_listbox_from_frame_scrolled_no_child():
    """Test _get_listbox_from_frame avec un ScrolledWindow sans enfant."""
    frame = Gtk.Frame()
    scroll = Gtk.ScrolledWindow()
    frame.set_child(scroll)
    assert _get_listbox_from_frame(frame) is None


def test_get_listbox_from_frame_viewport_no_child():
    """Test _get_listbox_from_frame avec un Viewport sans enfant."""
    frame = Gtk.Frame()
    viewport = Gtk.Viewport()
    frame.set_child(viewport)
    assert _get_listbox_from_frame(frame) is None


def test_refresh_list_os_error_on_stat(mock_controller, mock_notebook):
    """Test _refresh_list quand os.path.getmtime lève une OSError."""
    backups = ["/path/to/backup"]
    with (
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=backups),
        patch("ui.tabs.ui_tab_backups.os.path.getmtime", side_effect=OSError("Stat error")),
        patch("ui.tabs.ui_tab_backups.categorize_backup_type", return_value="Manuel"),
    ):
        build_backups_tab(mock_controller, mock_notebook)
        # On vérifie juste que ça ne crash pas et que le bloc except OSError est passé


def test_on_create_clicked_exception(mock_controller):
    """Test _on_create_clicked avec une exception générique."""
    refresh_callback = MagicMock()
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.create_grub_default_backup", side_effect=Exception("Unexpected error")),
    ):
        _on_create_clicked(MagicMock(), mock_controller, refresh_callback)
        assert "❌ Échec de la création" in mock_controller.show_info.call_args[0][0]


def test_on_create_clicked_empty_tar(mock_controller):
    """Test _on_create_clicked avec une archive tar vide."""
    refresh_callback = MagicMock()
    mock_tar = MagicMock()
    mock_tar.getnames.return_value = []
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.create_grub_default_backup", return_value="/path/to/backup"),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.tarfile.open", return_value=mock_tar),
    ):
        mock_tar.__enter__.return_value = mock_tar
        _on_create_clicked(MagicMock(), mock_controller, refresh_callback)
        assert "L'archive tar.gz est vide" in mock_controller.show_info.call_args[0][0]


def test_on_create_clicked_invalid_tar(mock_controller):
    """Test _on_create_clicked avec une archive tar invalide."""
    refresh_callback = MagicMock()
    import tarfile

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.create_grub_default_backup", return_value="/path/to/backup"),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.tarfile.open", side_effect=tarfile.TarError("Invalid tar")),
    ):
        _on_create_clicked(MagicMock(), mock_controller, refresh_callback)
        assert "Archive tar.gz invalide" in mock_controller.show_info.call_args[0][0]


def test_on_restore_clicked_no_listbox(mock_controller):
    """Test _on_restore_clicked quand la listbox est introuvable."""
    list_frame = Gtk.Frame()
    _on_restore_clicked(MagicMock(), mock_controller, list_frame)
    # Ne devrait rien faire (pas de crash)


def test_on_restore_clicked_exception(mock_controller):
    """Test l'exception dans do_restore via _on_restore_clicked."""
    mock_dialog = MagicMock()
    mock_result = MagicMock()

    def mock_choose(parent, _, callback):
        callback(mock_dialog, mock_result)

    mock_dialog.choose = mock_choose
    mock_dialog.choose_finish.return_value = 1  # Confirmer

    list_frame = Gtk.Frame()
    listbox = Gtk.ListBox()
    row = Gtk.ListBoxRow()
    row.backup_path = "/path/to/backup"
    listbox.append(row)
    listbox.select_row(row)
    list_frame.set_child(listbox)

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.ui_dialogs.Gtk.AlertDialog", return_value=mock_dialog),
        patch("ui.tabs.ui_tab_backups.restore_grub_default_backup", side_effect=Exception("Restore failed")),
        patch("ui.tabs.ui_tab_backups._get_listbox_from_frame", return_value=listbox),
    ):
        # On mock selected_row car select_row ne fonctionne pas forcément en headless
        with patch.object(listbox, "get_selected_row", return_value=row):
            _on_restore_clicked(MagicMock(), mock_controller, list_frame)
            # do_restore est appelé par confirm_action
            assert "❌ Échec de la restauration" in mock_controller.show_info.call_args[0][0]


def test_on_delete_clicked_no_listbox(mock_controller):
    """Test _on_delete_clicked quand la listbox est introuvable."""
    list_frame = Gtk.Frame()
    _on_delete_clicked(MagicMock(), mock_controller, list_frame, MagicMock())
    # Ne devrait rien faire


def test_on_delete_clicked_exception(mock_controller):
    """Test l'exception dans do_delete via _on_delete_clicked."""
    mock_dialog = MagicMock()
    mock_result = MagicMock()

    def mock_choose(parent, _, callback):
        callback(mock_dialog, mock_result)

    mock_dialog.choose = mock_choose
    mock_dialog.choose_finish.return_value = 1  # Confirmer

    list_frame = Gtk.Frame()
    listbox = Gtk.ListBox()
    row = Gtk.ListBoxRow()
    row.backup_path = "/path/to/backup"
    listbox.append(row)
    list_frame.set_child(listbox)

    refresh_callback = MagicMock()

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.ui_dialogs.Gtk.AlertDialog", return_value=mock_dialog),
        patch("ui.tabs.ui_tab_backups.delete_grub_default_backup", side_effect=Exception("Delete failed")),
        patch("ui.tabs.ui_tab_backups._get_listbox_from_frame", return_value=listbox),
    ):
        with patch.object(listbox, "get_selected_row", return_value=row):
            _on_delete_clicked(MagicMock(), mock_controller, list_frame, refresh_callback)
            assert "❌ Échec de la suppression" in mock_controller.show_info.call_args[0][0]


def test_on_restore_clicked_no_selection(mock_controller):
    """Test _on_restore_clicked sans sélection."""
    list_frame = Gtk.Frame()
    listbox = Gtk.ListBox()
    list_frame.set_child(listbox)
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups._get_listbox_from_frame", return_value=listbox),
        patch.object(listbox, "get_selected_row", return_value=None),
    ):
        _on_restore_clicked(MagicMock(), mock_controller, list_frame)
        mock_controller.show_info.assert_called_with("Veuillez sélectionner une sauvegarde à restaurer.", "warning")


def test_on_delete_clicked_no_selection(mock_controller):
    """Test _on_delete_clicked sans sélection."""
    list_frame = Gtk.Frame()
    listbox = Gtk.ListBox()
    list_frame.set_child(listbox)
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups._get_listbox_from_frame", return_value=listbox),
        patch.object(listbox, "get_selected_row", return_value=None),
    ):
        _on_delete_clicked(MagicMock(), mock_controller, list_frame, MagicMock())
        mock_controller.show_info.assert_called_with("Veuillez sélectionner une sauvegarde à supprimer.", "warning")


def test_refresh_list_medium_file(mock_controller, mock_notebook):
    """Test _refresh_list avec un fichier entre 1KB et 1MB pour couvrir la ligne 265."""
    backups = ["/path/to/medium_backup.tar.gz"]
    with (
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=backups),
        patch("ui.tabs.ui_tab_backups.os.path.getmtime", return_value=1234567890),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", return_value=500 * 1024),  # 500KB
        patch("ui.tabs.ui_tab_backups.categorize_backup_type", return_value="Manuel"),
    ):
        build_backups_tab(mock_controller, mock_notebook)


def test_refresh_list_large_file(mock_controller, mock_notebook):
    """Test _refresh_list avec un fichier > 1MB pour couvrir la ligne 267."""
    backups = ["/path/to/large_backup.tar.gz"]
    with (
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=backups),
        patch("ui.tabs.ui_tab_backups.os.path.getmtime", return_value=1234567890),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", return_value=2 * 1024 * 1024),  # 2MB
        patch("ui.tabs.ui_tab_backups.categorize_backup_type", return_value="Manuel"),
    ):
        build_backups_tab(mock_controller, mock_notebook)


def test_connect_listbox_handler_no_listbox(mock_controller, mock_notebook):
    """Test _connect_listbox_handler quand il n'y a pas de listbox (couvre 360->362)."""
    with (
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
        patch("ui.tabs.ui_tab_backups.GLib.idle_add", side_effect=lambda f: f()),  # Exécuter immédiatement
    ):
        build_backups_tab(mock_controller, mock_notebook)


def test_get_listbox_from_frame_with_viewport():
    """Test _get_listbox_from_frame avec un Viewport (couvre les branches de recherche)."""
    frame = Gtk.Frame()
    viewport = Gtk.Viewport()
    listbox = Gtk.ListBox()
    viewport.set_child(listbox)
    frame.set_child(viewport)
    assert _get_listbox_from_frame(frame) == listbox


def test_on_delete_clicked_no_root(mock_controller):
    """Test _on_delete_clicked sans droits root."""
    with patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=1000):
        _on_delete_clicked(MagicMock(), mock_controller, MagicMock(), MagicMock())
        mock_controller.show_info.assert_called_with(
            "Droits administrateur requis pour supprimer une sauvegarde", "error"
        )
