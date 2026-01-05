"""Tests pour le gestionnaire de visibilité des entrées GRUB."""

import json
from unittest.mock import patch

import pytest

from core.core_exceptions import GrubConfigError, GrubValidationError
from core.io.grub_parsing_utils import extract_menuentry_id
from core.managers.core_entry_visibility_manager import (
    apply_hidden_entries_to_grub_cfg,
    find_grub_cfg_path,
    load_hidden_entry_ids,
    save_hidden_entry_ids,
)


class TestLoadHiddenEntryIds:
    """Tests pour load_hidden_entry_ids."""

    def test_load_hidden_entry_ids_success(self, tmp_path):
        """Test chargement réussi des IDs masqués."""
        config_file = tmp_path / "hidden.json"
        data = ["entry1", "entry2", "entry3"]
        config_file.write_text(json.dumps(data))

        result = load_hidden_entry_ids(str(config_file))
        assert result == {"entry1", "entry2", "entry3"}

    def test_load_hidden_entry_ids_file_not_found(self, tmp_path):
        """Test quand le fichier n'existe pas."""
        config_file = tmp_path / "nonexistent.json"
        result = load_hidden_entry_ids(str(config_file))
        assert result == set()

    def test_load_hidden_entry_ids_invalid_json(self, tmp_path):
        """Test avec JSON invalide."""
        config_file = tmp_path / "hidden.json"
        config_file.write_text("invalid json")

        result = load_hidden_entry_ids(str(config_file))
        assert result == set()

    def test_load_hidden_entry_ids_invalid_data_type(self, tmp_path):
        """Test avec type de données invalide."""
        config_file = tmp_path / "hidden.json"
        config_file.write_text('"not a list"')

        result = load_hidden_entry_ids(str(config_file))
        assert result == set()

    def test_load_hidden_entry_ids_empty_list(self, tmp_path):
        """Test avec liste vide."""
        config_file = tmp_path / "hidden.json"
        config_file.write_text("[]")

        result = load_hidden_entry_ids(str(config_file))
        assert result == set()

    def test_load_hidden_entry_ids_with_whitespace(self, tmp_path):
        """Test avec IDs contenant des espaces."""
        config_file = tmp_path / "hidden.json"
        data = ["entry1", "  ", "entry2"]
        config_file.write_text(json.dumps(data))

        result = load_hidden_entry_ids(str(config_file))
        assert result == {"entry1", "entry2"}

    def test_load_hidden_entry_ids_read_error(self, tmp_path):
        """Test avec erreur de lecture."""
        config_file = tmp_path / "hidden.json"
        config_file.write_text("[]")

        with patch("builtins.open", side_effect=OSError):
            result = load_hidden_entry_ids(str(config_file))
            assert result == set()


class TestSaveHiddenEntryIds:
    """Tests pour save_hidden_entry_ids."""

    def test_save_hidden_entry_ids_success(self, tmp_path):
        """Test sauvegarde réussie des IDs masqués."""
        config_file = tmp_path / "hidden.json"
        ids = {"entry2", "entry1", "entry3"}

        save_hidden_entry_ids(ids, str(config_file))

        # Vérifier que le fichier existe et contient les bonnes données
        assert config_file.exists()
        with open(config_file) as f:
            data = json.load(f)
            assert data == ["entry1", "entry2", "entry3"]  # Trié

    def test_save_hidden_entry_ids_creates_directory(self, tmp_path):
        """Test création du répertoire si nécessaire."""
        config_dir = tmp_path / "subdir"
        config_file = config_dir / "hidden.json"
        ids = {"entry1"}

        save_hidden_entry_ids(ids, str(config_file))
        assert config_file.exists()

    def test_save_hidden_entry_ids_write_error(self, tmp_path):
        """Test avec erreur d'écriture."""
        config_file = tmp_path / "hidden.json"
        ids = {"entry1"}

        with patch("builtins.open", side_effect=OSError):
            # Ne devrait pas lever d'exception
            save_hidden_entry_ids(ids, str(config_file))


