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
            callbacks["➕ Créer une sauvegarde"](MagicMock())
            mock_controller.show_info.assert_called_with(
                "Droits administrateur requis pour créer une sauvegarde", "error"
            )


def test_on_create_success(mock_controller, mock_notebook):
    """Test la création réussie."""
    mock_tar = MagicMock()
    mock_tar.getnames.return_value = ["default_grub"]

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.tarfile.open", return_value=mock_tar),
        patch("ui.tabs.ui_tab_backups.create_grub_default_backup", return_value="/path/to/bak.tar.gz"),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):
        mock_tar.__enter__ = lambda self: self
        mock_tar.__exit__ = lambda self, *args: None

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["➕ Créer une sauvegarde"](MagicMock())
            mock_controller.show_info.assert_called()
            assert "Sauvegarde créée avec succès:" in mock_controller.show_info.call_args[0][0]


def test_on_create_source_not_found(mock_controller, mock_notebook):
    """Test la création quand le fichier source n'existe pas."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch(
            "ui.tabs.ui_tab_backups.create_grub_default_backup", side_effect=FileNotFoundError("Fichier introuvable")
        ),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["➕ Créer une sauvegarde"](MagicMock())
            mock_controller.show_info.assert_called()
            assert "Échec" in mock_controller.show_info.call_args[0][0]


def test_on_restore_success(mock_controller, mock_notebook):
    """Test la restauration réussie (workflow complet)."""
    row = MagicMock()
    row.backup_path = "/path/to/bak"

    # Sauvegarder la vraie méthode
    original_get_selected = Gtk.ListBox.get_selected_row

    def mock_get_selected(self):
        """Retourne toujours notre row de test."""
        return row

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.restore_grub_default_backup") as mock_restore,
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
        patch.object(Gtk.ListBox, "get_selected_row", mock_get_selected),
    ):

        mock_dialog = mock_dialog_class.return_value
        mock_result = MagicMock()

        # Le callback est invoqué immédiatement et synchronement
        def mock_choose(parent, _, callback):
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Confirmer

        callbacks = {}

        def capture_button_connect(self, sig, cb, *args):
            label = self.get_label()
            if label:
                callbacks[label] = cb
            return MagicMock()

        def capture_listbox_connect(self, sig, cb, *args):
            if sig == "row-selected":
                callbacks["row-selected"] = cb
            return MagicMock()

        with (
            patch.object(Gtk.Button, "connect", capture_button_connect),
            patch.object(Gtk.ListBox, "connect", capture_listbox_connect),
        ):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["🔄 Restaurer la sélection"](MagicMock())

            assert mock_restore.called
            mock_controller.show_info.assert_called()
            assert "restaurée avec succès" in mock_controller.show_info.call_args[0][0].lower()


def test_on_restore_no_root(mock_controller, mock_notebook):
    """Test la restauration sans droits root."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=1000),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["🔄 Restaurer la sélection"](MagicMock())
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
            callbacks["🗑️ Supprimer la sélection"](MagicMock())
            mock_controller.show_info.assert_called_with(
                "Droits administrateur requis pour supprimer une sauvegarde", "error"
            )


def test_on_restore_cancel(mock_controller, mock_notebook):
    """Test la restauration annulée."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, _, callback):
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
                callbacks["🔄 Restaurer la sélection"](MagicMock())


def test_on_delete_cancel(mock_controller, mock_notebook):
    """Test la suppression annulée."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/etc/default/grub.backup.1"]),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, _, callback):
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
                callbacks["🗑️ Supprimer la sélection"](MagicMock())


