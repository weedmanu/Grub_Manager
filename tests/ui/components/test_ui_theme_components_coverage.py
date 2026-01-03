
import pytest
from unittest.mock import MagicMock, patch
from gi.repository import Gtk
import os

# Set headless backend for GTK
os.environ["GDK_BACKEND"] = "headless"

from ui.components.ui_theme_components import ResolutionSelector, ImageScaleSelector, TextEntry

def test_resolution_selector():
    callback = MagicMock()
    selector = ResolutionSelector("1920x1080", callback=callback)
    assert selector.get_resolution() == "1920x1080"
    
    # Change selection
    selector.dropdown.set_selected(0) # 640x480
    selector._on_changed(selector.dropdown, None)
    callback.assert_called_with("640x480")
    
    # Set resolution
    selector.set_resolution("800x600")
    assert selector.get_resolution() == "800x600"
    
    # Set unknown resolution
    selector.set_resolution("unknown")
    assert selector.get_resolution() == "800x600"

def test_resolution_selector_invalid_initial():
    selector = ResolutionSelector("invalid")
    # Should default to first item or stay at 0
    assert selector.get_resolution() == "640x480"

def test_resolution_selector_no_callback():
    selector = ResolutionSelector("1920x1080", callback=None)
    selector._on_changed(selector.dropdown, None)

def test_image_scale_selector():
    callback = MagicMock()
    selector = ImageScaleSelector("fit", callback=callback)
    assert selector.get_method() == "fit"
    
    # Change selection
    selector.dropdown.set_selected(1) # stretch
    selector._on_changed(selector.dropdown, None)
    callback.assert_called_with("stretch")
    
    # Set method
    selector.set_method("crop")
    assert selector.get_method() == "crop"
    
    # Set unknown method
    selector.set_method("unknown")
    assert selector.get_method() == "crop"

def test_image_scale_selector_invalid_initial():
    selector = ImageScaleSelector("invalid")
    assert selector.get_method() == "fit"

def test_image_scale_selector_no_callback():
    selector = ImageScaleSelector("fit", callback=None)
    selector._on_changed(selector.dropdown, None)

def test_text_entry():
    callback = MagicMock()
    entry = TextEntry("Label", "initial", placeholder="hint", callback=callback)
    assert entry.get_text() == "initial"
    
    # Change text
    entry.entry.set_text("new")
    entry._on_changed(entry.entry)
    callback.assert_called_with("new")
    
    # Set text
    entry.set_text("another")
    assert entry.get_text() == "another"

def test_text_entry_no_callback():
    entry = TextEntry("Label", "initial", callback=None)
    entry._on_changed(entry.entry)
