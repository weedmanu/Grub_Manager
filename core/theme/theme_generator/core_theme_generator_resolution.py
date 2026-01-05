"""Helpers liés à la résolution (mapping -> config)."""

from __future__ import annotations

from typing import Any, ClassVar

from .core_theme_generator_enums import ThemeResolution
from .core_theme_generator_models import ItemConfig, ResolutionConfig, TerminalConfig


class ThemeResolutionHelper:
    """Helpers pour les configurations spécifiques à une résolution."""

    RESOLUTION_CONFIGS: ClassVar[dict[ThemeResolution, ResolutionConfig]] = {
        ThemeResolution.RESOLUTION_1080P: ResolutionConfig(
            1920,
            1080,
            terminal=TerminalConfig(font_size=14),
            item=ItemConfig(font_size=16),
        ),
        ThemeResolution.RESOLUTION_2K: ResolutionConfig(
            2560,
            1440,
            terminal=TerminalConfig(font_size=18),
            item=ItemConfig(
                font_size=24,
                icon_width=48,
                icon_height=48,
                icon_space=24,
                height=56,
                padding=8,
                spacing=16,
            ),
        ),
        ThemeResolution.RESOLUTION_4K: ResolutionConfig(
            3840,
            2160,
            terminal=TerminalConfig(font_size=18),
            item=ItemConfig(
                font_size=32,
                icon_width=64,
                icon_height=64,
                icon_space=36,
                height=80,
                padding=12,
                spacing=24,
            ),
        ),
        ThemeResolution.RESOLUTION_ULTRAWIDE: ResolutionConfig(
            2560,
            1080,
            terminal=TerminalConfig(font_size=14),
            item=ItemConfig(font_size=16),
        ),
        ThemeResolution.RESOLUTION_ULTRAWIDE_2K: ResolutionConfig(
            3440,
            1440,
            terminal=TerminalConfig(font_size=18),
            item=ItemConfig(font_size=24),
        ),
    }

    @staticmethod
    def get_config_for_resolution(resolution: Any) -> ResolutionConfig:
        """Retourne la config correspondant à la résolution."""
        if resolution in ThemeResolutionHelper.RESOLUTION_CONFIGS:
            return ThemeResolutionHelper.RESOLUTION_CONFIGS[resolution]
        return ThemeResolutionHelper.RESOLUTION_CONFIGS[ThemeResolution.RESOLUTION_1080P]

    @staticmethod
    def get_custom_resolution_config(width: int, height: int) -> ResolutionConfig:
        """Retourne une config auto-scale pour une résolution custom."""
        pixel_count = width * height

        if pixel_count <= 1920 * 1080:  # ~2MP
            return ThemeResolutionHelper.RESOLUTION_CONFIGS[ThemeResolution.RESOLUTION_1080P]
        if pixel_count <= 2560 * 1440:  # ~3.6MP
            return ThemeResolutionHelper.RESOLUTION_CONFIGS[ThemeResolution.RESOLUTION_2K]
        return ThemeResolutionHelper.RESOLUTION_CONFIGS[ThemeResolution.RESOLUTION_4K]
