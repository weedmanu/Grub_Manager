"""Service core: preview GRUB réelle via QEMU.

Responsabilités:
- Construire un ISO bootable GRUB qui charge un grub.cfg (mode mirror) ou un menu safe.
- Lancer QEMU (BIOS/UEFI) pour afficher le menu GRUB dans un rendu proche du réel.

Ce module ne dépend PAS de GTK (UI) et lève des exceptions core.
"""

from __future__ import annotations

import os
import pwd
import re
import shutil
import subprocess
import tempfile
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from core.config.core_config_paths import discover_grub_cfg_paths
from core.core_exceptions import GrubCommandError, GrubConfigError

_MENU_COLOR_RE = re.compile(r"^\s*set\s+menu_color_(normal|highlight)\s*=\s*([^\s#]+)")
_BG_COLOR_RE = re.compile(r"^\s*background_color\s+([^#]+)")
_MENUENTRY_RE = re.compile(r"^\s*menuentry\s+(['\"])(.*?)\1")
_SUBMENU_RE = re.compile(r"^\s*submenu\s+(['\"])(.*?)\1")
_TIMEOUT_RE = re.compile(r"^\s*set\s+timeout\s*=\s*(\d+)")
_THEME_SET_RE = re.compile(r"^\s*set\s+theme\s*=\s*(.+?)\s*$")

_SEARCH_RE = re.compile(r"^\s*search\b")
_SET_ROOT_RE = re.compile(r"^\s*set\s+root\s*=\s*.*$")
_SET_PREFIX_RE = re.compile(r"^\s*set\s+prefix\s*=\s*.*$")


@dataclass(frozen=True, slots=True)
class QemuPreviewOptions:
    """Options de preview QEMU."""

    mode: str = "mirror"  # mirror|safe
    firmware: str = "auto"  # auto|bios|uefi
    display: str = "sdl"
    memory_mb: int = 512
    timeout: int = 30


@dataclass(frozen=True, slots=True)
class ExtractedVisuals:
    """Valeurs visuelles extraites d'un grub.cfg (couleurs/timeout)."""

    menu_color_normal: str | None
    menu_color_highlight: str | None
    background_color: str | None
    timeout: int | None


@dataclass(frozen=True, slots=True)
class ExtractedTheme:
    """Thème extrait d'un grub.cfg et chemin résolu vers theme.txt."""

    theme_expr: str | None
    resolved_theme_txt: Path | None
    iso_theme_txt: str | None


def _strip_quotes(value: str) -> str:
    v = (value or "").strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    return v


def extract_visuals_from_grub_cfg(text: str) -> ExtractedVisuals:
    """Extrait les couleurs et le timeout depuis un grub.cfg (best-effort)."""
    menu_normal: str | None = None
    menu_highlight: str | None = None
    background_color: str | None = None
    timeout: int | None = None

    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        m = _MENU_COLOR_RE.match(raw)
        if m:
            kind, value = m.group(1), m.group(2).strip()
            if kind == "normal":
                menu_normal = value
            else:
                menu_highlight = value
            continue

        m = _BG_COLOR_RE.match(raw)
        if m:
            background_color = m.group(1).strip()
            continue

        m = _TIMEOUT_RE.match(raw)
        if m:
            try:
                timeout = int(m.group(1))
            except ValueError:
                pass

    return ExtractedVisuals(
        menu_color_normal=menu_normal,
        menu_color_highlight=menu_highlight,
        background_color=background_color,
        timeout=timeout,
    )


def extract_entry_titles_from_grub_cfg(text: str) -> list[str]:
    """Retourne les titres des menuentry/submenu rencontrés (ordre d'apparition)."""
    titles: list[str] = []

    for raw in (text or "").splitlines():
        if not raw.strip():
            continue

        m = _MENUENTRY_RE.match(raw)
        if m:
            titles.append(m.group(2))
            continue

        m = _SUBMENU_RE.match(raw)
        if m:
            titles.append(m.group(2))

    return titles


