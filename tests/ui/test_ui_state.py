"""Tests pour le gestionnaire d'état de l'UI."""

from unittest.mock import MagicMock, patch

import pytest

from ui.ui_state import AppState, AppStateManager


class TestAppStateManager:
    """Tests pour la classe AppStateManager."""

    @pytest.fixture
    def manager(self):
        """Fixture pour un AppStateManager avec mocks."""
        with patch("ui.ui_state.load_hidden_entry_ids", return_value={"entry1"}):
            with patch("ui.ui_state.ActiveThemeManager"):
                return AppStateManager()

    def test_init(self, manager):
        """Test l'initialisation."""
        assert manager.state == AppState.CLEAN
        assert manager.modified is False
        assert manager.is_loading() is False
        assert manager.hidden_entry_ids == {"entry1"}
        assert manager.entries_visibility_dirty is False

    def test_set_loading(self, manager):
        """Test le flag de chargement."""
        manager.set_loading(True)
        assert manager.is_loading() is True
        manager.set_loading(False)
        assert manager.is_loading() is False

    def test_apply_state_clean(self, manager):
        """Test la transition vers l'état CLEAN."""
        save_btn = MagicMock()
        reload_btn = MagicMock()

        with patch("os.geteuid", return_value=0):
            manager.apply_state(AppState.CLEAN, save_btn, reload_btn)

            assert manager.state == AppState.CLEAN
            assert manager.modified is False
            save_btn.set_sensitive.assert_called_with(False)
            reload_btn.set_sensitive.assert_called_with(True)

    def test_apply_state_dirty(self, manager):
        """Test la transition vers l'état DIRTY."""
        save_btn = MagicMock()
        reload_btn = MagicMock()

        with patch("os.geteuid", return_value=0):
            manager.apply_state(AppState.DIRTY, save_btn, reload_btn)

            assert manager.state == AppState.DIRTY
            assert manager.modified is True
            save_btn.set_sensitive.assert_called_with(True)
            reload_btn.set_sensitive.assert_called_with(True)

    def test_apply_state_applying(self, manager):
        """Test la transition vers l'état APPLYING."""
        save_btn = MagicMock()
        reload_btn = MagicMock()

        with patch("os.geteuid", return_value=0):
            manager.apply_state(AppState.APPLYING, save_btn, reload_btn)

            assert manager.state == AppState.APPLYING
            save_btn.set_sensitive.assert_called_with(False)
            reload_btn.set_sensitive.assert_called_with(False)

    def test_apply_state_no_root(self, manager):
        """Test quand l'utilisateur n'est pas root."""
        save_btn = MagicMock()
        reload_btn = MagicMock()

        with patch("os.geteuid", return_value=1000):
            manager.apply_state(AppState.DIRTY, save_btn, reload_btn)

            # Même si DIRTY, save_btn doit être désactivé car pas root
            save_btn.set_sensitive.assert_called_with(False)

    def test_apply_state_visibility_dirty(self, manager):
        """Test quand seule la visibilité des entrées est modifiée."""
        save_btn = MagicMock()
        reload_btn = MagicMock()
        manager.entries_visibility_dirty = True

        with patch("os.geteuid", return_value=0):
            manager.apply_state(AppState.CLEAN, save_btn, reload_btn)

            # Doit pouvoir sauvegarder car visibility_dirty est True
            save_btn.set_sensitive.assert_called_with(True)

    def test_mark_dirty(self, manager):
        """Test mark_dirty."""
        save_btn = MagicMock()
        reload_btn = MagicMock()

        with patch("os.geteuid", return_value=0):
            manager.mark_dirty(save_btn, reload_btn)
            assert manager.state == AppState.DIRTY

    def test_mark_dirty_while_applying(self, manager):
        """Test que mark_dirty ne fait rien si on est déjà en train d'appliquer."""
        save_btn = MagicMock()
        reload_btn = MagicMock()
        manager.state = AppState.APPLYING

        manager.mark_dirty(save_btn, reload_btn)
        assert manager.state == AppState.APPLYING  # Inchangé

    def test_update_state_data(self, manager):
        """Test update_state_data."""
        new_data = MagicMock()
        manager.update_state_data(new_data)
        assert manager.state_data == new_data

    def test_update_default_choice_ids(self, manager):
        """Test update_default_choice_ids."""
        ids = ["0", "1", "saved"]
        manager.update_default_choice_ids(ids)
        assert manager.get_default_choice_ids() == ids
