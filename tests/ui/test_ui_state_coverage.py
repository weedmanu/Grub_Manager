
from unittest.mock import MagicMock, patch

import pytest

from ui.ui_state import AppState, AppStateManager


@pytest.fixture
def state_manager():
    with patch("ui.ui_state.load_hidden_entry_ids", return_value=set()), \
         patch("ui.ui_state.ActiveThemeManager"):
        return AppStateManager()

def test_app_state_manager_init(state_manager):
    assert state_manager.state == AppState.CLEAN
    assert state_manager.modified is False
    assert state_manager.is_loading() is False
    assert state_manager.get_default_choice_ids() == ["saved"]

def test_apply_state_clean(state_manager):
    save_btn = MagicMock()
    reload_btn = MagicMock()

    with patch("os.geteuid", return_value=0):
        state_manager.apply_state(AppState.CLEAN, save_btn, reload_btn)
        assert state_manager.state == AppState.CLEAN
        assert state_manager.modified is False
        save_btn.set_sensitive.assert_called_with(False)
        reload_btn.set_sensitive.assert_called_with(True)

def test_apply_state_dirty_root(state_manager):
    save_btn = MagicMock()
    reload_btn = MagicMock()

    with patch("os.geteuid", return_value=0):
        state_manager.apply_state(AppState.DIRTY, save_btn, reload_btn)
        assert state_manager.state == AppState.DIRTY
        assert state_manager.modified is True
        save_btn.set_sensitive.assert_called_with(True)
        reload_btn.set_sensitive.assert_called_with(True)

def test_apply_state_dirty_no_root(state_manager):
    save_btn = MagicMock()
    reload_btn = MagicMock()

    with patch("os.geteuid", return_value=1000):
        state_manager.apply_state(AppState.DIRTY, save_btn, reload_btn)
        save_btn.set_sensitive.assert_called_with(False)

def test_apply_state_applying(state_manager):
    save_btn = MagicMock()
    reload_btn = MagicMock()

    with patch("os.geteuid", return_value=0):
        state_manager.apply_state(AppState.APPLYING, save_btn, reload_btn)
        assert state_manager.state == AppState.APPLYING
        save_btn.set_sensitive.assert_called_with(False)
        reload_btn.set_sensitive.assert_called_with(False)

def test_apply_state_visibility_dirty(state_manager):
    save_btn = MagicMock()
    reload_btn = MagicMock()
    state_manager.entries_visibility_dirty = True

    with patch("os.geteuid", return_value=0):
        state_manager.apply_state(AppState.CLEAN, save_btn, reload_btn)
        save_btn.set_sensitive.assert_called_with(True)

def test_mark_dirty(state_manager):
    save_btn = MagicMock()
    reload_btn = MagicMock()

    with patch("os.geteuid", return_value=0):
        state_manager.mark_dirty(save_btn, reload_btn)
        assert state_manager.state == AppState.DIRTY

        # If already applying, should not mark dirty
        state_manager.state = AppState.APPLYING
        state_manager.mark_dirty(save_btn, reload_btn)
        assert state_manager.state == AppState.APPLYING

def test_loading_flag(state_manager):
    state_manager.set_loading(True)
    assert state_manager.is_loading() is True
    state_manager.set_loading(False)
    assert state_manager.is_loading() is False


def test_is_dirty_false(state_manager):
    state_manager.modified = False
    state_manager.entries_visibility_dirty = False
    assert state_manager.is_dirty() is False


def test_is_dirty_true_modified(state_manager):
    state_manager.modified = True
    state_manager.entries_visibility_dirty = False
    assert state_manager.is_dirty() is True


def test_is_dirty_true_visibility(state_manager):
    state_manager.modified = False
    state_manager.entries_visibility_dirty = True
    assert state_manager.is_dirty() is True

def test_update_state_data(state_manager):
    mock_data = MagicMock()
    state_manager.update_state_data(mock_data)
    assert state_manager.state_data == mock_data

def test_update_default_choice_ids(state_manager):
    ids = ["a", "b"]
    state_manager.update_default_choice_ids(ids)
    assert state_manager.get_default_choice_ids() == ids
