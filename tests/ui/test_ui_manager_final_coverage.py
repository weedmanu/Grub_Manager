from unittest.mock import MagicMock, patch

import pytest
from gi.repository import GLib

from ui.ui_manager import GrubConfigManager

INFO = "info"
WARNING = "warning"
ERROR = "error"


@pytest.fixture
def ui_manager():
    # Subclass to bypass Gtk.ApplicationWindow.__init__
    class TestGrubConfigManager(GrubConfigManager):
        def __init__(self, application):
            self.application = application
            self.state_manager = MagicMock()
            self.default_dropdown = MagicMock()
            self.timeout_dropdown = MagicMock()
            self.info_revealer = MagicMock()
            self.info_label = MagicMock()
            self.info_box = MagicMock()
            self.save_btn = MagicMock()
            self.reload_btn = MagicMock()
            self.hidden_timeout_check = MagicMock()
            self.gfxmode_dropdown = MagicMock()
            self.gfxpayload_dropdown = MagicMock()
            self.disable_os_prober_check = MagicMock()
            self.terminal_color_check = MagicMock()

    with patch("ui.ui_manager.UIBuilder"), patch("ui.ui_manager.AppState"), patch("ui.ui_manager.AppStateManager"):
        manager = TestGrubConfigManager(MagicMock())
        return manager


def test_ensure_timeout_choice_new_value(ui_manager):
    """Test _ensure_timeout_choice when adding a new value."""
    # Setup
    model = MagicMock()
    # Setup existing items: "1", "5", "10"
    model.get_n_items.return_value = 3
    model.get_string.side_effect = lambda i: ["1", "5", "10"][i]

    ui_manager.timeout_dropdown.get_model.return_value = model

    # Execute with a value not in the list ("3" should be inserted between "1" and "5", so index 1)
    ui_manager._ensure_timeout_choice("3")

    # Verify splice was called: index 1, remove 0, add ["3"]
    model.splice.assert_called_with(1, 0, ["3"])


def test_ensure_timeout_choice_exception(ui_manager):
    """Test _ensure_timeout_choice when splice raises exception."""
    model = MagicMock()
    model.get_n_items.return_value = 3
    model.get_string.side_effect = lambda i: ["1", "5", "10"][i]

    # Make splice raise an exception to trigger the fallback
    model.splice.side_effect = TypeError("Splice failed")

    ui_manager.timeout_dropdown.get_model.return_value = model

    # Call with new value
    ui_manager._ensure_timeout_choice("3")

    # Verify fallback to append was called
    model.append.assert_called_with("3")


def test_on_hidden_timeout_toggled_inactive(ui_manager):
    """Test on_hidden_timeout_toggled when widget is inactive."""
    ui_manager.state_manager.is_loading.return_value = False
    widget = MagicMock()
    widget.get_active.return_value = False
    ui_manager.on_modified = MagicMock()

    ui_manager.on_hidden_timeout_toggled(widget)

    # Should NOT call _sync_timeout_choices
    # But SHOULD call on_modified
    ui_manager.on_modified.assert_called_with(widget)


def test_on_reload_confirmed_explicit(ui_manager):
    """Explicitly test the confirmation path of on_reload."""
    ui_manager.state_manager.modified = True
    ui_manager.load_config = MagicMock()

    with patch("gi.repository.Gtk.AlertDialog") as MockDialog:
        dlg = MockDialog.return_value

        # Setup the callback execution
        def side_effect(parent, _, callback):
            # Simulate callback with result 1
            callback(dlg, 1)

        dlg.choose.side_effect = side_effect
        dlg.choose_finish.return_value = 1

        ui_manager.on_reload(None)

        # Verify load_config was called
        ui_manager.load_config.assert_called_once()