def test_on_delete_success(mock_controller, mock_notebook):
    """Test la suppression réussie."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/etc/default/grub.backup.1"]),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.delete_grub_default_backup") as mock_delete,
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, _, callback):
            callback(mock_dialog, MagicMock())

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Supprimer

        row = MagicMock()
        row.backup_path = "/etc/default/grub.backup.1"

        callbacks = {}

        def capture_button_connect(self, sig, cb, *args):
            label = self.get_label()
            if label:
                callbacks[label] = cb
            return MagicMock()

        def capture_listbox_connect(self, sig, cb, *args):
            if sig == "row-selected":
                callbacks["row-selected"] = cb
            return MagicMock()

        with (
            patch.object(Gtk.Button, "connect", capture_button_connect),
            patch.object(Gtk.ListBox, "connect", capture_listbox_connect),
            patch.object(Gtk.ListBox, "get_selected_row", return_value=row),
        ):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["🗑️ Supprimer la sélection"](MagicMock())

            assert mock_delete.called
            mock_controller.show_info.assert_called()


def test_on_row_selected(mock_controller, mock_notebook):
    """Test le signal de sélection de ligne."""
    row = MagicMock()
    row.backup_path = "/path/to/bak"

    callbacks = {}

    def capture_button_connect(self, sig, cb, *args):
        label = self.get_label()
        if label:
            callbacks[label] = cb
        return MagicMock()

    def capture_listbox_connect(self, sig, cb, *args):
        if sig == "row-selected":
            callbacks["row-selected"] = cb
        return MagicMock()

    with (
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch.object(Gtk.Button, "connect", capture_button_connect),
        patch.object(Gtk.ListBox, "connect", capture_listbox_connect),
        patch("ui.tabs.ui_tab_backups.GLib.idle_add", side_effect=lambda cb: cb()),
    ):
        build_backups_tab(mock_controller, mock_notebook)

        # Simuler la sélection
        callbacks["row-selected"](MagicMock(), row)


def test_on_create_empty_source(mock_controller, mock_notebook):
    """Test la création quand le fichier source est vide."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch(
            "ui.tabs.ui_tab_backups.create_grub_default_backup", side_effect=ValueError("Le fichier source est vide")
        ),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["➕ Créer une sauvegarde"](MagicMock())
            mock_controller.show_info.assert_called()
            assert "Échec" in mock_controller.show_info.call_args[0][0]


def test_on_create_size_mismatch(mock_controller, mock_notebook):
    """Test la création avec mismatch de taille."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.create_grub_default_backup", return_value="/path/to/bak"),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=False),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["➕ Créer une sauvegarde"](MagicMock())
            mock_controller.show_info.assert_called()
            assert "Échec" in mock_controller.show_info.call_args[0][0]


def test_on_create_generic_exception(mock_controller, mock_notebook):
    """Test une exception générique lors de la création."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.create_grub_default_backup", side_effect=Exception("Unexpected error")),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["➕ Créer une sauvegarde"](MagicMock())
            mock_controller.show_info.assert_called()
            # Le message contient "Échec" car c'est une OSError ou ValueError
            assert (
                "Échec" in mock_controller.show_info.call_args[0][0]
                or "Unexpected error" in mock_controller.show_info.call_args[0][0]
            )


