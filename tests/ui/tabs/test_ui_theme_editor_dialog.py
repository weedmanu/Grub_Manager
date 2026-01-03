import gi

gi.require_version("Gtk", "4.0")
from unittest.mock import MagicMock

from gi.repository import Gtk

from ui.tabs.ui_theme_editor_dialog import ThemeEditorDialog


def test_theme_editor_dialog_init():
    # Mock state_manager
    state_manager = MagicMock()

    # Create parent window
    parent = Gtk.Window()

    # Instantiate dialog
    dialog = ThemeEditorDialog(parent, state_manager)

    assert isinstance(dialog, Gtk.Window)
    assert dialog.get_title() == "Éditeur de thèmes GRUB"
    assert dialog.state_manager == state_manager

    # Verify widgets are assigned
    assert dialog.title_color_btn is not None
    assert dialog.theme_name_entry is not None
    assert dialog.preview_buffer is not None


def test_theme_editor_dialog_load_default():
    # Mock state_manager
    state_manager = MagicMock()
    parent = Gtk.Window()

    # Instantiate dialog
    dialog = ThemeEditorDialog(parent, state_manager)

    # _load_default_theme is called in __init__
    # We can check if current_theme is set in the editor
    assert dialog._editor.current_theme is not None


def test_load_default_theme_no_editor():
    """Test _load_default_theme when _editor attribute is missing."""
    state_manager = MagicMock()
    parent = Gtk.Window()
    dialog = ThemeEditorDialog(parent, state_manager)

    # Remove _editor attribute
    del dialog._editor

    # Call _load_default_theme, should not raise error
    dialog._load_default_theme()
