
import os
from unittest.mock import MagicMock

from gi.repository import Gtk

# Set headless backend for GTK
os.environ["GDK_BACKEND"] = "headless"

from ui.tabs.ui_tab_entries import _add_styled_switch, build_entries_tab


class MockController:
    def __init__(self):
        self.entries_listbox = None
        self.disable_os_prober_check = None
        self.hide_advanced_options_check = None
        self.hide_memtest_check = None
        self.on_menu_options_toggled = MagicMock()
        self.on_hide_category_toggled = MagicMock()

def test_build_entries_tab():
    controller = MockController()
    notebook = Gtk.Notebook()

    build_entries_tab(controller, notebook)

    assert notebook.get_n_pages() == 1
    assert isinstance(controller.entries_listbox, Gtk.ListBox)
    assert isinstance(controller.disable_os_prober_check, Gtk.Switch)
    assert isinstance(controller.hide_advanced_options_check, Gtk.Switch)
    assert isinstance(controller.hide_memtest_check, Gtk.Switch)

    # Check if switches are connected
    controller.disable_os_prober_check.set_active(True)
    assert controller.on_menu_options_toggled.called

    controller.hide_advanced_options_check.set_active(True)
    assert controller.on_hide_category_toggled.called

def test_add_styled_switch_no_description():
    container = Gtk.Box()
    switch = Gtk.Switch()
    _add_styled_switch(container, "Test Label", switch, description=None)

    # Check if children were added (Box and Separator)
    # container -> [row (Box), separator (Separator)]
    # row -> [vbox (Box), switch (Switch)]
    # vbox -> [label (Label)]

    child = container.get_first_child()
    assert isinstance(child, Gtk.Box)

    vbox = child.get_first_child()
    assert isinstance(vbox, Gtk.Box)

    label = vbox.get_first_child()
    assert isinstance(label, Gtk.Label)
    assert label.get_text() == "Test Label"

    # Check that there is no second child in vbox (no description)
    assert vbox.get_last_child() == label
