"""Tests pour core/io/core_grub_menu_parser.py - Extraction des entrées GRUB."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.io.core_grub_menu_parser import (
    GrubDefaultChoice,
    _candidate_grub_cfg_paths,
    _discover_efi_grub_cfg_paths,
    _extract_menuentry_id,
    _iter_readable_grub_cfg_lines,
    _parse_choices,
    get_simulated_os_prober_entries,
    read_grub_default_choices,
    read_grub_default_choices_with_source,
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
        choice = GrubDefaultChoice(id="0", title="Ubuntu 22.04", menu_id="gnulinux-simple", source="10_linux")
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

    def test_parse_submenu_closing_on_same_line(self):
        """Vérifie le parsing d'un sous-menu qui se ferme sur la même ligne ou immédiatement."""
        lines = [
            "submenu 'Empty' { }",
            "menuentry 'After' { }",
        ]
        choices = _parse_choices(lines)
        assert len(choices) == 1
        assert choices[0].id == "1"  # Index 0 était le submenu, index 1 est le menuentry

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
        assert len(choices) == 2

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
        assert choices[0].id == "0>0>0>0"

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


class TestReadGrubDefaultChoices:
    """Tests pour read_grub_default_choices."""

    def test_read_from_valid_file(self):
        """Vérifie la lecture depuis un fichier valide."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
            f.write(
                """
menuentry 'Ubuntu' --id 'ubuntu' {
    echo test
}
menuentry 'Windows' --id 'windows' {
    echo test2
}
"""
            )
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
            temp_path = f.name

        try:
            choices = read_grub_default_choices(temp_path)
            assert choices == []
        finally:
            Path(temp_path).unlink()

    def test_read_missing_file_returns_empty(self, tmp_path):
        """Vérifie que la lecture d'un fichier manquant retourne une liste vide."""
        missing = tmp_path / "nope.cfg"
        assert read_grub_default_choices(str(missing)) == []

    def test_read_menu_and_submenu(self, tmp_path):
        """Test complet avec menu et submenu."""
        grub_cfg = tmp_path / "grub.cfg"
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
        assert [c.id for c in choices] == ["0", "1>0", "1>1", "2"]
        assert choices[0].title == "Ubuntu"
        assert "Advanced options" in choices[1].title
        assert choices[-1].title == "UEFI Firmware Settings"


class TestGetSimulatedOsProberEntries:
    """Tests pour get_simulated_os_prober_entries."""

    def test_requires_root(self):
        """Vérifie que os-prober nécessite root."""
        with patch("os.geteuid", return_value=1000):
            entries = get_simulated_os_prober_entries()
            assert entries == []

    def test_os_prober_not_found(self):
        """Vérifie quand os-prober n'est pas installé."""
        with patch("os.geteuid", return_value=0):
            with patch("shutil.which", return_value=None):
                entries = get_simulated_os_prober_entries()
                assert entries == []

    def test_os_prober_success(self):
        """Vérifie le succès d'os-prober."""
        mock_stdout = "/dev/sda1:Windows 10:Windows:chain\nINVALID_LINE\n/dev/sdb1:Debian:Linux:linux"
        with patch("os.geteuid", return_value=0):
            with patch("shutil.which", return_value="/usr/bin/os-prober"):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0, stdout=mock_stdout)
                    entries = get_simulated_os_prober_entries()
                    assert len(entries) == 2
                    assert entries[0].title == "Windows 10 (détecté)"
                    assert "osprober-simulated-/dev/sda1" in entries[0].id
                    assert entries[1].title == "Debian (détecté)"

    def test_os_prober_empty_output(self):
        """Vérifie quand os-prober retourne une sortie vide."""
        with patch("os.geteuid", return_value=0):
            with patch("shutil.which", return_value="/usr/bin/os-prober"):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0, stdout="")
                    entries = get_simulated_os_prober_entries()
                    assert entries == []

    def test_os_prober_failure(self):
        """Vérifie l'échec d'os-prober."""
        with patch("os.geteuid", return_value=0):
            with patch("shutil.which", return_value="/usr/bin/os-prober"):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=1, stdout="")
                    entries = get_simulated_os_prober_entries()
                    assert entries == []

    def test_os_prober_exception(self):
        """Vérifie la gestion d'exception dans os-prober."""
        with patch("os.geteuid", return_value=0):
            with patch("shutil.which", return_value="/usr/bin/os-prober"):
                with patch("subprocess.run", side_effect=Exception("Crash")):
                    entries = get_simulated_os_prober_entries()
                    assert entries == []


