"""Tests pour core/apply_manager.py - Gestionnaire d'application sécurisée."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

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
    def manager(self):
        """Fixture pour créer une instance de GrubApplyManager."""
        return GrubApplyManager("/tmp/test_grub")

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

    def test_transition_to(self, manager):
        """Vérifie les transitions d'état."""
        assert manager._state == ApplyState.IDLE
        manager._transition_to(ApplyState.BACKUP)
        assert manager._state == ApplyState.BACKUP

    @patch("core.managers.core_apply_manager.shutil.copy2")
    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    @patch("core.managers.core_apply_manager.Path.read_text")
    def test_create_backup_success(self, mock_read, mock_stat, mock_exists, mock_copy, manager):
        """Vérifie la création réussie d'un backup."""
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 100
        mock_read.return_value = "GRUB_TIMEOUT=5\n"

        manager._create_backup()

        mock_copy.assert_called_once_with(manager.grub_default_path, manager.backup_path)

    @patch("core.managers.core_apply_manager.Path.exists")
    def test_create_backup_file_missing(self, mock_exists, manager):
        """Vérifie que _create_backup échoue si le fichier n'existe pas."""
        mock_exists.return_value = False
        with pytest.raises(FileNotFoundError):
            manager._create_backup()

    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    def test_create_backup_empty_source(self, mock_stat, mock_exists, manager):
        """Vérifie que _create_backup échoue si la source est vide."""
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 0
        with pytest.raises(RuntimeError, match="Le fichier source est vide"):
            manager._create_backup()

    @patch("core.managers.core_apply_manager.subprocess.run")
    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="menuentry 'Ubuntu' {\n}\n### BEGIN /etc/\n### END /etc/\nlinux /boot/vmlinuz",
    )
    def test_generate_test_config_success(self, mock_file, mock_stat, mock_exists, mock_run, manager):
        """Vérifie la génération réussie de la config de test."""
        mock_run.return_value.returncode = 0
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 200

        manager._generate_test_config()

        mock_run.assert_called_once()
        assert "grub-mkconfig" in mock_run.call_args[0][0]

    @patch("core.managers.core_apply_manager.subprocess.run")
    def test_generate_test_config_failure(self, mock_run, manager):
        """Vérifie l'échec de grub-mkconfig."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Error"

        with pytest.raises(RuntimeError, match="grub-mkconfig a échoué"):
            manager._generate_test_config()

    @patch("core.managers.core_apply_manager.shutil.which")
    @patch("core.managers.core_apply_manager.subprocess.run")
    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="menuentry 'Ubuntu' {\n}\n### BEGIN /etc/\n### END /etc/\nlinux /boot/vmlinuz",
    )
    def test_validate_config_success(self, mock_file, mock_stat, mock_exists, mock_run, mock_which, manager):
        """Vérifie la validation réussie."""
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 200
        mock_which.return_value = "/usr/bin/grub-script-check"
        mock_run.return_value.returncode = 0

        manager._validate_config()

        mock_run.assert_called_once()

    @patch("core.managers.core_apply_manager.Path.exists")
    def test_validate_config_missing_file(self, mock_exists, manager):
        """Vérifie l'échec si le fichier de test manque."""
        mock_exists.return_value = False
        with pytest.raises(RuntimeError, match="Le fichier de configuration de test a disparu"):
            manager._validate_config()

    @patch("core.managers.core_apply_manager.shutil.which")
    @patch("core.managers.core_apply_manager.subprocess.run")
    def test_apply_final_update_grub(self, mock_run, mock_which, manager):
        """Vérifie l'application finale avec update-grub."""
        mock_which.return_value = "/usr/sbin/update-grub"
        mock_run.return_value.returncode = 0

        manager._apply_final()

        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == ["/usr/sbin/update-grub"]

    @patch("core.managers.core_apply_manager.shutil.which")
    @patch("core.managers.core_apply_manager.subprocess.run")
    def test_apply_final_grub_mkconfig(self, mock_run, mock_which, manager):
        """Vérifie l'application finale avec grub-mkconfig si update-grub absent."""
        mock_which.return_value = None
        mock_run.return_value.returncode = 0

        manager._apply_final()

        mock_run.assert_called_once()
        assert "grub-mkconfig" in mock_run.call_args[0][0][0]

    @patch("core.managers.core_apply_manager.shutil.copy2")
    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    @patch("core.managers.core_apply_manager.Path.read_text")
    def test_rollback_success(self, mock_read, mock_stat, mock_exists, mock_copy, manager):
        """Vérifie le rollback réussi."""
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 100
        mock_read.return_value = "GRUB_TIMEOUT=5\n"

        manager._rollback()

        assert mock_copy.call_count >= 1

    @patch("core.managers.core_apply_manager.Path.exists")
    def test_rollback_no_backup(self, mock_exists, manager):
        """Vérifie l'échec du rollback sans backup."""
        mock_exists.return_value = False
        with pytest.raises(FileNotFoundError):
            manager._rollback()

    @patch("core.managers.core_apply_manager.write_grub_default")
    @patch("core.managers.core_apply_manager.GrubApplyManager._create_backup")
    @patch("core.managers.core_apply_manager.GrubApplyManager._generate_test_config")
    @patch("core.managers.core_apply_manager.GrubApplyManager._validate_config")
    @patch("core.managers.core_apply_manager.GrubApplyManager._apply_final")
    @patch("core.managers.core_apply_manager.GrubApplyManager._cleanup_backup")
    @patch("core.managers.core_apply_manager.Path.read_text")
    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    def test_apply_configuration_full_success(
        self,
        mock_stat,
        mock_exists,
        mock_read,
        mock_cleanup,
        mock_apply,
        mock_validate,
        mock_generate,
        mock_backup,
        mock_write,
        manager,
    ):
        """Vérifie le workflow complet avec succès."""
        mock_read.return_value = "GRUB_TIMEOUT=5\n"
        mock_exists.return_value = True

        # Calls to stat:
        # 1. Before apply: st_mtime
        # 2. After apply: st_mtime
        # 3. After apply: st_size
        mock_stat.side_effect = [MagicMock(st_mtime=100), MagicMock(st_mtime=200), MagicMock(st_size=200)]

        result = manager.apply_configuration({"GRUB_TIMEOUT": "5"})

        assert result.success is True
        assert result.state == ApplyState.SUCCESS
        mock_backup.assert_called_once()
        mock_write.assert_called_once()
        mock_generate.assert_called_once()
        mock_validate.assert_called_once()
        mock_apply.assert_called_once()
        mock_cleanup.assert_called_once()

    def test_apply_configuration_empty_config(self, manager):
        """Vérifie le rejet d'une config vide."""
        result = manager.apply_configuration({})
        assert result.success is False
        assert result.state == ApplyState.ERROR
        assert "Configuration fournie est vide" in str(result.details) or "Configuration fournie est vide" in str(
            result.message
        )

    @patch("core.managers.core_apply_manager.write_grub_default")
    @patch("core.managers.core_apply_manager.shutil.copy2")
    @patch("core.managers.core_apply_manager.shutil.which")
    @patch("core.managers.core_apply_manager.subprocess.run")
    @patch("core.managers.core_apply_manager.os.remove")
    @patch("core.managers.core_apply_manager.Path.read_text")
    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="menuentry 'Ubuntu' {\n}\n### BEGIN /etc/\n### END /etc/\nlinux /boot/vmlinuz",
    )
    def test_apply_configuration_integration_mocked(
        self,
        mock_file,
        mock_stat,
        mock_exists,
        mock_read,
        mock_remove,
        mock_run,
        mock_which,
        mock_copy,
        mock_write,
        manager,
    ):
        """Test d'intégration avec mocks bas niveau pour couvrir la logique interne."""
        # Setup mocks
        mock_exists.return_value = True
        mock_read.return_value = "GRUB_TIMEOUT=5\n"
        mock_which.return_value = "/usr/sbin/update-grub"
        mock_run.return_value.returncode = 0

        # Stat calls sequence is complex, let's try to provide enough valid returns
        # We need to ensure st_size > 0 for checks
        mock_stat.return_value.st_size = 100
        mock_stat.return_value.st_mtime = 100

        # Run
        result = manager.apply_configuration({"GRUB_TIMEOUT": "10"})

        # Assert
        assert result.success is True
        assert result.state == ApplyState.SUCCESS

        # Verify flow
        mock_copy.assert_called()  # Backup
        mock_write.assert_called()  # Write temp
        mock_run.assert_called()  # Generate test & Validate & Apply
        mock_remove.assert_called()  # Cleanup

    @patch("core.managers.core_apply_manager.write_grub_default")
    @patch("core.managers.core_apply_manager.shutil.copy2")
    @patch("core.managers.core_apply_manager.shutil.which")
    @patch("core.managers.core_apply_manager.subprocess.run")
    @patch("core.managers.core_apply_manager.Path.read_text")
    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    def test_apply_configuration_integration_generate_failure(
        self, mock_stat, mock_exists, mock_read, mock_run, mock_which, mock_copy, mock_write, manager
    ):
        """Test échec génération config."""
        mock_exists.return_value = True
        mock_read.return_value = "GRUB_TIMEOUT=5\n"
        mock_stat.return_value.st_size = 100

        # grub-mkconfig fails
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Error generating config"

        result = manager.apply_configuration({"GRUB_TIMEOUT": "10"})

        assert result.success is False
        assert result.state == ApplyState.ROLLBACK
        assert "grub-mkconfig a échoué" in str(result.message) or "grub-mkconfig a échoué" in str(result.details)

    @patch("core.managers.core_apply_manager.write_grub_default")
    @patch("core.managers.core_apply_manager.shutil.copy2")
    @patch("core.managers.core_apply_manager.shutil.which")
    @patch("core.managers.core_apply_manager.subprocess.run")
    @patch("core.managers.core_apply_manager.Path.read_text")
    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    @patch("builtins.open", new_callable=mock_open, read_data="line1\nline2\nline3\nline4\nline5")
    def test_apply_configuration_integration_validate_failure(
        self, mock_file, mock_stat, mock_exists, mock_read, mock_run, mock_which, mock_copy, mock_write, manager
    ):
        """Test échec validation config (syntaxe invalide)."""
        mock_exists.return_value = True
        mock_read.return_value = "GRUB_TIMEOUT=5\n"
        mock_stat.return_value.st_size = 100
        mock_which.return_value = "/usr/bin/grub-script-check"

        # 1. grub-mkconfig (success)
        # 2. grub-script-check (failure)
        mock_run.side_effect = [MagicMock(returncode=0), MagicMock(returncode=1, stderr="Syntax error")]

        result = manager.apply_configuration({"GRUB_TIMEOUT": "10"})

        assert result.success is False
        assert result.state == ApplyState.ROLLBACK
        assert "Validation syntaxique échouée" in str(result.message) or "Validation syntaxique échouée" in str(
            result.details
        )

    @patch("core.managers.core_apply_manager.write_grub_default")
    @patch("core.managers.core_apply_manager.GrubApplyManager._create_backup")
    @patch("core.managers.core_apply_manager.GrubApplyManager._rollback")
    def test_apply_configuration_write_failure(self, mock_rollback, mock_backup, mock_write, manager):
        """Vérifie le rollback en cas d'échec d'écriture."""
        mock_write.side_effect = OSError("Write error")

        result = manager.apply_configuration({"GRUB_TIMEOUT": "5"})

        assert result.success is False
        assert result.state == ApplyState.ROLLBACK
        mock_rollback.assert_called_once()

    @patch("core.managers.core_apply_manager.write_grub_default")
    @patch("core.managers.core_apply_manager.GrubApplyManager._create_backup")
    @patch("core.managers.core_apply_manager.GrubApplyManager._generate_test_config")
    @patch("core.managers.core_apply_manager.GrubApplyManager._validate_config")
    @patch("core.managers.core_apply_manager.Path.read_text")
    def test_apply_configuration_no_apply_changes(
        self, mock_read, mock_validate, _mock_gen, mock_backup, mock_write, manager
    ):
        """Test avec apply_changes=False (112->135)."""
        mock_read.return_value = "GRUB_TIMEOUT=5\n"
        result = manager.apply_configuration({"GRUB_TIMEOUT": "5"}, apply_changes=False)
        assert result.success is True
        assert result.state == ApplyState.SUCCESS
        assert "Configuration validée" in result.details

    @patch("core.managers.core_apply_manager.write_grub_default")
    @patch("core.managers.core_apply_manager.GrubApplyManager._create_backup")
    @patch("core.managers.core_apply_manager.GrubApplyManager._rollback")
    def test_apply_configuration_rollback_failure(self, mock_rollback, mock_backup, mock_write, manager):
        """Test échec du rollback (162-164)."""
        mock_write.side_effect = RuntimeError("Write error")
        mock_rollback.side_effect = RuntimeError("Rollback failed")

        result = manager.apply_configuration({"GRUB_TIMEOUT": "5"})
        assert result.success is False
        assert result.state == ApplyState.ERROR
        assert "Rollback échoué" in result.details

    @patch("core.managers.core_apply_manager.Path.read_text")
    @patch("core.managers.core_apply_manager.Path.stat")
    @patch("core.managers.core_apply_manager.Path.exists")
    def test_create_backup_no_config_lines(self, mock_exists, mock_stat, mock_read, manager):
        """Test backup avec source sans config (206-207)."""
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 100
        mock_read.return_value = "# Only comments\n\n"
        with pytest.raises(RuntimeError, match="Le fichier source ne contient pas de configuration valide"):
            manager._create_backup()

    @patch("core.managers.core_apply_manager.shutil.copy2")
    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    @patch("core.managers.core_apply_manager.Path.read_text")
    def test_create_backup_size_mismatch(self, mock_read, mock_stat, mock_exists, mock_copy, manager):
        """Test backup avec taille incorrecte (217-218)."""
        mock_exists.return_value = True
        mock_stat.side_effect = [MagicMock(st_size=100), MagicMock(st_size=50)]  # Source=100, Backup=50
        mock_read.return_value = "CONFIG=1"
        with pytest.raises(RuntimeError, match="Le backup est incomplet"):
            manager._create_backup()

    @patch("core.managers.core_apply_manager.shutil.copy2")
    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    @patch("core.managers.core_apply_manager.Path.read_text")
    def test_create_backup_os_error(self, mock_read, mock_stat, mock_exists, mock_copy, manager):
        """Test backup avec erreur OS (221-223)."""
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 100
        mock_read.return_value = "CONFIG=1"
        mock_copy.side_effect = OSError("Permission denied")
        with pytest.raises(OSError):
            manager._create_backup()

    @patch("core.managers.core_apply_manager.subprocess.run")
    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    def test_generate_test_config_empty_output(self, mock_stat, mock_exists, mock_run, manager):
        """Test génération config vide (237-238)."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 0
        with pytest.raises(RuntimeError, match="Le fichier de configuration généré est vide ou absent"):
            manager._generate_test_config()

    @patch("core.managers.core_apply_manager.subprocess.run")
    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    @patch("builtins.open", new_callable=mock_open, read_data="line1\nline2")
    def test_generate_test_config_too_short(self, mock_file, mock_stat, mock_exists, mock_run, manager):
        """Test génération config trop courte (248-251)."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 100
        with pytest.raises(RuntimeError, match="Le fichier de configuration généré est anormalement court"):
            manager._generate_test_config()

    @patch("core.managers.core_apply_manager.subprocess.run")
    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    def test_generate_test_config_read_error(self, mock_stat, mock_exists, mock_run, manager):
        """Test erreur lecture config générée (262-264)."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 100
        with patch("builtins.open", side_effect=OSError("Read error")):
            with pytest.raises(RuntimeError, match="Impossible de valider le fichier généré"):
                manager._generate_test_config()

    @patch("core.managers.core_apply_manager.write_grub_default")
    @patch("core.managers.core_apply_manager.Path.read_text")
    def test_apply_configuration_written_file_empty(self, mock_read, mock_write, manager):
        """Test apply_configuration avec fichier écrit vide (91-92)."""
        manager._transition_to = MagicMock()
        manager._create_backup = MagicMock()
        mock_read.return_value = "# Only comments\n\n"

        result = manager.apply_configuration({"GRUB_TIMEOUT": "5", "GRUB_DEFAULT": "0"})

        assert result.success is False
        assert "Le fichier écrit ne contient pas de configuration valide" in result.message

    @patch("core.managers.core_apply_manager.GRUB_CFG_PATH", "/tmp/grub.cfg")
    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    @patch("core.managers.core_apply_manager.Path.read_text")
    @patch("core.managers.core_apply_manager.write_grub_default")
    def test_apply_configuration_grub_cfg_not_exists_after_apply(
        self, mock_write, mock_read, mock_stat, mock_exists, manager
    ):
        """Test apply_configuration où grub.cfg n'existe pas après application (112->135)."""
        manager._create_backup = MagicMock()
        manager._generate_test_config = MagicMock()
        manager._validate_config = MagicMock()
        manager._apply_final = MagicMock()
        manager._cleanup_backup = MagicMock()

        # mock_exists.side_effect:
        # 1. Path(GRUB_CFG_PATH).exists() before apply (in apply_configuration) -> True
        # 2. Path(GRUB_CFG_PATH).exists() after apply (in apply_configuration) -> False
        mock_exists.side_effect = [True, False]
        mock_stat.return_value.st_mtime = 1000
        mock_read.return_value = "GRUB_TIMEOUT=5\nGRUB_DEFAULT=0"

        result = manager.apply_configuration({"GRUB_TIMEOUT": "5", "GRUB_DEFAULT": "0"}, apply_changes=True)

        assert result.success is True
        assert result.details is None  # verification_details remains None if not exists

    @patch("core.managers.core_apply_manager.Path.read_text")
    @patch("core.managers.core_apply_manager.Path.stat")
    def test_create_backup_read_os_error(self, mock_stat, mock_read, manager):
        """Test _create_backup avec OSError sur read_text (206-207)."""
        mock_stat.return_value.st_size = 100
        mock_read.side_effect = OSError("Read failure")
        with pytest.raises(OSError, match="Read failure"):
            manager._create_backup()

    @patch("core.managers.core_apply_manager.shutil.copy2")
    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    @patch("core.managers.core_apply_manager.Path.read_text")
    def test_rollback_source_not_exists(self, mock_read, mock_stat, mock_exists, mock_copy, manager):
        """Test _rollback quand le fichier source n'existe pas (389->398)."""
        # mock_exists:
        # 1. self.backup_path.exists() -> True
        # 2. self.grub_default_path.exists() -> False
        mock_exists.side_effect = [True, False]
        mock_stat.return_value.st_size = 100
        mock_read.return_value = "RESTORED=1"

        manager._rollback()

        # Verify copy2 was called only once (for restoration, not for archiving)
        assert mock_copy.call_count == 1
        mock_copy.assert_called_with(manager.backup_path, manager.grub_default_path)

    @patch("core.managers.core_apply_manager.shutil.copy2")
    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    @patch("core.managers.core_apply_manager.Path.read_text")
    def test_rollback_archive_os_error(self, mock_read, mock_stat, mock_exists, mock_copy, manager):
        """Test _rollback avec erreur lors de l'archivage du fichier corrompu (396-397)."""
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 100
        mock_read.return_value = "RESTORED=1"

        # side_effect for copy2:
        # 1. shutil.copy2(self.grub_default_path, corrupted_backup) -> OSError
        # 2. shutil.copy2(self.backup_path, self.grub_default_path) -> Success
        mock_copy.side_effect = [OSError("Archive failed"), None]

        manager._rollback()

        assert mock_copy.call_count == 2

    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    def test_validate_config_empty(self, mock_stat, mock_exists, manager):
        """Test validation config vide (280-281)."""
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 0
        with pytest.raises(RuntimeError, match="Le fichier de configuration généré est vide"):
            manager._validate_config()

    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    @patch("core.managers.core_apply_manager.shutil.which", return_value=None)
    @patch("builtins.open", new_callable=mock_open, read_data="line1\nline2\nline3\nline4\nline5")
    def test_validate_config_small_and_no_check(self, mock_file, mock_which, mock_stat, mock_exists, manager):
        """Test validation petit fichier et pas de grub-script-check (284, 302)."""
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 50  # < 100
        manager._validate_config()  # Ne devrait pas lever d'exception

    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    @patch("core.managers.core_apply_manager.shutil.which", return_value=None)
    @patch("builtins.open", new_callable=mock_open, read_data="line1\nline2")
    def test_validate_config_missing_markers_and_too_minimal(
        self, mock_file, mock_which, mock_stat, mock_exists, manager
    ):
        """Test validation marqueurs manquants et trop minimal (324, 327-333)."""
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 200
        with pytest.raises(RuntimeError, match="La configuration générée semble incomplète"):
            manager._validate_config()

    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    @patch("core.managers.core_apply_manager.shutil.which", return_value=None)
    def test_validate_config_read_error(self, mock_which, mock_stat, mock_exists, manager):
        """Test erreur lecture pendant validation (333-337)."""
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 200
        with patch("builtins.open", side_effect=OSError("Read error")):
            with pytest.raises(RuntimeError, match="Erreur de lecture du fichier de configuration"):
                manager._validate_config()

    @patch("core.managers.core_apply_manager.shutil.which", return_value=None)
    @patch("core.managers.core_apply_manager.subprocess.run")
    def test_apply_final_no_update_grub(self, mock_run, mock_which, manager):
        """Test apply_final sans update-grub (362-363)."""
        mock_run.return_value = MagicMock(returncode=1, stderr="Error")
        with pytest.raises(RuntimeError, match="Mise à jour finale échouée"):
            manager._apply_final()

    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    def test_rollback_empty_backup(self, mock_stat, mock_exists, manager):
        """Test rollback avec backup vide (378-379)."""
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 0
        with pytest.raises(RuntimeError, match="Le fichier de sauvegarde est vide"):
            manager._rollback()

    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    def test_rollback_os_error(self, mock_stat, mock_exists, manager):
        """Test rollback avec erreur OS (381-383)."""
        mock_exists.return_value = True
        mock_stat.side_effect = OSError("Stat error")
        with pytest.raises(OSError):
            manager._rollback()

    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    @patch("core.managers.core_apply_manager.shutil.copy2")
    @patch("core.managers.core_apply_manager.Path.read_text")
    def test_rollback_archive_error(self, mock_read, mock_copy, mock_stat, mock_exists, manager):
        """Test rollback avec erreur d'archivage (389->398, 394-395)."""
        mock_exists.side_effect = [True, True, True]  # backup, grub_default, grub_default
        mock_stat.return_value.st_size = 100
        mock_copy.side_effect = [OSError("Archive error"), None]  # 1er copy2 échoue, 2ème réussit
        mock_read.return_value = "RESTORED=1"

        manager._rollback()  # Ne devrait pas lever d'exception car l'erreur d'archivage est catchée

    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.Path.stat")
    @patch("core.managers.core_apply_manager.shutil.copy2")
    @patch("core.managers.core_apply_manager.Path.read_text")
    def test_rollback_restored_invalid(self, mock_read, mock_copy, mock_stat, mock_exists, manager):
        """Test rollback avec restauration invalide (408-409)."""
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 100
        mock_read.return_value = "# Empty restored file"
        with pytest.raises(RuntimeError, match="Le fichier restauré est invalide"):
            manager._rollback()

    @patch("core.managers.core_apply_manager.Path.exists")
    @patch("core.managers.core_apply_manager.os.remove")
    def test_cleanup_backup_error(self, mock_remove, mock_exists, manager):
        """Test cleanup avec erreur (423-424)."""
        mock_exists.return_value = True
        mock_remove.side_effect = OSError("Remove error")
        manager._cleanup_backup()  # Ne devrait pas lever d'exception
