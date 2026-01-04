"""Tests pour le constructeur d'interface utilisateur UIBuilder."""

import gi

gi.require_version("Gtk", "4.0")
from unittest.mock import MagicMock, patch

from gi.repository import Gtk

from ui.ui_builder import UIBuilder


def test_create_main_ui():
    """Test la création de l'interface principale."""
    # Mock window (GrubConfigManager)
    window = MagicMock()

    # We need to mock the tab build functions because they might do complex things
    with (
        patch("ui.ui_builder.build_general_tab"),
        patch("ui.ui_builder.build_entries_tab"),
        patch("ui.ui_builder.build_display_tab"),
        patch("ui.ui_builder.build_maintenance_tab"),
        patch("ui.ui_builder.TabThemeConfig") as MockTabThemeConfig,
    ):

        # Mock TabThemeConfig instance to return a real Gtk.Box
        mock_theme_config = MockTabThemeConfig.return_value
        mock_theme_config.build.return_value = Gtk.Box()

        # Call the function
        UIBuilder.create_main_ui(window)

        # Verify window.set_child was called
        window.set_child.assert_called_once()
        assert isinstance(window.set_child.call_args[0][0], Gtk.Box)

        # Verify buttons were created and assigned
        assert isinstance(window.reload_btn, Gtk.Button)
        assert isinstance(window.save_btn, Gtk.Button)
        assert isinstance(window.info_revealer, Gtk.Revealer)
        assert isinstance(window.info_label, Gtk.Label)


def test_create_bottom_bar():
    window = MagicMock()
    container = Gtk.Box()

    UIBuilder._create_bottom_bar(window, container)

    assert isinstance(window.info_revealer, Gtk.Revealer)
    assert isinstance(window.reload_btn, Gtk.Button)
    assert isinstance(window.save_btn, Gtk.Button)


def test_create_notebook():
    window = MagicMock()
    container = Gtk.Box()

    with (
        patch("ui.ui_builder.build_general_tab"),
        patch("ui.ui_builder.build_entries_tab"),
        patch("ui.ui_builder.build_display_tab"),
        patch("ui.ui_builder.build_maintenance_tab"),
        patch("ui.ui_builder.TabThemeConfig") as MockTabThemeConfig,
    ):

        mock_theme_config = MockTabThemeConfig.return_value
        mock_theme_config.build.return_value = Gtk.Box()

        notebook = UIBuilder._create_notebook(window, container)

        # Trigger switch-page signal - Case 1: Sauvegardes (buttons disabled)
        page_backups = Gtk.Box()
        notebook.append_page(page_backups, Gtk.Label(label="Sauvegardes"))
        notebook.set_current_page(1)
        window.save_btn.set_sensitive.assert_called_with(False)
        window.reload_btn.set_sensitive.assert_called_with(False)

        # Trigger switch-page signal - Case 2: Other tab, not dirty
        window.state_manager.is_dirty.return_value = False
        page_other = Gtk.Box()
        notebook.append_page(page_other, Gtk.Label(label="Autre"))
        # Manually emit signal to be 100% sure
        notebook.emit("switch-page", page_other, 2)
        window.save_btn.set_sensitive.assert_called_with(False)
        window.reload_btn.set_sensitive.assert_called_with(True)

        # Trigger switch-page signal - Case 2b: Menu (always enabled)
        window.save_btn.set_sensitive.reset_mock()
        window.reload_btn.set_sensitive.reset_mock()
        page_menu = Gtk.Box()
        notebook.append_page(page_menu, Gtk.Label(label="Menu"))
        notebook.emit("switch-page", page_menu, 3)
        window.save_btn.set_sensitive.assert_called_with(True)
        window.reload_btn.set_sensitive.assert_called_with(True)

        # Trigger switch-page signal - Case 3: Other tab, dirty (buttons NOT disabled by this logic)
        window.state_manager.is_dirty.return_value = True
        window.save_btn.set_sensitive.reset_mock()
        notebook.set_current_page(0)  # Switch back to first tab
        # Should not call set_sensitive(False) in the elif block
        assert not any(call.args == (False,) for call in window.save_btn.set_sensitive.call_args_list)
