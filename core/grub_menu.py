"""Extraction des entrées GRUB depuis grub.cfg (lecture seule).

Objectif: alimenter l'UI (liste des choix possibles pour GRUB_DEFAULT) sans jamais
modifier grub.cfg.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from glob import glob

from loguru import logger

from .paths import GRUB_CFG_PATH, GRUB_CFG_PATHS


@dataclass(frozen=True)
class GrubDefaultChoice:
    """Choix possible pour GRUB_DEFAULT.

    id: valeur GRUB_DEFAULT (ex: "0", "saved", "1>2" pour sous-menu)
    title: libellé affichable (inclut le chemin de sous-menu si besoin)
    source: script d'origine (ex: "10_linux", "30_os-prober")
    """

    id: str
    title: str
    menu_id: str = ""
    source: str = ""


@dataclass
class _Scope:
    """État de parsing pour un niveau de sous-menu."""

    prefix: list[int]
    titles: list[str]
    next_index: int
    start_depth: int


_MENUENTRY_RE = re.compile(r"^\s*menuentry\b.*?['\"]([^'\"]+)['\"]")
_SUBMENU_RE = re.compile(r"^\s*submenu\b.*?['\"]([^'\"]+)['\"]")
_MENUENTRY_ID_RE = re.compile(r"\s--id(?:=|\s+)(['\"]?)([^'\"\s]+)\1")
_MENUENTRY_DYNAMIC_ID_RE = re.compile(r"\$\{?menuentry_id_option\}?\s+['\"]([^'\"]+)['\"]")
_SECTION_BEGIN_RE = re.compile(r"^### BEGIN /etc/grub\.d/(\S+) ###")


def _extract_menuentry_id(line: str) -> str:
    m = _MENUENTRY_ID_RE.search(line)
    if m:
        return m.group(2)
    m = _MENUENTRY_DYNAMIC_ID_RE.search(line)
    if m:
        return m.group(1)
    return ""


def _discover_efi_grub_cfg_paths() -> list[str]:
    """Découvre des candidats `grub.cfg` EFI sous `/boot/efi/EFI/*/grub.cfg`.

    Certains systèmes (notamment UEFI) exposent aussi un `grub.cfg` sous la
    partition EFI. Il peut s'agir d'un stub (sans `menuentry`) ou du vrai.
    On l'ajoute en candidats *après* les chemins classiques.
    """
    return sorted(glob("/boot/efi/EFI/*/grub.cfg"))


def _candidate_grub_cfg_paths(path: str) -> list[str]:
    """Retourne une liste ordonnée de chemins candidats pour `grub.cfg`."""
    if path == GRUB_CFG_PATH:
        # Même logique que Grub_utils: conserver l'ordre des chemins standards.
        ordered: list[str] = []
        for p in [*GRUB_CFG_PATHS, *_discover_efi_grub_cfg_paths()]:
            if p not in ordered:
                ordered.append(p)
        return ordered
    return [path]


def _iter_readable_grub_cfg_lines(candidates: list[str]):
    """Yield (path, lines) pour chaque candidat existant et lisible."""
    logger.debug(f"[_iter_readable_grub_cfg_lines] Recherche parmi {len(candidates)} candidats")
    existing = [p for p in candidates if os.path.exists(p)]
    if not existing:
        logger.warning(f"[_iter_readable_grub_cfg_lines] grub.cfg introuvable (candidats: {', '.join(candidates)})")
        return

    last_error: OSError | None = None
    for candidate in existing:
        try:
            logger.debug(f"[_iter_readable_grub_cfg_lines] Lecture {candidate}")
            with open(candidate, encoding="utf-8", errors="replace") as f:
                yield candidate, f.read().splitlines()
        except OSError as e:
            last_error = e
            logger.warning(f"[_iter_readable_grub_cfg_lines] Impossible de lire {candidate}: {e}")

    if last_error:
        logger.warning(f"[_iter_readable_grub_cfg_lines] ERREUR: {last_error} (uid={os.geteuid()})")
    return


def _parse_choices(lines: list[str]) -> list[GrubDefaultChoice]:
    """Parse les lignes de grub.cfg en choix `GRUB_DEFAULT`."""
    logger.debug(f"[_parse_choices] Parsing {len(lines)} lignes")
    choices: list[GrubDefaultChoice] = []

    brace_depth = 0
    stack: list[_Scope] = [_Scope(prefix=[], titles=[], next_index=0, start_depth=0)]
    current_source = "unknown"

    for line in lines:
        m_section = _SECTION_BEGIN_RE.match(line)
        if m_section:
            current_source = m_section.group(1)
            continue

        m_sub = _SUBMENU_RE.match(line)
        if m_sub:
            title = m_sub.group(1)
            idx = stack[-1].next_index
            stack[-1].next_index += 1

            start_depth = brace_depth
            opens = line.count("{")
            closes = line.count("}")
            brace_depth += opens - closes

            stack.append(
                _Scope(
                    prefix=[*stack[-1].prefix, idx],
                    titles=[*stack[-1].titles, title],
                    next_index=0,
                    start_depth=start_depth,
                )
            )

            while len(stack) > 1 and brace_depth <= stack[-1].start_depth:
                stack.pop()
            continue

        m_ent = _MENUENTRY_RE.match(line)
        if m_ent:
            title = m_ent.group(1)
            menu_id = _extract_menuentry_id(line)
            idx = stack[-1].next_index
            stack[-1].next_index += 1

            id_parts = [*stack[-1].prefix, idx]
            choice_id = ">".join(str(i) for i in id_parts)

            if stack[-1].titles:
                display = " > ".join([*stack[-1].titles, title])
            else:
                display = title

            choices.append(GrubDefaultChoice(id=choice_id, title=display, menu_id=menu_id, source=current_source))

        opens = line.count("{")
        closes = line.count("}")
        brace_depth += opens - closes

        while len(stack) > 1 and brace_depth <= stack[-1].start_depth:
            stack.pop()

    logger.debug(f"[_parse_choices] Succès - {len(choices)} choix extraits")
    return choices


def read_grub_default_choices(path: str = GRUB_CFG_PATH) -> list[GrubDefaultChoice]:
    """Extrait les entrées GRUB depuis `grub.cfg`.

    Le fichier n'est jamais modifié; il sert uniquement à construire la liste de
    choix valides pour `GRUB_DEFAULT` (ex: "0", "1>2").
    """
    choices, _used = read_grub_default_choices_with_source(path)
    return choices


def read_grub_default_choices_with_source(path: str = GRUB_CFG_PATH) -> tuple[list[GrubDefaultChoice], str | None]:
    """Comme `read_grub_default_choices`, mais renvoie aussi le chemin réellement lu."""
    logger.debug(f"[read_grub_default_choices_with_source] Debut - path={path}")
    candidates = _candidate_grub_cfg_paths(path)
    best_empty: tuple[str, list[str]] | None = None
    for used_path, lines in _iter_readable_grub_cfg_lines(candidates):
        choices = _parse_choices(lines)
        if choices:
            if used_path != path:
                logger.info(f"grub.cfg utilisé: {used_path}")
            logger.success(f"[read_grub_default_choices_with_source] {len(choices)} entrées trouvées")
            return choices, used_path
        if best_empty is None:
            best_empty = (used_path, lines)

    # Tous les fichiers lisibles n'ont donné aucune entrée.
    if best_empty is not None:
        used_path, _ = best_empty
        if used_path != path:
            logger.info(f"grub.cfg utilisé (vide): {used_path}")
        logger.warning(f"[read_grub_default_choices_with_source] Aucune entrée trouvée dans {used_path}")
        return [], used_path
    logger.error("[read_grub_default_choices_with_source] ERREUR: Impossible de lire grub.cfg")
    return [], None


def get_simulated_os_prober_entries() -> list[GrubDefaultChoice]:
    """Exécute os-prober et retourne des entrées simulées."""
    logger.debug("[get_simulated_os_prober_entries] Début")
    if os.geteuid() != 0:
        logger.warning(f"[get_simulated_os_prober_entries] os-prober nécessite les droits root (uid={os.geteuid()})")
        return []

    os_prober_cmd = shutil.which("os-prober")
    if not os_prober_cmd:
        logger.debug("[get_simulated_os_prober_entries] os-prober non trouvé")
        return []

    try:
        # os-prober output format: /dev/sda1:Windows 10:Windows:chain
        logger.debug("[get_simulated_os_prober_entries] Exécution os-prober")
        result = subprocess.run([os_prober_cmd], capture_output=True, text=True, check=False)
        logger.debug(f"[get_simulated_os_prober_entries] Résultat: returncode={result.returncode}")
        if result.returncode != 0 or not result.stdout:
            logger.debug("[get_simulated_os_prober_entries] Aucun OS détecté")
            return []

        entries = []
        for line in result.stdout.splitlines():
            parts = line.split(":")
            if len(parts) >= 2:
                # On crée un ID simulé. Note: le vrai ID dépend de grub-mkconfig (UUID, etc.)
                # Ici on veut juste afficher quelque chose.
                title = f"{parts[1]} (détecté)"
                # L'ID réel est souvent 'osprober-chain-UUID' ou 'osprober-gnulinux-...'
                # On met un placeholder qui sera reconnu par _entry_is_os_prober
                fake_id = f"osprober-simulated-{parts[0]}"
                logger.debug(f"[get_simulated_os_prober_entries] Détecté: {title}")
                entries.append(GrubDefaultChoice(id=fake_id, title=title, menu_id=fake_id, source="30_os-prober"))
        logger.success(f"[get_simulated_os_prober_entries] {len(entries)} OS détecté(s)")
        return entries
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"[get_simulated_os_prober_entries] ERREUR: {e}")
        return []
