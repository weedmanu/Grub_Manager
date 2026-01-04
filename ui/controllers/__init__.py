"""Contrôleurs spécialisés pour l'UI GTK (Single Responsibility)."""

from .timeout_controller import TimeoutController
from .default_choice_controller import DefaultChoiceController
from .permission_controller import PermissionController

__all__ = [
    "TimeoutController",
    "DefaultChoiceController",
    "PermissionController",
]
