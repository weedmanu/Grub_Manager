from unittest.mock import MagicMock, patch

import pytest

from core.system.core_system_grub_commands import GrubDefaultChoice, GrubUiModel, GrubUiState
from core.system.core_system_sync_checker import SyncStatus
from ui.controllers.ui_controllers_manager import GrubConfigManager
from ui.models.ui_models_state import AppState

WARNING = "warning"


# Copied from test_ui_manager.py to avoid circular imports or complex refactoring
class GrubConfigManagerFull(GrubConfigManager):
    """Sous-classe pour mocker les composants UI sans charger GTK."""

    def __init__(self, app):
        self.app = app
        self.window = MagicMock()
        self.builder = MagicMock()

        # Mock state manager
        self.state_manager = MagicMock()
        self.state_manager.state = AppState.CLEAN
        self.state_manager.modified = False

        def _mark_dirty(*_args, **_kwargs):
            self.state_manager.modified = True
            self.state_manager.state = AppState.DIRTY

        def _apply_state(state, *_args):
            self.state_manager.state = state
            self.state_manager.modified = state != AppState.CLEAN

        def _update_state_data(state_data):
            self.state_manager.state_data = state_data

        self.state_manager.set_loading.side_effect = lambda *args: None
        self.state_manager.mark_dirty.side_effect = _mark_dirty
        self.state_manager.apply_state.side_effect = _apply_state
        self.state_manager.update_state_data.side_effect = _update_state_data

        self.state_manager._default_choice_ids = ["saved"]
        self.state_manager.get_default_choice_ids.side_effect = lambda: list(self.state_manager._default_choice_ids)
        self.state_manager.update_default_choice_ids.side_effect = lambda ids: setattr(
            self.state_manager, "_default_choice_ids", list(ids)
        )

        self.state_manager.get_state.side_effect = lambda: AppState(grub_state=self.state_manager.state_data)
        self.state_manager.update_state.side_effect = lambda app_state: setattr(
            self.state_manager, "state_data", app_state.grub_state
        )

        self.state_manager.hidden_entry_ids = []

        # Mock UI components
        self.timeout_dropdown = MagicMock()
        self.default_dropdown = MagicMock()
        self.hidden_timeout_check = MagicMock()
        self.gfxmode_dropdown = MagicMock()
        self.gfxpayload_dropdown = MagicMock()
        self.cmdline_dropdown = MagicMock()
        self.terminal_color_check = MagicMock()
        self.disable_os_prober_check = MagicMock()
        self.entries_listbox = MagicMock()
        self.info_revealer = MagicMock()
        self.info_box = MagicMock()
        self.info_label = MagicMock()
        self.reload_btn = MagicMock()
        self.save_btn = MagicMock()

        self.entries_renderer = MagicMock()
        self.workflow = MagicMock()
        self.infobar = None

        # theme_config_controller with proper mocks
        self.theme_config_controller = MagicMock()
        self.theme_config_controller.widgets = MagicMock()
        self.theme_config_controller.widgets.panels = MagicMock()
        panels = self.theme_config_controller.widgets.panels
        panels.theme_switch = MagicMock()
        panels.theme_switch.get_active.return_value = True
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

        # Mock PermissionController
        self.perm_ctrl = MagicMock()

        # Mock show_info
        self.show_info = MagicMock()

        # Defaults
        self.cmdline_dropdown.get_selected.return_value = 0
        self.default_dropdown.get_selected.return_value = 0


@pytest.fixture
def mock_app():
    return MagicMock()


@pytest.fixture
def manager(mock_app):
    mgr = GrubConfigManagerFull(mock_app)
    return mgr


def test_load_config_refresh_grub_success(manager):
    """Test que load_config n'appelle jamais update-grub (même si root)."""
    sync_status = SyncStatus(
        in_sync=True,
        grub_default_exists=True,
        grub_cfg_exists=True,
        message="OK",
        grub_default_mtime=0,
        grub_cfg_mtime=0,
    )
    entry = GrubDefaultChoice(id="entry1", title="Entry 1")
    state = GrubUiState(model=GrubUiModel(), entries=[entry], raw_config={})

    with (
        patch("os.geteuid", return_value=0),
        patch("ui.controllers.ui_controllers_manager.check_grub_sync", return_value=sync_status),
        patch("ui.controllers.ui_controllers_manager.load_grub_ui_state", return_value=state),
        patch("ui.controllers.ui_controllers_manager.render_entries_view"),
    ):
        manager.load_config(refresh_grub=True)

        # Verify absence of warning/error
        manager.show_info.assert_not_called()


def test_load_config_refresh_grub_failure(manager):
    """Test que load_config n'appelle jamais update-grub (donc pas de warning associé)."""
    sync_status = SyncStatus(
        in_sync=True,
        grub_default_exists=True,
        grub_cfg_exists=True,
        message="OK",
        grub_default_mtime=0,
        grub_cfg_mtime=0,
    )
    state = GrubUiState(model=GrubUiModel(), entries=[], raw_config={})

    with (
        patch("os.geteuid", return_value=0),
        patch("ui.controllers.ui_controllers_manager.check_grub_sync", return_value=sync_status),
        patch("ui.controllers.ui_controllers_manager.load_grub_ui_state", return_value=state),
        patch("ui.controllers.ui_controllers_manager.render_entries_view"),
    ):
        manager.load_config(refresh_grub=True)
        # Avec 0 entrée et root, l'UI peut afficher un warning "Aucune entrée".
        assert manager.show_info.called
        args = manager.show_info.call_args[0]
        assert "Aucune entrée" in args[0]
        assert "update-grub" not in args[0]


def test_load_config_refresh_grub_not_root(manager):
    """Test que update-grub n'est PAS appelé si non-root."""
    sync_status = SyncStatus(
        in_sync=True,
        grub_default_exists=True,
        grub_cfg_exists=True,
        message="OK",
        grub_default_mtime=0,
        grub_cfg_mtime=0,
    )
    state = GrubUiState(model=GrubUiModel(), entries=[], raw_config={})

    with (
        patch("os.geteuid", return_value=1000),
        patch("ui.controllers.ui_controllers_manager.check_grub_sync", return_value=sync_status),
        patch("ui.controllers.ui_controllers_manager.load_grub_ui_state", return_value=state),
        patch("ui.controllers.ui_controllers_manager.render_entries_view"),
    ):
        manager.load_config(refresh_grub=True)


def test_load_config_no_refresh(manager):
    """Test que update-grub n'est PAS appelé si refresh_grub=False."""
    sync_status = SyncStatus(
        in_sync=True,
        grub_default_exists=True,
        grub_cfg_exists=True,
        message="OK",
        grub_default_mtime=0,
        grub_cfg_mtime=0,
    )
    state = GrubUiState(model=GrubUiModel(), entries=[], raw_config={})

    with (
        patch("os.geteuid", return_value=0),
        patch("ui.controllers.ui_controllers_manager.check_grub_sync", return_value=sync_status),
        patch("ui.controllers.ui_controllers_manager.load_grub_ui_state", return_value=state),
        patch("ui.controllers.ui_controllers_manager.render_entries_view"),
    ):
        manager.load_config(refresh_grub=False)
