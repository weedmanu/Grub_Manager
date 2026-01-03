"""Tests pour core/grub_menu.py - Extraction des entrées GRUB."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from core.grub_menu import (
    GrubDefaultChoice,
    _extract_menuentry_id,
    _parse_choices,
    get_simulated_os_prober_entries,
    read_grub_default_choices,
)


class TestGrubDefaultChoice:
    """Tests pour GrubDefaultChoice."""

    def test_creation_minimal(self):
        """Vérifie la création minimale d'un choix."""
        choice = GrubDefaultChoice(id="0", title="Ubuntu")
        assert choice.id == "0"
        assert choice.title == "Ubuntu"
        assert choice.menu_id == ""
        assert choice.source == ""

    def test_creation_complete(self):
        """Vérifie la création complète d'un choix."""
        choice = GrubDefaultChoice(
            id="0",
            title="Ubuntu 22.04",
            menu_id="gnulinux-simple",
            source="10_linux"
        )
        assert choice.id == "0"
        assert choice.title == "Ubuntu 22.04"
        assert choice.menu_id == "gnulinux-simple"
        assert choice.source == "10_linux"

    def test_frozen_dataclass(self):
        """Vérifie que GrubDefaultChoice est immuable."""
        choice = GrubDefaultChoice(id="0", title="Test")
        with pytest.raises(AttributeError):
            choice.id = "1"


class TestExtractMenuentryId:
    """Tests pour _extract_menuentry_id."""

    def test_extract_id_with_equals(self):
        """Vérifie l'extraction avec --id=value."""
        line = "menuentry 'Ubuntu' --id=gnulinux-simple {"
        assert _extract_menuentry_id(line) == "gnulinux-simple"

    def test_extract_id_with_space(self):
        """Vérifie l'extraction avec --id value."""
        line = "menuentry 'Ubuntu' --id gnulinux-simple {"
        assert _extract_menuentry_id(line) == "gnulinux-simple"

    def test_extract_id_with_quotes(self):
        """Vérifie l'extraction avec quotes."""
        line = "menuentry 'Ubuntu' --id 'gnulinux-simple' {"
        assert _extract_menuentry_id(line) == "gnulinux-simple"

    def test_extract_id_dynamic(self):
        """Vérifie l'extraction avec $menuentry_id_option."""
        line = "menuentry 'Ubuntu' $menuentry_id_option 'gnulinux-simple-id' {"
        assert _extract_menuentry_id(line) == "gnulinux-simple-id"

    def test_extract_id_no_id(self):
        """Vérifie le cas sans ID."""
        line = "menuentry 'Ubuntu' {"
        assert _extract_menuentry_id(line) == ""


class TestParseChoices:
    """Tests pour _parse_choices."""

    def test_parse_simple_menu(self):
        """Vérifie le parsing d'un menu simple."""
        lines = [
            "### BEGIN /etc/grub.d/10_linux ###",
            "menuentry 'Ubuntu' --id 'ubuntu-1' {",
            "  echo test",
            "}",
        ]

        choices = _parse_choices(lines)
        assert len(choices) == 1
        assert choices[0].id == "0"
        assert choices[0].title == "Ubuntu"
        assert choices[0].menu_id == "ubuntu-1"
        assert choices[0].source == "10_linux"

    def test_parse_multiple_entries(self):
        """Vérifie le parsing de plusieurs entrées."""
        lines = [
            "menuentry 'Ubuntu 1' --id 'ubuntu-1' {",
            "}",
            "menuentry 'Ubuntu 2' --id 'ubuntu-2' {",
            "}",
            "menuentry 'Ubuntu 3' --id 'ubuntu-3' {",
            "}",
        ]

        choices = _parse_choices(lines)
        assert len(choices) == 3
        assert choices[0].id == "0"
        assert choices[1].id == "1"
        assert choices[2].id == "2"

    def test_parse_submenu(self):
        """Vérifie le parsing d'un sous-menu."""
        lines = [
            "submenu 'Advanced options' {",
            "  menuentry 'Recovery mode' --id 'recovery' {",
            "  }",
            "  menuentry 'Older kernel' --id 'old-kernel' {",
            "  }",
            "}",
        ]

        choices = _parse_choices(lines)
        assert len(choices) == 2
        # Les entrées dans le sous-menu ont un ID de type "0>0"
        assert choices[0].id == "0>0"
        assert "Advanced options" in choices[0].title
        assert "Recovery mode" in choices[0].title
        assert choices[1].id == "0>1"
        assert "Advanced options" in choices[1].title
        assert "Older kernel" in choices[1].title

    def test_parse_nested_submenus(self):
        """Vérifie le parsing de sous-menus imbriqués."""
        lines = [
            "submenu 'Level 1' {",
            "  submenu 'Level 2' {",
            "    menuentry 'Deep entry' {",
            "    }",
            "  }",
            "}",
        ]

        choices = _parse_choices(lines)
        assert len(choices) == 1
        assert choices[0].id == "0>0>0"
        assert "Level 1" in choices[0].title
        assert "Level 2" in choices[0].title
        assert "Deep entry" in choices[0].title


