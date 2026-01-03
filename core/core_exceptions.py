"""Module d'exceptions personnalisées pour Grub Manager.

Fournit une hiérarchie d'exceptions spécifiques pour une gestion
d'erreurs plus fine et un diagnostic amélioré.
"""

from __future__ import annotations


class GrubManagerError(Exception):
    """Exception de base pour toutes les erreurs de Grub Manager.

    Toutes les exceptions spécifiques à l'application héritent de cette classe.
    Permet de capturer toutes les erreurs métier avec `except GrubManagerError`.

    Example:
        try:
            perform_grub_operation()
        except GrubManagerError as e:
            logger.error(f"Erreur GRUB: {e}")
    """


class GrubConfigError(GrubManagerError):
    """Erreur liée à la configuration GRUB.

    Levée lorsque des fichiers de configuration GRUB sont invalides,
    manquants ou corrompus.

    Example:
        if not grub_cfg_path.exists():
            raise GrubConfigError(f"Fichier de configuration introuvable: {grub_cfg_path}")
    """


class GrubScriptNotFoundError(GrubManagerError):
    """Script GRUB introuvable.

    Levée lorsqu'un script dans /etc/grub.d est manquant.

    Example:
        if not script_path.exists():
            raise GrubScriptNotFoundError(f"Script introuvable: {script_path}")
    """


class GrubPermissionError(GrubManagerError):
    """Permissions insuffisantes pour une opération GRUB.

    Levée lorsque l'opération nécessite des privilèges root.

    Example:
        if os.geteuid() != 0:
            raise GrubPermissionError("Cette opération nécessite les privilèges root")
    """


class GrubParsingError(GrubManagerError):
    """Erreur lors du parsing de fichiers GRUB.

    Levée lorsque le parsing de grub.cfg ou /etc/default/grub échoue.

    Example:
        if not valid_syntax(grub_cfg_content):
            raise GrubParsingError(f"Syntaxe invalide ligne {line_number}")
    """


class GrubBackupError(GrubManagerError):
    """Erreur lors de la gestion des sauvegardes.

    Levée lorsqu'une sauvegarde ne peut pas être créée ou restaurée.

    Example:
        if not backup_created:
            raise GrubBackupError(f"Impossible de créer la sauvegarde: {reason}")
    """


class GrubThemeError(GrubManagerError):
    """Erreur liée aux thèmes GRUB.

    Levée lorsqu'un thème est invalide ou que son installation échoue.

    Example:
        if not theme_txt.exists():
            raise GrubThemeError(f"theme.txt manquant dans {theme_dir}")
    """


class GrubCommandError(GrubManagerError):
    """Erreur lors de l'exécution de commandes GRUB.

    Levée lorsqu'une commande système (grub-install, update-grub) échoue.

    Attributes:
        command: La commande qui a échoué
        returncode: Code de retour
        stderr: Sortie d'erreur

    Example:
        result = subprocess.run(["update-grub"], capture_output=True)
        if result.returncode != 0:
            raise GrubCommandError(
                f"update-grub a échoué: {result.stderr.decode()}"
            )
    """

    def __init__(
        self,
        message: str,
        command: str | None = None,
        returncode: int | None = None,
        stderr: str | None = None,
    ):
        """Initialise GrubCommandError avec contexte de la commande.

        Args:
            message: Message d'erreur descriptif
            command: Commande qui a échoué (optionnel)
            returncode: Code de retour de la commande (optionnel)
            stderr: Sortie d'erreur (optionnel)
        """
        super().__init__(message)
        self.command = command
        self.returncode = returncode
        self.stderr = stderr

    def __str__(self) -> str:
        """Représentation textuelle enrichie de l'erreur."""
        parts = [super().__str__()]
        if self.command:
            parts.append(f"Commande: {self.command}")
        if self.returncode is not None:
            parts.append(f"Code retour: {self.returncode}")
        if self.stderr:
            parts.append(f"Stderr: {self.stderr[:200]}")  # Limiter la taille
        return " | ".join(parts)


class GrubSyncError(GrubManagerError):
    """Erreur de synchronisation entre configuration et grub.cfg.

    Levée lorsque /etc/default/grub et /boot/grub/grub.cfg sont désynchronisés.

    Example:
        if not is_synced:
            raise GrubSyncError("Fichiers désynchronisés, exécutez update-grub")
    """


class GrubValidationError(GrubManagerError):
    """Erreur de validation de données utilisateur.

    Levée lorsque des données saisies par l'utilisateur sont invalides.

    Example:
        if timeout < 0:
            raise GrubValidationError("Le timeout doit être >= 0")
    """
