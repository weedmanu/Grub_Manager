"""Tests pour les composants de thème UI."""

from unittest.mock import MagicMock, patch

import gi
gi.require_version('Gtk', '4.0')
import pytest

from ui.components.ui_theme_components import ImageScaleSelector, ResolutionSelector, TextEntry


class TestResolutionSelector:
    """Tests pour ResolutionSelector."""

    @pytest.fixture
    def mock_gtk(self):
        """Mock pour les composants GTK."""
        with patch("ui.components.ui_theme_components.Gtk") as mock_gtk:
            # Mock Label
            mock_label = MagicMock()
            mock_gtk.Label.return_value = mock_label

            # Mock DropDown
            mock_dropdown = MagicMock()
            mock_gtk.DropDown.new_from_strings.return_value = mock_dropdown

            yield {
                'gtk': mock_gtk,
                'label': mock_label,
                'dropdown': mock_dropdown
            }

    def test_initialization_default(self, mock_gtk):
        """Test l'initialisation par défaut."""
        selector = ResolutionSelector()

        assert selector.callback is None
        mock_gtk['gtk'].Label.assert_called_once_with(label="Résolution:")
        mock_gtk['gtk'].DropDown.new_from_strings.assert_called_once_with(ResolutionSelector.RESOLUTIONS)

        # Vérifier que la résolution par défaut est sélectionnée
        selector.dropdown.set_selected.assert_called_once_with(8)  # Index de "1920x1080"

    def test_initialization_with_callback(self, mock_gtk):
        """Test l'initialisation avec callback."""
        callback = MagicMock()
        selector = ResolutionSelector("1280x720", callback=callback)

        assert selector.callback == callback
        # Vérifier que l'index correct est sélectionné
        selector.dropdown.set_selected.assert_called_once_with(3)  # Index de "1280x720"

    def test_initialization_invalid_resolution(self, mock_gtk):
        """Test l'initialisation avec résolution invalide."""
        selector = ResolutionSelector("invalid")

        # Vérifier que rien n'est sélectionné (index -1 ou 0)
        selector.dropdown.set_selected.assert_not_called()

    def test_get_resolution(self, mock_gtk):
        """Test la récupération de la résolution."""
        selector = ResolutionSelector()
        selector.dropdown.get_selected.return_value = 5  # "1366x768"

        resolution = selector.get_resolution()

        assert resolution == "1366x768"
        selector.dropdown.get_selected.assert_called_once()

    def test_set_resolution_valid(self, mock_gtk):
        """Test la définition d'une résolution valide."""
        selector = ResolutionSelector()
        selector.dropdown.set_selected.reset_mock()

        selector.set_resolution("2560x1440")

        selector.dropdown.set_selected.assert_called_once_with(9)  # Index de "2560x1440"

    def test_set_resolution_invalid(self, mock_gtk):
        """Test la définition d'une résolution invalide."""
        selector = ResolutionSelector()

        # Reset le mock pour ignorer l'appel d'initialisation
        selector.dropdown.set_selected.reset_mock()

        selector.set_resolution("invalid")

        selector.dropdown.set_selected.assert_not_called()

    def test_on_changed_with_callback(self, mock_gtk):
        """Test le callback lors du changement."""
        callback = MagicMock()
        selector = ResolutionSelector(callback=callback)
        selector.get_resolution = MagicMock(return_value="1024x768")

        selector._on_changed(selector.dropdown, None)

        callback.assert_called_once_with("1024x768")

    def test_on_changed_without_callback(self, mock_gtk):
        """Test le changement sans callback."""
        selector = ResolutionSelector()
        selector.get_resolution = MagicMock(return_value="1024x768")

        # Ne devrait pas planter
        selector._on_changed(selector.dropdown, None)


