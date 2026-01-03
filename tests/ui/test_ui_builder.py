import gi

gi.require_version("Gtk", "4.0")
from unittest.mock import MagicMock, patch

from gi.repository import Gtk

from ui.ui_builder import UIBuilder


def test_create_main_ui():
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

        # Trigger switch-page signal
        page = Gtk.Box()
        notebook.append_page(page, Gtk.Label(label="Test"))
        notebook.set_current_page(1)


def test_obsolete_methods():
    window = MagicMock()
    container = Gtk.Box()
    UIBuilder._create_info_area(window, container)
    UIBuilder._create_action_buttons(window, container)
