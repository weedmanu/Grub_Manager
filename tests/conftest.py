import os
import sys
from unittest.mock import MagicMock

# Désactiver les avertissements de version GTK
import gi
try:
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
except (ValueError, ImportError):
    pass

from gi.repository import Gtk, Adw

def pytest_configure(config):
    """Configuration globale de pytest."""
    # Forcer un backend headless pour GDK si possible
    os.environ["GDK_BACKEND"] = "headless"
    
    # Mocker Gtk.init pour éviter les plantages sans display
    Gtk.init = MagicMock(return_value=True)
    
    # Mocker Adw.init
    try:
        Adw.init = MagicMock(return_value=True)
    except:
        pass

    # Empêcher les fenêtres de s'afficher réellement
    Gtk.Window.present = MagicMock()
    Gtk.Window.show = MagicMock()
    
    print("\n[Conftest] GTK/Adw sécurisés pour les tests (Headless mode)")
