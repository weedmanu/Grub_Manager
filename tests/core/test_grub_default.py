from __future__ import annotations

from pathlib import Path

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
    base = tmp_path / "grub"
    base.write_text("GRUB_TIMEOUT=5\nGRUB_DEFAULT=0\n", encoding="utf-8")

    initial = ensure_initial_grub_default_backup(str(base))
    assert initial is not None
    initial_path = Path(initial)
    assert initial_path.exists()
    assert initial_path.read_text(encoding="utf-8") == base.read_text(encoding="utf-8")

    # Modifie le fichier source, puis réappelle: le backup initial ne doit pas changer.
    base.write_text("MODIFIED", encoding="utf-8")
    initial2 = ensure_initial_grub_default_backup(str(base))
    assert initial2 == initial
    assert Path(initial2).read_text(encoding="utf-8").startswith("GRUB_TIMEOUT=5")


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

    with patch("shutil.copy2", side_effect=OSError("Permission denied")):
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
    base = tmp_path / "grub"
    fallback = tmp_path / "grub.backup.current"
    fallback.write_text("FALLBACK CONTENT")

    # base n'existe pas, mais fallback existe
    created = create_grub_default_backup(str(base))
    assert Path(created).read_text() == "FALLBACK CONTENT"


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
    base = tmp_path / "grub"
    base.write_text("GRUB_TIMEOUT=5\n", encoding="utf-8")

    assert list_grub_default_backups(str(base)) == []

    created = create_grub_default_backup(str(base))
    created_path = Path(created)
    assert created_path.exists()
    assert created_path.read_text(encoding="utf-8") == "GRUB_TIMEOUT=5\n"

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
