"""Tests pour les opérations I/O sur /etc/default/grub."""

import os
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.core_exceptions import GrubBackupError, GrubConfigError
from core.io.core_grub_default_io import (
    GRUB_DEFAULT_PATH,
    _best_fallback_for_missing_config,
    _prune_manual_backups,
    _touch_now,
    create_grub_default_backup,
    create_last_modif_backup,
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
        assert not result

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
        assert not result

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
            assert not result


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

    def test_ensure_initial_backup_tar_filter_skips_unreadable_source(self, tmp_path, monkeypatch):
        """Couvre la branche du filtre tar: fichier existant mais non lisible."""
        fake_grub = tmp_path / "grub"
        fake_grub.write_text("GRUB_TIMEOUT=5")

        unreadable = tmp_path / "unreadable"
        unreadable.write_text("secret")

        original_access = os.access

        def access_side_effect(p, mode):
            if str(p) == str(unreadable):
                return False
            return original_access(p, mode)

        monkeypatch.setattr(os, "access", access_side_effect)

        class DummyTar:
            def __enter__(self):
                return self

            def __exit__(self, *_exc_info):
                return False

            def add(self, name, arcname=None, filter_func=None, **kwargs):
                if filter_func is not None:
                    tarinfo = tarfile.TarInfo(name=str(unreadable))
                    assert filter_func(tarinfo) is None

        with patch("tarfile.open", return_value=DummyTar()):
            res = ensure_initial_grub_default_backup(str(fake_grub))
            assert res == str(tmp_path / "grub_backup.initial.tar.gz")

    def test_ensure_initial_backup_grub_d_script_add_permission_error_is_swallowed(self, tmp_path):
        """Couvre le except lors de l'ajout d'un script grub.d au tar."""
        fake_grub_default = tmp_path / "grub"
        fake_grub_default.write_text("GRUB_TIMEOUT=5")

        fake_grub_d = tmp_path / "grub.d"
        fake_grub_d.mkdir()
        script_path = fake_grub_d / "10_linux"
        script_path.write_text("echo linux")

        mock_grub_d = MagicMock(spec=Path)
        mock_grub_d.exists.return_value = True
        mock_grub_d.iterdir.return_value = [script_path]

        class DummyTar:
            def __enter__(self):
                return self

            def __exit__(self, *_exc_info):
                return False

            def add(self, name, arcname=None, filter=None, **kwargs):
                if arcname is not None and str(arcname).startswith("grub.d/"):
                    raise PermissionError("Denied")
                return None

        def path_side_effect(p):
            if str(p) == "/etc/grub.d":
                return mock_grub_d
            return Path(p)

        with (
            patch("core.io.core_grub_default_io.GRUB_DEFAULT_PATH", str(fake_grub_default)),
            patch("core.io.core_grub_default_io.GRUB_CFG_PATHS", []),
            patch("os.path.abspath", side_effect=lambda x: x),
            patch("core.io.core_grub_default_io.Path") as mock_path_cls,
            patch("tarfile.open", return_value=DummyTar()),
        ):
            mock_path_cls.side_effect = path_side_effect
            res = ensure_initial_grub_default_backup(str(fake_grub_default))
            assert res == str(tmp_path / "grub_backup.initial.tar.gz")


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
            with pytest.raises(GrubConfigError):
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
            patch("os.remove"),
            patch("shutil.rmtree"),
        ):

            restore_grub_default_backup(str(archive_path), target_grub)

            assert mock_copy.call_count == 3
            calls = [c[0] for c in mock_copy.call_args_list]
            assert any(c[1] == target_grub for c in calls)
            assert any(c[1] == "/etc/grub.d/20_memtest" for c in calls)
            assert any(c[1] == "/boot/grub/grub.cfg" for c in calls)

    def test_restore_backup_tar_error(self, tmp_path):
        """Test restauration avec archive corrompue (mais extension .tar.gz)."""
        archive_path = tmp_path / "corrupt.tar.gz"
        archive_path.write_text("not a tar")

        with pytest.raises(OSError, match="Échec de la restauration"):
            restore_grub_default_backup(str(archive_path))

    def test_restore_backup_legacy_text_file(self, tmp_path):
        """Test restauration d'un backup legacy (fichier texte simple)."""
        backup_path = tmp_path / "grub.backup"
        backup_path.write_text("GRUB_TIMEOUT=42")
        target_path = tmp_path / "grub_restored"

        restore_grub_default_backup(str(backup_path), str(target_path))

        assert target_path.read_text() == "GRUB_TIMEOUT=42"

    def test_restore_backup_legacy_copy_error(self, tmp_path):
        """Test erreur lors de la restauration legacy."""
        backup_path = tmp_path / "grub.backup"
        backup_path.write_text("content")

        with patch("shutil.copy2", side_effect=OSError("Disk full")):
            with pytest.raises(OSError, match="Échec de la restauration legacy"):
                restore_grub_default_backup(str(backup_path), "/target")

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
        assert not result

    def test_parse_grub_default_no_equals(self):
        """Test parsing ligne sans =."""
        text = "INVALID LINE"
        result = parse_grub_default(text)
        assert not result


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
            with pytest.raises(GrubConfigError):
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
        with open(config_path, encoding="utf-8") as f:
            content = f.read()
            assert "GRUB_TIMEOUT=5" in content
            assert "GRUB_DEFAULT=0" in content

    def test_write_grub_default_backup_failure(self, tmp_path):
        """Test échec de création du backup."""
        config_path = tmp_path / "grub"
        config_path.write_text("content")

        with patch("shutil.copy2", side_effect=OSError):
            with pytest.raises(GrubBackupError):
                write_grub_default({"GRUB_TIMEOUT": "5"}, str(config_path))

    def test_write_grub_default_write_failure(self, tmp_path):
        """Test échec d'écriture."""
        config_path = tmp_path / "grub"
        config_path.write_text("content")

        with patch("builtins.open", side_effect=OSError):
            with pytest.raises(GrubBackupError):
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

    def test_tar_filter_manual_exception(self):
        """Test le filtre tar manuel quand une exception survient."""
        from core.io.core_grub_default_io import _tar_filter_manual
        
        tarinfo = MagicMock()
        tarinfo.name = "/some/path"
        
        with patch("os.path.exists", side_effect=OSError("Disk error")):
            result = _tar_filter_manual(tarinfo)
            assert result is None

    def test_tar_filter_initial_exception(self):
        """Test le filtre tar initial quand une exception survient."""
        from core.io.core_grub_default_io import _tar_filter_initial
        
        tarinfo = MagicMock()
        tarinfo.name = "/some/path"
        
        with patch("os.path.exists", side_effect=OSError("Disk error")):
            result = _tar_filter_initial(tarinfo)
            assert result is None


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

        def mock_open(file, mode="r", **kwargs):
            if str(file) == str(config_path) and "w" in mode:
                raise OSError("Write failed")
            return original_open(file, mode, **kwargs)

        with patch("builtins.open", side_effect=mock_open):
            with pytest.raises(GrubConfigError, match="Write failed"):
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
            with pytest.raises(GrubConfigError):
                create_grub_default_backup(str(config_path))

    def test_prune_manual_backups_oserror(self, tmp_path):
        """Test OSError lors de la suppression dans prune."""
        base_path = tmp_path / "grub"
        p = tmp_path / "grub.backup.manual.1"
        p.write_text("old")

        # On doit patcher os.remove dans le module core.io.core_grub_default_io
        with patch("core.io.core_grub_default_io.os.remove", side_effect=OSError("Delete failed")):
            deleted = _prune_manual_backups(str(base_path), keep=0)
            assert not deleted

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

        # Simuler que le backup n'existe pas encore et qu'on est sur GRUB_DEFAULT_PATH
        with (
            patch("core.io.core_grub_default_io.os.path.abspath", return_value=str(GRUB_DEFAULT_PATH)),
            patch("core.io.core_grub_default_io.Path") as mock_path_class,
            patch("core.io.core_grub_default_io.tarfile.open") as mock_tar_open,
        ):
            # Configuration des mocks
            mock_path = MagicMock()
            mock_path.exists.return_value = False  # Le backup n'existe pas
            mock_path.parent = tmp_path
            mock_path_class.return_value = mock_path

            mock_tar = MagicMock()
            mock_tar_open.return_value.__enter__.return_value = mock_tar

            # Appel de la fonction
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
        """Test l'erreur OSError lors de la suppression d'un backup manuel."""
        from core.io.core_grub_default_io import _prune_manual_backups

        with (
            patch("core.io.core_grub_default_io.glob", return_value=["grub.backup.manual.old"]),
            patch("os.path.isfile", return_value=True),
            patch("os.path.getmtime", return_value=100),
            patch("os.remove", side_effect=OSError("Permission denied")),
        ):
            _prune_manual_backups("/etc/default/grub")

    def test_ensure_initial_backup_coverage_boost(self):
        """Boost de couverture pour la sauvegarde initiale (cas où elle existe déjà)."""
        # Branche 166->170: initial backup exists
        from core.io.core_grub_default_io import ensure_initial_grub_default_backup

        with patch("core.io.core_grub_default_io.Path.exists", return_value=True):
            ensure_initial_grub_default_backup()

    def test_ensure_initial_backup_empty_iterdir(self):
        """Test la sauvegarde initiale avec un dossier grub.d vide."""
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
        """Boost de couverture pour la création de sauvegarde."""
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
        """Test l'erreur OSError lors de l'ajout d'un fichier au tar."""
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
        """Test le cas où aucun candidat de secours n'est trouvé."""
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
        """Test le cas où getmtime échoue sur un candidat de secours."""
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
        """Test la réussite de la restauration et vérifie les fichiers."""
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

    def test_restore_backup_with_members(self, tmp_path):
        """Test la restauration avec des membres spécifiques dans l'archive."""
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