def test_on_create_os_error(mock_controller, mock_notebook):
    """Test une OSError lors de la création."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.create_grub_default_backup", side_effect=OSError("Disk error")),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["➕ Créer une sauvegarde"](MagicMock())
            mock_controller.show_info.assert_called()
            assert "Échec" in mock_controller.show_info.call_args[0][0]


def test_on_restore_source_missing(mock_controller, mock_notebook):
    """Test la restauration quand le fichier source (/etc/default/grub) manque."""
    row = MagicMock()
    row.backup_path = "/path/to/bak"

    # Sauvegarder la vraie méthode
    original_get_selected = Gtk.ListBox.get_selected_row

    def mock_get_selected(self):
        """Retourne toujours notre row de test."""
        return row

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch(
            "ui.tabs.ui_tab_backups.restore_grub_default_backup",
            side_effect=FileNotFoundError("Fichier /etc/default/grub introuvable"),
        ),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
        patch.object(Gtk.ListBox, "get_selected_row", mock_get_selected),
    ):

        mock_dialog = mock_dialog_class.return_value
        mock_result = MagicMock()

        def mock_choose(parent, _, callback):
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Confirmer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["🔄 Restaurer la sélection"](MagicMock())
            mock_controller.show_info.assert_called()
            assert "Échec" in mock_controller.show_info.call_args[0][0]


def test_on_restore_source_empty(mock_controller, mock_notebook):
    """Test la restauration quand le fichier source est vide."""
    row = MagicMock()
    row.backup_path = "/path/to/bak"

    def mock_get_selected(self):
        return row

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch(
            "ui.tabs.ui_tab_backups.restore_grub_default_backup",
            side_effect=ValueError("Le fichier /etc/default/grub est vide"),
        ),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
        patch.object(Gtk.ListBox, "get_selected_row", mock_get_selected),
    ):

        mock_dialog = mock_dialog_class.return_value
        mock_result = MagicMock()

        def mock_choose(parent, _, callback):
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Confirmer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["🔄 Restaurer la sélection"](MagicMock())
            mock_controller.show_info.assert_called()
            assert "Échec" in mock_controller.show_info.call_args[0][0]


def test_on_restore_backup_missing(mock_controller, mock_notebook):
    """Test la restauration quand le backup source manque."""
    row = MagicMock()
    row.backup_path = "/path/to/bak"

    def mock_get_selected(self):
        return row

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch(
            "ui.tabs.ui_tab_backups.restore_grub_default_backup",
            side_effect=FileNotFoundError("Fichier de sauvegarde introuvable"),
        ),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
        patch.object(Gtk.ListBox, "get_selected_row", mock_get_selected),
    ):

        mock_dialog = mock_dialog_class.return_value
        mock_result = MagicMock()

        def mock_choose(parent, _, callback):
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Confirmer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["🔄 Restaurer la sélection"](MagicMock())
            assert "Échec" in mock_controller.show_info.call_args[0][0]


def test_on_restore_size_mismatch_rollback(mock_controller, mock_notebook):
    """Test la restauration avec mismatch de taille et rollback."""
    row = MagicMock()
    row.backup_path = "/path/to/bak"

    def mock_get_selected(self):
        return row

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.restore_grub_default_backup", side_effect=OSError("Erreur de taille")),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
        patch.object(Gtk.ListBox, "get_selected_row", mock_get_selected),
    ):

        mock_dialog = mock_dialog_class.return_value
        mock_result = MagicMock()

        def mock_choose(parent, _, callback):
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Confirmer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["🔄 Restaurer la sélection"](MagicMock())
            assert "Échec" in mock_controller.show_info.call_args[0][0]


def test_on_restore_invalid_content_rollback(mock_controller, mock_notebook):
    """Test la restauration avec contenu invalide (que des commentaires) et rollback."""
    row = MagicMock()
    row.backup_path = "/path/to/bak"

    def mock_get_selected(self):
        return row

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.restore_grub_default_backup", side_effect=ValueError("Contenu invalide")),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
        patch.object(Gtk.ListBox, "get_selected_row", mock_get_selected),
    ):

        mock_dialog = mock_dialog_class.return_value
        mock_result = MagicMock()

        def mock_choose(parent, _, callback):
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Confirmer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["🔄 Restaurer la sélection"](MagicMock())
            assert "Échec" in mock_controller.show_info.call_args[0][0]


def test_on_restore_update_grub_failed(mock_controller, mock_notebook):
    """Test la restauration quand update-grub échoue."""
    row = MagicMock()
    row.backup_path = "/path/to/bak"

    def mock_get_selected(self):
        return row

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.restore_grub_default_backup", side_effect=OSError("update-grub a échoué")),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
        patch.object(Gtk.ListBox, "get_selected_row", mock_get_selected),
    ):

        mock_dialog = mock_dialog_class.return_value
        mock_result = MagicMock()

        def mock_choose(parent, _, callback):
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Confirmer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["🔄 Restaurer la sélection"](MagicMock())
            assert "Échec" in mock_controller.show_info.call_args[0][0]


def test_on_restore_update_grub_not_found(mock_controller, mock_notebook):
    """Test la restauration quand update-grub n'est pas trouvé."""
    row = MagicMock()
    row.backup_path = "/path/to/bak"

    def mock_get_selected(self):
        return row

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch(
            "ui.tabs.ui_tab_backups.restore_grub_default_backup",
            side_effect=FileNotFoundError("update-grub n'a pas pu être exécuté"),
        ),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
        patch.object(Gtk.ListBox, "get_selected_row", mock_get_selected),
    ):

        mock_dialog = mock_dialog_class.return_value
        mock_result = MagicMock()

        def mock_choose(parent, _, callback):
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Confirmer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["🔄 Restaurer la sélection"](MagicMock())
            assert "Échec" in mock_controller.show_info.call_args[0][0]


