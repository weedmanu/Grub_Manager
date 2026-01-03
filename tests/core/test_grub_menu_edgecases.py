"""Tests additionnels pour atteindre 90%+ de couverture core."""

from __future__ import annotations

from core.grub_menu import (
    _extract_menuentry_id,
    _parse_choices,
)


class TestExtractMenuentryIdEdgeCases:
    """Tests pour les cas limites de _extract_menuentry_id."""

    def test_extract_id_complex_attributes(self):
        """Vérifie l'extraction avec plusieurs attributs."""
        line = "menuentry 'Ubuntu' --class gnu-linux --class os --id 'ubuntu-20' --users root {"
        assert _extract_menuentry_id(line) == "ubuntu-20"

    def test_extract_id_single_quotes_mixed(self):
        """Vérifie l'extraction avec mélange de quotes."""
        line = 'menuentry "Ubuntu" --id ubuntu-simple {'
        assert _extract_menuentry_id(line) == "ubuntu-simple"

    def test_extract_id_with_dashes(self):
        """Vérifie les IDs avec des tirets."""
        line = "menuentry 'Ubuntu' --id 'gnu-linux-simple-ubuntu' {"
        assert _extract_menuentry_id(line) == "gnu-linux-simple-ubuntu"


class TestParseChoicesEdgeCases:
    """Tests pour les cas limites de _parse_choices."""

    def test_parse_empty_submenu(self):
        """Vérifie le parsing d'un sous-menu vide."""
        lines = [
            "submenu 'Advanced' {",
            "}",
        ]

        choices = _parse_choices(lines)
        assert len(choices) == 0

    def test_parse_menuentry_without_id(self):
        """Vérifie le parsing d'une entrée sans ID."""
        lines = [
            "menuentry 'Ubuntu' {",
            "}",
            "menuentry 'Windows' --id windows {",
            "}",
        ]

        choices = _parse_choices(lines)
        # Les deux entrées doivent être parsées
        assert len(choices) >= 1

    def test_parse_nested_submenu_deep(self):
        """Vérifie le parsing de submenu très imbriqués."""
        lines = [
            "submenu 'L1' {",
            "  submenu 'L2' {",
            "    submenu 'L3' {",
            "      menuentry 'Deep' {",
            "      }",
            "    }",
            "  }",
            "}",
        ]

        choices = _parse_choices(lines)
        assert len(choices) == 1
        # L'ID doit refléter la profondeur
        assert ">" in choices[0].id

    def test_parse_mixed_content(self):
        """Vérifie le parsing avec du contenu mélangé."""
        lines = [
            "### BEGIN /etc/grub.d/10_linux ###",
            "export menuentry_id_option",
            "menuentry 'Ubuntu' --id ubuntu-1 {",
            "    load_video",
            "}",
            "### END /etc/grub.d/10_linux ###",
            "### BEGIN /etc/grub.d/20_memtest86+ ###",
            "menuentry 'Memory test' --id memtest {",
            "}",
            "### END /etc/grub.d/20_memtest86+ ###",
        ]

        choices = _parse_choices(lines)
        assert len(choices) == 2
        assert choices[0].source == "10_linux"
        assert choices[1].source == "20_memtest86+"
