"""Tests pour les filtres tar dans core_grub_default_io."""

import tarfile
from unittest.mock import patch

from core.io.core_grub_default_io import _tar_filter_initial, _tar_filter_manual


class TestTarFilters:
    """Tests pour les fonctions de filtrage tar."""

    def test_tar_filter_initial_access_denied(self):
        """Test _tar_filter_initial quand l'accès est refusé."""
        tarinfo = tarfile.TarInfo(name="/etc/shadow")

        with patch("os.path.exists", return_value=True):
            with patch("os.access", return_value=False):
                result = _tar_filter_initial(tarinfo)
                assert result is None

    def test_tar_filter_initial_os_error(self):
        """Test _tar_filter_initial quand une OSError survient."""
        tarinfo = tarfile.TarInfo(name="/some/file")

        with patch("os.path.exists", side_effect=OSError("Disk error")):
            result = _tar_filter_initial(tarinfo)
            assert result is None

    def test_tar_filter_initial_success(self):
        """Test _tar_filter_initial avec succès."""
        tarinfo = tarfile.TarInfo(name="/some/file")

        with patch("os.path.exists", return_value=True):
            with patch("os.access", return_value=True):
                result = _tar_filter_initial(tarinfo)
                assert result is tarinfo

    def test_tar_filter_manual_access_denied(self):
        """Test _tar_filter_manual quand l'accès est refusé."""
        tarinfo = tarfile.TarInfo(name="/etc/shadow")

        with patch("os.path.exists", return_value=True):
            with patch("os.access", return_value=False):
                result = _tar_filter_manual(tarinfo)
                assert result is None

    def test_tar_filter_manual_os_error(self):
        """Test _tar_filter_manual quand une OSError survient."""
        tarinfo = tarfile.TarInfo(name="/some/file")

        with patch("os.path.exists", side_effect=OSError("Disk error")):
            result = _tar_filter_manual(tarinfo)
            assert result is None

    def test_tar_filter_manual_success(self):
        """Test _tar_filter_manual avec succès."""
        tarinfo = tarfile.TarInfo(name="/some/file")

        with patch("os.path.exists", return_value=True):
            with patch("os.access", return_value=True):
                result = _tar_filter_manual(tarinfo)
                assert result is tarinfo
