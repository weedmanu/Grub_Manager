from __future__ import annotations

from pathlib import Path

import core.grub_menu as grub_menu
import core.model as model


def test_load_state_uses_actual_grub_cfg_for_color_fallback(tmp_path: Path, monkeypatch) -> None:
    # Simule un système où le chemin par défaut est illisible/inexistant,
    # mais un autre grub.cfg existe et contient les couleurs effectives.
    grub1 = tmp_path / "grub.cfg"  # 'par défaut' (vide)
    grub2 = tmp_path / "grub2.cfg"  # utilisé réellement

    grub2.write_text(
        """
set menu_color_normal=white/black
set menu_color_highlight=black/light-gray
menuentry 'Linux' $menuentry_id_option 'id-1' { }
""".lstrip(),
        encoding="utf-8",
    )

    # Patch des constantes dans le module grub_menu (utilisées pour la recherche alternative).
    monkeypatch.setattr(grub_menu, "GRUB_CFG_PATH", str(grub1))
    monkeypatch.setattr(grub_menu, "GRUB_CFG_PATHS", [str(grub1), str(grub2)])

    # Patch côté model aussi, car il compare/forward le path.
    monkeypatch.setattr(model, "GRUB_CFG_PATH", str(grub1))

    grub_default = tmp_path / "default_grub"
    # Pas de GRUB_COLOR_* dans /etc/default/grub => fallback attendu.
    grub_default.write_text("GRUB_TIMEOUT=5\nGRUB_DEFAULT=0\n", encoding="utf-8")

    state = model.load_grub_ui_state(grub_default_path=str(grub_default), grub_cfg_path=str(grub1))
    assert state.model.color_normal_fg == "white"
    assert state.model.color_normal_bg == "black"
    assert state.model.color_highlight_fg == "black"
    assert state.model.color_highlight_bg == "light-gray"
