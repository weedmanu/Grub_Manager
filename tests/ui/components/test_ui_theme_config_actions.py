"""Tests pour ui_theme_config_actions.

Objectif: exécuter les callbacks internes (_on_activate_clicked/_on_preview_clicked)
qui appellent les handlers injectés.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import gi

gi.require_version("Gtk", "4.0")
import pytest

from ui.components.ui_theme_config_actions import build_theme_config_right_column


class TestBuildThemeConfigRightColumn:
    """Tests pour build_theme_config_right_column."""

    @pytest.fixture
    def mock_gtk(self):
        """Mock pour les composants GTK utilisés par ce module."""
        with patch("ui.components.ui_theme_config_actions.Gtk") as mock_gtk:
            actions_title = MagicMock()
            global_title = MagicMock()
            mock_gtk.Label.side_effect = [actions_title, global_title]

            actions_box = MagicMock()
            global_actions_box = MagicMock()
            mock_gtk.Box.side_effect = [actions_box, global_actions_box]

            sep_actions = MagicMock()
            mock_gtk.Separator.return_value = sep_actions

            activate_btn = MagicMock()
            preview_btn = MagicMock()
            edit_btn = MagicMock()
            delete_btn = MagicMock()
            editor_btn = MagicMock()
            mock_gtk.Button.side_effect = [activate_btn, preview_btn, edit_btn, delete_btn, editor_btn]

            yield {
                "gtk": mock_gtk,
                "activate_btn": activate_btn,
                "preview_btn": preview_btn,
            }

    def test_activate_and_preview_handlers_called(self, mock_gtk):
        """Les handlers injectés sont appelés via les callbacks internes."""
        on_activate = MagicMock()
        on_preview = MagicMock()

        parts = build_theme_config_right_column(
            on_activate=on_activate,
            on_preview=on_preview,
            on_edit=MagicMock(),
            on_delete=MagicMock(),
            on_open_editor=MagicMock(),
        )

        # Récupère les callbacks branchés via connect("clicked", <handler>)
        activate_handler = mock_gtk["activate_btn"].connect.call_args.args[1]
        preview_handler = mock_gtk["preview_btn"].connect.call_args.args[1]

        activate_handler(MagicMock())
        preview_handler(MagicMock())

        on_activate.assert_called_once_with()
        on_preview.assert_called_once_with()

        # sanity: les widgets clés sont exposés
        assert parts.activate_btn is mock_gtk["activate_btn"]
        assert parts.preview_btn is mock_gtk["preview_btn"]
