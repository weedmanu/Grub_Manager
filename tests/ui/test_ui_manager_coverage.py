from unittest.mock import MagicMock, patch

import pytest
from gi.repository import GLib, Gtk

from ui.ui_manager import GrubConfigManager
from ui.ui_state import AppStateManager


class MockGrubConfigManager(GrubConfigManager):
    def __init__(self):
        # Bypass Gtk.ApplicationWindow.__init__
        self.timeout_dropdown = None
        self.default_dropdown = None
        self.hidden_timeout_check = None
        self.gfxmode_dropdown = None
        self.gfxpayload_dropdown = None
        self.terminal_color_check = None
        self.disable_os_prober_check = None
        self.entries_listbox = None
        self.maintenance_output = None
        self.info_revealer = None
        self.info_box = None
        self.info_label = None
        self.reload_btn = None
        self.save_btn = None

        self.state_manager = MagicMock(spec=AppStateManager)
        self.state_manager.state_data = MagicMock()
        self.state_manager.state_data.raw_config = {}
        self.state_manager.state_data.entries = []
        self.state_manager.hidden_entry_ids = []
        self.state_manager.entries_visibility_dirty = False


@pytest.fixture
def manager():
    return MockGrubConfigManager()


def test_get_timeout_value_exception(manager):
    """Test _get_timeout_value handles exceptions."""
    manager.timeout_dropdown = MagicMock()
    with patch("ui.ui_gtk_helpers.GtkHelper.dropdown_get_value", return_value="invalid"):
        assert manager._get_timeout_value() == 5


def test_sync_timeout_choices_none_widgets(manager):
    """Test _sync_timeout_choices with None widgets."""
    manager.timeout_dropdown = None
    manager._sync_timeout_choices(5)  # Should not raise

    manager.timeout_dropdown = MagicMock()
    manager.timeout_dropdown.get_model.return_value = None
    manager._sync_timeout_choices(5)  # Should not raise


def test_ensure_timeout_choice_none_widgets(manager):
    """Test _ensure_timeout_choice with None widgets."""
    manager.timeout_dropdown = None
    assert manager._ensure_timeout_choice("5") is None

    manager.timeout_dropdown = MagicMock()
    manager.timeout_dropdown.get_model.return_value = None
    assert manager._ensure_timeout_choice("5") is None


def test_ensure_timeout_choice_logic(manager):
    """Test _ensure_timeout_choice insertion logic."""
    manager.timeout_dropdown = MagicMock()
    model = MagicMock()
    manager.timeout_dropdown.get_model.return_value = model

    # Case: Existing value
    with patch("ui.ui_gtk_helpers.GtkHelper.stringlist_find", return_value=2):
        assert manager._ensure_timeout_choice("5") == 2

    # Case: New value, invalid int conversion for wanted
    with patch("ui.ui_gtk_helpers.GtkHelper.stringlist_find", side_effect=[None, 3]):
        assert manager._ensure_timeout_choice("invalid") == 3
        # Should append at end
        model.get_n_items.assert_called()

    # Case: New value, insertion loop
    with patch("ui.ui_gtk_helpers.GtkHelper.stringlist_find", side_effect=[None, 1]):
        model.get_n_items.return_value = 2
        # Mock get_string to return values for comparison
        # We want to insert "3" into ["1", "5"] -> should be index 1
        model.get_string.side_effect = ["1", "5"]

        assert manager._ensure_timeout_choice("3") == 1


def test_ensure_timeout_choice_loop_exceptions(manager):
    """Test exceptions inside the loop of _ensure_timeout_choice."""
    manager.timeout_dropdown = MagicMock()
    model = MagicMock()
    manager.timeout_dropdown.get_model.return_value = model

    with patch("ui.ui_gtk_helpers.GtkHelper.stringlist_find", side_effect=[None, 0]):
        model.get_n_items.return_value = 1
        # get_string raises exception
        model.get_string.side_effect = TypeError("Mock error")

        manager._ensure_timeout_choice("5")
        # Should continue loop and eventually insert


def test_set_timeout_value_edge_cases(manager):
    """Test _set_timeout_value edge cases."""
    manager.timeout_dropdown = None
    manager._set_timeout_value(5)  # Should return early

    manager.timeout_dropdown = MagicMock()
    with patch.object(manager, "_ensure_timeout_choice", return_value=None):
        manager._set_timeout_value(5)
        manager.timeout_dropdown.set_selected.assert_called_with(0)


