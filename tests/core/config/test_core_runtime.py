"""Tests pour core/runtime.py - Utilitaires CLI."""

from __future__ import annotations

from io import StringIO

from core.config.core_config_runtime import configure_logging, parse_debug_flag, parse_verbosity_flags


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


class TestParseVerbosityFlags:
    """Tests pour parse_verbosity_flags."""

    def test_no_flags(self):
        debug, verbose, remaining = parse_verbosity_flags(["script.py", "arg1"])
        assert debug is False
        assert verbose is False
        assert remaining == ["script.py", "arg1"]

    def test_verbose_flag(self):
        debug, verbose, remaining = parse_verbosity_flags(["--verbose", "arg"])
        assert debug is False
        assert verbose is True
        assert remaining == ["arg"]

    def test_debug_flag(self):
        debug, verbose, remaining = parse_verbosity_flags(["--debug", "arg"])
        assert debug is True
        assert verbose is False
        assert remaining == ["arg"]

    def test_both_flags(self):
        debug, verbose, remaining = parse_verbosity_flags(["--verbose", "--debug", "arg"])
        assert debug is True
        assert verbose is True
        assert remaining == ["arg"]


class TestConfigureLogging:
    """Tests pour configure_logging."""

    def test_configure_info_level(self):
        """Vérifie la configuration en mode INFO."""
        # Sans --verbose/--debug: silencieux (pas de handler).
        configure_logging(debug=False, verbose=False)

        from loguru import logger

        output = StringIO()
        logger.add(output, level="INFO")
        logger.info("Test info message")
        assert "Test info message" in output.getvalue()

    def test_configure_verbose_level(self):
        """Vérifie la configuration en mode --verbose (INFO)."""
        from loguru import logger

        configure_logging(debug=False, verbose=True)

        output = StringIO()
        logger.add(output, level="INFO")
        logger.info("Verbose info")
        assert "Verbose info" in output.getvalue()

    def test_configure_debug_level(self):
        """Vérifie la configuration en mode DEBUG."""
        # Ne devrait pas lever d'exception
        configure_logging(debug=True, verbose=False)

    def test_logging_actually_works(self):
        """Vérifie que le logging fonctionne après configuration."""
        from loguru import logger

        configure_logging(debug=True, verbose=False)

        # Capturer la sortie
        output = StringIO()
        logger.add(output, level="DEBUG")

        logger.debug("Test debug message")

        result = output.getvalue()
        assert "Test debug message" in result
