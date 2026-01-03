"""Tests pour les exceptions personnalisées de Grub Manager."""

import pytest

from core.core_exceptions import (
    GrubBackupError,
    GrubCommandError,
    GrubConfigError,
    GrubManagerError,
    GrubParsingError,
    GrubPermissionError,
    GrubScriptNotFoundError,
    GrubSyncError,
    GrubThemeError,
    GrubValidationError,
)


class TestGrubManagerError:
    """Tests pour l'exception de base GrubManagerError."""

    def test_grub_manager_error_basic(self):
        """Test l'exception de base."""
        error = GrubManagerError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_grub_manager_error_inheritance(self):
        """Test que toutes les exceptions héritent de GrubManagerError."""
        exceptions = [
            GrubConfigError("config error"),
            GrubScriptNotFoundError("script not found"),
            GrubPermissionError("permission denied"),
            GrubParsingError("parsing failed"),
            GrubBackupError("backup failed"),
            GrubThemeError("theme error"),
            GrubCommandError("command failed"),
            GrubSyncError("sync error"),
            GrubValidationError("validation error"),
        ]

        for exc in exceptions:
            assert isinstance(exc, GrubManagerError)


class TestGrubConfigError:
    """Tests pour GrubConfigError."""

    def test_grub_config_error(self):
        """Test GrubConfigError."""
        error = GrubConfigError("Configuration invalide")
        assert str(error) == "Configuration invalide"
        assert isinstance(error, GrubManagerError)


class TestGrubScriptNotFoundError:
    """Tests pour GrubScriptNotFoundError."""

    def test_grub_script_not_found_error(self):
        """Test GrubScriptNotFoundError."""
        error = GrubScriptNotFoundError("Script 10_linux manquant")
        assert str(error) == "Script 10_linux manquant"
        assert isinstance(error, GrubManagerError)


class TestGrubPermissionError:
    """Tests pour GrubPermissionError."""

    def test_grub_permission_error(self):
        """Test GrubPermissionError."""
        error = GrubPermissionError("Privilèges root requis")
        assert str(error) == "Privilèges root requis"
        assert isinstance(error, GrubManagerError)


class TestGrubParsingError:
    """Tests pour GrubParsingError."""

    def test_grub_parsing_error(self):
        """Test GrubParsingError."""
        error = GrubParsingError("Erreur de syntaxe ligne 42")
        assert str(error) == "Erreur de syntaxe ligne 42"
        assert isinstance(error, GrubManagerError)


class TestGrubBackupError:
    """Tests pour GrubBackupError."""

    def test_grub_backup_error(self):
        """Test GrubBackupError."""
        error = GrubBackupError("Échec de la sauvegarde")
        assert str(error) == "Échec de la sauvegarde"
        assert isinstance(error, GrubManagerError)


class TestGrubThemeError:
    """Tests pour GrubThemeError."""

    def test_grub_theme_error(self):
        """Test GrubThemeError."""
        error = GrubThemeError("Thème corrompu")
        assert str(error) == "Thème corrompu"
        assert isinstance(error, GrubManagerError)


class TestGrubCommandError:
    """Tests pour GrubCommandError."""

    def test_grub_command_error_basic(self):
        """Test GrubCommandError basique."""
        error = GrubCommandError("Commande échouée")
        assert str(error) == "Commande échouée"
        assert error.command is None
        assert error.returncode is None
        assert error.stderr is None

    def test_grub_command_error_with_command(self):
        """Test GrubCommandError avec commande."""
        error = GrubCommandError("Échec", command="update-grub")
        assert "Échec" in str(error)
        assert "Commande: update-grub" in str(error)
        assert error.command == "update-grub"
        assert error.returncode is None
        assert error.stderr is None

    def test_grub_command_error_with_returncode(self):
        """Test GrubCommandError avec code de retour."""
        error = GrubCommandError("Échec", returncode=1)
        assert "Échec" in str(error)
        assert "Code retour: 1" in str(error)
        assert error.command is None
        assert error.returncode == 1
        assert error.stderr is None

    def test_grub_command_error_with_stderr(self):
        """Test GrubCommandError avec stderr."""
        error = GrubCommandError("Échec", stderr="Erreur fatale")
        assert "Échec" in str(error)
        assert "Stderr: Erreur fatale" in str(error)
        assert error.command is None
        assert error.returncode is None
        assert error.stderr == "Erreur fatale"

    def test_grub_command_error_with_all_fields(self):
        """Test GrubCommandError avec tous les champs."""
        error = GrubCommandError(
            "Commande échouée",
            command="grub-install",
            returncode=2,
            stderr="Disque non trouvé"
        )
        error_str = str(error)
        assert "Commande échouée" in error_str
        assert "Commande: grub-install" in error_str
        assert "Code retour: 2" in error_str
        assert "Stderr: Disque non trouvé" in error_str

    def test_grub_command_error_stderr_truncation(self):
        """Test la troncature du stderr dans __str__."""
        long_stderr = "x" * 300
        error = GrubCommandError("Échec", stderr=long_stderr)
        error_str = str(error)
        # Vérifier que stderr est tronqué à 200 caractères
        assert "Stderr: " + "x" * 200 in error_str
        assert len(error_str.split("Stderr: ")[1]) == 200


class TestGrubSyncError:
    """Tests pour GrubSyncError."""

    def test_grub_sync_error(self):
        """Test GrubSyncError."""
        error = GrubSyncError("Fichiers désynchronisés")
        assert str(error) == "Fichiers désynchronisés"
        assert isinstance(error, GrubManagerError)


class TestGrubValidationError:
    """Tests pour GrubValidationError."""

    def test_grub_validation_error(self):
        """Test GrubValidationError."""
        error = GrubValidationError("Timeout invalide")
        assert str(error) == "Timeout invalide"
        assert isinstance(error, GrubManagerError)