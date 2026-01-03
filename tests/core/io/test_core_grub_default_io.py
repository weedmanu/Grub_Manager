"""Tests pour les opérations I/O sur /etc/default/grub."""

import os
import shutil
import tarfile
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.io.core_grub_default_io import (
    GRUB_DEFAULT_PATH,
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
    restore_grub_default_backup,
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
        _touch_now("/nonexistent/path/that/should/fail")

    def test_touch_now_oserror(self):
        """Test _touch_now avec une OSError simulée."""
        with patch("os.utime", side_effect=OSError):
            # Ne doit pas lever d'exception
            _touch_now("/some/path")


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
        backup_path = tmp_path / "grub_backup.initial.tar.gz"
        config_path.write_text("GRUB_TIMEOUT=5")
        backup_path.write_text("GRUB_TIMEOUT=5")

        result = ensure_initial_grub_default_backup(str(config_path))
        assert result == str(backup_path)

    def test_create_backup_success(self, tmp_path):
        """Test création réussie du backup initial."""
        config_path = tmp_path / "grub"
        backup_path = tmp_path / "grub_backup.initial.tar.gz"
        config_path.write_text("GRUB_TIMEOUT=5")

        result = ensure_initial_grub_default_backup(str(config_path))
        assert result == str(backup_path)
        assert backup_path.exists()

    def test_create_backup_file_missing(self, tmp_path):
        """Test quand le fichier original n'existe pas."""
        config_path = tmp_path / "grub"

        with patch("core.io.core_grub_default_io.read_grub_default") as mock_read:
            mock_read.side_effect = OSError("Fichier manquant")
            result = ensure_initial_grub_default_backup(str(config_path))
            assert result is None

    def test_create_backup_copy_failure(self, tmp_path):
        """Test échec de création du tar (permissions, etc.)."""
        config_path = tmp_path / "grub"
        config_path.write_text("GRUB_TIMEOUT=5")

        with patch("tarfile.open", side_effect=OSError("Permission denied")):
            result = ensure_initial_grub_default_backup(str(config_path))
            assert result is None

    def test_ensure_initial_backup_full_system(self, tmp_path):
        """Test backup complet du système (grub.d, grub.cfg)."""
        fake_grub_default = tmp_path / "grub"
        fake_grub_default.write_text("GRUB_TIMEOUT=5")

        fake_grub_d = tmp_path / "grub.d"
        fake_grub_d.mkdir()
        (fake_grub_d / "10_linux").write_text("echo linux")

        fake_boot_grub = tmp_path / "boot" / "grub"
        fake_boot_grub.mkdir(parents=True)
        (fake_boot_grub / "grub.cfg").write_text("menuentry 'Linux' {}")

        with (
            patch("core.io.core_grub_default_io.GRUB_DEFAULT_PATH", str(fake_grub_default)),
            patch("core.io.core_grub_default_io.GRUB_CFG_PATHS", [str(fake_boot_grub / "grub.cfg")]),
            patch("os.path.abspath", side_effect=lambda x: x),
            patch("core.io.core_grub_default_io.Path") as mock_path_cls,
        ):

            mock_grub_d = MagicMock(spec=Path)
            mock_grub_d.exists.return_value = True

            real_script_path = fake_grub_d / "10_linux"
            mock_script = MagicMock(spec=Path)
            mock_script.is_file.return_value = True
            mock_script.name = "10_linux"
            mock_script.__str__.return_value = str(real_script_path)
            mock_script.__fspath__.return_value = str(real_script_path)

            mock_grub_d.iterdir.return_value = [mock_script]

            def path_side_effect(p):
                if str(p) == "/etc/grub.d":
                    return mock_grub_d
                return Path(p)

            mock_path_cls.side_effect = path_side_effect

            res = ensure_initial_grub_default_backup(str(fake_grub_default))
            assert res is not None
            assert os.path.exists(res)

            with tarfile.open(res, "r:gz") as tar:
                names = tar.getnames()
                assert "default_grub" in names
                assert "grub.d/10_linux" in names
                assert any(n.startswith("grub.cfg_") for n in names)

    def test_ensure_initial_backup_tar_add_failure(self, tmp_path):
        """Test échec partiel lors de l'ajout au tar."""
        fake_grub = tmp_path / "grub"
        fake_grub.write_text("test")

        with patch("tarfile.TarFile.add", side_effect=PermissionError("Denied")):
            res = ensure_initial_grub_default_backup(str(fake_grub))
            assert res is not None

    def test_ensure_initial_backup_path_not_file(self, tmp_path):
        """Test quand le chemin n'est pas un fichier."""
        with (
            patch("os.path.isfile", return_value=False),
            patch("core.io.core_grub_default_io.read_grub_default", side_effect=OSError("Missing")),
        ):
            res = ensure_initial_grub_default_backup(str(tmp_path / "not_a_file"))
            assert res is None

    def test_ensure_initial_backup_grub_d_not_exists(self, tmp_path):
        """Test quand /etc/grub.d n'existe pas."""
        fake_grub = tmp_path / "grub"
        fake_grub.write_text("GRUB_TIMEOUT=5")

        with (
            patch("os.path.abspath", return_value=os.path.abspath(GRUB_DEFAULT_PATH)),
            patch("pathlib.Path.exists", side_effect=[False, False]),
            patch("os.path.isfile", return_value=True),
            patch("os.path.exists", return_value=True),
        ):
            res = ensure_initial_grub_default_backup(str(fake_grub))
            assert res is not None

    def test_ensure_initial_backup_script_not_file(self, tmp_path):
        """Test quand un script dans grub.d n'est pas un fichier."""
        fake_grub = tmp_path / "grub"
        fake_grub.write_text("GRUB_TIMEOUT=5")

        mock_script = MagicMock(spec=Path)
        mock_script.is_file.return_value = False
        mock_script.name = "not_a_script"

        with (
            patch("os.path.abspath", return_value=os.path.abspath(GRUB_DEFAULT_PATH)),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.iterdir", return_value=[mock_script]),
            patch("os.path.isfile", return_value=True),
            patch("os.path.exists", return_value=True),
        ):
            res = ensure_initial_grub_default_backup(str(fake_grub))
            assert res is not None

    def test_ensure_initial_backup_script_error_handling(self, tmp_path):
        """Test gestion d'erreur lors de l'ajout d'un script."""
        fake_grub = tmp_path / "grub"
        fake_grub.write_text("GRUB_TIMEOUT=5")

        mock_script = MagicMock(spec=Path)
        mock_script.is_file.return_value = True
        mock_script.name = "error_script"
        mock_script.__str__.return_value = "/etc/grub.d/error_script"

        with (
            patch("os.path.abspath", return_value=os.path.abspath(GRUB_DEFAULT_PATH)),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.iterdir", return_value=[mock_script]),
            patch("os.path.isfile", return_value=True),
            patch("os.path.exists", return_value=True),
            patch("tarfile.TarFile.add") as mock_add,
        ):

            mock_add.side_effect = [None, PermissionError("Denied")]

            res = ensure_initial_grub_default_backup(str(fake_grub))
            assert res is not None

    def test_ensure_initial_backup_path_not_file_during_tar(self, tmp_path):
        """Test quand le fichier disparaît pendant la création du tar."""
        fake_grub = tmp_path / "grub"
        fake_grub.write_text("GRUB_TIMEOUT=5")

        is_file_results = [True, False, False, False, False]
        with patch("os.path.isfile", side_effect=is_file_results):
            res = ensure_initial_grub_default_backup(str(fake_grub))
            assert res is not None


class TestListGrubDefaultBackups:
    """Tests pour list_grub_default_backups."""

    def test_list_backups(self, tmp_path):
        """Test listage des backups."""
        config_path = tmp_path / "grub"
        config_path.write_text("content")

        # Crée différents types de backups
        backups = [
            (tmp_path / "grub_backup.initial.tar.gz", 100),
            (tmp_path / "grub.backup.manual.20240101-120000.tar.gz", 200),
            (tmp_path / "grub.backup.manual.20240102-120000.tar.gz", 300),
            (tmp_path / "grub.backup.tar.gz", 50),
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
        assert result.endswith(".tar.gz")
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
            assert result.endswith(".tar.gz")
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
            backup_path = tmp_path / f"grub.backup.manual.{i}.tar.gz"
            backup_path.write_text("old backup")
            os.utime(backup_path, (i + 1, i + 1))

        create_grub_default_backup(str(config_path))

        # Devrait garder seulement 3 backups (le nouveau + 2 anciens)
        manual_backups = list(tmp_path.glob("grub.backup.manual.*.tar.gz"))
        assert len(manual_backups) == 3

    def test_create_backup_full_system(self, tmp_path):
        """Test backup complet lors d'un backup manuel."""
        fake_grub_default = tmp_path / "grub"
        fake_grub_default.write_text("GRUB_TIMEOUT=5")

        fake_grub_d = tmp_path / "grub.d"
        fake_grub_d.mkdir()
        (fake_grub_d / "10_linux").write_text("echo linux")

        fake_boot_grub = tmp_path / "boot" / "grub"
        fake_boot_grub.mkdir(parents=True)
        (fake_boot_grub / "grub.cfg").write_text("menuentry 'Linux' {}")

        with (
            patch("core.io.core_grub_default_io.GRUB_DEFAULT_PATH", str(fake_grub_default)),
            patch("core.io.core_grub_default_io.GRUB_CFG_PATHS", [str(fake_boot_grub / "grub.cfg")]),
            patch("os.path.abspath", side_effect=lambda x: x),
            patch("core.io.core_grub_default_io.Path") as mock_path_cls,
        ):

            mock_grub_d = MagicMock(spec=Path)
            mock_grub_d.exists.return_value = True

            real_script_path = fake_grub_d / "10_linux"
            mock_script = MagicMock(spec=Path)
            mock_script.is_file.return_value = True
            mock_script.name = "10_linux"
            mock_script.__str__.return_value = str(real_script_path)
            mock_script.__fspath__.return_value = str(real_script_path)

            mock_grub_d.iterdir.return_value = [mock_script]

            def path_side_effect(p):
                if str(p) == "/etc/grub.d":
                    return mock_grub_d
                return Path(p)

            mock_path_cls.side_effect = path_side_effect

            res = create_grub_default_backup(str(fake_grub_default))
            assert res is not None
            assert os.path.exists(res)

    def test_create_backup_uuid_collision(self, tmp_path):
        """Test gestion des collisions d'UUID lors de la création du nom de fichier."""
        fake_grub = tmp_path / "grub"
        fake_grub.write_text("test")

        original_exists = os.path.exists

        def exists_side_effect(p):
            if ".manual." in str(p):
                if not hasattr(exists_side_effect, "count"):
                    exists_side_effect.count = 0
                exists_side_effect.count += 1
                # Simule 2 collisions puis succès
                return exists_side_effect.count <= 2
            return original_exists(p)

        with patch("os.path.exists", side_effect=exists_side_effect), patch("os.path.isfile", return_value=True):
            res = create_grub_default_backup(str(fake_grub))
            assert "manual" in res

    def test_create_backup_tar_open_failure(self, tmp_path):
        """Test échec d'ouverture du tar (ex: disque plein)."""
        fake_grub = tmp_path / "grub"
        fake_grub.write_text("test")

        with patch("tarfile.open", side_effect=OSError("Disk full")):
            with pytest.raises(OSError, match="Échec création sauvegarde"):
                create_grub_default_backup(str(fake_grub))

    def test_create_backup_tar_add_script_failure(self, tmp_path):
        """Test échec d'ajout d'un script lors d'un backup manuel."""
        fake_grub = tmp_path / "grub"
        fake_grub.write_text("GRUB_TIMEOUT=5")

        with (
            patch("os.path.abspath", return_value=os.path.abspath(GRUB_DEFAULT_PATH)),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.iterdir", return_value=[Path("/etc/grub.d/00_header")]),
            patch("pathlib.Path.is_file", return_value=True),
            patch("tarfile.TarFile.add") as mock_add,
            patch("os.path.isfile", return_value=True),
            patch("os.path.exists", return_value=True),
        ):

            def add_side_effect(name, *args, **kwargs):
                if "00_header" in str(name):
                    raise PermissionError("Denied")
                return None

            mock_add.side_effect = add_side_effect

            res = create_grub_default_backup(str(fake_grub))
            assert res is not None


class TestRestoreGrubDefaultBackup:
    """Tests pour restore_grub_default_backup."""

    def test_restore_backup_full_success(self, tmp_path):
        """Test restauration complète réussie."""
        archive_path = tmp_path / "test_backup.tar.gz"
        grub_content = b"GRUB_TIMEOUT=10"
        script_content = b"echo script"
        cfg_content = b"menuentry 'Test' {}"

        with tarfile.open(archive_path, "w:gz") as tar:
            f1 = tmp_path / "f1"
            f1.write_bytes(grub_content)
            tar.add(f1, arcname="default_grub")

            f2 = tmp_path / "f2"
            f2.write_bytes(script_content)
            tar.add(f2, arcname="grub.d/20_memtest")

            f3 = tmp_path / "f3"
            f3.write_bytes(cfg_content)
            tar.add(f3, arcname="grub.cfg_grub")

        target_grub = str(tmp_path / "restored_grub")

        with (
            patch("shutil.copy2") as mock_copy,
            patch("os.remove") as mock_remove,
            patch("shutil.rmtree") as mock_rmtree,
        ):

            restore_grub_default_backup(str(archive_path), target_grub)

            assert mock_copy.call_count == 3
            calls = [c[0] for c in mock_copy.call_args_list]
            assert any(c[1] == target_grub for c in calls)
            assert any(c[1] == "/etc/grub.d/20_memtest" for c in calls)
            assert any(c[1] == "/boot/grub/grub.cfg" for c in calls)

    def test_restore_backup_tar_error(self, tmp_path):
        """Test restauration avec archive corrompue."""
        archive_path = tmp_path / "corrupt.tar.gz"
        archive_path.write_text("not a tar")

        with pytest.raises(OSError, match="Échec de la restauration"):
            restore_grub_default_backup(str(archive_path))

    def test_restore_backup_os_error_during_copy(self, tmp_path):
        """Test échec lors de la copie des fichiers extraits."""
        archive_path = tmp_path / "test.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            f = tmp_path / "f"
            f.write_text("data")
            tar.add(f, arcname="default_grub")

        with patch("shutil.copy2", side_effect=OSError("Disk full")):
            with pytest.raises(OSError, match="Échec de la restauration"):
                restore_grub_default_backup(str(archive_path), "/some/target")

    def test_restore_backup_cleanup_tmp_grub_d(self, tmp_path):
        """Test nettoyage du dossier temporaire grub.d."""
        backup_path = tmp_path / "test.tar.gz"
        with tarfile.open(backup_path, "w:gz") as tar:
            f = tmp_path / "test_script"
            f.write_text("echo 1")
            tar.add(f, arcname="grub.d/test_script")

        target_grub = tmp_path / "grub_dest"

        original_exists = os.path.exists

        def side_effect(p):
            if p == "/tmp/grub.d":
                return True
            return original_exists(p)

        with (
            patch("os.path.exists", side_effect=side_effect),
            patch("shutil.copy2"),
            patch("os.remove"),
            patch("shutil.rmtree") as mock_rmtree,
        ):
            restore_grub_default_backup(str(backup_path), str(target_grub))
            mock_rmtree.assert_called_once_with("/tmp/grub.d")


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


class TestTarFilters:
    """Tests pour les fonctions de filtrage tar internes."""

    def test_tar_filter_permission_denied(self, tmp_path):
        """Test le filtre tar quand l'accès est refusé."""
        fake_grub = tmp_path / "grub"
        fake_grub.write_text("GRUB_TIMEOUT=5")

        with patch("os.access", return_value=False), patch("os.path.exists", return_value=True):
            res = ensure_initial_grub_default_backup(str(fake_grub))
            assert res is not None
            assert os.path.exists(res)

    def test_tar_filter_exception(self, tmp_path):
        """Test le filtre tar quand une exception survient."""
        fake_grub = tmp_path / "grub"
        fake_grub.write_text("GRUB_TIMEOUT=5")

        with patch("os.path.exists", side_effect=OSError("Crash")):
            res = ensure_initial_grub_default_backup(str(fake_grub))
            assert res is not None

    def test_tar_filter_manual_permission_denied(self, tmp_path):
        """Test le filtre tar manuel quand l'accès est refusé."""
        fake_grub = tmp_path / "grub"
        fake_grub.write_text("GRUB_TIMEOUT=5")

        with patch("os.access", return_value=False), patch("os.path.exists", return_value=True):
            res = create_grub_default_backup(str(fake_grub))
            assert res is not None


class TestEdgeCases:
    """Tests pour les cas limites restants."""

    def test_delete_backup_refuse_canonical(self, tmp_path):
        """Test le refus de supprimer le fichier canonique."""
        config_path = tmp_path / "grub"
        config_path.write_text("content")

        with pytest.raises(ValueError, match="Refus de supprimer le fichier canonique"):
            delete_grub_default_backup(str(config_path), path=str(config_path))

    def test_delete_backup_initial_success(self, tmp_path):
        """Test la suppression du backup initial."""
        config_path = tmp_path / "grub"
        backup_path = tmp_path / "grub_backup.initial.tar.gz"
        backup_path.write_text("initial")

        delete_grub_default_backup(str(backup_path), path=str(config_path))
        assert not backup_path.exists()

    def test_write_grub_default_oserror_on_write(self, tmp_path):
        """Test OSError lors de l'écriture finale dans write_grub_default."""
        config_path = tmp_path / "grub"
        config_path.write_text("old")

        # On mocke open pour l'écriture seulement
        original_open = open

        def mock_open(file, mode="r", *args, **kwargs):
            if str(file) == str(config_path) and "w" in mode:
                raise OSError("Write failed")
            return original_open(file, mode, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open):
            with pytest.raises(OSError, match="Write failed"):
                write_grub_default({"K": "V"}, str(config_path))

    def test_restore_backup_with_all_types(self, tmp_path):
        """Test la restauration avec tous les types de fichiers (grub.d, grub.cfg)."""
        archive_path = tmp_path / "full.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            f = tmp_path / "f"
            f.write_text("data")
            tar.add(f, arcname="default_grub")
            tar.add(f, arcname="grub.d/99_test")
            tar.add(f, arcname="grub.cfg_grub2")

        with patch("shutil.copy2"), patch("os.remove"), patch("shutil.rmtree"):
            # Ne doit pas lever d'exception
            restore_grub_default_backup(str(archive_path), str(tmp_path / "dest"))

    def test_create_backup_many_collisions(self, tmp_path):
        """Test create_grub_default_backup avec de nombreuses collisions de noms."""
        fake_grub = tmp_path / "grub"
        fake_grub.write_text("test")

        original_exists = os.path.exists

        def exists_side_effect(p):
            if ".manual." in str(p):
                if not hasattr(exists_side_effect, "count"):
                    exists_side_effect.count = 0
                exists_side_effect.count += 1
                return exists_side_effect.count <= 130  # Plus que max_attempts (128)
            return original_exists(p)

        with (
            patch("os.path.exists", side_effect=exists_side_effect),
            patch("os.path.isfile", return_value=True),
            patch("tarfile.open"),
            patch("uuid.uuid4") as mock_uuid,
        ):
            mock_uuid.return_value.hex = "extreme-uuid"
            create_grub_default_backup(str(fake_grub))
            assert mock_uuid.called

    def test_prune_manual_backups_delete_success(self, tmp_path):
        """Test la suppression réussie dans prune."""
        base_path = tmp_path / "grub"
        for i in range(5):
            p = tmp_path / f"grub.backup.manual.{i}"
            p.write_text("old")
            os.utime(p, (i, i))

        deleted = _prune_manual_backups(str(base_path), keep=2)
        assert len(deleted) == 3

    def test_list_backups_with_initial_v2(self, tmp_path):
        """Test list_grub_default_backups avec backup initial présent."""
        config_path = tmp_path / "grub"
        config_path.write_text("c")
        initial = tmp_path / "grub_backup.initial.tar.gz"
        initial.write_text("i")

        with patch("core.io.core_grub_default_io.GRUB_DEFAULT_PATH", str(config_path)):
            backups = list_grub_default_backups(str(config_path))
            assert any("initial" in b for b in backups)

    def test_ensure_initial_backup_already_exists_v3(self, tmp_path):
        """Test ensure_initial_grub_default_backup quand le backup existe déjà."""
        config_path = tmp_path / "grub"
        config_path.write_text("c")
        initial = tmp_path / "grub_backup.initial.tar.gz"
        initial.write_text("i")

        res = ensure_initial_grub_default_backup(str(config_path))
        assert res == str(initial)

    def test_list_backups_with_initial(self, tmp_path):
        """Test list_grub_default_backups incluant le backup initial."""
        config_path = tmp_path / "grub"
        config_path.write_text("content")
        initial_backup = tmp_path / "grub_backup.initial.tar.gz"
        initial_backup.write_text("initial")

        backups = list_grub_default_backups(str(config_path))
        assert any("grub_backup.initial.tar.gz" in b for b in backups)

    def test_create_backup_no_source_found(self, tmp_path):
        """Test create_grub_default_backup quand aucune source n'est trouvée."""
        config_path = tmp_path / "nonexistent_grub"
        with patch("core.io.core_grub_default_io._best_fallback_for_missing_config", return_value=None):
            with pytest.raises(FileNotFoundError):
                create_grub_default_backup(str(config_path))

    def test_prune_manual_backups_oserror(self, tmp_path):
        """Test OSError lors de la suppression dans prune."""
        base_path = tmp_path / "grub"
        p = tmp_path / "grub.backup.manual.1"
        p.write_text("old")

        # On doit patcher os.remove dans le module core.io.core_grub_default_io
        with patch("core.io.core_grub_default_io.os.remove", side_effect=OSError("Delete failed")):
            deleted = _prune_manual_backups(str(base_path), keep=0)
            assert deleted == []

    def test_ensure_initial_backup_safe_is_file_oserror(self, tmp_path):
        """Test OSError dans _safe_is_file de ensure_initial_backup."""
        config_path = tmp_path / "grub"
        with patch("core.io.core_grub_default_io.os.path.isfile", side_effect=OSError):
            res = ensure_initial_grub_default_backup(str(config_path))
            assert res is None

    def test_ensure_initial_backup_tar_add_oserror_internal(self, tmp_path):
        """Test OSError interne lors de tar.add dans ensure_initial_backup."""
        config_path = tmp_path / "grub"
        config_path.write_text("c")
        with patch("tarfile.open") as mock_open:
            mock_tar = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_tar
            mock_tar.add.side_effect = OSError("Add failed")
            res = ensure_initial_grub_default_backup(str(config_path))
            # Ne doit pas être None car l'erreur est catchée en interne
            assert res is not None

    def test_ensure_initial_backup_exists_check_oserror_internal(self, tmp_path):
        """Test OSError lors du check d'existence dans le loop grub.cfg."""
        config_path = tmp_path / "grub"
        config_path.write_text("c")
        with patch("core.io.core_grub_default_io.os.path.abspath", return_value=str(GRUB_DEFAULT_PATH)):
            with patch("core.io.core_grub_default_io.os.path.exists", side_effect=[False, OSError]):
                res = ensure_initial_grub_default_backup(str(config_path))
                assert res is not None

    def test_create_backup_safe_exists_oserror(self, tmp_path):
        """Test OSError dans _safe_exists de create_backup."""
        config_path = tmp_path / "grub"
        config_path.write_text("c")
        with patch("core.io.core_grub_default_io.os.path.exists", side_effect=OSError):
            res = create_grub_default_backup(str(config_path))
            assert res is not None

    def test_create_backup_safe_is_file_oserror(self, tmp_path):
        """Test OSError dans _safe_is_file de create_backup."""
        config_path = tmp_path / "grub"
        config_path.write_text("c")
        # On doit patcher os.path.isfile dans le module core.io.core_grub_default_io
        with patch("core.io.core_grub_default_io.os.path.isfile", side_effect=OSError):
            with pytest.raises(OSError):
                create_grub_default_backup(str(config_path))

    def test_create_backup_exists_check_oserror_internal(self, tmp_path):
        """Test OSError lors du check d'existence dans le loop grub.cfg de create_backup."""
        config_path = tmp_path / "grub"
        config_path.write_text("c")
        with patch("core.io.core_grub_default_io.os.path.abspath", return_value=str(GRUB_DEFAULT_PATH)):
            # On fournit assez de valeurs pour éviter StopIteration
            # 1. backup_path exists check (False)
            # 2. source_path is_file check (True)
            # 3. grub_d_dir exists check (True)
            # 4. script is_file check (True)
            # 5. grub_cfg exists check (OSError)
            side_effects = [False, True, True, True, OSError] + [False] * 100
            with patch("core.io.core_grub_default_io.os.path.exists", side_effect=side_effects):
                res = create_grub_default_backup(str(config_path))
                assert res is not None

    def test_ensure_initial_backup_tar_open_oserror_v2(self, tmp_path):
        """Test OSError lors de tarfile.open dans ensure_initial_backup."""
        config_path = tmp_path / "grub"
        config_path.write_text("c")
        with patch("core.io.core_grub_default_io.tarfile.open", side_effect=OSError("Open failed")):
            res = ensure_initial_grub_default_backup(str(config_path))
            assert res is None

    def test_ensure_initial_backup_tar_add_oserror_v2(self, tmp_path):
        """Test OSError lors de tar.add dans ensure_initial_backup."""
        config_path = tmp_path / "grub"
        config_path.write_text("c")
        mock_tar = MagicMock()
        mock_tar.add.side_effect = OSError("Add failed")
        with patch("core.io.core_grub_default_io.tarfile.open", return_value=mock_tar):
            mock_tar.__enter__.return_value = mock_tar
            res = ensure_initial_grub_default_backup(str(config_path))
            assert res is not None

    def test_ensure_initial_backup_exists_check_oserror_v2(self, tmp_path):
        """Test OSError lors du check d'existence final dans ensure_initial_backup."""
        config_path = tmp_path / "grub"
        config_path.write_text("c")
        # On patche os.path.exists pour qu'il lève une erreur lors du check de grub.cfg
        with patch("core.io.core_grub_default_io.os.path.abspath", return_value=str(GRUB_DEFAULT_PATH)):
            side_effects = [False, True, True, True, OSError] + [False] * 100
            with patch("core.io.core_grub_default_io.os.path.exists", side_effect=side_effects):
                res = ensure_initial_grub_default_backup(str(config_path))
                assert res is not None

    def test_create_backup_tar_close_oserror_v2(self, tmp_path):
        """Test OSError lors de la fermeture du tar dans create_backup."""
        config_path = tmp_path / "grub"
        config_path.write_text("c")
        with patch("core.io.core_grub_default_io.tarfile.open") as mock_open:
            mock_open.return_value.__exit__.side_effect = OSError("Close failed")
            with pytest.raises(OSError, match="Close failed"):
                create_grub_default_backup(str(config_path))

    def test_restore_backup_file_not_found(self, tmp_path):
        """Test FileNotFoundError dans restore_backup."""
        with pytest.raises(FileNotFoundError):
            restore_grub_default_backup("nonexistent.tar.gz", "dest")

    def test_ensure_initial_backup_no_grub_d(self, tmp_path):
        """Test ensure_initial_backup quand /etc/grub.d n'existe pas."""
        config_path = tmp_path / "grub"
        config_path.write_text("c")
        with patch("core.io.core_grub_default_io.os.path.abspath", return_value=str(GRUB_DEFAULT_PATH)):
            with patch("core.io.core_grub_default_io.Path.exists", side_effect=[False, False]):
                res = ensure_initial_grub_default_backup(str(config_path))
                assert res is not None

    def test_create_backup_no_grub_d(self, tmp_path):
        """Test create_backup quand /etc/grub.d n'existe pas."""
        config_path = tmp_path / "grub"
        config_path.write_text("c")
        with patch("core.io.core_grub_default_io.os.path.abspath", return_value=str(GRUB_DEFAULT_PATH)):
            with patch("core.io.core_grub_default_io.Path.exists", side_effect=[False, False]):
                res = create_grub_default_backup(str(config_path))
                assert res is not None

    def test_restore_backup_no_grub_d_in_archive(self, tmp_path):
        """Test restore_backup quand l'archive ne contient pas de grub.d."""
        archive_path = tmp_path / "f.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            f = tmp_path / "f"
            f.write_text("d")
            tar.add(f, arcname="default_grub")

        with patch("shutil.copy2"), patch("os.remove"):
            # On patche os.path.exists pour qu'il renvoie True pour l'archive mais False pour /tmp/grub.d
            original_exists = os.path.exists

            def mock_exists(p):
                if p == "/tmp/grub.d":
                    return False
                return original_exists(p)

            with patch("os.path.exists", side_effect=mock_exists):
                restore_grub_default_backup(str(archive_path), str(tmp_path / "dest"))

    def test_restore_backup_no_grub_cfg_in_archive(self, tmp_path):
        """Test restore_backup quand l'archive ne contient pas de grub.cfg."""
        archive_path = tmp_path / "f.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            f = tmp_path / "f"
            f.write_text("d")
            tar.add(f, arcname="default_grub")

        with patch("shutil.copy2"), patch("os.remove"):
            restore_grub_default_backup(str(archive_path), str(tmp_path / "dest"))


class TestFinalCoverage:
    """Tests pour atteindre 100% de couverture sur core_grub_default_io.py."""

    def test_prune_manual_backups_oserror_on_remove(self):
        from core.io.core_grub_default_io import _prune_manual_backups

        with (
            patch("core.io.core_grub_default_io.glob", return_value=["grub.backup.manual.old"]),
            patch("os.path.isfile", return_value=True),
            patch("os.path.getmtime", return_value=100),
            patch("os.remove", side_effect=OSError("Permission denied")),
        ):
            _prune_manual_backups("/etc/default/grub")

    def test_ensure_initial_backup_coverage_boost(self):
        # Branche 166->170: initial backup exists
        from core.io.core_grub_default_io import ensure_initial_grub_default_backup

        with patch("core.io.core_grub_default_io.Path.exists", return_value=True):
            ensure_initial_grub_default_backup()

    def test_ensure_initial_backup_empty_iterdir(self):
        # Branche 119->118: empty iterdir
        from core.io.core_grub_default_io import ensure_initial_grub_default_backup

        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path.is_file.return_value = True
        mock_path.parent.exists.return_value = True

        mock_grub_d = MagicMock()
        mock_grub_d.exists.return_value = True
        mock_grub_d.iterdir.return_value = []

        def path_side_effect(p, *args, **kwargs):
            if "/etc/grub.d" in str(p):
                return mock_grub_d
            return mock_path

        with (
            patch("core.io.core_grub_default_io.Path", side_effect=path_side_effect),
            patch("core.io.core_grub_default_io.tarfile.open"),
        ):
            ensure_initial_grub_default_backup()

    def test_create_backup_coverage_boost(self):
        # Branche 260->259: grub.d loop
        from core.io.core_grub_default_io import create_grub_default_backup

        with (
            patch("core.io.core_grub_default_io.Path.exists", return_value=True),
            patch("core.io.core_grub_default_io.Path.is_file", return_value=True),
            patch("os.listdir", side_effect=[["10_linux"], []]),
            patch("core.io.core_grub_default_io.tarfile.open"),
        ):
            create_grub_default_backup()

    def test_create_backup_tar_add_oserror_path(self):
        # Branche 252-253: OSError in tar.add
        from core.io.core_grub_default_io import create_grub_default_backup

        mock_tar_obj = MagicMock()
        mock_tar_obj.add.side_effect = OSError("Add failed")
        with (
            patch("core.io.core_grub_default_io.Path.exists", return_value=True),
            patch("core.io.core_grub_default_io.Path.is_file", return_value=True),
            patch("core.io.core_grub_default_io.tarfile.open", return_value=mock_tar_obj),
        ):
            create_grub_default_backup()

    def test_best_fallback_no_valid_candidate(self):
        # Branche 422->411
        from core.io.core_grub_default_io import _best_fallback_for_missing_config

        with (
            patch("os.listdir", return_value=[]),
            patch("core.io.core_grub_default_io.glob", return_value=[]),
            patch("os.path.isfile", return_value=False),
        ):
            res = _best_fallback_for_missing_config("/etc/default/grub")
            assert res is None

    def test_best_fallback_with_mtime_error(self):
        from core.io.core_grub_default_io import _best_fallback_for_missing_config

        with (
            patch("core.io.core_grub_default_io.glob", return_value=["/etc/default/grub.backup.1"]),
            patch("os.path.isfile", return_value=True),
            patch("os.path.getmtime", side_effect=FileNotFoundError),
        ):
            try:
                _best_fallback_for_missing_config("/etc/default/grub")
            except FileNotFoundError:
                pass

    def test_restore_backup_success_check_files(self, tmp_path):
        # Branche 358->341: restore loop
        from core.io.core_grub_default_io import restore_grub_default_backup

        backup_path = tmp_path / "backup.tar.gz"
        grub_default = tmp_path / "grub"
        grub_default.write_text("GRUB_DEFAULT=0")
        with tarfile.open(backup_path, "w:gz") as tar:
            info = tarfile.TarInfo(name="other_file")
            info.size = 0
            tar.addfile(info)
        with patch("core.io.core_grub_default_io.GRUB_DEFAULT_PATH", str(grub_default)):
            restore_grub_default_backup(str(backup_path))

    def test_restore_backup_with_members_coverage(self, tmp_path):
        from core.io.core_grub_default_io import restore_grub_default_backup

        backup_path = tmp_path / "backup.tar.gz"
        grub_default = tmp_path / "grub"
        grub_default.write_text("GRUB_DEFAULT=0")
        with tarfile.open(backup_path, "w:gz") as tar:
            d = tmp_path / "etc_default"
            d.mkdir()
            f = d / "grub"
            f.write_text("TEST")
            tar.add(str(f), arcname="etc/default/grub")
            d2 = tmp_path / "etc_grub_d"
            d2.mkdir()
            f2 = d2 / "10_linux"
            f2.write_text("TEST2")
            tar.add(str(f2), arcname="etc/grub.d/10_linux")
        with (
            patch("core.io.core_grub_default_io.GRUB_DEFAULT_PATH", str(grub_default)),
            patch("os.remove"),
            patch("shutil.copy2"),
        ):
            restore_grub_default_backup(str(backup_path))
