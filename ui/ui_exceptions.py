"""Exceptions spécifiques à l'interface utilisateur.

Centralise toutes les erreurs liées à l'UI (GTK, validation, widgets).
"""

from core.core_exceptions import GrubManagerError


class UiError(GrubManagerError):
    """Exception de base pour les erreurs UI."""


class UiValidationError(UiError):
    """Erreur de validation des données dans l'UI."""


class UiWidgetError(UiError):
    """Erreur liée à un widget spécifique."""


class UiStateError(UiError):
    """Erreur d'état de l'interface."""
