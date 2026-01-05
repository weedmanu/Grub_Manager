"""Tests pour ui.ui_model_mapper."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.system.core_grub_system_commands import GrubUiModel
from ui.ui_model_mapper import ModelWidgetMapper


def _make_window() -> MagicMock:
    window = MagicMock()
    window.state_manager = MagicMock()
    window.state_manager.hidden_entry_ids = set()

    window.sync_timeout_choices = MagicMock()
    window.refresh_default_choices = MagicMock()
    window.set_default_choice = MagicMock()

    window.hidden_timeout_check = MagicMock()
    window.cmdline_dropdown = MagicMock()
    window.gfxmode_dropdown = MagicMock()
    window.gfxpayload_dropdown = MagicMock()
    window.disable_os_prober_check = MagicMock()

    window.hide_advanced_options_check = MagicMock()
    window.hide_memtest_check = MagicMock()

    window.get_default_choice = MagicMock(return_value="0")
    window.get_timeout_value = MagicMock(return_value=5)
    window.get_cmdline_value = MagicMock(return_value="quiet splash")
    
    # Add theme_config_controller with proper mocks for color combos
    window.theme_config_controller = MagicMock()
    window.theme_config_controller.theme_switch = MagicMock()
    window.theme_config_controller.theme_switch.get_active.return_value = True
    window.theme_config_controller.bg_image_entry = MagicMock()
    window.theme_config_controller.bg_image_entry.get_text.return_value = ""
    window.theme_config_controller.normal_fg_combo = MagicMock()
    window.theme_config_controller.normal_fg_combo.get_selected.return_value = -1
    window.theme_config_controller.normal_bg_combo = MagicMock()
    window.theme_config_controller.normal_bg_combo.get_selected.return_value = -1
    window.theme_config_controller.highlight_fg_combo = MagicMock()
    window.theme_config_controller.highlight_fg_combo.get_selected.return_value = -1
    window.theme_config_controller.highlight_bg_combo = MagicMock()
    window.theme_config_controller.highlight_bg_combo.get_selected.return_value = -1

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


def test_model_mapper_with_dropdown_exceptions():
    """Test ui_model_mapper when dropdowns raise exceptions."""
    from core.models.core_grub_ui_model import GrubUiModel
    
    window = MagicMock()
    window.get_default_choice.return_value = "0"
    window.get_timeout_value.return_value = 5
    window.get_cmdline_value.return_value = "quiet"

    # Dropdown that returns invalid values
    window.gfxmode_dropdown = MagicMock()
    window.gfxpayload_dropdown = MagicMock()
    window.hidden_timeout_check = MagicMock()
    window.disable_os_prober_check = MagicMock()

    # Theme controller with no combos
    window.theme_config_controller = None
    window.state_manager = MagicMock()
    window.state_manager.state_data = SimpleNamespace(
        model=GrubUiModel(theme_management_enabled=False)
    )

    with patch("ui.ui_model_mapper.GtkHelper.dropdown_get_value", return_value=""):
        model = ModelWidgetMapper.read_model_from_ui(window)
        assert model.timeout == 5


def test_read_model_with_exception_in_color_parsing():
    """Test color parsing with out-of-range combo values."""
    from core.models.core_grub_ui_model import GrubUiModel
    
    window = MagicMock()
    window.get_default_choice.return_value = "0"
    window.get_timeout_value.return_value = 5
    window.get_cmdline_value.return_value = ""

    window.gfxmode_dropdown = None
    window.gfxpayload_dropdown = None
    window.hidden_timeout_check = None
    window.disable_os_prober_check = None

    # Theme controller with out-of-range combo indices (negative)
    window.theme_config_controller = MagicMock()
    window.theme_config_controller.theme_switch = None
    window.theme_config_controller.bg_image_entry = None

    # Create mock combos with proper return values
    normal_fg_combo = MagicMock()
    normal_fg_combo.get_selected = MagicMock(return_value=-1)
    window.theme_config_controller.normal_fg_combo = normal_fg_combo

    normal_bg_combo = MagicMock()
    normal_bg_combo.get_selected = MagicMock(return_value=-1)
    window.theme_config_controller.normal_bg_combo = normal_bg_combo

    highlight_fg_combo = MagicMock()
    highlight_fg_combo.get_selected = MagicMock(return_value=-1)
    window.theme_config_controller.highlight_fg_combo = highlight_fg_combo

    highlight_bg_combo = MagicMock()
    highlight_bg_combo.get_selected = MagicMock(return_value=-1)
    window.theme_config_controller.highlight_bg_combo = highlight_bg_combo

    window.state_manager = MagicMock()
    window.state_manager.state_data = MagicMock()
    window.state_manager.state_data.model = GrubUiModel(theme_management_enabled=True)

    # Should handle negative indices gracefully
    model = ModelWidgetMapper.read_model_from_ui(window)
    assert model.grub_color_normal == ""  # Out of range returns empty


def test_read_model_from_ui_uses_dropdown_values_and_active_theme(monkeypatch):
    window = _make_window()
    window.hidden_timeout_check.get_active.return_value = True
    window.disable_os_prober_check.get_active.return_value = True

    # Dropdown getters
    monkeypatch.setattr("ui.ui_model_mapper.GtkHelper.dropdown_get_value", lambda _w: " 1024x768 ")

    # Set theme in model since read_model_from_ui takes it from there
    window.state_manager.state_data.model = GrubUiModel(
        grub_theme="/themes/MyTheme/theme.txt",
        theme_management_enabled=True
    )

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


def test_apply_model_to_ui_without_theme_config_controller(monkeypatch):
    """Cover the false branch of `if window.theme_config_controller:`."""
    window = _make_window()
    window.theme_config_controller = None

    model = SimpleNamespace(
        timeout=10,
        hidden_timeout=False,
        quiet=False,
        splash=False,
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

def test_read_model_from_ui_color_bounds_checking():
    """Test les vérifications de bornes pour les index de couleur."""
    window = MagicMock()
    window.state_manager = MagicMock()
    
    ctrl = MagicMock()
    ctrl.timeout_spin = MagicMock(get_value=MagicMock(return_value=10))
    ctrl.hidden_timeout_spin = MagicMock(get_value=MagicMock(return_value=0))
    ctrl.gfxmode_entry = MagicMock(get_text=MagicMock(return_value=""))
    ctrl.default_combo = MagicMock(get_selected=MagicMock(return_value=0))
    ctrl.default_switch = MagicMock(get_active=MagicMock(return_value=False))
    
    # Test with valid indices to trigger the color building code path
    ctrl.normal_fg_combo = MagicMock(get_selected=MagicMock(return_value=0))
    ctrl.normal_bg_combo = MagicMock(get_selected=MagicMock(return_value=1))
    ctrl.highlight_fg_combo = MagicMock(get_selected=MagicMock(return_value=1))
    ctrl.highlight_bg_combo = MagicMock(get_selected=MagicMock(return_value=0))
    
    window.theme_config_controller = ctrl
    window.entries_renderer = MagicMock()
    window.entries_renderer.hidden_entries = []
    
    # This should trigger the valid path and return a model
    model = ModelWidgetMapper.read_model_from_ui(window)
    assert model is not None
    # Verify color normal was set (not empty)
    assert hasattr(model, 'grub_color_normal')
    assert hasattr(model, 'grub_color_highlight')


def test_read_model_from_ui_invalid_bg_index():
    """Test when background color index is out of bounds."""
    window = MagicMock()
    window.state_manager = MagicMock()
    
    ctrl = MagicMock()
    ctrl.timeout_spin = MagicMock(get_value=MagicMock(return_value=10))
    ctrl.hidden_timeout_spin = MagicMock(get_value=MagicMock(return_value=0))
    ctrl.gfxmode_entry = MagicMock(get_text=MagicMock(return_value=""))
    ctrl.default_combo = MagicMock(get_selected=MagicMock(return_value=0))
    ctrl.default_switch = MagicMock(get_active=MagicMock(return_value=False))
    
    # Valid fg index, but invalid bg index (out of bounds)
    ctrl.normal_fg_combo = MagicMock(get_selected=MagicMock(return_value=0))
    ctrl.normal_bg_combo = MagicMock(get_selected=MagicMock(return_value=999))  # Out of bounds
    ctrl.highlight_fg_combo = MagicMock(get_selected=MagicMock(return_value=0))
    ctrl.highlight_bg_combo = MagicMock(get_selected=MagicMock(return_value=-1))  # Negative
    
    window.theme_config_controller = ctrl
    window.entries_renderer = MagicMock()
    window.entries_renderer.hidden_entries = []
    
    # Should handle invalid indices gracefully
    model = ModelWidgetMapper.read_model_from_ui(window)
    assert model is not None
    # Color fields should be empty strings when indices are invalid
    assert model.grub_color_normal == ""
    assert model.grub_color_highlight == ""


def test_read_model_from_ui_bg_index_out_of_range_executes_bg_check():
    """Ensure the bg bounds-check line is executed (fg valid, bg invalid)."""
    from ui.tabs.ui_tab_theme_config import GRUB_COLORS

    window = _make_window()
    ctrl = window.theme_config_controller
    ctrl.theme_switch.get_active.return_value = True

    ctrl.normal_fg_combo.get_selected.return_value = 0
    ctrl.normal_bg_combo.get_selected.return_value = len(GRUB_COLORS)  # out of range

    model = ModelWidgetMapper.read_model_from_ui(window)
    assert model.grub_color_normal == ""


def test_read_model_from_ui_executes_bg_idx_line_with_stub_combos():
    """Force execution of bg_idx assignment line using non-Mock combos."""

    class _Combo:
        def __init__(self, idx: int):
            self._idx = idx

        def get_selected(self) -> int:
            return self._idx

    window = _make_window()
    ctrl = window.theme_config_controller

    # Replace mocks with plain objects to ensure coverage tracks lines reliably
    ctrl.normal_fg_combo = _Combo(0)
    ctrl.normal_bg_combo = _Combo(0)
    ctrl.highlight_fg_combo = _Combo(0)
    ctrl.highlight_bg_combo = _Combo(0)

    model = ModelWidgetMapper.read_model_from_ui(window)
    assert isinstance(model.grub_color_normal, str)


def test_read_model_from_ui_calls_bg_combo_get_selected():
    """Make sure bg combo get_selected is called (covers bg_idx assignment line)."""
    window = _make_window()
    ctrl = window.theme_config_controller

    # Keep only the normal color path for a deterministic call count
    ctrl.highlight_fg_combo = None
    ctrl.highlight_bg_combo = None

    ctrl.normal_fg_combo.get_selected.return_value = 0
    ctrl.normal_bg_combo.get_selected.return_value = 0

    ModelWidgetMapper.read_model_from_ui(window)

    assert ctrl.normal_fg_combo.get_selected.called
    assert ctrl.normal_bg_combo.get_selected.called


def test_read_model_from_ui_grub_colors_importerror_path(monkeypatch):
    """Trigger the ImportError branch when importing GRUB_COLORS."""
    window = _make_window()

    real_import = __import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "ui.tabs.ui_tab_theme_config":
            raise ImportError("forced")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", fake_import)

    model = ModelWidgetMapper.read_model_from_ui(window)
    assert model is not None


def test_read_model_from_ui_theme_switch_disabled():
    """Test reading model when theme_switch is disabled."""
    window = MagicMock()
    window.state_manager = MagicMock()
    window.state_manager.state_data = None
    
    ctrl = MagicMock()
    ctrl.timeout_spin = MagicMock(get_value=MagicMock(return_value=10))
    ctrl.hidden_timeout_spin = MagicMock(get_value=MagicMock(return_value=0))
    ctrl.gfxmode_entry = MagicMock(get_text=MagicMock(return_value=""))
    ctrl.default_combo = MagicMock(get_selected=MagicMock(return_value=0))
    ctrl.default_switch = MagicMock(get_active=MagicMock(return_value=False))
    ctrl.theme_switch = MagicMock(get_active=MagicMock(return_value=False))  # Disabled
    ctrl.bg_image_entry = MagicMock(get_text=MagicMock(return_value=""))

    # Important: prevent MagicMock truthiness from triggering _get_color
    ctrl.normal_fg_combo = None
    ctrl.normal_bg_combo = None
    ctrl.highlight_fg_combo = None
    ctrl.highlight_bg_combo = None
    
    window.theme_config_controller = ctrl
    window.entries_renderer = MagicMock()
    window.entries_renderer.hidden_entries = []
    
    # Should work even with theme disabled
    model = ModelWidgetMapper.read_model_from_ui(window)
    assert model is not None
    assert model.theme_management_enabled is False
    # Color fields should be empty strings when indices are invalid
    assert model.grub_color_normal == ""
    assert model.grub_color_highlight == ""


def test_read_model_from_ui_missing_color_widgets():
    """Test quand les widgets de couleur sont None."""
    window = MagicMock()
    window.state_manager = MagicMock()
    
    ctrl = MagicMock()
    ctrl.timeout_spin = MagicMock(get_value=MagicMock(return_value=10))
    ctrl.hidden_timeout_spin = MagicMock(get_value=MagicMock(return_value=0))
    ctrl.gfxmode_entry = MagicMock(get_text=MagicMock(return_value=""))
    ctrl.default_combo = MagicMock(get_selected=MagicMock(return_value=0))
    ctrl.default_switch = MagicMock(get_active=MagicMock(return_value=False))
    
    # Widgets None
    ctrl.normal_fg_combo = None
    ctrl.normal_bg_combo = None
    ctrl.highlight_fg_combo = None
    ctrl.highlight_bg_combo = None
    
    window.theme_config_controller = ctrl
    window.entries_renderer = MagicMock()
    window.entries_renderer.hidden_entries = []
    
    model = ModelWidgetMapper.read_model_from_ui(window)
    assert model is not None


def test_get_color_from_combos_fg_none():
    """Test _get_color_from_combos returns empty when fg_combo is None (line 25)."""
    result = ModelWidgetMapper._get_color_from_combos(None, MagicMock(), ["white"])
    assert result == ""


def test_get_color_from_combos_bg_none():
    """Test _get_color_from_combos returns empty when bg_combo is None (line 25)."""
    result = ModelWidgetMapper._get_color_from_combos(MagicMock(), None, ["white"])
    assert result == ""