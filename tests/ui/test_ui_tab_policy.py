"""Tests unitaires pour la politique des boutons d'onglets."""

from unittest.mock import MagicMock

from ui.controllers.ui_controllers_tab_policy import TabPolicy, apply_tab_policy


def test_tab_policy_get_button_states():
    # Busy -> False, False
    assert TabPolicy.get_button_states("Général", busy=True) == (False, False)

    # Sauvegardes/Maintenance -> False, False
    assert TabPolicy.get_button_states("Sauvegardes", busy=False) == (False, False)
    assert TabPolicy.get_button_states("Maintenance", busy=False) == (False, False)

    # Tous les autres -> True, True
    assert TabPolicy.get_button_states("Général", busy=False) == (True, True)
    assert TabPolicy.get_button_states("General", busy=False) == (True, True)
    assert TabPolicy.get_button_states("Menu", busy=False) == (True, True)
    assert TabPolicy.get_button_states("Affichage", busy=False) == (True, True)
    assert TabPolicy.get_button_states("Thèmes", busy=False) == (True, True)
    assert TabPolicy.get_button_states("Inconnu", busy=False) == (True, True)


def test_apply_tab_policy():
    window = MagicMock()
    window.state_manager.state = "clean"

    apply_tab_policy(window, "Sauvegardes")
    window.reload_btn.set_sensitive.assert_called_with(False)
    window.preview_btn.set_sensitive.assert_called_with(False)
    window.save_btn.set_sensitive.assert_called_with(False)

    apply_tab_policy(window, "Thèmes")
    window.reload_btn.set_sensitive.assert_called_with(True)
    window.preview_btn.set_sensitive.assert_called_with(True)
    window.save_btn.set_sensitive.assert_called_with(True)

    apply_tab_policy(window, "Général")
    window.reload_btn.set_sensitive.assert_called_with(True)
    window.preview_btn.set_sensitive.assert_called_with(True)
    window.save_btn.set_sensitive.assert_called_with(True)
