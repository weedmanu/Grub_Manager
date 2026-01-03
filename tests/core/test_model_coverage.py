"""Tests de couverture pour core/models/core_grub_ui_model.py."""

from unittest.mock import patch, MagicMock
from core.models.core_grub_ui_model import (
    GrubUiModel, 
    model_from_config, 
    merged_config_from_model,
    load_grub_ui_state,
    save_grub_ui_state,
    GrubUiState
)

def test_model_from_config_cmdline_variants():
    """Test model_from_config avec différentes variantes de CMDLINE."""
    # Cas sans quiet/splash
    cfg = {"GRUB_CMDLINE_LINUX_DEFAULT": "nomodeset"}
    model = model_from_config(cfg)
    assert model.quiet is False
    assert model.splash is False
    
    # Cas avec quiet seulement
    cfg = {"GRUB_CMDLINE_LINUX_DEFAULT": "quiet nomodeset"}
    model = model_from_config(cfg)
    assert model.quiet is True
    assert model.splash is False
    
    # Cas avec splash seulement
    cfg = {"GRUB_CMDLINE_LINUX_DEFAULT": "splash nomodeset"}
    model = model_from_config(cfg)
    assert model.quiet is False
    assert model.splash is True

def test_merged_config_all_branches():
    """Test toutes les branches de merged_config_from_model."""
    # Cas où tout est activé
    model = GrubUiModel(
        save_default=True,
        disable_submenu=True,
        disable_recovery=True,
        disable_os_prober=True,
        grub_theme="/boot/grub/themes/mytheme/theme.txt"
    )
    merged = merged_config_from_model({}, model)
    assert merged["GRUB_SAVEDEFAULT"] == "true"
    assert merged["GRUB_DISABLE_SUBMENU"] == "y"
    assert merged["GRUB_DISABLE_RECOVERY"] == "true"
    assert merged["GRUB_DISABLE_OS_PROBER"] == "true"
    assert merged["GRUB_THEME"] == "/boot/grub/themes/mytheme/theme.txt"
    
    # Cas où tout est désactivé (vérifier suppression des clés si présentes dans base)
    base = {
        "GRUB_SAVEDEFAULT": "true",
        "GRUB_DISABLE_SUBMENU": "y",
        "GRUB_DISABLE_RECOVERY": "true",
        "GRUB_DISABLE_OS_PROBER": "true",
        "GRUB_THEME": "/old/theme"
    }
    model = GrubUiModel(
        save_default=False,
        disable_submenu=False,
        disable_recovery=False,
        disable_os_prober=False,
        grub_theme=""
    )
    merged = merged_config_from_model(base, model)
    assert "GRUB_SAVEDEFAULT" not in merged
    assert "GRUB_DISABLE_SUBMENU" not in merged
    assert "GRUB_DISABLE_RECOVERY" not in merged
    assert "GRUB_DISABLE_OS_PROBER" not in merged
    assert "GRUB_THEME" not in merged

    # Cas où tout est désactivé et absent de base (pour couvrir les branches else)
    merged_empty = merged_config_from_model({}, model)
    assert "GRUB_SAVEDEFAULT" not in merged_empty
    assert "GRUB_DISABLE_SUBMENU" not in merged_empty
    assert "GRUB_DISABLE_RECOVERY" not in merged_empty
    assert "GRUB_DISABLE_OS_PROBER" not in merged_empty
    assert "GRUB_THEME" not in merged_empty

def test_load_grub_ui_state():
    """Test load_grub_ui_state."""
    with (
        patch("core.models.core_grub_ui_model.read_grub_default", return_value={"GRUB_TIMEOUT": "10"}),
        patch("core.models.core_grub_ui_model.read_grub_default_choices_with_source", return_value=([], "/boot/grub/grub.cfg"))
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
        # Vérifier que le timeout a été mis à jour dans l'appel
        saved_config = mock_write.call_args[0][0]
        assert saved_config["GRUB_TIMEOUT"] == "15"
