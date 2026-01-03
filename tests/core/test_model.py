from __future__ import annotations

from core.model import (
    GrubUiModel,
    merged_config_from_model,
    model_from_config,
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
    assert model.color_normal_fg == "white"
    assert model.color_normal_bg == "black"
    assert model.color_highlight_fg == "yellow"
    assert model.color_highlight_bg == "blue"


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
        color_normal_fg="light-gray",
        color_normal_bg="black",
        color_highlight_fg="yellow",
        color_highlight_bg="blue",
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
    assert merged["GRUB_COLOR_NORMAL"] == "light-gray/black"
    assert merged["GRUB_COLOR_HIGHLIGHT"] == "yellow/blue"

    # A disabled flag should not be present.
    assert "GRUB_DISABLE_RECOVERY" not in merged
