"""Modèle core pour l'UI et orchestration (lecture/merge/sauvegarde).

But: l'UI ne manipule pas de logique GRUB. Elle ne voit qu'un modèle simple et
appelle le core.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from loguru import logger

from ..config.core_config_paths import GRUB_CFG_PATH, GRUB_DEFAULT_PATH
from ..io.core_io_grub_default import read_grub_default, write_grub_default
from ..io.core_io_grub_menu_parser import GrubDefaultChoice, read_grub_default_choices_with_source
from ..services.core_services_grub_script import GrubScriptService


@dataclass(frozen=True)
class GrubUiModel:
    """Modèle manipulé par l'UI (valeurs simplifiées).

    Ce modèle est volontairement découplé du format exact de `/etc/default/grub`.
    """

    # pylint: disable=too-many-instance-attributes

    timeout: int = 5
    default: str = "0"  # "0", "1", ... ou "saved" ou "1>2" (sous-menu)

    save_default: bool = False
    hidden_timeout: bool = False

    gfxmode: str = ""
    gfxpayload_linux: str = ""
    grub_terminal: str = ""  # GRUB_TERMINAL_OUTPUT (gfxterm, console, serial)

    disable_os_prober: bool = False
    grub_theme: str = ""  # Chemin vers le fichier theme.txt

    # Paramètres de thème simple (si theme_management_enabled=False)
    grub_background: str = ""
    grub_color_normal: str = ""
    grub_color_highlight: str = ""

    # Gestion des scripts de thème (ex: 05_debian_theme, 60_theme_custom)
    # Si False, on désactive ces scripts lors de l'application.
    theme_management_enabled: bool = True

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
    "GRUB_BACKGROUND",
    "GRUB_COLOR_NORMAL",
    "GRUB_COLOR_HIGHLIGHT",
    "GRUB_CMDLINE_LINUX_DEFAULT",
}


def _normalize_grub_terminal_value(value: str) -> str:
    """Normalise une valeur terminal GRUB issue de l'UI/config.

    GRUB attend des valeurs comme: gfxterm, console, serial ou "gfxterm console".
    L'UI peut contenir des libellés annotés (ex: "gfxterm (graphique)").
    """
    raw = (value or "").strip()
    if not raw:
        return ""

    if "(" in raw:
        raw = raw.split("(", 1)[0].strip()

    normalized = " ".join(raw.lower().split())

    if normalized in {"gfxterm", "console", "serial", "gfxterm console"}:
        return normalized

    # Valeur inconnue: on renvoie une version nettoyée (sans parenthèses)
    return normalized


def _as_bool(config: dict[str, str], key: str, true_values: set[str]) -> bool:
    """Return True if config[key] is in the true_values set.

    DEV: Conversion booléenne flottante pour les options GRUB.
    """
    result = config.get(key, "") in true_values
    if result:
        logger.debug(f"[_as_bool] {key}={config.get(key)} → TRUE")
    return result


def model_from_config(config: dict[str, str], theme_scripts_enabled: bool = True) -> GrubUiModel:
    """Construit un `GrubUiModel` à partir d'un dict issu de `/etc/default/grub`."""
    logger.debug(f"[model_from_config] Construction depuis config - {len(config)} clés")

    def _int(value: str, default: int) -> int:
        try:
            return max(0, int(value))
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
        grub_terminal=_normalize_grub_terminal_value(
            config.get("GRUB_TERMINAL_OUTPUT", config.get("GRUB_TERMINAL", ""))
        ),
        disable_os_prober=_as_bool(config, "GRUB_DISABLE_OS_PROBER", {"true"}),
        grub_theme=config.get("GRUB_THEME", ""),
        grub_background=config.get("GRUB_BACKGROUND", ""),
        grub_color_normal=config.get("GRUB_COLOR_NORMAL", ""),
        grub_color_highlight=config.get("GRUB_COLOR_HIGHLIGHT", ""),
        theme_management_enabled=theme_scripts_enabled,
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
    cfg.update(
        {
            "GRUB_TIMEOUT": str(int(model.timeout)),
            "GRUB_DEFAULT": (model.default or "0").strip() or "0",
            "GRUB_TIMEOUT_STYLE": "hidden" if model.hidden_timeout else "menu",
            # Force l'activation pour les versions récentes de GRUB (2.06+) où c'est désactivé par défaut
            "GRUB_DISABLE_OS_PROBER": "true" if model.disable_os_prober else "false",
        }
    )

    # === OPTIONS BOOLÉENNES (présentes SI activées) ===
    # GRUB_SAVEDEFAULT: True si GRUB_DEFAULT=saved OU si explicitement demandé
    if model.save_default or model.default == "saved":
        cfg["GRUB_SAVEDEFAULT"] = "true"

    # === OPTIONS GRAPHIQUES / THÈME SIMPLE (présentes si non vides) ===
    for key, value in (
        ("GRUB_GFXMODE", model.gfxmode),
        ("GRUB_GFXPAYLOAD_LINUX", model.gfxpayload_linux),
        ("GRUB_TERMINAL_OUTPUT", _normalize_grub_terminal_value(model.grub_terminal)),
        ("GRUB_BACKGROUND", model.grub_background),
        ("GRUB_COLOR_NORMAL", model.grub_color_normal),
        ("GRUB_COLOR_HIGHLIGHT", model.grub_color_highlight),
    ):
        value = value.strip()
        if value:
            cfg[key] = value

    # === THÈME (présent si défini) ===
    # UX: la sélection d'un thème via theme.txt ne dépend plus d'un switch de mode.
    theme_path = model.grub_theme.strip()
    if theme_path:
        cfg["GRUB_THEME"] = theme_path
    else:
        cfg.pop("GRUB_THEME", None)

    # === PARAMÈTRES KERNEL (GRUB_CMDLINE_LINUX_DEFAULT) ===
    cmdline_parts = [flag for flag, enabled in (("quiet", model.quiet), ("splash", model.splash)) if enabled]
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

    # Détection de l'état des scripts de thème
    script_service = GrubScriptService()
    theme_scripts = script_service.scan_theme_scripts()
    # Si au moins un script de thème est exécutable, on considère que la gestion est activée
    theme_scripts_enabled = any(s.is_executable for s in theme_scripts)

    # HEURISTIQUE DE CORRECTION:
    # Si l'utilisateur a configuré des options simples (Background/Colors) ET qu'il n'y a pas de GRUB_THEME,
    # on force le mode "Simple" (theme_management_enabled=False) même si les scripts sont encore actifs.
    # Cela permet à l'UI de refléter l'intention de l'utilisateur, et le prochain "Appliquer"
    # désactivera correctement les scripts.
    has_simple_config = bool(config.get("GRUB_BACKGROUND") or config.get("GRUB_COLOR_NORMAL"))
    has_theme_config = bool(config.get("GRUB_THEME"))

    if has_simple_config and not has_theme_config:
        logger.info("[load_grub_ui_state] Détection config simple sans thème -> Force theme_management_enabled=False")
        theme_scripts_enabled = False

    logger.debug(f"[load_grub_ui_state] Scripts de thème activés: {theme_scripts_enabled}")

    model = model_from_config(config, theme_scripts_enabled=theme_scripts_enabled)

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
