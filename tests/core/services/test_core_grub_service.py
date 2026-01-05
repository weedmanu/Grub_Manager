"""Tests pour le service GRUB."""

from unittest.mock import patch

from core.services.core_services_grub import GrubConfig, GrubService, MenuEntry


class TestGrubService:
    """Tests pour la classe GrubService."""

    @patch("core.services.core_services_grub.read_grub_default")
    def test_read_current_config_success(self, mock_read):
        """Test la lecture réussie de la configuration."""
        mock_read.return_value = {
            "GRUB_TIMEOUT": "5",
            "GRUB_DEFAULT": "2",
            "GRUB_COLOR_NORMAL": "red/blue",
            "GRUB_COLOR_HIGHLIGHT": "blue/red",
            "GRUB_GFXMODE": "1920x1080",
            "GRUB_THEME": "/boot/grub/themes/test/theme.txt",
            "GRUB_CMDLINE_LINUX": "quiet",
            "GRUB_CMDLINE_LINUX_DEFAULT": "splash",
            "GRUB_DISABLE_RECOVERY": "true",
            "GRUB_DISABLE_OS_PROBER": "true",
            "GRUB_INIT_TUNE": "440 1",
        }

        config = GrubService().read_current_config()

        assert isinstance(config, GrubConfig)
        assert config.timeout == 5
        assert config.default_entry == "2"
        assert config.grub_color_normal == "red/blue"
        assert config.grub_color_highlight == "blue/red"
        assert config.grub_gfxmode == "1920x1080"
        assert config.grub_theme == "/boot/grub/themes/test/theme.txt"
        assert config.grub_cmdline_linux == "quiet"
        assert config.grub_cmdline_linux_default == "splash"
        assert config.grub_disable_recovery == "true"
        assert config.grub_disable_os_prober == "true"
        assert config.grub_init_tune == "440 1"

    @patch("core.services.core_services_grub.read_grub_default")
    def test_read_current_config_defaults(self, mock_read):
        """Test les valeurs par défaut si la config est vide."""
        mock_read.return_value = {}

        config = GrubService().read_current_config()

        assert config.timeout == 10
        assert config.default_entry == "0"
        assert config.grub_color_normal == "white/black"
        assert config.grub_theme is None

    @patch("core.services.core_services_grub.read_grub_default")
    def test_read_current_config_error(self, mock_read):
        """Test la gestion d'erreur lors de la lecture."""
        mock_read.side_effect = OSError("Erreur lecture")

        config = GrubService().read_current_config()

        assert isinstance(config, GrubConfig)
        assert config.timeout == 10  # Valeur par défaut

    @patch("core.services.core_services_grub.get_simulated_os_prober_entries")
    def test_get_menu_entries_success(self, mock_get_entries):
        """Test la récupération des entrées du menu."""
        mock_get_entries.return_value = [
            {"title": "Ubuntu", "id": "ubuntu_id"},
            {"title": "Windows", "id": "windows_id"},
        ]

        entries = GrubService().get_menu_entries()

        assert len(entries) == 2
        assert isinstance(entries[0], MenuEntry)
        assert entries[0].title == "Ubuntu"
        assert entries[0].id == "ubuntu_id"
        assert entries[1].title == "Windows"
        assert entries[1].id == "windows_id"

    @patch("core.services.core_services_grub.get_simulated_os_prober_entries")
    def test_get_menu_entries_non_dict_objects(self, mock_get_entries):
        class Obj:
            def __init__(self, title: str, id: str):
                self.title = title
                self.id = id

        mock_get_entries.return_value = [Obj("Linux", "linux_id")]
        entries = GrubService().get_menu_entries()
        assert entries == [MenuEntry(title="Linux", id="linux_id")]

    @patch("core.services.core_services_grub.get_simulated_os_prober_entries")
    def test_get_menu_entries_error(self, mock_get_entries):
        """Test la gestion d'erreur lors de la récupération des entrées."""
        mock_get_entries.side_effect = ValueError("Erreur parsing")

        entries = GrubService().get_menu_entries()

        assert len(entries) == 1
        assert entries[0].title == "Ubuntu"
        assert entries[0].id == "gnulinux"

    def test_get_theme_name(self):
        """Test l'extraction du nom du thème."""
        service = GrubService()
        assert service.get_theme_name(None) == "05_debian_theme (par défaut)"
        assert service.get_theme_name("") == "05_debian_theme (par défaut)"
        assert service.get_theme_name("/boot/grub/themes/mytheme") == "mytheme"
        assert service.get_theme_name("simple_name") == "simple_name"