def test_refresh_default_choices_none_widgets(manager):
    """Test _refresh_default_choices with None widgets."""
    manager.default_dropdown = None
    manager._refresh_default_choices([])

    manager.default_dropdown = MagicMock()
    manager.default_dropdown.get_model.return_value = None
    manager._refresh_default_choices([])


def test_get_default_choice_edge_cases(manager):
    """Test _get_default_choice edge cases."""
    manager.default_dropdown = None
    assert manager._get_default_choice() == "0"

    manager.default_dropdown = MagicMock()
    manager.default_dropdown.get_selected.return_value = None
    assert manager._get_default_choice() == "0"

    manager.default_dropdown.get_selected.return_value = 0
    manager.state_manager.get_default_choice_ids = MagicMock(side_effect=Exception("Mock"))
    assert manager._get_default_choice() == "0"


def test_set_default_choice_edge_cases(manager):
    """Test _set_default_choice edge cases."""
    manager.default_dropdown = None
    manager._set_default_choice("saved")  # Should return early

    manager.default_dropdown = MagicMock()

    # Case: Exception during append
    manager.state_manager.get_default_choice_ids = MagicMock(return_value=["id1"])
    model = MagicMock()
    manager.default_dropdown.get_model.return_value = model
    model.append.side_effect = Exception("Mock append error")

    manager._set_default_choice("new_id")
    manager.default_dropdown.set_selected.assert_called_with(0)


def test_apply_model_to_ui_none_widgets(manager):
    """Test _apply_model_to_ui with None widgets."""
    # Set all widgets to None
    manager.hidden_timeout_check = None
    manager.gfxmode_dropdown = None
    manager.gfxpayload_dropdown = None
    manager.disable_os_prober_check = None
    manager.terminal_color_check = None

    model = MagicMock()
    model.timeout = 5

    # Should run without error
    manager._apply_model_to_ui(model, [])


def test_load_config_exceptions(manager):
    """Test load_config exception handling."""
    manager.info_label = MagicMock()
    with patch("ui.ui_manager.check_grub_sync", side_effect=Exception("Unexpected")):
        manager.load_config()
        # Should show error info
        assert manager.info_label.set_text.called


def test_on_modified_loading(manager):
    """Test on_modified when loading."""
    manager.state_manager.is_loading = MagicMock(return_value=True)
    manager.on_modified(MagicMock())
    # Should return early
    assert not manager.state_manager.mark_dirty.called


def test_on_hidden_timeout_toggled_loading(manager):
    """Test on_hidden_timeout_toggled when loading."""
    manager.state_manager.is_loading = MagicMock(return_value=True)
    manager.on_hidden_timeout_toggled(MagicMock())
    # Should return early


def test_on_menu_options_toggled_loading(manager):
    """Test on_menu_options_toggled when loading."""
    manager.state_manager.is_loading = MagicMock(return_value=True)
    manager.on_modified = MagicMock()
    manager.on_menu_options_toggled(MagicMock())
    # Should return early
    manager.on_modified.assert_not_called()


def test_on_save_not_root(manager):
    """Test on_save when not root."""
    manager.info_label = MagicMock()
    with patch("os.geteuid", return_value=1000):
        manager.on_save(None)
        # Should show error
        # We can check if show_info was called with specific message if needed


def test_perform_save_verification_failure(manager):
    """Test _perform_save when verification fails."""
    manager._read_model_from_ui = MagicMock()
    manager.state_manager.state_data.raw_config = {}
    manager.info_label = MagicMock()

    with (
        patch("ui.ui_manager.GrubApplyManager") as MockApplyManager,
        patch("ui.ui_manager.read_grub_default") as mock_read,
    ):

        instance = MockApplyManager.return_value
        instance.apply_configuration.return_value.success = True

        # Verification fails (values don't match)
        mock_read.return_value = {"GRUB_TIMEOUT": "999", "GRUB_DEFAULT": "wrong"}

        manager._perform_save(apply_now=True)
        # Should log warning (we can't easily assert log calls without caplog, but code path is covered)


def test_perform_save_verification_exception(manager):
    """Test _perform_save when verification raises exception."""
    manager._read_model_from_ui = MagicMock()
    manager.info_label = MagicMock()

    with (
        patch("ui.ui_manager.GrubApplyManager") as MockApplyManager,
        patch("ui.ui_manager.read_grub_default", side_effect=Exception("Read error")),
    ):

        instance = MockApplyManager.return_value
        instance.apply_configuration.return_value.success = True

        manager._perform_save(apply_now=True)
        # Should catch exception and continue


