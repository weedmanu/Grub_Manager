"""Tests pour le gestionnaire de thème actif."""

import json
from unittest.mock import MagicMock, mock_open, patch

import pytest

from core.theme.core_active_theme_manager import ActiveThemeManager
from core.models.core_theme_models import GrubTheme, create_custom_theme


class TestActiveThemeManager:
    """Tests pour la classe ActiveThemeManager."""

    @pytest.fixture
    def manager(self):
        """Fixture pour créer une instance de ActiveThemeManager."""
        return ActiveThemeManager()

    @pytest.fixture
    def mock_theme(self):
        """Fixture pour un thème mocké."""
        theme = MagicMock(spec=GrubTheme)
        theme.name = "Test Theme"
        return theme

    def test_initialization(self, manager):
        """Test l'initialisation du gestionnaire."""
        assert manager.active_theme is None
        assert manager._cache_timestamp == 0.0

    @patch("core.theme.core_active_theme_manager.ActiveThemeManager.ACTIVE_THEME_FILE")
    def test_load_active_theme_no_file(self, mock_file, manager):
        """Test le chargement quand le fichier n'existe pas."""
        mock_file.exists.return_value = False

        # Mock _create_default_theme et save_active_theme
        manager._create_default_theme = MagicMock(return_value="default_theme")
        manager.save_active_theme = MagicMock()

        theme = manager.load_active_theme()

        assert theme == "default_theme"
        manager._create_default_theme.assert_called_once()
        manager.save_active_theme.assert_called_once()

    @patch("core.theme.core_active_theme_manager.ActiveThemeManager.ACTIVE_THEME_FILE")
    def test_load_active_theme_from_cache(self, mock_file, manager, mock_theme):
        """Test le chargement depuis le cache."""
        manager.active_theme = mock_theme
        manager._is_cache_valid = MagicMock(return_value=True)

        theme = manager.load_active_theme()

        assert theme == mock_theme
        mock_file.exists.assert_not_called()  # Ne devrait pas vérifier le disque

    @patch("core.theme.core_active_theme_manager.ActiveThemeManager.ACTIVE_THEME_FILE")
    def test_load_active_theme_success(self, mock_file, manager):
        """Test le chargement réussi depuis un fichier."""
        mock_file.exists.return_value = True
        mock_file.stat.return_value.st_mtime = 12345.0

        theme_data = {"name": "Loaded Theme"}
        mock_content = json.dumps(theme_data)

        # Mock le retour de _theme_from_dict avec un objet qui a un attribut name
        mock_theme = MagicMock()
        mock_theme.name = "Loaded Theme"
        manager._theme_from_dict = MagicMock(return_value=mock_theme)

        with patch("builtins.open", mock_open(read_data=mock_content)):
            with patch("json.load", return_value=theme_data):
                theme = manager.load_active_theme()

        assert theme == mock_theme
        assert manager._cache_timestamp == 12345.0
        manager._theme_from_dict.assert_called_once_with(theme_data)

    @patch("core.theme.core_active_theme_manager.ActiveThemeManager.ACTIVE_THEME_FILE")
    def test_load_active_theme_error(self, mock_file, manager):
        """Test la gestion d'erreur lors du chargement."""
        mock_file.exists.return_value = True

        manager._create_default_theme = MagicMock(return_value="default_theme")

        # Simuler une erreur JSON
        with patch("builtins.open", mock_open(read_data="invalid json")):
            with patch("json.load", side_effect=json.JSONDecodeError("msg", "doc", 0)):
                theme = manager.load_active_theme()

        assert theme == "default_theme"
        manager._create_default_theme.assert_called_once()

    @patch("core.theme.core_active_theme_manager.ActiveThemeManager.ACTIVE_THEME_FILE")
    def test_save_active_theme(self, mock_file, manager, mock_theme):
        """Test la sauvegarde du thème."""
        manager.active_theme = mock_theme
        manager._theme_to_dict = MagicMock(return_value={"name": "Test Theme"})
        mock_file.stat.return_value.st_mtime = 67890.0

        with patch("builtins.open", mock_open()) as mock_f:
            manager.save_active_theme()

            mock_file.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
            mock_f.assert_called_once_with(mock_file, "w", encoding="utf-8")

        assert manager._cache_timestamp == 67890.0

    def test_save_active_theme_none(self, manager):
        """Test que la sauvegarde ne fait rien si aucun thème actif."""
        manager.active_theme = None

        with patch("builtins.open", mock_open()) as mock_f:
            manager.save_active_theme()
            mock_f.assert_not_called()

    def test_get_active_theme(self, manager, mock_theme):
        """Test get_active_theme retourne le thème existant ou charge."""
        # Cas 1: Thème déjà chargé
        manager.active_theme = mock_theme
        assert manager.get_active_theme() == mock_theme

        # Cas 2: Thème non chargé
        manager.active_theme = None
        manager.load_active_theme = MagicMock(return_value="loaded_theme")
        assert manager.get_active_theme() == "loaded_theme"
        manager.load_active_theme.assert_called_once()

    def test_export_to_grub_config(self, manager, mock_theme):
        """Test l'export vers la configuration GRUB."""
        manager.active_theme = mock_theme

        config = manager.export_to_grub_config()

        assert "GRUB_TIMEOUT" in config
        assert config["GRUB_TIMEOUT"] == str(mock_theme.grub_timeout)
        assert "GRUB_THEME" in config

    def test_export_to_grub_config_loads_theme(self, manager):
        """Test que l'export charge le thème s'il n'est pas chargé."""
        manager.active_theme = None
        manager.get_active_theme = MagicMock(return_value=create_custom_theme("test"))

        manager.export_to_grub_config()
        manager.get_active_theme.assert_called_once()

    def test_create_default_theme(self, manager):
        """Test la création du thème par défaut."""
        theme = manager._create_default_theme()

        assert isinstance(theme, GrubTheme)
        assert theme.name == "default"
        assert theme.colors.title_color == "#FFFFFF"

    @patch("core.theme.core_active_theme_manager.ActiveThemeManager.ACTIVE_THEME_FILE")
    def test_is_cache_valid(self, mock_file, manager):
        """Test la validation du cache."""
        # Cas fichier n'existe pas
        mock_file.exists.return_value = False
        assert manager._is_cache_valid() is False

        # Cas cache valide
        mock_file.exists.return_value = True
        mock_file.stat.return_value.st_mtime = 100.0
        manager._cache_timestamp = 100.0
        assert manager._is_cache_valid() is True

        # Cas cache invalide
        mock_file.stat.return_value.st_mtime = 200.0
        assert manager._is_cache_valid() is False

        # Cas erreur OS
        mock_file.stat.side_effect = OSError()
        assert manager._is_cache_valid() is False

    def test_theme_conversion_roundtrip(self, manager):
        """Test la conversion thème <-> dict."""
        # Créer un thème complet
        original_theme = create_custom_theme(
            name="RoundtripTheme", title_color="#123456", background_color="#654321", background_image="bg.png"
        )
        original_theme.grub_timeout = 42
        original_theme.grub_disable_recovery = True
        original_theme.hidden_entries = ["entry1", "entry2"]

        # Convertir en dict
        data = manager._theme_to_dict(original_theme)

        # Vérifier quelques champs du dict
        assert data["name"] == "RoundtripTheme"
        assert data["colors"]["title_color"] == "#123456"
        assert data["grub_timeout"] == 42
        assert data["grub_disable_recovery"] is True
        assert data["hidden_entries"] == ["entry1", "entry2"]

        # Reconstruire le thème
        restored_theme = manager._theme_from_dict(data)

        # Vérifier l'égalité
        assert restored_theme.name == original_theme.name
        assert restored_theme.colors.title_color == original_theme.colors.title_color
        assert restored_theme.grub_timeout == original_theme.grub_timeout
        assert restored_theme.grub_disable_recovery == original_theme.grub_disable_recovery
        assert restored_theme.hidden_entries == original_theme.hidden_entries