class TestExtractMenuentryId:
    """Tests pour extract_menuentry_id."""

    def test_extract_menuentry_id_dash_id_equals(self):
        """Test extraction ID avec --id=."""
        line = 'menuentry "Ubuntu" --id=ubuntu-entry {'
        result = extract_menuentry_id(line)
        assert result == "ubuntu-entry"

    def test_extract_menuentry_id_dash_id_space(self):
        """Test extraction ID avec --id suivi d'espace."""
        line = 'menuentry "Ubuntu" --id ubuntu-entry {'
        result = extract_menuentry_id(line)
        assert result == "ubuntu-entry"

    def test_extract_menuentry_id_dash_id_quotes(self):
        """Test extraction ID avec --id et guillemets."""
        line = 'menuentry "Ubuntu" --id "ubuntu-entry" {'
        result = extract_menuentry_id(line)
        assert result == "ubuntu-entry"

    def test_extract_menuentry_id_menuentry_option(self):
        """Test extraction ID avec $menuentry_id_option."""
        line = 'menuentry "Ubuntu" ${menuentry_id_option} "ubuntu-entry" {'
        result = extract_menuentry_id(line)
        assert result == "ubuntu-entry"

    def test_extract_menuentry_id_no_id(self):
        """Test sans ID."""
        line = 'menuentry "Ubuntu" {'
        result = extract_menuentry_id(line)
        assert result == ""


class TestCandidateGrubCfgPaths:
    """Tests pour discover_grub_cfg_paths."""

    @patch("core.config.core_paths.glob")
    def test_candidate_grub_cfg_paths(self, mock_glob):
        """Test génération des chemins candidats avec doublons."""
        # On simule des doublons entre GRUB_CFG_PATHS et glob
        with patch("core.config.core_paths.GRUB_CFG_PATHS", ["/boot/grub/grub.cfg", "/boot/grub/grub.cfg"]):
            mock_glob.return_value = ["/boot/grub/grub.cfg", "/boot/efi/EFI/ubuntu/grub.cfg"]

            from core.config.core_paths import discover_grub_cfg_paths

            result = discover_grub_cfg_paths()

            assert result.count("/boot/grub/grub.cfg") == 1
            assert "/boot/efi/EFI/ubuntu/grub.cfg" in result


class TestFindGrubCfgPath:
    """Tests pour find_grub_cfg_path."""

    @patch("core.managers.core_entry_visibility_manager.discover_grub_cfg_paths")
    @patch("os.path.exists")
    def test_find_grub_cfg_path_found(self, mock_exists, mock_candidates):
        """Test quand un chemin est trouvé."""
        mock_candidates.return_value = ["/path1/grub.cfg", "/path2/grub.cfg"]
        mock_exists.side_effect = [False, True]

        result = find_grub_cfg_path()
        assert result == "/path2/grub.cfg"

    @patch("core.managers.core_entry_visibility_manager.discover_grub_cfg_paths")
    @patch("os.path.exists")
    def test_find_grub_cfg_path_not_found(self, mock_exists, mock_candidates):
        """Test quand aucun chemin n'est trouvé."""
        mock_candidates.return_value = ["/path1/grub.cfg", "/path2/grub.cfg"]
        mock_exists.return_value = False

        result = find_grub_cfg_path()
        assert result is None


