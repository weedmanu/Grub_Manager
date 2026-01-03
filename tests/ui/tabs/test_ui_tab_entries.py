import gi

gi.require_version("Gtk", "4.0")
from unittest.mock import MagicMock

from gi.repository import Gtk

from ui.tabs.ui_tab_entries import build_entries_tab


def test_build_entries_tab():
    # Mock controller
    controller = MagicMock()
    controller.on_menu_options_toggled = MagicMock()

    # Mock notebook
    notebook = Gtk.Notebook()

    # Call the function
    build_entries_tab(controller, notebook)

    # Verify that widgets were created and assigned to controller
    assert isinstance(controller.entries_listbox, Gtk.ListBox)
    assert isinstance(controller.disable_recovery_check, Gtk.CheckButton)
    assert isinstance(controller.disable_os_prober_check, Gtk.CheckButton)
    assert isinstance(controller.disable_submenu_check, Gtk.CheckButton)

    # Verify that notebook has one page
    assert notebook.get_n_pages() == 1

    # Verify page label
    page = notebook.get_nth_page(0)
    label = notebook.get_tab_label(page)
    assert label.get_label() == "Menu"


def test_build_entries_tab_signals():
    # Mock controller
    controller = MagicMock()

    # Mock notebook
    notebook = Gtk.Notebook()

    # Call the function
    build_entries_tab(controller, notebook)

    # Trigger signals
    controller.disable_recovery_check.set_active(True)
    controller.disable_os_prober_check.set_active(True)
    controller.disable_submenu_check.set_active(True)