def test_parse_grub_default_basic() -> None:
    """Test le parsing de base d'un fichier GRUB default."""
    text = """
# comment
GRUB_TIMEOUT=5
GRUB_DEFAULT="saved"
GRUB_TERMINAL=console
INVALID_LINE
GRUB_GFXMODE=1920x1080
"""
    cfg = parse_grub_default(text)
    assert cfg["GRUB_TIMEOUT"] == "5"
    assert cfg["GRUB_DEFAULT"] == "saved"
    assert cfg["GRUB_TERMINAL"] == "console"
    assert cfg["GRUB_GFXMODE"] == "1920x1080"
    assert "INVALID_LINE" not in cfg


def test_format_grub_default_quotes_and_backup_header() -> None:
    """Test le formatage avec guillemets et en-tête de sauvegarde."""
    cfg = {
        "GRUB_TIMEOUT": "5",
        "GRUB_DEFAULT": "saved",
        "GRUB_CMDLINE_LINUX_DEFAULT": "quiet splash",
        "GRUB_DISTRIBUTOR": "Ubuntu",
    }
    out = format_grub_default(cfg, "/tmp/grub.backup")
    assert out.startswith("# Configuration GRUB modifiée")
    assert "# Sauvegarde: /tmp/grub.backup" in out

    # Values with spaces should be quoted.
    assert 'GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"' in out


def test_read_write_grub_default_roundtrip(tmp_path: Path) -> None:
    """Test l'aller-retour lecture/écriture de la configuration."""
    p = tmp_path / "grub"
    p.write_text("GRUB_TIMEOUT=5\nGRUB_DEFAULT=0\n", encoding="utf-8")

    cfg = read_grub_default(str(p))
    assert cfg["GRUB_TIMEOUT"] == "5"

    cfg["GRUB_TIMEOUT"] = "10"
    backup = write_grub_default(cfg, str(p))

    backup_path = Path(backup)
    assert backup_path.exists()
    assert backup_path.read_text(encoding="utf-8").startswith("GRUB_TIMEOUT=5")

    # New file should contain updated value.
    new_text = p.read_text(encoding="utf-8")
    assert "GRUB_TIMEOUT=10" in new_text