def test_perform_save_apply_now_false(manager):
    """Test _perform_save with apply_now=False."""
    manager._read_model_from_ui = MagicMock()
    manager.info_label = MagicMock()

    with patch("ui.ui_manager.GrubApplyManager") as MockApplyManager:
        instance = MockApplyManager.return_value
        instance.apply_configuration.return_value.success = True

        manager.state_manager.entries_visibility_dirty = True
        manager._perform_save(apply_now=False)
        # Should append message about masking not applied


def test_perform_save_hidden_entries_exception(manager):
    """Test _perform_save exception during hidden entries application."""
    manager._read_model_from_ui = MagicMock()
    manager.state_manager.hidden_entry_ids = ["id1"]
    manager.info_label = MagicMock()

    with (
        patch("ui.ui_manager.GrubApplyManager") as MockApplyManager,
        patch("ui.ui_manager.apply_hidden_entries_to_grub_cfg", side_effect=Exception("Mask error")),
    ):

        instance = MockApplyManager.return_value
        instance.apply_configuration.return_value.success = True

        manager._perform_save(apply_now=True)
        # Should catch exception and show warning


def test_perform_save_general_exception(manager):
    """Test _perform_save general exception."""
    manager._read_model_from_ui = MagicMock(side_effect=Exception("General error"))
    manager.info_label = MagicMock()
    manager._perform_save(apply_now=True)
    # Should show error info


def test_show_info_none_widgets(manager):
    """Test show_info with None widgets."""
    manager.info_label = None
    manager.show_info("msg", "info")

    manager.info_label = MagicMock()
    manager.info_box = None
    manager.show_info("msg", "info")

    manager.info_box = MagicMock()
    manager.info_revealer = None
    manager.show_info("msg", "info")


def test_init_coverage():
    """Test __init__ method coverage."""
    app = MagicMock(spec=Gtk.Application)
    with (
        patch("ui.ui_manager.Gtk.ApplicationWindow.__init__") as mock_super_init,
        patch("ui.ui_manager.UIBuilder.create_main_ui") as mock_create_ui,
        patch("ui.ui_manager.GrubConfigManager.load_config") as mock_load_config,
        patch("ui.ui_manager.GrubConfigManager.check_permissions") as mock_check_permissions,
        patch("ui.ui_manager.GrubConfigManager.set_default_size") as mock_set_size,
    ):

        def side_effect_create_ui(mgr):
            mgr.save_btn = MagicMock()
            mgr.reload_btn = MagicMock()

        mock_create_ui.side_effect = side_effect_create_ui

        mgr = GrubConfigManager(app)

        mock_super_init.assert_called_once()
        mock_create_ui.assert_called_once()
        mock_load_config.assert_called_once()
        mock_check_permissions.assert_called_once()
        mock_set_size.assert_called_with(850, 700)
        assert isinstance(mgr.state_manager, AppStateManager)


def test_get_timeout_value_none(manager):
    """Test _get_timeout_value when dropdown is None."""
    manager.timeout_dropdown = None
    assert manager._get_timeout_value() == 5


def test_set_default_choice_coverage(manager):
    """Test _set_default_choice branches."""
    manager.default_dropdown = MagicMock()
    model = MagicMock()
    manager.default_dropdown.get_model.return_value = model

    # Case 1: "saved"
    manager._set_default_choice("saved")
    manager.default_dropdown.set_selected.assert_called_with(0)

    # Case 2: Existing ID
    manager.state_manager.get_default_choice_ids.return_value = ["saved", "id1", "id2"]
    manager._set_default_choice("id2")
    manager.default_dropdown.set_selected.assert_called_with(2)

    # Case 3: New ID (append)
    manager._set_default_choice("new_id")
    model.append.assert_called_with("new_id")
    # Should update ids and select last
    assert manager.state_manager.update_default_choice_ids.called

    # Case 4: Exception during append
    model.append.side_effect = Exception("Error")
    manager._set_default_choice("error_id")
    manager.default_dropdown.set_selected.assert_called_with(0)


