"""Tests pour core/io/grub_validation.py."""

from pathlib import Path
from unittest.mock import patch

from core.io.grub_validation import validate_grub_file


class TestValidateGrubFile:
    def test_file_not_exists(self):
        path = Path("/non/existent/path")
        result = validate_grub_file(path)
        assert result.is_valid is False
        assert "absent" in result.error_message

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.stat")
    def test_file_empty(self, mock_stat, mock_exists):
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 0
        result = validate_grub_file(Path("/tmp/grub.cfg"))
        assert result.is_valid is False
        assert "vide" in result.error_message

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.stat")
    @patch("pathlib.Path.read_text")
    def test_file_too_short(self, mock_read, mock_stat, mock_exists):
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 100
        mock_read.return_value = "# Comment\n"
        result = validate_grub_file(Path("/tmp/grub.cfg"), min_lines=5)
        assert result.is_valid is False
        assert "Trop peu de lignes" in result.error_message

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.stat")
    @patch("pathlib.Path.read_text")
    def test_file_valid(self, mock_read, mock_stat, mock_exists):
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 100
        mock_read.return_value = "line1\nline2\nline3"
        result = validate_grub_file(Path("/tmp/grub.cfg"), min_lines=2)
        assert result.is_valid is True
        assert result.meaningful_lines == 3

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.stat")
    @patch("pathlib.Path.read_text")
    def test_read_error(self, mock_read, mock_stat, mock_exists):
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 100
        mock_read.side_effect = OSError("Read error")
        result = validate_grub_file(Path("/tmp/grub.cfg"))
        assert result.is_valid is False
        assert "Erreur de lecture" in result.error_message
