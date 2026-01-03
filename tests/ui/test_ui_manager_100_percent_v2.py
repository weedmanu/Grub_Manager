import pytest
from unittest.mock import MagicMock, patch
from ui.ui_manager import GrubConfigManager, INFO, WARNING, ERROR

class TestUiManagerFinalGap:
    @pytest.fixture
    def manager(self):
        with patch.object(GrubConfigManager, '__init__', return_value=None):
            manager = GrubConfigManager()
            manager.window = MagicMock()
            manager.info_label = MagicMock()
            manager.info_box = MagicMock()
            manager.info_revealer = MagicMock()
            manager.save_btn = MagicMock()
            manager.reload_btn = MagicMock()
            manager.state_manager = MagicMock()
            
            # Initialize widgets expected by load_config -> _apply_model_to_ui
            manager.timeout_dropdown = MagicMock()
            manager.timeout_dropdown.get_model.return_value.get_n_items.return_value = 0
            
            manager.default_dropdown = MagicMock()
            manager.default_dropdown.get_model.return_value.get_n_items.return_value = 0
            
            manager.hidden_timeout_check = MagicMock()
            
            manager.gfxmode_dropdown = MagicMock()
            manager.gfxmode_dropdown.get_model.return_value.get_n_items.return_value = 0
            
            manager.gfxpayload_dropdown = MagicMock()
            manager.gfxpayload_dropdown.get_model.return_value.get_n_items.return_value = 0
            
            manager.terminal_color_check = MagicMock()
            manager.disable_submenu_check = MagicMock()
            manager.disable_recovery_check = MagicMock()
            manager.disable_os_prober_check = MagicMock()
            
            manager.entries_listbox = MagicMock()
            
            return manager

    def test_load_config_root_no_entries(self, manager):
        """Cover line 414: load_config with root user and no entries."""
        with patch('ui.ui_manager.os.geteuid', return_value=0), \
             patch('ui.ui_manager.check_grub_sync') as mock_sync, \
             patch('ui.ui_manager.load_grub_ui_state') as mock_load_state, \
             patch('ui.ui_manager.render_entries_view'):
            
            mock_sync.return_value.in_sync = True
            
            # Mock state
            mock_state = MagicMock()
            mock_state.entries = [] # No entries
            mock_state.model.hidden_timeout = False
            mock_load_state.return_value = mock_state
            
            # Mock state manager to return empty entries
            manager.state_manager.state_data.entries = []
            
            manager.load_config()
            
            # Verify show_info was called with the specific warning
            manager.info_label.set_text.assert_called()
            args, _ = manager.info_label.set_text.call_args
            assert "Aucune entrée GRUB détectée" in args[0]

    def test_on_menu_options_toggled(self, manager):
        """Cover lines 458-460: on_menu_options_toggled."""
        widget = MagicMock()
        manager.state_manager.is_loading.return_value = False
        
        with patch('ui.ui_manager.render_entries_view') as mock_render:
            manager.on_menu_options_toggled(widget)
            
            manager.state_manager.mark_dirty.assert_called()
            mock_render.assert_called_once_with(manager)

    def test_perform_save_hidden_entries_success(self, manager):
        """Cover lines 579-580: _perform_save with hidden entries success."""
        manager.state_manager.apply_state = MagicMock()
        manager.state_manager.state_data.raw_config = {}
        manager.state_manager.hidden_entry_ids = {"entry1"}
        manager.state_manager.entries_visibility_dirty = True
        
        # Mock model
        mock_model = MagicMock()
        mock_model.timeout = 5
        mock_model.default = "0"
        manager._read_model_from_ui = MagicMock(return_value=mock_model)
        
        with patch('ui.ui_manager.merged_config_from_model', return_value={}), \
             patch('ui.ui_manager.GrubApplyManager') as MockApplyManager, \
             patch('ui.ui_manager.read_grub_default', return_value={"GRUB_TIMEOUT": "5", "GRUB_DEFAULT": "0"}), \
             patch('ui.ui_manager.apply_hidden_entries_to_grub_cfg') as mock_apply_hidden:
            
            mock_apply_manager = MockApplyManager.return_value
            mock_apply_manager.apply_configuration.return_value.success = True
            mock_apply_manager.apply_configuration.return_value.message = "Success"
            mock_apply_manager.apply_configuration.return_value.details = None
            
            mock_apply_hidden.return_value = ("/boot/grub/grub.cfg", 1)
            
            manager._perform_save(apply_now=True)
            
            # Verify success path
            assert manager.state_manager.entries_visibility_dirty is False
            mock_apply_hidden.assert_called_once()

    def test_show_info_invalid_type(self, manager):
        """Cover line 617->620: show_info with invalid msg_type."""
        # Setup info box context
        ctx = MagicMock()
        ctx.has_class.return_value = False
        manager.info_box.get_style_context.return_value = ctx
        
        manager.show_info("Test message", "INVALID_TYPE")
        
        # Verify add_class was NOT called
        ctx.add_class.assert_not_called()
        # Verify revealer was still shown
        manager.info_revealer.set_reveal_child.assert_called_with(True)
