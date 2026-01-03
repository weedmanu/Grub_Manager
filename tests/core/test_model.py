from __future__ import annotations

from core.models.core_grub_ui_model import (
    GrubUiModel,
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
        "GRUB_COLOR_NORMAL": "white/black",
        "GRUB_COLOR_HIGHLIGHT": "yellow/blue",
    }

    model = model_from_config(cfg)
    assert model.timeout == 7
    assert model.default == "saved"
    assert model.hidden_timeout is True
    assert model.save_default is True
    assert model.disable_submenu is True
    assert model.disable_recovery is True
    assert model.disable_os_prober is True
    assert model.gfxmode == "1920x1080"
    assert model.gfxpayload_linux == "keep"
    assert model.terminal_color is True
    # Color attributes removed - now managed by theme system


def test_merged_config_preserves_unknown_keys_and_replaces_managed() -> None:
    base = {
        "GRUB_TIMEOUT": "5",
        "GRUB_DEFAULT": "0",
        "SOME_UNKNOWN": "keepme",
        "GRUB_DISABLE_RECOVERY": "true",
        "GRUB_COLOR_NORMAL": "red/black",
    }

    model = GrubUiModel(
        timeout=3,
        default="1>2",
        save_default=True,
        hidden_timeout=False,
        gfxmode="1024x768",
        gfxpayload_linux="text",
        disable_submenu=False,
        disable_recovery=False,
        disable_os_prober=False,
        terminal_color=True,
    )

    merged = merged_config_from_model(base, model)

    # Unknown keys are preserved.
    assert merged["SOME_UNKNOWN"] == "keepme"

    # Managed keys are set from the model.
    assert merged["GRUB_TIMEOUT"] == "3"
    assert merged["GRUB_DEFAULT"] == "1>2"
    assert merged["GRUB_TIMEOUT_STYLE"] == "menu"
    assert merged["GRUB_SAVEDEFAULT"] == "true"
    assert merged["GRUB_GFXMODE"] == "1024x768"
    assert merged["GRUB_GFXPAYLOAD_LINUX"] == "text"
    assert merged["GRUB_TERMINAL"] == "console"
    # Color attributes removed - now managed by theme system

    # A disabled flag should not be present.
    assert "GRUB_DISABLE_RECOVERY" not in merged


def test_model_from_config_invalid_int() -> None:
    """Test conversion int avec valeur invalide."""
    cfg = {"GRUB_TIMEOUT": "invalid"}
    model = model_from_config(cfg)
    assert model.timeout == 5  # Valeur par défaut


def test_merged_config_empty_strings() -> None:
    """Test fusion avec chaînes vides pour les options graphiques."""
    model = GrubUiModel(gfxmode="  ", gfxpayload_linux="")
    merged = merged_config_from_model({}, model)
    assert "GRUB_GFXMODE" not in merged
    assert "GRUB_GFXPAYLOAD_LINUX" not in merged


def test_merged_config_all_flags() -> None:
    """Test fusion avec tous les drapeaux activés."""
    model = GrubUiModel(
        save_default=True, disable_submenu=True, disable_recovery=True, disable_os_prober=True, terminal_color=True
    )
    merged = merged_config_from_model({}, model)
    assert merged["GRUB_SAVEDEFAULT"] == "true"
    assert merged["GRUB_DISABLE_SUBMENU"] == "y"
    assert merged["GRUB_DISABLE_RECOVERY"] == "true"
    assert merged["GRUB_DISABLE_OS_PROBER"] == "true"
    assert merged["GRUB_TERMINAL"] == "console"


def test_load_save_grub_ui_state(tmp_path, monkeypatch) -> None:
    """Test chargement et sauvegarde de l'état complet."""
    grub_default = tmp_path / "grub"
    grub_cfg = tmp_path / "grub.cfg"

    grub_default.write_text("GRUB_TIMEOUT=5\n", encoding="utf-8")
    grub_cfg.write_text("menuentry 'Ubuntu' --id ubuntu {\n}\n", encoding="utf-8")

    from unittest.mock import patch

    # On mocke les fonctions IO pour éviter de dépendre de leur implémentation exacte ici
    with (
        patch("core.models.core_grub_ui_model.read_grub_default") as mock_read_default,
        patch("core.models.core_grub_ui_model.read_grub_default_choices_with_source") as mock_read_choices,
        patch("core.models.core_grub_ui_model.write_grub_default") as mock_write_default,
    ):

        mock_read_default.return_value = {"GRUB_TIMEOUT": "5"}
        from core.io.core_grub_menu_parser import GrubDefaultChoice

        mock_read_choices.return_value = ([GrubDefaultChoice("ubuntu", "Ubuntu")], str(grub_cfg))
        mock_write_default.return_value = str(grub_default) + ".bak"

        # Test Load
        state = load_grub_ui_state(str(grub_default), str(grub_cfg))
        assert state.model.timeout == 5
        assert len(state.entries) == 1
        assert state.entries[0].title == "Ubuntu"

        # Test Save
        new_model = GrubUiModel(timeout=10)
        backup = save_grub_ui_state(state, new_model, str(grub_default))
        assert backup == str(grub_default) + ".bak"
        mock_write_default.assert_called_once()
        # Vérifier que le timeout a été mis à jour dans l'appel à write_grub_default
        args, _ = mock_write_default.call_args
        assert args[0]["GRUB_TIMEOUT"] == "10"
