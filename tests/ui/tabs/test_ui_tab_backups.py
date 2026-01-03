"""Tests pour l'onglet Sauvegardes."""

from unittest.mock import MagicMock, mock_open, patch

import gi
import pytest

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ui.tabs.ui_tab_backups import build_backups_tab


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.get_height.return_value = 600
    return controller


@pytest.fixture
def mock_notebook():
    return MagicMock(spec=Gtk.Notebook)


def test_build_backups_tab(mock_controller, mock_notebook):
    """Test la construction de l'onglet sauvegardes."""
    with patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]):
        build_backups_tab(mock_controller, mock_notebook)
        assert mock_notebook.append_page.called


def test_refresh_with_data(mock_controller, mock_notebook):
    """Test le rafraîchissement avec des données."""
    backups = ["/boot/grub/grub.default.bak.1"]
    with (
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=backups),
        patch("ui.tabs.ui_tab_backups.os.path.getmtime", return_value=1234567890),
        patch("ui.tabs.ui_tab_backups.categorize_backup_type", return_value="Manuel"),
    ):
        build_backups_tab(mock_controller, mock_notebook)


def test_refresh_error(mock_controller, mock_notebook):
    """Test le rafraîchissement avec erreur."""
    with patch("ui.tabs.ui_tab_backups.list_grub_default_backups", side_effect=OSError("Error")):
        build_backups_tab(mock_controller, mock_notebook)
        mock_controller.show_info.assert_called()


def test_on_create_no_root(mock_controller, mock_notebook):
    """Test la création sans droits root."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=1000),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["Créer une sauvegarde"](MagicMock())
            mock_controller.show_info.assert_called_with(
                "Droits administrateur requis pour créer une sauvegarde", "error"
            )


def test_on_create_success(mock_controller, mock_notebook):
    """Test la création réussie."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", return_value=100),
        patch("ui.tabs.ui_tab_backups.create_grub_default_backup", return_value="/path/to/bak"),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["Créer une sauvegarde"](MagicMock())
            mock_controller.show_info.assert_called()
            assert "Sauvegarde créée:" in mock_controller.show_info.call_args[0][0]


def test_on_create_source_not_found(mock_controller, mock_notebook):
    """Test la création quand le fichier source n'existe pas."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=False),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["Créer une sauvegarde"](MagicMock())
            mock_controller.show_info.assert_called()
            assert "introuvable" in mock_controller.show_info.call_args[0][0]


def test_on_restore_success(mock_controller, mock_notebook):
    """Test la restauration réussie (workflow complet)."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", return_value=100),
        patch("shutil.copy2") as mock_copy,
        patch("shutil.which", return_value="/usr/sbin/update-grub"),
        patch("subprocess.run") as mock_run,
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
        patch("builtins.open", mock_open(read_data="GRUB_DEFAULT=0\n")),
    ):

        mock_run.return_value = MagicMock(returncode=0)
        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Restaurer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/path/to/bak"
                mock_get_row.return_value = row

                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Restaurer"](MagicMock())

                assert mock_copy.called
                assert mock_run.called
                mock_controller.show_info.assert_called_with(
                    "✓ Restauration réussie ! Le système GRUB a été regénéré.", "info"
                )


def test_on_restore_no_root(mock_controller, mock_notebook):
    """Test la restauration sans droits root."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=1000),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["Restaurer"](MagicMock())
            mock_controller.show_info.assert_called_with(
                "Droits administrateur requis pour restaurer une sauvegarde", "error"
            )


def test_on_delete_no_root(mock_controller, mock_notebook):
    """Test la suppression sans droits root."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=1000),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["Supprimer"](MagicMock())
            mock_controller.show_info.assert_called_with(
                "Droits administrateur requis pour supprimer une sauvegarde", "error"
            )


def test_on_restore_cancel(mock_controller, mock_notebook):
    """Test la restauration annulée."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 0  # Annuler

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/path/to/bak"
                mock_get_row.return_value = row

                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Restaurer"](MagicMock())


def test_on_delete_cancel(mock_controller, mock_notebook):
    """Test la suppression annulée."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/etc/default/grub.backup.1"]),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 0  # Annuler

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/etc/default/grub.backup.1"
                mock_get_row.return_value = row

                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Supprimer"](MagicMock())