class TestGrubCfgDiscovery:
    """Tests pour la découverte de grub.cfg."""

    def test_discover_efi_grub_cfg_paths(self):
        """Test la découverte des chemins EFI."""
        with patch("core.io.core_grub_menu_parser.glob", return_value=["/boot/efi/EFI/ubuntu/grub.cfg"]):
            paths = _discover_efi_grub_cfg_paths()
            assert "/boot/efi/EFI/ubuntu/grub.cfg" in paths

    def test_candidate_grub_cfg_paths_default(self):
        """Test les candidats par défaut avec doublons."""
        with patch("core.io.core_grub_menu_parser.GRUB_CFG_PATHS", ["/boot/grub/grub.cfg", "/boot/grub/grub.cfg"]):
            with patch(
                "core.io.core_grub_menu_parser._discover_efi_grub_cfg_paths",
                return_value=["/boot/grub/grub.cfg", "/efi/grub.cfg"],
            ):
                paths = _candidate_grub_cfg_paths("/boot/grub/grub.cfg")
                assert "/boot/grub/grub.cfg" in paths
                assert "/efi/grub.cfg" in paths
                assert len(paths) == 2

    def test_candidate_grub_cfg_paths_custom(self):
        """Test avec un chemin personnalisé."""
        paths = _candidate_grub_cfg_paths("/tmp/grub.cfg")
        assert paths == ["/tmp/grub.cfg"]


class TestIterReadableGrubCfgLines:
    """Tests pour _iter_readable_grub_cfg_lines."""

    def test_iter_no_candidates(self):
        """Test quand aucun candidat n'existe."""
        with patch("os.path.exists", return_value=False):
            results = list(_iter_readable_grub_cfg_lines(["/none"]))
            assert results == []

    def test_iter_mixed_existence(self, tmp_path):
        """Test avec des candidats existants et non existants."""
        f = tmp_path / "exists.cfg"
        f.write_text("content")

        results = list(_iter_readable_grub_cfg_lines([str(f), "/nonexistent"]))
        assert len(results) == 1
        assert results[0][0] == str(f)

    def test_iter_multiple_candidates(self, tmp_path):
        """Test avec plusieurs candidats dont un illisible."""
        f1 = tmp_path / "grub1.cfg"
        f1.write_text("content1")
        f2 = tmp_path / "grub2.cfg"
        f2.write_text("content2")

        with patch("os.path.exists", side_effect=[True, True]):
            with patch("builtins.open") as mock_open:
                mock_open.side_effect = [
                    OSError("Error"),
                    MagicMock(__enter__=lambda x: MagicMock(read=lambda: "line1")),
                ]
                results = list(_iter_readable_grub_cfg_lines([str(f1), str(f2)]))
                assert len(results) == 1
                assert results[0][0] == str(f2)

    def test_iter_success(self, tmp_path):
        """Test lecture réussie."""
        f = tmp_path / "grub.cfg"
        f.write_text("line1\nline2")

        results = list(_iter_readable_grub_cfg_lines([str(f)]))
        assert len(results) == 1
        assert results[0][0] == str(f)
        assert results[0][1] == ["line1", "line2"]


class TestReadGrubDefaultChoicesWithSource:
    """Tests pour read_grub_default_choices_with_source."""

    def test_read_success_different_path(self, tmp_path):
        """Test succès de lecture avec un chemin différent du demandé."""
        f_requested = tmp_path / "requested.cfg"
        f_actual = tmp_path / "actual.cfg"
        f_actual.write_text("menuentry 'OS' { }")

        with patch(
            "core.io.core_grub_menu_parser._candidate_grub_cfg_paths", return_value=[str(f_requested), str(f_actual)]
        ):
            choices, used_path = read_grub_default_choices_with_source(str(f_requested))
            assert len(choices) == 1
            assert used_path == str(f_actual)

    def test_read_empty_different_path(self, tmp_path):
        """Test fichier vide avec un chemin différent du demandé."""
        f_requested = tmp_path / "requested.cfg"
        f_actual = tmp_path / "actual.cfg"
        f_actual.write_text("# Empty")

        with patch(
            "core.io.core_grub_menu_parser._candidate_grub_cfg_paths", return_value=[str(f_requested), str(f_actual)]
        ):
            choices, used_path = read_grub_default_choices_with_source(str(f_requested))
            assert choices == []
            assert used_path == str(f_actual)

    def test_read_multiple_empty_candidates(self, tmp_path):
        """Test avec plusieurs candidats vides."""
        f1 = tmp_path / "empty1.cfg"
        f1.write_text("# Empty 1")
        f2 = tmp_path / "empty2.cfg"
        f2.write_text("# Empty 2")

        with patch("core.io.core_grub_menu_parser._candidate_grub_cfg_paths", return_value=[str(f1), str(f2)]):
            choices, used_path = read_grub_default_choices_with_source(str(f1))
            assert choices == []
            assert used_path == str(f1)

    def test_read_failure_all_candidates(self):
        """Test échec total."""
        with patch("core.io.core_grub_menu_parser._iter_readable_grub_cfg_lines", return_value=[]):
            choices, used_path = read_grub_default_choices_with_source("/none")
            assert choices == []
            assert used_path is None
