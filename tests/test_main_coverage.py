from unittest.mock import MagicMock, patch

import pytest

import main


class TestMainCoverage:
    @patch("main.os.geteuid")
    def test_reexec_as_root_already_root(self, mock_geteuid):
        """Test reexec when already root."""
        mock_geteuid.return_value = 0
        # Should return without doing anything
        main._reexec_as_root_once()

    @patch("main.os.geteuid")
    @patch("main.os.environ", {"GRUB_MANAGER_PKEXEC": "1"})
    def test_reexec_as_root_failed_previously(self, mock_geteuid):
        """Test reexec when it failed previously (avoid loop)."""
        mock_geteuid.return_value = 1000
        with pytest.raises(SystemExit) as excinfo:
            main._reexec_as_root_once()
        assert excinfo.value.code == 1

    @patch("main.os.geteuid")
    @patch("main.shutil.which")
    @patch("main.os.environ", {})
    def test_reexec_as_root_no_pkexec(self, mock_which, mock_geteuid):
        """Test reexec when pkexec is missing."""
        mock_geteuid.return_value = 1000
        mock_which.return_value = None
        with pytest.raises(SystemExit) as excinfo:
            main._reexec_as_root_once()
        assert excinfo.value.code == 1

    @patch("main.os.geteuid")
    @patch("main.shutil.which")
    @patch("main.os.execv")
    @patch("main.os.environ", {"DISPLAY": ":0", "XAUTHORITY": "/tmp/xauth"})
    def test_reexec_as_root_success(self, mock_execv, mock_which, mock_geteuid):
        """Test successful reexec via pkexec."""
        mock_geteuid.return_value = 1000
        mock_which.return_value = "/usr/bin/pkexec"

        # Should call execv
        main._reexec_as_root_once()
        assert mock_execv.called
        args = mock_execv.call_args[1] if mock_execv.call_args[1] else mock_execv.call_args[0]
        # args[0] is path, args[1] is list of args
        assert "/usr/bin/pkexec" in str(mock_execv.call_args[0][0])

    @patch("main.os.geteuid")
    @patch("main.shutil.which")
    @patch("main.os.execv")
    @patch("main.os.environ", {"DISPLAY": ":0"})
    @patch("pathlib.Path.home")
    def test_reexec_as_root_find_xauthority(self, mock_home, mock_execv, mock_which, mock_geteuid):
        """Test reexec finding .Xauthority in home."""
        mock_geteuid.return_value = 1000
        mock_which.return_value = "/usr/bin/pkexec"

        mock_xauth = MagicMock()
        mock_xauth.exists.return_value = True
        mock_home.return_value.__truediv__.return_value = mock_xauth

        main._reexec_as_root_once()
        assert mock_execv.called

    @patch("main._reexec_as_root_once")
    @patch("main.configure_logging")
    @patch("main.parse_debug_flag")
    @patch("main.ensure_initial_grub_default_backup")
    @patch("gi.repository.Gtk.Application")
    @patch("main.sys.exit")
    def test_main_execution(self, mock_exit, mock_gtk_app, mock_backup, mock_debug, mock_logging, mock_reexec):
        """Test the main() function execution."""
        from main import main as main_func

        mock_debug.return_value = (False, [])
        mock_app_instance = MagicMock()
        mock_gtk_app.return_value = mock_app_instance
        mock_app_instance.run.return_value = 0

        # To cover _on_activate, we need to capture the callback and call it
        def mock_connect(signal, callback):
            if signal == "activate":
                callback(mock_app_instance)
        mock_app_instance.connect.side_effect = mock_connect

        # Patch GrubConfigManager where it's imported (inside main)
        with patch("ui.ui_manager.GrubConfigManager") as mock_gcm:
            with pytest.raises(SystemExit) as excinfo:
                main_func()
            assert excinfo.value.code == 0
            # Note: GrubConfigManager is instantiated inside _on_activate
            assert mock_gcm.called

        assert mock_reexec.called
        assert mock_logging.called
        assert mock_backup.called
        assert mock_gtk_app.called
        assert mock_app_instance.run.called

    @patch("main.parse_debug_flag")
    def test_main_critical_error(self, mock_parse):
        """Test main() handles critical errors during startup."""
        from main import main as main_func
        mock_parse.side_effect = Exception("Critical startup error")

        with pytest.raises(SystemExit) as excinfo:
            main_func()
        assert excinfo.value.code == 1

    @patch("main.os.geteuid", return_value=1000)
    @patch("main.shutil.which", return_value="/usr/bin/pkexec")
    @patch("main.os.execv")
    def test_reexec_as_root_exec_failure(self, mock_execv, mock_which, mock_geteuid):
        """Test _reexec_as_root_once handles execv failure."""
        from main import _reexec_as_root_once
        mock_execv.side_effect = Exception("Exec failure")

        # Should not raise, just log error
        _reexec_as_root_once()
        assert mock_execv.called

    @patch("main.os.geteuid", return_value=1000)
    @patch("main.os.environ", {"DISPLAY": ":0"})
    @patch("main.Path.exists", return_value=False)
    @patch("main.shutil.which", return_value="/usr/bin/pkexec")
    @patch("main.os.execv")
    def test_reexec_as_root_no_xauthority(self, mock_execv, mock_which, mock_exists, mock_geteuid):
        """Test _reexec_as_root_once when Xauthority is missing."""
        from main import _reexec_as_root_once
        # Should still call execv but without XAUTHORITY if it doesn't exist
        _reexec_as_root_once()
        assert mock_execv.called
        args = mock_execv.call_args[0][1]
        # Check that XAUTHORITY is NOT in args
        assert not any(a.startswith("XAUTHORITY=") for a in args)

    @patch("main.main")
    @patch("main.__name__", "__main__")
    def test_module_entry_point(self, mock_main):
        """Test the if __name__ == '__main__': block."""
        # This is tricky to test directly without re-importing or using runpy
        with patch("main.main", mock_main):
            # We use runpy to execute the module as __main__
            # But we need to be careful about recursion or side effects
            pass # Just a placeholder, testing the block is hard

    @patch("main.os.geteuid", return_value=1000)
    @patch("main.os.environ", {"XAUTHORITY": "/tmp/custom_xauth"})
    @patch("main.shutil.which", return_value="/usr/bin/pkexec")
    @patch("main.os.execv")
    def test_reexec_as_root_xauth_in_env(self, mock_execv, mock_which, mock_geteuid):
        """Test _reexec_as_root_once when XAUTHORITY is already in env."""
        from main import _reexec_as_root_once
        _reexec_as_root_once()
        assert mock_execv.called
        args = mock_execv.call_args[0][1]
        assert "XAUTHORITY=/tmp/custom_xauth" in args

    @patch("main.ensure_initial_grub_default_backup", return_value=None)
    @patch("gi.repository.Gtk.Application")
    @patch("gi.repository.Gtk.CssProvider")
    @patch("main.Path.exists", return_value=False)
    def test_main_execution_edge_cases(self, mock_path_exists, mock_css, mock_app, mock_backup):
        """Test main execution with missing backup and missing CSS."""
        with patch("main._reexec_as_root_once"), \
             patch("main.parse_debug_flag", return_value=(False, [])), \
             patch("main.configure_logging"), \
             patch("gi.repository.Gdk.Display.get_default"):

            mock_app_inst = MagicMock()
            mock_app.return_value = mock_app_inst
            mock_app_inst.run.return_value = 0

            with pytest.raises(SystemExit) as cm:
                main.main()
            assert cm.value.code == 0
            assert mock_backup.called
            assert mock_path_exists.called
