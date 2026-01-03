from unittest.mock import MagicMock, patch

import gi
import pytest

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from core.system.core_grub_system_commands import GrubDefaultChoice, GrubUiModel, GrubUiState
from core.system.core_sync_checker import SyncStatus
from ui.ui_manager import GrubConfigManager
from ui.ui_state import AppState, AppStateManager


# Subclass to bypass Gtk.ApplicationWindow.__init__ but allow create_ui
class GrubConfigManagerFull(GrubConfigManager):
    def __init__(self, application):
        # Bypass super().__init__ to avoid window creation
        self.application = application
        self.set_default_size = MagicMock()

        # Initialize attributes
        self.timeout_dropdown = MagicMock(spec=Gtk.DropDown)
        self.default_dropdown = MagicMock(spec=Gtk.DropDown)
        self.hidden_timeout_check = MagicMock(spec=Gtk.CheckButton)
        self.gfxmode_dropdown = MagicMock(spec=Gtk.DropDown)
        self.gfxpayload_dropdown = MagicMock(spec=Gtk.DropDown)
        self.terminal_color_check = MagicMock(spec=Gtk.CheckButton)
        self.disable_os_prober_check = MagicMock(spec=Gtk.CheckButton)
        self.entries_listbox = MagicMock(spec=Gtk.ListBox)
        self.maintenance_output = MagicMock(spec=Gtk.TextView)
        self.info_revealer = MagicMock(spec=Gtk.Revealer)
        self.info_box = MagicMock(spec=Gtk.Box)
        self.info_label = MagicMock(spec=Gtk.Label)
        self.reload_btn = MagicMock(spec=Gtk.Button)
        self.save_btn = MagicMock(spec=Gtk.Button)

        self.state_manager = MagicMock(spec=AppStateManager)
        self.state_manager.hidden_entry_ids = set()
        self.state_manager.state_data = MagicMock()
        self.state_manager.state_data.raw_config = {}
        self.state_manager.state_data.entries = []

        # Mock show_info to avoid UI interaction
        self.show_info = MagicMock()


@pytest.fixture
def mock_app():
    return MagicMock(spec=Gtk.Application)


@pytest.fixture
def manager(mock_app):
    with patch("ui.ui_manager.UIBuilder"):
        manager = GrubConfigManagerFull(mock_app)
        return manager


def test_create_ui(mock_app):
    with patch("ui.ui_manager.UIBuilder") as mock_builder:
        manager = GrubConfigManagerFull(mock_app)
        manager.create_ui()

        mock_builder.create_main_ui.assert_called_once_with(manager)
        manager.state_manager.apply_state.assert_called_with(AppState.CLEAN, manager.save_btn, manager.reload_btn)


def test_check_permissions_root(manager):
    with patch("os.geteuid", return_value=0):
        manager.check_permissions()
        manager.show_info.assert_not_called()


def test_check_permissions_non_root(manager):
    with patch("os.geteuid", return_value=1000):
        manager.check_permissions()
        manager.show_info.assert_called_once()
        args = manager.show_info.call_args[0]
        assert "nécessite les droits administrateur" in args[0]


def test_load_config_success(manager):
    sync_status = SyncStatus(
        in_sync=True,
        grub_default_exists=True,
        grub_cfg_exists=True,
        message="OK",
        grub_default_mtime=0,
        grub_cfg_mtime=0,
    )

    model = GrubUiModel(timeout=10, default="saved")
    entries = [GrubDefaultChoice(id="id1", title="Title 1")]
    state = GrubUiState(model=model, entries=entries, raw_config={})

    with (
        patch("ui.ui_manager.check_grub_sync", return_value=sync_status),
        patch("ui.ui_manager.load_grub_ui_state", return_value=state),
        patch("ui.ui_manager.render_entries_view") as mock_render,
        patch("ui.ui_gtk_helpers.GtkHelper.dropdown_set_value"),
    ):

        manager.load_config()

        manager.state_manager.update_state_data.assert_called_with(state)
        mock_render.assert_called_once_with(manager)
        manager.state_manager.apply_state.assert_called_with(AppState.CLEAN, manager.save_btn, manager.reload_btn)
        manager.default_dropdown.set_selected.assert_called()


