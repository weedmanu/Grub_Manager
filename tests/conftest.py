"""Configuration pytest: harnais de tests GTK/Adw avec sécurité.

Active:
- Détection GTK (skip UI si indisponible)
- Mocks GLib timers/idle
- Blocage subprocess (sécurité)
- Limites CPU/RAM Linux (protection machine)
- Faulthandler pour diagnostiquer les hangs
"""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Ajouter le dossier racine du projet au PYTHONPATH
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Désactiver les avertissements de version GTK
import gi
import pytest
from loguru import logger

try:
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
except (ValueError, ImportError):
    pass

from gi.repository import GLib, Gtk


def _can_init_gtk() -> bool:
    """Retourne True si Gtk peut s'initialiser dans l'environnement courant.

    Important: ne pas mocker Gtk.init() dans les tests. Créer des widgets sans
    vraie initialisation peut provoquer un SIGSEGV côté C.
    """
    try:
        init_check = getattr(Gtk, "init_check", None)
        if callable(init_check):
            result = init_check()
            # Gtk.init_check() peut retourner bool ou (bool, argv)
            if isinstance(result, tuple):
                return bool(result[0])
            return bool(result)

        # Fallback
        Gtk.init()
        return True
    except Exception:
        return False


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _apply_resource_limits() -> None:
    """Applique des limites CPU/RAM au process de test (Linux).

    Objectif: éviter qu'un test qui boucle/hang n'épuise la machine.
    Contrôle via env:
      - PYTEST_CPU_LIMIT_SECONDS (défaut 900)
      - PYTEST_MEM_LIMIT_MB (défaut 2048)
      - PYTEST_DISABLE_RESOURCE_LIMITS=1 pour désactiver
    """
    if os.environ.get("PYTEST_DISABLE_RESOURCE_LIMITS") in {"1", "true", "yes"}:
        return

    if sys.platform != "linux":
        return

    try:
        import resource
    except Exception:
        return

    cpu_seconds = _env_int("PYTEST_CPU_LIMIT_SECONDS", 900)
    # RLIMIT_AS limite l'espace d'adressage virtuel (inclut les libs GTK/GI mappées).
    # 2GB peut être trop bas sur certaines machines -> MemoryError aléatoires.
    mem_limit_mb = _env_int("PYTEST_MEM_LIMIT_MB", 8192)
    mem_bytes = int(mem_limit_mb) * 1024 * 1024

    # CPU total du process (sec). Un test bloqué en C finira tué par le kernel.
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
    except Exception:
        pass

    # Mémoire virtuelle max (bytes). Protège contre les fuites/allocations massives.
    try:
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    except Exception:
        pass


def _enable_faulthandler() -> None:
    """Active les dumps de stack en cas de hang/timeout pour garder du contrôle."""
    try:
        import faulthandler

        faulthandler.enable(all_threads=True)
    except Exception:
        pass


def pytest_configure(config):
    """Configuration globale de pytest."""
    _apply_resource_limits()
    _enable_faulthandler()

    # Stabiliser Loguru pendant les tests: pas d'enqueue (thread/queue) pour éviter
    # des crashes lors du shutdown Python/GC.
    try:
        logger.remove()
        logger.add(sys.stderr, enqueue=False)
    except Exception:
        pass

    # Détecter si GTK est réellement utilisable (display/backends dispo).
    # On ne force pas de backend GDK ici: si nécessaire, l'environnement de CI
    # doit fournir un DISPLAY (ex: xvfb) ou configurer GDK_BACKEND.
    config._gtk_available = _can_init_gtk()  # type: ignore[attr-defined]

    # Mocker GLib.timeout_add et timeout_add_seconds pour éviter les timers réels
    GLib.timeout_add = MagicMock(return_value=1)
    GLib.timeout_add_seconds = MagicMock(return_value=1)
    GLib.source_remove = MagicMock(return_value=True)
    GLib.idle_add = MagicMock(return_value=1)

    # Empêcher les fenêtres de s'afficher réellement
    Gtk.Window.present = MagicMock()
    Gtk.Window.show = MagicMock()

    # Empêcher l'affichage des dialogues GTK (peut segfault en headless)
    try:
        Gtk.AlertDialog.show = MagicMock()
    except Exception:
        pass

    status = "OK" if getattr(config, "_gtk_available", False) else "INDISPONIBLE"
    print("\n[Conftest] Tests sécurisés: subprocess bloqués, limites CPU/RAM actives " f"(GTK: {status})")


def pytest_runtest_setup(item):
    """Skip les tests UI si GTK n'est pas initialisable.

    Cela évite des crashes natifs quand l'environnement n'a pas de display.
    """
    try:
        gtk_available = bool(getattr(item.config, "_gtk_available", False))
    except Exception:
        gtk_available = False

    if gtk_available:
        return

    path = str(getattr(item, "fspath", ""))
    if "/tests/ui/" in path.replace("\\", "/"):
        pytest.skip("GTK indisponible (pas de display/backend): tests UI ignorés")


@pytest.fixture(autouse=True)
def secure_subprocess(monkeypatch):
    """Empêche les appels subprocess réels pendant les tests pour éviter de figer le système."""

    def mocked_run(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("args")
        # On autorise les appels si on est explicitement dans un bloc de patch
        # Mais par défaut, on lève une erreur pour la sécurité
        raise RuntimeError(f"SÉCURITÉ : Appel subprocess non autorisé dans les tests : {cmd}")

    # On mocke les principales fonctions de subprocess globalement
    monkeypatch.setattr(subprocess, "run", mocked_run)
    monkeypatch.setattr(subprocess, "Popen", mocked_run)
    monkeypatch.setattr(subprocess, "call", mocked_run)
    monkeypatch.setattr(subprocess, "check_call", mocked_run)
    monkeypatch.setattr(subprocess, "check_output", mocked_run)

    yield


@pytest.fixture(autouse=True)
def keep_gdk_backend_stable():
    """Évite de modifier GDK_BACKEND implicitement pendant les tests."""
    yield


def pytest_sessionfinish(session, exitstatus):
    """Nettoie les ressources globales.

    Important pour Loguru: arrêter proprement les handlers en fin de session.
    """
    # satisfy vulture: arguments required by hook signature
    del session, exitstatus
    try:
        logger.complete()
    except Exception:
        pass
    try:
        logger.remove()
    except Exception:
        pass