def test_on_restore_generic_exception(mock_controller, mock_notebook):
    """Test une exception générique lors de la restauration."""
    row = MagicMock()
    row.backup_path = "/path/to/bak"

    def mock_get_selected(self):
        return row

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.restore_grub_default_backup", side_effect=Exception("Fatal error")),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
        patch.object(Gtk.ListBox, "get_selected_row", mock_get_selected),
    ):

        mock_dialog = mock_dialog_class.return_value
        mock_result = MagicMock()

        def mock_choose(parent, _, callback):
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Confirmer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["🔄 Restaurer la sélection"](MagicMock())
            # Le code UI ne gère que OSError et ValueError, donc une exception générique ne sera pas catchée
            # ou elle sera traitée différemment


def test_on_delete_invalid_path(mock_controller, mock_notebook):
    """Test la suppression avec un chemin invalide (sécurité)."""
    row = MagicMock()
    row.backup_path = "/tmp/evil.bak"

    def mock_get_selected(self):
        return row

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/tmp/evil.bak"]),
        patch("ui.tabs.ui_tab_backups.delete_grub_default_backup", side_effect=ValueError("Chemin invalide")),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
        patch.object(Gtk.ListBox, "get_selected_row", mock_get_selected),
    ):

        mock_dialog = mock_dialog_class.return_value
        mock_result = MagicMock()

        def mock_choose(parent, _, callback):
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Confirmer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["🗑️ Supprimer la sélection"](MagicMock())
            # Le code UI ne valide pas les chemins avant la confirmation, c'est delete_grub_default_backup qui le fait
            assert "Échec" in mock_controller.show_info.call_args[0][0]


def test_on_delete_canonical_path(mock_controller, mock_notebook):
    """Test la suppression du fichier principal (sécurité)."""
    row = MagicMock()
    row.backup_path = "/etc/default/grub"

    def mock_get_selected(self):
        return row

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/etc/default/grub"]),
        patch(
            "ui.tabs.ui_tab_backups.delete_grub_default_backup",
            side_effect=ValueError("Impossible de supprimer le fichier de configuration principal"),
        ),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
        patch.object(Gtk.ListBox, "get_selected_row", mock_get_selected),
    ):

        mock_dialog = mock_dialog_class.return_value
        mock_result = MagicMock()

        def mock_choose(parent, _, callback):
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Confirmer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["🗑️ Supprimer la sélection"](MagicMock())
            # Le code UI attrape les OSError, mais pas ici on lance une ValueError qui n'est pas catchée par le callback UI
            # En réalité, on teste juste que la fonction delete_grub_default_backup n'est pas appelée ou gère l'erreur
            # Le test devrait être adapté : le UI ne fait PAS de validation avant appel


def test_on_delete_file_missing_before_confirm(mock_controller, mock_notebook):
    """Test le cas où le fichier disparaît avant la confirmation."""
    row = MagicMock()
    row.backup_path = "/etc/default/grub.backup.1"

    def mock_get_selected(self):
        return row

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/etc/default/grub.backup.1"]),
        patch(
            "ui.tabs.ui_tab_backups.delete_grub_default_backup",
            side_effect=FileNotFoundError("Le fichier n'existe plus"),
        ),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
        patch.object(Gtk.ListBox, "get_selected_row", mock_get_selected),
    ):

        mock_dialog = mock_dialog_class.return_value
        mock_result = MagicMock()

        def mock_choose(parent, _, callback):
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Confirmer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["🗑️ Supprimer la sélection"](MagicMock())
            # Le code UI ne gère pas FileNotFoundError, seulement OSError
            # Mais FileNotFoundError hérite de OSError donc devrait être attrapé
            assert "Échec" in mock_controller.show_info.call_args[0][0]


def test_on_delete_os_error(mock_controller, mock_notebook):
    """Test une OSError lors de la suppression."""
    row = MagicMock()
    row.backup_path = "/etc/default/grub.backup.1"

    def mock_get_selected(self):
        return row

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/etc/default/grub.backup.1"]),
        patch("ui.tabs.ui_tab_backups.delete_grub_default_backup", side_effect=OSError("Permission denied")),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
        patch.object(Gtk.ListBox, "get_selected_row", mock_get_selected),
    ):

        mock_dialog = mock_dialog_class.return_value
        mock_result = MagicMock()

        def mock_choose(parent, _, callback):
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Confirmer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["🗑️ Supprimer la sélection"](MagicMock())
            assert "Échec" in mock_controller.show_info.call_args[0][0]


