"""Tests spécifiques pour combler les lacunes de couverture dans le noyau."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.io.core_grub_default_io import (
    create_grub_default_backup, 
    ensure_initial_grub_default_backup,
    create_last_modif_backup
)


class TestCoreGrubDefaultIOCoverage:
    """Tests de couverture pour core_grub_default_io.py."""

    def test_ensure_initial_backup_tar_filter_exception(self):
        """Test l'exception OSError dans _tar_filter."""
        with patch("tarfile.open") as mock_tar_open:
            mock_tar = MagicMock()
            mock_tar_open.return_value.__enter__.return_value = mock_tar

            def side_effect_add(tar, path, arcname, filter_func):
                tarinfo = MagicMock()
                tarinfo.name = "/etc/default/grub"

                # Lever une exception dès os.path.exists pour être sûr d'aller dans le except
                with patch("os.path.exists", side_effect=OSError("Disk error")):
                    result = filter_func(tarinfo)
                    assert result is None

            with patch("core.io.core_grub_default_io._add_to_tar", side_effect=side_effect_add):
                ensure_initial_grub_default_backup()

    def test_create_backup_tar_filter_manual_exception(self):
        """Test l'exception OSError dans _tar_filter_manual."""
        with patch("tarfile.open") as mock_tar_open:
            mock_tar = MagicMock()
            mock_tar_open.return_value.__enter__.return_value = mock_tar

            def side_effect_add(tar, path, arcname, filter_func):
                tarinfo = MagicMock()
                tarinfo.name = "/etc/default/grub"

                # On doit mocker os.path.exists et os.access ICI pour le filtre
                # car le filtre est appelé à l'intérieur de _add_to_tar
                with patch("os.path.exists", return_value=True):
                    with patch("os.access", side_effect=OSError("Access denied")):
                        result = filter_func(tarinfo)
                        assert result is None

            # Mocker os.path.isfile pour que _safe_is_file retourne True
            # Mocker os.path.exists pour que _safe_exists retourne False (pas de conflit de nom)
            with patch("os.path.isfile", return_value=True):
                with patch("os.path.exists", return_value=False):
                    with patch("core.io.core_grub_default_io._add_to_tar", side_effect=side_effect_add):
                        create_grub_default_backup("/tmp/dummy_grub")

    def test_create_last_modif_backup_with_directory_in_grub_d(self, tmp_path):
        """Couvre la branche 229->228 (script.is_file() est False)."""
        grub_default = tmp_path / "grub"
        grub_default.write_text("GRUB_TIMEOUT=5")

        grub_d = tmp_path / "grub.d"
        grub_d.mkdir()
        (grub_d / "subdir").mkdir()  # Ceci n'est pas un fichier

        with patch("core.io.core_grub_default_io.GRUB_DEFAULT_PATH", str(grub_default)), \
             patch("core.io.core_grub_default_io.Path", side_effect=lambda p: Path(str(p).replace("/etc/grub.d", str(grub_d)))), \
             patch("core.io.core_grub_default_io.GRUB_CFG_PATHS", []):

            # On force full_system_backup à True en faisant correspondre les chemins
            with patch("os.path.abspath", side_effect=lambda p: str(p)):
                res = create_last_modif_backup(str(grub_default))
                assert res is not None
                assert os.path.exists(res)
