"""Constantes UI pour l'application Grub Manager.

Centralise toutes les valeurs magiques et constantes de l'interface utilisateur.
"""

from typing import Final

# === Dimensions des widgets ===

# Boutons de couleur
COLOR_BUTTON_SIZE: Final[int] = 50
COLOR_BUTTON_SPACING: Final[int] = 10

# Grilles
GRID_ROW_SPACING: Final[int] = 12
GRID_COLUMN_SPACING: Final[int] = 24

# Marges
MARGIN_SMALL: Final[int] = 5
MARGIN_NORMAL: Final[int] = 10
MARGIN_LARGE: Final[int] = 20

# Tailles minimales
MIN_WINDOW_WIDTH: Final[int] = 800
MIN_WINDOW_HEIGHT: Final[int] = 600
MIN_DIALOG_WIDTH: Final[int] = 900
MIN_DIALOG_HEIGHT: Final[int] = 700
MIN_LIST_HEIGHT: Final[int] = 250

# Labels
LABEL_WIDTH: Final[int] = 150
LABEL_WIDTH_SMALL: Final[int] = 120

# === Palettes de couleurs GRUB ===

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

# Couleurs par défaut
DEFAULT_TITLE_COLOR: Final[str] = "#FFFFFF"
DEFAULT_DESKTOP_COLOR: Final[str] = "#000000"
DEFAULT_MENU_FG: Final[str] = "#FFFFFF"
DEFAULT_MENU_BG: Final[str] = "#000000"
DEFAULT_HIGHLIGHT_FG: Final[str] = "#000000"
DEFAULT_HIGHLIGHT_BG: Final[str] = "#D3D3D3"

# === Classes CSS ===

CSS_CLASS_SECTION_HEADER: Final[str] = "section-header"
CSS_CLASS_SECTION_TITLE: Final[str] = "section-title"
CSS_CLASS_COLOR_GRID: Final[str] = "color-grid"
CSS_CLASS_WARNING: Final[str] = "warning"
CSS_CLASS_ERROR: Final[str] = "error"
CSS_CLASS_SUCCESS: Final[str] = "suggested-action"
CSS_CLASS_DESTRUCTIVE: Final[str] = "destructive-action"

# === Timeout et délais ===

DEFAULT_GRUB_TIMEOUT: Final[int] = 5
MIN_TIMEOUT: Final[int] = 0
MAX_TIMEOUT: Final[int] = 60
TIMEOUT_INCREMENT: Final[int] = 1
TIMEOUT_LARGE_INCREMENT: Final[int] = 5

# === Résolutions GRUB ===

RESOLUTION_PRESETS: Final[list[str]] = [
    "auto",
    "1920x1080",
    "1680x1050",
    "1600x900",
    "1440x900",
    "1366x768",
    "1280x1024",
    "1280x800",
    "1024x768",
    "800x600",
]

DEFAULT_RESOLUTION: Final[str] = "auto"

# === Méthodes de mise à l'échelle d'image ===

IMAGE_SCALE_METHODS: Final[list[str]] = [
    "stretch",
    "crop",
    "padding",
    "fitwidth",
    "fitheight",
]

DEFAULT_SCALE_METHOD: Final[str] = "stretch"

# === Alignements d'image ===

IMAGE_H_ALIGNMENTS: Final[list[str]] = ["left", "center", "right"]
IMAGE_V_ALIGNMENTS: Final[list[str]] = ["top", "center", "bottom"]

DEFAULT_H_ALIGN: Final[str] = "center"
DEFAULT_V_ALIGN: Final[str] = "center"

# === Messages utilisateur ===

MSG_NO_THEME_SELECTED: Final[str] = "Veuillez sélectionner un thème"
MSG_THEME_ACTIVATED: Final[str] = "Thème '{name}' activé avec succès"
MSG_THEME_SAVED: Final[str] = "Thème '{name}' sauvegardé"
MSG_SCRIPT_ACTIVATED: Final[str] = "Script activé: {name}"
MSG_ERROR_ACTIVATION: Final[str] = "Erreur lors de l'activation:\n{error}"
MSG_NO_THEMES_FOUND: Final[str] = "Aucun thème trouvé"
MSG_EDITOR_OPENED: Final[str] = "Éditeur de thème ouvert"

# === Chemins système GRUB ===
# Note: Ces constantes dupliquent core.config.paths mais sont utiles pour l'UI

UI_GRUB_SCRIPT_PATTERN: Final[str] = "*theme*"
UI_THEME_FILE_NAME: Final[str] = "theme.txt"

# === Icônes et symboles ===

ICON_ACTIVE: Final[str] = "✓"
ICON_INACTIVE: Final[str] = "⚠"
ICON_ERROR: Final[str] = "✗"
ICON_INFO: Final[str] = "i"

# === Scripts GRUB ===

SCRIPT_PERMISSION_EXECUTABLE: Final[int] = 0o111
