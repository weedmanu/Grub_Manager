"""Utilitaires de lazy loading pour optimiser les performances.

Permet de charger les modules et composants lourds uniquement quand nécessaire,
réduisant ainsi le temps de démarrage de l'application.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from types import ModuleType


class LazyLoader:
    """Chargeur lazy pour modules Python."""

    def __init__(self, module_name: str):
        """Initialise le lazy loader.

        Args:
            module_name: Nom complet du module à charger
        """
        self._module_name = module_name
        self._module: ModuleType | None = None
        logger.debug(f"[LazyLoader] Créé pour '{module_name}'")

    def __getattr__(self, name: str) -> Any:
        """Charge le module à la première utilisation.

        Args:
            name: Nom de l'attribut recherché

        Returns:
            Attribut du module chargé
        """
        if self._module is None:
            logger.debug(f"[LazyLoader] Chargement de '{self._module_name}'")
            self._module = importlib.import_module(self._module_name)
            logger.info(f"[LazyLoader] Module '{self._module_name}' chargé")

        return getattr(self._module, name)


class LazyComponent:
    """Wrapper pour composants UI chargés à la demande."""

    def __init__(self, factory: Callable[[], Any]):
        """Initialise le composant lazy.

        Args:
            factory: Fonction de création du composant
        """
        self._factory = factory
        self._instance: Any = None
        logger.debug("[LazyComponent] Composant lazy créé")

    def get(self) -> Any:
        """Retourne l'instance du composant (crée si nécessaire).

        Returns:
            Instance du composant
        """
        if self._instance is None:
            logger.debug("[LazyComponent] Instanciation du composant")
            self._instance = self._factory()
            logger.info("[LazyComponent] Composant instancié")

        return self._instance

    def is_loaded(self) -> bool:
        """Vérifie si le composant a été chargé.

        Returns:
            True si chargé, False sinon
        """
        return self._instance is not None

    def reset(self) -> None:
        """Réinitialise le composant (force le rechargement)."""
        if self._instance:
            logger.debug("[LazyComponent] Réinitialisation du composant")
            self._instance = None


def lazy_import(module_name: str) -> LazyLoader:
    """Crée un loader lazy pour un module.

    Args:
        module_name: Nom du module

    Returns:
        LazyLoader pour ce module

    Example:
        >>> subprocess = lazy_import("subprocess")
        >>> # Le module n'est pas encore chargé
        >>> result = subprocess.run(["echo", "test"])  # Chargement au premier usage
    """
    return LazyLoader(module_name)


def lazy_property(factory: Callable[[Any], Any]) -> property:
    """Décorateur pour créer une propriété lazy.

    Args:
        factory: Fonction de création de la valeur

    Returns:
        Property qui charge à la demande

    Example:
        >>> class MyClass:
        ...     @lazy_property
        ...     def heavy_data(self):
        ...         return load_heavy_data()
    """
    attr_name = f"_lazy_{factory.__name__}"

    def getter(self) -> Any:
        if not hasattr(self, attr_name):
            logger.debug(f"[LazyProperty] Chargement de '{factory.__name__}'")
            setattr(self, attr_name, factory(self))
        return getattr(self, attr_name)

    return property(getter)
