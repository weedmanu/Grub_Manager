"""Tests pour core/runtime.py - Utilitaires CLI."""

from __future__ import annotations

from io import StringIO

from core.runtime import configure_logging, parse_debug_flag


class TestParseDebugFlag:
    """Tests pour parse_debug_flag."""

    def test_no_debug_flag(self):
        """Vérifie le parsing sans --debug."""
        argv = ["script.py", "arg1", "arg2"]
        debug, remaining = parse_debug_flag(argv)

        assert debug is False
        assert remaining == ["script.py", "arg1", "arg2"]

    def test_with_debug_flag(self):
        """Vérifie le parsing avec --debug."""
        argv = ["script.py", "--debug", "arg1"]
        debug, remaining = parse_debug_flag(argv)

        assert debug is True
        assert remaining == ["script.py", "arg1"]

    def test_debug_flag_middle(self):
        """Vérifie --debug au milieu."""
        argv = ["script.py", "arg1", "--debug", "arg2"]
        debug, remaining = parse_debug_flag(argv)

        assert debug is True
        assert remaining == ["script.py", "arg1", "arg2"]

    def test_multiple_debug_flags(self):
        """Vérifie plusieurs --debug."""
        argv = ["--debug", "--debug", "arg"]
        debug, remaining = parse_debug_flag(argv)

        assert debug is True
        assert remaining == ["arg"]

    def test_empty_argv(self):
        """Vérifie argv vide."""
        debug, remaining = parse_debug_flag([])

        assert debug is False
        assert remaining == []


class TestConfigureLogging:
    """Tests pour configure_logging."""

    def test_configure_info_level(self):
        """Vérifie la configuration en mode INFO."""
        # Ne devrait pas lever d'exception
        configure_logging(debug=False)

    def test_configure_debug_level(self):
        """Vérifie la configuration en mode DEBUG."""
        # Ne devrait pas lever d'exception
        configure_logging(debug=True)

    def test_logging_actually_works(self):
        """Vérifie que le logging fonctionne après configuration."""
        from loguru import logger

        configure_logging(debug=True)

        # Capturer la sortie
        output = StringIO()
        logger.add(output, level="DEBUG")

        logger.debug("Test debug message")

        result = output.getvalue()
        assert "Test debug message" in result