def test_perform_save_verification_mismatch(ui_manager):
    """Test _perform_save when verification fails."""
    ui_manager.state_manager.apply_state = MagicMock()
    ui_manager._read_model_from_ui = MagicMock()
    ui_manager.show_info = MagicMock()

    # Mock successful apply
    with (
        patch("ui.ui_manager.merged_config_from_model"),
        patch("ui.ui_manager.GrubApplyManager") as MockApplyManager,
        patch("ui.ui_manager.read_grub_default") as mock_read,
        patch("ui.ui_manager.apply_hidden_entries_to_grub_cfg"),
    ):

        apply_manager = MockApplyManager.return_value
        apply_manager.apply_configuration.return_value.success = True
        apply_manager.apply_configuration.return_value.message = "Success"
        apply_manager.apply_configuration.return_value.details = ""

        # Mock read_grub_default to return mismatched values
        mock_read.return_value = {"GRUB_TIMEOUT": "999", "GRUB_DEFAULT": "wrong"}

        # Execute
        ui_manager._perform_save(apply_now=True)

        # We can't easily assert the log message, but we can ensure it didn't crash
        # and that show_info was called with success (since verification failure is just a warning)
        ui_manager.show_info.assert_called()
        args = ui_manager.show_info.call_args[0]
        assert "Success" in args[0]


def test_hide_info_callback_none_revealer(ui_manager):
    """Test _hide_info_callback when revealer is None."""
    ui_manager.info_revealer = None
    result = ui_manager._hide_info_callback()
    assert result is False


def test_set_default_choice_exception(ui_manager):
    """Test _set_default_choice when model.append raises exception."""
    ui_manager.state_manager.get_default_choice_ids.return_value = ["0"]
    model = MagicMock()
    model.append.side_effect = Exception("Append failed")
    ui_manager.default_dropdown.get_model.return_value = model

    # Call with a value not in the list
    ui_manager._set_default_choice("new_value")

    # Should fall back to selecting 0
    ui_manager.default_dropdown.set_selected.assert_called_with(0)


def test_on_hidden_timeout_toggled_loading(ui_manager):
    """Test on_hidden_timeout_toggled when loading is in progress."""
    ui_manager.state_manager.is_loading.return_value = True
    widget = MagicMock()

    ui_manager.on_hidden_timeout_toggled(widget)

    # Should return early and not call get_active
    widget.get_active.assert_not_called()


def test_on_reload_dialog_glib_error(ui_manager):
    """Test on_reload when dialog raises GLib.Error."""
    ui_manager.state_manager.modified = True

    with patch("ui.ui_manager.Gtk.AlertDialog") as MockDialog:
        dialog_instance = MockDialog.return_value

        # Simulate dialog choice callback
        def side_effect(parent, _, callback):
            # Create a mock dialog that raises GLib.Error on choose_finish
            mock_dlg = MagicMock()
            mock_dlg.choose_finish.side_effect = GLib.Error("Cancelled")
            callback(mock_dlg, MagicMock())

        dialog_instance.choose.side_effect = side_effect

        ui_manager.on_reload(MagicMock())

        # Should catch error and not reload
        # load_config is mocked in fixture? No, it's a method on ui_manager.
        # We need to mock load_config to verify it's NOT called
        # But ui_manager is a real object (with mocked dependencies).
        # We can patch load_config on the instance.
        with patch.object(ui_manager, "load_config") as mock_load:
            ui_manager.on_reload(MagicMock())
            mock_load.assert_not_called()


def test_perform_save_verification_exception(ui_manager):
    """Test _perform_save when verification raises exception."""
    # Setup successful save
    with (
        patch("ui.ui_manager.GrubApplyManager") as MockApplyManager,
        patch("ui.ui_manager.read_grub_default") as mock_read,
    ):

        manager_instance = MockApplyManager.return_value
        manager_instance.apply_configuration.return_value.success = True
        manager_instance.apply_configuration.return_value.message = "Success"

        # Verification raises exception
        mock_read.side_effect = Exception("Read failed")

        ui_manager._perform_save(apply_now=True)

        # Should still show success message (warning logged)
        # Verify show_info called with INFO (not ERROR)
        args, _ = ui_manager.info_label.set_text.call_args
        assert "Success" in args[0]


def test_show_info_missing_widgets(ui_manager):
    """Test show_info when widgets are None."""
    # Case 1: info_box is None
    ui_manager.info_box = None
    ui_manager.show_info("Message", INFO)
    # Should return early (no crash)

    # Case 2: info_revealer is None
    ui_manager.info_box = MagicMock()  # Restore info_box
    ui_manager.info_revealer = None
    ui_manager.show_info("Message", INFO)
    # Should return early

    # Case 3: info_label is None
    ui_manager.info_label = None
    ui_manager.show_info("Message", INFO)
    # Should return early


