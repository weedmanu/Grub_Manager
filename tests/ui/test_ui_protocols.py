"""Tests pour les Protocols (interfaces) UI."""

from __future__ import annotations

from unittest.mock import MagicMock

from core.models.core_grub_ui_model import GrubUiModel
from core.system.core_grub_system_commands import GrubDefaultChoice
from ui.ui_protocols import (
    ConfigModelMapper,
    DefaultChoiceWidget,
    InfoDisplay,
    PermissionChecker,
    TimeoutWidget,
)


class MockTimeoutWidget:
    """Implémentation test de TimeoutWidget."""

    def get_timeout_value(self) -> int:
        return 10

    def set_timeout_value(self, value: int) -> None:
        pass

    def sync_timeout_choices(self, _current: int) -> None:
        pass


class MockDefaultChoiceWidget:
    """Implémentation test de DefaultChoiceWidget."""

    def get_default_choice(self) -> str:
        return "saved"

    def set_default_choice(self, value: str) -> None:
        pass

    def refresh_default_choices(self, _choices: list[GrubDefaultChoice], _current: str) -> None:
        pass


class MockConfigModelMapper:
    """Implémentation test de ConfigModelMapper."""

    def apply_model_to_ui(self, model: GrubUiModel, entries: list[GrubDefaultChoice]) -> None:
        pass

    def read_model_from_ui(self) -> GrubUiModel:
        return GrubUiModel()


class MockPermissionChecker:
    """Implémentation test de PermissionChecker."""

    def is_root(self) -> bool:
        return True

    def can_modify_system(self) -> bool:
        return True


class MockInfoDisplay:
    """Implémentation test de InfoDisplay."""

    def show_info(self, _message: str, _level: str = "info") -> None:
        pass

    def hide_info_callback(self) -> bool:
        return True


class TestProtocolsStructure:
    """Tests pour vérifier que les Protocols sont bien formés."""

    def test_timeout_widget_protocol_exists(self):
        """TimeoutWidget Protocol existe et est utilisable."""
        widget = MockTimeoutWidget()
        assert widget.get_timeout_value() == 10
        widget.set_timeout_value(5)
        widget.sync_timeout_choices(5)

    def test_default_choice_widget_protocol_exists(self):
        """DefaultChoiceWidget Protocol existe et est utilisable."""
        widget = MockDefaultChoiceWidget()
        assert widget.get_default_choice() == "saved"
        widget.set_default_choice("0")
        widget.refresh_default_choices([], "0")

    def test_config_model_mapper_protocol_exists(self):
        """ConfigModelMapper Protocol existe et est utilisable."""
        mapper = MockConfigModelMapper()
        mapper.apply_model_to_ui(GrubUiModel(), [])
        model = mapper.read_model_from_ui()
        assert isinstance(model, GrubUiModel)

    def test_permission_checker_protocol_exists(self):
        """PermissionChecker Protocol existe et est utilisable."""
        checker = MockPermissionChecker()
        assert checker.is_root() is True
        assert checker.can_modify_system() is True

    def test_info_display_protocol_exists(self):
        """InfoDisplay Protocol existe et est utilisable."""
        display = MockInfoDisplay()
        display.show_info("Test message")
        assert display.hide_info_callback() is True

    def test_protocol_method_signatures(self):
        """Les méthodes des Protocols ont les bons arguments."""
        # TimeoutWidget
        assert hasattr(TimeoutWidget, "get_timeout_value")
        assert hasattr(TimeoutWidget, "set_timeout_value")
        assert hasattr(TimeoutWidget, "sync_timeout_choices")

        # DefaultChoiceWidget
        assert hasattr(DefaultChoiceWidget, "get_default_choice")
        assert hasattr(DefaultChoiceWidget, "set_default_choice")
        assert hasattr(DefaultChoiceWidget, "refresh_default_choices")

        # ConfigModelMapper
        assert hasattr(ConfigModelMapper, "apply_model_to_ui")
        assert hasattr(ConfigModelMapper, "read_model_from_ui")

        # PermissionChecker
        assert hasattr(PermissionChecker, "is_root")
        assert hasattr(PermissionChecker, "can_modify_system")

        # InfoDisplay
        assert hasattr(InfoDisplay, "show_info")
        assert hasattr(InfoDisplay, "hide_info_callback")


class TestProtocolInheritance:
    """Tests pour vérifier que les classes implémentent les Protocols."""

    def test_grub_config_manager_implements_timeout_widget(self):
        """GrubConfigManager implémente TimeoutWidget."""
        from ui.ui_manager import GrubConfigManager

        required_methods = ["get_timeout_value", "set_timeout_value", "sync_timeout_choices"]
        for method in required_methods:
            assert hasattr(GrubConfigManager, method), f"TimeoutWidget: {method} missing"

    def test_grub_config_manager_implements_default_choice_widget(self):
        """GrubConfigManager implémente DefaultChoiceWidget."""
        from ui.ui_manager import GrubConfigManager

        required_methods = [
            "get_default_choice",
            "set_default_choice",
            "refresh_default_choices",
        ]
        for method in required_methods:
            assert hasattr(GrubConfigManager, method), f"DefaultChoiceWidget: {method} missing"

    def test_grub_config_manager_implements_config_model_mapper(self):
        """GrubConfigManager implémente ConfigModelMapper."""
        from ui.ui_manager import GrubConfigManager

        required_methods = ["apply_model_to_ui", "read_model_from_ui"]
        for method in required_methods:
            assert hasattr(GrubConfigManager, method), f"ConfigModelMapper: {method} missing"

    def test_grub_config_manager_implements_permission_checker(self):
        """GrubConfigManager utilise un PermissionController."""
        from tests.ui.test_ui_manager import GrubConfigManagerFull

        # Utiliser la version test qui n'appelle pas le parent GTK
        app = MagicMock()
        manager = GrubConfigManagerFull(app)

        # Vérifier que le contrôleur de permissions existe
        assert hasattr(manager, "perm_ctrl")
        assert manager.perm_ctrl is not None

    def test_grub_config_manager_implements_info_display(self):
        """GrubConfigManager implémente InfoDisplay."""
        from ui.ui_manager import GrubConfigManager

        required_methods = ["show_info", "hide_info_callback"]
        for method in required_methods:
            assert hasattr(GrubConfigManager, method), f"InfoDisplay: {method} missing"
