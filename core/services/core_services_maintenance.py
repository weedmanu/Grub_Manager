"""Service de maintenance pour GRUB.

Gère la logique de détection et de génération de commandes pour la maintenance.
"""

import glob
import os
import shutil

from loguru import logger

from core.io.core_io_grub_default import read_grub_default


class MaintenanceService:
    """Service fournissant les commandes et informations de maintenance."""

    def get_restore_command(self) -> tuple[str, list[str]] | None:
        """Détecte le gestionnaire de paquets et retourne la commande de réinstallation.

        Returns:
            Tuple (nom_du_gestionnaire, liste_commande) ou None si aucun n'est trouvé
        """
        logger.debug("[MaintenanceService.get_restore_command] Détection du gestionnaire de paquets")

        if shutil.which("apt-get"):
            return ("APT", ["apt-get", "install", "--reinstall", "grub-common"])

        if shutil.which("pacman"):
            return ("Pacman", ["pacman", "-S", "--noconfirm", "grub"])

        if shutil.which("dnf"):
            return ("DNF", ["dnf", "reinstall", "-y", "grub2-common"])

        if shutil.which("zypper"):
            return ("Zypper", ["zypper", "install", "--force", "grub2"])

        return None

    def get_reinstall_05_debian_command(self) -> list[str] | None:
        """Retourne la commande pour réinstaller le script 05_debian.

        Returns:
            Liste de commande ou None si aucun gestionnaire de paquets n'est trouvé.
        """
        restore_cmd = self.get_restore_command()
        if restore_cmd:
            return restore_cmd[1]
        return None

    def get_enable_05_debian_theme_command(self) -> list[str]:
        """Retourne la commande pour activer le script 05_debian_theme.

        Returns:
            Liste de commande.
        """
        return ["chmod", "+x", "/etc/grub.d/05_debian_theme"]

    def find_theme_script_path(self) -> str | None:
        """Cherche le chemin du script de thème GRUB.

        Returns:
            Chemin absolu du fichier ou None si non trouvé.
        """
        # Lire GRUB_THEME depuis /etc/default/grub
        try:
            config = read_grub_default()
            theme_setting = config.get("GRUB_THEME", "")
            if theme_setting:
                theme_path = theme_setting.strip('"').strip("'")
                if os.path.exists(theme_path):
                    return theme_path
        except OSError:
            pass

        # Chemins de recherche pour le thème
        common_paths = [
            "/boot/grub/themes/*/theme.txt",
            "/boot/grub2/themes/*/theme.txt",
            "/usr/share/grub/themes/*/theme.txt",
        ]

        for pattern in common_paths:
            matches = glob.glob(pattern)
            if matches:
                return matches[0]

        # Chercher dans /etc/grub.d/
        if os.path.exists("/etc/grub.d"):
            for filename in os.listdir("/etc/grub.d"):
                filepath = os.path.join("/etc/grub.d", filename)
                if "theme" in filename.lower() and os.path.isfile(filepath):
                    return filepath

        # Chercher dans les configs custom
        grub_config_patterns = [
            "/boot/grub/custom.cfg",
            "/boot/grub2/custom.cfg",
            "/boot/grub/grub.cfg.d/*.cfg",
            "/boot/grub2/grub.cfg.d/*.cfg",
        ]

        for pattern in grub_config_patterns:
            matches = glob.glob(pattern)
            for match in matches:
                try:
                    with open(match, encoding="utf-8", errors="ignore") as f:
                        content = f.read(500)
                        if "theme" in content.lower():
                            return match
                except OSError:
                    pass

        return None
