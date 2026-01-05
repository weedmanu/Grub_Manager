from unittest.mock import MagicMock

import pytest
from gi.repository import Gdk, Gtk

from ui.dialogs.ui_dialogs_interactive_theme_generator import (
    ElementConfigPanel,
    InteractiveThemeGeneratorPanel,
    ThemeElement,
    ThemeElementRow,
)


@pytest.fixture
def mock_element():
    return ThemeElement(name="test_element", label="Test Element", description="Test Description", enabled=True)


def test_theme_element_row(mock_element):
    on_toggle = MagicMock()
    on_configure = MagicMock()

    row = ThemeElementRow(mock_element, on_toggle, on_configure)

    # Test toggle
    row.switch.set_active(False)
    # The signal handler should be called
    assert mock_element.enabled is False
    on_toggle.assert_called_with(mock_element, False)

    # Test configure button
    row.on_configure(mock_element)
    on_configure.assert_called_with(mock_element)


def test_element_config_panel_boot_menu():
    element = ThemeElement(name="boot_menu", label="Boot Menu", description="")
    panel = ElementConfigPanel(element)
    assert "left" in panel.config_widgets
    assert "top" in panel.config_widgets
    assert "width" in panel.config_widgets
    assert "height" in panel.config_widgets


def test_element_config_panel_get_properties():
    element = ThemeElement(name="boot_menu", label="Boot Menu", description="")
    panel = ElementConfigPanel(element)

    # The editor is the first child (after the title label)
    # Actually, ElementConfigPanel appends the title, then the editor.
    # So editor is the second child.
    title = panel.get_first_child()
    editor = title.get_next_sibling()

    # Mock widgets to return specific values
    editor.config_widgets["left"].get_value = MagicMock(return_value=10.0)

    # Add an entry
    entry = MagicMock(spec=Gtk.Entry)
    entry.get_text.return_value = "test text"
    editor.config_widgets["text_entry"] = entry

    # Add a color button
    color_btn = MagicMock(spec=Gtk.ColorButton)
    rgba = MagicMock(spec=Gdk.RGBA)
    rgba.red = 1.0
    rgba.green = 0.0
    rgba.blue = 0.0
    color_btn.get_property.side_effect = lambda prop: rgba if prop == "rgba" else None
    editor.config_widgets["color"] = color_btn

    # Add a dropdown
    dropdown = MagicMock(spec=Gtk.DropDown)
    dropdown.get_selected.return_value = 2
    model = MagicMock()
    item = MagicMock()
    item.get_string.return_value = "option3"
    model.get_item.return_value = item
    dropdown.get_model.return_value = model
    editor.config_widgets["dropdown"] = dropdown

    # Add a font button
    font_btn = MagicMock(spec=Gtk.FontButton)
    font_btn.get_property.side_effect = lambda prop: "Sans 12" if prop == "font" else None
    editor.config_widgets["font"] = font_btn

    props = panel.get_properties()
    assert props["left"] == 10.0
    assert props["text_entry"] == "test text"
    assert props["color"] == "#ff0000"
    assert props["dropdown"] == "option3"
    assert props["font"] == "Sans 12"


def test_element_config_panel_generic():
    element = ThemeElement(name="unknown", label="Unknown", description="")
    panel = ElementConfigPanel(element)
    # Should use _build_generic_config
    assert panel.get_first_child() is not None


def test_element_config_panel_get_properties_unknown_widget():
    element = ThemeElement(name="boot_menu", label="Boot Menu", description="")
    panel = ElementConfigPanel(element)
    title = panel.get_first_child()
    editor = title.get_next_sibling()

    # Add an unknown widget type
    editor.config_widgets["unknown"] = MagicMock()
    props = panel.get_properties()
    assert "unknown" not in props


def test_element_config_panel_all_configs():
    elements = ["progress_bar", "timeout_label", "footer_image", "desktop_image", "colors", "fonts"]
    for name in elements:
        element = ThemeElement(name=name, label=name, description="")
        panel = ElementConfigPanel(element)
        assert panel is not None


def test_interactive_theme_generator_panel():
    on_updated = MagicMock()
    panel = InteractiveThemeGeneratorPanel(on_theme_updated=on_updated)

    # Test element toggle notification
    element = panel.elements["boot_menu"]
    panel._on_element_toggled(element, False)
    on_updated.assert_called()

    # Test notify_update without callback
    panel.on_theme_updated = None
    panel._notify_update()  # Should not crash

    # Test configure element
    panel._on_configure_element(element)
    # Check if config_container has the right panel
    child = panel.config_container.get_first_child()
    assert child == panel.config_panels["boot_menu"]

    # Test show_config_panel with unknown element
    panel._show_config_panel("unknown")
    assert panel.config_container.get_first_child() is None

    # Test get_theme_config
    config = panel.get_theme_config()
    assert "elements" in config
    assert "properties" in config
    assert "boot_menu" in config["elements"]
    assert "boot_menu" in config["properties"]

    # Test get_theme_config with element not in config_panels
    del panel.config_panels["boot_menu"]
    config = panel.get_theme_config()
    assert "boot_menu" not in config["properties"]


def test_interactive_theme_generator_panel_clear_config_container():
    panel = InteractiveThemeGeneratorPanel()
    panel.config_container.append(Gtk.Label(label="1"))
    panel.config_container.append(Gtk.Label(label="2"))
    panel._show_config_panel("non_existent")
    assert panel.config_container.get_first_child() is None
