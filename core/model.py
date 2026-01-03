"""Modèle core pour l'UI et orchestration (lecture/merge/sauvegarde).

But: l'UI ne manipule pas de logique GRUB. Elle ne voit qu'un modèle simple et
appelle le core.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Final

from loguru import logger

from .grub_default import read_grub_default, write_grub_default
from .grub_menu import GrubDefaultChoice, read_grub_default_choices_with_source
from .paths import GRUB_CFG_PATH, GRUB_DEFAULT_PATH


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

    disable_submenu: bool = False
    disable_recovery: bool = False
    disable_os_prober: bool = False
    terminal_color: bool = False

    color_normal_fg: str = ""
    color_normal_bg: str = ""
    color_highlight_fg: str = ""
    color_highlight_bg: str = ""


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
    "GRUB_DISABLE_SUBMENU",
    "GRUB_DISABLE_RECOVERY",
    "GRUB_DISABLE_OS_PROBER",
    "GRUB_GFXMODE",
    "GRUB_GFXPAYLOAD_LINUX",
    "GRUB_TERMINAL",
    "GRUB_COLOR_NORMAL",
    "GRUB_COLOR_HIGHLIGHT",
}


def _split_grub_color(value: str) -> tuple[str, str]:
    """Split a GRUB color value (e.g. 'white/black') into (fg, bg).

    DEV: Analyse une couleur GRUB format "foreground/background".
    """
    raw = (value or "").strip()
    if not raw:
        logger.debug("[_split_grub_color] Couleur vide")
        return "", ""
    if "/" not in raw:
        logger.debug(f"[_split_grub_color] Format simplifié (pas de /): {raw}")
        return raw, ""
    fg, bg = raw.split("/", 1)
    logger.debug(f"[_split_grub_color] Couleur splitée - fg={fg}, bg={bg}")
    return fg.strip(), bg.strip()


def _join_grub_color(fg: str, bg: str) -> str:
    """Join (fg, bg) into a GRUB color value.

    Returns an empty string if both values are empty.

    DEV: Reconstruit une couleur GRUB depuis foreground/background.
    """
    fg_s = (fg or "").strip()
    bg_s = (bg or "").strip()
    if not fg_s and not bg_s:
        logger.debug("[_join_grub_color] Pas de couleur fournie (fg et bg vides)")
        return ""
    if fg_s and bg_s:
        result = f"{fg_s}/{bg_s}"
        logger.debug(f"[_join_grub_color] Couleur complète: {result}")
        return result
    result = fg_s or bg_s
    logger.debug(f"[_join_grub_color] Couleur partielle: {result}")
    return result


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
    logger.debug(f"[model_from_config] Début - config keys: {list(config.keys())}")

    def _int(value: str, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    timeout = _int(config.get("GRUB_TIMEOUT", "5"), 5)
    default_value = (config.get("GRUB_DEFAULT", "0") or "0").strip() or "0"

    hidden_timeout = config.get("GRUB_TIMEOUT_STYLE", "menu") == "hidden"
    terminal_color = "console" in config.get("GRUB_TERMINAL", "")

    normal_fg, normal_bg = _split_grub_color(config.get("GRUB_COLOR_NORMAL", ""))
    hi_fg, hi_bg = _split_grub_color(config.get("GRUB_COLOR_HIGHLIGHT", ""))

    return GrubUiModel(
        timeout=timeout,
        default=default_value,
        save_default=_as_bool(config, "GRUB_SAVEDEFAULT", {"true"}),
        hidden_timeout=hidden_timeout,
        gfxmode=config.get("GRUB_GFXMODE", ""),
        gfxpayload_linux=config.get("GRUB_GFXPAYLOAD_LINUX", ""),
        disable_submenu=_as_bool(config, "GRUB_DISABLE_SUBMENU", {"y"}),
        disable_recovery=_as_bool(config, "GRUB_DISABLE_RECOVERY", {"true"}),
        disable_os_prober=_as_bool(config, "GRUB_DISABLE_OS_PROBER", {"true"}),
        terminal_color=terminal_color,
        color_normal_fg=normal_fg,
        color_normal_bg=normal_bg,
        color_highlight_fg=hi_fg,
        color_highlight_bg=hi_bg,
    )


def _extract_menu_colors_from_grub_cfg(grub_cfg_text: str) -> tuple[str, str, str, str]:
    """Extract effective menu colors from grub.cfg.

    Searches (in file order) for assignments:
    - set menu_color_normal=<fg>/<bg>
    - set menu_color_highlight=<fg>/<bg>

    Returns:
        Tuple (normal_fg, normal_bg, highlight_fg, highlight_bg). Fields may
        be empty if not found.

    DEV: Parse grub.cfg pour extraire les couleurs finales du menu.
    """
    logger.debug("[_extract_menu_colors_from_grub_cfg] Extraction des couleurs du grub.cfg")
    normal = ""
    highlight = ""

    # On retient la dernière valeur rencontrée (celle qui s'applique à la fin).
    pat_normal = re.compile(r"^\s*set\s+menu_color_normal\s*=\s*(.+?)\s*$")
    pat_highlight = re.compile(r"^\s*set\s+menu_color_highlight\s*=\s*(.+?)\s*$")
    for raw_line in grub_cfg_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        m = pat_normal.match(line)
        if m:
            normal = m.group(1).strip().strip('"').strip("'")
            logger.debug(f"[_extract_menu_colors_from_grub_cfg] Couleur normale trouvée: {normal}")
            continue
        m = pat_highlight.match(line)
        if m:
            highlight = m.group(1).strip().strip('"').strip("'")
            logger.debug(f"[_extract_menu_colors_from_grub_cfg] Couleur highlight trouvée: {highlight}")

    normal_fg, normal_bg = _split_grub_color(normal)
    hi_fg, hi_bg = _split_grub_color(highlight)
    logger.success("[_extract_menu_colors_from_grub_cfg] Extraction réussie")
    return normal_fg, normal_bg, hi_fg, hi_bg


def _fallback_colors_from_grub_cfg(grub_cfg_path: str) -> tuple[str, str, str, str]:
    """Read grub.cfg and extract menu colors (best-effort).

    DEV: Fallback pour récupérer les couleurs si non présentes dans /etc/default/grub.
    """
    logger.debug(f"[_fallback_colors_from_grub_cfg] Lecture de {grub_cfg_path}")
    try:
        with open(grub_cfg_path, encoding="utf-8", errors="replace") as f:
            content = f.read()
            logger.debug(f"[_fallback_colors_from_grub_cfg] Fichier lu ({len(content)} bytes)")
            return _extract_menu_colors_from_grub_cfg(content)
    except OSError as e:
        logger.warning(f"[_fallback_colors_from_grub_cfg] Impossible de lire {grub_cfg_path}: {e}")
        return "", "", "", ""


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

    if model.disable_submenu:
        cfg["GRUB_DISABLE_SUBMENU"] = "y"
    # Sinon : clé absente = sous-menus activés

    if model.disable_recovery:
        cfg["GRUB_DISABLE_RECOVERY"] = "true"
    # Sinon : clé absente = mode recovery activé

    if model.disable_os_prober:
        cfg["GRUB_DISABLE_OS_PROBER"] = "true"
    # Sinon : clé absente = os-prober activé

    # === OPTIONS GRAPHIQUES (présentes si non vides) ===
    if model.gfxmode.strip():
        cfg["GRUB_GFXMODE"] = model.gfxmode.strip()
    if model.gfxpayload_linux.strip():
        cfg["GRUB_GFXPAYLOAD_LINUX"] = model.gfxpayload_linux.strip()

    # === TERMINAL (présent si mode console demandé) ===
    if model.terminal_color:
        cfg["GRUB_TERMINAL"] = "console"
    # Sinon : clé absente = terminal graphique par défaut

    # === COULEURS (présentes si définies) ===
    normal = _join_grub_color(model.color_normal_fg, model.color_normal_bg)
    if normal:
        cfg["GRUB_COLOR_NORMAL"] = normal

    highlight = _join_grub_color(model.color_highlight_fg, model.color_highlight_bg)
    if highlight:
        cfg["GRUB_COLOR_HIGHLIGHT"] = highlight

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

    DEV: Charge la configuration complète avec fallback des couleurs depuis grub.cfg.
    """
    logger.debug(f"[load_grub_ui_state] Chargement depuis {grub_default_path} et {grub_cfg_path}")
    config = read_grub_default(grub_default_path)
    logger.debug(f"[load_grub_ui_state] Config lue: {len(config)} clés")

    entries, used_grub_cfg_path = read_grub_default_choices_with_source(grub_cfg_path)
    logger.debug(f"[load_grub_ui_state] {len(entries)} entrées trouvées")

    model = model_from_config(config)
    if not (model.color_normal_fg or model.color_normal_bg or model.color_highlight_fg or model.color_highlight_bg):
        logger.debug("[load_grub_ui_state] Couleurs manquantes, extraction depuis grub.cfg")
        nfg, nbg, hfg, hbg = _fallback_colors_from_grub_cfg(used_grub_cfg_path or grub_cfg_path)
        model = replace(
            model,
            color_normal_fg=nfg,
            color_normal_bg=nbg,
            color_highlight_fg=hfg,
            color_highlight_bg=hbg,
        )
        logger.debug("[load_grub_ui_state] Couleurs fallback appliquées")

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
