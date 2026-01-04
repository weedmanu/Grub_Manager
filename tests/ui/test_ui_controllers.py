"""Tests pour les contrôleurs SRP (Single Responsibility)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from ui.controllers import (
    TimeoutController,
    DefaultChoiceController,
    PermissionController,
)


class TestTimeoutController:
    """Tests pour TimeoutController."""

    def test_get_value_returns_default_when_dropdown_none(self):
        """Retourne 5 par défaut si dropdown est None."""
        parent = MagicMock()
        parent.timeout_dropdown = None
        
        ctrl = TimeoutController(parent)
        assert ctrl.get_value() == 5

    def test_get_value_returns_selected_value(self):
        """Retourne la valeur sélectionnée du dropdown."""
        parent = MagicMock()
        parent.timeout_dropdown = MagicMock()
        parent.timeout_dropdown.get_selected.return_value = "10"
        
        ctrl = TimeoutController(parent)
        assert ctrl.get_value() == 10

    def test_get_value_returns_default_on_error(self):
        """Retourne 5 en cas d'erreur."""
        parent = MagicMock()
        parent.timeout_dropdown = MagicMock()
        parent.timeout_dropdown.get_selected.side_effect = ValueError("Invalid")
        
        ctrl = TimeoutController(parent)
        assert ctrl.get_value() == 5

    def test_get_value_returns_default_on_attribute_error(self):
        """Retourne 5 si un AttributeError est levé."""
        parent = MagicMock()
        parent.timeout_dropdown = MagicMock()
        parent.timeout_dropdown.get_selected.side_effect = AttributeError("Missing attr")
        
        ctrl = TimeoutController(parent)
        assert ctrl.get_value() == 5

    def test_set_value_handles_none_model(self):
        """N'échoue pas si get_model() retourne None."""
        parent = MagicMock()
        parent.timeout_dropdown = MagicMock()
        parent.timeout_dropdown.get_model.return_value = None
        
        ctrl = TimeoutController(parent)
        ctrl.set_value(10)  # Ne doit pas lever d'exception
        
        # Vérifier que set_selected n'a pas été appelé
        parent.timeout_dropdown.set_selected.assert_not_called()

    def test_set_value_handles_conversion_error(self):
        """Ne lève pas d'exception si int() échoue."""
        parent = MagicMock()
        model = MagicMock()
        model.get_n_items.return_value = 2
        # get_item retourne une chaîne non-convertible
        model.get_item.side_effect = ["invalid", "also_invalid"]
        
        parent.timeout_dropdown = MagicMock()
        parent.timeout_dropdown.get_model.return_value = model
        
        ctrl = TimeoutController(parent)
        ctrl.set_value(10)  # Ne doit pas lever d'exception
        
        # Avec des valeurs invalides, aucun match ne sera trouvé
        # donc set_selected ne sera pas appelé avec l'index du match
        # (ou sera appelé avec 0 en dernier lieu si trouvé)
        # Dans notre cas, pas d'appel du tout car except attrape
        parent.timeout_dropdown.set_selected.assert_not_called()

    def test_set_value_selects_matching_item(self):
        """Sélectionne l'élément correspondant à la valeur."""
        parent = MagicMock()
        model = MagicMock()
        model.get_n_items.return_value = 3
        model.get_item.side_effect = ["5", "10", "15"]
        
        parent.timeout_dropdown = MagicMock()
        parent.timeout_dropdown.get_model.return_value = model
        
        ctrl = TimeoutController(parent)
        ctrl.set_value(10)
        
        parent.timeout_dropdown.set_selected.assert_called_with(1)

    def test_set_value_does_nothing_if_dropdown_none(self):
        """N'échoue pas si dropdown est None."""
        parent = MagicMock()
        parent.timeout_dropdown = None
        
        ctrl = TimeoutController(parent)
        ctrl.set_value(10)  # Ne doit pas lever d'exception
        
        parent.timeout_dropdown = MagicMock()
        parent.timeout_dropdown.set_selected.assert_not_called()

    def test_sync_choices_callable(self):
        """sync_choices est une méthode existante."""
        parent = MagicMock()
        ctrl = TimeoutController(parent)
        
        assert callable(ctrl.sync_choices)
        ctrl.sync_choices(10)  # Ne doit pas lever d'exception


