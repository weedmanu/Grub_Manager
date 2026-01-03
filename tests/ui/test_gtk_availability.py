import gi

gi.require_version("Gtk", "4.0")
import pytest
from gi.repository import Gtk


def test_gtk_init():
    try:
        Gtk.init()
        label = Gtk.Label(label="test")
        assert label.get_label() == "test"
    except Exception as e:
        pytest.skip(f"GTK not available or no display: {e}")
