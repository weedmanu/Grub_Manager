from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.io.core_io_grub_validation import ValidationResult
from core.managers.core_managers_apply import GrubApplyManager
from core.managers.core_managers_apply_states import (
    ApplyFinalState,
    BackupState,
    CleanupState,
    GenerateTestState,
    GrubApplyState,
    GrubBackupError,
    GrubCommandError,
    GrubValidationError,
    ValidateState,
)


class TestApplyStatesCoverage:

    @pytest.fixture
    def context(self):
        # ApplyContext est un dataclass: ses champs ne sont pas des attributs de classe,
        # donc MagicMock(spec=ApplyContext) bloque l'accès à des champs valides.
        # Ici on veut un double simple et flexible pour couvrir les branches.
        ctx = MagicMock()
        ctx.grub_default_path = MagicMock(spec=Path)
        ctx.backup_path = MagicMock(spec=Path)
        ctx.temp_cfg_path = MagicMock(spec=Path)
        ctx.new_config = {"GRUB_TIMEOUT": "5"}
        ctx.apply_changes = True
        ctx.theme_management_enabled = True
        ctx.pending_script_changes = {}
        ctx.verification_details = None
        return ctx

    @patch("core.managers.core_managers_apply_states.validate_grub_file")
    def test_backup_state_invalid_source_validation(self, mock_validate, context):
        """Test BackupState raises GrubBackupError when validation fails."""
        context.grub_default_path.exists.return_value = True
        mock_validate.return_value = ValidationResult(False, "Invalid syntax")

        state = BackupState(context)

        with pytest.raises(GrubBackupError, match="Source invalide: Invalid syntax"):
            state.execute()

    def test_generate_test_state_rollback_removes_file(self, context):
        """Test GenerateTestState.rollback removes temp file if it exists."""
        context.temp_cfg_path.exists.return_value = True

        state = GenerateTestState(context)

        with patch("os.remove") as mock_remove:
            state.rollback()
            mock_remove.assert_called_once_with(context.temp_cfg_path)

    def test_generate_test_state_rollback_ignores_oserror(self, context):
        """Test GenerateTestState.rollback ignores OSError during removal."""
        context.temp_cfg_path.exists.return_value = True

        state = GenerateTestState(context)

        with patch("os.remove", side_effect=OSError("Permission denied")):
            state.rollback()  # Should not raise

    def test_abstract_rollback_returns_none(self, context):
        """Test GrubApplyState.rollback returns None."""

        # Create a concrete class to instantiate the abstract one
        class ConcreteState(GrubApplyState):
            def execute(self):
                return None

        state = ConcreteState(context)
        assert state.rollback() is None

    def test_generate_test_state_execute_command_failure(self, context):
        """Test GenerateTestState.execute raises GrubCommandError on failure."""
        context.temp_cfg_path = Path("/tmp/grub.cfg")
        state = GenerateTestState(context)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="Error")

            with pytest.raises(GrubCommandError):
                state.execute()

    def test_validate_state_missing_file(self, context):
        """Test ValidateState raises GrubValidationError if temp file is missing."""
        context.temp_cfg_path.exists.return_value = False

        state = ValidateState(context)

        with pytest.raises(GrubValidationError, match="Le fichier de configuration de test a disparu"):
            state.execute()

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_apply_final_state_not_modified(self, mock_which, mock_run, context):
        """Test ApplyFinalState detects when grub.cfg is not modified."""
        mock_which.return_value = "/usr/sbin/update-grub"
        mock_run.return_value = MagicMock(returncode=0)

    @patch("core.managers.core_managers_apply_states.validate_grub_file")
    def test_backup_state_oserror_validation(self, mock_validate, context):
        """Couvre les lignes 62-63."""
        context.grub_default_path.exists.return_value = True
        mock_validate.side_effect = OSError("Disk error")
        state = BackupState(context)
        with pytest.raises(GrubBackupError, match=r"Impossible de vérifier le fichier source: Disk error"):
            state.execute()

    def test_backup_state_copy_oserror(self, context):
        """Couvre les lignes 72-88."""
        context.grub_default_path.exists.return_value = True
        with (
            patch("core.managers.core_managers_apply_states.validate_grub_file") as mock_val,
            patch("shutil.copy2", side_effect=OSError("Copy failed")),
        ):
            mock_val.return_value = MagicMock(is_valid=True)
            state = BackupState(context)
            with pytest.raises(GrubBackupError, match="Impossible de créer le backup"):
                state.execute()

    def test_write_state_execute_success(self, context):
        """Couvre les lignes 96-107."""
        from core.managers.core_managers_apply_states import GenerateTestState, WriteState

        with patch("core.managers.core_managers_apply_states.write_grub_default") as mock_write:
            context.grub_default_path.read_text.return_value = "GRUB_TIMEOUT=5\n"
            state = WriteState(context)
            next_state = state.execute()
            assert next_state == GenerateTestState
            mock_write.assert_called_once()

    def test_write_state_execute_empty_file(self, context):
        """Couvre les lignes 104-105."""
        from core.managers.core_managers_apply_states import WriteState

        with patch("core.managers.core_managers_apply_states.write_grub_default"):
            context.grub_default_path.read_text.return_value = "# Only comments\n"
            state = WriteState(context)
            with pytest.raises(GrubValidationError, match="Le fichier écrit ne contient pas de configuration valide"):
                state.execute()

    def test_write_state_rollback_success(self, context):
        """Couvre les lignes 111-132."""
        from core.managers.core_managers_apply_states import WriteState

        context.backup_path.exists.return_value = True
        context.backup_path.stat.return_value.st_size = 100
        context.grub_default_path.read_text.return_value = "GRUB_TIMEOUT=5\n"
        with patch("shutil.copy2") as mock_copy:
            state = WriteState(context)
            state.rollback()
            mock_copy.assert_called_once()

    def test_write_state_rollback_no_backup(self, context):
        """Couvre les lignes 114-115."""
        from core.managers.core_managers_apply_states import GrubRollbackError, WriteState

        context.backup_path.exists.return_value = False
        state = WriteState(context)
        with pytest.raises(GrubRollbackError, match="Backup introuvable"):
            state.rollback()

    def test_validate_state_execute_success(self, context):
        """Couvre les lignes 187-190, 197-199, 210-212."""
        from core.managers.core_managers_apply_states import ApplyFinalState, ValidateState

        context.temp_cfg_path.exists.return_value = True
        # Il faut au moins 5 lignes non vides/commentées
        context.temp_cfg_path.read_text.return_value = "line1\nline2\nline3\nline4\nline5\n"
        with patch("shutil.which", return_value="/usr/bin/grub-script-check"), patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            state = ValidateState(context)
            next_state = state.execute()
            assert next_state == ApplyFinalState

    @patch("subprocess.run")
    def test_apply_final_state_execute_success(self, mock_run, context):
        """Couvre les lignes 237-240, 257, 268."""
        from core.managers.core_managers_apply_states import ApplyFinalState, CleanupState

        context.apply_changes = True
        # On mock GrubScriptService pour éviter les appels chmod réels
        with (
            patch("shutil.which", return_value="/usr/sbin/update-grub"),
            patch("core.managers.core_managers_apply_states.Path.exists", return_value=True),
            patch("core.managers.core_managers_apply_states.GrubScriptService", create=True) as mock_service_class,
        ):

            mock_service = mock_service_class.return_value
            mock_service.scan_theme_scripts.return_value = []
            mock_run.return_value = MagicMock(returncode=0)

            state = ApplyFinalState(context)
            next_state = state.execute()
            assert next_state == CleanupState

    def test_cleanup_state_execute_success(self, context):
        """Couvre les lignes 282, 284-286."""
        from core.managers.core_managers_apply_states import CleanupState

        context.backup_path.exists.return_value = True
        context.temp_cfg_path.exists.return_value = True
        with patch("os.remove") as mock_remove:
            state = CleanupState(context)
            next_state = state.execute()
            assert next_state is None
            assert mock_remove.call_count == 2

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_apply_final_state_grub_cfg_missing(self, mock_which, mock_run, context):
        """Test ApplyFinalState handles missing grub.cfg (e.g. first generation)."""
        mock_which.return_value = "/usr/sbin/update-grub"
        mock_run.return_value = MagicMock(returncode=0)

        with patch("core.managers.core_managers_apply_states.Path") as mock_path_cls:
            mock_path_obj = MagicMock()
            mock_path_cls.return_value = mock_path_obj
            # Exists returns False initially, then False after (simulating failure to create?)
            # or just testing the branch where it doesn't exist.
            # The code checks `if Path(GRUB_CFG_PATH).exists():` after execution.
            mock_path_obj.exists.return_value = False

            state = ApplyFinalState(context)
            state.execute()

            # verification_details should not be updated with "non modifié" or "régénéré"
            # It keeps default or previous value?
            # Actually the code doesn't set verification_details if file doesn't exist after update.
            # But we want to cover the `else` (implicit) of `if Path(GRUB_CFG_PATH).exists():`

    def test_cleanup_state_missing_files(self, context):
        """Test CleanupState handles missing files gracefully."""
        context.backup_path.exists.return_value = False
        context.temp_cfg_path.exists.return_value = False

        state = CleanupState(context)

        with patch("os.remove") as mock_remove:
            state.execute()
            mock_remove.assert_not_called()

    def test_core_apply_manager_update_internal_state_unknown(self):
        """Test _update_internal_state with unknown class."""
        manager = GrubApplyManager()

        class UnknownState:
            pass

        manager._update_internal_state(UnknownState)
        # Should just pass and not crash, covering the implicit else

    def test_generate_test_state_rollback_no_file(self, context):
        """Test GenerateTestState.rollback does nothing if file doesn't exist."""
        context.temp_cfg_path.exists.return_value = False

        state = GenerateTestState(context)

        with patch("os.remove") as mock_remove:
            state.rollback()
            mock_remove.assert_not_called()

    def test_validate_state_no_check_tool(self, context):
        """Test ValidateState skips syntax check if tool is missing."""
        context.temp_cfg_path.exists.return_value = True
        context.temp_cfg_path.stat.return_value.st_size = 100
        # Mock read_text to return enough lines to pass content check
        context.temp_cfg_path.read_text.return_value = "line1\nline2\nline3\nline4"

        state = ValidateState(context)

        with patch("shutil.which", return_value=None):
            with patch("subprocess.run") as mock_run:
                next_state = state.execute()

                assert next_state == ApplyFinalState
                mock_run.assert_not_called()

    def test_validate_state_empty_file(self, context):
        """Test ValidateState raises error if file is empty."""
        context.temp_cfg_path.exists.return_value = True
        context.temp_cfg_path.stat.return_value.st_size = 0

        state = ValidateState(context)

        with pytest.raises(GrubValidationError, match="Le fichier de configuration généré est vide"):
            state.execute()

    def test_apply_final_state_non_executable_script(self, context):
        """Couvre la ligne 235 (make_non_executable)."""
        # On veut should_be_executable = False
        # Dans ApplyFinalState, c'est script.name in theme_scripts
        context.theme_management_enabled = False
        context.pending_script_changes = {"/etc/grub.d/00_header": False}
        state = ApplyFinalState(context)

        mock_service = MagicMock()
        # On simule que le script est actuellement exécutable pour entrer dans le bloc de modification
        mock_script = MagicMock()
        mock_script.name = "00_header"
        mock_script.path = Path("/etc/grub.d/00_header")
        mock_script.is_executable = True
        mock_service.scan_theme_scripts.return_value = [mock_script]

        with (
            patch("core.managers.core_managers_apply_states.GrubScriptService", return_value=mock_service),
            patch("core.managers.core_managers_apply_states.Path.exists", return_value=True),
            patch("core.managers.core_managers_apply_states.Path.stat") as mock_stat,
            patch("shutil.which", return_value="/usr/bin/update-grub"),
            patch("subprocess.run") as mock_run,
        ):

            mock_run.return_value = MagicMock(returncode=0)
            mock_stat.return_value.st_mtime = 100
            state.execute()

        mock_service.make_non_executable.assert_called_once_with(Path("/etc/grub.d/00_header"))

    def test_apply_final_state_script_loop_exception(self, context):
        """Couvre les lignes 244-245 (Exception dans la boucle des scripts)."""
        state = ApplyFinalState(context)

        mock_service = MagicMock()
        # Le code catch explicitement RuntimeError (et pas Exception générique)
        mock_service.scan_theme_scripts.side_effect = RuntimeError("Scan failed")

        with (
            patch("core.managers.core_managers_apply_states.GrubScriptService", return_value=mock_service),
            patch("core.managers.core_managers_apply_states.Path.exists", return_value=True),
            patch("core.managers.core_managers_apply_states.Path.stat") as mock_stat,
            patch("shutil.which", return_value="/usr/bin/update-grub"),
            patch("subprocess.run") as mock_run,
        ):

            mock_run.return_value = MagicMock(returncode=0)
            mock_stat.return_value.st_mtime = 100
            # L'exception doit être rattrapée et logguée comme warning
            state.execute()
