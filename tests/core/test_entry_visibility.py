from __future__ import annotations

from pathlib import Path

from core.entry_visibility import apply_hidden_entries_to_grub_cfg


def test_apply_hidden_entries_to_grub_cfg_removes_menuentry_block(tmp_path: Path) -> None:
    grub_cfg = tmp_path / "grub.cfg"
    grub_cfg.write_text(
        """
set default=0
set timeout=5

menuentry 'Ubuntu' --class ubuntu $menuentry_id_option 'gnulinux-simple-aaa' {
    echo 'boot ubuntu'
}

menuentry 'Windows Boot Manager' --class windows $menuentry_id_option 'osprober-efi-bbb' {
    echo 'boot windows'
}
""".lstrip(),
        encoding="utf-8",
    )

    used, masked = apply_hidden_entries_to_grub_cfg({"osprober-efi-bbb"}, grub_cfg_path=str(grub_cfg))
    assert used == str(grub_cfg)
    assert masked == 1

    out = grub_cfg.read_text(encoding="utf-8")
    assert "Ubuntu" in out
    assert "menuentry 'Windows Boot Manager'" not in out
    assert "GRUB_MANAGER_HIDDEN" in out


def test_apply_hidden_entries_noop_when_empty(tmp_path: Path) -> None:
    grub_cfg = tmp_path / "grub.cfg"
    grub_cfg.write_text("menuentry 'X' $menuentry_id_option 'id-x' {\n}\n", encoding="utf-8")

    used, masked = apply_hidden_entries_to_grub_cfg(set(), grub_cfg_path=str(grub_cfg))
    assert used == str(grub_cfg)
    assert masked == 0
