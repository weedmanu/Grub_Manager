from __future__ import annotations

from core.model import _extract_menu_colors_from_grub_cfg, _fallback_colors_from_grub_cfg


def test_extract_menu_colors_from_grub_cfg_uses_last_assignment() -> None:
    text = """
### BEGIN /etc/grub.d/05_debian_theme ###
set menu_color_normal=cyan/blue
set menu_color_highlight=white/blue
### END /etc/grub.d/05_debian_theme ###

### BEGIN /etc/grub.d/05_grub_colors ###
set menu_color_normal=light-gray/black
set menu_color_highlight=white/dark-gray
### END /etc/grub.d/05_grub_colors ###
"""

    nfg, nbg, hfg, hbg = _extract_menu_colors_from_grub_cfg(text)
    assert (nfg, nbg) == ("light-gray", "black")
    assert (hfg, hbg) == ("white", "dark-gray")


def test_fallback_colors_from_grub_cfg_reads_file(tmp_path) -> None:
    grub_cfg = tmp_path / "grub.cfg"
    grub_cfg.write_text("set menu_color_normal=yellow/blue\nset menu_color_highlight=white/blue\n", encoding="utf-8")

    nfg, nbg, hfg, hbg = _fallback_colors_from_grub_cfg(str(grub_cfg))
    assert (nfg, nbg) == ("yellow", "blue")
    assert (hfg, hbg) == ("white", "blue")