def test_on_delete_success(mock_controller, mock_notebook):
    """Test la suppression réussie."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/etc/default/grub.backup.1"]),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.delete_grub_default_backup") as mock_delete,
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Supprimer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/etc/default/grub.backup.1"
                mock_get_row.return_value = row

                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Supprimer"](MagicMock())

                assert mock_delete.called
                mock_controller.show_info.assert_called()


def test_on_row_selected(mock_controller, mock_notebook):
    """Test le signal de sélection de ligne."""
    with patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]):
        callbacks = {}
        with patch.object(Gtk.ListBox, "connect", lambda s, sig, cb: callbacks.update({"row-selected": cb})):
            build_backups_tab(mock_controller, mock_notebook)

            row = MagicMock()
            row.backup_path = "/path/to/bak"
            callbacks["row-selected"](MagicMock(), row)


def test_on_create_empty_source(mock_controller, mock_notebook):
    """Test la création quand le fichier source est vide."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["Créer une sauvegarde"](MagicMock())
            mock_controller.show_info.assert_called()
            assert "est vide" in mock_controller.show_info.call_args[0][0]


def test_on_create_size_mismatch(mock_controller, mock_notebook):
    """Test la création avec mismatch de taille."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", side_effect=[100, 50]),
        patch("ui.tabs.ui_tab_backups.create_grub_default_backup", return_value="/path/to/bak"),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["Créer une sauvegarde"](MagicMock())
            mock_controller.show_info.assert_called()
            assert "incomplet" in mock_controller.show_info.call_args[0][0]


def test_on_create_generic_exception(mock_controller, mock_notebook):
    """Test une exception générique lors de la création."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", side_effect=Exception("Unexpected error")),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["Créer une sauvegarde"](MagicMock())
            mock_controller.show_info.assert_called()
            assert "Erreur inattendue" in mock_controller.show_info.call_args[0][0]


def test_on_create_os_error(mock_controller, mock_notebook):
    """Test une OSError lors de la création."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", side_effect=OSError("Disk error")),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["Créer une sauvegarde"](MagicMock())
            mock_controller.show_info.assert_called()
            assert "Erreur lors de la création" in mock_controller.show_info.call_args[0][0]


def test_on_restore_source_missing(mock_controller, mock_notebook):
    """Test la restauration quand le fichier source (/etc/default/grub) manque."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=False),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Restaurer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/path/to/bak"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Restaurer"](MagicMock())
                mock_controller.show_info.assert_called_with("Erreur: Fichier /etc/default/grub introuvable", "error")


def test_on_restore_source_empty(mock_controller, mock_notebook):
    """Test la restauration quand le fichier source est vide."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", return_value=0),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Restaurer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/path/to/bak"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Restaurer"](MagicMock())
                mock_controller.show_info.assert_called_with("Erreur: Le fichier /etc/default/grub est vide", "error")


def test_on_restore_backup_missing(mock_controller, mock_notebook):
    """Test la restauration quand le backup source manque."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", return_value=100),
        patch("shutil.copy2"),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=False),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Restaurer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/path/to/bak"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Restaurer"](MagicMock())
                assert "Fichier de sauvegarde introuvable" in mock_controller.show_info.call_args[0][0]


def test_on_restore_size_mismatch_rollback(mock_controller, mock_notebook):
    """Test la restauration avec mismatch de taille et rollback."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", side_effect=[100, 100, 100, 50]),
        patch("shutil.copy2") as mock_copy,
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Restaurer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/path/to/bak"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Restaurer"](MagicMock())
                assert mock_copy.call_count >= 2  # Copy to safety, copy to restore, copy for rollback
                assert "rollback effectué" in mock_controller.show_info.call_args[0][0]


def test_on_restore_invalid_content_rollback(mock_controller, mock_notebook):
    """Test la restauration avec contenu invalide (que des commentaires) et rollback."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", return_value=100),
        patch("shutil.copy2") as mock_copy,
        patch("builtins.open", mock_open(read_data="# Only comments\n# No config\n")),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Restaurer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/path/to/bak"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Restaurer"](MagicMock())
                assert "rollback effectué" in mock_controller.show_info.call_args[0][0]