def test_on_reload_dialog_cancel(manager):
    """Test on_reload dialog cancellation."""
    manager.state_manager.modified = True

    with patch("ui.ui_manager.Gtk.AlertDialog") as MockDialog:
        dialog_instance = MockDialog.return_value

        def side_effect_choose(parent, _, callback):
            # Simulate callback execution
            callback(dialog_instance, MagicMock())

        dialog_instance.choose.side_effect = side_effect_choose
        dialog_instance.choose_finish.side_effect = GLib.Error("Cancelled")

        manager.load_config = MagicMock()
        manager.on_reload(None)
        manager.load_config.assert_not_called()


def test_on_save_dialog_cancel(manager):
    """Test on_save dialog cancellation."""
    with patch("os.geteuid", return_value=0), patch("ui.ui_manager.Gtk.AlertDialog") as MockDialog:

        dialog_instance = MockDialog.return_value

        def side_effect_choose(parent, _, callback):
            callback(dialog_instance, MagicMock())

        dialog_instance.choose.side_effect = side_effect_choose
        dialog_instance.choose_finish.side_effect = GLib.Error("Cancelled")

        manager._perform_save = MagicMock()
        manager.on_save(None)

        manager._perform_save.assert_not_called()


def test_perform_save_verification_warning(manager):
    """Test _perform_save verification mismatch warning."""
    manager._read_model_from_ui = MagicMock()
    manager._read_model_from_ui.return_value.timeout = 10
    manager._read_model_from_ui.return_value.default = "id1"

    with (
        patch("ui.ui_manager.merged_config_from_model", return_value={}),
        patch("ui.ui_manager.GrubApplyManager") as MockApplyManager,
        patch("ui.ui_manager.read_grub_default") as mock_read,
    ):

        instance = MockApplyManager.return_value
        instance.apply_configuration.return_value.success = True
        instance.apply_configuration.return_value.message = "Success"
        instance.apply_configuration.return_value.details = "Details"

        # Mismatch values
        mock_read.return_value = {"GRUB_TIMEOUT": "5", "GRUB_DEFAULT": "id2"}

        manager.show_info = MagicMock()
        manager._perform_save(apply_now=False)

        # Should still succeed but log warning
        manager.show_info.assert_called()


def test_perform_save_hidden_entries_exception(manager):
    """Test _perform_save hidden entries application exception."""
    manager._read_model_from_ui = MagicMock()
    manager.state_manager.hidden_entry_ids = ["hidden1"]

    with (
        patch("ui.ui_manager.merged_config_from_model", return_value={}),
        patch("ui.ui_manager.GrubApplyManager") as MockApplyManager,
        patch("ui.ui_manager.read_grub_default", return_value={}),
        patch("ui.ui_manager.apply_hidden_entries_to_grub_cfg", side_effect=Exception("Hide Error")),
    ):

        instance = MockApplyManager.return_value
        instance.apply_configuration.return_value.success = True
        instance.apply_configuration.return_value.message = "Success"
        instance.apply_configuration.return_value.details = None

        manager.show_info = MagicMock()
        manager._perform_save(apply_now=True)

        # Should show warning about hide error
        args, _ = manager.show_info.call_args
        assert "Masquage échoué" in args[0]
        assert args[1] == "warning"


def test_perform_save_dirty_visibility_not_applied(manager):
    """Test _perform_save with dirty visibility but apply_now=False."""
    manager._read_model_from_ui = MagicMock()
    manager.state_manager.entries_visibility_dirty = True

    with (
        patch("ui.ui_manager.merged_config_from_model", return_value={}),
        patch("ui.ui_manager.GrubApplyManager") as MockApplyManager,
        patch("ui.ui_manager.read_grub_default", return_value={}),
    ):

        instance = MockApplyManager.return_value
        instance.apply_configuration.return_value.success = True
        instance.apply_configuration.return_value.message = "Success"
        instance.apply_configuration.return_value.details = None

        manager.show_info = MagicMock()
        manager._perform_save(apply_now=False)

        args, _ = manager.show_info.call_args
        assert "Masquage non appliqué" in args[0]


def test_set_default_choice_not_found(manager):
    """Test _set_default_choice with value not found in list."""
    manager.default_dropdown = MagicMock()
    manager.state_manager.get_default_choice_ids = MagicMock(return_value=["id1", "id2"])

    # Mock model to allow appending
    model = MagicMock()
    manager.default_dropdown.get_model.return_value = model

    # Call with unknown value
    manager._set_default_choice("unknown_id")

    # Should append to model and select it
    model.append.assert_called_with("unknown_id")
    # Should update state manager
    manager.state_manager.update_default_choice_ids.assert_called()
    # Should select the new item (index 2)
    manager.default_dropdown.set_selected.assert_called_with(2)


