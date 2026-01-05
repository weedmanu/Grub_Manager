"""Tests pour le contrôleur de permissions."""

from unittest.mock import MagicMock, patch

import pytest

from ui.controllers.permission_controller import PermissionController
from ui.ui_infobar_controller import WARNING


class TestPermissionController:
    """Tests pour PermissionController."""

    def test_is_root_true(self):
        """Test is_root quand l'utilisateur est root."""
        with patch("os.geteuid", return_value=0):
            ctrl = PermissionController()
            assert ctrl.is_root() is True
            # Test du cache (deuxième appel)
            assert ctrl.is_root() is True

    def test_is_root_false(self):
        """Test is_root quand l'utilisateur n'est pas root."""
        with patch("os.geteuid", return_value=1000):
            ctrl = PermissionController()
            assert ctrl.is_root() is False
            # Test du cache (deuxième appel)
            assert ctrl.is_root() is False

    def test_check_and_warn_root(self):
        """Test check_and_warn quand root."""
        with patch("os.geteuid", return_value=0):
            ctrl = PermissionController()
            callback = MagicMock()
            
            result = ctrl.check_and_warn(callback)
            
            assert result is True
            callback.assert_not_called()

    def test_check_and_warn_non_root(self):
        """Test check_and_warn quand non root."""
        with patch("os.geteuid", return_value=1000):
            ctrl = PermissionController()
            callback = MagicMock()
            
            result = ctrl.check_and_warn(callback)
            
            assert result is False
            callback.assert_called_once()
            args = callback.call_args[0]
            assert "Attention" in args[0]
            assert args[1] == WARNING

    def test_can_modify_system(self):
        """Test can_modify_system."""
        with patch("os.geteuid", return_value=0):
            ctrl = PermissionController()
            assert ctrl.can_modify_system() is True

        with patch("os.geteuid", return_value=1000):
            ctrl = PermissionController()
            assert ctrl.can_modify_system() is False
