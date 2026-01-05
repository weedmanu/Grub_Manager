"""Data loader pour le preview GRUB - responsabilité unique de chargement de données."""

from __future__ import annotations

import os
from pathlib import Path

from loguru import logger

from core.config.core_config_paths import discover_grub_cfg_paths
from core.models.core_models_grub_ui import GrubUiModel
from core.models.core_models_theme import GrubTheme
from core.services.core_services_grub import GrubService, MenuEntry
from ui.dialogs.preview.ui_dialogs_preview_grub_css import PreviewColors, PreviewFonts, PreviewLayout
from ui.dialogs.preview.ui_dialogs_preview_grub_parsers import (
    GrubConfigParser,
    SystemMenuColors,
    ThemeTxtOverrides,
)


class GrubPreviewDataLoader:
    """Charge les données nécessaires pour le preview GRUB."""

    def __init__(
        self,
        *,
        use_system_files: bool = True,
        model: GrubUiModel | None = None,
        theme: GrubTheme | None = None,
        theme_txt_path: Path | None = None,
    ):
        """Initialise le data loader.

        Args:
            use_system_files: Si True, lit les fichiers système
            model: Modèle UI optionnel
            theme: Thème optionnel
            theme_txt_path: Chemin explicite vers theme.txt
        """
        self.use_system_files = use_system_files
        self.model = model
        self.theme = theme
        self._theme_txt_path = theme_txt_path
        self._system_menu_colors: SystemMenuColors | None = None
        self._system_theme_overrides: ThemeTxtOverrides | None = None
        self._system_theme_dir: Path | None = None
        self.grub_service = GrubService()

    def load_preview_data(self) -> tuple[int, str, list[MenuEntry]]:
        """Charge les données du preview (timeout, default, entries).

        Returns:
            Tuple (timeout, default_entry, menu_entries)
        """
        try:
            if self.use_system_files:
                config = self.grub_service.read_current_config()
                timeout = config.timeout
                default_entry = config.default_entry
            elif self.model:
                timeout = self.model.timeout
                default_entry = self.model.default
            else:
                config = self.grub_service.read_current_config()
                timeout = config.timeout
                default_entry = config.default_entry

            menu_entries = self.grub_service.get_menu_entries()

            # Limiter à 10 entrées max pour un ratio réaliste
            if len(menu_entries) > 10:
                menu_entries = menu_entries[:10]

            # Si moins de 5 entrées, en créer des supplémentaires pour le ratio
            while len(menu_entries) < 8:
                idx = len(menu_entries)
                menu_entries.append(
                    MenuEntry(
                        title=f"Ubuntu (option {idx + 1})",
                        id=f"gnulinux-{idx}",
                    )
                )

            return timeout, default_entry, menu_entries
        except (OSError, RuntimeError) as e:
            logger.warning(f"[GrubPreviewDataLoader] Erreur lecture config: {e}")
            # Créer 8 entrées par défaut
            default_entries = [
                MenuEntry(title="Ubuntu", id="gnulinux-0"),
                MenuEntry(title="Ubuntu (options avancées)", id="gnulinux-advanced"),
                MenuEntry(title="Ubuntu (mode recovery)", id="gnulinux-recovery"),
                MenuEntry(title="Ubuntu (kernel précédent)", id="gnulinux-old"),
                MenuEntry(title="Memory test (memtest86+)", id="memtest"),
                MenuEntry(title="Memory test (memtest86+, serial console)", id="memtest-serial"),
                MenuEntry(title="Windows Boot Manager (on /dev/nvme1p1)", id="windows"),
                MenuEntry(title="UEFI Firmware Settings", id="uefi-firmware"),
            ]
            return 10, "0", default_entries

    def load_system_menu_colors(self) -> SystemMenuColors | None:
        """Charge les couleurs menu_color_* depuis grub.cfg.

        Returns:
            SystemMenuColors si trouvé, None sinon
        """
        if self._system_menu_colors is not None:
            return self._system_menu_colors

        try:
            for candidate in discover_grub_cfg_paths():
                try:
                    if not os.path.exists(candidate):
                        continue
                    with open(candidate, encoding="utf-8", errors="replace") as f:
                        parsed = GrubConfigParser.parse_grub_cfg_menu_colors(f.read().splitlines())
                    if parsed is not None:
                        self._system_menu_colors = parsed
                        return parsed
                except OSError:
                    continue
        except Exception as exc:
            logger.debug(f"[GrubPreviewDataLoader] Erreur chargement menu colors: {exc}")

        self._system_menu_colors = None
        return None

    def _try_load_theme_from_explicit_path(self) -> bool:
        """Essaie de charger le thème depuis le chemin explicite."""
        if self._theme_txt_path is None:
            return False

        theme_file = self._theme_txt_path
        self._system_theme_dir = theme_file.parent
        try:
            if theme_file.exists():
                self._system_theme_overrides = GrubConfigParser.parse_theme_txt(theme_file)
            else:
                self._system_theme_overrides = None
        except (OSError, ValueError):
            self._system_theme_overrides = None
        return True

    def _try_load_theme_from_grub_cfg(self) -> tuple[bool, bool]:
        """Essaie de charger le thème depuis grub.cfg.

        Returns:
            (any_cfg_readable, theme_found)
        """
        any_cfg_readable = False
        try:
            for candidate in discover_grub_cfg_paths():
                try:
                    if not os.path.exists(candidate):
                        continue
                    with open(candidate, encoding="utf-8", errors="replace") as f:
                        lines = f.read().splitlines()
                    any_cfg_readable = True
                    theme_path = GrubConfigParser.parse_grub_cfg_theme_path(lines)
                    if not theme_path:
                        continue
                    theme_file = Path(theme_path)
                    self._system_theme_dir = theme_file.parent
                    if theme_file.exists():
                        self._system_theme_overrides = GrubConfigParser.parse_theme_txt(theme_file)
                        return any_cfg_readable, True
                except OSError:
                    continue
        except Exception as exc:
            logger.debug(f"[GrubPreviewDataLoader] grub.cfg ignoré: {exc}")

        return any_cfg_readable, False

    def _try_load_theme_from_default_grub(self) -> None:
        """Essaie de charger le thème depuis /etc/default/grub."""
        try:
            cfg = GrubService.read_current_config()
        except (OSError, RuntimeError, ValueError):
            return

        theme_path = (cfg.grub_theme or "").strip().strip('"').strip("'")
        if not theme_path:
            return

        theme_file = Path(theme_path)
        self._system_theme_dir = theme_file.parent

        try:
            if theme_file.exists():
                self._system_theme_overrides = GrubConfigParser.parse_theme_txt(theme_file)
        except (OSError, ValueError):
            self._system_theme_overrides = None

    def load_system_theme_overrides(self) -> ThemeTxtOverrides | None:
        """Charge les overrides de theme.txt.

        Priorité:
        - `theme_txt_path` explicite
        - sinon mode système via grub.cfg puis /etc/default/grub

        Returns:
            ThemeTxtOverrides si trouvé, None sinon
        """
        if self._system_theme_overrides is not None:
            return self._system_theme_overrides

        if self._try_load_theme_from_explicit_path():
            return self._system_theme_overrides

        if not self.use_system_files:
            return None

        # Mode système: priorité grub.cfg puis fallback GRUB_THEME
        any_cfg_readable, theme_found = self._try_load_theme_from_grub_cfg()

        # Si grub.cfg lisible mais sans thème, pas de fallback GRUB_THEME
        if any_cfg_readable:
            if not theme_found:
                self._system_theme_overrides = None
            return self._system_theme_overrides

        # Fallback GRUB_THEME si grub.cfg illisible
        self._try_load_theme_from_default_grub()
        return self._system_theme_overrides

    def _get_default_preview_style(self) -> tuple[PreviewColors, PreviewFonts, PreviewLayout]:
        """Retourne le style par défaut."""
        colors = PreviewColors(
            fg_color="white",
            bg_color="rgba(0, 0, 0, 0.5)",
            hl_fg="black",
            hl_bg="#D3D3D3",
            title_color="white",
        )
        fonts = PreviewFonts(title_font="DejaVu Sans Bold 14pt", entry_font="DejaVu Sans Mono 12pt")
        layout = PreviewLayout(menu_top="20%", menu_left="15%", menu_width="70%", menu_height="auto")
        return colors, fonts, layout

    def _get_text_mode_fonts_layout(self) -> tuple[PreviewFonts, PreviewLayout]:
        """Retourne polices et layout pour le mode texte."""
        fonts = PreviewFonts(title_font="Monospace 10pt", entry_font="Monospace 9pt")
        layout = PreviewLayout(menu_top="0", menu_left="0", menu_width="100%", menu_height="100%")
        return fonts, layout

    def _try_get_colors_from_default_grub(self) -> PreviewColors | None:
        """Essaie de charger les couleurs depuis /etc/default/grub."""
        if not self.use_system_files:
            return None
        try:
            cfg = GrubService.read_current_config()
            n_fg, n_bg = GrubConfigParser.parse_grub_color_pair(
                cfg.grub_color_normal, default_fg="white", default_bg="black"
            )
            h_fg, h_bg = GrubConfigParser.parse_grub_color_pair(
                cfg.grub_color_highlight, default_fg="black", default_bg="#D3D3D3"
            )
            return PreviewColors(fg_color=n_fg, bg_color=n_bg, hl_fg=h_fg, hl_bg=h_bg, title_color=n_fg)
        except (OSError, RuntimeError, ValueError):
            return None

    def _apply_theme_overrides(
        self, colors: PreviewColors, fonts: PreviewFonts, layout: PreviewLayout
    ) -> tuple[PreviewColors, PreviewFonts, PreviewLayout]:
        """Applique les overrides theme.txt."""
        if not self._system_theme_overrides:
            return colors, fonts, layout

        ov = self._system_theme_overrides

        if ov.item_color:
            colors = PreviewColors(
                fg_color=ov.item_color,
                bg_color=colors.bg_color,
                hl_fg=ov.selected_item_color or colors.hl_fg,
                hl_bg=colors.hl_bg,
                title_color=ov.item_color,
            )

        if ov.item_font:
            fonts = PreviewFonts(title_font=fonts.title_font, entry_font=ov.item_font)
        elif ov.terminal_font:
            fonts = PreviewFonts(title_font=fonts.title_font, entry_font=ov.terminal_font)

        if ov.boot_menu_left and ov.boot_menu_top and ov.boot_menu_width and ov.boot_menu_height:
            layout = PreviewLayout(
                menu_top=ov.boot_menu_top,
                menu_left=ov.boot_menu_left,
                menu_width=ov.boot_menu_width,
                menu_height=ov.boot_menu_height,
            )

        return colors, fonts, layout

    def _apply_model_theme_style(
        self, colors: PreviewColors, fonts: PreviewFonts, layout: PreviewLayout
    ) -> tuple[PreviewColors, PreviewFonts, PreviewLayout]:
        """Applique le style du thème du modèle."""
        if not (self.model and self.model.theme_management_enabled and self.theme):
            return colors, fonts, layout

        theme_bg = self.theme.colors.menu_normal_bg
        resolved_bg = (
            "rgba(0, 0, 0, 0.4)"
            if theme_bg == "black"
            else GrubConfigParser.parse_grub_color(theme_bg, "rgba(0, 0, 0, 0.4)")
        )
        colors = PreviewColors(
            fg_color=GrubConfigParser.parse_grub_color(self.theme.colors.menu_normal_fg, "white"),
            bg_color=resolved_bg,
            hl_fg=GrubConfigParser.parse_grub_color(self.theme.colors.menu_highlight_fg, "black"),
            hl_bg=GrubConfigParser.parse_grub_color(self.theme.colors.menu_highlight_bg, "#D3D3D3"),
            title_color=GrubConfigParser.parse_grub_color(self.theme.colors.title_color, "white"),
        )

        if self.theme.layout:
            layout = PreviewLayout(
                menu_top=self.theme.layout.menu_top,
                menu_left=self.theme.layout.menu_left,
                menu_width=self.theme.layout.menu_width,
                menu_height=self.theme.layout.menu_height,
            )

        if self.theme.fonts:
            fonts = PreviewFonts(
                title_font=self.theme.fonts.title_font.replace("Regular", "").strip(),
                entry_font=self.theme.fonts.terminal_font.replace("Regular", "").strip(),
            )

        return colors, fonts, layout

    def resolve_preview_style(self, *, is_text_mode: bool) -> tuple[PreviewColors, PreviewFonts, PreviewLayout]:
        """Résout le style du preview selon la priorité des sources.

        Args:
            is_text_mode: Si True, mode texte console

        Returns:
            Tuple (colors, fonts, layout)
        """
        # Charger les données système si nécessaire
        if self._system_menu_colors is None:
            self.load_system_menu_colors()
        if self._system_theme_overrides is None:
            self.load_system_theme_overrides()

        colors, fonts, layout = self._get_default_preview_style()

        # PRIORITÉ 1 : Couleurs grub.cfg (menu_color_*)
        if self._system_menu_colors is not None:
            smc = self._system_menu_colors
            colors = PreviewColors(
                fg_color=smc.normal_fg,
                bg_color=smc.normal_bg,
                hl_fg=smc.highlight_fg,
                hl_bg=smc.highlight_bg,
                title_color=smc.normal_fg,
            )
            if is_text_mode:
                fonts, layout = self._get_text_mode_fonts_layout()
            return colors, fonts, layout

        # PRIORITÉ 2 : Overrides theme.txt
        if self._system_theme_overrides:
            return self._apply_theme_overrides(colors, fonts, layout)

        # PRIORITÉ 3 : Mode texte avec couleurs /etc/default/grub
        if is_text_mode:
            fonts, layout = self._get_text_mode_fonts_layout()
            loaded_colors = self._try_get_colors_from_default_grub()
            if loaded_colors:
                return loaded_colors, fonts, layout
            return (
                PreviewColors(
                    fg_color="white",
                    bg_color="black",
                    hl_fg="black",
                    hl_bg="#D3D3D3",
                    title_color="white",
                ),
                fonts,
                layout,
            )

        # Fallback système (/etc/default/grub)
        loaded_colors = self._try_get_colors_from_default_grub()
        if loaded_colors:
            colors = loaded_colors

        # Appliquer le thème du modèle si disponible
        colors, fonts, layout = self._apply_model_theme_style(colors, fonts, layout)

        # Fallback final : couleurs du modèle simple
        if self.model and not (self.model.theme_management_enabled and self.theme):
            colors = PreviewColors(
                fg_color=GrubConfigParser.parse_grub_color(self.model.grub_color_normal, "white"),
                bg_color="rgba(0, 0, 0, 0.6)",
                hl_fg=GrubConfigParser.parse_grub_color(self.model.grub_color_highlight, "black"),
                hl_bg=colors.hl_bg,
                title_color=colors.title_color,
            )

        return colors, fonts, layout

    def get_desktop_color(self) -> str:
        """Retourne la couleur de fond du desktop.

        Returns:
            Couleur CSS
        """
        if self._system_theme_overrides and self._system_theme_overrides.desktop_color:
            return self._system_theme_overrides.desktop_color

        if self._system_menu_colors:
            return self._system_menu_colors.normal_bg

        return "#8C8C8C"

    def get_item_dimensions(self) -> tuple[int, int, int]:
        """Retourne les dimensions des items (padding, spacing, height).

        Returns:
            Tuple (padding, spacing, height)
        """
        ov = self._system_theme_overrides
        if ov:
            padding = int(ov.item_padding) if ov.item_padding is not None else 10
            spacing = int(ov.item_spacing) if ov.item_spacing is not None else 4
            height = int(ov.item_height) if ov.item_height is not None else 0
            return padding, spacing, height

        return 10, 4, 0
