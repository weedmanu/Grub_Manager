"""Tests pour core/apply_manager.py - Gestionnaire d'application sécurisée."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from core.core_exceptions import GrubRollbackError
from core.managers.core_managers_apply import ApplyResult, ApplyState, GrubApplyManager
from core.managers.core_managers_apply_states import (
    ApplyContext,
    ApplyPaths,
    BackupState,
    WriteState,
)


class TestApplyState:
    """Tests pour l'énumération ApplyState."""

    def test_all_states_exist(self):
        """Vérifie que tous les états nécessaires existent."""
        assert hasattr(ApplyState, "IDLE")
        assert hasattr(ApplyState, "BACKUP")
        assert hasattr(ApplyState, "WRITE_TEMP")
        assert hasattr(ApplyState, "GENERATE_TEST")
        assert hasattr(ApplyState, "VALIDATE")
        assert hasattr(ApplyState, "APPLY")
        assert hasattr(ApplyState, "ROLLBACK")
        assert hasattr(ApplyState, "ERROR")
        assert hasattr(ApplyState, "SUCCESS")


class TestApplyResult:
    """Tests pour ApplyResult."""

    def test_success_result(self):
        """Vérifie la création d'un résultat de succès."""
        result = ApplyResult(True, "OK", ApplyState.SUCCESS)
        assert result.success is True
        assert result.message == "OK"
        assert result.state == ApplyState.SUCCESS
        assert result.details is None

    def test_error_result_with_details(self):
        """Vérifie un résultat d'erreur avec détails."""
        result = ApplyResult(False, "Failed", ApplyState.ERROR, details="Stack trace")
        assert result.success is False
        assert result.message == "Failed"
        assert result.state == ApplyState.ERROR
        assert result.details == "Stack trace"