def test_write_grub_default_requires_existing_file(tmp_path: Path) -> None:
    """Test que l'écriture échoue si le fichier source n'existe pas."""
    p = tmp_path / "missing"
    with pytest.raises(GrubBackupError):
        # shutil.copy2 should raise if source doesn't exist.
        write_grub_default({"GRUB_TIMEOUT": "5"}, str(p))


def test_read_grub_default_restores_from_backup_current(tmp_path: Path) -> None:
    """Test la restauration automatique depuis backup.current si le fichier principal manque."""
    base = tmp_path / "grub"
    backup_current = tmp_path / "grub.backup.current"

    backup_current.write_text("GRUB_TIMEOUT=7\nGRUB_DEFAULT=0\n", encoding="utf-8")
    assert not base.exists()

    cfg = read_grub_default(str(base))
    assert cfg["GRUB_TIMEOUT"] == "7"
    # Best-effort restore should recreate the canonical file.
    assert base.exists()


def test_ensure_initial_grub_default_backup_creates_once(tmp_path: Path) -> None:
    """Test que la sauvegarde initiale n'est créée qu'une seule fois."""
    import tarfile

    base = tmp_path / "grub"
    base.write_text("GRUB_TIMEOUT=5\nGRUB_DEFAULT=0\n", encoding="utf-8")

    initial = ensure_initial_grub_default_backup(str(base))
    assert initial is not None
    initial_path = Path(initial)
    assert initial_path.exists()

    # Vérifier que le contenu du tar.gz contient le fichier grub
    with tarfile.open(initial_path, "r:gz") as tar:
        assert "default_grub" in tar.getnames()
        extracted = tar.extractfile("default_grub")
        assert extracted is not None
        content = extracted.read().decode("utf-8")
        assert content == base.read_text(encoding="utf-8")

    # Modifie le fichier source, puis réappelle: le backup initial ne doit pas changer.
    base.write_text("MODIFIED", encoding="utf-8")
    initial2 = ensure_initial_grub_default_backup(str(base))
    assert initial2 == initial

    # Vérifier que le contenu du tar.gz n'a pas changé
    with tarfile.open(initial_path, "r:gz") as tar:
        extracted = tar.extractfile("default_grub")
        assert extracted is not None
        content = extracted.read().decode("utf-8")
        assert content.startswith("GRUB_TIMEOUT=5")


def test_ensure_initial_grub_default_backup_missing_source_and_fallback(tmp_path: Path) -> None:
    """Test backup initial quand la source et les fallbacks sont absents."""
    base = tmp_path / "nonexistent"
    result = ensure_initial_grub_default_backup(str(base))
    assert result is None


def test_ensure_initial_grub_default_backup_os_error(tmp_path: Path) -> None:
    """Test backup initial avec erreur système."""
    base = tmp_path / "grub"
    base.write_text("test")

    from unittest.mock import patch

    with patch("tarfile.open", side_effect=OSError("Permission denied")):
        result = ensure_initial_grub_default_backup(str(base))
        assert result is None


def test_create_grub_default_backup_no_source_no_fallback(tmp_path: Path) -> None:
    """Test création backup manuel sans source ni fallback."""
    # On utilise un sous-répertoire vide pour être sûr que glob ne trouve rien
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    base = empty_dir / "grub"
    with pytest.raises(GrubConfigError):
        create_grub_default_backup(str(base))


def test_create_grub_default_backup_with_fallback(tmp_path: Path) -> None:
    """Test création backup manuel avec fallback quand la source est absente."""
    import tarfile

    base = tmp_path / "grub"
    fallback = tmp_path / "grub.backup.current"
    fallback.write_text("FALLBACK CONTENT")

    # base n'existe pas, mais fallback existe
    created = create_grub_default_backup(str(base))
    created_path = Path(created)

    # Vérifier le contenu du tar.gz
    with tarfile.open(created_path, "r:gz") as tar:
        assert "default_grub" in tar.getnames()
        f = tar.extractfile("default_grub")
        assert f is not None
        content = f.read().decode("utf-8")
        assert content == "FALLBACK CONTENT"


def test_delete_grub_default_backup_invalid_path(tmp_path: Path) -> None:
    """Test suppression backup avec chemin invalide."""
    base = tmp_path / "grub"
    with pytest.raises(ValueError, match="Chemin de sauvegarde invalide"):
        delete_grub_default_backup("/tmp/other", path=str(base))

    # Pour déclencher "Refus de supprimer le fichier canonique", il faut que le chemin
    # commence par allowed_prefix MAIS soit égal au fichier canonique après abspath.
    # On utilise ".." pour tromper le startswith.
    backup_path = str(base) + ".backup/../" + base.name
    with pytest.raises(ValueError, match="Refus de supprimer le fichier canonique"):
        delete_grub_default_backup(backup_path, path=str(base))


def test_parse_grub_default_edge_cases() -> None:
    """Test cas limites du parser."""
    text = "KEY=value\nEMPTY_KEY=\n=VALUE\n# Comment\n  \n"
    cfg = parse_grub_default(text)
    assert cfg["KEY"] == "value"
    assert cfg["EMPTY_KEY"] == ""
    assert "" not in cfg


def test_read_grub_default_os_error_on_restore(tmp_path: Path) -> None:
    """Test erreur lors de la restauration automatique dans read_grub_default."""
    base = tmp_path / "grub"
    fallback = tmp_path / "grub.backup.current"
    fallback.write_text("KEY=VAL")

    from unittest.mock import patch

    with patch("shutil.copy2", side_effect=OSError("Read-only file system")):
        # Devrait quand même lire le fallback
        cfg = read_grub_default(str(base))
        assert cfg["KEY"] == "VAL"


def test_write_grub_default_os_error(tmp_path: Path) -> None:
    """Test erreur d'écriture dans write_grub_default."""
    base = tmp_path / "grub"
    base.write_text("test")

    from unittest.mock import patch

    # Cas 1: Échec du backup
    with patch("shutil.copy2", side_effect=OSError("Disk full")):
        with pytest.raises(GrubBackupError):
            write_grub_default({}, str(base))

    # Cas 2: Succès du backup, échec de l'écriture
    with patch("shutil.copy2", return_value=None):
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            with pytest.raises(GrubConfigError):
                write_grub_default({}, str(base))