class TestImageScaleSelector:
    """Tests pour ImageScaleSelector."""

    @pytest.fixture
    def mock_gtk(self):
        """Mock pour les composants GTK."""
        with patch("ui.components.ui_theme_components.Gtk") as mock_gtk:
            # Mock Label
            mock_label = MagicMock()
            mock_gtk.Label.return_value = mock_label

            # Mock DropDown
            mock_dropdown = MagicMock()
            mock_gtk.DropDown.new_from_strings.return_value = mock_dropdown

            yield {
                'gtk': mock_gtk,
                'label': mock_label,
                'dropdown': mock_dropdown
            }

    def test_initialization_default(self, mock_gtk):
        """Test l'initialisation par défaut."""
        selector = ImageScaleSelector()

        assert selector.callback is None
        mock_gtk['gtk'].Label.assert_called_once_with(label="Redimensionnement:")
        mock_gtk['gtk'].DropDown.new_from_strings.assert_called_once_with(ImageScaleSelector.SCALE_METHODS)

        # Vérifier que la méthode par défaut est sélectionnée
        selector.dropdown.set_selected.assert_called_once_with(0)  # Index de "fit"

    def test_initialization_with_callback(self, mock_gtk):
        """Test l'initialisation avec callback."""
        callback = MagicMock()
        selector = ImageScaleSelector("stretch", callback=callback)

        assert selector.callback == callback
        # Vérifier que l'index correct est sélectionné
        selector.dropdown.set_selected.assert_called_once_with(1)  # Index de "stretch"

    def test_initialization_invalid_method(self, mock_gtk):
        """Test l'initialisation avec méthode invalide."""
        selector = ImageScaleSelector("invalid")

        # Vérifier que rien n'est sélectionné
        selector.dropdown.set_selected.assert_not_called()

    def test_get_method(self, mock_gtk):
        """Test la récupération de la méthode."""
        selector = ImageScaleSelector()
        selector.dropdown.get_selected.return_value = 2  # "crop"

        method = selector.get_method()

        assert method == "crop"
        selector.dropdown.get_selected.assert_called_once()

    def test_set_method_valid(self, mock_gtk):
        """Test la définition d'une méthode valide."""
        selector = ImageScaleSelector()
        selector.dropdown.set_selected.reset_mock()

        selector.set_method("stretch")

        selector.dropdown.set_selected.assert_called_once_with(1)  # Index de "stretch"

    def test_set_method_invalid(self, mock_gtk):
        """Test la définition d'une méthode invalide."""
        selector = ImageScaleSelector()

        # Reset le mock pour ignorer l'appel d'initialisation
        selector.dropdown.set_selected.reset_mock()

        selector.set_method("invalid")

        selector.dropdown.set_selected.assert_not_called()

    def test_on_changed_with_callback(self, mock_gtk):
        """Test le callback lors du changement."""
        callback = MagicMock()
        selector = ImageScaleSelector(callback=callback)
        selector.get_method = MagicMock(return_value="crop")

        selector._on_changed(selector.dropdown, None)

        callback.assert_called_once_with("crop")

    def test_on_changed_without_callback(self, mock_gtk):
        """Test le changement sans callback."""
        selector = ImageScaleSelector()
        selector.get_method = MagicMock(return_value="crop")

        # Ne devrait pas planter
        selector._on_changed(selector.dropdown, None)


class TestTextEntry:
    """Tests pour TextEntry."""

    @pytest.fixture
    def mock_gtk(self):
        """Mock pour les composants GTK."""
        with patch("ui.components.ui_theme_components.Gtk") as mock_gtk:
            # Mock Label
            mock_label = MagicMock()
            mock_gtk.Label.return_value = mock_label

            # Mock Entry
            mock_entry = MagicMock()
            mock_gtk.Entry.return_value = mock_entry

            yield {
                'gtk': mock_gtk,
                'label': mock_label,
                'entry': mock_entry
            }

    def test_initialization_minimal(self, mock_gtk):
        """Test l'initialisation minimale."""
        entry = TextEntry("Test Label")

        assert entry.callback is None
        mock_gtk['gtk'].Label.assert_called_once_with(label="Test Label")
        mock_gtk['gtk'].Entry.assert_called_once()
        entry.entry.set_text.assert_called_once_with("")
        entry.entry.set_placeholder_text.assert_not_called()

    def test_initialization_full(self, mock_gtk):
        """Test l'initialisation complète."""
        callback = MagicMock()
        entry = TextEntry("Test Label", "initial", placeholder="hint", callback=callback)

        assert entry.callback == callback
        entry.entry.set_text.assert_called_once_with("initial")
        entry.entry.set_placeholder_text.assert_called_once_with("hint")

    def test_get_text(self, mock_gtk):
        """Test la récupération du texte."""
        entry = TextEntry("Test")
        entry.entry.get_text.return_value = "test text"

        text = entry.get_text()

        assert text == "test text"
        entry.entry.get_text.assert_called_once()

    def test_set_text(self, mock_gtk):
        """Test la définition du texte."""
        entry = TextEntry("Test")

        # Reset le mock pour ignorer l'appel d'initialisation
        entry.entry.set_text.reset_mock()

        entry.set_text("new text")

        entry.entry.set_text.assert_called_once_with("new text")

    def test_on_changed_with_callback(self, mock_gtk):
        """Test le callback lors du changement."""
        callback = MagicMock()
        entry = TextEntry("Test", callback=callback)
        entry.get_text = MagicMock(return_value="changed text")

        entry._on_changed(entry.entry)

        callback.assert_called_once_with("changed text")

    def test_on_changed_without_callback(self, mock_gtk):
        """Test le changement sans callback."""
        entry = TextEntry("Test")
        entry.get_text = MagicMock(return_value="changed text")

        # Ne devrait pas planter
        entry._on_changed(entry.entry)