def build_preview_grub_cfg(*, source_grub_cfg_text: str, force_timeout: int = 30) -> str:
    """Construit un grub.cfg non bootable (mode safe) basé sur le grub.cfg source."""
    visuals = extract_visuals_from_grub_cfg(source_grub_cfg_text)
    titles = extract_entry_titles_from_grub_cfg(source_grub_cfg_text)

    menu_normal = visuals.menu_color_normal or "white/black"
    menu_highlight = visuals.menu_color_highlight or "black/light-gray"
    bg_cmd = f"background_color {visuals.background_color}" if visuals.background_color else ""

    preview_entries: list[str] = []
    for idx, title in enumerate(titles[:60]):
        safe_title = title.replace('"', "'")
        preview_entries.append(
            "\n".join(
                [
                    f'menuentry "{safe_title}" --id=preview_{idx} {{',
                    "  echo 'Preview QEMU: cette entrée est non bootable.'",
                    "  echo 'Appuie sur ESC pour revenir au menu.'",
                    "  sleep -1",
                    "}",
                ]
            )
        )

    preview_entries.append("\n".join(['menuentry "Quitter (halt)" {', "  halt", "}"]))
    preview_entries.append("\n".join(['menuentry "Redémarrer" {', "  reboot", "}"]))

    return (
        "\n".join(
            [
                "# grub.cfg généré pour preview QEMU (mode safe)",
                "set default=0",
                f"set timeout={force_timeout}",
                "",
                "insmod all_video",
                "insmod gfxterm",
                "terminal_output gfxterm",
                "",
                f"set menu_color_normal={menu_normal}",
                f"set menu_color_highlight={menu_highlight}",
                *([bg_cmd] if bg_cmd else []),
                "",
                "\n\n".join(preview_entries),
                "",
            ]
        ).strip()
        + "\n"
    )


def _resolve_theme_txt_path(*, theme_expr: str, source_cfg_path: Path) -> Path | None:
    raw = _strip_quotes(theme_expr)
    if not raw:
        return None

    raw = raw.replace("${prefix}", "/boot/grub").replace("$prefix", "/boot/grub")
    raw = raw.replace("${grub_prefix}", "/boot/grub").replace("$grub_prefix", "/boot/grub")
    raw = re.sub(r"^\([^\)]+\)", "", raw).strip()

    p = Path(raw)
    if not p.is_absolute():
        p = (source_cfg_path.parent / raw).resolve()

    try:
        return p if p.exists() and p.is_file() else None
    except OSError:
        return None


def extract_theme_from_grub_cfg(*, text: str, source_cfg_path: Path) -> ExtractedTheme:
    """Extrait et résout `set theme=...` depuis un grub.cfg (best-effort)."""
    theme_expr: str | None = None
    for raw in (text or "").splitlines():
        m = _THEME_SET_RE.match(raw)
        if m:
            theme_expr = m.group(1).strip()

    resolved = (
        _resolve_theme_txt_path(theme_expr=theme_expr or "", source_cfg_path=source_cfg_path) if theme_expr else None
    )
    iso_theme_txt: str | None = None

    if resolved is not None:
        try:
            rel = resolved.relative_to(Path("/boot/grub"))
            iso_theme_txt = f"$prefix/{rel.as_posix()}"
        except ValueError:
            iso_theme_txt = "$prefix/themes/host-theme/theme.txt"

    return ExtractedTheme(theme_expr=theme_expr, resolved_theme_txt=resolved, iso_theme_txt=iso_theme_txt)


def sanitize_grub_cfg_for_iso(
    *,
    grub_cfg_text: str,
    theme: ExtractedTheme | None,
    force_timeout: int,
) -> str:
    """Nettoie un grub.cfg hôte pour être chargé depuis l'ISO (cd0).

    Retire les directives qui dépendent du disque hôte (search/set root/prefix),
    force un timeout et réécrit la ligne `set theme` si possible.
    """
    out: list[str] = []

    for raw in (grub_cfg_text or "").splitlines():
        if _SEARCH_RE.match(raw) or _SET_ROOT_RE.match(raw) or _SET_PREFIX_RE.match(raw):
            continue

        if _TIMEOUT_RE.match(raw):
            out.append(f"set timeout={force_timeout}")
            continue

        m = _THEME_SET_RE.match(raw)
        if m:
            original_expr = m.group(1).strip()
            if theme and theme.iso_theme_txt:
                out.append(f"set theme={theme.iso_theme_txt}")
                continue

            normalized = _strip_quotes(original_expr)
            normalized = normalized.replace("${prefix}", "$prefix")
            normalized = re.sub(r"^\([^\)]+\)", "", normalized).strip()
            if normalized.startswith("/boot/grub/"):
                normalized = "$prefix/" + normalized.removeprefix("/boot/grub/")
            if "/themes/" in normalized and not normalized.startswith("$prefix/"):
                idx = normalized.find("/themes/")
                normalized = "$prefix" + normalized[idx:]
            out.append(f"set theme={normalized}")
            continue

        out.append(raw)

    return "\n".join(out).rstrip() + "\n"


