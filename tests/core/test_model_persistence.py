"""Tests de persistance des options booléennes dans le modèle GRUB."""

from __future__ import annotations

from core.model import GrubUiModel, merged_config_from_model, model_from_config


def test_disable_os_prober_persistence_when_false() -> None:
    """Vérifie que DISABLE_OS_PROBER est bien absent si désactivé."""
    base_config = {
        "GRUB_TIMEOUT": "5",
        "GRUB_DEFAULT": "0",
        "GRUB_DISABLE_OS_PROBER": "true",  # Présent initialement
    }

    model = GrubUiModel(
        timeout=5,
        default="0",
        disable_os_prober=False,  # On désactive
    )

    merged = merged_config_from_model(base_config, model)

    # La clé doit être ABSENTE (supprimée)
    assert "GRUB_DISABLE_OS_PROBER" not in merged
    assert merged["GRUB_TIMEOUT"] == "5"
    assert merged["GRUB_DEFAULT"] == "0"


def test_disable_os_prober_persistence_when_true() -> None:
    """Vérifie que DISABLE_OS_PROBER est bien présent si activé."""
    base_config = {
        "GRUB_TIMEOUT": "5",
        "GRUB_DEFAULT": "0",
        # GRUB_DISABLE_OS_PROBER absent (os-prober activé)
    }

    model = GrubUiModel(
        timeout=5,
        default="0",
        disable_os_prober=True,  # On active la désactivation
    )

    merged = merged_config_from_model(base_config, model)

    # La clé doit être PRÉSENTE
    assert merged["GRUB_DISABLE_OS_PROBER"] == "true"


def test_disable_recovery_toggle() -> None:
    """Vérifie le toggle recovery on->off->on."""
    base = {"GRUB_TIMEOUT": "5", "GRUB_DISABLE_RECOVERY": "true"}

    # 1. État initial: recovery désactivé
    model = model_from_config(base)
    assert model.disable_recovery is True

    # 2. On réactive recovery
    model_enabled = GrubUiModel(
        timeout=model.timeout,
        default=model.default,
        disable_recovery=False,
    )
    merged = merged_config_from_model(base, model_enabled)
    assert "GRUB_DISABLE_RECOVERY" not in merged

    # 3. On relit: doit être False
    model2 = model_from_config(merged)
    assert model2.disable_recovery is False

    # 4. On redésactive
    model_disabled = GrubUiModel(
        timeout=model2.timeout,
        default=model2.default,
        disable_recovery=True,
    )
    merged2 = merged_config_from_model(merged, model_disabled)
    assert merged2["GRUB_DISABLE_RECOVERY"] == "true"


def test_disable_submenu_toggle() -> None:
    """Vérifie le toggle submenu."""
    # Cycle complet: off -> on -> off
    base = {"GRUB_TIMEOUT": "5"}

    # Activer
    model_on = GrubUiModel(timeout=5, default="0", disable_submenu=True)
    merged = merged_config_from_model(base, model_on)
    assert merged["GRUB_DISABLE_SUBMENU"] == "y"

    # Désactiver
    model_off = GrubUiModel(timeout=5, default="0", disable_submenu=False)
    merged2 = merged_config_from_model(merged, model_off)
    assert "GRUB_DISABLE_SUBMENU" not in merged2


def test_terminal_console_toggle() -> None:
    """Vérifie le toggle terminal console."""
    base = {"GRUB_TIMEOUT": "5"}

    # Activer console
    model_console = GrubUiModel(timeout=5, default="0", terminal_color=True)
    merged = merged_config_from_model(base, model_console)
    assert merged["GRUB_TERMINAL"] == "console"

    # Désactiver (retour graphique)
    model_gfx = GrubUiModel(timeout=5, default="0", terminal_color=False)
    merged2 = merged_config_from_model(merged, model_gfx)
    assert "GRUB_TERMINAL" not in merged2


def test_savedefault_auto_with_saved() -> None:
    """Vérifie que SAVEDEFAULT est automatiquement activé si DEFAULT=saved."""
    base = {"GRUB_TIMEOUT": "5"}

    model = GrubUiModel(
        timeout=5,
        default="saved",
        save_default=False,  # Même si explicitement False
    )

    merged = merged_config_from_model(base, model)

    # Doit quand même être présent car GRUB_DEFAULT=saved
    assert merged["GRUB_DEFAULT"] == "saved"
    assert merged["GRUB_SAVEDEFAULT"] == "true"


def test_savedefault_explicit() -> None:
    """Vérifie SAVEDEFAULT explicite sans DEFAULT=saved."""
    base = {"GRUB_TIMEOUT": "5"}

    # save_default=True mais default="0"
    model = GrubUiModel(timeout=5, default="0", save_default=True)
    merged = merged_config_from_model(base, model)
    assert merged["GRUB_SAVEDEFAULT"] == "true"

    # save_default=False et default="0"
    model2 = GrubUiModel(timeout=5, default="0", save_default=False)
    merged2 = merged_config_from_model(base, model2)
    assert "GRUB_SAVEDEFAULT" not in merged2


def test_roundtrip_all_options() -> None:
    """Test de cycle complet: config -> model -> config -> model."""
    original = {
        "GRUB_TIMEOUT": "10",
        "GRUB_DEFAULT": "0",
        "GRUB_TIMEOUT_STYLE": "menu",
        "GRUB_DISABLE_SUBMENU": "y",
        "GRUB_DISABLE_RECOVERY": "true",
        # GRUB_DISABLE_OS_PROBER absent (activé)
        "GRUB_GFXMODE": "1920x1080",
        "GRUB_COLOR_NORMAL": "white/black",
        "GRUB_UNMANAGED_KEY": "keep_me",
    }

    # 1. Charger
    model = model_from_config(original)
    assert model.timeout == 10
    assert model.default == "0"
    assert model.disable_submenu is True
    assert model.disable_recovery is True
    assert model.disable_os_prober is False  # Absent = non désactivé
    assert model.gfxmode == "1920x1080"

    # 2. Sauvegarder
    merged = merged_config_from_model(original, model)
    assert merged["GRUB_TIMEOUT"] == "10"
    assert merged["GRUB_DISABLE_SUBMENU"] == "y"
    assert merged["GRUB_DISABLE_RECOVERY"] == "true"
    assert "GRUB_DISABLE_OS_PROBER" not in merged  # Toujours absent
    assert merged["GRUB_GFXMODE"] == "1920x1080"
    assert merged["GRUB_UNMANAGED_KEY"] == "keep_me"  # Préservé

    # 3. Recharger
    model2 = model_from_config(merged)
    assert model2.timeout == model.timeout
    assert model2.disable_submenu == model.disable_submenu
    assert model2.disable_recovery == model.disable_recovery
    assert model2.disable_os_prober == model.disable_os_prober


def test_preserve_unmanaged_keys() -> None:
    """Vérifie que les clés non gérées sont préservées."""
    base = {
        "GRUB_TIMEOUT": "5",
        "GRUB_CMDLINE_LINUX": "quiet splash",
        "GRUB_CUSTOM_OPTION": "value",
    }

    model = GrubUiModel(timeout=10, default="0")
    merged = merged_config_from_model(base, model)

    # Clés gérées modifiées
    assert merged["GRUB_TIMEOUT"] == "10"

    # Clés non gérées préservées
    assert merged["GRUB_CMDLINE_LINUX"] == "quiet splash"
    assert merged["GRUB_CUSTOM_OPTION"] == "value"
