import os
import subprocess
import sys
from unittest.mock import MagicMock

# Désactiver les avertissements de version GTK
import gi
import pytest

try:
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
except (ValueError, ImportError):
    pass

from gi.repository import Adw, GLib, Gtk


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

    # Forcer un backend headless pour GDK si possible
    os.environ["GDK_BACKEND"] = "headless"

    # Mocker Gtk.init pour éviter les plantages sans display
    Gtk.init = MagicMock(return_value=True)

    # Mocker Adw.init
    try:
        Adw.init = MagicMock(return_value=True)
    except:
        pass

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

    print(
        "\n[Conftest] Tests sécurisés: GTK/Adw headless, subprocess bloqués, "
        "limites CPU/RAM actives (env override possible)"
    )


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
def headless_gdk():
    """S'assure que GDK est en mode headless pour chaque test."""
    os.environ["GDK_BACKEND"] = "headless"
    yield