class TestApplyHiddenEntriesToGrubCfg:
    """Tests pour apply_hidden_entries_to_grub_cfg."""

    def test_apply_hidden_entries_empty_set(self, tmp_path):
        """Test avec ensemble vide d'IDs masqués."""
        config_file = tmp_path / "grub.cfg"
        config_file.write_text("# GRUB config")

        result_path, count = apply_hidden_entries_to_grub_cfg(set(), grub_cfg_path=str(config_file))
        assert result_path == str(config_file)
        assert count == 0

    def test_apply_hidden_entries_no_grub_cfg_path(self, tmp_path):
        """Test sans chemin grub.cfg spécifié."""
        config_file = tmp_path / "grub.cfg"
        config_content = """menuentry "Ubuntu" --id ubuntu {
}
menuentry "Windows" --id windows {
}
"""
        config_file.write_text(config_content)
        hidden_ids = {"ubuntu"}

        with patch("core.managers.core_entry_visibility_manager.find_grub_cfg_path") as mock_find:
            mock_find.return_value = str(config_file)

            result_path, count = apply_hidden_entries_to_grub_cfg(hidden_ids)
            assert result_path == str(config_file)
            assert count == 1

    def test_apply_hidden_entries_grub_cfg_not_found(self):
        """Test quand grub.cfg n'est pas trouvé."""
        hidden_ids = {"entry1"}

        with patch("core.managers.core_entry_visibility_manager.find_grub_cfg_path") as mock_find:
            mock_find.return_value = None

            with pytest.raises(GrubConfigError):
                apply_hidden_entries_to_grub_cfg(hidden_ids)

    def test_apply_hidden_entries_would_hide_all(self, tmp_path):
        """Test protection contre masquage de toutes les entrées."""
        config_file = tmp_path / "grub.cfg"
        config_content = """menuentry "Ubuntu" --id ubuntu {
}
menuentry "Windows" --id windows {
}
"""
        config_file.write_text(config_content)

        # Tenter de masquer les 2 entrées
        hidden_ids = {"ubuntu", "windows"}

        with pytest.raises(GrubValidationError, match=r"PROTECTION.*Au moins 1 entrée"):
            apply_hidden_entries_to_grub_cfg(hidden_ids, grub_cfg_path=str(config_file))

    def test_apply_hidden_entries_success(self, tmp_path):
        """Test masquage réussi."""
        config_file = tmp_path / "grub.cfg"
        config_content = """menuentry "Ubuntu" --id ubuntu {
echo "Loading Ubuntu"
}
menuentry "Windows" --id windows {
echo "Loading Windows"
}
menuentry "Debian" --id debian {
echo "Loading Debian"
}
"""
        config_file.write_text(config_content)

        hidden_ids = {"ubuntu"}  # Il restera 2 entrées (Windows, Debian)

        result_path, count = apply_hidden_entries_to_grub_cfg(hidden_ids, grub_cfg_path=str(config_file))

        assert result_path == str(config_file)
        assert count == 1

        # Vérifier le contenu modifié
        with open(config_file) as f:
            content = f.read()
            assert "### GRUB_MANAGER_HIDDEN id=ubuntu title=Ubuntu" in content
            assert 'menuentry "Ubuntu" --id ubuntu {' not in content
            assert 'menuentry "Windows" --id windows {' in content

    def test_apply_hidden_entries_backup_creation_failure(self, tmp_path):
        """Test avec échec de création du backup."""
        config_file = tmp_path / "grub.cfg"
        config_content = """menuentry "Ubuntu" --id ubuntu {
}
menuentry "Windows" --id windows {
}
"""
        config_file.write_text(config_content)

        hidden_ids = {"ubuntu"}

        with patch("shutil.copy2", side_effect=OSError("Permission denied")):
            # Ne devrait pas lever d'exception malgré l'échec du backup
            result_path, count = apply_hidden_entries_to_grub_cfg(hidden_ids, grub_cfg_path=str(config_file))
            assert result_path == str(config_file)
            assert count == 1

    def test_apply_hidden_entries_warning_remaining_one(self, tmp_path):
        """Test l'avertissement quand il ne reste qu'une seule entrée (remaining < 2)."""
        config_file = tmp_path / "grub.cfg"
        config_content = """menuentry "Ubuntu" --id ubuntu {
}
menuentry "Windows" --id windows {
}
"""
        config_file.write_text(config_content)

        hidden_ids = {"ubuntu"}  # Il restera Windows (1 seule entrée)

        result_path, count = apply_hidden_entries_to_grub_cfg(hidden_ids, grub_cfg_path=str(config_file))
        assert count == 1
        assert result_path == str(config_file)

    def test_apply_hidden_entries_no_changes_needed(self, tmp_path):
        """Test quand aucune modification n'est nécessaire."""
        config_file = tmp_path / "grub.cfg"
        config_content = """menuentry "Ubuntu" --id ubuntu {
}
"""
        config_file.write_text(config_content)

        hidden_ids = {"nonexistent"}

        result_path, count = apply_hidden_entries_to_grub_cfg(hidden_ids, grub_cfg_path=str(config_file))

        assert result_path == str(config_file)
        assert count == 0

        # Vérifier que le fichier n'a pas changé
        with open(config_file) as f:
            assert f.read() == config_content