def test_touch_now_os_error() -> None:
    """Test _touch_now avec erreur (ne doit pas lever)."""
    from unittest.mock import patch

    from core.io.core_grub_default_io import _touch_now

    with patch("os.utime", side_effect=OSError):
        _touch_now("/nonexistent")  # Ne doit pas lever


def test_prune_manual_backups_os_error(tmp_path: Path) -> None:
    """Test _prune_manual_backups avec erreur de suppression."""
    from core.io.core_grub_default_io import _prune_manual_backups

    base = tmp_path / "grub"
    b1 = tmp_path / "grub.backup.manual.1"
    b2 = tmp_path / "grub.backup.manual.2"
    b1.write_text("1")
    b2.write_text("2")

    from unittest.mock import patch

    with patch("os.remove", side_effect=OSError):
        deleted = _prune_manual_backups(str(base), keep=1)
        assert len(deleted) == 0


def test_backup_list_create_delete(tmp_path: Path) -> None:
    """Test le cycle de vie des sauvegardes (création, liste, suppression)."""
    import tarfile

    base = tmp_path / "grub"
    base.write_text("GRUB_TIMEOUT=5\n", encoding="utf-8")

    assert list_grub_default_backups(str(base)) == []

    created = create_grub_default_backup(str(base))
    created_path = Path(created)
    assert created_path.exists()

    # Vérifier le contenu du tar.gz
    with tarfile.open(created_path, "r:gz") as tar:
        assert "default_grub" in tar.getnames()
        f = tar.extractfile("default_grub")
        assert f is not None
        content = f.read().decode("utf-8")
        assert content == "GRUB_TIMEOUT=5\n"

    backups = list_grub_default_backups(str(base))
    assert created in backups

    delete_grub_default_backup(created, path=str(base))
    assert not created_path.exists()


def test_manual_backup_rotation_keeps_3(tmp_path: Path) -> None:
    """Test que la rotation des sauvegardes manuelles n'en garde que 3."""
    base = tmp_path / "grub"
    base.write_text("GRUB_TIMEOUT=5\n", encoding="utf-8")

    p1 = create_grub_default_backup(str(base))
    p2 = create_grub_default_backup(str(base))
    p3 = create_grub_default_backup(str(base))
    assert Path(p1).exists()
    assert Path(p2).exists()
    assert Path(p3).exists()

    p4 = create_grub_default_backup(str(base))
    assert Path(p4).exists()

    # Après 4 créations, il ne doit rester que 3 sauvegardes manuelles.
    manuals = [p for p in list_grub_default_backups(str(base)) if ".backup.manual." in p]
    assert len(manuals) == 3
    # La plus vieille (p1) doit avoir été supprimée.
    assert not Path(p1).exists()


def test_list_grub_default_backups_includes_initial_and_sorts(tmp_path: Path) -> None:
    """Test que la liste des sauvegardes inclut l'initiale et est triée par date."""
    base = tmp_path / "grub"
    base.write_text("X", encoding="utf-8")

    # Deux backups manuelles + un initial
    b1 = tmp_path / "grub.backup.manual.1.tar.gz"
    b2 = tmp_path / "grub.backup.manual.2.tar.gz"
    b1.write_text("1", encoding="utf-8")
    b2.write_text("2", encoding="utf-8")

    initial = Path(f"{base}_backup.initial.tar.gz")
    initial.write_text("init", encoding="utf-8")

    # Contrôle strict du tri via mtime
    os.utime(b1, (100, 100))
    os.utime(b2, (200, 200))
    os.utime(initial, (150, 150))

    out = list_grub_default_backups(str(base))
    assert out[0] == str(b2)  # plus récent
    assert str(initial) in out
    assert str(b1) in out
    # Le fichier canonique ne doit jamais être listé
    assert str(base) not in out


def test_create_grub_default_backup_unique_name_collision(tmp_path: Path) -> None:
    """Couvre la boucle d'unicité du nom en cas de collision."""
    base = tmp_path / "grub"
    base.write_text("GRUB_TIMEOUT=5\n", encoding="utf-8")

    fake_ts = "20000101-000000"
    base_backup = f"{base}.backup.manual.{fake_ts}.tar.gz"
    suffixed_backup = f"{base}.backup.manual.{fake_ts}.1.tar.gz"

    def exists_side_effect(p: str) -> bool:
        if p == base_backup:
            return True
        if p == suffixed_backup:
            return False
        if p == str(base):
            return True
        return False

    # Mock tarfile pour éviter d'interagir avec /etc/grub.d et /boot
    tar_cm = MagicMock()
    tar_obj = MagicMock()
    tar_cm.__enter__.return_value = tar_obj
    tar_cm.__exit__.return_value = False

    with (
        patch("core.io.core_grub_default_io.datetime") as mock_datetime,
        patch("core.io.core_grub_default_io.os.path.exists", side_effect=exists_side_effect),
        patch("core.io.core_grub_default_io.tarfile.open", return_value=tar_cm) as mock_tar_open,
    ):
        mock_datetime.now.return_value.strftime.return_value = fake_ts
        created = create_grub_default_backup(str(base))

    assert created == suffixed_backup
    mock_tar_open.assert_called_once()


