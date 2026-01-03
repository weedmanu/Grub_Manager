"""Tests pour le générateur de thèmes."""

from unittest.mock import MagicMock, patch

import pytest

from core.theme.core_theme_generator import (
    GrubTheme,
    ThemeColors,
    ThemeFonts,
    ThemeGenerator,
    ThemeImage,
    ThemeLayout,
    create_custom_theme,
)


class TestThemeGenerator:
    """Tests pour la classe ThemeGenerator."""

    @pytest.fixture
    def default_theme(self):
        """Fixture pour un thème par défaut."""
        return GrubTheme(name="TestTheme")

    def test_export_grub_config_defaults(self, default_theme):
        """Test l'export de la configuration GRUB avec les valeurs par défaut."""
        config = ThemeGenerator.export_grub_config(default_theme)
        
        assert config["GRUB_DEFAULT"] == "0"
        assert config["GRUB_TIMEOUT"] == "5"
        assert config["GRUB_TIMEOUT_STYLE"] == "menu"
        assert config["GRUB_GFXMODE"] == "auto"
        assert config["GRUB_THEME"].endswith("/TestTheme/theme.txt")
        
        # Vérifie que les options booléennes par défaut (False) ne sont pas présentes
        assert "GRUB_DISABLE_RECOVERY" not in config
        assert "GRUB_DISABLE_OS_PROBER" not in config

    def test_export_grub_config_custom(self, default_theme):
        """Test l'export avec des valeurs personnalisées."""
        default_theme.grub_timeout = 10
        default_theme.grub_disable_recovery = True
        default_theme.grub_disable_os_prober = True
        default_theme.grub_cmdline_linux = "nomodeset"
        default_theme.grub_recordfail_timeout = 30
        default_theme.grub_disable_submenu = True
        default_theme.grub_disable_linux_uuid = True
        default_theme.grub_savedefault = True
        default_theme.grub_hidden_timeout_quiet = True
        default_theme.grub_init_tune = "480 440 1"
        default_theme.grub_preload_modules = "lvm fat"
        
        config = ThemeGenerator.export_grub_config(default_theme)
        
        assert config["GRUB_TIMEOUT"] == "10"
        assert config["GRUB_DISABLE_RECOVERY"] == "true"
        assert config["GRUB_DISABLE_OS_PROBER"] == "true"
        assert config["GRUB_CMDLINE_LINUX"] == "nomodeset"
        assert config["GRUB_RECORDFAIL_TIMEOUT"] == "30"
        assert config["GRUB_DISABLE_SUBMENU"] == "y"
        assert config["GRUB_DISABLE_LINUX_UUID"] == "true"
        assert config["GRUB_SAVEDEFAULT"] == "true"
        assert config["GRUB_HIDDEN_TIMEOUT_QUIET"] == "true"
        assert config["GRUB_INIT_TUNE"] == "480 440 1"
        assert config["GRUB_PRELOAD_MODULES"] == "lvm fat"

    def test_generate_theme_txt_basic(self, default_theme):
        """Test la génération du fichier theme.txt de base."""
        default_theme.title_text = "My Custom Title"
        content = ThemeGenerator.generate_theme_txt(default_theme)
        
        assert '# GRUB Theme: TestTheme' in content
        assert 'title-text: "My Custom Title"' in content
        assert 'desktop-color: "#000000"' in content
        assert '+ boot_menu {' in content
        assert 'scrollbar = true' in content
        assert '+ progress_bar {' in content
        assert '+ label {' in content

    def test_generate_theme_txt_with_image(self, default_theme):
        """Test la génération avec une image de fond."""
        default_theme.image.desktop_image = "background.png"
        
        content = ThemeGenerator.generate_theme_txt(default_theme)
        
        assert 'desktop-image: "background.png"' in content
        assert 'desktop-image-scale-method: "stretch"' in content
        assert 'desktop-image-h-align: "center"' in content
        assert 'desktop-image-v-align: "center"' in content
        assert 'desktop-color' not in content  # Ne doit pas apparaître si image présente

    def test_generate_theme_txt_options(self, default_theme):
        """Test la génération avec différentes options d'affichage."""
        # Cas 1: Tout désactivé
        default_theme.show_boot_menu = False
        default_theme.show_progress_bar = False
        default_theme.show_timeout_message = False
        
        content = ThemeGenerator.generate_theme_txt(default_theme)
        
        assert '+ boot_menu {' not in content
        assert '+ progress_bar {' not in content
        assert '+ label {' not in content

        # Cas 2: Menu activé mais scrollbar désactivée
        default_theme.show_boot_menu = True
        default_theme.show_scrollbar = False
        content = ThemeGenerator.generate_theme_txt(default_theme)
        assert '+ boot_menu {' in content
        assert 'scrollbar = true' not in content

    def test_save_theme(self, default_theme, tmp_path):
        """Test la sauvegarde d'un thème."""
        theme_file = ThemeGenerator.save_theme(default_theme, tmp_path)
        
        assert theme_file.exists()
        assert theme_file.name == "theme.txt"
        assert str(tmp_path / "TestTheme" / "theme.txt") == str(theme_file)
        
        content = theme_file.read_text()
        assert '# GRUB Theme: TestTheme' in content

    def test_create_default_themes(self):
        """Test la création des thèmes par défaut."""
        themes = ThemeGenerator.create_default_themes()
        
        assert len(themes) >= 4
        names = [t.name for t in themes]
        assert "classic" in names
        assert "dark" in names
        assert "blue" in names
        assert "matrix" in names
        
        # Vérifier un détail d'un thème
        matrix = next(t for t in themes if t.name == "matrix")
        assert matrix.colors.title_color == "#00FF00"


class TestCreateCustomTheme:
    """Tests pour la fonction create_custom_theme."""

    def test_create_custom_theme_defaults(self):
        """Test la création avec les valeurs par défaut."""
        theme = create_custom_theme("MyTheme")
        
        assert theme.name == "MyTheme"
        assert theme.colors.title_color == "#FFFFFF"
        assert theme.colors.desktop_color == "#000000"
        assert theme.image.desktop_image == ""

    def test_create_custom_theme_custom_values(self):
        """Test la création avec des valeurs personnalisées."""
        theme = create_custom_theme(
            "MyTheme",
            title_color="#FF0000",
            background_color="#0000FF",
            background_image="bg.png"
        )
        
        assert theme.colors.title_color == "#FF0000"
        assert theme.colors.desktop_color == "#0000FF"
        assert theme.image.desktop_image == "bg.png"


class TestDataClasses:
    """Tests basiques pour les dataclasses."""

    def test_theme_colors_defaults(self):
        colors = ThemeColors()
        assert colors.title_color == "#FFFFFF"

    def test_theme_fonts_defaults(self):
        fonts = ThemeFonts()
        assert "DejaVu" in fonts.title_font

    def test_theme_layout_defaults(self):
        layout = ThemeLayout()
        assert layout.menu_left == "20%"

    def test_theme_image_defaults(self):
        image = ThemeImage()
        assert image.desktop_image == ""
