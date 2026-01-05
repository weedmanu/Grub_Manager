"""Logique partagée pour la configuration simple du thème.

But: éviter de dupliquer le même calcul (fond + couleurs) entre l'onglet et le
composant, tout en gardant une surface API facile à tester.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any


def apply_simple_theme_config_from_widgets(
    *,
    state_manager: Any,
    colors: list[str],
    bg_image_entry: Any,
    normal_fg_combo: Any,
    normal_bg_combo: Any,
    highlight_fg_combo: Any,
    highlight_bg_combo: Any,
) -> bool:
    """Lit les widgets et met à jour le modèle si possible.

    Returns:
        True si une mise à jour a été effectuée, False sinon.
    """
    if not bg_image_entry or not normal_fg_combo or not normal_bg_combo:
        return False
    if not highlight_fg_combo or not highlight_bg_combo:
        return False

    selected = [
        normal_fg_combo.get_selected(),
        normal_bg_combo.get_selected(),
        highlight_fg_combo.get_selected(),
        highlight_bg_combo.get_selected(),
    ]
    if any(idx is None or idx < 0 for idx in selected):
        return False

    bg_image = bg_image_entry.get_text()

    n_fg = colors[normal_fg_combo.get_selected()]
    n_bg = colors[normal_bg_combo.get_selected()]
    color_normal = f"{n_fg}/{n_bg}"

    h_fg = colors[highlight_fg_combo.get_selected()]
    h_bg = colors[highlight_bg_combo.get_selected()]
    color_highlight = f"{h_fg}/{h_bg}"

    current_model = state_manager.get_model()
    new_model = replace(
        current_model,
        grub_background=bg_image,
        grub_color_normal=color_normal,
        grub_color_highlight=color_highlight,
    )
    state_manager.update_model(new_model)
    return True
