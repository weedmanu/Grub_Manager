"""Tests pour le service de scripts GRUB."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.core_exceptions import GrubCommandError, GrubScriptNotFoundError
from core.services.core_services_grub_script import EXECUTABLE_PERMISSION, GrubScript, GrubScriptService


class TestGrubScript:
    """Tests pour la dataclass GrubScript."""

    def test_grub_script_str(self):
        """Test la représentation textuelle."""
        script = GrubScript(name="test", path=Path("/tmp/test"), is_executable=True)
        assert str(script) == "test (actif)"

        script.is_executable = False
        assert str(script) == "test (inactif)"


class TestGrubScriptService:
    """Tests pour le service GrubScriptService."""

    @pytest.fixture
    def service(self):
        """Fixture pour le service."""
        return GrubScriptService(Path("/tmp/grub.d"))

    def test_initialization(self):
        """Test l'initialisation."""
        service = GrubScriptService()
        assert service.script_dir == Path("/etc/grub.d")

        custom_service = GrubScriptService(Path("/custom/path"))
        assert custom_service.script_dir == Path("/custom/path")

    def test_scan_theme_scripts_dir_not_exists(self, service):
        """Test le scan quand le répertoire n'existe pas."""
        with patch.object(Path, "exists", return_value=False):
            scripts = service.scan_theme_scripts()
            assert scripts == []

    def test_scan_theme_scripts_success(self, service):
        """Test le scan réussi."""
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "glob") as mock_glob:
                # Mock des fichiers trouvés
                file1 = MagicMock(spec=Path)
                file1.is_file.return_value = True
                file1.name = "05_theme"
                file1.stat.return_value.st_mode = EXECUTABLE_PERMISSION

                file2 = MagicMock(spec=Path)
                file2.is_file.return_value = True
                file2.name = "06_theme"
                file2.stat.return_value.st_mode = 0  # Non exécutable

                file3 = MagicMock(spec=Path)
                file3.is_file.return_value = False  # Pas un fichier

                mock_glob.return_value = [file1, file2, file3]

                scripts = service.scan_theme_scripts()

                assert len(scripts) == 2
                assert scripts[0].name == "05_theme"
                assert scripts[0].is_executable is True
                assert scripts[1].name == "06_theme"
                assert scripts[1].is_executable is False

    @patch("subprocess.run")
    def test_make_executable_success(self, mock_run, service):
        """Test make_executable succès."""
        path = Path("/tmp/script")

        result = service.make_executable(path)

        assert result is True
        mock_run.assert_called_once_with(
            ["chmod", "+x", str(path)],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_make_executable_error(self, mock_run, service):
        """Test make_executable erreur subprocess."""
        path = Path("/tmp/script")
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr="error")

        with pytest.raises(GrubCommandError) as exc:
            service.make_executable(path)

        assert "Échec chmod +x" in str(exc.value)

    @patch("subprocess.run")
    def test_make_executable_permission_error(self, mock_run, service):
        """Test make_executable erreur permission."""
        path = Path("/tmp/script")
        mock_run.side_effect = PermissionError("denied")

        with pytest.raises(PermissionError):
            service.make_executable(path)

    @patch("subprocess.run")
    def test_make_executable_not_found(self, mock_run, service):
        """Test make_executable fichier non trouvé."""
        path = Path("/tmp/script")
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(GrubScriptNotFoundError):
            service.make_executable(path)

    @patch("subprocess.run")
    def test_make_non_executable_success(self, mock_run, service):
        """Test make_non_executable succès."""
        path = Path("/tmp/script")

        result = service.make_non_executable(path)

        assert result is True
        mock_run.assert_called_once_with(
            ["chmod", "-x", str(path)],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_make_non_executable_error(self, mock_run, service):
        """Test make_non_executable erreur."""
        path = Path("/tmp/script")
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr="error")

        with pytest.raises(GrubCommandError):
            service.make_non_executable(path)

    @patch("subprocess.run")
    def test_make_non_executable_permission_error(self, mock_run, service):
        """Test make_non_executable erreur permission."""
        path = Path("/tmp/script")
        mock_run.side_effect = PermissionError("denied")

        with pytest.raises(PermissionError):
            service.make_non_executable(path)

    @patch("subprocess.run")
    def test_make_non_executable_not_found(self, mock_run, service):
        """Test make_non_executable fichier non trouvé."""
        path = Path("/tmp/script")
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(GrubScriptNotFoundError):
            service.make_non_executable(path)

    def test_is_executable(self, service):
        """Test is_executable."""
        path = MagicMock(spec=Path)

        # Cas n'existe pas
        path.exists.return_value = False
        assert service.is_executable(path) is False

        # Cas existe et exécutable
        path.exists.return_value = True
        path.stat.return_value.st_mode = EXECUTABLE_PERMISSION
        assert service.is_executable(path) is True

        # Cas existe et non exécutable
        path.stat.return_value.st_mode = 0
        assert service.is_executable(path) is False
