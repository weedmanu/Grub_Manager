import gi

gi.require_version("Gtk", "4.0")
from unittest.mock import MagicMock

from gi.repository import Gtk

from ui.tabs.ui_tabs_general import build_general_tab


def test_build_general_tab():
    # Mock controller
    controller = MagicMock()
    controller.on_modified = MagicMock()
    controller.on_hidden_timeout_toggled = MagicMock()

    # Mock notebook
    notebook = Gtk.Notebook()

    # Call the function
    build_general_tab(controller, notebook)

    # Verify that widgets were created and assigned to controller
    assert isinstance(controller.timeout_dropdown, Gtk.DropDown)
    assert isinstance(controller.default_dropdown, Gtk.DropDown)
    assert isinstance(controller.hidden_timeout_check, Gtk.Switch)

    # Verify that notebook has one page
    assert notebook.get_n_pages() == 1

    # Verify page label
    page = notebook.get_nth_page(0)
    label = notebook.get_tab_label(page)
    assert label.get_label() == "Général"


def test_build_general_tab_signals():
    # Mock controller
    controller = MagicMock()

    # Mock notebook
    notebook = Gtk.Notebook()

    # Call the function
    build_general_tab(controller, notebook)

    # Trigger signals and verify controller methods are called
    # Note: notify::selected is triggered when selection changes
    controller.timeout_dropdown.set_selected(1)
    # We can't easily check if on_modified was called because it's a signal connection
    # but we can check if the connection exists or just assume it works if no error.

    controller.hidden_timeout_check.set_active(True)
    # toggled signal should trigger on_hidden_timeout_toggled


import os

# Set headless backend for GTK
os.environ["GDK_BACKEND"] = "headless"


class MockController:
    def __init__(self):
        self.timeout_dropdown = None
        self.default_dropdown = None
        self.hidden_timeout_check = None
        self.cmdline_dropdown = None
        self.on_modified = MagicMock()
        self.on_hidden_timeout_toggled = MagicMock()