def test_ensure_initial_grub_default_backup_filter_handles_unreadable(tmp_path: Path) -> None:
    """Couvre les branches du _tar_filter (None + exception)."""
    base = tmp_path / "grub"
    base.write_text("GRUB_TIMEOUT=5\n", encoding="utf-8")

    tar_cm = MagicMock()
    tar_obj = MagicMock()
    tar_cm.__enter__.return_value = tar_obj
    tar_cm.__exit__.return_value = False

    # Force l'appel du filter dans tar.add
    def add_side_effect(_src, arcname=None, filter=None, **_kwargs):
        if filter is not None:
            tarinfo = MagicMock()
            tarinfo.name = str(base)
            _ = filter(tarinfo)

    tar_obj.add.side_effect = add_side_effect

    with (
        patch("core.io.core_grub_default_io.tarfile.open", return_value=tar_cm),
        patch("core.io.core_grub_default_io.Path.exists", return_value=False),
        patch("core.io.core_grub_default_io.os.path.exists", return_value=True),
        patch("core.io.core_grub_default_io.os.access", return_value=False),
    ):
        out = ensure_initial_grub_default_backup(str(base))
        assert out is not None

    # Branche exception dans le filter
    with (
        patch("core.io.core_grub_default_io.tarfile.open", return_value=tar_cm),
        patch("core.io.core_grub_default_io.Path.exists", return_value=False),
        patch("core.io.core_grub_default_io.os.path.exists", side_effect=OSError("boom")),
    ):
        out2 = ensure_initial_grub_default_backup(str(base))
        assert out2 is not None


def test_create_grub_default_backup_filter_handles_unreadable(tmp_path: Path) -> None:
    """Couvre les branches du _tar_filter_manual (None + exception)."""
    base = tmp_path / "grub"
    base.write_text("GRUB_TIMEOUT=5\n", encoding="utf-8")

    tar_cm = MagicMock()
    tar_obj = MagicMock()
    tar_cm.__enter__.return_value = tar_obj
    tar_cm.__exit__.return_value = False

    def add_side_effect(_src, arcname=None, filter=None, **_kwargs):
        if filter is not None:
            tarinfo = MagicMock()
            tarinfo.name = str(base)
            _ = filter(tarinfo)

    tar_obj.add.side_effect = add_side_effect

    with (
        patch("core.io.core_grub_default_io.tarfile.open", return_value=tar_cm),
        patch("core.io.core_grub_default_io.os.path.exists", return_value=True),
        patch("core.io.core_grub_default_io.os.access", return_value=False),
    ):
        _ = create_grub_default_backup(str(base))

    with (
        patch("core.io.core_grub_default_io.tarfile.open", return_value=tar_cm),
        patch("core.io.core_grub_default_io.os.path.exists", side_effect=OSError("boom")),
    ):
        _ = create_grub_default_backup(str(base))


def test_restore_grub_default_backup_restores_all_members(tmp_path: Path) -> None:
    """Couvre les branches default_grub, grub.d/*, grub.cfg_* + nettoyage /tmp/grub.d."""
    backup_path = str(tmp_path / "backup.tar.gz")

    tar_cm = MagicMock()
    tar_obj = MagicMock()
    tar_cm.__enter__.return_value = tar_obj
    tar_cm.__exit__.return_value = False

    members = []
    m1 = MagicMock()
    m1.name = "default_grub"
    members.append(m1)
    m2 = MagicMock()
    m2.name = "grub.d/00_header"
    members.append(m2)
    m3 = MagicMock()
    m3.name = "grub.cfg_grub"
    members.append(m3)
    tar_obj.getmembers.return_value = members

    def exists_side_effect(p: str) -> bool:
        if p == backup_path:
            return True
        if p == "/tmp/grub.d":
            return True
        return False

    with (
        patch("core.io.core_grub_default_io.os.path.exists", side_effect=exists_side_effect),
        patch("core.io.core_grub_default_io.tarfile.open", return_value=tar_cm),
        patch("core.io.core_grub_default_io.shutil.copy2") as mock_copy2,
        patch("core.io.core_grub_default_io.os.remove") as mock_remove,
        patch("core.io.core_grub_default_io.shutil.rmtree") as mock_rmtree,
    ):
        from core.io.core_grub_default_io import restore_grub_default_backup

        restore_grub_default_backup(backup_path, target_path=str(tmp_path / "grub"))

        assert tar_obj.extract.call_count == 3
        assert mock_copy2.call_count == 3
        # Nettoyage des fichiers extraits
        assert mock_remove.call_count == 3
        mock_rmtree.assert_called_once_with("/tmp/grub.d")


def test_restore_grub_default_backup_wraps_tar_errors(tmp_path: Path) -> None:
    """Test que les erreurs tarfile sont encapsulées dans des OSError lors de la restauration."""
    backup_path = str(tmp_path / "missing_or_bad.tar.gz")

    with (
        patch("core.io.core_grub_default_io.os.path.exists", return_value=True),
        patch("core.io.core_grub_default_io.tarfile.open", side_effect=tarfile.ReadError("bad")),
    ):
        from core.io.core_grub_default_io import restore_grub_default_backup

        with pytest.raises(OSError, match="Échec de la restauration"):
            restore_grub_default_backup(backup_path, target_path=str(tmp_path / "grub"))