def build_wrapper_grub_cfg(*, real_cfg_relpath: str = "real_grub.cfg") -> str:
    """Construit un grub.cfg wrapper qui chain-load un grub.cfg sanitisé."""
    return "\n".join(
        [
            "# grub.cfg wrapper (preview QEMU)",
            "insmod all_video",
            "insmod gfxterm",
            "insmod gfxmenu",
            "insmod png",
            "insmod jpeg",
            "terminal_output gfxterm",
            "",
            "set root=cd0",
            "set prefix=(cd0)/boot/grub",
            "",
            f"configfile $prefix/{real_cfg_relpath}",
            "",
            'menuentry "Preview (fallback)" {',
            "  echo 'Impossible de charger le grub.cfg réel (sanitisé).'",
            "  sleep -1",
            "}",
            "",
        ]
    )


def _copy_boot_grub_assets_into_iso(*, iso_root: Path) -> None:
    host_boot_grub = Path("/boot/grub")
    if not host_boot_grub.exists():
        return

    dst_boot_grub = iso_root / "boot" / "grub"
    dst_boot_grub.mkdir(parents=True, exist_ok=True)

    for name in ("themes", "fonts", "locale"):
        src = host_boot_grub / name
        dst = dst_boot_grub / name
        if not src.exists() or not src.is_dir():
            continue
        try:
            shutil.copytree(src, dst, dirs_exist_ok=True)
        except TypeError:
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        except OSError:
            continue

    for fname in ("unicode.pf2",):
        srcf = host_boot_grub / fname
        dstf = dst_boot_grub / fname
        try:
            if srcf.exists() and srcf.is_file() and not dstf.exists():
                shutil.copy2(srcf, dstf)
        except OSError:
            pass