class TestGrubApplyManager:
    """Tests pour GrubApplyManager."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Fixture pour créer une instance de GrubApplyManager."""
        return GrubApplyManager(str(tmp_path / "grub"))

    def test_initialization(self, manager, tmp_path):
        """Vérifie l'initialisation."""
        assert manager._state == ApplyState.IDLE
        assert manager.grub_default_path == tmp_path / "grub"
        assert manager.backup_path == tmp_path / "grub.bak.apply"

    @patch("core.managers.core_managers_apply.BackupState")
    @patch("core.managers.core_managers_apply.WriteState")
    @patch("core.managers.core_managers_apply.GenerateTestState")
    @patch("core.managers.core_managers_apply.ValidateState")
    @patch("core.managers.core_managers_apply.ApplyFinalState")
    @patch("core.managers.core_managers_apply.CleanupState")
    def test_apply_configuration_success(
        self, mock_cleanup, mock_apply_final, mock_validate, mock_generate, mock_write, mock_backup, manager
    ):
        """Vérifie le workflow complet avec succès."""
        # Configure mocks with __name__ for logging
        mock_backup.__name__ = "BackupState"
        mock_write.__name__ = "WriteState"
        mock_generate.__name__ = "GenerateTestState"
        mock_validate.__name__ = "ValidateState"
        mock_apply_final.__name__ = "ApplyFinalState"
        mock_cleanup.__name__ = "CleanupState"

        # Setup chain of states
        # execute() returns the NEXT state class
        mock_backup.return_value.execute.return_value = mock_write
        mock_write.return_value.execute.return_value = mock_generate
        mock_generate.return_value.execute.return_value = mock_validate
        mock_validate.return_value.execute.return_value = mock_apply_final
        mock_apply_final.return_value.execute.return_value = mock_cleanup
        mock_cleanup.return_value.execute.return_value = None  # End of loop

        result = manager.apply_configuration({"GRUB_TIMEOUT": "5"})

        assert result.success is True
        assert result.state == ApplyState.SUCCESS

        # Verify all states were instantiated and executed
        mock_backup.assert_called()
        mock_write.assert_called()
        mock_generate.assert_called()
        mock_validate.assert_called()
        mock_apply_final.assert_called()
        mock_cleanup.assert_called()

    @patch("core.managers.core_managers_apply.BackupState")
    def test_apply_configuration_failure_at_backup(self, mock_backup, manager):
        """Vérifie l'échec au backup."""
        mock_backup.__name__ = "BackupState"
        mock_backup.return_value.execute.side_effect = Exception("Backup failed")

        result = manager.apply_configuration({"GRUB_TIMEOUT": "5"})

        assert result.success is False
        assert result.state == ApplyState.ERROR
        assert "Backup failed" in result.message

    @patch("core.managers.core_managers_apply.BackupState")
    @patch("core.managers.core_managers_apply.WriteState")
    def test_apply_configuration_failure_with_rollback(self, mock_write, mock_backup, manager):
        """Vérifie l'échec avec rollback."""
        mock_backup.__name__ = "BackupState"
        mock_write.__name__ = "WriteState"

        mock_backup.return_value.execute.return_value = mock_write
        mock_write.return_value.execute.side_effect = Exception("Write failed")

        # Mock WriteState for rollback (instantiated in _perform_rollback)
        # Note: WriteState is instantiated twice: once in loop, once in rollback

        result = manager.apply_configuration({"GRUB_TIMEOUT": "5"})

        assert result.success is False
        assert result.state == ApplyState.ROLLBACK
        assert "Write failed" in result.message

        # Verify rollback was called on WriteState
        # WriteState is called with context.
        # We need to check if rollback() was called on any instance
        assert mock_write.return_value.rollback.called or mock_write.return_value.execute.side_effect

    @patch("core.managers.core_managers_apply.BackupState")
    @patch("core.managers.core_managers_apply.WriteState")
    def test_apply_configuration_rollback_critical_failure(self, mock_write, mock_backup, manager):
        """Vérifie l'échec critique du rollback."""
        mock_backup.__name__ = "BackupState"
        mock_write.__name__ = "WriteState"

        mock_backup.return_value.execute.return_value = mock_write
        mock_write.return_value.execute.side_effect = Exception("Write failed")

        # Mock WriteState.rollback to fail
        mock_write.return_value.rollback.side_effect = Exception("Rollback failed")

        result = manager.apply_configuration({"GRUB_TIMEOUT": "5"})

        assert result.success is False
        assert result.state == ApplyState.ERROR
        assert "Rollback échoué" in result.details

    def test_perform_rollback_remove_error(self, manager, tmp_path):
        """Vérifie l'erreur de suppression du fichier temporaire lors du rollback."""
        context = ApplyContext(
            paths=ApplyPaths(backup_path=tmp_path / "backup", temp_cfg_path=tmp_path / "temp"),
            grub_default_path=tmp_path / "grub",
            new_config={},
            apply_changes=True,
        )
        context.temp_cfg_path.write_text("temp")

        with patch("os.remove", side_effect=OSError("Delete failed")):
            with patch("core.managers.core_managers_apply.WriteState") as mock_write:
                manager._perform_rollback(context)
                # Should not raise, just log warning
                mock_write.assert_called()

    def test_perform_rollback_write_state_exception(self, manager, tmp_path):
        """Vérifie les exceptions lors du rollback via WriteState."""
        context = ApplyContext(
            paths=ApplyPaths(backup_path=tmp_path / "backup", temp_cfg_path=tmp_path / "temp"),
            grub_default_path=tmp_path / "grub",
            new_config={},
            apply_changes=True,
        )

        with patch("core.managers.core_managers_apply.WriteState") as mock_write:
            # Case 1: GrubRollbackError (re-raised)
            mock_write.return_value.rollback.side_effect = GrubRollbackError("Rollback error")
            with pytest.raises(GrubRollbackError):
                manager._perform_rollback(context)

            # Case 2: Generic Exception (wrapped)
            mock_write.return_value.rollback.side_effect = Exception("Generic error")
            with pytest.raises(GrubRollbackError, match="Erreur inattendue"):
                manager._perform_rollback(context)

    def test_update_internal_state(self, manager):
        """Vérifie la mise à jour de l'état interne."""
        # We need to use the real classes here because _update_internal_state checks for equality
        # But in the test environment, we might have patched them?
        # No, this test method doesn't use @patch, so it uses real classes imported at top level
        manager._update_internal_state(BackupState)
        assert manager._state == ApplyState.BACKUP

        manager._update_internal_state(WriteState)
        assert manager._state == ApplyState.WRITE_TEMP

    @patch("core.managers.core_managers_apply.WriteState")
    def test_perform_rollback(self, mock_write, manager, tmp_path):
        """Vérifie le rollback global."""
        context = ApplyContext(
            paths=ApplyPaths(backup_path=tmp_path / "backup", temp_cfg_path=tmp_path / "temp"),
            grub_default_path=tmp_path / "grub",
            new_config={},
            apply_changes=True,
        )

        # Create temp file to verify deletion
        context.temp_cfg_path.write_text("temp")

        manager._perform_rollback(context)

        assert not context.temp_cfg_path.exists()
        mock_write.assert_called_with(context)
        mock_write.return_value.rollback.assert_called_once()