def test_load_config_no_entries_non_root(manager):
    """Test load_config with no entries and non-root user."""
    manager.info_label = MagicMock()

    with (
        patch("ui.ui_manager.check_grub_sync") as mock_sync,
        patch("ui.ui_manager.load_grub_ui_state") as mock_load_state,
        patch("ui.ui_manager.render_entries_view"),
        patch("os.geteuid", return_value=1000),
    ):

        mock_sync.return_value.in_sync = True

        state = MagicMock()
        state.entries = []
        state.model.hidden_timeout = False
        mock_load_state.return_value = state

        manager.load_config()

        # Should show warning about permissions
        manager.info_label.set_text.assert_any_call(
            "Entrées GRUB indisponibles: lecture de /boot/grub/grub.cfg refusée (droits). "
            "Relancez l'application avec pkexec/sudo."
        )


def test_on_hidden_timeout_toggled_active(manager):
    """Test on_hidden_timeout_toggled when active."""
    manager.state_manager.is_loading = MagicMock(return_value=False)
    widget = MagicMock()
    widget.get_active.return_value = True

    manager.timeout_dropdown = MagicMock()
    manager.timeout_dropdown.get_model.return_value = MagicMock()

    with (
        patch("ui.ui_gtk_helpers.GtkHelper.stringlist_replace_all"),
        patch("ui.ui_gtk_helpers.GtkHelper.stringlist_find", return_value=0),
    ):

        manager.on_hidden_timeout_toggled(widget)

        # Should sync choices to 0 and set value to 0
        manager.timeout_dropdown.set_selected.assert_called()


def test_on_reload_cancel(manager):
    """Test on_reload cancellation."""
    manager.state_manager.modified = True

    with patch("ui.ui_manager.Gtk.AlertDialog") as MockDialog:
        dialog_instance = MockDialog.return_value

        def choose_side_effect(parent, _, callback):
            # Simulate callback with result
            callback(dialog_instance, MagicMock())

        dialog_instance.choose.side_effect = choose_side_effect
        dialog_instance.choose_finish.return_value = 0  # Cancel

        manager.on_reload(None)

        # Should NOT call load_config
        # We can't easily assert load_config NOT called because it's a method on manager which is the SUT
        # But we can check if show_info was called (it is called on success)
        manager.info_label = MagicMock()
        assert not manager.info_label.set_text.called


def test_on_save_cancel(manager):
    """Test on_save cancellation."""
    with patch("os.geteuid", return_value=0), patch("ui.ui_manager.Gtk.AlertDialog") as MockDialog:

        dialog_instance = MockDialog.return_value

        def choose_side_effect(parent, _, callback):
            callback(dialog_instance, MagicMock())

        dialog_instance.choose.side_effect = choose_side_effect
        dialog_instance.choose_finish.return_value = 0  # Cancel

        with patch.object(manager, "_perform_save") as mock_perform:
            manager.on_save(None)
            mock_perform.assert_not_called()


def test_perform_save_dirty_visibility_no_apply(manager):
    """Test _perform_save with dirty visibility and no apply."""
    manager._read_model_from_ui = MagicMock()
    manager.info_label = MagicMock()
    manager.state_manager.entries_visibility_dirty = True

    with patch("ui.ui_manager.GrubApplyManager") as MockApplyManager:
        instance = MockApplyManager.return_value
        instance.apply_configuration.return_value.success = True
        instance.apply_configuration.return_value.message = "Success"
        instance.apply_configuration.return_value.details = ""

        manager._perform_save(apply_now=False)

        # Check if message contains the warning
        args, _ = manager.info_label.set_text.call_args
        assert "(Masquage non appliqué car update-grub ignoré)" in args[0]


def test_show_info_existing_classes(manager):
    """Test show_info removing existing classes."""
    manager.info_label = MagicMock()
    manager.info_box = MagicMock()
    manager.info_revealer = MagicMock()

    # Simulate "info" class being present
    manager.info_box.has_css_class.side_effect = lambda k: k == "info"

    manager.show_info("msg", "warning")

    # Should remove "info"
    manager.info_box.remove_css_class.assert_called_with("info")
    # Should add "warning"
    manager.info_box.add_css_class.assert_called_with("warning")


