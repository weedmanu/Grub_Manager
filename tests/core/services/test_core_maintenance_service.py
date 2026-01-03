"""Tests pour le service de maintenance."""

from unittest.mock import mock_open, patch

import pytest

from core.services.core_maintenance_service import MaintenanceService


@pytest.fixture
def service():
    return MaintenanceService()


def test_get_restore_command_apt(service):
    with patch("shutil.which", side_effect=lambda x: "/usr/bin/apt-get" if x == "apt-get" else None):
        assert service.get_restore_command() == ("APT", ["apt-get", "install", "--reinstall", "grub-common"])


def test_get_restore_command_pacman(service):
    with patch("shutil.which", side_effect=lambda x: "/usr/bin/pacman" if x == "pacman" else None):
        assert service.get_restore_command() == ("Pacman", ["pacman", "-S", "--noconfirm", "grub"])


def test_get_restore_command_dnf(service):
    with patch("shutil.which", side_effect=lambda x: "/usr/bin/dnf" if x == "dnf" else None):
        assert service.get_restore_command() == ("DNF", ["dnf", "reinstall", "-y", "grub2-common"])


def test_get_restore_command_zypper(service):
    with patch("shutil.which", side_effect=lambda x: "/usr/bin/zypper" if x == "zypper" else None):
        assert service.get_restore_command() == ("Zypper", ["zypper", "install", "--force", "grub2"])


def test_get_restore_command_none(service):
    with patch("shutil.which", return_value=None):
        assert service.get_restore_command() is None


def test_get_reinstall_05_debian_command(service):
    with patch.object(service, "get_restore_command", return_value=("APT", ["cmd"])):
        assert service.get_reinstall_05_debian_command() == ["cmd"]


def test_get_reinstall_05_debian_command_none(service):
    with patch.object(service, "get_restore_command", return_value=None):
        assert service.get_reinstall_05_debian_command() is None


def test_get_enable_05_debian_theme_command(service):
    assert service.get_enable_05_debian_theme_command() == ["chmod", "+x", "/etc/grub.d/05_debian_theme"]


def test_find_theme_script_path_in_config(service):
    with (
        patch(
            "core.services.core_maintenance_service.read_grub_default", return_value={"GRUB_THEME": "/tmp/theme.txt"}
        ),
        patch("os.path.exists", side_effect=lambda p: p == "/tmp/theme.txt"),
    ):
        assert service.find_theme_script_path() == "/tmp/theme.txt"


def test_find_theme_script_path_common_paths(service):
    with (
        patch("core.services.core_maintenance_service.read_grub_default", return_value={}),
        patch("glob.glob", return_value=["/boot/grub/themes/starfield/theme.txt"]),
    ):
        assert service.find_theme_script_path() == "/boot/grub/themes/starfield/theme.txt"


def test_find_theme_script_path_grub_d(service):
    with (
        patch("core.services.core_maintenance_service.read_grub_default", return_value={}),
        patch("glob.glob", return_value=[]),
        patch("os.path.exists", side_effect=lambda p: p == "/etc/grub.d"),
        patch("os.listdir", return_value=["05_debian_theme"]),
        patch("os.path.isfile", return_value=True),
    ):
        assert service.find_theme_script_path() == "/etc/grub.d/05_debian_theme"


def test_find_theme_script_path_custom_cfg(service):
    with (
        patch("core.services.core_maintenance_service.read_grub_default", return_value={}),
        patch("glob.glob", side_effect=lambda p: ["/boot/grub/custom.cfg"] if "custom.cfg" in p else []),
        patch("os.path.exists", return_value=False),
        patch("builtins.open", mock_open(read_data="set theme=/boot/grub/themes/dark/theme.txt")),
    ):
        assert service.find_theme_script_path() == "/boot/grub/custom.cfg"


def test_find_theme_script_path_none(service):
    with (
        patch("core.services.core_maintenance_service.read_grub_default", return_value={}),
        patch("glob.glob", return_value=[]),
        patch("os.path.exists", return_value=False),
    ):
        assert service.find_theme_script_path() is None


def test_find_theme_script_path_oserror_read_default(service):
    with (
        patch("core.services.core_maintenance_service.read_grub_default", side_effect=OSError("Read error")),
        patch("glob.glob", return_value=[]),
        patch("os.path.exists", return_value=False),
    ):
        assert service.find_theme_script_path() is None


def test_find_theme_script_path_oserror_custom_cfg(service):
    with (
        patch("core.services.core_maintenance_service.read_grub_default", return_value={}),
        patch("glob.glob", side_effect=lambda p: ["/boot/grub/custom.cfg"] if "custom.cfg" in p else []),
        patch("os.path.exists", return_value=False),
        patch("builtins.open", side_effect=OSError("Read error")),
    ):
        assert service.find_theme_script_path() is None


def test_find_theme_script_path_in_config_not_exists(service):
    """Test when GRUB_THEME is set but file does not exist."""
    with (
        patch(
            "core.services.core_maintenance_service.read_grub_default", return_value={"GRUB_THEME": "/tmp/missing.txt"}
        ),
        patch("os.path.exists", return_value=False),
        patch("glob.glob", return_value=[]),
    ):
        assert service.find_theme_script_path() is None


def test_find_theme_script_path_grub_d_not_exists(service):
    """Test when /etc/grub.d does not exist."""
    with (
        patch("core.services.core_maintenance_service.read_grub_default", return_value={}),
        patch("glob.glob", return_value=[]),
        patch("os.path.exists", return_value=False),
    ):
        assert service.find_theme_script_path() is None


def test_find_theme_script_path_grub_d_empty(service):
    """Test when /etc/grub.d exists but is empty."""
    with (
        patch("core.services.core_maintenance_service.read_grub_default", return_value={}),
        patch("glob.glob", return_value=[]),
        patch("os.path.exists", side_effect=lambda p: p == "/etc/grub.d"),
        patch("os.listdir", return_value=[]),
    ):
        assert service.find_theme_script_path() is None


def test_find_theme_script_path_grub_d_no_match(service):
    """Test when /etc/grub.d exists but files don't match 'theme'."""
    with (
        patch("core.services.core_maintenance_service.read_grub_default", return_value={}),
        patch("glob.glob", return_value=[]),
        patch("os.path.exists", side_effect=lambda p: p == "/etc/grub.d"),
        patch("os.listdir", return_value=["00_header", "10_linux"]),
        patch("os.path.isfile", return_value=True),
    ):
        assert service.find_theme_script_path() is None


def test_find_theme_script_path_custom_cfg_no_theme_keyword(service):
    """Test when custom.cfg exists but doesn't contain 'theme'."""
    with (
        patch("core.services.core_maintenance_service.read_grub_default", return_value={}),
        patch("glob.glob", side_effect=lambda p: ["/boot/grub/custom.cfg"] if "custom.cfg" in p else []),
        patch("os.path.exists", return_value=False),
        patch("builtins.open", mock_open(read_data="menuentry 'My OS' { ... }")),
    ):
        assert service.find_theme_script_path() is None
