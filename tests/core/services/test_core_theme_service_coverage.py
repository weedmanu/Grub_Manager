import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
from core.services.core_theme_service import ThemeService

class TestThemeServiceCoverage:
    @pytest.fixture
    def service(self):
        return ThemeService()

    @patch("core.services.core_theme_service.read_grub_default")
    @patch("core.services.core_theme_service.GRUB_CFG_PATHS", ["/boot/grub/grub.cfg"])
    def test_is_theme_enabled_in_grub_exception_and_cfg_found(self, mock_read_default, service):
        """Test exception in read_grub_default and finding theme in grub.cfg."""
        mock_read_default.side_effect = OSError("Read error")
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value="set theme=/boot/grub/themes/test/theme.txt"):
            assert service.is_theme_enabled_in_grub() is True

    @patch("core.services.core_theme_service.read_grub_default")
    @patch("core.services.core_theme_service.GRUB_CFG_PATHS", ["/boot/grub/grub.cfg"])
    def test_is_theme_enabled_in_grub_cfg_not_exists(self, mock_read_default, service):
        """Test grub.cfg does not exist."""
        mock_read_default.return_value = {}
        
        with patch("pathlib.Path.exists", return_value=False):
            assert service.is_theme_enabled_in_grub() is False

    @patch("core.services.core_theme_service.read_grub_default")
    @patch("core.services.core_theme_service.GRUB_CFG_PATHS", ["/boot/grub/grub.cfg"])
    def test_is_theme_enabled_in_grub_cfg_permission_error(self, mock_read_default, service):
        """Test permission error when reading grub.cfg."""
        mock_read_default.return_value = {}
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", side_effect=PermissionError("Denied")):
            assert service.is_theme_enabled_in_grub() is False

    @patch("core.services.core_theme_service.read_grub_default")
    @patch("core.services.core_theme_service.GRUB_CFG_PATHS", ["/boot/grub/grub.cfg"])
    def test_is_theme_enabled_in_grub_cfg_no_theme(self, mock_read_default, service):
        """Test no theme found in grub.cfg."""
        mock_read_default.return_value = {}
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value="set timeout=5"):
            assert service.is_theme_enabled_in_grub() is False

    @patch("core.services.core_theme_service.read_grub_default")
    @patch("core.services.core_theme_service.GRUB_CFG_PATHS", ["/boot/grub/grub.cfg"])
    def test_is_theme_enabled_in_grub_found_in_default(self, mock_read_default, service):
        """Test theme found in /etc/default/grub."""
        mock_read_default.return_value = {"GRUB_THEME": "/boot/grub/themes/test/theme.txt"}
        assert service.is_theme_enabled_in_grub() is True

    @patch("core.services.core_theme_service.read_grub_default")
    @patch("core.services.core_theme_service.GRUB_CFG_PATHS", ["/boot/grub/grub.cfg"])
    def test_is_theme_enabled_in_grub_cfg_empty_theme(self, mock_read_default, service):
        """Test empty theme path in grub.cfg."""
        mock_read_default.return_value = {}
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value="set theme=\nset theme=\"\""):
            assert service.is_theme_enabled_in_grub() is False

    @patch("core.services.core_theme_service.get_all_grub_themes_dirs")
    def test_scan_system_themes_dir_not_exists(self, mock_get_dirs, service):
        """Test scan when a theme directory does not exist."""
        mock_dir = MagicMock(spec=Path)
        mock_dir.exists.return_value = False
        mock_get_dirs.return_value = [mock_dir]
        
        themes = service.scan_system_themes()
        assert len(themes) == 0

    @patch("core.services.core_theme_service.get_all_grub_themes_dirs")
    @patch("core.services.core_theme_service.create_custom_theme")
    def test_scan_system_themes_success(self, mock_create, mock_get_dirs, service):
        """Test successful theme scan."""
        mock_dir = MagicMock(spec=Path)
        mock_dir.exists.return_value = True
        
        mock_theme_dir = MagicMock(spec=Path)
        mock_theme_dir.is_dir.return_value = True
        mock_theme_dir.name = "good_theme"
        (mock_theme_dir / "theme.txt").exists.return_value = True
        
        mock_dir.iterdir.return_value = [mock_theme_dir]
        mock_get_dirs.return_value = [mock_dir]
        
        mock_theme = MagicMock()
        mock_create.return_value = mock_theme
        
        themes = service.scan_system_themes()
        assert "good_theme" in themes
        assert themes["good_theme"] == (mock_theme, mock_theme_dir)

    @patch("core.services.core_theme_service.get_all_grub_themes_dirs")
    @patch("core.services.core_theme_service.create_custom_theme")
    def test_scan_system_themes_mixed_items(self, mock_create, mock_get_dirs, service):
        """Test scan with mixed items (valid theme, file, dir without theme.txt)."""
        mock_dir = MagicMock(spec=Path)
        mock_dir.exists.return_value = True
        
        # 1. Valid theme
        mock_theme_dir = MagicMock(spec=Path)
        mock_theme_dir.is_dir.return_value = True
        mock_theme_dir.name = "good_theme"
        (mock_theme_dir / "theme.txt").exists.return_value = True
        
        # 2. Just a file
        mock_file = MagicMock(spec=Path)
        mock_file.is_dir.return_value = False
        
        # 3. Dir without theme.txt
        mock_empty_dir = MagicMock(spec=Path)
        mock_empty_dir.is_dir.return_value = True
        (mock_empty_dir / "theme.txt").exists.return_value = False
        
        mock_dir.iterdir.return_value = [mock_theme_dir, mock_file, mock_empty_dir]
        mock_get_dirs.return_value = [mock_dir]
        
        mock_create.return_value = MagicMock()
        
        themes = service.scan_system_themes()
        assert "good_theme" in themes
        assert len(themes) == 1

    @patch("core.services.core_theme_service.get_all_grub_themes_dirs")
    @patch("core.services.core_theme_service.create_custom_theme")
    def test_scan_system_themes_exception(self, mock_create, mock_get_dirs, service):
        """Test exception during theme creation in scan."""
        mock_dir = MagicMock(spec=Path)
        mock_dir.exists.return_value = True
        
        mock_theme_dir = MagicMock(spec=Path)
        mock_theme_dir.is_dir.return_value = True
        mock_theme_dir.name = "bad_theme"
        (mock_theme_dir / "theme.txt").exists.return_value = True
        
        mock_dir.iterdir.return_value = [mock_theme_dir]
        mock_get_dirs.return_value = [mock_dir]
        
        mock_create.side_effect = ValueError("Invalid theme")
        
        themes = service.scan_system_themes()
        assert "bad_theme" not in themes
        assert len(themes) == 0

    def test_is_theme_custom(self, service):
        """Test is_theme_custom logic."""
        assert service.is_theme_custom(Path("/boot/grub/themes/mytheme")) is True
        assert service.is_theme_custom(Path("/usr/share/grub/themes/system")) is False

    def test_delete_theme_system(self, service):
        """Test refusal to delete system theme."""
        path = Path("/usr/share/grub/themes/system")
        assert service.delete_theme(path) is False

    @patch("shutil.rmtree")
    def test_delete_theme_exception(self, mock_rmtree, service):
        """Test exception during deletion."""
        path = Path("/boot/grub/themes/custom")
        with patch.object(Path, "exists", return_value=True):
            mock_rmtree.side_effect = OSError("Delete failed")
            assert service.delete_theme(path) is False

    @patch("shutil.rmtree")
    def test_delete_theme_not_exists(self, mock_rmtree, service):
        """Test deletion of non-existent theme."""
        path = Path("/boot/grub/themes/custom")
        with patch.object(Path, "exists", return_value=False):
            assert service.delete_theme(path) is False
            mock_rmtree.assert_not_called()

    @patch("shutil.rmtree")
    def test_delete_theme_success(self, mock_rmtree, service):
        """Test successful deletion."""
        path = Path("/boot/grub/themes/custom")
        with patch.object(Path, "exists", return_value=True):
            assert service.delete_theme(path) is True
            mock_rmtree.assert_called_once_with(path)
