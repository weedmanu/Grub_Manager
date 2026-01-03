from ui import ui_constants


def test_ui_constants_exist():
    assert ui_constants.COLOR_BUTTON_SIZE == 50
    assert ui_constants.DEFAULT_GRUB_TIMEOUT == 5
    assert "white" in ui_constants.COLOR_PRESETS