def test_load_config_desync(manager):
    sync_status = SyncStatus(
        in_sync=False,
        grub_default_exists=True,
        grub_cfg_exists=True,
        message="Desync",
        grub_default_mtime=0,
        grub_cfg_mtime=0,
    )
    state = GrubUiState(model=GrubUiModel(), entries=[], raw_config={})

    with (
        patch("ui.ui_manager.check_grub_sync", return_value=sync_status),
        patch("ui.ui_manager.load_grub_ui_state", return_value=state),
        patch("ui.ui_manager.render_entries_view"),
    ):

        manager.load_config()

        manager.show_info.assert_any_call("⚠ Desync", "warning")


def test_load_config_hidden_timeout(manager):
    sync_status = SyncStatus(
        in_sync=True,
        grub_default_exists=True,
        grub_cfg_exists=True,
        message="OK",
        grub_default_mtime=0,
        grub_cfg_mtime=0,
    )
    model = GrubUiModel(hidden_timeout=True)
    state = GrubUiState(model=model, entries=[], raw_config={})

    with (
        patch("ui.ui_manager.check_grub_sync", return_value=sync_status),
        patch("ui.ui_manager.load_grub_ui_state", return_value=state),
        patch("ui.ui_manager.render_entries_view"),
    ):

        manager.load_config()

        # Check if any call contains the expected string in the first argument
        found = False
        target = "menu GRUB"
        for call in manager.show_info.call_args_list:
            args, _ = call
            if args and target in args[0]:
                found = True
                break
        assert found, f"Expected message containing '{target}' not found in {manager.show_info.call_args_list}"


def test_load_config_hidden_entries(manager):
    sync_status = SyncStatus(
        in_sync=True,
        grub_default_exists=True,
        grub_cfg_exists=True,
        message="OK",
        grub_default_mtime=0,
        grub_cfg_mtime=0,
    )
    model = GrubUiModel()
    state = GrubUiState(model=model, entries=[], raw_config={})

    manager.state_manager.hidden_entry_ids = {"entry1"}

    with (
        patch("ui.ui_manager.check_grub_sync", return_value=sync_status),
        patch("ui.ui_manager.load_grub_ui_state", return_value=state),
        patch("ui.ui_manager.render_entries_view"),
    ):

        manager.load_config()

        args_list = manager.show_info.call_args_list
        found = any("entrée(s) GRUB sont masquées" in str(call) for call in args_list)
        assert found


def test_read_model_from_ui(manager):
    manager.timeout_dropdown.get_model.return_value = MagicMock()

    with (
        patch("ui.ui_gtk_helpers.GtkHelper.dropdown_get_value", return_value="10"),
        patch.object(manager, "_get_timeout_value", return_value=10),
        patch.object(manager, "_get_default_choice", return_value="saved"),
    ):

        manager.hidden_timeout_check.get_active.return_value = True
        manager.disable_os_prober_check.get_active.return_value = False
        manager.terminal_color_check.get_active.return_value = True

        model = manager._read_model_from_ui()

        assert model.timeout == 10
        assert model.default == "saved"
        assert model.save_default is True
        assert model.hidden_timeout is True
        assert model.quiet is True


def test_apply_model_to_ui(manager):
    model = GrubUiModel(
        timeout=5,
        default="id1",
        hidden_timeout=True,
        gfxmode="1024x768",
        gfxpayload_linux="keep",
        disable_os_prober=True,
        quiet=True,
    )
    entries = [GrubDefaultChoice(id="id1", title="Title 1")]

    with (
        patch("ui.ui_gtk_helpers.GtkHelper.dropdown_set_value") as mock_set_val,
        patch.object(manager, "_sync_timeout_choices") as mock_sync_timeout,
        patch.object(manager, "_refresh_default_choices") as mock_refresh_defaults,
        patch.object(manager, "_set_default_choice") as mock_set_default,
    ):

        manager._apply_model_to_ui(model, entries)

        mock_sync_timeout.assert_called_with(5)
        manager.hidden_timeout_check.set_active.assert_called_with(True)

        mock_set_val.assert_any_call(manager.gfxmode_dropdown, "1024x768")
        mock_set_val.assert_any_call(manager.gfxpayload_dropdown, "keep")
        manager.disable_os_prober_check.set_active.assert_called_with(True)

        mock_refresh_defaults.assert_called_with(entries)
        mock_set_default.assert_called_with("id1")


