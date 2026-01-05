"""Tests pour les états de la machine à états d'application GRUB."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.core_exceptions import (
    GrubBackupError,
    GrubCommandError,
    GrubRollbackError,
    GrubValidationError,
)
from core.managers.apply_states import (
    ApplyContext,
    ApplyFinalState,
    BackupState,
    CleanupState,
    GenerateTestState,
    ValidateState,
    WriteState,
)


class TestApplyStates:
    """Tests pour les classes d'état."""

    @pytest.fixture
    def context(self, tmp_path):
        """Fixture pour créer un contexte de test."""
        grub_default = tmp_path / "grub"
        grub_default.write_text("GRUB_TIMEOUT=5")
        return ApplyContext(
            grub_default_path=grub_default,
            backup_path=grub_default.with_suffix(".bak"),
            temp_cfg_path=grub_default.parent / "grub.cfg.test",
            new_config={"GRUB_TIMEOUT": "10"},
            apply_changes=True,
        )

    # === BackupState ===

    def test_backup_state_success(self, context):
        """Test BackupState avec succès."""
        state = BackupState(context)

        with patch("core.managers.apply_states.validate_grub_file") as mock_val:
            mock_val.return_value.is_valid = True

            next_state = state.execute()

            assert next_state == WriteState
            assert context.backup_path.exists()
            assert context.backup_path.read_text() == "GRUB_TIMEOUT=5"

    def test_backup_state_missing_file(self, context):
        """Test BackupState avec fichier manquant."""
        context.grub_default_path.unlink()
        state = BackupState(context)

        with pytest.raises(GrubBackupError, match="n'existe pas"):
            state.execute()

    def test_backup_state_invalid_source(self, context):
        """Test BackupState avec source invalide."""
        state = BackupState(context)

        with patch("core.managers.apply_states.validate_grub_file") as mock_val:
            mock_val.return_value.is_valid = False
            mock_val.return_value.error_message = "Invalid"

            with pytest.raises(GrubBackupError, match="Source invalide"):
                state.execute()

    def test_backup_state_validation_oserror(self, context):
        """Test BackupState avec erreur OS durant validation."""
        state = BackupState(context)

        with patch("core.managers.apply_states.validate_grub_file", side_effect=OSError("Disk error")):
            with pytest.raises(OSError, match="Disk error"):
                state.execute()

    def test_backup_state_copy_failure(self, context):
        """Test BackupState avec échec de copie."""
        state = BackupState(context)

        with patch("core.managers.apply_states.validate_grub_file") as mock_val:
            mock_val.return_value.is_valid = True
            with patch("shutil.copy2", side_effect=OSError("Copy failed")):
                with pytest.raises(GrubBackupError, match="Impossible de créer le backup"):
                    state.execute()

    def test_backup_state_incomplete_copy(self, context):
        """Test BackupState avec copie incomplète."""
        state = BackupState(context)

        with patch("core.managers.apply_states.validate_grub_file") as mock_val:
            mock_val.return_value.is_valid = True
            # Mock stat to return different sizes
            # We provide enough values to avoid StopIteration if called multiple times
            with patch.object(Path, "stat") as mock_stat:
                mock_stat.side_effect = [
                    MagicMock(st_size=100),  # source (before copy)
                    MagicMock(st_size=50),  # backup (after copy)
                    MagicMock(st_size=100),  # extra safety
                    MagicMock(st_size=100),  # extra safety
                ]
                with patch("shutil.copy2"):  # Mock copy to do nothing
                    with pytest.raises(GrubBackupError, match="backup est incomplet"):
                        state.execute()

    # === WriteState ===

    def test_write_state_success(self, context):
        """Test WriteState avec succès."""
        state = WriteState(context)

        with patch("core.managers.apply_states.write_grub_default") as mock_write:
            # Mock read_text to return valid content after write
            with patch.object(Path, "read_text", return_value="GRUB_TIMEOUT=10\n"):
                next_state = state.execute()

                assert next_state == GenerateTestState
                mock_write.assert_called_once()

    def test_write_state_empty_result(self, context):
        """Test WriteState avec résultat vide."""
        state = WriteState(context)

        with patch("core.managers.apply_states.write_grub_default"):
            with patch.object(Path, "read_text", return_value=""):
                with pytest.raises(GrubValidationError, match="ne contient pas de configuration valide"):
                    state.execute()

    def test_write_state_rollback_success(self, context):
        """Test WriteState.rollback avec succès."""
        state = WriteState(context)
        context.backup_path.write_text("BACKUP")

        state.rollback()

        assert context.grub_default_path.read_text() == "BACKUP"

    def test_write_state_rollback_missing_backup(self, context):
        """Test WriteState.rollback avec backup manquant."""
        state = WriteState(context)
        # Backup not created

        with pytest.raises(GrubRollbackError, match="Backup introuvable"):
            state.rollback()

    def test_write_state_rollback_failure(self, context):
        """Test WriteState.rollback avec échec de copie."""
        state = WriteState(context)
        context.backup_path.write_text("BACKUP")

        with patch("shutil.copy2", side_effect=OSError("Restore failed")):
            with pytest.raises(GrubRollbackError, match="Impossible de restaurer"):
                state.rollback()

    # === GenerateTestState ===

    def test_generate_test_state_success(self, context):
        """Test GenerateTestState avec succès."""
        state = GenerateTestState(context)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0

            # Mock temp file existence
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "stat", return_value=MagicMock(st_size=100)):
                    next_state = state.execute()
                    assert next_state == ValidateState

    def test_generate_test_state_command_failure(self, context):
        """Test GenerateTestState avec échec commande."""
        state = GenerateTestState(context)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "Error"

            with pytest.raises(GrubCommandError, match="grub-mkconfig a échoué"):
                state.execute()

    def test_generate_test_state_empty_output(self, context):
        """Test GenerateTestState avec sortie vide."""
        state = GenerateTestState(context)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0

            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "stat", return_value=MagicMock(st_size=0)):
                    with pytest.raises(GrubValidationError, match="vide ou absent"):
                        state.execute()

    def test_generate_test_state_rollback(self, context):
        """Test GenerateTestState.rollback (nettoyage)."""
        state = GenerateTestState(context)
        context.temp_cfg_path.write_text("TEMP")

        state.rollback()

        assert not context.temp_cfg_path.exists()

    # === ValidateState ===

    def test_validate_state_success(self, context):
        """Test ValidateState avec succès."""
        state = ValidateState(context)
        context.temp_cfg_path.write_text("menuentry 'Linux' {\n}\n### BEGIN /etc/ ###\n# Comment\nset timeout=5")

        with patch("shutil.which", return_value="/usr/bin/grub-script-check"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0

                next_state = state.execute()
                assert next_state == ApplyFinalState

    def test_validate_state_missing_file(self, context):
        """Test ValidateState avec fichier manquant."""
        state = ValidateState(context)
        # temp file not created

        with pytest.raises(GrubValidationError, match="disparu"):
            state.execute()

    def test_validate_state_syntax_error(self, context):
        """Test ValidateState avec erreur syntaxe."""
        state = ValidateState(context)
        context.temp_cfg_path.write_text("content")

        with patch("shutil.which", return_value="/usr/bin/grub-script-check"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 1
                mock_run.return_value.stderr = "Syntax error"

                with pytest.raises(GrubValidationError, match="Validation syntaxique échouée"):
                    state.execute()

    def test_validate_state_incomplete_content(self, context):
        """Test ValidateState avec contenu incomplet."""
        state = ValidateState(context)
        context.temp_cfg_path.write_text("Too short")

        with patch("shutil.which", return_value=None):  # Skip syntax check
            with pytest.raises(GrubValidationError, match="incomplète"):
                state.execute()

    def test_validate_state_read_error(self, context):
        """Test ValidateState avec erreur lecture."""
        state = ValidateState(context)
        context.temp_cfg_path.write_text("content")

        with patch("shutil.which", return_value=None):
            with patch.object(Path, "read_text", side_effect=OSError("Read failed")):
                with pytest.raises(GrubValidationError, match="Erreur de lecture"):
                    state.execute()

    # === ApplyFinalState ===

    def test_apply_final_state_success(self, context):
        """Test ApplyFinalState avec succès."""
        state = ApplyFinalState(context)

        # Create dummy file for mtime check
        context.temp_cfg_path.write_text("content")

        with patch("shutil.which", return_value="/usr/sbin/update-grub"):
            with patch("subprocess.run") as mock_run:
                # Simulate file modification by update-grub
                def mock_run_side_effect(*args, **kwargs):
                    # Update the file to change its mtime
                    context.temp_cfg_path.write_text("updated content")
                    result = MagicMock()
                    result.returncode = 0
                    return result
                
                mock_run.side_effect = mock_run_side_effect

                with patch("core.managers.apply_states.GRUB_CFG_PATH", str(context.temp_cfg_path)):
                    next_state = state.execute()
                    assert next_state == CleanupState
                    assert "✓" in str(context.verification_details)

    def test_apply_final_state_skip(self, context):
        """Test ApplyFinalState ignoré."""
        context.apply_changes = False
        state = ApplyFinalState(context)

        next_state = state.execute()
        assert next_state == CleanupState
        assert "update-grub non exécuté" in str(context.verification_details)

    def test_apply_final_state_failure(self, context):
        """Test ApplyFinalState avec échec."""
        state = ApplyFinalState(context)

        with patch("shutil.which", return_value="/usr/sbin/update-grub"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 1
                mock_run.return_value.stderr = "Update failed"

                with pytest.raises(GrubCommandError, match="Mise à jour finale échouée"):
                    state.execute()

    def test_apply_final_state_script_exception_handling(self, context):
        """Test ApplyFinalState avec exception lors de la modification des scripts."""
        state = ApplyFinalState(context)

        # Mock script_service pour lever une exception
        with (
            patch("core.managers.apply_states.GrubScriptService") as mock_svc_class,
            patch("core.managers.apply_states.shutil.which", return_value="/usr/sbin/update-grub"),
            patch("core.managers.apply_states.subprocess.run") as mock_run,
        ):
            mock_svc = MagicMock()
            mock_svc_class.return_value = mock_svc

            # Script exception
            mock_svc.scan_theme_scripts.return_value = [
                MagicMock(name="test", path="/etc/grub.d/test", is_executable=False)
            ]
            mock_svc.make_executable.side_effect = Exception("Permission denied")

            mock_run.return_value = MagicMock(returncode=0, stderr="")

            # Should not raise, logs warning and continues
            next_state = state.execute()
            assert next_state is not None

    # === CleanupState ===

    def test_cleanup_state(self, context):
        """Test CleanupState."""
        state = CleanupState(context)
        context.backup_path.write_text("BAK")
        context.temp_cfg_path.write_text("TMP")

        state.execute()

        assert not context.backup_path.exists()
        assert not context.temp_cfg_path.exists()

    def test_cleanup_state_error(self, context):
        """Test CleanupState avec erreur (ne doit pas lever)."""
        state = CleanupState(context)
        context.backup_path.write_text("BAK")

        with patch("os.remove", side_effect=OSError("Delete failed")):
            state.execute()  # Should not raise

    def test_cleanup_state_no_temp_file(self, context):
        """Test CleanupState sans fichier temporaire."""
        state = CleanupState(context)
        context.backup_path.write_text("BAK")
        # temp_cfg_path does not exist

        state.execute()
        assert not context.backup_path.exists()

    def test_write_state_rollback_empty_backup(self, context):
        """Test WriteState.rollback avec backup vide."""
        state = WriteState(context)
        context.backup_path.write_text("")

        with pytest.raises(GrubRollbackError, match="vide"):
            state.rollback()

    def test_write_state_rollback_restored_invalid(self, context):
        """Test WriteState.rollback avec fichier restauré invalide."""
        state = WriteState(context)
        context.backup_path.write_text("# Comment only")

        with pytest.raises(GrubRollbackError, match="invalide"):
            state.rollback()

    def test_write_state_rollback_restored_empty_lines(self, context):
        """Test WriteState.rollback avec fichier restauré vide de sens."""
        state = WriteState(context)
        context.backup_path.write_text("# Just a comment\n\n")

        with pytest.raises(GrubRollbackError, match="invalide"):
            state.rollback()
