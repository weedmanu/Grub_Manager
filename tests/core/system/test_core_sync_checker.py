"""Tests pour la vérification de synchronisation GRUB."""

from pathlib import Path
from time import sleep
from unittest.mock import patch

from core.system.core_sync_checker import check_grub_sync


def test_sync_checker_detects_desync(tmp_path: Path, monkeypatch) -> None:
    """Vérifie que le checker détecte une désynchronisation."""
    grub_default = tmp_path / "grub"
    grub_cfg = tmp_path / "grub.cfg"

    # Créer grub_default en premier
    grub_default.write_text("GRUB_TIMEOUT=5\n", encoding="utf-8")
    sleep(0.01)  # Petit délai pour garantir des mtimes différents

    # Créer grub_cfg après (plus récent)
    grub_cfg.write_text("menuentry 'Test' {}\n", encoding="utf-8")
    sleep(0.01)

    # Modifier grub_default (devient plus récent que grub_cfg)
    grub_default.write_text("GRUB_TIMEOUT=10\n", encoding="utf-8")

    # Patcher les chemins
    monkeypatch.setattr("core.system.core_sync_checker.GRUB_DEFAULT_PATH", str(grub_default))
    monkeypatch.setattr("core.system.core_sync_checker.GRUB_CFG_PATH", str(grub_cfg))

    status = check_grub_sync()

    assert status.in_sync is False
    assert status.grub_default_exists is True
    assert status.grub_cfg_exists is True
    assert "désynchronisée" in status.message.lower() or "update-grub" in status.message.lower()


def test_sync_checker_detects_sync(tmp_path: Path, monkeypatch) -> None:
    """Vérifie que le checker détecte une synchronisation."""
    grub_default = tmp_path / "grub"
    grub_cfg = tmp_path / "grub.cfg"

    # Créer grub_default en premier
    grub_default.write_text("GRUB_TIMEOUT=5\n", encoding="utf-8")
    sleep(0.01)

    # Créer grub_cfg après (plus récent - normal)
    grub_cfg.write_text("menuentry 'Test' {}\n", encoding="utf-8")

    # Patcher les chemins
    monkeypatch.setattr("core.system.core_sync_checker.GRUB_DEFAULT_PATH", str(grub_default))
    monkeypatch.setattr("core.system.core_sync_checker.GRUB_CFG_PATH", str(grub_cfg))

    status = check_grub_sync()

    assert status.in_sync is True
    assert status.grub_default_exists is True
    assert status.grub_cfg_exists is True
    assert "synchronisée" in status.message.lower()


def test_sync_checker_missing_grub_default(tmp_path: Path, monkeypatch) -> None:
    """Vérifie le comportement quand /etc/default/grub n'existe pas."""
    grub_default = tmp_path / "grub"
    grub_cfg = tmp_path / "grub.cfg"

    # Créer seulement grub_cfg
    grub_cfg.write_text("menuentry 'Test' {}\n", encoding="utf-8")

    # Patcher les chemins
    monkeypatch.setattr("core.system.core_sync_checker.GRUB_DEFAULT_PATH", str(grub_default))
    monkeypatch.setattr("core.system.core_sync_checker.GRUB_CFG_PATH", str(grub_cfg))

    status = check_grub_sync()

    assert status.in_sync is False
    assert status.grub_default_exists is False
    assert status.grub_cfg_exists is True
    assert "introuvable" in status.message.lower()


def test_sync_checker_missing_grub_cfg(tmp_path: Path, monkeypatch) -> None:
    """Vérifie le comportement quand /boot/grub/grub.cfg n'existe pas."""
    grub_default = tmp_path / "grub"
    grub_cfg = tmp_path / "grub.cfg"

    # Créer seulement grub_default
    grub_default.write_text("GRUB_TIMEOUT=5\n", encoding="utf-8")

    # Patcher les chemins
    monkeypatch.setattr("core.system.core_sync_checker.GRUB_DEFAULT_PATH", str(grub_default))
    monkeypatch.setattr("core.system.core_sync_checker.GRUB_CFG_PATH", str(grub_cfg))

    status = check_grub_sync()

    assert status.in_sync is False
    assert status.grub_default_exists is True
    assert status.grub_cfg_exists is False
    assert "update-grub" in status.message.lower()


def test_sync_checker_os_error(tmp_path: Path, monkeypatch) -> None:
    """Vérifie le comportement en cas d'erreur système (OSError)."""
    grub_default = tmp_path / "grub"
    grub_cfg = tmp_path / "grub.cfg"

    grub_default.write_text("test")
    grub_cfg.write_text("test")

    # Patcher les chemins
    monkeypatch.setattr("core.system.core_sync_checker.GRUB_DEFAULT_PATH", str(grub_default))
    monkeypatch.setattr("core.system.core_sync_checker.GRUB_CFG_PATH", str(grub_cfg))

    from unittest.mock import MagicMock

    # On simule que exists() fonctionne (renvoie True) mais stat() échoue ensuite
    # exists() appelle stat() en interne.
    # 1. exists(grub_default) -> appelle stat -> success
    # 2. exists(grub_cfg) -> appelle stat -> success
    # 3. grub_default_path.stat() -> OSError

    mock_stat = MagicMock()
    mock_stat.side_effect = [
        MagicMock(st_mtime=1000),  # pour exists(grub_default)
        MagicMock(st_mtime=2000),  # pour exists(grub_cfg)
        OSError("Permission denied"),  # pour le stat() explicite
    ]

    with patch("pathlib.Path.stat", mock_stat):
        status = check_grub_sync()
        assert status.in_sync is False
        assert "Erreur de vérification" in status.message
