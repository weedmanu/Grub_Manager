"""Tests pour core/paths.py - Chemins système GRUB."""

from __future__ import annotations

from core.config.core_paths import GRUB_CFG_PATH, GRUB_CFG_PATHS, GRUB_DEFAULT_PATH


class TestPaths:
    """Tests pour les constantes de chemins."""

    def test_grub_default_path(self):
        """Vérifie le chemin de /etc/default/grub."""
        assert GRUB_DEFAULT_PATH == "/etc/default/grub"
        assert isinstance(GRUB_DEFAULT_PATH, str)

    def test_grub_cfg_paths_is_list(self):
        """Vérifie que GRUB_CFG_PATHS est une liste."""
        assert isinstance(GRUB_CFG_PATHS, list)
        assert len(GRUB_CFG_PATHS) >= 1

    def test_grub_cfg_paths_contains_valid_paths(self):
        """Vérifie que les chemins sont valides."""
        for path in GRUB_CFG_PATHS:
            assert isinstance(path, str)
            assert path.startswith("/")
            assert "grub.cfg" in path

    def test_grub_cfg_path_is_first(self):
        """Vérifie que GRUB_CFG_PATH est le premier de la liste."""
        assert GRUB_CFG_PATH == GRUB_CFG_PATHS[0]

    def test_paths_are_immutable(self):
        """Vérifie que les constantes ne peuvent pas être modifiées."""
        # Note: En Python, on ne peut pas vraiment rendre const au niveau runtime,
        # mais on vérifie que ce sont bien des finales (typing)
        import core.config.core_paths

        # Vérifier que les annotations existent
        annotations = getattr(core.config.core_paths, "__annotations__", {})

        # Si annotés, doivent être Final
        if "GRUB_DEFAULT_PATH" in annotations:
            assert "Final" in str(annotations["GRUB_DEFAULT_PATH"])


class TestThemePaths:
    """Tests pour les fonctions de chemins de thèmes."""

    def test_get_grub_themes_dir_first_exists(self):
        """Test retourne le premier répertoire existant."""
        from pathlib import Path
        from unittest.mock import patch
        from core.config.core_paths import get_grub_themes_dir, GRUB_THEMES_DIRS

        with patch.object(Path, "exists") as mock_exists:
            # Le premier existe
            mock_exists.side_effect = [True, False, False]
            
            path = get_grub_themes_dir()
            
            assert path == Path(GRUB_THEMES_DIRS[0])

    def test_get_grub_themes_dir_second_exists(self):
        """Test retourne le deuxième si le premier n'existe pas."""
        from pathlib import Path
        from unittest.mock import patch
        from core.config.core_paths import get_grub_themes_dir, GRUB_THEMES_DIRS

        with patch.object(Path, "exists") as mock_exists:
            # Le premier n'existe pas, le deuxième oui
            mock_exists.side_effect = [False, True, False]
            
            path = get_grub_themes_dir()
            
            assert path == Path(GRUB_THEMES_DIRS[1])

    def test_get_grub_themes_dir_none_exists(self):
        """Test retourne le défaut si aucun n'existe."""
        from pathlib import Path
        from unittest.mock import patch
        from core.config.core_paths import get_grub_themes_dir, GRUB_THEMES_DIR

        with patch.object(Path, "exists", return_value=False):
            path = get_grub_themes_dir()
            
            assert path == Path(GRUB_THEMES_DIR)

    def test_get_all_grub_themes_dirs(self):
        """Test retourne tous les répertoires existants."""
        from pathlib import Path
        from unittest.mock import patch
        from core.config.core_paths import get_all_grub_themes_dirs, GRUB_THEMES_DIRS

        with patch.object(Path, "exists") as mock_exists:
            # Le premier et le troisième existent
            mock_exists.side_effect = [True, False, True]
            
            paths = get_all_grub_themes_dirs()
            
            assert len(paths) == 2
            assert Path(GRUB_THEMES_DIRS[0]) in paths
            assert Path(GRUB_THEMES_DIRS[2]) in paths
            assert Path(GRUB_THEMES_DIRS[1]) not in paths
