"""Constantes UI pour l'application Grub Manager.

Centralise toutes les valeurs magiques et constantes de l'interface utilisateur.
"""

from typing import Final

# === Dimensions des widgets ===

# Boutons de couleur
COLOR_BUTTON_SIZE: Final[int] = 50

# === Palettes de couleurs GRUB ===

GRUB_COLORS: Final[list[str]] = [
    "black",
    "blue",
    "green",
    "cyan",
    "red",
    "magenta",
    "brown",
    "light-gray",
    "dark-gray",
    "light-blue",
    "light-green",
    "light-cyan",
    "light-red",
    "light-magenta",
    "yellow",
    "white",
]

COLOR_PRESETS: Final[dict[str, str]] = {
    "white": "#FFFFFF",
    "black": "#000000",
    "red": "#FF0000",
    "green": "#00FF00",
    "blue": "#0000FF",
    "cyan": "#00FFFF",
    "magenta": "#FF00FF",
    "yellow": "#FFFF00",
    "light-gray": "#D3D3D3",
    "gray": "#808080",
    "dark-gray": "#404040",
}

# === Timeout et délais ===

DEFAULT_GRUB_TIMEOUT: Final[int] = 5

# === Résolutions GRUB ===

DEFAULT_RESOLUTION: Final[str] = "auto"

# === Messages utilisateur ===

MSG_NO_THEME_SELECTED: Final[str] = "Veuillez sélectionner un thème"

# === Icônes et symboles ===

ICON_ACTIVE: Final[str] = "Actif"

# === Scripts GRUB ===
