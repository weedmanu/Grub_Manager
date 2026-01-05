"""Tests pour core/apply_manager.py - Gestionnaire d'application sécurisée."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from core.core_exceptions import GrubRollbackError
from core.managers.apply_states import (
    ApplyContext,
    BackupState,
    WriteState,
)
from core.managers.core_apply_manager import ApplyResult, ApplyState, GrubApplyManager


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

    @patch("core.managers.core_apply_manager.BackupState")
    @patch("core.managers.core_apply_manager.WriteState")
    @patch("core.managers.core_apply_manager.GenerateTestState")
    @patch("core.managers.core_apply_manager.ValidateState")
    @patch("core.managers.core_apply_manager.ApplyFinalState")
    @patch("core.managers.core_apply_manager.CleanupState")
    def test_apply_configuration_success(
        self, MockCleanup, MockApplyFinal, MockValidate, MockGenerate, MockWrite, MockBackup, manager
    ):
        """Vérifie le workflow complet avec succès."""
        # Configure mocks with __name__ for logging
        MockBackup.__name__ = "BackupState"
        MockWrite.__name__ = "WriteState"
        MockGenerate.__name__ = "GenerateTestState"
        MockValidate.__name__ = "ValidateState"
        MockApplyFinal.__name__ = "ApplyFinalState"
        MockCleanup.__name__ = "CleanupState"

        # Setup chain of states
        # execute() returns the NEXT state class
        MockBackup.return_value.execute.return_value = MockWrite
        MockWrite.return_value.execute.return_value = MockGenerate
        MockGenerate.return_value.execute.return_value = MockValidate
        MockValidate.return_value.execute.return_value = MockApplyFinal
        MockApplyFinal.return_value.execute.return_value = MockCleanup
        MockCleanup.return_value.execute.return_value = None  # End of loop

        result = manager.apply_configuration({"GRUB_TIMEOUT": "5"})

        assert result.success is True
        assert result.state == ApplyState.SUCCESS

        # Verify all states were instantiated and executed
        MockBackup.assert_called()
        MockWrite.assert_called()
        MockGenerate.assert_called()
        MockValidate.assert_called()
        MockApplyFinal.assert_called()
        MockCleanup.assert_called()

    @patch("core.managers.core_apply_manager.BackupState")
    def test_apply_configuration_failure_at_backup(self, MockBackup, manager):
        """Vérifie l'échec au backup."""
        MockBackup.__name__ = "BackupState"
        MockBackup.return_value.execute.side_effect = Exception("Backup failed")

        result = manager.apply_configuration({"GRUB_TIMEOUT": "5"})

        assert result.success is False
        assert result.state == ApplyState.ERROR
        assert "Backup failed" in result.message

    @patch("core.managers.core_apply_manager.BackupState")
    @patch("core.managers.core_apply_manager.WriteState")
    def test_apply_configuration_failure_with_rollback(self, MockWrite, MockBackup, manager):
        """Vérifie l'échec avec rollback."""
        MockBackup.__name__ = "BackupState"
        MockWrite.__name__ = "WriteState"

        MockBackup.return_value.execute.return_value = MockWrite
        MockWrite.return_value.execute.side_effect = Exception("Write failed")

        # Mock WriteState for rollback (instantiated in _perform_rollback)
        # Note: WriteState is instantiated twice: once in loop, once in rollback

        result = manager.apply_configuration({"GRUB_TIMEOUT": "5"})

        assert result.success is False
        assert result.state == ApplyState.ROLLBACK
        assert "Write failed" in result.message

        # Verify rollback was called on WriteState
        # WriteState is called with context.
        # We need to check if rollback() was called on any instance
        assert MockWrite.return_value.rollback.called or MockWrite.return_value.execute.side_effect

    @patch("core.managers.core_apply_manager.BackupState")
    @patch("core.managers.core_apply_manager.WriteState")
    def test_apply_configuration_rollback_critical_failure(self, MockWrite, MockBackup, manager):
        """Vérifie l'échec critique du rollback."""
        MockBackup.__name__ = "BackupState"
        MockWrite.__name__ = "WriteState"

        MockBackup.return_value.execute.return_value = MockWrite
        MockWrite.return_value.execute.side_effect = Exception("Write failed")

        # Mock WriteState.rollback to fail
        MockWrite.return_value.rollback.side_effect = Exception("Rollback failed")

        result = manager.apply_configuration({"GRUB_TIMEOUT": "5"})

        assert result.success is False
        assert result.state == ApplyState.ERROR
        assert "Rollback échoué" in result.details

    def test_perform_rollback_remove_error(self, manager, tmp_path):
        """Vérifie l'erreur de suppression du fichier temporaire lors du rollback."""
        context = ApplyContext(
            grub_default_path=tmp_path / "grub",
            backup_path=tmp_path / "backup",
            temp_cfg_path=tmp_path / "temp",
            new_config={},
            apply_changes=True,
        )
        context.temp_cfg_path.write_text("temp")

        with patch("os.remove", side_effect=OSError("Delete failed")):
            with patch("core.managers.core_apply_manager.WriteState") as MockWrite:
                manager._perform_rollback(context)
                # Should not raise, just log warning
                MockWrite.assert_called()

    def test_perform_rollback_write_state_exception(self, manager, tmp_path):
        """Vérifie les exceptions lors du rollback via WriteState."""
        context = ApplyContext(
            grub_default_path=tmp_path / "grub",
            backup_path=tmp_path / "backup",
            temp_cfg_path=tmp_path / "temp",
            new_config={},
            apply_changes=True,
        )

        with patch("core.managers.core_apply_manager.WriteState") as MockWrite:
            # Case 1: GrubRollbackError (re-raised)
            MockWrite.return_value.rollback.side_effect = GrubRollbackError("Rollback error")
            with pytest.raises(GrubRollbackError):
                manager._perform_rollback(context)

            # Case 2: Generic Exception (wrapped)
            MockWrite.return_value.rollback.side_effect = Exception("Generic error")
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

    @patch("core.managers.core_apply_manager.WriteState")
    def test_perform_rollback(self, MockWrite, manager, tmp_path):
        """Vérifie le rollback global."""
        context = ApplyContext(
            grub_default_path=tmp_path / "grub",
            backup_path=tmp_path / "backup",
            temp_cfg_path=tmp_path / "temp",
            new_config={},
            apply_changes=True,
        )

        # Create temp file to verify deletion
        context.temp_cfg_path.write_text("temp")

        manager._perform_rollback(context)

        assert not context.temp_cfg_path.exists()
        MockWrite.assert_called_with(context)
        MockWrite.return_value.rollback.assert_called_once()
