"""Tests pour core/io/grub_parsing_utils.py."""

from core.io.core_io_grub_parsing_utils import extract_menuentry_id, extract_menuentry_title


class TestExtractMenuentryId:
    def test_extract_id_simple(self):
        line = "menuentry 'Ubuntu' --class ubuntu --id 'gnulinux-simple-uuid' {"
        assert extract_menuentry_id(line) == "gnulinux-simple-uuid"

    def test_extract_id_equals(self):
        line = "menuentry 'Ubuntu' --id=gnulinux-simple-uuid {"
        assert extract_menuentry_id(line) == "gnulinux-simple-uuid"

    def test_extract_id_dynamic(self):
        line = "menuentry 'Ubuntu' $menuentry_id_option 'gnulinux-simple-uuid' {"
        assert extract_menuentry_id(line) == "gnulinux-simple-uuid"

    def test_extract_id_none(self):
        line = "menuentry 'Ubuntu' {"
        assert extract_menuentry_id(line) == ""


class TestExtractMenuentryTitle:
    def test_extract_title_simple(self):
        line = "menuentry 'Ubuntu' {"
        assert extract_menuentry_title(line) == "Ubuntu"

    def test_extract_title_double_quotes(self):
        line = 'menuentry "Ubuntu Linux" {'
        assert extract_menuentry_title(line) == "Ubuntu Linux"

    def test_extract_title_none(self):
        line = "if [ x$feature_all_video_module = xy ]; then"
        assert extract_menuentry_title(line) == ""
