"""Tests pour le module de lazy loading."""

from unittest.mock import MagicMock

from core.config.core_lazy_loading import LazyComponent, LazyLoader, lazy_import, lazy_property


class TestLazyLoader:
    """Tests pour la classe LazyLoader."""

    def test_lazy_loader_initialization(self):
        """Test l'initialisation du LazyLoader."""
        loader = LazyLoader("os")
        assert loader._module_name == "os"
        assert loader._module is None

    def test_lazy_loader_loads_module_on_access(self):
        """Test que le module est chargé lors de l'accès à un attribut."""
        loader = LazyLoader("os")
        assert loader._module is None

        # Accès à un attribut (path)
        path_module = loader.path

        assert loader._module is not None
        assert loader._module.__name__ == "os"
        assert path_module is not None

    def test_lazy_loader_caches_module(self):
        """Test que le module n'est chargé qu'une seule fois."""
        loader = LazyLoader("sys")

        # Premier accès
        _ = loader.version
        module_ref = loader._module

        # Deuxième accès
        _ = loader.platform

        assert loader._module is module_ref

    def test_lazy_import_helper(self):
        """Test la fonction helper lazy_import."""
        loader = lazy_import("json")
        assert isinstance(loader, LazyLoader)
        assert loader._module_name == "json"


class TestLazyComponent:
    """Tests pour la classe LazyComponent."""

    def test_lazy_component_initialization(self):
        """Test l'initialisation du LazyComponent."""
        factory = MagicMock()
        component = LazyComponent(factory)

        assert component._factory == factory
        assert component._instance is None
        assert not component.is_loaded()
        factory.assert_not_called()

    def test_lazy_component_get_creates_instance(self):
        """Test que get() crée l'instance via la factory."""
        expected_instance = "test_instance"
        factory = MagicMock(return_value=expected_instance)
        component = LazyComponent(factory)

        instance = component.get()

        assert instance == expected_instance
        assert component._instance == expected_instance
        assert component.is_loaded()
        factory.assert_called_once()

    def test_lazy_component_get_caches_instance(self):
        """Test que get() retourne l'instance mise en cache."""
        factory = MagicMock(return_value="instance")
        component = LazyComponent(factory)

        instance1 = component.get()
        instance2 = component.get()

        assert instance1 is instance2
        factory.assert_called_once()

    def test_lazy_component_reset(self):
        """Test la réinitialisation du composant."""
        factory = MagicMock(return_value="instance")
        component = LazyComponent(factory)

        component.get()
        assert component.is_loaded()

        component.reset()
        assert not component.is_loaded()
        assert component._instance is None

        # Vérifie qu'on peut recharger après reset
        component.get()
        assert component.is_loaded()
        assert factory.call_count == 2

    def test_lazy_component_reset_when_not_loaded(self):
        """Test la réinitialisation quand le composant n'est pas chargé."""
        factory = MagicMock(return_value="instance")
        component = LazyComponent(factory)

        # Reset sans avoir chargé l'instance
        assert not component.is_loaded()
        component.reset()
        assert not component.is_loaded()
        assert component._instance is None
        factory.assert_not_called()


class TestLazyProperty:
    """Tests pour le décorateur lazy_property."""

    def test_lazy_property_decorator(self):
        """Test le fonctionnement du décorateur lazy_property."""

        class TestClass:
            def __init__(self):
                self.factory_called = 0

            @lazy_property
            def heavy_resource(self):
                self.factory_called += 1
                return "heavy_data"

        obj = TestClass()

        # Vérifie que la factory n'est pas appelée à l'init
        assert obj.factory_called == 0

        # Premier accès
        val1 = obj.heavy_resource
        assert val1 == "heavy_data"
        assert obj.factory_called == 1

        # Deuxième accès (doit utiliser le cache)
        val2 = obj.heavy_resource
        assert val2 == "heavy_data"
        assert obj.factory_called == 1