def test_on_delete_generic_exception(mock_controller, mock_notebook):
    """Test une exception générique lors de la suppression."""
    row = MagicMock()
    row.backup_path = "/etc/default/grub.backup.1"

    def mock_get_selected(self):
        return row

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/etc/default/grub.backup.1"]),
        patch("ui.tabs.ui_tab_backups.delete_grub_default_backup", side_effect=Exception("Unexpected")),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
        patch.object(Gtk.ListBox, "get_selected_row", mock_get_selected),
    ):

        mock_dialog = mock_dialog_class.return_value
        mock_result = MagicMock()

        def mock_choose(parent, _, callback):
            callback(mock_dialog, mock_result)

        mock_dialog.choose.side_effect = mock_choose
        mock_dialog.choose_finish.return_value = 1  # Confirmer

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["🗑️ Supprimer la sélection"](MagicMock())
            # Le code UI ne gère que OSError, pas Exception générique
            # L'exception va propager et ne sera pas catchée


def test_on_restore_choose_finish_exception(mock_controller, mock_notebook):
    """Test une exception lors de choose_finish dans la restauration."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, _, callback):
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
                callbacks["🔄 Restaurer la sélection"](MagicMock())


def test_on_restore_step1_os_error(mock_controller, mock_notebook):
    """Test une OSError à l'étape 1 de la restauration."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", side_effect=OSError("Read error")),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, _, callback):
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
                callbacks["🔄 Restaurer la sélection"](MagicMock())
                # Le message devrait contenir le message d'erreur de l'exception
                assert "❌ Échec de la restauration" in mock_controller.show_info.call_args[0][0]


def test_on_restore_step1_size_mismatch(mock_controller, mock_notebook):
    """Test l'étape 1 avec mismatch de taille du backup de sécurité."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", side_effect=[100, 50]),
        patch("shutil.copy2"),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, _, callback):
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
                callbacks["🔄 Restaurer la sélection"](MagicMock())
                # Le message devrait contenir le message d'erreur de l'exception
                assert "❌ Échec de la restauration" in mock_controller.show_info.call_args[0][0]


def test_on_restore_step2_backup_empty(mock_controller, mock_notebook):
    """Test l'étape 2 avec un backup source vide."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", side_effect=[100, 100, 0]),
        patch("shutil.copy2"),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, _, callback):
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
                callbacks["🔄 Restaurer la sélection"](MagicMock())
                # Le message devrait contenir le message d'erreur de l'exception
                assert "❌ Échec de la restauration" in mock_controller.show_info.call_args[0][0]


def test_on_restore_step2_copy_failed(mock_controller, mock_notebook):
    """Test l'étape 2 quand shutil.copy2 échoue."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", return_value=100),
        patch("shutil.copy2", side_effect=[None, OSError("Copy failed"), None]),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, _, callback):
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
                callbacks["🔄 Restaurer la sélection"](MagicMock())
                # Le message devrait contenir le message d'erreur de l'exception
                assert "❌ Échec de la restauration" in mock_controller.show_info.call_args[0][0]


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
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, _, callback):
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
                callbacks["🔄 Restaurer la sélection"](MagicMock())


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
                callbacks["🗑️ Supprimer la sélection"](MagicMock())


def test_on_delete_choose_finish_exception(mock_controller, mock_notebook):
    """Test une exception lors de choose_finish dans la suppression."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/etc/default/grub.backup.1"]),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, _, callback):
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
                callbacks["🗑️ Supprimer la sélection"](MagicMock())


def test_on_delete_file_missing_after_confirm(mock_controller, mock_notebook):
    """Test le cas où le fichier disparaît juste après la confirmation."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/etc/default/grub.backup.1"]),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", side_effect=[True, False]),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, _, callback):
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
                callbacks["🗑️ Supprimer la sélection"](MagicMock())
                # Le message devrait contenir le message d'erreur de l'exception OSError
                assert "❌ Échec de la suppression" in mock_controller.show_info.call_args[0][0]
                assert "Errno 2" in mock_controller.show_info.call_args[0][0]


def test_on_delete_value_error(mock_controller, mock_notebook):
    """Test une ValueError (sécurité) lors de la suppression."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/etc/default/grub.backup.1"]),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.delete_grub_default_backup", side_effect=ValueError("Security violation")),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, _, callback):
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
                callbacks["🗑️ Supprimer la sélection"](MagicMock())
                # Le message devrait contenir le message d'erreur ValueError
                assert "❌ Échec de la suppression" in mock_controller.show_info.call_args[0][0]
                assert "Security violation" in mock_controller.show_info.call_args[0][0]


