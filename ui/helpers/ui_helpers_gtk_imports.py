"""Imports GTK4 centralisés.

Objectif:
- Centraliser `gi.require_version(...)` au même endroit.
- Éviter les warnings pylint `wrong-import-position` dans les modules UI.

Ce module doit être importé uniquement par la couche UI.
"""

# ruff: noqa: RUF022
# isort: skip_file

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gio", "2.0")
gi.require_version("Gdk", "4.0")

# pylint: disable=wrong-import-position
from gi.repository import Gdk, Gio, GLib, Gtk, Pango  # noqa: E402

__all__ = ["Gdk", "Gio", "GLib", "Gtk", "Pango"]
