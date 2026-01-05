"""Tests pour le composant ColorPicker."""

from unittest.mock import MagicMock, patch

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
import pytest
from gi.repository import Gdk, Gtk

from ui.components.ui_components_color_picker import ColorPicker, create_color_grid_row


class TestColorPicker:
    """Tests pour la classe ColorPicker."""

    @pytest.fixture
    def mock_gtk(self):
        """Mock pour les composants GTK."""
        with (
            patch("ui.components.ui_components_color_picker.Gtk") as mock_gtk,
            patch("ui.components.ui_components_color_picker.Gdk") as mock_gdk,
        ):
            # Mock Label
            mock_label = MagicMock()
            mock_gtk.Label.return_value = mock_label

            # Mock ColorButton
            mock_color_button = MagicMock()
            mock_gtk.ColorButton.return_value = mock_color_button

            # Mock Box
            mock_box = MagicMock()
            mock_gtk.Box.return_value = mock_box

            # Mock RGBA
            mock_rgba = MagicMock()
            mock_gdk.RGBA.return_value = mock_rgba

            yield {
                "gtk": mock_gtk,
                "gdk": mock_gdk,
                "label": mock_label,
                "color_button": mock_color_button,
                "box": mock_box,
                "rgba": mock_rgba,
            }

    def test_initialization(self, mock_gtk):
        """Test l'initialisation du ColorPicker."""
        with patch.object(ColorPicker, "set_color") as mock_set_color:
            picker = ColorPicker("Test Color", "#FF0000")

            assert picker.label_text == "Test Color"
            assert picker.callback is None

            # Vérifier que les widgets ont été créés
            mock_gtk["gtk"].Label.assert_called_once_with(label="Test Color")
            mock_gtk["gtk"].ColorButton.assert_called_once()

            # Vérifier que set_color a été appelé
            mock_set_color.assert_called_once_with("#FF0000")

            # Vérifier la connexion du signal
            picker.color_button.connect.assert_called_once_with("color-set", picker._on_color_changed)

    def test_initialization_with_callback(self, mock_gtk):
        """Test l'initialisation avec callback."""
        callback = MagicMock()
        picker = ColorPicker("Test Color", "#00FF00", callback=callback)

        assert picker.callback == callback

    def test_get_color(self, mock_gtk):
        """Test la récupération de la couleur."""
        picker = ColorPicker("Test", "#FFFFFF")

        # Mock la valeur RGBA
        mock_rgba = MagicMock()
        mock_rgba.red = 0.5
        mock_rgba.green = 0.25
        mock_rgba.blue = 1.0
        picker.color_button.get_property.return_value = mock_rgba

        color = picker.get_color()

        assert color == "#7F3FFF"  # 0.5*255=127.5->7F, 0.25*255=63.75->3F, 1.0*255=255->FF
        picker.color_button.get_property.assert_called_with("rgba")

    def test_set_color_valid(self, mock_gtk):
        """Test la définition d'une couleur valide."""
        picker = ColorPicker("Test", "#FFFFFF")

        # Reset les mocks pour ignorer les appels d'initialisation
        mock_gtk["gdk"].RGBA.return_value.parse.reset_mock()
        picker.color_button.set_property.reset_mock()

        picker.set_color("#123456")

        # Vérifier que RGBA.parse a été appelé
        mock_gtk["gdk"].RGBA.return_value.parse.assert_called_once_with("#123456")
        # Vérifier que set_property a été appelé
        picker.color_button.set_property.assert_called_with("rgba", mock_gtk["gdk"].RGBA.return_value)

    def test_set_color_invalid(self, mock_gtk):
        """Test la définition d'une couleur invalide."""
        picker = ColorPicker("Test", "#FFFFFF")

        # Reset le mock pour ignorer l'appel initial
        picker.color_button.set_property.reset_mock()

        # Mock une exception lors du parsing
        mock_gtk["gdk"].RGBA.return_value.parse.side_effect = ValueError("Invalid color")

        picker.set_color("invalid")

        # Vérifier que set_property n'a pas été appelé avec "rgba"
        # Note: set_property peut être appelé pour d'autres choses (comme use-alpha)
        # mais ici on vérifie qu'il n'est pas appelé après l'erreur
        assert not any(call.args[0] == "rgba" for call in picker.color_button.set_property.call_args_list)

    def test_on_color_changed_with_callback(self, mock_gtk):
        """Test le callback lors du changement de couleur."""
        callback = MagicMock()
        picker = ColorPicker("Test", "#FFFFFF", callback=callback)

        # Mock get_color
        picker.get_color = MagicMock(return_value="#ABCDEF")

        picker._on_color_changed(picker.color_button)

        callback.assert_called_once_with("#ABCDEF")

    def test_on_color_changed_without_callback(self, mock_gtk):
        """Test le changement de couleur sans callback."""
        picker = ColorPicker("Test", "#FFFFFF")

        picker.get_color = MagicMock(return_value="#ABCDEF")

        # Ne devrait pas planter
        picker._on_color_changed(picker.color_button)

    def test_get_widget(self, mock_gtk):
        """Test la récupération du widget complet."""
        picker = ColorPicker("Test", "#FFFFFF")

        widget = picker.get_widget()

        # Vérifier que Box a été créé
        mock_gtk["gtk"].Box.assert_called_once_with(orientation=mock_gtk["gtk"].Orientation.HORIZONTAL, spacing=10)

        # Vérifier que les widgets ont été ajoutés
        widget.append.assert_any_call(picker.label)
        widget.append.assert_any_call(picker.color_button)

        assert widget == mock_gtk["box"]