def test_load_config_file_not_found(manager):
    with patch("ui.ui_manager.check_grub_sync", side_effect=FileNotFoundError("Missing")):
        manager.load_config()


def test_on_save_not_root(manager):
    with patch("os.geteuid", return_value=1000):
        manager.on_save(None)
        manager.show_info.assert_called_with("Droits administrateur requis pour enregistrer", "error")


def test_on_save_root_confirm(manager):
    with (
        patch("os.geteuid", return_value=0),
        patch("gi.repository.Gtk.AlertDialog") as MockDialog,
        patch.object(manager, "_perform_save") as mock_perform,
    ):

        mock_dlg_instance = MockDialog.return_value

        def side_effect_choose(parent, _, callback):
            mock_res = MagicMock()
            callback(mock_dlg_instance, mock_res)

        mock_dlg_instance.choose.side_effect = side_effect_choose
        mock_dlg_instance.choose_finish.return_value = 1

        manager.on_save(None)

        mock_perform.assert_called_once_with(apply_now=True)


def test_perform_save_success(manager):
    model = GrubUiModel(timeout=5, default="saved")

    with (
        patch.object(manager, "_read_model_from_ui", return_value=model),
        patch("ui.ui_manager.merged_config_from_model", return_value={}),
        patch("ui.ui_manager.GrubApplyManager") as MockApplyManager,
        patch("ui.ui_manager.read_grub_default", return_value={"GRUB_TIMEOUT": "5", "GRUB_DEFAULT": "saved"}),
        patch("ui.ui_manager.apply_hidden_entries_to_grub_cfg"),
    ):

        mock_apply_instance = MockApplyManager.return_value
        mock_apply_instance.apply_configuration.return_value = MagicMock(success=True, message="Success", details=None)

        manager._perform_save(apply_now=True)

        manager.state_manager.apply_state.assert_any_call(AppState.APPLYING, manager.save_btn, manager.reload_btn)
        manager.state_manager.apply_state.assert_any_call(AppState.CLEAN, manager.save_btn, manager.reload_btn)
        manager.show_info.assert_called_with("Success", "info")


def test_perform_save_failure(manager):
    model = GrubUiModel(timeout=5, default="saved")

    with (
        patch.object(manager, "_read_model_from_ui", return_value=model),
        patch("ui.ui_manager.merged_config_from_model", return_value={}),
        patch("ui.ui_manager.GrubApplyManager") as MockApplyManager,
    ):

        mock_apply_instance = MockApplyManager.return_value
        mock_apply_instance.apply_configuration.return_value = MagicMock(success=False, message="Some error")

        manager._perform_save(apply_now=True)

        manager.show_info.assert_called_with("Erreur: Some error", "error")


def test_on_reload_modified_confirm(manager):
    manager.state_manager.modified = True

    with patch("gi.repository.Gtk.AlertDialog") as MockDialog, patch.object(manager, "load_config") as mock_load:

        mock_dlg_instance = MockDialog.return_value

        def side_effect_choose(parent, _, callback):
            mock_res = MagicMock()
            callback(mock_dlg_instance, mock_res)

        mock_dlg_instance.choose.side_effect = side_effect_choose
        mock_dlg_instance.choose_finish.return_value = 1

        manager.on_reload(None)

        mock_load.assert_called_once()
        manager.show_info.assert_called_with("Configuration rechargée", "info")


def test_on_reload_clean(manager):
    manager.state_manager.modified = False

    with patch.object(manager, "load_config") as mock_load:
        manager.on_reload(None)
        mock_load.assert_called_once()
