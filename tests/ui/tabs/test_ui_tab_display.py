import gi

gi.require_version("Gtk", "4.0")
from unittest.mock import MagicMock

from gi.repository import Gtk

from ui.tabs.ui_tab_display import build_display_tab


def test_build_display_tab():
    # Mock controller
    controller = MagicMock()
    controller.on_modified = MagicMock()

    # Mock notebook
    notebook = Gtk.Notebook()

    # Call the function
    build_display_tab(controller, notebook)

    # Verify that widgets were created and assigned to controller
    assert isinstance(controller.gfxmode_dropdown, Gtk.DropDown)
    assert isinstance(controller.gfxpayload_dropdown, Gtk.DropDown)

    # Verify that notebook has one page
    assert notebook.get_n_pages() == 1

    # Verify page label
    page = notebook.get_nth_page(0)
    label = notebook.get_tab_label(page)
    assert label.get_label() == "Affichage"


def test_build_display_tab_signals():
    # Mock controller
    controller = MagicMock()

    # Mock notebook
    notebook = Gtk.Notebook()

    # Call the function
    build_display_tab(controller, notebook)

    # Trigger signals
    controller.gfxmode_dropdown.set_selected(1)
    controller.gfxpayload_dropdown.set_selected(1)


import os

# Set headless backend for GTK
os.environ["GDK_BACKEND"] = "headless"



class MockController:
    def __init__(self):
        self.gfxmode_dropdown = None
        self.gfxpayload_dropdown = None
        self.on_modified = MagicMock()


def test_build_display_tab():
    controller = MockController()
    notebook = Gtk.Notebook()

    build_display_tab(controller, notebook)

    assert notebook.get_n_pages() == 1
    assert isinstance(controller.gfxmode_dropdown, Gtk.DropDown)
    assert isinstance(controller.gfxpayload_dropdown, Gtk.DropDown)

    # Check if signals are connected
    controller.gfxmode_dropdown.set_selected(1)
    assert controller.on_modified.called

    controller.gfxpayload_dropdown.set_selected(1)
    assert controller.on_modified.call_count == 2