class TestCreateColorGridRow:
    """Tests pour la fonction helper create_color_grid_row."""

    @patch("ui.components.ui_components_color_picker.ColorPicker")
    def test_create_color_grid_row(self, mock_color_picker_class):
        """Test la création d'une ligne pour Grid."""
        mock_picker = MagicMock()
        mock_label = MagicMock()
        mock_color_button = MagicMock()
        mock_picker.label = mock_label
        mock_picker.color_button = mock_color_button

        mock_color_picker_class.return_value = mock_picker

        callback = MagicMock()
        label, button = create_color_grid_row("Test Label", "#123456", callback=callback)

        # Vérifier que ColorPicker a été créé avec les bons paramètres
        mock_color_picker_class.assert_called_once_with("Test Label", "#123456", callback=callback)

        # Vérifier le retour
        assert label == mock_label
        assert button == mock_color_button


def test_color_picker_init():
    callback = MagicMock()
    picker = ColorPicker("Test Label", "#FF0000", callback=callback)
    assert picker.label_text == "Test Label"
    assert picker.get_color() == "#FF0000"


def test_color_picker_on_color_changed():
    callback = MagicMock()
    picker = ColorPicker("Test Label", "#FFFFFF", callback=callback)

    # Simulate color change
    rgba = Gdk.RGBA()
    rgba.parse("#00FF00")
    picker.color_button.set_property("rgba", rgba)

    picker._on_color_changed(picker.color_button)
    callback.assert_called_with("#00FF00")


def test_color_picker_on_color_changed_no_callback():
    picker = ColorPicker("Test Label", "#FFFFFF", callback=None)
    # Should not crash
    picker._on_color_changed(picker.color_button)


def test_color_picker_set_color_invalid():
    picker = ColorPicker("Test Label", "#FFFFFF")
    # Should not crash on invalid color
    picker.set_color("invalid")
    assert picker.get_color() == "#FFFFFF"


def test_color_picker_get_widget():
    picker = ColorPicker("Test Label", "#FFFFFF")
    widget = picker.get_widget()
    assert isinstance(widget, Gtk.Box)
    # Check if label and button are in the box
    # In GTK4 we can't easily list children like in GTK3 without iterating


def test_create_color_grid_row():
    callback = MagicMock()
    label, button = create_color_grid_row("Test", "#0000FF", callback=callback)
    assert isinstance(label, Gtk.Label)
    assert isinstance(button, Gtk.ColorButton)
    assert label.get_text() == "Test"
