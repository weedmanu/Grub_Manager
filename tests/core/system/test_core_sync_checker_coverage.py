"""Tests de couverture pour core/system/core_sync_checker.py."""

from pathlib import Path
from unittest.mock import patch
from core.system.core_sync_checker import check_grub_sync

def test_sync_checker_stat_exception(tmp_path: Path, monkeypatch) -> None:
    """Vérifie le comportement en cas d'exception lors du stat()."""
    grub_default = tmp_path / "grub"
    grub_cfg = tmp_path / "grub.cfg"
    
    grub_default.write_text("content")
    grub_cfg.write_text("content")
    
    monkeypatch.setattr("core.system.core_sync_checker.GRUB_DEFAULT_PATH", str(grub_default))
    monkeypatch.setattr("core.system.core_sync_checker.GRUB_CFG_PATH", str(grub_cfg))
    
    # On patche exists pour qu'il passe, puis stat pour qu'il échoue
    with patch("core.system.core_sync_checker.Path.exists", return_value=True):
        with patch("core.system.core_sync_checker.Path.stat", side_effect=OSError("Permission denied")):
            status = check_grub_sync()
            
            assert status.in_sync is False
            assert "erreur" in status.message.lower()
            assert "permission denied" in status.message.lower()