def test_on_restore_update_grub_failed(mock_controller, mock_notebook):
    """Test la restauration quand update-grub échoue."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", return_value=100),
        patch("shutil.copy2"),
        patch("shutil.which", return_value="/usr/sbin/update-grub"),
        patch("subprocess.run") as mock_run,
        patch("builtins.open", mock_open(read_data="GRUB_DEFAULT=0\n")),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_run.return_value = MagicMock(returncode=1, stderr="Error updating grub")
        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Restaurer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/path/to/bak"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Restaurer"](MagicMock())
                assert "update-grub a échoué" in mock_controller.show_info.call_args[0][0]


def test_on_restore_update_grub_not_found(mock_controller, mock_notebook):
    """Test la restauration quand update-grub n'est pas trouvé."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", return_value=100),
        patch("shutil.copy2"),
        patch("shutil.which", return_value=None),
        patch("builtins.open", mock_open(read_data="GRUB_DEFAULT=0\n")),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Restaurer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/path/to/bak"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Restaurer"](MagicMock())
                assert "n'a pas pu être exécuté" in mock_controller.show_info.call_args[0][0]


def test_on_restore_generic_exception(mock_controller, mock_notebook):
    """Test une exception générique lors de la restauration."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", side_effect=Exception("Fatal error")),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Restaurer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/path/to/bak"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Restaurer"](MagicMock())
                assert "Erreur critique" in mock_controller.show_info.call_args[0][0]


def test_on_delete_invalid_path(mock_controller, mock_notebook):
    """Test la suppression avec un chemin invalide (sécurité)."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/tmp/evil.bak"]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/tmp/evil.bak"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Supprimer"](MagicMock())
                assert "Chemin invalide" in mock_controller.show_info.call_args[0][0]


def test_on_delete_canonical_path(mock_controller, mock_notebook):
    """Test la suppression du fichier principal (sécurité)."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/etc/default/grub"]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/etc/default/grub"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Supprimer"](MagicMock())
                assert (
                    "Impossible de supprimer le fichier de configuration principal"
                    in mock_controller.show_info.call_args[0][0]
                )


def test_on_delete_file_missing_before_confirm(mock_controller, mock_notebook):
    """Test le cas où le fichier disparaît avant la confirmation."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/etc/default/grub.backup.1"]),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=False),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/etc/default/grub.backup.1"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Supprimer"](MagicMock())
                assert "n'existe plus" in mock_controller.show_info.call_args[0][0]


def test_on_delete_os_error(mock_controller, mock_notebook):
    """Test une OSError lors de la suppression."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/etc/default/grub.backup.1"]),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.delete_grub_default_backup", side_effect=OSError("Permission denied")),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Supprimer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/etc/default/grub.backup.1"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Supprimer"](MagicMock())
                assert "Erreur lors de la suppression" in mock_controller.show_info.call_args[0][0]


def test_on_delete_generic_exception(mock_controller, mock_notebook):
    """Test une exception générique lors de la suppression."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/etc/default/grub.backup.1"]),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.delete_grub_default_backup", side_effect=Exception("Unexpected")),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Supprimer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/etc/default/grub.backup.1"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Supprimer"](MagicMock())
                assert "Erreur inattendue" in mock_controller.show_info.call_args[0][0]


def test_on_restore_choose_finish_exception(mock_controller, mock_notebook):
    """Test une exception lors de choose_finish dans la restauration."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.side_effect = Exception("Dialog error")

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/path/to/bak"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Restaurer"](MagicMock())


def test_on_restore_step1_os_error(mock_controller, mock_notebook):
    """Test une OSError à l'étape 1 de la restauration."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", side_effect=OSError("Read error")),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/path/to/bak"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Restaurer"](MagicMock())
                assert "Erreur lors du backup de sécurité" in mock_controller.show_info.call_args[0][0]


def test_on_restore_step1_size_mismatch(mock_controller, mock_notebook):
    """Test l'étape 1 avec mismatch de taille du backup de sécurité."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", side_effect=[100, 50]),
        patch("shutil.copy2"),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/path/to/bak"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Restaurer"](MagicMock())
                assert "fichier incomplet" in mock_controller.show_info.call_args[0][0]


def test_on_restore_step2_backup_empty(mock_controller, mock_notebook):
    """Test l'étape 2 avec un backup source vide."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", side_effect=[100, 100, 0]),
        patch("shutil.copy2"),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/path/to/bak"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Restaurer"](MagicMock())
                assert "Le backup est vide ou corrompu" in mock_controller.show_info.call_args[0][0]


