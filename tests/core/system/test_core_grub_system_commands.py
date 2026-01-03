"""Tests pour les commandes système GRUB."""

from unittest.mock import MagicMock, patch

import pytest

from core.system.core_grub_system_commands import CommandResult, run_update_grub


class TestCommandResult:
    """Tests pour CommandResult."""

    def test_command_result_creation(self):
        """Test création d'un CommandResult."""
        result = CommandResult(0, "stdout content", "stderr content")
        assert result.returncode == 0
        assert result.stdout == "stdout content"
        assert result.stderr == "stderr content"

    def test_command_result_frozen(self):
        """Test que CommandResult est frozen."""
        result = CommandResult(0, "", "")
        with pytest.raises(AttributeError):
            result.returncode = 1


class TestRunUpdateGrub:
    """Tests pour run_update_grub."""

    @patch("core.system.core_grub_system_commands.shutil.which")
    @patch("core.system.core_grub_system_commands.subprocess.run")
    def test_run_update_grub_success(self, mock_subprocess_run, mock_which):
        """Test exécution réussie d'update-grub."""
        mock_which.return_value = "/usr/sbin/update-grub"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Génération du fichier de configuration GRUB..."
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        result = run_update_grub()

        assert result.returncode == 0
        assert result.stdout == "Génération du fichier de configuration GRUB..."
        assert result.stderr == ""
        # On vérifie que which a été appelé avec un path contenant les répertoires sbin
        args, kwargs = mock_which.call_args
        assert args[0] == "update-grub"
        assert "/usr/sbin" in kwargs["path"]
        assert "/sbin" in kwargs["path"]
        
        mock_subprocess_run.assert_called_once_with(
            ["/usr/sbin/update-grub"],
            capture_output=True,
            text=True,
            check=False
        )

    @patch("core.system.core_grub_system_commands.shutil.which")
    @patch("core.system.core_grub_system_commands.subprocess.run")
    def test_run_update_grub_failure_no_stderr(self, mock_subprocess_run, mock_which):
        """Test échec de run_update_grub sans message d'erreur (pour la couverture)."""
        mock_which.return_value = "/usr/sbin/update-grub"
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        result = run_update_grub()

        assert result.returncode == 1
        assert result.stderr == ""

    @patch("core.system.core_grub_system_commands.shutil.which")
    @patch("core.system.core_grub_system_commands.subprocess.run")
    def test_run_update_grub_failure(self, mock_subprocess_run, mock_which):
        """Test exécution échouée d'update-grub."""
        mock_which.return_value = "/usr/sbin/update-grub"
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Erreur: fichier introuvable"
        mock_subprocess_run.return_value = mock_result

        result = run_update_grub()

        assert result.returncode == 1
        assert result.stdout == ""
        assert result.stderr == "Erreur: fichier introuvable"

    @patch("core.system.core_grub_system_commands.shutil.which")
    @patch("core.system.core_grub_system_commands.subprocess.run")
    def test_run_update_grub_command_not_found(self, mock_subprocess_run, mock_which):
        """Test quand update-grub n'est pas trouvé."""
        mock_which.return_value = None
        mock_subprocess_run.side_effect = FileNotFoundError("No such file or directory")

        result = run_update_grub()

        assert result.returncode == 127
        assert result.stdout == ""
        assert "Commande 'update-grub' introuvable" in result.stderr

    @patch("core.system.core_grub_system_commands.shutil.which")
    @patch("core.system.core_grub_system_commands.subprocess.run")
    @patch.dict("core.system.core_grub_system_commands.os.environ", {"PATH": "/custom/path"})
    def test_run_update_grub_custom_path(self, mock_subprocess_run, mock_which):
        """Test avec PATH personnalisé."""
        mock_which.return_value = "/custom/path/update-grub"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "success"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        result = run_update_grub()

        assert result.returncode == 0
        mock_which.assert_called_once_with("update-grub", path="/custom/path:/usr/sbin:/sbin:/usr/bin:/bin")

    @patch("core.system.core_grub_system_commands.shutil.which")
    @patch("core.system.core_grub_system_commands.subprocess.run")
    @patch.dict("core.system.core_grub_system_commands.os.environ", {}, clear=True)
    def test_run_update_grub_no_path_env(self, mock_subprocess_run, mock_which):
        """Test sans variable d'environnement PATH."""
        mock_which.return_value = "/usr/sbin/update-grub"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "success"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        result = run_update_grub()

        assert result.returncode == 0
        mock_which.assert_called_once_with("update-grub", path=":/usr/sbin:/sbin:/usr/bin:/bin")