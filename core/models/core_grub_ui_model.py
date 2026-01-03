"""Modèle core pour l'UI et orchestration (lecture/merge/sauvegarde).

But: l'UI ne manipule pas de logique GRUB. Elle ne voit qu'un modèle simple et
appelle le core.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from loguru import logger

from ..config.core_paths import GRUB_CFG_PATH, GRUB_DEFAULT_PATH
from ..io.core_grub_default_io import read_grub_default, write_grub_default
from ..io.core_grub_menu_parser import GrubDefaultChoice, read_grub_default_choices_with_source


@dataclass(frozen=True)
class GrubUiModel:
    """Modèle manipulé par l'UI (valeurs simplifiées).

    Ce modèle est volontairement découplé du format exact de `/etc/default/grub`.
    """

    timeout: int = 5
    default: str = "0"  # "0", "1", ... ou "saved" ou "1>2" (sous-menu)

    save_default: bool = False
    hidden_timeout: bool = False

    gfxmode: str = ""
    gfxpayload_linux: str = ""

    disable_os_prober: bool = False
    grub_theme: str = ""  # Chemin vers le fichier theme.txt

    # Paramètres kernel (GRUB_CMDLINE_LINUX_DEFAULT)
    quiet: bool = True  # Mode silencieux
    splash: bool = True  # Écran de démarrage


@dataclass(frozen=True)
class GrubUiState:
    """État complet nécessaire à l'UI.

    `raw_config` contient la configuration brute afin de pouvoir préserver les
    clés inconnues lors du merge/sauvegarde.
    """

    model: GrubUiModel
    entries: list[GrubDefaultChoice]
    raw_config: dict[str, str]


_MANAGED_KEYS: Final[set[str]] = {
    "GRUB_TIMEOUT",
    "GRUB_DEFAULT",
    "GRUB_TIMEOUT_STYLE",
    "GRUB_SAVEDEFAULT",
    "GRUB_DISABLE_OS_PROBER",
    "GRUB_GFXMODE",
    "GRUB_GFXPAYLOAD_LINUX",
    "GRUB_TERMINAL",
    "GRUB_THEME",
    "GRUB_CMDLINE_LINUX_DEFAULT",
}


def _as_bool(config: dict[str, str], key: str, true_values: set[str]) -> bool:
    """Return True if config[key] is in the true_values set.

    DEV: Conversion booléenne flottante pour les options GRUB.
    """
    result = config.get(key, "") in true_values
    if result:
        logger.debug(f"[_as_bool] {key}={config.get(key)} → TRUE")
    return result


def model_from_config(config: dict[str, str]) -> GrubUiModel:
    """Construit un `GrubUiModel` à partir d'un dict issu de `/etc/default/grub`."""
    logger.debug(f"[model_from_config] Construction depuis config - {len(config)} clés")

    def _int(value: str, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    timeout = _int(config.get("GRUB_TIMEOUT", "5"), 5)
    default_value = (config.get("GRUB_DEFAULT", "0") or "0").strip() or "0"
    hidden_timeout = config.get("GRUB_TIMEOUT_STYLE", "menu") == "hidden"

    # Analyser GRUB_CMDLINE_LINUX_DEFAULT pour quiet et splash
    cmdline = config.get("GRUB_CMDLINE_LINUX_DEFAULT", "quiet splash")
    quiet = "quiet" in cmdline
    splash = "splash" in cmdline

    return GrubUiModel(
        timeout=timeout,
        default=default_value,
        save_default=_as_bool(config, "GRUB_SAVEDEFAULT", {"true"}),
        hidden_timeout=hidden_timeout,
        gfxmode=config.get("GRUB_GFXMODE", ""),
        gfxpayload_linux=config.get("GRUB_GFXPAYLOAD_LINUX", ""),
        disable_os_prober=_as_bool(config, "GRUB_DISABLE_OS_PROBER", {"true"}),
        grub_theme=config.get("GRUB_THEME", ""),
        quiet=quiet,
        splash=splash,
    )


def merged_config_from_model(base_config: dict[str, str], model: GrubUiModel) -> dict[str, str]:
    """Fusionne `model` dans `base_config` en préservant les clés non gérées.

    Les clés gérées (_MANAGED_KEYS) sont d'abord supprimées, puis réécrites selon
    les valeurs du modèle. Les options booléennes sont explicitement absentes si False
    (comportement GRUB: absence = désactivé).
    """
    logger.debug(f"[merged_config_from_model] Début - model.timeout={model.timeout}, base keys={len(base_config)}")
    cfg = dict(base_config)

    # Suppression de TOUTES les clés gérées pour repartir proprement
    for k in _MANAGED_KEYS:
        cfg.pop(k, None)

    # === OPTIONS OBLIGATOIRES (toujours présentes) ===
    cfg["GRUB_TIMEOUT"] = str(int(model.timeout))
    cfg["GRUB_DEFAULT"] = (model.default or "0").strip() or "0"
    cfg["GRUB_TIMEOUT_STYLE"] = "hidden" if model.hidden_timeout else "menu"

    # === OPTIONS BOOLÉENNES (présentes SI activées) ===
    # GRUB_SAVEDEFAULT: True si GRUB_DEFAULT=saved OU si explicitement demandé
    if model.save_default or model.default == "saved":
        cfg["GRUB_SAVEDEFAULT"] = "true"

    if model.disable_os_prober:
        cfg["GRUB_DISABLE_OS_PROBER"] = "true"
    # Sinon : clé absente = os-prober activé

    # === OPTIONS GRAPHIQUES (présentes si non vides) ===
    if model.gfxmode.strip():
        cfg["GRUB_GFXMODE"] = model.gfxmode.strip()
    if model.gfxpayload_linux.strip():
        cfg["GRUB_GFXPAYLOAD_LINUX"] = model.gfxpayload_linux.strip()

    # === THÈME (présent si défini) ===
    if model.grub_theme.strip():
        cfg["GRUB_THEME"] = model.grub_theme.strip()
    # Sinon : clé absente = pas de thème

    # === PARAMÈTRES KERNEL (GRUB_CMDLINE_LINUX_DEFAULT) ===
    cmdline_parts = []
    if model.quiet:
        cmdline_parts.append("quiet")
    if model.splash:
        cmdline_parts.append("splash")

    if cmdline_parts:
        cfg["GRUB_CMDLINE_LINUX_DEFAULT"] = " ".join(cmdline_parts)
    # Sinon : clé absente = aucun paramètre par défaut

    logger.debug(
        f"[merged_config_from_model] Succès - merged keys={len(cfg)}, "
        f"modified keys={sum(1 for k in _MANAGED_KEYS if k in cfg)}"
    )
    return cfg


def load_grub_ui_state(
    grub_default_path: str = GRUB_DEFAULT_PATH,
    grub_cfg_path: str = GRUB_CFG_PATH,
) -> GrubUiState:
    """Load UI state from /etc/default/grub and grub.cfg (read-only).

    DEV: Charge la configuration complète.
    """
    logger.debug(f"[load_grub_ui_state] Chargement depuis {grub_default_path} et {grub_cfg_path}")
    config = read_grub_default(grub_default_path)
    logger.debug(f"[load_grub_ui_state] Config lue: {len(config)} clés")

    entries, _used_grub_cfg_path = read_grub_default_choices_with_source(grub_cfg_path)
    logger.debug(f"[load_grub_ui_state] {len(entries)} entrées trouvées")

    model = model_from_config(config)

    logger.success("[load_grub_ui_state] État chargé avec succès")
    return GrubUiState(model=model, entries=entries, raw_config=config)


def save_grub_ui_state(state: GrubUiState, model: GrubUiModel, grub_default_path: str = GRUB_DEFAULT_PATH) -> str:
    """Save merged configuration to /etc/default/grub.

    Returns:
        Path to the created backup file.

    DEV: Fusion du modèle UI dans la config brute et écriture.
    """
    logger.debug(f"[save_grub_ui_state] Sauvegarde vers {grub_default_path}")
    merged = merged_config_from_model(state.raw_config, model)
    logger.debug(f"[save_grub_ui_state] Config fusionnée: {len(merged)} clés")
    backup_path = write_grub_default(merged, grub_default_path)
    logger.success(f"[save_grub_ui_state] Sauvegarde complète, backup: {backup_path}")
    return backup_path
