"""Tests pour les opérations I/O sur /etc/default/grub."""

import os
import tempfile
from unittest.mock import patch

import pytest

from core.io.core_grub_default_io import (
    _best_fallback_for_missing_config,
    _prune_manual_backups,
    _touch_now,
    create_grub_default_backup,
    delete_grub_default_backup,
    ensure_initial_grub_default_backup,
    format_grub_default,
    list_grub_default_backups,
    parse_grub_default,
    read_grub_default,
    write_grub_default,
)


class TestTouchNow:
    """Tests pour _touch_now."""

    def test_touch_now_success(self):
        """Test _touch_now avec succès."""
        with tempfile.NamedTemporaryFile() as f:
            original_mtime = os.path.getmtime(f.name)
            _touch_now(f.name)
            new_mtime = os.path.getmtime(f.name)
            assert new_mtime >= original_mtime

    def test_touch_now_failure(self):
        """Test _touch_now avec échec (best-effort)."""
        # Ne devrait pas lever d'exception
        _touch_now("/nonexistent/path")


class TestPruneManualBackups:
    """Tests pour _prune_manual_backups."""

    def test_prune_manual_backups_no_files(self, tmp_path):
        """Test avec aucun fichier de sauvegarde."""
        result = _prune_manual_backups(str(tmp_path / "grub"))
        assert result == []

    def test_prune_manual_backups_keep_all(self, tmp_path):
        """Test où on garde tous les fichiers."""
        base_path = tmp_path / "grub"
        # Crée 2 fichiers (keep=3 par défaut)
        for i in range(2):
            backup_path = tmp_path / f"grub.backup.manual.{i}"
            backup_path.write_text("content")
            # Simule des temps différents
            os.utime(backup_path, (i + 1, i + 1))

        result = _prune_manual_backups(str(base_path))
        assert result == []

        # Vérifie que les fichiers existent encore
        assert len(list(tmp_path.glob("grub.backup.manual.*"))) == 2

    def test_prune_manual_backups_delete_old(self, tmp_path):
        """Test où on supprime les anciens fichiers."""
        base_path = tmp_path / "grub"
        # Crée 5 fichiers
        for i in range(5):
            backup_path = tmp_path / f"grub.backup.manual.{i}"
            backup_path.write_text("content")
            # Simule des temps différents (plus vieux d'abord)
            os.utime(backup_path, (i + 1, i + 1))

        result = _prune_manual_backups(str(base_path), keep=2)
        assert len(result) == 3  # 5 - 2 = 3 supprimés

        # Vérifie qu'il reste 2 fichiers
        remaining = list(tmp_path.glob("grub.backup.manual.*"))
        assert len(remaining) == 2

    def test_prune_manual_backups_delete_failure(self, tmp_path):
        """Test avec échec de suppression (best-effort)."""
        base_path = tmp_path / "grub"
        backup_path = tmp_path / "grub.backup.manual.1"
        backup_path.write_text("content")

        with patch("os.remove", side_effect=OSError):
            result = _prune_manual_backups(str(base_path), keep=0)
            # Ne devrait pas lever d'exception malgré l'échec
            assert result == []


