import gi

gi.require_version("Gtk", "4.0")
from unittest.mock import MagicMock

from gi.repository import Gtk

from ui.tabs.ui_tab_entries import _add_styled_switch, build_entries_tab


def test_build_entries_tab():
    # Mock controller
    controller = MagicMock()
    controller.on_menu_options_toggled = MagicMock()
    controller.on_hide_category_toggled = MagicMock()

    # Mock notebook
    notebook = Gtk.Notebook()

    # Call the function
    build_entries_tab(controller, notebook)

    # Verify that widgets were created and assigned to controller
    assert isinstance(controller.entries_listbox, Gtk.ListBox)
    assert isinstance(controller.disable_os_prober_check, Gtk.Switch)
    assert isinstance(controller.hide_advanced_options_check, Gtk.Switch)
    assert isinstance(controller.hide_memtest_check, Gtk.Switch)

    # Verify that notebook has one page
    assert notebook.get_n_pages() == 1

    # Verify page label
    page = notebook.get_nth_page(0)
    label = notebook.get_tab_label(page)
    assert label.get_label() == "Menu"


def test_add_styled_switch_no_description():
    container = Gtk.Box()
    switch = Gtk.Switch()
    _add_styled_switch(container, "Test", switch, description=None)
    # No error means success, and coverage will be 100%