def test_set_default_choice_model_none(ui_manager):
    """Test _set_default_choice when dropdown model is None."""
    ui_manager.default_dropdown.get_model.return_value = None

    ui_manager._set_default_choice("some_value")

    # Should fall through to setting selected to 0
    ui_manager.default_dropdown.set_selected.assert_called_with(0)


def test_on_reload_dialog_glib_error_coverage(ui_manager):
    """Test on_reload when dialog raises GLib.Error (coverage focus)."""
    ui_manager.state_manager.modified = True

    with patch("ui.ui_manager.Gtk.AlertDialog") as MockDialog:
        dialog_instance = MockDialog.return_value

        def side_effect(parent, _, callback):
            mock_dlg = MagicMock()
            # Ensure this raises the specific GLib.Error that the except block catches
            mock_dlg.choose_finish.side_effect = GLib.Error("Cancelled")
            callback(mock_dlg, MagicMock())

        dialog_instance.choose.side_effect = side_effect

        # We want to ensure the logger.debug line is hit.
        with patch("ui.ui_manager.logger") as mock_logger:
            ui_manager.on_reload(MagicMock())

            # Verify that the specific debug message was logged
            found = False
            for call in mock_logger.debug.call_args_list:
                if "Dialog cancelled" in str(call):
                    found = True
                    break
            assert found, "Did not catch GLib.Error in on_reload"


def test_on_save_dialog_glib_error_coverage(ui_manager):
    """Test on_save when dialog raises GLib.Error (coverage focus)."""
    # Must be root
    with patch("os.geteuid", return_value=0):
        with patch("ui.ui_manager.Gtk.AlertDialog") as MockDialog:
            dialog_instance = MockDialog.return_value

            def side_effect(parent, _, callback):
                mock_dlg = MagicMock()
                mock_dlg.choose_finish.side_effect = GLib.Error("Cancelled")
                callback(mock_dlg, MagicMock())

            dialog_instance.choose.side_effect = side_effect

            with patch("ui.ui_manager.logger") as mock_logger:
                ui_manager.on_save(MagicMock())

                found = False
                for call in mock_logger.debug.call_args_list:
                    if "Dialog cancelled" in str(call):
                        found = True
                        break
                assert found, "Did not catch GLib.Error in on_save"


def test_hide_info_callback_none_revealer_coverage(ui_manager):
    """Test _hide_info_callback when revealer is None."""
    ui_manager.info_revealer = None
    assert ui_manager._hide_info_callback() is False


def test_show_info_revealer_exists_coverage(ui_manager):
    """Test show_info when revealer exists (branch coverage)."""
    ui_manager.info_revealer = MagicMock()
    ui_manager.info_box = MagicMock()
    ui_manager.info_label = MagicMock()

    with patch("ui.ui_manager.GLib.timeout_add_seconds") as mock_timeout:
        ui_manager.show_info("msg", INFO)

        ui_manager.info_revealer.set_reveal_child.assert_called_with(True)
        mock_timeout.assert_called_once()


def test_perform_save_hidden_entries_exception_coverage(ui_manager):
    """Test _perform_save when hidden entries application fails."""
    ui_manager.state_manager.apply_state = MagicMock()
    ui_manager._read_model_from_ui = MagicMock()
    ui_manager.show_info = MagicMock()

    # Ensure hidden entries are present so the block is entered
    ui_manager.state_manager.hidden_entry_ids = {"entry1"}

    with (
        patch("ui.ui_manager.merged_config_from_model"),
        patch("ui.ui_manager.GrubApplyManager") as MockApplyManager,
        patch("ui.ui_manager.read_grub_default"),
        patch("ui.ui_manager.apply_hidden_entries_to_grub_cfg") as mock_apply,
    ):

        apply_manager = MockApplyManager.return_value
        apply_manager.apply_configuration.return_value.success = True
        apply_manager.apply_configuration.return_value.message = "Success"

        # Make apply_hidden_entries_to_grub_cfg raise exception
        mock_apply.side_effect = Exception("Hidden entries failed")

        ui_manager._perform_save(apply_now=True)

        # Verify warning message
        args, _ = ui_manager.show_info.call_args
        assert "Masquage échoué" in args[0]
        assert args[1] == WARNING
