
import pytest
from unittest.mock import MagicMock
from gi.repository import Gtk
import os

# Set headless backend for GTK
os.environ["GDK_BACKEND"] = "headless"

from ui.tabs.ui_tab_general import build_general_tab

class MockController:
    def __init__(self):
        self.timeout_dropdown = None
        self.default_dropdown = None
        self.hidden_timeout_check = None
        self.cmdline_dropdown = None
        self.on_modified = MagicMock()
        self.on_hidden_timeout_toggled = MagicMock()

def test_build_general_tab():
    controller = MockController()
    notebook = Gtk.Notebook()
    
    build_general_tab(controller, notebook)
    
    assert notebook.get_n_pages() == 1
    assert isinstance(controller.timeout_dropdown, Gtk.DropDown)
    assert isinstance(controller.default_dropdown, Gtk.DropDown)
    assert isinstance(controller.hidden_timeout_check, Gtk.Switch)
    assert isinstance(controller.cmdline_dropdown, Gtk.DropDown)
    
    # Check if signals are connected
    controller.timeout_dropdown.set_selected(1)
    assert controller.on_modified.called
    
    controller.hidden_timeout_check.set_active(True)
    assert controller.on_hidden_timeout_toggled.called
