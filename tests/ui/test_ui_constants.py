from ui.config import ui_config_constants as ui_constants


def test_ui_constants_exist():
    assert ui_constants.COLOR_BUTTON_SIZE == 50
    assert ui_constants.DEFAULT_GRUB_TIMEOUT == 5
    assert "white" in ui_constants.COLOR_PRESETS
    assert ui_constants.COLOR_PRESETS["white"] == "#FFFFFF"
    assert ui_constants.DEFAULT_RESOLUTION == "auto"
    assert ui_constants.MSG_NO_THEME_SELECTED == "Veuillez sélectionner un thème"
    assert ui_constants.ICON_ACTIVE == "Actif"
