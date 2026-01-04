"""Tests pour le modèle de données GRUB UI."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from unittest.mock import patch

import core.io.core_grub_menu_parser as grub_menu
from core.models.core_grub_ui_model import (
    GrubUiModel,
    GrubUiState,
    load_grub_ui_state,
    merged_config_from_model,
    model_from_config,
    save_grub_ui_state,
)


def test_model_from_config_defaults_and_flags() -> None:
    cfg = {
        "GRUB_TIMEOUT": "7",
        "GRUB_DEFAULT": "saved",
        "GRUB_TIMEOUT_STYLE": "hidden",
        "GRUB_SAVEDEFAULT": "true",
        "GRUB_DISABLE_SUBMENU": "y",
        "GRUB_DISABLE_RECOVERY": "true",
        "GRUB_DISABLE_OS_PROBER": "true",
        "GRUB_GFXMODE": "1920x1080",
        "GRUB_GFXPAYLOAD_LINUX": "keep",
        "GRUB_TERMINAL": "console",
    }

    model = model_from_config(cfg)
    assert model.timeout == 7
    assert model.default == "saved"
    assert model.hidden_timeout is True
    assert model.save_default is True
    assert model.disable_os_prober is True
    assert model.gfxmode == "1920x1080"
    assert model.gfxpayload_linux == "keep"


def test_model_from_config_invalid_int() -> None:
    """Test conversion int avec valeur invalide."""
    cfg = {"GRUB_TIMEOUT": "invalid"}
    model = model_from_config(cfg)
    assert model.timeout == 5  # Valeur par défaut


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

    # Cas 4: Les deux
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


def test_merged_config_preserves_unknown_keys_and_replaces_managed() -> None:
    base = {
        "GRUB_TIMEOUT": "5",
        "GRUB_DEFAULT": "0",
        "SOME_UNKNOWN": "keepme",
        "GRUB_DISABLE_RECOVERY": "true",
    }

    model = GrubUiModel(
        timeout=3,
        default="1>2",
        save_default=True,
        hidden_timeout=False,
        gfxmode="1024x768",
        gfxpayload_linux="text",
        disable_os_prober=False,
    )

    merged = merged_config_from_model(base, model)

    assert merged["SOME_UNKNOWN"] == "keepme"
    assert merged["GRUB_TIMEOUT"] == "3"
    assert merged["GRUB_DEFAULT"] == "1>2"
    assert merged["GRUB_TIMEOUT_STYLE"] == "menu"
    assert merged["GRUB_SAVEDEFAULT"] == "true"
    assert merged["GRUB_GFXMODE"] == "1024x768"
    assert merged["GRUB_GFXPAYLOAD_LINUX"] == "text"
    assert merged["GRUB_DISABLE_RECOVERY"] == "true"


def test_merged_config_empty_strings() -> None:
    """Test fusion avec chaînes vides pour les options graphiques."""
    model = GrubUiModel(gfxmode="  ", gfxpayload_linux="")
    merged = merged_config_from_model({}, model)
    assert "GRUB_GFXMODE" not in merged
    assert "GRUB_GFXPAYLOAD_LINUX" not in merged


def test_merged_config_all_flags() -> None:
    """Test fusion avec tous les drapeaux activés."""
    model = GrubUiModel(save_default=True, disable_os_prober=True)
    merged = merged_config_from_model({}, model)
    assert merged["GRUB_SAVEDEFAULT"] == "true"
    assert merged["GRUB_DISABLE_OS_PROBER"] == "true"


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


def test_disable_os_prober_persistence_when_false() -> None:
    """Vérifie que DISABLE_OS_PROBER est bien absent si désactivé."""
    base_config = {
        "GRUB_TIMEOUT": "5",
        "GRUB_DEFAULT": "0",
        "GRUB_DISABLE_OS_PROBER": "true",
    }
    model = GrubUiModel(timeout=5, default="0", disable_os_prober=False)
    merged = merged_config_from_model(base_config, model)
    assert "GRUB_DISABLE_OS_PROBER" not in merged


def test_disable_recovery_is_preserved_when_present() -> None:
    """GRUB_DISABLE_RECOVERY n'est plus géré: il doit être préservé tel quel."""
    base = {"GRUB_TIMEOUT": "5", "GRUB_DEFAULT": "0", "GRUB_DISABLE_RECOVERY": "true"}
    model = model_from_config(base)
    merged = merged_config_from_model(base, model)
    assert merged["GRUB_DISABLE_RECOVERY"] == "true"


def test_load_grub_ui_state():
    """Test load_grub_ui_state."""
    with (
        patch("core.models.core_grub_ui_model.read_grub_default", return_value={"GRUB_TIMEOUT": "10"}),
        patch(
            "core.models.core_grub_ui_model.read_grub_default_choices_with_source",
            return_value=([], "/boot/grub/grub.cfg"),
        ),
    ):
        state = load_grub_ui_state()
        assert isinstance(state, GrubUiState)
        assert state.model.timeout == 10
        assert state.raw_config["GRUB_TIMEOUT"] == "10"


def test_save_grub_ui_state():
    """Test save_grub_ui_state."""
    model = GrubUiModel(timeout=15)
    state = GrubUiState(model=model, entries=[], raw_config={"GRUB_TIMEOUT": "10"})

    with patch("core.models.core_grub_ui_model.write_grub_default", return_value="/path/to/backup") as mock_write:
        result = save_grub_ui_state(state, model)
        assert result == "/path/to/backup"
        mock_write.assert_called_once()
        saved_config = mock_write.call_args[0][0]
        assert saved_config["GRUB_TIMEOUT"] == "15"


def test_load_state_uses_actual_grub_cfg_for_color_fallback(tmp_path: Path, monkeypatch) -> None:
    grub1 = tmp_path / "grub.cfg"
    grub2 = tmp_path / "grub2.cfg"

    grub2.write_text(
        """
set menu_color_normal=white/black
set menu_color_highlight=black/light-gray
menuentry 'Linux' $menuentry_id_option 'id-1' { }
""".lstrip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(grub_menu, "GRUB_CFG_PATH", str(grub1))
    monkeypatch.setattr(grub_menu, "GRUB_CFG_PATHS", [str(grub1), str(grub2)])

    grub_default = tmp_path / "default_grub"
    grub_default.write_text("GRUB_TIMEOUT=5\nGRUB_DEFAULT=0\n", encoding="utf-8")

    state = load_grub_ui_state(grub_default_path=str(grub_default), grub_cfg_path=str(grub1))
    assert state.model.timeout == 5
    assert state.model.default == "0"


def test_load_save_grub_ui_state_roundtrip(tmp_path, monkeypatch) -> None:
    """Test chargement et sauvegarde de l'état complet."""
    grub_default = tmp_path / "grub"
    grub_default.write_text("GRUB_TIMEOUT=5\nGRUB_DEFAULT=0\n", encoding="utf-8")

    grub_cfg = tmp_path / "grub.cfg"
    grub_cfg.write_text("menuentry 'Linux' { }", encoding="utf-8")

    state = load_grub_ui_state(grub_default_path=str(grub_default), grub_cfg_path=str(grub_cfg))
    assert state.model.timeout == 5

    updated_model = dataclasses.replace(state.model, timeout=10)
    save_grub_ui_state(state, updated_model, grub_default_path=str(grub_default))

    new_state = load_grub_ui_state(grub_default_path=str(grub_default), grub_cfg_path=str(grub_cfg))
    assert new_state.model.timeout == 10