class TestDefaultChoiceController:
    """Tests pour DefaultChoiceController."""

    def test_get_choice_returns_default_when_dropdown_none(self):
        """Retourne '0' par défaut si dropdown est None."""
        parent = MagicMock()
        parent.default_dropdown = None
        
        ctrl = DefaultChoiceController(parent)
        assert ctrl.get_choice() == "0"

    def test_get_choice_returns_selected_item(self):
        """Retourne l'élément sélectionné du dropdown."""
        parent = MagicMock()
        model = MagicMock()
        model.get_item.return_value = "saved"
        
        parent.default_dropdown = MagicMock()
        parent.default_dropdown.get_selected.return_value = 0
        parent.default_dropdown.get_model.return_value = model
        
        ctrl = DefaultChoiceController(parent)
        assert ctrl.get_choice() == "saved"

    def test_get_choice_returns_default_on_error(self):
        """Retourne '0' en cas d'erreur."""
        parent = MagicMock()
        parent.default_dropdown = MagicMock()
        parent.default_dropdown.get_selected.return_value = -1
        
        ctrl = DefaultChoiceController(parent)
        assert ctrl.get_choice() == "0"

    def test_get_choice_handles_none_model(self):
        """Retourne '0' si get_model() retourne None."""
        parent = MagicMock()
        parent.default_dropdown = MagicMock()
        parent.default_dropdown.get_selected.return_value = 0
        parent.default_dropdown.get_model.return_value = None
        
        ctrl = DefaultChoiceController(parent)
        assert ctrl.get_choice() == "0"

    def test_get_choice_handles_attribute_error(self):
        """Retourne '0' si AttributeError est levé."""
        parent = MagicMock()
        parent.default_dropdown = MagicMock()
        parent.default_dropdown.get_selected.side_effect = AttributeError("Missing")
        
        ctrl = DefaultChoiceController(parent)
        assert ctrl.get_choice() == "0"

    def test_set_choice_selects_saved(self):
        """Sélectionne l'index 0 quand valeur est 'saved'."""
        parent = MagicMock()
        parent.default_dropdown = MagicMock()
        
        ctrl = DefaultChoiceController(parent)
        ctrl.set_choice("saved")
        
        parent.default_dropdown.set_selected.assert_called_with(0)

    def test_set_choice_handles_none_model(self):
        """N'échoue pas si get_model() retourne None."""
        parent = MagicMock()
        parent.default_dropdown = MagicMock()
        parent.default_dropdown.get_model.return_value = None
        
        ctrl = DefaultChoiceController(parent)
        ctrl.set_choice("custom")
        
        # set_selected ne doit pas être appelé
        parent.default_dropdown.set_selected.assert_not_called()

    def test_set_choice_finds_matching_item(self):
        """Trouve et sélectionne l'élément correspondant."""
        parent = MagicMock()
        model = MagicMock()
        model.get_n_items.return_value = 3
        model.get_item.side_effect = ["saved", "0", "1>2"]
        
        parent.default_dropdown = MagicMock()
        parent.default_dropdown.get_model.return_value = model
        
        ctrl = DefaultChoiceController(parent)
        ctrl.set_choice("1>2")
        
        parent.default_dropdown.set_selected.assert_called_with(2)

    def test_set_choice_adds_new_item_if_not_found(self):
        """Ajoute une nouvelle option si elle n'existe pas."""
        parent = MagicMock()
        model = MagicMock()
        model.get_n_items.return_value = 1
        model.get_item.return_value = "saved"
        
        parent.default_dropdown = MagicMock()
        parent.default_dropdown.get_model.return_value = model
        
        ctrl = DefaultChoiceController(parent)
        ctrl.set_choice("custom")
        
        # Vérifier que append a été appelée avec la nouvelle valeur
        model.append.assert_called_with("custom")
        # Après append, get_n_items devrait retourner 2, donc set_selected(1)
        # Mais comme on simule, on vérifie juste que set_selected a été appelé
        parent.default_dropdown.set_selected.assert_called()

    def test_set_choice_handles_empty_string(self):
        """Traite les chaînes vides comme '0'."""
        parent = MagicMock()
        model = MagicMock()
        model.get_n_items.return_value = 1
        model.get_item.return_value = "saved"
        
        parent.default_dropdown = MagicMock()
        parent.default_dropdown.get_model.return_value = model
        
        ctrl = DefaultChoiceController(parent)
        ctrl.set_choice("")
        
        # Une chaîne vide devient "0", qui doit être recherchée
        # Si le modèle retourne "saved", elle ne sera pas trouvée
        # Donc append sera appelée avec "0"
        model.append.assert_called_with("0")
        parent.default_dropdown.set_selected.assert_called()

    def test_set_choice_handles_exception_in_loop(self):
        """Ne lève pas d'exception si une erreur se produit dans la boucle."""
        parent = MagicMock()
        model = MagicMock()
        # get_n_items retourne 1 pour la boucle, mais get_item lève
        model.get_n_items.return_value = 1
        model.get_item.side_effect = ValueError("Conversion error")
        
        parent.default_dropdown = MagicMock()
        parent.default_dropdown.get_model.return_value = model
        
        ctrl = DefaultChoiceController(parent)
        ctrl.set_choice("custom")  # Ne doit pas lever d'exception
        
        # Avec l'exception, l'execution se termine dans le except

    def test_refresh_choices_callable(self):
        """refresh_choices est une méthode existante."""
        parent = MagicMock()
        ctrl = DefaultChoiceController(parent)
        
        assert callable(ctrl.refresh_choices)
        ctrl.refresh_choices(["0", "1"], "0")  # Ne doit pas lever d'exception