class TestEnsureInitialGrubDefaultBackup:
    """Tests pour ensure_initial_grub_default_backup."""

    def test_backup_already_exists(self, tmp_path):
        """Test quand le backup initial existe déjà."""
        config_path = tmp_path / "grub"
        backup_path = tmp_path / "grub.backup.initial"
        config_path.write_text("GRUB_TIMEOUT=5")
        backup_path.write_text("GRUB_TIMEOUT=5")

        result = ensure_initial_grub_default_backup(str(config_path))
        assert result == str(backup_path)

    def test_create_backup_success(self, tmp_path):
        """Test création réussie du backup initial."""
        config_path = tmp_path / "grub"
        backup_path = tmp_path / "grub.backup.initial"
        config_path.write_text("GRUB_TIMEOUT=5")

        result = ensure_initial_grub_default_backup(str(config_path))
        assert result == str(backup_path)
        assert backup_path.exists()

    def test_create_backup_file_missing(self, tmp_path):
        """Test quand le fichier original n'existe pas."""
        config_path = tmp_path / "grub"

        with patch("core.io.core_grub_default_io.read_grub_default") as mock_read:
            mock_read.return_value = {"GRUB_TIMEOUT": "5"}
            result = ensure_initial_grub_default_backup(str(config_path))
            assert result is None

    def test_create_backup_copy_failure(self, tmp_path):
        """Test échec de copie (permissions, etc.)."""
        config_path = tmp_path / "grub"
        config_path.write_text("GRUB_TIMEOUT=5")

        with patch("shutil.copy2", side_effect=OSError):
            result = ensure_initial_grub_default_backup(str(config_path))
            assert result is None


class TestListGrubDefaultBackups:
    """Tests pour list_grub_default_backups."""

    def test_list_backups(self, tmp_path):
        """Test listage des backups."""
        config_path = tmp_path / "grub"
        config_path.write_text("content")

        # Crée différents types de backups
        backups = [
            (tmp_path / "grub.backup.initial", 100),
            (tmp_path / "grub.backup.manual.20240101-120000", 200),
            (tmp_path / "grub.backup.manual.20240102-120000", 300),
            (tmp_path / "grub.backup", 50),
        ]

        for backup_path, mtime in backups:
            backup_path.write_text("backup content")
            os.utime(backup_path, (mtime, mtime))

        result = list_grub_default_backups(str(config_path))

        # Devrait être trié par date décroissante (plus récent d'abord)
        assert len(result) == 4
        # Le plus récent (mtime=300) devrait être en premier
        assert "grub.backup.manual.20240102-120000" in result[0]


class TestCreateGrubDefaultBackup:
    """Tests pour create_grub_default_backup."""

    def test_create_backup_success(self, tmp_path):
        """Test création réussie d'un backup."""
        config_path = tmp_path / "grub"
        config_path.write_text("GRUB_TIMEOUT=5")

        result = create_grub_default_backup(str(config_path))

        assert result.startswith(str(config_path) + ".backup.manual.")
        assert os.path.exists(result)

    def test_create_backup_with_fallback(self, tmp_path):
        """Test création avec fallback quand le fichier n'existe pas."""
        config_path = tmp_path / "grub"
        fallback_path = tmp_path / "grub.backup.current"
        fallback_path.write_text("GRUB_TIMEOUT=10")

        with patch("core.io.core_grub_default_io._best_fallback_for_missing_config") as mock_fallback:
            mock_fallback.return_value = str(fallback_path)
            result = create_grub_default_backup(str(config_path))

            assert result.startswith(str(config_path) + ".backup.manual.")
            assert os.path.exists(result)

    def test_create_backup_no_source(self, tmp_path):
        """Test quand aucune source n'est trouvée."""
        config_path = tmp_path / "grub"

        with patch("core.io.core_grub_default_io._best_fallback_for_missing_config") as mock_fallback:
            mock_fallback.return_value = None
            with pytest.raises(FileNotFoundError):
                create_grub_default_backup(str(config_path))

    def test_create_backup_pruning(self, tmp_path):
        """Test le nettoyage automatique des anciens backups."""
        config_path = tmp_path / "grub"
        config_path.write_text("GRUB_TIMEOUT=5")

        # Crée 5 anciens backups
        for i in range(5):
            backup_path = tmp_path / f"grub.backup.manual.{i}"
            backup_path.write_text("old backup")
            os.utime(backup_path, (i + 1, i + 1))

        create_grub_default_backup(str(config_path))

        # Devrait garder seulement 3 backups (le nouveau + 2 anciens)
        manual_backups = list(tmp_path.glob("grub.backup.manual.*"))
        assert len(manual_backups) == 3


