from __future__ import annotations

from unittest.mock import MagicMock, patch

import gi
import pytest

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ui.tabs.ui_theme_editor_dialog import ThemeEditorDialog


@pytest.fixture
def state_manager():
    return MagicMock()


@pytest.fixture
def parent_window():
    return Gtk.Window()


def test_theme_editor_dialog_init(parent_window, state_manager):
    with patch("ui.tabs.ui_theme_editor_dialog.TabThemeEditor") as mock_editor_class:
        mock_editor = mock_editor_class.return_value
        mock_editor.build.return_value = Gtk.Box()

        # Mock all widgets that are copied
        mock_editor.title_color_btn = MagicMock()
        mock_editor.bg_color_btn = MagicMock()
        mock_editor.menu_fg_btn = MagicMock()
        mock_editor.menu_bg_btn = MagicMock()
        mock_editor.highlight_fg_btn = MagicMock()
        mock_editor.highlight_bg_btn = MagicMock()
        mock_editor.bg_image_entry = MagicMock()
        mock_editor.bg_image_scale_combo = MagicMock()
        mock_editor.show_boot_menu_check = MagicMock()
        mock_editor.show_progress_check = MagicMock()
        mock_editor.show_timeout_check = MagicMock()
        mock_editor.show_scrollbar_check = MagicMock()
        mock_editor.theme_name_entry = MagicMock()
        mock_editor.title_text_entry = MagicMock()
        mock_editor.grub_timeout_spin = MagicMock()
        mock_editor.grub_gfxmode_entry = MagicMock()
        mock_editor.preview_buffer = MagicMock()

        dialog = ThemeEditorDialog(parent_window, state_manager)

        assert dialog.state_manager == state_manager
        assert dialog.title_color_btn == mock_editor.title_color_btn
        assert mock_editor.load_default_theme.called


def test_theme_editor_dialog_load_default_theme_no_editor(parent_window, state_manager):
    with patch("ui.tabs.ui_theme_editor_dialog.TabThemeEditor") as mock_editor_class:
        mock_editor = mock_editor_class.return_value
        mock_editor.build.return_value = Gtk.Box()
        dialog = ThemeEditorDialog(parent_window, state_manager)

        # Manually remove _editor to test the branch
        del dialog._editor
        dialog._load_default_theme()  # Should not crash
