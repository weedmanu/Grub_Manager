from unittest.mock import MagicMock

import gi
import pytest

gi.require_version("Gtk", "4.0")
from gi.repository import GObject, Gtk

from core.system.core_grub_system_commands import GrubDefaultChoice
from ui.ui_manager import GrubConfigManager
from ui.ui_state import AppStateManager


# Mock Gtk.StringList for testing dropdown models
class MockStringList(GObject.Object):
    def __init__(self, items=None):
        super().__init__()
        self.items = items or []

    def get_n_items(self):
        return len(self.items)

    def get_string(self, index):
        if 0 <= index < len(self.items):
            return self.items[index]
        return None

    def splice(self, position, n_removals, additions):
        # Simulate splice behavior
        self.items[position : position + n_removals] = additions

    def append(self, item):
        self.items.append(item)

    def remove(self, index):
        if 0 <= index < len(self.items):
            self.items.pop(index)

    def __iter__(self):
        return iter(self.items)


# Subclass to bypass Gtk.ApplicationWindow.__init__
class GrubConfigManagerForTest(GrubConfigManager):
    def __init__(self, application):
        # Do NOT call super().__init__ to avoid Gtk.ApplicationWindow init issues
        self.application = application

        # Initialize attributes expected by methods
        self.timeout_dropdown = MagicMock(spec=Gtk.DropDown)
        self.default_dropdown = MagicMock(spec=Gtk.DropDown)
        self.hidden_timeout_check = MagicMock(spec=Gtk.CheckButton)

        self.state_manager = MagicMock(spec=AppStateManager)

        # Initialize other attributes to None as in the real class
        self.gfxmode_dropdown = None
        self.gfxpayload_dropdown = None
        self.terminal_color_check = None
        self.disable_os_prober_check = None
        self.entries_listbox = None
        self.maintenance_output = None
        self.info_revealer = None
        self.info_box = None
        self.info_label = None
        self.reload_btn = None
        self.save_btn = None


@pytest.fixture
def mock_app():
    return MagicMock(spec=Gtk.Application)


@pytest.fixture
def manager(mock_app):
    manager = GrubConfigManagerForTest(mock_app)
    return manager


def test_get_timeout_value(manager):
    # Setup mock dropdown
    model = MockStringList(["0", "5", "10"])
    manager.timeout_dropdown.get_model.return_value = model
    manager.timeout_dropdown.get_selected.return_value = 1  # "5"

    assert manager._get_timeout_value() == 5

    # Test invalid/hidden case -> returns 5 (default)
    model = MockStringList(["0", "5", "Hidden"])
    manager.timeout_dropdown.get_model.return_value = model
    manager.timeout_dropdown.get_selected.return_value = 2  # "Hidden"
    # "Hidden" cannot be converted to int, so it returns 5
    assert manager._get_timeout_value() == 5


def test_sync_timeout_choices(manager):
    # Case 1: Hidden checked -> ensure "Hidden" in list and selected
    # Note: _sync_timeout_choices logic is complex, it rebuilds the list.
    # We mock GtkHelper to verify calls if we want, or just check the model state.

    # We need to mock GtkHelper because it's used inside.
    # But here we are using the real GtkHelper imported in ui_manager.
    # Since we use MockStringList, GtkHelper should work fine with it.

    manager.hidden_timeout_check.get_active.return_value = True
    model = MockStringList(["5", "10"])
    manager.timeout_dropdown.get_model.return_value = model

    # Pass current value
    manager._sync_timeout_choices(5)

    # The logic in _sync_timeout_choices rebuilds the list based on base_values + current.
    # base_values = ["0", "1", "2", "5", "10", "30"]
    # It does NOT check hidden_timeout_check anymore (it was removed in previous refactors or I missed it).
    # Let's check the code of _sync_timeout_choices in ui_manager.py again.
    # It does NOT use hidden_timeout_check. It just ensures 'current' is in the list.

    assert "5" in model.items
    assert "10" in model.items
    manager.timeout_dropdown.set_selected.assert_called()


def test_ensure_timeout_choice(manager):
    model = MockStringList(["5", "10"])
    manager.timeout_dropdown.get_model.return_value = model

    # Value exists
    manager._ensure_timeout_choice("5")
    assert model.items == ["5", "10"]

    # Value doesn't exist -> should be added
    manager._ensure_timeout_choice("15")
    assert "15" in model.items


def test_set_timeout_value(manager):
    model = MockStringList(["5", "10"])
    manager.timeout_dropdown.get_model.return_value = model

    # Set normal value
    manager._set_timeout_value(10)
    # Verify set_selected called with index of "10" (which is 1)
    manager.timeout_dropdown.set_selected.assert_called_with(1)

    # Set value not in list -> adds it
    manager._set_timeout_value(15)
    assert "15" in model.items
    # Index of 15 should be 2 (5, 10, 15)
    manager.timeout_dropdown.set_selected.assert_called_with(2)


def test_refresh_default_choices(manager):
    # Mock state manager returning choices
    choices = [
        GrubDefaultChoice(id="id1", title="Choice 1", source="src1"),
        GrubDefaultChoice(id="id2", title="Choice 2", source="src2"),
    ]
    # Note: ui_manager calls self.state_manager.update_default_choice_ids(ids)

    # Setup default dropdown model
    model = MockStringList(["Old Choice"])
    manager.default_dropdown.get_model.return_value = model

    manager._refresh_default_choices(choices)

    # Should have replaced items
    assert "Choice 1" in model.items
    assert "Choice 2" in model.items
    assert "saved (dernière sélection)" in model.items
    assert "Old Choice" not in model.items

    # Verify state manager update
    manager.state_manager.update_default_choice_ids.assert_called()
    args = manager.state_manager.update_default_choice_ids.call_args[0][0]
    assert args == ["saved", "id1", "id2"]


def test_get_default_choice(manager):
    model = MockStringList(["saved (dernière sélection)", "Choice 1"])
    manager.default_dropdown.get_model.return_value = model
    manager.default_dropdown.get_selected.return_value = 1

    # Mock state manager returning IDs
    manager.state_manager.get_default_choice_ids.return_value = ["saved", "id1"]

    assert manager._get_default_choice() == "id1"


def test_set_default_choice(manager):
    model = MockStringList(["saved (dernière sélection)", "Choice 1"])
    manager.default_dropdown.get_model.return_value = model

    # Mock state manager returning IDs
    manager.state_manager.get_default_choice_ids.return_value = ["saved", "id1"]

    manager._set_default_choice("id1")

    manager.default_dropdown.set_selected.assert_called_with(1)