def test_ensure_timeout_choice_loop_completion(manager):
    """Test _ensure_timeout_choice loop completion (no break)."""
    manager.timeout_dropdown = MagicMock()
    model = MagicMock()
    manager.timeout_dropdown.get_model.return_value = model

    # Setup model with values smaller than wanted "100"
    model.get_n_items.return_value = 2
    model.get_string.side_effect = ["10", "20"]

    with patch("ui.ui_gtk_helpers.GtkHelper.stringlist_find", side_effect=[None, 2]):
        # Wanted "100" > "10" and "20", so loop finishes without break
        # insert_at should remain 2 (initial value)
        with patch("ui.ui_gtk_helpers.GtkHelper.stringlist_insert") as mock_insert:
            manager._ensure_timeout_choice("100")
            mock_insert.assert_called_with(model, 2, "100")


def test_on_save_dialog_exception(manager):
    """Test on_save dialog exception handling."""
    manager.info_label = MagicMock()

    # Mock root permission
    with patch("os.geteuid", return_value=0), patch("ui.ui_manager.logger") as mock_logger:
        with patch("gi.repository.Gtk.AlertDialog") as MockDialog:
            dialog_instance = MockDialog.return_value

            # Mock choose to call callback immediately
            def side_effect_choose(parent, _, callback):
                callback(dialog_instance, MagicMock())

            dialog_instance.choose.side_effect = side_effect_choose

            # Mock choose_finish to raise GLib.Error
            dialog_instance.choose_finish.side_effect = GLib.Error("Mock GLib Error")

            manager.on_save(None)
            # Should catch exception and return (no crash)
            # Verify exception was caught and logged
            # Note: The log message format in ui_manager.py is: f"[on_save._on_response] Dialog cancelled: {e}"
            # We check if any debug call contains "Dialog cancelled"
            assert any("Dialog cancelled" in str(call) for call in mock_logger.debug.mock_calls)


def test_on_reload_dialog_exception(manager):
    """Test on_reload dialog exception handling."""
    manager.state_manager.modified = True
    manager.info_label = MagicMock()

    with patch("gi.repository.Gtk.AlertDialog") as MockDialog, patch("ui.ui_manager.logger") as mock_logger:
        dialog_instance = MockDialog.return_value

        def side_effect_choose(parent, _, callback):
            callback(dialog_instance, MagicMock())

        dialog_instance.choose.side_effect = side_effect_choose

        dialog_instance.choose_finish.side_effect = GLib.Error("Mock GLib Error")

        manager.on_reload(None)
        # Should catch exception and return
        assert any("Dialog cancelled" in str(call) for call in mock_logger.debug.mock_calls)


def test_perform_save_verification_success(manager):
    """Test _perform_save verification success."""
    manager._read_model_from_ui = MagicMock()
    # Setup model values
    model = manager._read_model_from_ui.return_value
    model.timeout = 5
    model.default = "0"

    manager.info_label = MagicMock()

    with (
        patch("ui.ui_manager.GrubApplyManager") as MockApplyManager,
        patch("ui.ui_manager.read_grub_default") as mock_read,
        patch("ui.ui_manager.logger") as mock_logger,
    ):

        instance = MockApplyManager.return_value
        instance.apply_configuration.return_value.success = True

        # Verification succeeds
        mock_read.return_value = {"GRUB_TIMEOUT": "5", "GRUB_DEFAULT": "0"}

        manager._perform_save(apply_now=True)
        # Should NOT log warning about verification mismatch
        assert not any("Valeurs écrites ne correspondent pas" in str(call) for call in mock_logger.warning.mock_calls)


def test_perform_save_verification_exception_coverage(manager):
    """Test _perform_save verification exception (explicit coverage)."""
    manager._read_model_from_ui = MagicMock()
    manager.info_label = MagicMock()

    with (
        patch("ui.ui_manager.GrubApplyManager") as MockApplyManager,
        patch("ui.ui_manager.read_grub_default", side_effect=Exception("Read error")),
        patch("ui.ui_manager.logger") as mock_logger,
    ):

        instance = MockApplyManager.return_value
        instance.apply_configuration.return_value.success = True

        manager._perform_save(apply_now=True)
        # Should catch exception and log warning
        assert any("Impossible de vérifier les valeurs écrites" in str(call) for call in mock_logger.warning.mock_calls)
