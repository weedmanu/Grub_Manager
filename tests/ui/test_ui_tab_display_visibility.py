"""Tests pour la visibilité dynamique des onglets selon le mode terminal."""

from unittest.mock import MagicMock

import pytest

from ui.helpers.ui_helpers_gtk_imports import Gtk
from ui.tabs.ui_tabs_display import _on_terminal_mode_changed, _toggle_theme_tabs_visibility


@pytest.fixture
def mock_notebook():
    """Crée un notebook mocké avec des pages."""
    notebook = MagicMock(spec=Gtk.Notebook)

    # Créer des pages mockées
    general_page = MagicMock(spec=Gtk.Box)
    general_page.set_visible = MagicMock()

    apparence_page = MagicMock(spec=Gtk.Box)
    apparence_page.set_visible = MagicMock()

    themes_page = MagicMock(spec=Gtk.Box)
    themes_page.set_visible = MagicMock()

    # Configurer get_n_pages
    notebook.get_n_pages.return_value = 3

    # Configurer get_nth_page
    def get_nth_page(idx):
        if idx == 0:
            return general_page
        elif idx == 1:
            return apparence_page
        elif idx == 2:
            return themes_page
        return None

    notebook.get_nth_page.side_effect = get_nth_page

    # Configurer get_tab_label_text
    def get_tab_label_text(page):
        if page is general_page:
            return "Général"
        elif page is apparence_page:
            return "Apparence"
        elif page is themes_page:
            return "Thèmes"
        return None

    notebook.get_tab_label_text.side_effect = get_tab_label_text

    # Configurer get_page pour retourner un objet avec set_property
    def get_page(page):
        page_obj = MagicMock()
        page_obj.set_property = MagicMock()
        return page_obj

    notebook.get_page.side_effect = get_page

    return notebook, general_page, apparence_page, themes_page


def test_toggle_theme_tabs_visibility_shows_theme_tabs(mock_notebook):
    """Vérifie que l'onglet Thèmes est affiché en mode graphique."""
    notebook, general_page, apparence_page, themes_page = mock_notebook

    _toggle_theme_tabs_visibility(notebook, show=True)

    # Seule la page Thèmes doit être affichée (pas Apparence qui reste toujours visible)
    themes_page.set_visible.assert_called_once_with(True)
    # Les pages Général et Apparence ne doivent pas être affectées
    general_page.set_visible.assert_not_called()
    apparence_page.set_visible.assert_not_called()


def test_toggle_theme_tabs_visibility_hides_theme_tabs(mock_notebook):
    """Vérifie que l'onglet Thèmes est masqué en mode console (Apparence reste visible)."""
    notebook, general_page, apparence_page, themes_page = mock_notebook

    _toggle_theme_tabs_visibility(notebook, show=False)

    # Seule la page Thèmes doit être masquée (Apparence reste visible pour les couleurs)
    themes_page.set_visible.assert_called_once_with(False)
    # Les pages Général et Apparence ne doivent pas être affectées
    general_page.set_visible.assert_not_called()
    apparence_page.set_visible.assert_not_called()


def test_on_terminal_mode_changed_graphical_mode():
    """Vérifie que le mode graphique active les options et affiche l'onglet Thèmes."""
    controller = MagicMock()

    # Configuration du mode gfxterm
    selected_item = MagicMock()
    selected_item.get_string.return_value = "gfxterm (graphique)"
    controller.grub_terminal_dropdown.get_selected_item.return_value = selected_item
    controller.grub_terminal_dropdown.get_selected.return_value = 0

    # Configurer le notebook
    notebook = MagicMock(spec=Gtk.Notebook)
    notebook.get_n_pages.return_value = 0  # Pas de pages pour simplifier
    controller.notebook = notebook

    _on_terminal_mode_changed(controller)

    # Le dropdown gfxmode doit être activé
    controller.gfxmode_dropdown.set_sensitive.assert_called_once_with(True)


def test_on_terminal_mode_changed_console_mode():
    """Vérifie que le mode console désactive les options graphiques et masque l'onglet Thèmes (pas Apparence)."""
    controller = MagicMock()

    # Configuration du mode console
    selected_item = MagicMock()
    selected_item.get_string.return_value = "console (texte)"
    controller.grub_terminal_dropdown.get_selected_item.return_value = selected_item
    controller.grub_terminal_dropdown.get_selected.return_value = 1

    # Configurer le notebook
    notebook = MagicMock(spec=Gtk.Notebook)
    notebook.get_n_pages.return_value = 0  # Pas de pages pour simplifier
    controller.notebook = notebook

    _on_terminal_mode_changed(controller)

    # Le dropdown gfxmode doit être désactivé
    controller.gfxmode_dropdown.set_sensitive.assert_called_once_with(False)


def test_on_terminal_mode_changed_no_dropdown():
    """Vérifie que la fonction ne plante pas si grub_terminal_dropdown est None."""
    controller = MagicMock()
    controller.grub_terminal_dropdown = None

    # Ne doit pas lever d'exception
    _on_terminal_mode_changed(controller)


def test_on_terminal_mode_changed_no_notebook():
    """Vérifie que la fonction gère l'absence de notebook."""
    controller = MagicMock()

    selected_item = MagicMock()
    selected_item.get_string.return_value = "gfxterm (graphique)"
    controller.grub_terminal_dropdown.get_selected_item.return_value = selected_item
    controller.notebook = None

    # Ne doit pas lever d'exception
    _on_terminal_mode_changed(controller)

    # Le dropdown gfxmode doit quand même être activé
    controller.gfxmode_dropdown.set_sensitive.assert_called_once_with(True)
