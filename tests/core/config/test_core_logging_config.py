"""Tests pour le module de configuration du logging."""

import sys
from unittest.mock import patch

import pytest

from core.config.core_logging_config import (
    DEBUG,
    INFO,
    WARNING,
    configure_logging,
    set_debug_mode,
    set_production_mode,
    set_silent_mode,
)


class TestLoggingConfig:
    """Tests pour la configuration du logging."""

    @pytest.fixture(autouse=True)
    def mock_logger(self):
        """Mock logger pour éviter les effets de bord."""
        with patch("core.config.core_logging_config.logger") as mock:
            yield mock

    def test_constants(self):
        """Vérifie les constantes de niveau de log."""
        assert DEBUG == "DEBUG"
        assert INFO == "INFO"
        assert WARNING == "WARNING"

    def test_configure_logging_defaults(self, mock_logger):
        """Test la configuration par défaut."""
        configure_logging()

        # Vérifie que remove() est appelé
        mock_logger.remove.assert_called_once()

        # Vérifie que add() est appelé pour stderr et le fichier
        assert mock_logger.add.call_count == 2

        # Vérifie les arguments pour stderr (premier appel)
        args, kwargs = mock_logger.add.call_args_list[0]
        assert args[0] == sys.stderr
        assert kwargs["level"] == INFO
        assert kwargs["diagnose"] is False

    def test_configure_logging_debug(self, mock_logger):
        """Test la configuration en mode debug."""
        configure_logging(level=DEBUG)

        # Vérifie les arguments pour stderr
        args, kwargs = mock_logger.add.call_args_list[0]
        assert kwargs["level"] == DEBUG
        assert kwargs["diagnose"] is True

    def test_configure_logging_no_file(self, mock_logger):
        """Test la configuration sans fichier de log."""
        configure_logging(enable_file_logging=False)

        # Vérifie que add() n'est appelé qu'une fois (pour stderr)
        assert mock_logger.add.call_count == 1

    @patch("core.config.core_logging_config.LOG_DIR")
    def test_configure_logging_creates_dir(self, mock_log_dir, mock_logger):
        """Test que le répertoire de logs est créé."""
        configure_logging(enable_file_logging=True)

        mock_log_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_set_production_mode(self, mock_logger):
        """Test l'activation du mode production."""
        with patch("core.config.core_logging_config.configure_logging") as mock_config:
            set_production_mode()

            mock_config.assert_called_once_with(level=INFO, enable_file_logging=False)
            mock_logger.info.assert_called_with("[Logging] Mode production activé")

    def test_set_debug_mode(self, mock_logger):
        """Test l'activation du mode debug."""
        with patch("core.config.core_logging_config.configure_logging") as mock_config:
            set_debug_mode()

            mock_config.assert_called_once_with(level=DEBUG, enable_file_logging=True)
            mock_logger.debug.assert_called_with("[Logging] Mode debug activé")

    def test_set_silent_mode(self, mock_logger):
        """Test l'activation du mode silencieux."""
        with patch("core.config.core_logging_config.configure_logging") as mock_config:
            set_silent_mode()

            mock_config.assert_called_once_with(level=WARNING, enable_file_logging=False)
            mock_logger.warning.assert_called_with("[Logging] Mode silencieux activé")