def test_on_restore_step2_copy_failed(mock_controller, mock_notebook):
    """Test l'étape 2 quand shutil.copy2 échoue."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", return_value=100),
        patch("shutil.copy2", side_effect=[None, OSError("Copy failed"), None]),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/path/to/bak"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Restaurer"](MagicMock())
                assert "Erreur lors de la restauration" in mock_controller.show_info.call_args[0][0]


def test_on_restore_step2_validation_os_error(mock_controller, mock_notebook):
    """Test l'étape 2 quand la validation du contenu échoue par OSError."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", return_value=100),
        patch("shutil.copy2"),
        patch("builtins.open", side_effect=OSError("Read error")),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/path/to/bak"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Restaurer"](MagicMock())


def test_on_delete_no_path_property(mock_controller, mock_notebook):
    """Test la suppression quand la propriété backup_path est manquante."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock(spec=Gtk.ListBoxRow)
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Supprimer"](MagicMock())


def test_on_delete_choose_finish_exception(mock_controller, mock_notebook):
    """Test une exception lors de choose_finish dans la suppression."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/etc/default/grub.backup.1"]),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.side_effect = Exception("Dialog error")

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/etc/default/grub.backup.1"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Supprimer"](MagicMock())


def test_on_delete_file_missing_after_confirm(mock_controller, mock_notebook):
    """Test le cas où le fichier disparaît juste après la confirmation."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/etc/default/grub.backup.1"]),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", side_effect=[True, False]),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/etc/default/grub.backup.1"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Supprimer"](MagicMock())
                assert "Le fichier a disparu" in mock_controller.show_info.call_args[0][0]


def test_on_delete_value_error(mock_controller, mock_notebook):
    """Test une ValueError (sécurité) lors de la suppression."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/etc/default/grub.backup.1"]),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.delete_grub_default_backup", side_effect=ValueError("Security violation")),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/etc/default/grub.backup.1"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Supprimer"](MagicMock())
                assert "Erreur sécurité" in mock_controller.show_info.call_args[0][0]


def test_on_row_selected_none(mock_controller, mock_notebook):
    """Test la sélection d'une ligne nulle."""
    with patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]):
        callbacks = {}
        with patch.object(Gtk.ListBox, "connect", lambda s, sig, cb: callbacks.update({"row-selected": cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["row-selected"](MagicMock(), None)


def test_on_create_backup_file_missing(mock_controller, mock_notebook):
    """Test le cas où le fichier backup n'est pas trouvé après création."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", side_effect=[True, False]),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", return_value=100),
        patch("ui.tabs.ui_tab_backups.create_grub_default_backup", return_value="/path/to/bak"),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["Créer une sauvegarde"](MagicMock())
            assert "n'a pas pu être créé" in mock_controller.show_info.call_args[0][0]


def test_on_restore_no_selection(mock_controller, mock_notebook):
    """Test la restauration sans sélection."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row", return_value=None):
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Restaurer"](MagicMock())


def test_on_restore_no_path(mock_controller, mock_notebook):
    """Test la restauration avec une ligne sans chemin."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = None
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Restaurer"](MagicMock())


def test_on_restore_rollback_failed(mock_controller, mock_notebook):
    """Test l'échec du rollback lors de la restauration."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", return_value=100),
        patch("shutil.copy2", side_effect=[None, OSError("Restore failed"), OSError("Rollback failed")]),
        patch("ui.tabs.ui_tab_backups.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, cancellable, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = "/path/to/bak"
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Restaurer"](MagicMock())


def test_on_delete_no_selection(mock_controller, mock_notebook):
    """Test la suppression sans sélection."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row", return_value=None):
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Supprimer"](MagicMock())


def test_on_delete_no_path(mock_controller, mock_notebook):
    """Test la suppression avec une ligne sans chemin."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = None
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Supprimer"](MagicMock())


def test_on_delete_main_file(mock_controller, mock_notebook):
    """Test la tentative de suppression du fichier principal."""
    from core.config.core_paths import GRUB_DEFAULT_PATH

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[GRUB_DEFAULT_PATH]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = GRUB_DEFAULT_PATH
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["Supprimer"](MagicMock())
                assert (
                    "Impossible de supprimer le fichier de configuration principal"
                    in mock_controller.show_info.call_args[0][0]
                )
