
import pytest
from unittest.mock import MagicMock, patch
from gi.repository import Gtk, GLib
import os

# Set headless backend for GTK
os.environ["GDK_BACKEND"] = "headless"

from ui.ui_gtk_helpers import GtkHelper

def test_stringlist_find():
    model = Gtk.StringList.new(["a", "b", "c"])
    assert GtkHelper.stringlist_find(model, "b") == 1
    assert GtkHelper.stringlist_find(model, "z") is None
    assert GtkHelper.stringlist_find(None, "a") is None

def test_stringlist_insert_success():
    model = Gtk.StringList.new(["a", "c"])
    GtkHelper.stringlist_insert(model, 1, "b")
    assert model.get_string(1) == "b"
    assert model.get_n_items() == 3

def test_stringlist_insert_exception():
    model = MagicMock()
    model.splice.side_effect = TypeError("Boom")
    GtkHelper.stringlist_insert(model, 0, "val")
    model.append.assert_called_with("val")

def test_dropdown_get_value_success():
    model = Gtk.StringList.new(["a", "b"])
    dropdown = MagicMock(spec=Gtk.DropDown)
    dropdown.get_selected.return_value = 1
    dropdown.get_model.return_value = model
    assert GtkHelper.dropdown_get_value(dropdown) == "b"

def test_dropdown_get_value_none():
    dropdown = MagicMock(spec=Gtk.DropDown)
    dropdown.get_selected.return_value = None
    dropdown.get_model.return_value = None
    assert GtkHelper.dropdown_get_value(dropdown) == ""

def test_dropdown_get_value_exception():
    dropdown = MagicMock(spec=Gtk.DropDown)
    dropdown.get_selected.return_value = 0
    model = MagicMock()
    model.get_string.side_effect = AttributeError("Boom")
    dropdown.get_model.return_value = model
    assert GtkHelper.dropdown_get_value(dropdown) == ""

def test_dropdown_get_value_auto():
    model = Gtk.StringList.new(["auto (default)", "b"])
    dropdown = MagicMock(spec=Gtk.DropDown)
    dropdown.get_selected.return_value = 0
    dropdown.get_model.return_value = model
    assert GtkHelper.dropdown_get_value(dropdown) == ""

def test_dropdown_get_value_val_none():
    dropdown = MagicMock(spec=Gtk.DropDown)
    dropdown.get_selected.return_value = 0
    model = MagicMock()
    model.get_string.return_value = None
    dropdown.get_model.return_value = model
    assert GtkHelper.dropdown_get_value(dropdown) == ""

def test_dropdown_set_value_none_model():
    dropdown = MagicMock(spec=Gtk.DropDown)
    dropdown.get_model.return_value = None
    GtkHelper.dropdown_set_value(dropdown, "val")
    dropdown.set_selected.assert_not_called()

def test_dropdown_set_value_empty_with_auto():
    model = Gtk.StringList.new(["auto (default)", "b"])
    dropdown = MagicMock(spec=Gtk.DropDown)
    dropdown.get_model.return_value = model
    GtkHelper.dropdown_set_value(dropdown, "")
    dropdown.set_selected.assert_called_with(0)

def test_dropdown_set_value_empty_no_auto():
    model = Gtk.StringList.new(["a", "b"])
    dropdown = MagicMock(spec=Gtk.DropDown)
    dropdown.get_model.return_value = model
    GtkHelper.dropdown_set_value(dropdown, "")
    dropdown.set_selected.assert_called_with(0)

def test_dropdown_set_value_exact_match():
    model = Gtk.StringList.new(["a", "b"])
    dropdown = MagicMock(spec=Gtk.DropDown)
    dropdown.get_model.return_value = model
    GtkHelper.dropdown_set_value(dropdown, "b")
    dropdown.set_selected.assert_called_with(1)

def test_dropdown_set_value_add_new_with_auto():
    model = Gtk.StringList.new(["auto (default)", "a"])
    dropdown = MagicMock(spec=Gtk.DropDown)
    dropdown.get_model.return_value = model
    GtkHelper.dropdown_set_value(dropdown, "new")
    assert model.get_string(1) == "new"
    dropdown.set_selected.assert_called_with(1)

def test_dropdown_set_value_add_new_no_auto():
    model = Gtk.StringList.new(["a", "b"])
    dropdown = MagicMock(spec=Gtk.DropDown)
    dropdown.get_model.return_value = model
    GtkHelper.dropdown_set_value(dropdown, "new")
    assert model.get_string(2) == "new"
    dropdown.set_selected.assert_called_with(2)

def test_dropdown_set_value_fallback_auto():
    # Case where find returns None after insert (should not happen with real model but for coverage)
    model = MagicMock()
    model.get_n_items.return_value = 1
    model.get_string.return_value = "auto (default)"
    dropdown = MagicMock(spec=Gtk.DropDown)
    dropdown.get_model.return_value = model
    
    with patch("ui.ui_gtk_helpers.GtkHelper.stringlist_find", return_value=None):
        GtkHelper.dropdown_set_value(dropdown, "new")
        dropdown.set_selected.assert_called_with(0)

def test_dropdown_set_value_fallback_zero():
    model = MagicMock()
    model.get_n_items.return_value = 1
    model.get_string.return_value = "not auto"
    dropdown = MagicMock(spec=Gtk.DropDown)
    dropdown.get_model.return_value = model
    
    with patch("ui.ui_gtk_helpers.GtkHelper.stringlist_find", return_value=None):
        GtkHelper.dropdown_set_value(dropdown, "new")
        dropdown.set_selected.assert_called_with(0)

def test_stringlist_replace_all_success():
    model = Gtk.StringList.new(["a", "b"])
    GtkHelper.stringlist_replace_all(model, ["c", "d", "e"])
    assert model.get_n_items() == 3
    assert model.get_string(0) == "c"

def test_stringlist_replace_all_none():
    GtkHelper.stringlist_replace_all(None, ["a"])

def test_stringlist_replace_all_exception():
    model = MagicMock()
    model.get_n_items.return_value = 2
    model.splice.side_effect = TypeError("Boom")
    
    # Mock remove to decrease n_items
    def mock_remove(idx):
        model.get_n_items.return_value -= 1
    model.remove.side_effect = mock_remove
    
    GtkHelper.stringlist_replace_all(model, ["a", "b"])
    assert model.remove.call_count == 2
    assert model.append.call_count == 2