class TestDeleteGrubDefaultBackup:
    """Tests pour delete_grub_default_backup."""

    def test_delete_backup_success(self, tmp_path):
        """Test suppression réussie d'un backup."""
        config_path = tmp_path / "grub"
        backup_path = tmp_path / "grub.backup.manual.20240101"
        backup_path.write_text("backup content")

        delete_grub_default_backup(str(backup_path), path=str(config_path))

        assert not backup_path.exists()

    def test_delete_backup_invalid_path(self, tmp_path):
        """Test suppression avec chemin invalide."""
        config_path = tmp_path / "grub"
        backup_path = tmp_path / "invalid.backup"

        with pytest.raises(ValueError, match="Chemin de sauvegarde invalide"):
            delete_grub_default_backup(str(backup_path), path=str(config_path))


class TestBestFallbackForMissingConfig:
    """Tests pour _best_fallback_for_missing_config."""

    def test_best_fallback_no_candidates(self, tmp_path):
        """Test quand aucun fallback n'existe."""
        config_path = tmp_path / "grub"
        result = _best_fallback_for_missing_config(str(config_path))
        assert result is None

    def test_best_fallback_with_candidates(self, tmp_path):
        """Test avec plusieurs fallbacks disponibles."""
        config_path = tmp_path / "grub"

        # Crée différents fallbacks avec des dates différentes
        fallbacks = [
            (tmp_path / "grub.backup.current", 100),
            (tmp_path / "grub.backup", 200),
            (tmp_path / "grub.backup.manual.1", 50),
        ]

        for path, mtime in fallbacks:
            path.write_text("content")
            os.utime(path, (mtime, mtime))

        result = _best_fallback_for_missing_config(str(config_path))

        # Devrait retourner le plus récent (grub.backup avec mtime=200)
        assert result == str(tmp_path / "grub.backup")


class TestParseGrubDefault:
    """Tests pour parse_grub_default."""

    def test_parse_grub_default_basic(self):
        """Test parsing basique."""
        text = """# Comment
GRUB_TIMEOUT=5
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
EMPTY_VAR=
"""
        result = parse_grub_default(text)
        expected = {
            "GRUB_TIMEOUT": "5",
            "GRUB_CMDLINE_LINUX_DEFAULT": "quiet splash",
            "EMPTY_VAR": "",
        }
        assert result == expected

    def test_parse_grub_default_quotes(self):
        """Test parsing avec guillemets."""
        text = 'GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"'
        result = parse_grub_default(text)
        assert result["GRUB_CMDLINE_LINUX_DEFAULT"] == "quiet splash"

    def test_parse_grub_default_single_quotes(self):
        """Test parsing avec guillemets simples."""
        text = "GRUB_CMDLINE_LINUX_DEFAULT='quiet splash'"
        result = parse_grub_default(text)
        assert result["GRUB_CMDLINE_LINUX_DEFAULT"] == "quiet splash"

    def test_parse_grub_default_empty(self):
        """Test parsing fichier vide."""
        result = parse_grub_default("")
        assert result == {}

    def test_parse_grub_default_no_equals(self):
        """Test parsing ligne sans =."""
        text = "INVALID LINE"
        result = parse_grub_default(text)
        assert result == {}


class TestFormatGrubDefault:
    """Tests pour format_grub_default."""

    def test_format_grub_default_basic(self):
        """Test formatage basique."""
        config = {"GRUB_TIMEOUT": "5", "GRUB_DEFAULT": "0"}
        result = format_grub_default(config, "/path/to/backup")

        lines = result.split("\n")
        assert lines[0] == "# Configuration GRUB modifiée par GRUB Configuration Manager"
        assert lines[1] == "# Sauvegarde: /path/to/backup"
        assert "GRUB_TIMEOUT=5" in lines
        assert "GRUB_DEFAULT=0" in lines

    def test_format_grub_default_quotes_needed(self):
        """Test formatage avec guillemets quand nécessaire."""
        config = {
            "GRUB_CMDLINE_LINUX_DEFAULT": "quiet splash",
            "GRUB_TIMEOUT": "5",
        }
        result = format_grub_default(config, "/backup")

        assert 'GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"' in result
        assert "GRUB_TIMEOUT=5" in result

    def test_format_grub_default_escape_quotes(self):
        """Test échappement des guillemets."""
        config = {"VAR": 'value with "quotes"'}
        result = format_grub_default(config, "/backup")

        assert 'VAR="value with \\"quotes\\""' in result


