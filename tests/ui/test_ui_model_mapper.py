"""Tests pour ui.ui_model_mapper."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ui.ui_model_mapper import ModelWidgetMapper


def _make_window() -> MagicMock:
    window = MagicMock()
    window.state_manager = MagicMock()
    window.state_manager.hidden_entry_ids = set()

    window._sync_timeout_choices = MagicMock()
    window._refresh_default_choices = MagicMock()
    window._set_default_choice = MagicMock()

    window.hidden_timeout_check = MagicMock()
    window.cmdline_dropdown = MagicMock()
    window.gfxmode_dropdown = MagicMock()
    window.gfxpayload_dropdown = MagicMock()
    window.disable_os_prober_check = MagicMock()

    window.hide_advanced_options_check = MagicMock()
    window.hide_memtest_check = MagicMock()

    window._get_default_choice = MagicMock(return_value="0")
    window._get_timeout_value = MagicMock(return_value=5)
    window._get_cmdline_value = MagicMock(return_value="quiet splash")

    return window


@pytest.mark.parametrize(
    "quiet,splash,expected_index",
    [
        (True, True, 0),
        (True, False, 1),
        (False, True, 2),
        (False, False, 3),
    ],
)
def test_apply_model_to_ui_sets_cmdline_dropdown(monkeypatch, quiet, splash, expected_index):
    window = _make_window()

    model = SimpleNamespace(
        timeout=10,
        hidden_timeout=False,
        quiet=quiet,
        splash=splash,
        gfxmode="1024x768",
        gfxpayload_linux="keep",
        disable_os_prober=False,
        default="0",
    )

    monkeypatch.setattr("ui.ui_model_mapper.GtkHelper.dropdown_set_value", MagicMock())

    ModelWidgetMapper.apply_model_to_ui(window, model, entries=[])

    window.cmdline_dropdown.set_selected.assert_called_with(expected_index)


def test_sync_global_hiding_switches_sets_switches_based_on_hidden_ids():
    window = _make_window()

    entries = [
        SimpleNamespace(menu_id="adv-id", title="Advanced options for Ubuntu", source="10_linux"),
        SimpleNamespace(menu_id="mem-id", title="Memory test (memtest86+)", source="20_memtest86+"),
    ]

    # When both ids are hidden, switches should become active
    window.state_manager.hidden_entry_ids = {"adv-id", "mem-id"}
    ModelWidgetMapper._sync_global_hiding_switches(window, entries)
    window.hide_advanced_options_check.set_active.assert_called_with(True)
    window.hide_memtest_check.set_active.assert_called_with(True)

    window.hide_advanced_options_check.reset_mock()
    window.hide_memtest_check.reset_mock()

    # When not all ids are hidden, switches should become inactive
    window.state_manager.hidden_entry_ids = {"adv-id"}
    ModelWidgetMapper._sync_global_hiding_switches(window, entries)
    window.hide_advanced_options_check.set_active.assert_called_with(True)
    window.hide_memtest_check.set_active.assert_called_with(False)


def test_read_model_from_ui_uses_dropdown_values_and_active_theme(monkeypatch):
    window = _make_window()
    window.hidden_timeout_check.get_active.return_value = True
    window.disable_os_prober_check.get_active.return_value = True

    # Dropdown getters
    monkeypatch.setattr("ui.ui_model_mapper.GtkHelper.dropdown_get_value", lambda _w: " 1024x768 ")

    # Active theme path
    monkeypatch.setattr("ui.ui_model_mapper.get_grub_themes_dir", lambda: Path("/themes"))
    theme = SimpleNamespace(name="MyTheme")
    theme_manager = MagicMock()
    theme_manager.get_active_theme.return_value = theme
    monkeypatch.setattr("ui.ui_model_mapper.ActiveThemeManager", lambda: theme_manager)

    model = ModelWidgetMapper.read_model_from_ui(window)

    assert model.timeout == 5
    assert model.default == "0"
    assert model.hidden_timeout is True
    assert model.disable_os_prober is True
    assert model.gfxmode == "1024x768"
    assert model.gfxpayload_linux == "1024x768"
    assert model.grub_theme == "/themes/MyTheme/theme.txt"
    assert model.quiet is True
    assert model.splash is True


def test_get_active_theme_path_returns_empty_on_error(monkeypatch):
    theme_manager = MagicMock()
    theme_manager.get_active_theme.side_effect = OSError("boom")
    monkeypatch.setattr("ui.ui_model_mapper.ActiveThemeManager", lambda: theme_manager)

    assert ModelWidgetMapper._get_active_theme_path() == ""


def test_apply_model_to_ui_without_cmdline_dropdown(monkeypatch):
    window = _make_window()
    window.cmdline_dropdown = None

    model = SimpleNamespace(
        timeout=10,
        hidden_timeout=False,
        quiet=True,
        splash=True,
        gfxmode="1024x768",
        gfxpayload_linux="keep",
        disable_os_prober=False,
        default="0",
    )

    monkeypatch.setattr("ui.ui_model_mapper.GtkHelper.dropdown_set_value", MagicMock())
    ModelWidgetMapper.apply_model_to_ui(window, model, entries=[])


def test_get_active_theme_path_empty_name_returns_empty(monkeypatch):
    theme_manager = MagicMock()
    theme_manager.get_active_theme.return_value = SimpleNamespace(name="")
    monkeypatch.setattr("ui.ui_model_mapper.ActiveThemeManager", lambda: theme_manager)

    assert ModelWidgetMapper._get_active_theme_path() == ""
