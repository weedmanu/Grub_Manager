from unittest.mock import MagicMock, patch

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GObject, Gtk

from ui.ui_gtk_helpers import GtkHelper


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


class MockStringListWithSpliceError(MockStringList):
    def splice(self, position, n_removals, additions):
        raise TypeError("Splice failed")


class MockStringListWithGetStringError(MockStringList):
    def get_string(self, index):
        raise TypeError("Get string failed")


def test_stringlist_find():
    model = MockStringList(["a", "b", "c"])
    assert GtkHelper.stringlist_find(model, "b") == 1
    assert GtkHelper.stringlist_find(model, "z") is None
    assert GtkHelper.stringlist_find(None, "a") is None


def test_stringlist_insert():
    model = MockStringList(["a", "c"])
    GtkHelper.stringlist_insert(model, 1, "b")
    assert model.items == ["a", "b", "c"]


def test_stringlist_insert_exception():
    model = MockStringListWithSpliceError(["a", "c"])
    # Should catch exception and append
    GtkHelper.stringlist_insert(model, 1, "b")
    assert model.items == ["a", "c", "b"]


def test_stringlist_replace_all():
    model = MockStringList(["a", "b"])
    GtkHelper.stringlist_replace_all(model, ["c", "d", "e"])
    assert model.items == ["c", "d", "e"]

    GtkHelper.stringlist_replace_all(None, ["x"])  # Should not crash


def test_stringlist_replace_all_exception():
    model = MockStringListWithSpliceError(["a", "b"])
    # Should catch exception and use remove/append loop
    GtkHelper.stringlist_replace_all(model, ["c", "d"])
    assert model.items == ["c", "d"]


def test_dropdown_get_value():
    dropdown = MagicMock(spec=Gtk.DropDown)
    model = MockStringList(["Option A", "Option B"])
    dropdown.get_model.return_value = model
    dropdown.get_selected.return_value = 1

    assert GtkHelper.dropdown_get_value(dropdown) == "Option B"

    # Test None/Invalid selection
    dropdown.get_selected.return_value = None
    assert GtkHelper.dropdown_get_value(dropdown) == ""

    # Test Model None
    dropdown.get_model.return_value = None
    assert GtkHelper.dropdown_get_value(dropdown) == ""


def test_dropdown_get_value_auto_prefix():
    dropdown = MagicMock(spec=Gtk.DropDown)
    model = MockStringList(["auto (Option A)", "Option B"])
    dropdown.get_model.return_value = model
    dropdown.get_selected.return_value = 0

    # Should return empty string if starts with auto_prefix (default "auto")
    assert GtkHelper.dropdown_get_value(dropdown) == ""

    # Custom prefix
    model = MockStringList(["custom (Option A)", "Option B"])
    dropdown.get_model.return_value = model
    dropdown.get_selected.return_value = 0
    assert GtkHelper.dropdown_get_value(dropdown, auto_prefix="custom") == ""


def test_dropdown_get_value_exception():
    dropdown = MagicMock(spec=Gtk.DropDown)
    model = MockStringListWithGetStringError(["Option A"])
    dropdown.get_model.return_value = model
    dropdown.get_selected.return_value = 0

    assert GtkHelper.dropdown_get_value(dropdown) == ""


def test_dropdown_set_value():
    dropdown = MagicMock(spec=Gtk.DropDown)
    model = MockStringList(["Option A", "Option B"])
    dropdown.get_model.return_value = model

    GtkHelper.dropdown_set_value(dropdown, "Option B")
    dropdown.set_selected.assert_called_with(1)

    GtkHelper.dropdown_set_value(dropdown, "Option C")
    # Should append and select
    assert "Option C" in model.items
    dropdown.set_selected.assert_called_with(2)


def test_dropdown_set_value_model_none():
    dropdown = MagicMock(spec=Gtk.DropDown)
    dropdown.get_model.return_value = None
    # Should not crash
    GtkHelper.dropdown_set_value(dropdown, "Option A")


def test_dropdown_set_value_empty():
    dropdown = MagicMock(spec=Gtk.DropDown)
    model = MockStringList(["auto (Default)", "Option A"])
    dropdown.get_model.return_value = model

    # Empty value -> select auto
    GtkHelper.dropdown_set_value(dropdown, "")
    dropdown.set_selected.assert_called_with(0)

    # Empty value, no auto -> select 0
    model = MockStringList(["Option A", "Option B"])
    dropdown.get_model.return_value = model
    GtkHelper.dropdown_set_value(dropdown, "")
    dropdown.set_selected.assert_called_with(0)


def test_dropdown_set_value_fallback():
    # Test case where insertion happens but finding it might fail (though hard to mock with just logic)
    # Or just cover the "no exact match found" path more thoroughly
    dropdown = MagicMock(spec=Gtk.DropDown)
    model = MockStringList(["auto (Default)", "Option A"])
    dropdown.get_model.return_value = model

    # Add new value, should insert after auto
    GtkHelper.dropdown_set_value(dropdown, "Option B")
    assert model.items == ["auto (Default)", "Option B", "Option A"]
    dropdown.set_selected.assert_called_with(1)


def test_dropdown_get_value_out_of_bounds():
    dropdown = MagicMock(spec=Gtk.DropDown)
    model = MockStringList(["Option A"])
    dropdown.get_model.return_value = model
    dropdown.get_selected.return_value = 10  # Out of bounds

    assert GtkHelper.dropdown_get_value(dropdown) == ""


def test_dropdown_set_value_insertion_check_failure_fallback_auto():
    """Test fallback to auto item when insertion check fails."""
    dropdown = MagicMock(spec=Gtk.DropDown)
    model = MockStringList(["Option 1", "auto Option 2"])
    dropdown.get_model.return_value = model

    # We want stringlist_find to return None even if we insert
    with patch("ui.ui_gtk_helpers.GtkHelper.stringlist_find", return_value=None):
        GtkHelper.dropdown_set_value(dropdown, "New Value")

        # Should have tried to insert
        assert "New Value" in model.items

        # But since find returned None, it should fallback to "auto Option 2" (index 1)
        dropdown.set_selected.assert_called_with(1)


def test_dropdown_set_value_insertion_check_failure_fallback_zero():
    """Test fallback to index 0 when insertion check fails and no auto item."""
    dropdown = MagicMock(spec=Gtk.DropDown)
    model = MockStringList(["Option 1", "Option 2"])
    dropdown.get_model.return_value = model

    with patch("ui.ui_gtk_helpers.GtkHelper.stringlist_find", return_value=None):
        GtkHelper.dropdown_set_value(dropdown, "New Value")

        # Should have tried to insert
        assert "New Value" in model.items

        # Fallback to 0
        dropdown.set_selected.assert_called_with(0)