class TestPermissionController:
    """Tests pour PermissionController."""

    def test_is_root_detects_root_user(self):
        """Détecte correctement l'utilisateur root."""
        ctrl = PermissionController()
        
        with patch("os.geteuid", return_value=0):
            assert ctrl.is_root() is True

    def test_is_root_detects_non_root_user(self):
        """Détecte correctement un utilisateur non-root."""
        ctrl = PermissionController()
        
        with patch("os.geteuid", return_value=1000):
            assert ctrl.is_root() is False

    def test_is_root_cached(self):
        """Met en cache le résultat de is_root()."""
        ctrl = PermissionController()
        
        with patch("os.geteuid", return_value=0):
            result1 = ctrl.is_root()
        
        # Changer la valeur retournée, le cache doit rester
        with patch("os.geteuid", return_value=1000):
            result2 = ctrl.is_root()
        
        assert result1 is True
        assert result2 is True  # Cache, pas appelé à nouveau

    def test_check_and_warn_returns_true_for_root(self):
        """Retourne True si l'utilisateur est root."""
        ctrl = PermissionController()
        callback = MagicMock()
        
        with patch("os.geteuid", return_value=0):
            result = ctrl.check_and_warn(callback)
            assert result is True
            callback.assert_not_called()

    def test_check_and_warn_returns_false_for_non_root(self):
        """Retourne False et affiche un avertissement si non-root."""
        ctrl = PermissionController()
        callback = MagicMock()
        
        with patch("os.geteuid", return_value=1000):
            result = ctrl.check_and_warn(callback)
            assert result is False
            callback.assert_called_once()
            assert "droits root" in callback.call_args[0][0]

    def test_can_modify_system_requires_root(self):
        """can_modify_system() retourne True uniquement si root."""
        ctrl = PermissionController()
        
        with patch("os.geteuid", return_value=0):
            assert ctrl.can_modify_system() is True
        
        # Créer une nouvelle instance (pas de cache)
        ctrl2 = PermissionController()
        with patch("os.geteuid", return_value=1000):
            assert ctrl2.can_modify_system() is False

    def test_can_read_grub_files_always_true(self):
        """can_read_grub_files() retourne toujours True (validation runtime)."""
        ctrl = PermissionController()
        assert ctrl.can_read_grub_files() is True