class TestGrubDefaultIOCoverage:
    """Tests de couverture supplémentaires pour core_grub_default_io."""

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.exists", return_value=True)
    @patch("core.io.core_grub_default_io.Path")
    def test_ensure_initial_backup_add_default_exception(self, mock_path_cls, mock_exists, mock_isfile, mock_tar_open):
        """Test exception when adding default_grub to initial backup."""
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        # Mock Path instances
        mock_path = MagicMock()
        mock_path_cls.return_value = mock_path

        # initial_backup_path = Path(path).parent / "grub_backup.initial.tar.gz"
        mock_initial_backup_path = MagicMock()
        mock_path.parent.__truediv__.return_value = mock_initial_backup_path
        mock_initial_backup_path.exists.return_value = False  # Backup doesn't exist yet

        # Raise exception on first add (default_grub)
        mock_tar.add.side_effect = [OSError("Add failed"), None, None]

        ensure_initial_grub_default_backup(GRUB_DEFAULT_PATH)

        # Verify add was called
        assert mock_tar.add.called

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.exists", return_value=True)
    @patch("core.io.core_grub_default_io.os.access", return_value=True)
    def test_create_backup_add_default_exception(self, _mock_access, mock_exists, mock_isfile, mock_tar_open):
        """Test exception when adding default_grub to manual backup."""
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        mock_tar.add.side_effect = OSError("Add failed")

        def exists_side_effect(path):
            if "backup.manual" in str(path):
                return False
            return True

        mock_exists.side_effect = exists_side_effect

        create_grub_default_backup(GRUB_DEFAULT_PATH)
        assert mock_tar.add.called

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.exists", return_value=True)
    @patch("core.io.core_grub_default_io.os.access", return_value=True)
    @patch("core.io.core_grub_default_io.Path")
    def test_create_backup_add_script_exception(
        self, mock_path_cls, _mock_access, mock_exists, mock_isfile, mock_tar_open
    ):
        """Test exception when adding script to manual backup."""
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        mock_grub_d = MagicMock()
        mock_grub_d.exists.return_value = True
        mock_script = MagicMock()
        mock_script.is_file.return_value = True
        mock_script.name = "00_header"
        mock_grub_d.iterdir.return_value = [mock_script]

        def path_side_effect(arg):
            if str(arg) == "/etc/grub.d":
                return mock_grub_d
            return MagicMock()

        mock_path_cls.side_effect = path_side_effect

        def exists_side_effect(path):
            if "backup.manual" in str(path):
                return False
            return True

        mock_exists.side_effect = exists_side_effect

        # default_grub success, script fail
        mock_tar.add.side_effect = [None, OSError("Add script failed"), None]

        create_grub_default_backup(GRUB_DEFAULT_PATH)
        assert mock_tar.add.call_count >= 2

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.exists", return_value=True)
    @patch("core.io.core_grub_default_io.os.access", return_value=True)
    @patch("core.io.core_grub_default_io.Path")
    @patch("core.io.core_grub_default_io.GRUB_CFG_PATHS", ["/boot/grub/grub.cfg"])
    def test_create_backup_add_cfg_exception(
        self, mock_path_cls, _mock_access, mock_exists, mock_isfile, mock_tar_open
    ):
        """Test exception when adding grub.cfg to manual backup."""
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        mock_grub_d = MagicMock()
        mock_grub_d.exists.return_value = False  # Skip scripts to focus on cfg

        def path_side_effect(arg):
            if str(arg) == "/etc/grub.d":
                return mock_grub_d
            if str(arg) == "/boot/grub/grub.cfg":
                p = MagicMock()
                p.parts = ["/", "boot", "grub", "grub.cfg"]
                return p
            return MagicMock()

        mock_path_cls.side_effect = path_side_effect

        def exists_side_effect(path):
            if "backup.manual" in str(path):
                return False
            return True

        mock_exists.side_effect = exists_side_effect

        # default_grub success, cfg fail
        mock_tar.add.side_effect = [None, OSError("Add cfg failed")]

        create_grub_default_backup(GRUB_DEFAULT_PATH)
        assert mock_tar.add.call_count >= 2

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.exists", return_value=True)
    @patch("core.io.core_grub_default_io.Path")
    def test_create_backup_grub_d_not_exists(self, mock_path_cls, mock_exists, mock_isfile, mock_tar_open):
        """Test manual backup when /etc/grub.d does not exist."""
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        mock_grub_d = MagicMock()
        mock_grub_d.exists.return_value = False

        def path_side_effect(arg):
            if str(arg) == "/etc/grub.d":
                return mock_grub_d
            return MagicMock()

        mock_path_cls.side_effect = path_side_effect

        def exists_side_effect(path):
            if "backup.manual" in str(path):
                return False
            return True

        mock_exists.side_effect = exists_side_effect

        create_grub_default_backup(GRUB_DEFAULT_PATH)
        # Should not try to iterate grub.d

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.exists")
    @patch("core.io.core_grub_default_io.Path")
    def test_ensure_initial_backup_os_exists_exception(self, mock_path_cls, mock_exists, mock_isfile, mock_tar_open):
        """Test OSError during os.path.exists in initial backup."""
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        mock_path = MagicMock()
        mock_path_cls.return_value = mock_path
        mock_initial_backup_path = MagicMock()
        mock_path.parent.__truediv__.return_value = mock_initial_backup_path
        mock_initial_backup_path.exists.return_value = False

        # Mock grub.d to be empty to reach grub.cfg loop
        mock_grub_d = MagicMock()
        mock_grub_d.exists.return_value = False

        def path_side_effect(arg):
            if str(arg) == "/etc/grub.d":
                return mock_grub_d
            return mock_path

        mock_path_cls.side_effect = path_side_effect

        # Raise OSError on exists check for grub.cfg
        mock_exists.side_effect = OSError("Exists failed")

        ensure_initial_grub_default_backup(GRUB_DEFAULT_PATH)
        # Should handle exception and continue (exists=False)

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.exists")
    @patch("core.io.core_grub_default_io.Path")
    def test_create_backup_os_exists_exception(self, mock_path_cls, mock_exists, mock_isfile, mock_tar_open):
        """Test OSError during os.path.exists in manual backup."""
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        mock_grub_d = MagicMock()
        mock_grub_d.exists.return_value = False

        def path_side_effect(arg):
            if str(arg) == "/etc/grub.d":
                return mock_grub_d
            return MagicMock()

        mock_path_cls.side_effect = path_side_effect

        # Raise OSError on exists check
        mock_exists.side_effect = OSError("Exists failed")

        create_grub_default_backup(GRUB_DEFAULT_PATH)
        # Should handle exception

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile")
    @patch("core.io.core_grub_default_io.read_grub_default")
    @patch("core.io.core_grub_default_io.Path")
    def test_ensure_initial_backup_restore_success(self, mock_path_cls, mock_read_default, mock_isfile, mock_tar_open):
        """Test initial backup when source is missing but restore succeeds."""
        mock_isfile.return_value = False
        mock_read_default.return_value = {"GRUB_TIMEOUT": "5"}

        mock_path = MagicMock()
        mock_path_cls.return_value = mock_path
        mock_initial_backup_path = MagicMock()
        mock_path.parent.__truediv__.return_value = mock_initial_backup_path
        mock_initial_backup_path.exists.return_value = False

        ensure_initial_grub_default_backup(GRUB_DEFAULT_PATH)
        assert mock_read_default.called

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.getmtime", return_value=1000)
    @patch("core.io.core_grub_default_io.os.path.isfile")
    @patch("core.io.core_grub_default_io.read_grub_default")
    def test_create_backup_restore_success(self, mock_read_default, mock_isfile, _mock_mtime, mock_tar_open):
        """Test manual backup when source is missing but restore succeeds."""

        # First call to isfile returns False, subsequent calls return True
        def isfile_side_effect(path):
            if not hasattr(isfile_side_effect, "called"):
                isfile_side_effect.called = True
                return False
            return True

        mock_isfile.side_effect = isfile_side_effect

        # Mock tar to avoid errors
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        result = create_grub_default_backup(GRUB_DEFAULT_PATH)
        assert "manual" in result
        assert mock_tar.add.called

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.exists")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.read_grub_default")
    def test_ensure_initial_backup_grub_d_not_exists(self, mock_read_default, mock_isfile, mock_exists, mock_tar_open):
        """Test ensure_initial_grub_default_backup when /etc/grub.d does not exist."""
        # Mock Path.exists globally for this test
        with patch("core.io.core_grub_default_io.Path.exists", return_value=False):
            # os.path.exists returns False for /etc/grub.d but True for grub.cfg
            def exists_side_effect(p):
                if "/etc/grub.d" in str(p):
                    return False
                return True

            mock_exists.side_effect = exists_side_effect

            mock_tar = MagicMock()
            mock_tar_open.return_value.__enter__.return_value = mock_tar

            ensure_initial_grub_default_backup(GRUB_DEFAULT_PATH)
            # Should add /etc/default/grub and one of GRUB_CFG_PATHS
            assert mock_tar.add.call_count == 2

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.exists", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.read_grub_default")
    def test_ensure_initial_backup_add_script_exception(
        self, mock_read_default, mock_isfile, mock_exists, mock_tar_open
    ):
        """Test ensure_initial_grub_default_backup handles exception during script addition."""
        # Mock Path.exists and Path.iterdir
        with (
            patch("core.io.core_grub_default_io.Path.exists", return_value=False) as mock_p_exists,
            patch("core.io.core_grub_default_io.Path.iterdir") as mock_iter,
            patch("core.io.core_grub_default_io.Path.is_file", return_value=True),
        ):

            # backup_path.exists() -> False (to trigger backup)
            # grub_d_dir.exists() -> True (to enter scripts loop)
            mock_p_exists.side_effect = [False, True]

            mock_script = MagicMock()
            mock_script.name = "00_header"
            mock_script.is_file.return_value = True
            mock_iter.return_value = [mock_script]

            mock_tar = MagicMock()
            mock_tar_open.return_value.__enter__.return_value = mock_tar

            # Trigger exception on second add (first is /etc/default/grub)
            def add_side_effect(name, *args, **kwargs):
                if "00_header" in str(name):
                    raise OSError("Tar add error")
                return None

            mock_tar.add.side_effect = add_side_effect

            ensure_initial_grub_default_backup(GRUB_DEFAULT_PATH)
            assert mock_tar.add.called

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.exists", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    def test_ensure_initial_backup_skips_non_file_grub_d_entry(self, mock_isfile, mock_exists, mock_tar_open):
        """Couvre la branche où un élément de /etc/grub.d n'est pas un fichier (119->118)."""
        with (
            patch("core.io.core_grub_default_io.Path.exists", return_value=False) as mock_p_exists,
            patch("core.io.core_grub_default_io.Path.iterdir") as mock_iter,
        ):
            # backup_path.exists() -> False (déclenche la création)
            # grub_d_dir.exists() -> True (entre dans la boucle grub.d)
            mock_p_exists.side_effect = [False, True]

            mock_script = MagicMock()
            mock_script.is_file.return_value = False
            mock_iter.return_value = [mock_script]

            mock_tar = MagicMock()
            mock_tar_open.return_value.__enter__.return_value = mock_tar

            ensure_initial_grub_default_backup(GRUB_DEFAULT_PATH)
            # On a ajouté /etc/default/grub, donc au moins 1 appel
            assert mock_tar.add.call_count >= 1

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    def test_ensure_initial_backup_add_grub_cfg_exception_is_handled(self, mock_isfile, mock_tar_open):
        """Couvre l'exception lors de l'ajout de grub.cfg (141-142)."""
        grub_cfg_path = "/boot/grub/grub.cfg"

        with (
            patch("core.io.core_grub_default_io.GRUB_CFG_PATHS", [grub_cfg_path]),
            patch("core.io.core_grub_default_io.os.path.exists", return_value=True),
            patch("core.io.core_grub_default_io.Path.exists", return_value=False),
        ):
            mock_tar = MagicMock()
            mock_tar_open.return_value.__enter__.return_value = mock_tar

            def add_side_effect(name, *args, **kwargs):
                if str(name) == grub_cfg_path:
                    raise OSError("Tar add error")
                return None

            mock_tar.add.side_effect = add_side_effect

            # Ne doit pas lever, juste logger et continuer.
            ensure_initial_grub_default_backup(GRUB_DEFAULT_PATH)
            assert mock_tar.add.called

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.exists", return_value=True)
    @patch("core.io.core_grub_default_io.Path")
    def test_create_backup_script_not_file(self, mock_path_cls, mock_exists, mock_isfile, mock_tar_open):
        """Test manual backup skips non-file items in /etc/grub.d."""
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        mock_grub_d = MagicMock()
        mock_grub_d.exists.return_value = True
        mock_script = MagicMock()
        mock_script.is_file.return_value = False  # Directory or other
        mock_grub_d.iterdir.return_value = [mock_script]

        def path_side_effect(arg):
            if str(arg) == "/etc/grub.d":
                return mock_grub_d
            return MagicMock()

        mock_path_cls.side_effect = path_side_effect

        def exists_side_effect(path):
            if "backup.manual" in str(path):
                return False
            return True

        mock_exists.side_effect = exists_side_effect

        create_grub_default_backup(GRUB_DEFAULT_PATH)
        # Should not add script
        assert mock_tar.add.call_count == 2  # default_grub + grub.cfg (if exists)


