"""Logique partagée pour la configuration simple du thème.

But: éviter de dupliquer le même calcul (fond + couleurs) entre l'onglet et le
composant, tout en gardant une surface API facile à tester.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any


@dataclass(frozen=True, slots=True)
class SimpleThemeConfigWidgets:
    """Widgets nécessaires à la configuration simple du thème."""

    bg_image_entry: Any
    normal_fg_combo: Any
    normal_bg_combo: Any
    highlight_fg_combo: Any
    highlight_bg_combo: Any


def _selected_indexes(widgets: SimpleThemeConfigWidgets) -> tuple[int, int, int, int] | None:
    selected = (
        widgets.normal_fg_combo.get_selected(),
        widgets.normal_bg_combo.get_selected(),
        widgets.highlight_fg_combo.get_selected(),
        widgets.highlight_bg_combo.get_selected(),
    )
    if any(idx is None or idx < 0 for idx in selected):
        return None
    return selected  # type: ignore[return-value]


def _color_pair(colors: list[str], fg_idx: int, bg_idx: int) -> str:
    return f"{colors[fg_idx]}/{colors[bg_idx]}"


def apply_simple_theme_config_from_widgets(
    *,
    state_manager: Any,
    colors: list[str],
    widgets: SimpleThemeConfigWidgets,
) -> bool:
    """Lit les widgets et met à jour le modèle si possible.

    Returns:
        True si une mise à jour a été effectuée, False sinon.
    """
    if (
        not widgets.bg_image_entry
        or not widgets.normal_fg_combo
        or not widgets.normal_bg_combo
        or not widgets.highlight_fg_combo
        or not widgets.highlight_bg_combo
    ):
        return False

    selected = _selected_indexes(widgets)
    if selected is None:
        return False

    normal_fg_idx, normal_bg_idx, highlight_fg_idx, highlight_bg_idx = selected

    bg_image = widgets.bg_image_entry.get_text()

    color_normal = _color_pair(colors, normal_fg_idx, normal_bg_idx)
    color_highlight = _color_pair(colors, highlight_fg_idx, highlight_bg_idx)

    current_model = state_manager.get_model()
    new_model = replace(
        current_model,
        grub_background=bg_image,
        grub_color_normal=color_normal,
        grub_color_highlight=color_highlight,
    )
    state_manager.update_model(new_model)
    return True
