
from ui.ui_constants import *

def test_constants_exist():
    # Just access some constants to ensure they are loaded
    assert COLOR_BUTTON_SIZE == 50
    assert COLOR_PRESETS["white"] == "#FFFFFF"
    assert DEFAULT_RESOLUTION == "auto"
    assert MSG_NO_THEME_SELECTED == "Veuillez sélectionner un thème"
    assert ICON_ACTIVE == "✓"