def _copy_theme_into_iso(*, iso_root: Path, theme: ExtractedTheme) -> None:
    if theme.resolved_theme_txt is None:
        return

    src_theme_txt = theme.resolved_theme_txt
    src_theme_dir = src_theme_txt.parent
    grub_dir = iso_root / "boot" / "grub"

    try:
        rel = src_theme_txt.relative_to(Path("/boot/grub"))
        dst_theme_txt = grub_dir / rel
        dst_theme_dir = dst_theme_txt.parent
    except ValueError:
        dst_theme_dir = grub_dir / "themes" / "host-theme"
        dst_theme_txt = dst_theme_dir / "theme.txt"

    dst_theme_dir.parent.mkdir(parents=True, exist_ok=True)
    if dst_theme_dir.exists():
        shutil.rmtree(dst_theme_dir)
    shutil.copytree(src_theme_dir, dst_theme_dir)

    if not dst_theme_txt.exists():
        dst_theme_txt.write_text(src_theme_txt.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")


def _write_iso_tree_mirror(*, iso_root: Path, wrapper_cfg: str, real_cfg: str, theme: ExtractedTheme) -> None:
    grub_dir = iso_root / "boot" / "grub"
    grub_dir.mkdir(parents=True, exist_ok=True)

    (grub_dir / "grub.cfg").write_text(wrapper_cfg, encoding="utf-8")
    (grub_dir / "real_grub.cfg").write_text(real_cfg, encoding="utf-8")

    _copy_boot_grub_assets_into_iso(iso_root=iso_root)
    _copy_theme_into_iso(iso_root=iso_root, theme=theme)


def _build_grub_preview_iso(*, iso_root: Path, output_iso: Path) -> None:
    output_iso.parent.mkdir(parents=True, exist_ok=True)
    if output_iso.exists() and not os.access(output_iso, os.W_OK):
        subprocess.run(["rm", "-f", str(output_iso)], check=False)

    cmd = ["grub-mkrescue", "-o", str(output_iso), str(iso_root)]
    try:
        # Capture stdout/stderr pour éviter le bruit (xorriso) dans le terminal de l'app.
        # En cas d'échec, on remonte le stderr.
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise GrubCommandError(
            "grub-mkrescue a échoué",
            command=" ".join(cmd),
            stderr=(exc.stderr or exc.stdout or str(exc)).strip(),
        ) from exc
    except OSError as exc:
        raise GrubCommandError("grub-mkrescue a échoué", command=" ".join(cmd), stderr=str(exc)) from exc


def _resolve_ovmf_paths() -> tuple[Path, Path]:
    base = Path("/usr/share/OVMF")
    code = next((p for p in [base / "OVMF_CODE_4M.fd", base / "OVMF_CODE.fd"] if p.exists()), None)
    vars_ = next((p for p in [base / "OVMF_VARS_4M.fd", base / "OVMF_VARS.fd"] if p.exists()), None)
    if code is None or vars_ is None:
        raise GrubCommandError("OVMF introuvable (installe le paquet ovmf)")
    return code, vars_


def _clean_env_for_qemu(env: Mapping[str, str]) -> dict[str, str]:
    """Retourne un env minimal pour QEMU (évite les variables GTK/Snap)."""
    cleaned = dict(env)
    for key in (
        "GTK_MODULES",
        "GTK_PATH",
        "GTK_EXE_PREFIX",
        "GIO_MODULE_DIR",
        "GSETTINGS_SCHEMA_DIR",
        "LOCPATH",
    ):
        cleaned.pop(key, None)
    return cleaned


class GrubQemuPreviewService:
    """Service core: construit et lance la preview QEMU."""

    def __init__(self, *, base_dir: Path | None = None) -> None:
        """Crée le service.

        Args:
            base_dir: Dossier racine (work/out). Par défaut sous /tmp.
        """
        self.base_dir = base_dir or Path("/tmp/grub_manager_qemu_preview")

    def _resolve_source_cfg(self, source_cfg_path: Path | None) -> Path:
        if source_cfg_path and source_cfg_path.exists():
            return source_cfg_path

        for p in discover_grub_cfg_paths():
            path = Path(p)
            if path.exists():
                return path

        raise GrubConfigError("Impossible de trouver grub.cfg (ex: /boot/grub/grub.cfg)")

    def build_iso(self, *, source_cfg_path: Path | None, options: QemuPreviewOptions) -> Path:
        """Construit l'ISO de preview pour les options données."""
        source_cfg = self._resolve_source_cfg(source_cfg_path)
        try:
            text = source_cfg.read_text(encoding="utf-8", errors="ignore")
        except (OSError, PermissionError) as exc:
            raise GrubConfigError(f"Impossible de lire {source_cfg}: {exc}") from exc

        work_dir = self.base_dir / "work"
        iso_root = work_dir / "iso_root"
        output_iso = self.base_dir / "out" / "grub-preview.iso"

        work_dir.mkdir(parents=True, exist_ok=True)

        if iso_root.exists():
            try:
                shutil.rmtree(iso_root)
            except PermissionError as exc:
                raise GrubConfigError(f"Impossible de nettoyer {iso_root}: {exc}") from exc
        iso_root.mkdir(parents=True, exist_ok=True)

        if options.mode == "safe":
            cfg = build_preview_grub_cfg(source_grub_cfg_text=text, force_timeout=options.timeout)
            grub_dir = iso_root / "boot" / "grub"
            grub_dir.mkdir(parents=True, exist_ok=True)
            (grub_dir / "grub.cfg").write_text(cfg, encoding="utf-8")
        elif options.mode == "mirror":
            theme = extract_theme_from_grub_cfg(text=text, source_cfg_path=source_cfg)
            real_cfg = sanitize_grub_cfg_for_iso(grub_cfg_text=text, theme=theme, force_timeout=options.timeout)
            wrapper_cfg = build_wrapper_grub_cfg(real_cfg_relpath="real_grub.cfg")
            _write_iso_tree_mirror(iso_root=iso_root, wrapper_cfg=wrapper_cfg, real_cfg=real_cfg, theme=theme)
        else:
            raise GrubConfigError(f"Mode preview inconnu: {options.mode}")

        _build_grub_preview_iso(iso_root=iso_root, output_iso=output_iso)

        # Si l'appli tourne en root, QEMU sera idéalement lancé en user: l'ISO doit être lisible.
        try:
            output_iso.chmod(0o644)
            output_iso.parent.chmod(0o755)
        except OSError:
            pass
        return output_iso

    def _resolve_firmware(self, options: QemuPreviewOptions) -> str:
        firmware = options.firmware
        if firmware == "auto":
            return "uefi" if Path("/sys/firmware/efi").exists() else "bios"
        return firmware

    def _resolve_target_user(self) -> tuple[int | None, str | None]:
        if os.geteuid() != 0:
            return None, None

        target_uid_raw = os.environ.get("PKEXEC_UID") or os.environ.get("SUDO_UID")
        if not target_uid_raw or not target_uid_raw.isdigit():
            return None, None

        target_uid = int(target_uid_raw)
        if target_uid == 0:
            return None, None

        try:
            target_user = pwd.getpwuid(target_uid).pw_name
        except (KeyError, OSError):
            target_user = None
        return target_uid, target_user

    def _build_qemu_cmd_base(self, options: QemuPreviewOptions) -> list[str]:
        return [
            "qemu-system-x86_64",
            "-display",
            options.display,
            "-m",
            str(options.memory_mb),
        ]

    def _add_uefi_firmware(self, *, qemu_cmd: list[str], target_uid: int | None) -> tuple[list[str], list[Path]]:
        ovmf_code, ovmf_vars = _resolve_ovmf_paths()
        vars_copy_dir = Path(tempfile.mkdtemp(prefix="grub-preview-ovmf-"))
        vars_copy = vars_copy_dir / "OVMF_VARS.fd"
        shutil.copy2(ovmf_vars, vars_copy)

        # Si on prévoit de lancer QEMU en user, rendre le fichier accessible à cet user.
        if target_uid is not None:
            try:
                os.chmod(vars_copy_dir, 0o755)
                os.chmod(vars_copy, 0o644)
                os.chown(vars_copy_dir, target_uid, -1)
                os.chown(vars_copy, target_uid, -1)
            except OSError:
                # Best-effort: si ça échoue, QEMU en user pourra échouer.
                pass

        qemu_cmd = [
            *qemu_cmd,
            "-machine",
            "q35",
            "-drive",
            f"if=pflash,format=raw,readonly=on,file={ovmf_code}",
            "-drive",
            f"if=pflash,format=raw,file={vars_copy}",
        ]
        return qemu_cmd, [vars_copy_dir]

    def _wrap_cmd_for_user(self, *, qemu_cmd: list[str], target_user: str | None) -> list[str]:
        if os.geteuid() != 0 or not target_user:
            return list(qemu_cmd)
        if shutil.which("runuser"):
            return ["runuser", "-u", target_user, "--", *qemu_cmd]
        if shutil.which("sudo"):
            return ["sudo", "-u", target_user, "--", *qemu_cmd]
        return list(qemu_cmd)

    def _schedule_cleanup(self, *, proc: subprocess.Popen, cleanup_paths: list[Path]) -> None:
        if not cleanup_paths:
            return

        def _cleanup() -> None:
            try:
                proc.wait(timeout=None)
            finally:
                for p in cleanup_paths:
                    try:
                        shutil.rmtree(p, ignore_errors=True)
                    except OSError:
                        pass

        threading.Thread(target=_cleanup, daemon=True).start()

    def launch_qemu(self, *, iso_path: Path, options: QemuPreviewOptions) -> subprocess.Popen:
        """Lance QEMU pour booter l'ISO de preview."""
        if not shutil.which("qemu-system-x86_64"):
            raise GrubCommandError("qemu-system-x86_64 introuvable (installe qemu-system-x86)")

        firmware = self._resolve_firmware(options)
        if firmware not in {"uefi", "bios"}:
            raise GrubCommandError(f"Firmware inconnue: {firmware}")

        target_uid, target_user = self._resolve_target_user()
        qemu_cmd = self._build_qemu_cmd_base(options)
        cleanup_paths: list[Path] = []

        if firmware == "uefi":
            qemu_cmd, cleanup_paths = self._add_uefi_firmware(qemu_cmd=qemu_cmd, target_uid=target_uid)

        qemu_cmd += ["-cdrom", str(iso_path), "-boot", "d"]

        env = _clean_env_for_qemu(os.environ)
        cmd = self._wrap_cmd_for_user(qemu_cmd=qemu_cmd, target_user=target_user)
        try:
            proc = subprocess.Popen(cmd, env=env)  # pylint: disable=consider-using-with
            self._schedule_cleanup(proc=proc, cleanup_paths=cleanup_paths)
            return proc
        except OSError as exc:
            raise GrubCommandError("Impossible de lancer QEMU", command=" ".join(cmd), stderr=str(exc)) from exc

    def start_preview(
        self, *, source_cfg_path: Path | None = None, options: QemuPreviewOptions | None = None
    ) -> subprocess.Popen:
        """Construit l'ISO puis lance QEMU (helper one-shot)."""
        opts = options or QemuPreviewOptions()
        iso = self.build_iso(source_cfg_path=source_cfg_path, options=opts)
        return self.launch_qemu(iso_path=iso, options=opts)
