"""Tests unitaires pour la politique des boutons d'onglets."""

from unittest.mock import MagicMock

from ui.ui_tab_policy import TabPolicy, apply_tab_policy


def test_tab_policy_get_button_states():
    # Sauvegardes/Maintenance -> False, False
    assert TabPolicy.get_button_states("Sauvegardes", True) == (False, False)
    assert TabPolicy.get_button_states("Maintenance", False) == (False, False)

    # Général/Menu/Affichage -> True, True
    assert TabPolicy.get_button_states("Général", False) == (True, True)
    assert TabPolicy.get_button_states("General", True) == (True, True)
    assert TabPolicy.get_button_states("Menu", False) == (True, True)
    assert TabPolicy.get_button_states("Affichage", True) == (True, True)

    # Autres (ex: Thèmes) -> Reload=True, Save=is_dirty
    assert TabPolicy.get_button_states("Thèmes", True) == (True, True)
    assert TabPolicy.get_button_states("Thèmes", False) == (True, False)
    assert TabPolicy.get_button_states("Inconnu", True) == (True, True)


def test_apply_tab_policy():
    window = MagicMock()
    window.state_manager.is_dirty.return_value = True

    apply_tab_policy(window, "Sauvegardes")
    window.reload_btn.set_sensitive.assert_called_with(False)
    window.save_btn.set_sensitive.assert_called_with(False)

    window.state_manager.is_dirty.return_value = False
    apply_tab_policy(window, "Thèmes")
    window.reload_btn.set_sensitive.assert_called_with(True)
    window.save_btn.set_sensitive.assert_called_with(False)

    window.state_manager.is_dirty.return_value = True
    apply_tab_policy(window, "Général")
    window.reload_btn.set_sensitive.assert_called_with(True)
    window.save_btn.set_sensitive.assert_called_with(True)