class TestReadGrubDefault:
    """Tests pour read_grub_default."""

    def test_read_grub_default_success(self, tmp_path):
        """Test lecture réussie."""
        config_path = tmp_path / "grub"
        config_path.write_text("GRUB_TIMEOUT=5\nGRUB_DEFAULT=0\n")

        result = read_grub_default(str(config_path))
        assert result == {"GRUB_TIMEOUT": "5", "GRUB_DEFAULT": "0"}

    def test_read_grub_default_with_fallback(self, tmp_path):
        """Test lecture avec fallback."""
        config_path = tmp_path / "grub"
        fallback_path = tmp_path / "grub.backup.current"
        fallback_path.write_text("GRUB_TIMEOUT=10\n")

        with patch("core.io.core_grub_default_io._best_fallback_for_missing_config") as mock_fallback:
            mock_fallback.return_value = str(fallback_path)
            result = read_grub_default(str(config_path))

            assert result == {"GRUB_TIMEOUT": "10"}
            # Vérifie que le fichier canonique a été restauré
            assert config_path.exists()

    def test_read_grub_default_fallback_restore_failure(self, tmp_path):
        """Test avec échec de restauration du fallback."""
        config_path = tmp_path / "grub"
        fallback_path = tmp_path / "grub.backup.current"
        fallback_path.write_text("GRUB_TIMEOUT=10\n")

        with (
            patch("core.io.core_grub_default_io._best_fallback_for_missing_config") as mock_fallback,
            patch("shutil.copy2", side_effect=OSError),
        ):
            mock_fallback.return_value = str(fallback_path)
            result = read_grub_default(str(config_path))

            assert result == {"GRUB_TIMEOUT": "10"}

    def test_read_grub_default_no_fallback(self, tmp_path):
        """Test quand aucun fallback n'existe."""
        config_path = tmp_path / "grub"

        with patch("core.io.core_grub_default_io._best_fallback_for_missing_config") as mock_fallback:
            mock_fallback.return_value = None
            with pytest.raises(FileNotFoundError):
                read_grub_default(str(config_path))


class TestWriteGrubDefault:
    """Tests pour write_grub_default."""

    def test_write_grub_default_success(self, tmp_path):
        """Test écriture réussie."""
        config_path = tmp_path / "grub"
        config_path.write_text("old content")

        config = {"GRUB_TIMEOUT": "5", "GRUB_DEFAULT": "0"}
        result = write_grub_default(config, str(config_path))

        # Vérifie que le backup a été créé
        assert result == str(config_path) + ".backup"
        assert os.path.exists(result)

        # Vérifie le contenu écrit
        with open(config_path) as f:
            content = f.read()
            assert "GRUB_TIMEOUT=5" in content
            assert "GRUB_DEFAULT=0" in content

    def test_write_grub_default_backup_failure(self, tmp_path):
        """Test échec de création du backup."""
        config_path = tmp_path / "grub"
        config_path.write_text("content")

        with patch("shutil.copy2", side_effect=OSError):
            with pytest.raises(OSError):
                write_grub_default({"GRUB_TIMEOUT": "5"}, str(config_path))

    def test_write_grub_default_write_failure(self, tmp_path):
        """Test échec d'écriture."""
        config_path = tmp_path / "grub"
        config_path.write_text("content")

        with patch("builtins.open", side_effect=OSError):
            with pytest.raises(OSError):
                write_grub_default({"GRUB_TIMEOUT": "5"}, str(config_path))
