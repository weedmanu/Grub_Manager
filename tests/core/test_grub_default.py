from __future__ import annotations

from pathlib import Path

import pytest

from core.grub_default import (
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
    base.write_text("GRUB_TIMEOUT=10\nGRUB_DEFAULT=0\n", encoding="utf-8")
    initial2 = ensure_initial_grub_default_backup(str(base))
    assert initial2 == initial
    assert initial_path.read_text(encoding="utf-8") == "GRUB_TIMEOUT=5\nGRUB_DEFAULT=0\n"


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
