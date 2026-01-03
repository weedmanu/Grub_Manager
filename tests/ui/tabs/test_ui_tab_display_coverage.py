
import os
from unittest.mock import MagicMock

from gi.repository import Gtk

# Set headless backend for GTK
os.environ["GDK_BACKEND"] = "headless"

from ui.tabs.ui_tab_display import build_display_tab


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
