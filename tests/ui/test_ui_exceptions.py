"""Tests pour les exceptions UI."""


from ui.ui_exceptions import UiError, UiStateError, UiValidationError, UiWidgetError


class TestUiExceptions:
    """Tests pour les exceptions UI."""

    def test_ui_error_basic(self):
        """Test UiError de base."""
        error = UiError("Erreur UI")
        assert str(error) == "Erreur UI"
        assert isinstance(error, Exception)

    def test_ui_error_inheritance(self):
        """Test que toutes les exceptions UI héritent de UiError."""
        errors = [
            UiValidationError("Validation failed"),
            UiWidgetError("Widget error"),
            UiStateError("State error"),
        ]

        for error in errors:
            assert isinstance(error, UiError)

    def test_ui_validation_error(self):
        """Test UiValidationError."""
        error = UiValidationError("Champ requis manquant")
        assert str(error) == "Champ requis manquant"
        assert isinstance(error, UiError)

    def test_ui_widget_error(self):
        """Test UiWidgetError."""
        error = UiWidgetError("Bouton non trouvé")
        assert str(error) == "Bouton non trouvé"
        assert isinstance(error, UiError)

    def test_ui_state_error(self):
        """Test UiStateError."""
        error = UiStateError("État invalide")
        assert str(error) == "État invalide"
        assert isinstance(error, UiError)
