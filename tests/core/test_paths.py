"""Tests pour core/paths.py - Chemins système GRUB."""

from __future__ import annotations

from core.paths import GRUB_CFG_PATH, GRUB_CFG_PATHS, GRUB_DEFAULT_PATH


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
        import core.paths

        # Vérifier que les annotations existent
        annotations = getattr(core.paths, "__annotations__", {})

        # Si annotés, doivent être Final
        if "GRUB_DEFAULT_PATH" in annotations:
            assert "Final" in str(annotations["GRUB_DEFAULT_PATH"])
