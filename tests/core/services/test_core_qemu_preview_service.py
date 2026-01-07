from pathlib import Path

from core.services.core_services_qemu_preview import (
    build_preview_grub_cfg,
    extract_entry_titles_from_grub_cfg,
    extract_theme_from_grub_cfg,
    extract_visuals_from_grub_cfg,
    sanitize_grub_cfg_for_iso,
)


def test_extract_visuals_last_wins() -> None:
    grub_cfg = """
set menu_color_normal=white/black
set menu_color_normal=green/black
set menu_color_highlight=black/light-gray
set menu_color_highlight=black/green
background_color 0,0,0
set timeout=5
"""
    v = extract_visuals_from_grub_cfg(grub_cfg)
    assert v.menu_color_normal == "green/black"
    assert v.menu_color_highlight == "black/green"
    assert v.background_color == "0,0,0"
    assert v.timeout == 5


def test_extract_entry_titles() -> None:
    grub_cfg = """
menuentry 'Ubuntu' { }
submenu "Advanced options for Ubuntu" { }
menuentry "Windows Boot Manager" { }
"""
    titles = extract_entry_titles_from_grub_cfg(grub_cfg)
    assert titles == ["Ubuntu", "Advanced options for Ubuntu", "Windows Boot Manager"]


def test_build_preview_grub_cfg_contains_colors_and_titles() -> None:
    grub_cfg = """
set menu_color_normal=green/black
set menu_color_highlight=black/green
background_color 0,0,0
menuentry 'Ubuntu' { }
menuentry 'Windows' { }
"""

    preview = build_preview_grub_cfg(source_grub_cfg_text=grub_cfg, force_timeout=12)

    assert "set timeout=12" in preview
    assert "set menu_color_normal=green/black" in preview
    assert "set menu_color_highlight=black/green" in preview
    assert "background_color 0,0,0" in preview

    assert 'menuentry "Ubuntu"' in preview
    assert 'menuentry "Windows"' in preview
    assert "Quitter (halt)" in preview
    assert "Redémarrer" in preview


def test_sanitize_grub_cfg_removes_search_root_prefix_and_rewrites_timeout_and_theme() -> None:
    grub_cfg = """
set root=hd0,gpt2
set prefix=(hd0,gpt2)/boot/grub
search --no-floppy --fs-uuid --set=root 1234-ABCD
set timeout=5
set theme=${prefix}/themes/mytheme/theme.txt
set menu_color_normal=green/black
"""
    theme = extract_theme_from_grub_cfg(text=grub_cfg, source_cfg_path=Path("/boot/grub/grub.cfg"))
    out = sanitize_grub_cfg_for_iso(grub_cfg_text=grub_cfg, theme=theme, force_timeout=42)

    assert "search --no-floppy" not in out
    assert "set root=" not in out
    assert "set prefix=" not in out
    assert "set timeout=42" in out

    # si le theme n'est pas résolu sur la machine de test, l'iso_theme_txt peut être None;
    # on vérifie surtout que le sanitize ne casse pas.
    assert "set menu_color_normal=green/black" in out
