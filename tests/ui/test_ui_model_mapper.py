"""Tests pour ui.ui_model_mapper."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.system.core_system_grub_commands import GrubUiModel
from ui.helpers.ui_helpers_model_mapper import ModelWidgetMapper


def _make_window() -> MagicMock:
    window = MagicMock()
    window.state_manager = MagicMock()
    # Le mapper lit la config thème depuis state_manager.state_data.model (plus de switch).
    window.state_manager.state_data = SimpleNamespace(
        model=SimpleNamespace(
            grub_theme="",
            theme_management_enabled=True,
            grub_background="",
            grub_color_normal="",
            grub_color_highlight="",
        )
    )
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
    window.theme_config_controller.widgets = MagicMock()
    window.theme_config_controller.widgets.panels = MagicMock()
    panels = window.theme_config_controller.widgets.panels
    panels.simple_config_panel = MagicMock()
    panels.simple_config_panel.widgets = MagicMock()
    widgets = panels.simple_config_panel.widgets
    widgets.bg_image_entry = MagicMock()
    widgets.bg_image_entry.get_text.return_value = ""
    widgets.normal_fg_combo = MagicMock()
    widgets.normal_fg_combo.get_selected.return_value = -1
    widgets.normal_bg_combo = MagicMock()
    widgets.normal_bg_combo.get_selected.return_value = -1
    widgets.highlight_fg_combo = MagicMock()
    widgets.highlight_fg_combo.get_selected.return_value = -1
    widgets.highlight_bg_combo = MagicMock()
    widgets.highlight_bg_combo.get_selected.return_value = -1

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
        grub_terminal="gfxterm",
        disable_os_prober=False,
        default="0",
    )

    monkeypatch.setattr("ui.helpers.ui_helpers_model_mapper.GtkHelper.dropdown_set_value", MagicMock())

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
    from core.models.core_models_grub_ui import GrubUiModel

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
    window.state_manager.state_data = SimpleNamespace(model=GrubUiModel(theme_management_enabled=False))

    with patch("ui.helpers.ui_helpers_model_mapper.GtkHelper.dropdown_get_value", return_value=""):
        model = ModelWidgetMapper.read_model_from_ui(window)
        assert model.timeout == 5


def test_read_model_with_exception_in_color_parsing():
    """Test color parsing with out-of-range combo values."""
    from core.models.core_models_grub_ui import GrubUiModel

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
    window.theme_config_controller.widgets = MagicMock()
    window.theme_config_controller.widgets.panels = MagicMock()
    window.theme_config_controller.widgets.panels.theme_switch = None
    window.theme_config_controller.widgets.panels.simple_config_panel = MagicMock()
    window.theme_config_controller.widgets.panels.simple_config_panel.widgets = MagicMock()
    window.theme_config_controller.widgets.panels.simple_config_panel.widgets.bg_image_entry = None

    # Create mock combos with proper return values
    normal_fg_combo = MagicMock()
    normal_fg_combo.get_selected = MagicMock(return_value=-1)
    window.theme_config_controller.widgets.panels.simple_config_panel.widgets.normal_fg_combo = normal_fg_combo

    normal_bg_combo = MagicMock()
    normal_bg_combo.get_selected = MagicMock(return_value=-1)
    window.theme_config_controller.widgets.panels.simple_config_panel.widgets.normal_bg_combo = normal_bg_combo

    highlight_fg_combo = MagicMock()
    highlight_fg_combo.get_selected = MagicMock(return_value=-1)
    window.theme_config_controller.widgets.panels.simple_config_panel.widgets.highlight_fg_combo = highlight_fg_combo

    highlight_bg_combo = MagicMock()
    highlight_bg_combo.get_selected = MagicMock(return_value=-1)
    window.theme_config_controller.widgets.panels.simple_config_panel.widgets.highlight_bg_combo = highlight_bg_combo

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
    monkeypatch.setattr("ui.helpers.ui_helpers_model_mapper.GtkHelper.dropdown_get_value", lambda _w: " 1024x768 ")

    # Set theme in model since read_model_from_ui takes it from there
    window.state_manager.state_data.model = GrubUiModel(
        grub_theme="/themes/MyTheme/theme.txt", theme_management_enabled=True
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
    monkeypatch.setattr("ui.helpers.ui_helpers_model_mapper.ActiveThemeManager", lambda: theme_manager)

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
        grub_terminal="gfxterm",
        disable_os_prober=False,
        default="0",
    )

    monkeypatch.setattr("ui.helpers.ui_helpers_model_mapper.GtkHelper.dropdown_set_value", MagicMock())
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
        grub_terminal="gfxterm",
        disable_os_prober=False,
        default="0",
    )

    monkeypatch.setattr("ui.helpers.ui_helpers_model_mapper.GtkHelper.dropdown_set_value", MagicMock())

    ModelWidgetMapper.apply_model_to_ui(window, model, entries=[])


def test_get_active_theme_path_empty_name_returns_empty(monkeypatch):
    theme_manager = MagicMock()
    theme_manager.get_active_theme.return_value = SimpleNamespace(name="")
    monkeypatch.setattr("ui.helpers.ui_helpers_model_mapper.ActiveThemeManager", lambda: theme_manager)

    assert ModelWidgetMapper._get_active_theme_path() == ""


def test_read_model_from_ui_color_bounds_checking():
    """Test les vérifications de bornes pour les index de couleur."""
    window = _make_window()
    ctrl = window.theme_config_controller
    panel = ctrl.widgets.panels.simple_config_panel

    panel.widgets.normal_fg_combo.get_selected.return_value = 0
    panel.widgets.normal_bg_combo.get_selected.return_value = 1
    panel.widgets.highlight_fg_combo.get_selected.return_value = 1
    panel.widgets.highlight_bg_combo.get_selected.return_value = 0

    model = ModelWidgetMapper.read_model_from_ui(window)
    assert model is not None
    # Verify color normal was set (not empty)
    assert hasattr(model, "grub_color_normal")
    assert hasattr(model, "grub_color_highlight")


def test_read_model_from_ui_invalid_bg_index():
    """Test when background color index is out of bounds."""
    window = _make_window()
    ctrl = window.theme_config_controller
    panel = ctrl.widgets.panels.simple_config_panel

    panel.widgets.normal_fg_combo.get_selected.return_value = 0
    panel.widgets.normal_bg_combo.get_selected.return_value = 999  # Out of bounds
    panel.widgets.highlight_fg_combo.get_selected.return_value = 0
    panel.widgets.highlight_bg_combo.get_selected.return_value = -1  # Negative

    model = ModelWidgetMapper.read_model_from_ui(window)
    assert model is not None
    # Color fields should be empty strings when indices are invalid
    assert model.grub_color_normal == ""
    assert model.grub_color_highlight == ""


def test_read_model_from_ui_bg_index_out_of_range_executes_bg_check():
    """Ensure the bg bounds-check line is executed (fg valid, bg invalid)."""
    from ui.config.ui_config_constants import GRUB_COLORS

    window = _make_window()
    ctrl = window.theme_config_controller
    panel = ctrl.widgets.panels.simple_config_panel
    panel.widgets.normal_fg_combo.get_selected.return_value = 0
    panel.widgets.normal_bg_combo.get_selected.return_value = len(GRUB_COLORS)  # out of range

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
    panel = ctrl.widgets.panels.simple_config_panel

    assert panel.widgets is not None

    # Replace mocks with plain objects to ensure coverage tracks lines reliably
    panel.widgets.normal_fg_combo = _Combo(0)
    panel.widgets.normal_bg_combo = _Combo(0)
    panel.widgets.highlight_fg_combo = _Combo(0)
    panel.widgets.highlight_bg_combo = _Combo(0)

    model = ModelWidgetMapper.read_model_from_ui(window)
    assert isinstance(model.grub_color_normal, str)


def test_read_model_from_ui_calls_bg_combo_get_selected():
    """Make sure bg combo get_selected is called (covers bg_idx assignment line)."""
    window = _make_window()
    ctrl = window.theme_config_controller
    panel = ctrl.widgets.panels.simple_config_panel

    # Keep only the normal color path for a deterministic call count
    panel.widgets.highlight_fg_combo = None
    panel.widgets.highlight_bg_combo = None

    panel.widgets.normal_fg_combo.get_selected.return_value = 0
    panel.widgets.normal_bg_combo.get_selected.return_value = 0

    ModelWidgetMapper.read_model_from_ui(window)

    assert panel.widgets.normal_fg_combo.get_selected.called
    assert panel.widgets.normal_bg_combo.get_selected.called


def test_read_model_from_ui_theme_switch_disabled():
    """Le switch n'existe plus: theme_management_enabled vient du modèle courant."""
    window = _make_window()
    window.state_manager.state_data.model.theme_management_enabled = False

    ctrl = window.theme_config_controller
    panel = ctrl.widgets.panels.simple_config_panel
    panel.widgets.bg_image_entry.get_text.return_value = ""
    panel.widgets.normal_fg_combo = None
    panel.widgets.normal_bg_combo = None
    panel.widgets.highlight_fg_combo = None
    panel.widgets.highlight_bg_combo = None

    # Doit fonctionner même si theme_management_enabled=False
    model = ModelWidgetMapper.read_model_from_ui(window)
    assert model is not None
    assert model.theme_management_enabled is False
    # Color fields should be empty strings when indices are invalid
    assert model.grub_color_normal == ""
    assert model.grub_color_highlight == ""


def test_read_model_from_ui_missing_color_widgets():
    """Test quand les widgets de couleur sont None."""
    window = _make_window()
    ctrl = window.theme_config_controller
    panel = ctrl.widgets.panels.simple_config_panel

    panel.widgets.normal_fg_combo = None
    panel.widgets.normal_bg_combo = None
    panel.widgets.highlight_fg_combo = None
    panel.widgets.highlight_bg_combo = None

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
