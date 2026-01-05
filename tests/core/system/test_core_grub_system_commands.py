"""Tests pour core/grub.py - Façade principale."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.system.core_system_grub_commands import CommandResult, run_update_grub


class TestCommandResult:
    """Tests pour CommandResult."""

    def test_creation(self):
        """Vérifie la création d'un CommandResult."""
        result = CommandResult(returncode=0, stdout="OK", stderr="")
        assert result.returncode == 0
        assert result.stdout == "OK"
        assert result.stderr == ""

    def test_frozen_dataclass(self):
        """Vérifie que CommandResult est immuable."""
        result = CommandResult(returncode=0, stdout="OK", stderr="")
        with pytest.raises(AttributeError):
            result.returncode = 1


class TestRunUpdateGrub:
    """Tests pour run_update_grub."""

    @patch("core.system.core_system_grub_commands.subprocess.run")
    @patch("core.system.core_system_grub_commands.shutil.which")
    def test_success(self, mock_which, mock_run):
        """Vérifie l'exécution réussie d'update-grub."""
        mock_which.return_value = "/usr/sbin/update-grub"
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Generating grub configuration file ...\ndone\n", stderr=""
        )

        result = run_update_grub()

        assert result.returncode == 0
        assert "Generating grub" in result.stdout
        assert result.stderr == ""
        mock_run.assert_called_once()

    @patch("core.system.core_system_grub_commands.subprocess.run")
    @patch("core.system.core_system_grub_commands.shutil.which")
    def test_failure(self, mock_which, mock_run):
        """Vérifie le cas d'échec d'update-grub."""
        mock_which.return_value = "/usr/sbin/update-grub"
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error: permission denied")

        result = run_update_grub()

        assert result.returncode == 1
        assert result.stderr == "Error: permission denied"

    @patch("core.system.core_system_grub_commands.subprocess.run")
    @patch("core.system.core_system_grub_commands.shutil.which")
    def test_failure_no_stderr(self, mock_which, mock_run):
        """Vérifie le cas d'échec d'update-grub sans sortie d'erreur."""
        mock_which.return_value = "/usr/sbin/update-grub"
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")

        result = run_update_grub()

        assert result.returncode == 1
        assert result.stderr == ""

    @patch("core.system.core_system_grub_commands.subprocess.run")
    @patch("core.system.core_system_grub_commands.shutil.which")
    def test_command_not_found(self, mock_which, mock_run):
        """Vérifie le cas où update-grub n'est pas trouvé."""
        mock_which.return_value = None
        mock_run.side_effect = FileNotFoundError("update-grub not found")

        result = run_update_grub()

        # La fonction devrait gérer l'exception et retourner un code d'erreur
        assert result.returncode != 0

    @patch("core.system.core_system_grub_commands.subprocess.run")
    @patch("core.system.core_system_grub_commands.shutil.which")
    def test_uses_expanded_path(self, mock_which, mock_run):
        """Vérifie que la recherche utilise un PATH élargi."""
        mock_which.return_value = "/usr/sbin/update-grub"
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        run_update_grub()

        # Vérifier que shutil.which a été appelé avec un path parameter
        call_args = mock_which.call_args
        assert call_args is not None
        assert "path" in call_args.kwargs
        # Le path doit contenir /usr/sbin
        assert "/usr/sbin" in call_args.kwargs["path"]


class TestImports:
    """Tests pour les imports de la façade."""

    def test_all_exports_exist(self):
        """Vérifie que tous les exports de __all__ sont disponibles."""
        import core.system.core_system_grub_commands
        from core.system.core_system_grub_commands import __all__

        for name in __all__:
            assert hasattr(core.system.core_system_grub_commands, name), f"{name} n'est pas exporté"

    def test_grub_default_functions(self):
        """Vérifie que les fonctions grub_default sont disponibles."""
        from core.system.core_system_grub_commands import (
            format_grub_default,
            parse_grub_default,
            read_grub_default,
            write_grub_default,
        )

        assert callable(format_grub_default)
        assert callable(parse_grub_default)
        assert callable(read_grub_default)
        assert callable(write_grub_default)

    def test_grub_menu_functions(self):
        """Vérifie que les fonctions grub_menu sont disponibles."""
        from core.system.core_system_grub_commands import (
            GrubDefaultChoice,
            read_grub_default_choices,
            read_grub_default_choices_with_source,
        )

        assert GrubDefaultChoice is not None
        assert callable(read_grub_default_choices)
        assert callable(read_grub_default_choices_with_source)

    def test_model_functions(self):
        """Vérifie que les fonctions model sont disponibles."""
        from core.system.core_system_grub_commands import (
            GrubUiModel,
            GrubUiState,
            load_grub_ui_state,
            save_grub_ui_state,
        )

        assert GrubUiModel is not None
        assert GrubUiState is not None
        assert callable(load_grub_ui_state)
        assert callable(save_grub_ui_state)

    def test_paths_constants(self):
        """Vérifie que les constantes de chemin sont disponibles."""
        from core.system.core_system_grub_commands import GRUB_CFG_PATH, GRUB_DEFAULT_PATH

        assert isinstance(GRUB_CFG_PATH, str)
        assert isinstance(GRUB_DEFAULT_PATH, str)
        assert GRUB_DEFAULT_PATH == "/etc/default/grub"