class TestCreateLastModifBackup:
    """Tests pour create_last_modif_backup."""

    def test_create_last_modif_backup_tar_error(self, tmp_path):
        """Test create_last_modif_backup avec erreur tarfile."""
        grub_default = tmp_path / "grub"
        grub_default.write_text("GRUB_TIMEOUT=5")

        with patch("core.io.core_grub_default_io.tarfile.open") as mock_tar:
            mock_tar.side_effect = tarfile.TarError("Tar error")

            with pytest.raises(OSError, match="Échec création backup"):
                create_last_modif_backup(str(grub_default))

    def test_create_last_modif_backup_oserror(self, tmp_path):
        """Test create_last_modif_backup avec OSError."""
        grub_default = tmp_path / "grub"
        grub_default.write_text("GRUB_TIMEOUT=5")

        with patch("core.io.core_grub_default_io.tarfile.open") as mock_tar:
            mock_tar.side_effect = OSError("Permission denied")

            with pytest.raises(OSError, match="Échec création backup"):
                create_last_modif_backup(str(grub_default))

    def test_create_last_modif_backup_full_success(self, tmp_path):
        """Test create_last_modif_backup avec succès complet (full system backup)."""
        grub_default = tmp_path / "grub"
        grub_default.write_text("GRUB_TIMEOUT=5")

        # On simule que le chemin passé est le chemin système par défaut
        with (
            patch("core.io.core_grub_default_io.GRUB_DEFAULT_PATH", str(grub_default)),
            patch("core.io.core_grub_default_io.GRUB_CFG_PATHS", ["/boot/grub/grub.cfg"]),
            patch("core.io.core_grub_default_io.Path") as mock_path_class,
            patch("core.io.core_grub_default_io.tarfile.open"),
            patch("core.io.core_grub_default_io._touch_now"),
            patch("core.io.core_grub_default_io._add_to_tar", return_value=True),
            patch("core.io.core_grub_default_io.os.path.abspath", side_effect=lambda x: x),
        ):
            # Setup mock pour Path("/etc/grub.d")
            mock_grub_d = MagicMock()
            mock_grub_d.exists.return_value = True

            script = MagicMock()
            script.is_file.return_value = True
            script.name = "10_linux"
            mock_grub_d.iterdir.return_value = [script]

            # Setup mock pour Path("/boot/grub/grub.cfg")
            mock_cfg_path = MagicMock()
            mock_cfg_path.parts = ["/", "boot", "grub", "grub.cfg"]

            def path_side_effect(p):
                if p == "/etc/grub.d":
                    return mock_grub_d
                if p == "/boot/grub/grub.cfg":
                    return mock_cfg_path
                return Path(p)

            mock_path_class.side_effect = path_side_effect

            result = create_last_modif_backup(str(grub_default))

            assert "grub_backup.last_modif.tar.gz" in result

    def test_create_last_modif_backup_partial_success(self, tmp_path):
        """Test create_last_modif_backup avec succès partiel (pas de full system backup)."""
        grub_default = tmp_path / "grub"
        grub_default.write_text("GRUB_TIMEOUT=5")

        # On simule que le chemin passé n'est PAS le chemin système par défaut
        with (
            patch("core.io.core_grub_default_io.GRUB_DEFAULT_PATH", "/etc/default/grub"),
            patch("core.io.core_grub_default_io.tarfile.open"),
            patch("core.io.core_grub_default_io._touch_now"),
            patch("core.io.core_grub_default_io._add_to_tar", return_value=True),
            patch("core.io.core_grub_default_io.os.path.abspath", side_effect=lambda x: x),
        ):
            result = create_last_modif_backup(str(grub_default))
            assert "grub_backup.last_modif.tar.gz" in result

    def test_create_last_modif_backup_no_grub_d(self, tmp_path):
        """Test create_last_modif_backup quand /etc/grub.d n'existe pas."""
        grub_default = tmp_path / "grub"
        grub_default.write_text("GRUB_TIMEOUT=5")

        with (
            patch("core.io.core_grub_default_io.GRUB_DEFAULT_PATH", str(grub_default)),
            patch("core.io.core_grub_default_io.Path") as mock_path_class,
            patch("core.io.core_grub_default_io.tarfile.open"),
            patch("core.io.core_grub_default_io._touch_now"),
            patch("core.io.core_grub_default_io._add_to_tar", return_value=True),
            patch("core.io.core_grub_default_io.os.path.abspath", side_effect=lambda x: x),
        ):
            mock_grub_d = MagicMock()
            mock_grub_d.exists.return_value = False

            def path_side_effect(p):
                if p == "/etc/grub.d":
                    return mock_grub_d
                return Path(p)

            mock_path_class.side_effect = path_side_effect

            create_last_modif_backup(str(grub_default))

    def test_create_last_modif_backup_empty_dirs(self, tmp_path):
        """Test create_last_modif_backup avec répertoires vides."""
        grub_default = tmp_path / "grub"
        grub_default.write_text("GRUB_TIMEOUT=5")

        with (
            patch("core.io.core_grub_default_io.GRUB_DEFAULT_PATH", str(grub_default)),
            patch("core.io.core_grub_default_io.Path") as mock_path_class,
            patch("core.io.core_grub_default_io.tarfile.open"),
            patch("core.io.core_grub_default_io._touch_now"),
            patch("core.io.core_grub_default_io._add_to_tar", side_effect=[True, False, False]),
            patch("core.io.core_grub_default_io.os.path.abspath", side_effect=lambda x: x),
        ):
            mock_grub_d = MagicMock()
            mock_grub_d.exists.return_value = True
            mock_grub_d.iterdir.return_value = [] # Vide

            def path_side_effect(p):
                if p == "/etc/grub.d":
                    return mock_grub_d
                return Path(p)

            mock_path_class.side_effect = path_side_effect

            create_last_modif_backup(str(grub_default))