class TestReadGrubDefaultChoices:
    """Tests pour read_grub_default_choices."""

    def test_read_from_valid_file(self):
        """Vérifie la lecture depuis un fichier valide."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
            f.write("""
menuentry 'Ubuntu' --id 'ubuntu' {
    echo test
}
menuentry 'Windows' --id 'windows' {
    echo test2
}
""")
            temp_path = f.name

        try:
            choices = read_grub_default_choices(temp_path)
            assert len(choices) == 2
            assert choices[0].title == "Ubuntu"
            assert choices[1].title == "Windows"
        finally:
            Path(temp_path).unlink()

    def test_read_empty_file(self):
        """Vérifie le comportement avec un fichier vide."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
            temp_path = f.name

        try:
            choices = read_grub_default_choices(temp_path)
            assert choices == []
        finally:
            Path(temp_path).unlink()


class TestGetSimulatedOsProberEntries:
    """Tests pour get_simulated_os_prober_entries."""

    def test_requires_root(self):
        """Vérifie que os-prober nécessite root."""
        import os
        if os.geteuid() != 0:
            entries = get_simulated_os_prober_entries()
            assert entries == []

    def test_returns_list(self):
        """Vérifie que la fonction retourne toujours une liste."""
        entries = get_simulated_os_prober_entries()
        assert isinstance(entries, list)


def test_read_grub_default_choices_menu_and_submenu(tmp_path: Path) -> None:
    grub_cfg = tmp_path / "grub.cfg"

    # Minimal-ish grub.cfg excerpt with submenu nesting.
    grub_cfg.write_text(
        """
set default=0

menuentry 'Ubuntu' {
    echo 'boot'
}

submenu 'Advanced options for Ubuntu' {
    menuentry 'Ubuntu, with Linux 6.5.0' {
        echo 'boot'
    }
    menuentry 'Ubuntu, with Linux 6.5.0 (recovery mode)' {
        echo 'boot'
    }
}

menuentry 'UEFI Firmware Settings' {
    fwsetup
}
""".lstrip(),
        encoding="utf-8",
    )

    choices = read_grub_default_choices(str(grub_cfg))

    # Expect 4 menu entries (top-level Ubuntu, 2 under submenu, UEFI).
    assert [c.id for c in choices] == ["0", "1>0", "1>1", "2"]

    assert choices[0].title == "Ubuntu"
    assert choices[1].title.startswith("Advanced options for Ubuntu")
    assert choices[-1].title == "UEFI Firmware Settings"


def test_read_grub_default_choices_missing_file_returns_empty(tmp_path: Path) -> None:
    missing = tmp_path / "nope.cfg"
    assert read_grub_default_choices(str(missing)) == []
