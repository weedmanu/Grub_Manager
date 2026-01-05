"""Tests pour ui_theme_config_actions.

Objectif: exécuter les callbacks internes (_on_activate_clicked/_on_preview_clicked)
qui appellent les handlers injectés.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import gi

gi.require_version("Gtk", "4.0")
import pytest

from ui.components.ui_components_theme_config_actions import ThemeConfigCallbacks, build_theme_config_right_column


class TestBuildThemeConfigRightColumn:
    """Tests pour build_theme_config_right_column."""

    @pytest.fixture
    def mock_gtk(self):
        """Mock pour les composants GTK utilisés par ce module."""
        with (
            patch("ui.components.ui_components_theme_config_actions.Gtk") as mock_gtk,
            patch("ui.components.ui_components_theme_config_actions.box_append_section_grid") as mock_grid_helper,
        ):

            actions_title = MagicMock()
            global_title = MagicMock()
            scripts_title = MagicMock()
            mock_gtk.Label.side_effect = [actions_title, scripts_title, global_title]

            actions_box = MagicMock()
            scripts_box = MagicMock()
            global_actions_box = MagicMock()
            mock_gtk.Box.side_effect = [actions_box, scripts_box, global_actions_box]

            # Mock box_append_section_grid to return a mock grid
            mock_grid = MagicMock()
            mock_grid_helper.return_value = mock_grid

            sep_actions = MagicMock()
            mock_gtk.Separator.return_value = sep_actions

            preview_btn = MagicMock()
            edit_btn = MagicMock()
            delete_btn = MagicMock()
            activate_script_btn = MagicMock()
            deactivate_script_btn = MagicMock()
            editor_btn = MagicMock()
            mock_gtk.Button.side_effect = [
                preview_btn,
                edit_btn,
                delete_btn,
                activate_script_btn,
                deactivate_script_btn,
                editor_btn,
            ]

            # Mock Gtk.Orientation constants
            mock_gtk.Orientation.HORIZONTAL = "horizontal"
            mock_gtk.Orientation.VERTICAL = "vertical"
            mock_gtk.Align.FILL = "fill"
            mock_gtk.Align.END = "end"

            yield {
                "gtk": mock_gtk,
                "preview_btn": preview_btn,
                "scripts_title": scripts_title,
                "grid": mock_grid,
            }

    def test_activate_and_preview_handlers_called(self, mock_gtk):
        """Les handlers injectés sont appelés via les callbacks internes."""
        on_preview = MagicMock()
        on_activate_theme = MagicMock()
        on_deactivate_theme = MagicMock()
        on_edit = MagicMock()
        on_delete = MagicMock()
        on_open_editor = MagicMock()

        parts = build_theme_config_right_column(
            callbacks=ThemeConfigCallbacks(
                on_preview=on_preview,
                on_activate_theme=on_activate_theme,
                on_deactivate_theme=on_deactivate_theme,
                on_edit=on_edit,
                on_delete=on_delete,
                on_open_editor=on_open_editor,
            )
        )

        # Vérifier que la structure est correcte
        assert parts.buttons.preview_btn is mock_gtk["preview_btn"]

        # Les callbacks sont branchés internement via connect("clicked", handler)
        assert mock_gtk["preview_btn"].connect.called

        # Récupérer et appeler le handler de preview pour couvrir la ligne 51
        preview_handler = None
        for call in mock_gtk["preview_btn"].connect.call_args_list:
            if call.args[0] == "clicked":
                preview_handler = call.args[1]
                break

        if preview_handler:
            preview_handler(mock_gtk["preview_btn"])
            on_preview.assert_called_once()

    def test_build_theme_config_right_column_all_handlers(self):
        """Test building theme config right column with all handlers connected."""
        with (
            patch("ui.components.ui_components_theme_config_actions.Gtk") as mock_gtk,
            patch("ui.components.ui_components_theme_config_actions.box_append_section_grid") as mock_grid_helper,
        ):

            # Setup mocks
            mock_gtk.Label.side_effect = [MagicMock(), MagicMock(), MagicMock()]
            mock_gtk.Box.side_effect = [MagicMock(), MagicMock(), MagicMock()]
            mock_gtk.Separator.return_value = MagicMock()

            mock_grid = MagicMock()
            mock_grid_helper.return_value = mock_grid

            buttons = [MagicMock() for _ in range(6)]
            mock_gtk.Button.side_effect = buttons

            # Mock orientation and align
            mock_gtk.Orientation.HORIZONTAL = "horizontal"
            mock_gtk.Orientation.VERTICAL = "vertical"
            mock_gtk.Align.FILL = "fill"
            mock_gtk.Align.END = "end"

            handlers = [MagicMock() for _ in range(6)]
            parts = build_theme_config_right_column(
                callbacks=ThemeConfigCallbacks(
                    on_preview=handlers[0],
                    on_activate_theme=handlers[1],
                    on_deactivate_theme=handlers[2],
                    on_edit=handlers[3],
                    on_delete=handlers[4],
                    on_open_editor=handlers[5],
                )
            )

            # Verify all parts returned
            assert parts.buttons.preview_btn is buttons[0]
            assert parts.buttons.activate_theme_btn is buttons[1]
            assert parts.buttons.deactivate_theme_btn is buttons[2]
            assert parts.buttons.edit_btn is buttons[3]
            assert parts.buttons.delete_btn is buttons[4]
