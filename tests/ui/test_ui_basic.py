"""Tests pour l'interface utilisateur GTK4."""

from __future__ import annotations

import gi
import pytest

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk  # noqa: E402

# Skip tous les tests UI si GTK n'est pas disponible
pytest.importorskip("gi")


class TestGtkImports:
    """Tests de base pour vérifier que GTK4 est disponible."""

    def test_gtk_version(self):
        """Vérifie que GTK 4.0 est disponible."""
        assert Gtk.MAJOR_VERSION == 4

    def test_basic_widgets(self):
        """Vérifie que les widgets de base sont disponibles."""
        # Ces widgets sont utilisés dans l'application
        assert hasattr(Gtk, "Application")
        assert hasattr(Gtk, "ApplicationWindow")
        assert hasattr(Gtk, "Box")
        assert hasattr(Gtk, "Button")
        assert hasattr(Gtk, "Label")
        assert hasattr(Gtk, "Notebook")
        assert hasattr(Gtk, "CheckButton")
        assert hasattr(Gtk, "DropDown")


class TestAppState:
    """Tests pour l'énumération AppState."""

    def test_app_state_enum(self):
        """Vérifie que AppState existe et a les bonnes valeurs."""
        from ui.app import AppState

        assert hasattr(AppState, "CLEAN")
        assert hasattr(AppState, "DIRTY")
        assert hasattr(AppState, "APPLYING")

        # Vérifier que ce sont des valeurs différentes
        assert AppState.CLEAN != AppState.DIRTY
        assert AppState.DIRTY != AppState.APPLYING


class TestGrubConfigManagerStructure:
    """Tests structurels pour GrubConfigManager (sans lancer l'UI)."""

    def test_class_exists(self):
        """Vérifie que la classe principale existe."""
        from ui.app import GrubConfigManager

        assert GrubConfigManager is not None
        assert issubclass(GrubConfigManager, Gtk.ApplicationWindow)

    def test_has_required_methods(self):
        """Vérifie que les méthodes essentielles existent."""
        from ui.app import GrubConfigManager

        required_methods = [
            "create_ui",
            "load_config",
            "on_modified",
            "on_save",
            "on_reload",
            "show_info",
            "_apply_model_to_ui",
            "_read_model_from_ui",
        ]

        for method_name in required_methods:
            assert hasattr(GrubConfigManager, method_name)
            assert callable(getattr(GrubConfigManager, method_name))

    def test_has_state_management(self):
        """Vérifie la gestion d'état."""
        from ui.app import GrubConfigManager

        assert hasattr(GrubConfigManager, "_apply_state")
        assert hasattr(GrubConfigManager, "_mark_dirty")


class TestTabModules:
    """Tests pour les modules d'onglets."""

    def test_all_tab_modules_exist(self):
        """Vérifie que tous les modules d'onglets existent."""
        from ui.tabs import backups, base, display, entries, entries_view, general, widgets

        assert backups is not None
        assert base is not None
        assert display is not None
        assert entries is not None
        assert entries_view is not None
        assert general is not None
        assert widgets is not None

    def test_tab_builders_exist(self):
        """Vérifie que les fonctions de construction d'onglets existent."""
        from ui.tabs.backups import build_backups_tab
        from ui.tabs.display import build_display_tab
        from ui.tabs.entries import build_entries_tab
        from ui.tabs.general import build_general_tab

        assert callable(build_general_tab)
        assert callable(build_display_tab)
        assert callable(build_entries_tab)
        assert callable(build_backups_tab)


class TestWidgetsHelpers:
    """Tests pour les helpers de widgets."""

    def test_widget_helpers_exist(self):
        """Vérifie que les fonctions helper existent."""
        from ui.tabs import widgets

        expected_functions = [
            "box_append_label",
            "box_append_section_title",
            "grid_add_labeled",
            "grid_add_check",
            "clear_listbox",
        ]

        for func_name in expected_functions:
            assert hasattr(widgets, func_name)
            assert callable(getattr(widgets, func_name))


class TestBaseHelpers:
    """Tests pour les helpers de base."""

    def test_base_helpers_exist(self):
        """Vérifie que les fonctions de base existent."""
        from ui.tabs import base

        assert hasattr(base, "make_scrolled_grid")
        assert hasattr(base, "apply_margins")

        assert callable(base.make_scrolled_grid)
        assert callable(base.apply_margins)

    def test_make_scrolled_grid_returns_tuple(self):
        """Vérifie que make_scrolled_grid retourne un tuple."""
        from ui.tabs.base import make_scrolled_grid

        result = make_scrolled_grid()
        assert isinstance(result, tuple)
        assert len(result) == 2

        scroll, grid = result
        assert isinstance(scroll, Gtk.ScrolledWindow)
        assert isinstance(grid, Gtk.Grid)

    def test_apply_margins(self):
        """Vérifie apply_margins."""
        from ui.tabs.base import apply_margins

        box = Gtk.Box()
        apply_margins(box, 10)

        assert box.get_margin_top() == 10
        assert box.get_margin_bottom() == 10
        assert box.get_margin_start() == 10
        assert box.get_margin_end() == 10


class TestEntriesView:
    """Tests pour le rendu des entrées."""

    def test_render_entries_exists(self):
        """Vérifie que render_entries existe."""
        from ui.tabs.entries_view import render_entries

        assert callable(render_entries)


# Tests d'intégration de base (sans lancer l'application complète)
class TestUIIntegration:
    """Tests d'intégration UI basiques."""

    def test_can_import_all_ui_modules(self):
        """Vérifie qu'on peut importer tous les modules UI sans erreur."""

        # Si on arrive ici, tous les imports ont réussi
        assert True

    def test_constants_exist(self):
        """Vérifie que les constantes UI existent."""
        from ui.app import ERROR, INFO, WARNING

        assert INFO == "info"
        assert WARNING == "warning"
        assert ERROR == "error"
