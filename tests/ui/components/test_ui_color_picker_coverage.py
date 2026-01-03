
import os
from unittest.mock import MagicMock

from gi.repository import Gdk, Gtk

# Set headless backend for GTK
os.environ["GDK_BACKEND"] = "headless"

from ui.components.ui_color_picker import ColorPicker, create_color_grid_row


def test_color_picker_init():
    callback = MagicMock()
    picker = ColorPicker("Test Label", "#FF0000", callback=callback)
    assert picker.label_text == "Test Label"
    assert picker.get_color() == "#FF0000"

def test_color_picker_on_color_changed():
    callback = MagicMock()
    picker = ColorPicker("Test Label", "#FFFFFF", callback=callback)

    # Simulate color change
    rgba = Gdk.RGBA()
    rgba.parse("#00FF00")
    picker.color_button.set_property("rgba", rgba)

    picker._on_color_changed(picker.color_button)
    callback.assert_called_with("#00FF00")

def test_color_picker_on_color_changed_no_callback():
    picker = ColorPicker("Test Label", "#FFFFFF", callback=None)
    # Should not crash
    picker._on_color_changed(picker.color_button)

def test_color_picker_set_color_invalid():
    picker = ColorPicker("Test Label", "#FFFFFF")
    # Should not crash on invalid color
    picker.set_color("invalid")
    assert picker.get_color() == "#FFFFFF"

def test_color_picker_get_widget():
    picker = ColorPicker("Test Label", "#FFFFFF")
    widget = picker.get_widget()
    assert isinstance(widget, Gtk.Box)
    # Check if label and button are in the box
    # In GTK4 we can't easily list children like in GTK3 without iterating
    pass

def test_create_color_grid_row():
    callback = MagicMock()
    label, button = create_color_grid_row("Test", "#0000FF", callback=callback)
    assert isinstance(label, Gtk.Label)
    assert isinstance(button, Gtk.ColorButton)
    assert label.get_text() == "Test"