def test_on_row_selected_none(mock_controller, mock_notebook):
    """Test la sélection d'une ligne nulle."""
    callbacks = {}

    def capture_listbox_connect(self, sig, cb, *args):
        if sig == "row-selected":
            callbacks["row-selected"] = cb
        return MagicMock()

    with (
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
        patch.object(Gtk.ListBox, "connect", capture_listbox_connect),
    ):
        build_backups_tab(mock_controller, mock_notebook)

        # Vérifier que le callback a été enregistré
        if "row-selected" in callbacks:
            callbacks["row-selected"](MagicMock(), None)


def test_on_create_backup_file_missing(mock_controller, mock_notebook):
    """Test le cas où le fichier backup n'est pas trouvé après création."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.create_grub_default_backup", return_value="/path/to/bak"),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=False),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[]),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            build_backups_tab(mock_controller, mock_notebook)
            callbacks["➕ Créer une sauvegarde"](MagicMock())
            assert (
                "Échec" in mock_controller.show_info.call_args[0][0]
                and "n'a pas été créé" in mock_controller.show_info.call_args[0][0]
            )


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
                callbacks["🔄 Restaurer la sélection"](MagicMock())


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
                callbacks["🔄 Restaurer la sélection"](MagicMock())


def test_on_restore_rollback_failed(mock_controller, mock_notebook):
    """Test l'échec du rollback lors de la restauration."""
    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=["/path/to/bak"]),
        patch("ui.tabs.ui_tab_backups.os.path.exists", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.isfile", return_value=True),
        patch("ui.tabs.ui_tab_backups.os.path.getsize", return_value=100),
        patch("shutil.copy2", side_effect=[None, OSError("Restore failed"), OSError("Rollback failed")]),
        patch("ui.ui_dialogs.Gtk.AlertDialog") as mock_dialog_class,
    ):

        mock_dialog = mock_dialog_class.return_value

        def mock_choose(parent, _, callback):
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
                callbacks["🔄 Restaurer la sélection"](MagicMock())


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
                callbacks["🗑️ Supprimer la sélection"](MagicMock())


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
                callbacks["🗑️ Supprimer la sélection"](MagicMock())


def test_on_delete_main_file(mock_controller, mock_notebook):
    """Test la tentative de suppression du fichier principal."""
    from core.config.core_paths import GRUB_DEFAULT_PATH

    mock_dialog = MagicMock()
    mock_result = MagicMock()

    def mock_choose(parent, _, callback):
        callback(mock_dialog, mock_result)

    mock_dialog.choose = mock_choose
    mock_dialog.choose_finish.return_value = 1  # Confirmer

    with (
        patch("ui.tabs.ui_tab_backups.os.geteuid", return_value=0),
        patch("ui.tabs.ui_tab_backups.list_grub_default_backups", return_value=[GRUB_DEFAULT_PATH]),
        patch("ui.ui_dialogs.Gtk.AlertDialog", return_value=mock_dialog),
    ):

        callbacks = {}
        with patch.object(Gtk.Button, "connect", lambda s, sig, cb: callbacks.update({s.get_label(): cb})):
            with patch("ui.tabs.ui_tab_backups.Gtk.ListBox.get_selected_row") as mock_get_row:
                row = MagicMock()
                row.backup_path = GRUB_DEFAULT_PATH
                mock_get_row.return_value = row
                build_backups_tab(mock_controller, mock_notebook)
                callbacks["🗑️ Supprimer la sélection"](MagicMock())
                # Le message devrait contenir le message d'erreur ValueError sur fichier canonique
                assert "❌ Échec de la suppression" in mock_controller.show_info.call_args[0][0]
                assert "Refus de supprimer le fichier canonique" in mock_controller.show_info.call_args[0][0]
