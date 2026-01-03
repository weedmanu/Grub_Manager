"""Tests additionnels pour atteindre 100% de couverture du modèle."""

from __future__ import annotations

from core.models.core_grub_ui_model import (
    GrubUiModel,
    merged_config_from_model,
    model_from_config,
)


def test_model_from_config_quiet_and_splash_variations() -> None:
    """Test les différentes variations de quiet et splash dans GRUB_CMDLINE_LINUX_DEFAULT."""
    # Cas 1: Aucun des deux
    cfg1 = {"GRUB_CMDLINE_LINUX_DEFAULT": ""}
    model1 = model_from_config(cfg1)
    assert model1.quiet is False
    assert model1.splash is False

    # Cas 2: Juste quiet
    cfg2 = {"GRUB_CMDLINE_LINUX_DEFAULT": "quiet"}
    model2 = model_from_config(cfg2)
    assert model2.quiet is True
    assert model2.splash is False

    # Cas 3: Juste splash
    cfg3 = {"GRUB_CMDLINE_LINUX_DEFAULT": "splash"}
    model3 = model_from_config(cfg3)
    assert model3.quiet is False
    assert model3.splash is True

    # Cas 4: Les deux dans un ordre différent
    cfg4 = {"GRUB_CMDLINE_LINUX_DEFAULT": "splash quiet root=/dev/sda1"}
    model4 = model_from_config(cfg4)
    assert model4.quiet is True
    assert model4.splash is True


def test_model_from_config_empty_default_value() -> None:
    """Test quand GRUB_DEFAULT est une chaîne vide ou whitespace-only."""
    cfg_empty = {"GRUB_DEFAULT": ""}
    model_empty = model_from_config(cfg_empty)
    assert model_empty.default == "0"

    cfg_space = {"GRUB_DEFAULT": "   "}
    model_space = model_from_config(cfg_space)
    assert model_space.default == "0"


def test_model_from_config_non_menu_timeout_style() -> None:
    """Test GRUB_TIMEOUT_STYLE avec valeurs autres que hidden."""
    cfg = {"GRUB_TIMEOUT_STYLE": "menu"}
    model = model_from_config(cfg)
    assert model.hidden_timeout is False

    cfg2 = {"GRUB_TIMEOUT_STYLE": "countdown"}
    model2 = model_from_config(cfg2)
    assert model2.hidden_timeout is False


def test_merged_config_no_cmdline_when_both_false() -> None:
    """Test que GRUB_CMDLINE_LINUX_DEFAULT n'est pas présente si quiet=False et splash=False."""
    model = GrubUiModel(quiet=False, splash=False)
    merged = merged_config_from_model({}, model)
    assert "GRUB_CMDLINE_LINUX_DEFAULT" not in merged


def test_merged_config_save_default_with_saved_default() -> None:
    """Test que GRUB_SAVEDEFAULT est activé si model.default == 'saved'."""
    model = GrubUiModel(default="saved", save_default=False)
    merged = merged_config_from_model({}, model)
    assert merged["GRUB_SAVEDEFAULT"] == "true"
    assert merged["GRUB_DEFAULT"] == "saved"


def test_merged_config_grub_theme_with_whitespace() -> None:
    """Test que le thème n'est pas présent si c'est juste des espaces."""
    model = GrubUiModel(grub_theme="   ")
    merged = merged_config_from_model({}, model)
    assert "GRUB_THEME" not in merged


def test_merged_config_grub_theme_with_value() -> None:
    """Test que le thème est présent et trimmé si défini."""
    model = GrubUiModel(grub_theme="  /boot/grub/themes/mytheme/theme.txt  ")
    merged = merged_config_from_model({}, model)
    assert merged["GRUB_THEME"] == "/boot/grub/themes/mytheme/theme.txt"


def test_model_timeout_conversion_edge_cases() -> None:
    """Test les cas limites de conversion du timeout."""
    # Timeout négatif
    cfg = {"GRUB_TIMEOUT": "-5"}
    model = model_from_config(cfg)
    assert model.timeout == -5

    # Très grand nombre
    cfg2 = {"GRUB_TIMEOUT": "999"}
    model2 = model_from_config(cfg2)
    assert model2.timeout == 999

    # Flottant
    cfg3 = {"GRUB_TIMEOUT": "3.5"}
    model3 = model_from_config(cfg3)
    assert model3.timeout == 5  # Défaut car ValueError


def test_merged_config_only_quiet() -> None:
    """Test GRUB_CMDLINE_LINUX_DEFAULT avec seulement quiet."""
    model = GrubUiModel(quiet=True, splash=False)
    merged = merged_config_from_model({}, model)
    assert merged["GRUB_CMDLINE_LINUX_DEFAULT"] == "quiet"


def test_merged_config_only_splash() -> None:
    """Test GRUB_CMDLINE_LINUX_DEFAULT avec seulement splash."""
    model = GrubUiModel(quiet=False, splash=True)
    merged = merged_config_from_model({}, model)
    assert merged["GRUB_CMDLINE_LINUX_DEFAULT"] == "splash"
