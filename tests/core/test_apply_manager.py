"""Tests pour core/apply_manager.py - Gestionnaire d'application sécurisée."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from core.apply_manager import ApplyResult, ApplyState, GrubApplyManager


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

    def test_initialization_default_path(self):
        """Vérifie l'initialisation avec le chemin par défaut."""
        manager = GrubApplyManager()
        assert manager._state == ApplyState.IDLE
        assert str(manager.grub_default_path).endswith("/grub")

    def test_initialization_custom_path(self):
        """Vérifie l'initialisation avec un chemin personnalisé."""
        custom_path = "/tmp/test_grub"
        manager = GrubApplyManager(custom_path)
        assert manager.grub_default_path == Path(custom_path)
        assert manager.backup_path == Path("/tmp/test_grub.bak.apply")

    def test_transition_to(self):
        """Vérifie les transitions d'état."""
        manager = GrubApplyManager()
        assert manager._state == ApplyState.IDLE

        manager._transition_to(ApplyState.BACKUP)
        assert manager._state == ApplyState.BACKUP

        manager._transition_to(ApplyState.SUCCESS)
        assert manager._state == ApplyState.SUCCESS

    def test_create_backup_file_missing(self):
        """Vérifie que _create_backup échoue si le fichier n'existe pas."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "missing.grub"
            manager = GrubApplyManager(str(test_file))

            with pytest.raises(FileNotFoundError):
                manager._create_backup()

    def test_create_backup_success(self):
        """Vérifie la création réussie d'un backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.grub"
            test_file.write_text("GRUB_TIMEOUT=5\n")

            manager = GrubApplyManager(str(test_file))
            manager._create_backup()

            assert manager.backup_path.exists()
            assert manager.backup_path.read_text() == "GRUB_TIMEOUT=5\n"

    def test_rollback_restores_original(self):
        """Vérifie que le rollback restaure le fichier original."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.grub"
            test_file.write_text("GRUB_TIMEOUT=5\n")

            manager = GrubApplyManager(str(test_file))
            manager._create_backup()

            # Modifier le fichier
            test_file.write_text("GRUB_TIMEOUT=10\n")
            assert test_file.read_text() == "GRUB_TIMEOUT=10\n"

            # Rollback
            manager._rollback()
            assert test_file.read_text() == "GRUB_TIMEOUT=5\n"

    def test_rollback_without_backup(self):
        """Vérifie que rollback gère l'absence de backup de manière sécurisée."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.grub"
            test_file.write_text("GRUB_TIMEOUT=5\n")

            manager = GrubApplyManager(str(test_file))
            # Pas de backup créé

            # Le rollback devrait lever une exception (situation critique)
            with pytest.raises(FileNotFoundError):
                manager._rollback()

    def test_cleanup_backup(self):
        """Vérifie la suppression du backup temporaire."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.grub"
            test_file.write_text("GRUB_TIMEOUT=5\n")

            manager = GrubApplyManager(str(test_file))
            manager._create_backup()

            assert manager.backup_path.exists()
            manager._cleanup_backup()
            assert not manager.backup_path.exists()

    def test_apply_configuration_requires_root(self):
        """Vérifie que apply_configuration échoue sans root (grub-mkconfig)."""
        if os.geteuid() == 0:
            pytest.skip("Test doit être lancé sans root")

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.grub"
            test_file.write_text("GRUB_TIMEOUT=5\n")

            manager = GrubApplyManager(str(test_file))
            config = {"GRUB_TIMEOUT": "10", "GRUB_DEFAULT": "0"}

            result = manager.apply_configuration(config, apply_changes=False)

            # Devrait échouer à l'étape grub-mkconfig
            assert result.success is False
            assert result.state in (ApplyState.ROLLBACK, ApplyState.ERROR)

    def test_apply_configuration_rollback_on_error(self):
        """Vérifie que le rollback est activé en cas d'erreur."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.grub"
            test_file.write_text("GRUB_TIMEOUT=5\n")

            manager = GrubApplyManager(str(test_file))
            config = {"GRUB_TIMEOUT": "10", "GRUB_DEFAULT": "0"}

            manager.apply_configuration(config, apply_changes=False)

            # En cas d'échec, le fichier doit être restauré
            assert test_file.read_text() == "GRUB_TIMEOUT=5\n"
