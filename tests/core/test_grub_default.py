from __future__ import annotations

import os
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.io.core_grub_default_io import (
    create_grub_default_backup,
    delete_grub_default_backup,
    ensure_initial_grub_default_backup,
    format_grub_default,
    list_grub_default_backups,
    parse_grub_default,
    read_grub_default,
    write_grub_default,
)


def test_parse_grub_default_basic() -> None:
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
    p = tmp_path / "missing"
    with pytest.raises(FileNotFoundError):
        # shutil.copy2 should raise if source doesn't exist.
        write_grub_default({"GRUB_TIMEOUT": "5"}, str(p))


def test_read_grub_default_restores_from_backup_current(tmp_path: Path) -> None:
    base = tmp_path / "grub"
    backup_current = tmp_path / "grub.backup.current"

    backup_current.write_text("GRUB_TIMEOUT=7\nGRUB_DEFAULT=0\n", encoding="utf-8")
    assert not base.exists()

    cfg = read_grub_default(str(base))
    assert cfg["GRUB_TIMEOUT"] == "7"
    # Best-effort restore should recreate the canonical file.
    assert base.exists()


def test_ensure_initial_grub_default_backup_creates_once(tmp_path: Path) -> None:
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
        content = tar.extractfile("default_grub").read().decode("utf-8")
        assert content == base.read_text(encoding="utf-8")

    # Modifie le fichier source, puis réappelle: le backup initial ne doit pas changer.
    base.write_text("MODIFIED", encoding="utf-8")
    initial2 = ensure_initial_grub_default_backup(str(base))
    assert initial2 == initial

    # Vérifier que le contenu du tar.gz n'a pas changé
    with tarfile.open(initial_path, "r:gz") as tar:
        content = tar.extractfile("default_grub").read().decode("utf-8")
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
    with pytest.raises(FileNotFoundError):
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
        content = tar.extractfile("default_grub").read().decode("utf-8")
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
        with pytest.raises(OSError):
            write_grub_default({}, str(base))

    # Cas 2: Succès du backup, échec de l'écriture
    with patch("shutil.copy2", return_value=None):
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            with pytest.raises(OSError):
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
        content = tar.extractfile("default_grub").read().decode("utf-8")
        assert content == "GRUB_TIMEOUT=5\n"

    backups = list_grub_default_backups(str(base))
    assert created in backups

    delete_grub_default_backup(created, path=str(base))
    assert not created_path.exists()


def test_manual_backup_rotation_keeps_3(tmp_path: Path) -> None:
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
    backup_path = str(tmp_path / "missing_or_bad.tar.gz")

    with (
        patch("core.io.core_grub_default_io.os.path.exists", return_value=True),
        patch("core.io.core_grub_default_io.tarfile.open", side_effect=tarfile.ReadError("bad")),
    ):
        from core.io.core_grub_default_io import restore_grub_default_backup

        with pytest.raises(OSError, match="Échec de la restauration"):
            restore_grub_default_backup(backup_path, target_path=str(tmp_path / "grub"))
