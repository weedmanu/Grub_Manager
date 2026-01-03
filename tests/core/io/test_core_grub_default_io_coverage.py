from unittest.mock import MagicMock, patch

from core.io.core_grub_default_io import (
    GRUB_DEFAULT_PATH,
    create_grub_default_backup,
    ensure_initial_grub_default_backup,
)


class TestGrubDefaultIOCoverage:
    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.exists", return_value=True)
    @patch("core.io.core_grub_default_io.Path")
    def test_ensure_initial_backup_add_default_exception(self, mock_path_cls, mock_exists, mock_isfile, mock_tar_open):
        """Test exception when adding default_grub to initial backup."""
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        # Mock Path instances
        mock_path = MagicMock()
        mock_path_cls.return_value = mock_path

        # initial_backup_path = Path(path).parent / "grub_backup.initial.tar.gz"
        mock_initial_backup_path = MagicMock()
        mock_path.parent.__truediv__.return_value = mock_initial_backup_path
        mock_initial_backup_path.exists.return_value = False # Backup doesn't exist yet

        # Raise exception on first add (default_grub)
        mock_tar.add.side_effect = [OSError("Add failed"), None, None]

        ensure_initial_grub_default_backup(GRUB_DEFAULT_PATH)

        # Verify add was called
        assert mock_tar.add.called

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.exists", return_value=True)
    @patch("core.io.core_grub_default_io.Path")
    def test_ensure_initial_backup_add_script_exception(self, mock_path_cls, mock_exists, mock_isfile, mock_tar_open):
        """Test exception when adding script to initial backup."""
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        # Mock Path instances
        mock_path = MagicMock()
        mock_grub_d = MagicMock()
        mock_initial_backup_path = MagicMock()

        def path_side_effect(arg):
            if str(arg) == "/etc/grub.d":
                return mock_grub_d
            return mock_path
        mock_path_cls.side_effect = path_side_effect

        mock_path.parent.__truediv__.return_value = mock_initial_backup_path
        mock_initial_backup_path.exists.return_value = False

        # Mock grub.d iteration
        mock_grub_d.exists.return_value = True
        mock_script = MagicMock()
        mock_script.is_file.return_value = True
        mock_script.name = "00_header"
        mock_grub_d.iterdir.return_value = [mock_script]

        # First add is default_grub (success), second is script (fail)
        mock_tar.add.side_effect = [None, OSError("Add script failed"), None]

        ensure_initial_grub_default_backup(GRUB_DEFAULT_PATH)

        # Verify script add was attempted
        assert mock_tar.add.call_count >= 2

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.exists", return_value=True)
    @patch("core.io.core_grub_default_io.os.access", return_value=True)
    def test_create_backup_add_default_exception(self, mock_access, mock_exists, mock_isfile, mock_tar_open):
        """Test exception when adding default_grub to manual backup."""
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        mock_tar.add.side_effect = OSError("Add failed")

        def exists_side_effect(path):
            if "backup.manual" in str(path):
                return False
            return True
        mock_exists.side_effect = exists_side_effect

        create_grub_default_backup(GRUB_DEFAULT_PATH)
        assert mock_tar.add.called

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.exists", return_value=True)
    @patch("core.io.core_grub_default_io.os.access", return_value=True)
    @patch("core.io.core_grub_default_io.Path")
    def test_create_backup_add_script_exception(self, mock_path_cls, mock_access, mock_exists, mock_isfile, mock_tar_open):
        """Test exception when adding script to manual backup."""
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        mock_grub_d = MagicMock()
        mock_grub_d.exists.return_value = True
        mock_script = MagicMock()
        mock_script.is_file.return_value = True
        mock_script.name = "00_header"
        mock_grub_d.iterdir.return_value = [mock_script]

        def path_side_effect(arg):
            if str(arg) == "/etc/grub.d":
                return mock_grub_d
            return MagicMock()
        mock_path_cls.side_effect = path_side_effect

        def exists_side_effect(path):
            if "backup.manual" in str(path):
                return False
            return True
        mock_exists.side_effect = exists_side_effect

        # default_grub success, script fail
        mock_tar.add.side_effect = [None, OSError("Add script failed"), None]

        create_grub_default_backup(GRUB_DEFAULT_PATH)
        assert mock_tar.add.call_count >= 2

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.exists", return_value=True)
    @patch("core.io.core_grub_default_io.os.access", return_value=True)
    @patch("core.io.core_grub_default_io.Path")
    @patch("core.io.core_grub_default_io.GRUB_CFG_PATHS", ["/boot/grub/grub.cfg"])
    def test_create_backup_add_cfg_exception(self, mock_path_cls, mock_access, mock_exists, mock_isfile, mock_tar_open):
        """Test exception when adding grub.cfg to manual backup."""
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        mock_grub_d = MagicMock()
        mock_grub_d.exists.return_value = False # Skip scripts to focus on cfg

        def path_side_effect(arg):
            if str(arg) == "/etc/grub.d":
                return mock_grub_d
            if str(arg) == "/boot/grub/grub.cfg":
                p = MagicMock()
                p.parts = ["/", "boot", "grub", "grub.cfg"]
                return p
            return MagicMock()
        mock_path_cls.side_effect = path_side_effect

        def exists_side_effect(path):
            if "backup.manual" in str(path):
                return False
            return True
        mock_exists.side_effect = exists_side_effect

        # default_grub success, cfg fail
        mock_tar.add.side_effect = [None, OSError("Add cfg failed")]

        create_grub_default_backup(GRUB_DEFAULT_PATH)
        assert mock_tar.add.call_count >= 2

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.exists", return_value=True)
    @patch("core.io.core_grub_default_io.Path")
    def test_create_backup_grub_d_not_exists(self, mock_path_cls, mock_exists, mock_isfile, mock_tar_open):
        """Test manual backup when /etc/grub.d does not exist."""
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        mock_grub_d = MagicMock()
        mock_grub_d.exists.return_value = False

        def path_side_effect(arg):
            if str(arg) == "/etc/grub.d":
                return mock_grub_d
            return MagicMock()
        mock_path_cls.side_effect = path_side_effect

        def exists_side_effect(path):
            if "backup.manual" in str(path):
                return False
            return True
        mock_exists.side_effect = exists_side_effect

        create_grub_default_backup(GRUB_DEFAULT_PATH)
        # Should not try to iterate grub.d

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.exists")
    @patch("core.io.core_grub_default_io.Path")
    def test_ensure_initial_backup_os_exists_exception(self, mock_path_cls, mock_exists, mock_isfile, mock_tar_open):
        """Test OSError during os.path.exists in initial backup."""
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        mock_path = MagicMock()
        mock_path_cls.return_value = mock_path
        mock_initial_backup_path = MagicMock()
        mock_path.parent.__truediv__.return_value = mock_initial_backup_path
        mock_initial_backup_path.exists.return_value = False

        # Mock grub.d to be empty to reach grub.cfg loop
        mock_grub_d = MagicMock()
        mock_grub_d.exists.return_value = False

        def path_side_effect(arg):
            if str(arg) == "/etc/grub.d":
                return mock_grub_d
            return mock_path
        mock_path_cls.side_effect = path_side_effect

        # Raise OSError on exists check for grub.cfg
        mock_exists.side_effect = OSError("Exists failed")

        ensure_initial_grub_default_backup(GRUB_DEFAULT_PATH)
        # Should handle exception and continue (exists=False)

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.exists")
    @patch("core.io.core_grub_default_io.Path")
    def test_create_backup_os_exists_exception(self, mock_path_cls, mock_exists, mock_isfile, mock_tar_open):
        """Test OSError during os.path.exists in manual backup."""
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        mock_grub_d = MagicMock()
        mock_grub_d.exists.return_value = False

        def path_side_effect(arg):
            if str(arg) == "/etc/grub.d":
                return mock_grub_d
            return MagicMock()
        mock_path_cls.side_effect = path_side_effect

        # Raise OSError on exists check
        mock_exists.side_effect = OSError("Exists failed")

        create_grub_default_backup(GRUB_DEFAULT_PATH)
        # Should handle exception

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile")
    @patch("core.io.core_grub_default_io.read_grub_default")
    @patch("core.io.core_grub_default_io.Path")
    def test_ensure_initial_backup_restore_success(self, mock_path_cls, mock_read_default, mock_isfile, mock_tar_open):
        """Test initial backup when source is missing but restore succeeds."""
        mock_isfile.return_value = False
        mock_read_default.return_value = {"GRUB_TIMEOUT": "5"}

        mock_path = MagicMock()
        mock_path_cls.return_value = mock_path
        mock_initial_backup_path = MagicMock()
        mock_path.parent.__truediv__.return_value = mock_initial_backup_path
        mock_initial_backup_path.exists.return_value = False

        ensure_initial_grub_default_backup(GRUB_DEFAULT_PATH)
        assert mock_read_default.called

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.getmtime", return_value=1000)
    @patch("core.io.core_grub_default_io.os.path.isfile")
    @patch("core.io.core_grub_default_io.read_grub_default")
    def test_create_backup_restore_success(self, mock_read_default, mock_isfile, mock_mtime, mock_tar_open):
        """Test manual backup when source is missing but restore succeeds."""
        # First call to isfile returns False, subsequent calls return True
        def isfile_side_effect(path):
            if not hasattr(isfile_side_effect, "called"):
                isfile_side_effect.called = True
                return False
            return True
        mock_isfile.side_effect = isfile_side_effect

        # Mock tar to avoid errors
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        result = create_grub_default_backup(GRUB_DEFAULT_PATH)
        assert "manual" in result
        assert mock_tar.add.called

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.exists")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.read_grub_default")
    def test_ensure_initial_backup_grub_d_not_exists(self, mock_read_default, mock_isfile, mock_exists, mock_tar_open):
        """Test ensure_initial_grub_default_backup when /etc/grub.d does not exist."""
        # Mock Path.exists globally for this test
        with patch("core.io.core_grub_default_io.Path.exists", return_value=False):
            # os.path.exists returns False for /etc/grub.d but True for grub.cfg
            def exists_side_effect(p):
                if "/etc/grub.d" in str(p): return False
                return True
            mock_exists.side_effect = exists_side_effect

            mock_tar = MagicMock()
            mock_tar_open.return_value.__enter__.return_value = mock_tar

            ensure_initial_grub_default_backup(GRUB_DEFAULT_PATH)
            # Should add /etc/default/grub and one of GRUB_CFG_PATHS
            assert mock_tar.add.call_count == 2

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.exists", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.read_grub_default")
    def test_ensure_initial_backup_add_script_exception_coverage(self, mock_read_default, mock_isfile, mock_exists, mock_tar_open):
        """Test ensure_initial_grub_default_backup handles exception during script addition."""
        # Mock Path.exists and Path.iterdir
        with patch("core.io.core_grub_default_io.Path.exists", return_value=False) as mock_p_exists, \
             patch("core.io.core_grub_default_io.Path.iterdir") as mock_iter, \
             patch("core.io.core_grub_default_io.Path.is_file", return_value=True):

            # backup_path.exists() -> False (to trigger backup)
            # grub_d_dir.exists() -> True (to enter scripts loop)
            mock_p_exists.side_effect = [False, True]

            mock_script = MagicMock()
            mock_script.name = "00_header"
            mock_script.is_file.return_value = True
            mock_iter.return_value = [mock_script]

            mock_tar = MagicMock()
            mock_tar_open.return_value.__enter__.return_value = mock_tar

            # Trigger exception on second add (first is /etc/default/grub)
            def add_side_effect(name, *args, **kwargs):
                if "00_header" in str(name):
                    raise OSError("Tar add error")
                return None
            mock_tar.add.side_effect = add_side_effect

            ensure_initial_grub_default_backup(GRUB_DEFAULT_PATH)
            assert mock_tar.add.called

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.exists", return_value=False)
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    def test_ensure_initial_backup_skips_non_file_grub_d_entry(self, mock_isfile, mock_exists, mock_tar_open):
        """Couvre la branche où un élément de /etc/grub.d n'est pas un fichier (119->118)."""
        with patch("core.io.core_grub_default_io.Path.exists", return_value=False) as mock_p_exists, \
             patch("core.io.core_grub_default_io.Path.iterdir") as mock_iter:
            # backup_path.exists() -> False (déclenche la création)
            # grub_d_dir.exists() -> True (entre dans la boucle grub.d)
            mock_p_exists.side_effect = [False, True]

            mock_script = MagicMock()
            mock_script.is_file.return_value = False
            mock_iter.return_value = [mock_script]

            mock_tar = MagicMock()
            mock_tar_open.return_value.__enter__.return_value = mock_tar

            ensure_initial_grub_default_backup(GRUB_DEFAULT_PATH)
            # On a ajouté /etc/default/grub, mais pas le script non-fichier
            assert mock_tar.add.call_count >= 1

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    def test_ensure_initial_backup_add_grub_cfg_exception_is_handled(self, mock_isfile, mock_tar_open):
        """Couvre l'exception lors de l'ajout de grub.cfg (141-142)."""
        grub_cfg_path = "/boot/grub/grub.cfg"

        with patch("core.io.core_grub_default_io.GRUB_CFG_PATHS", [grub_cfg_path]), \
             patch("core.io.core_grub_default_io.os.path.exists", return_value=True), \
             patch("core.io.core_grub_default_io.Path.exists", return_value=False):
            mock_tar = MagicMock()
            mock_tar_open.return_value.__enter__.return_value = mock_tar

            def add_side_effect(name, *args, **kwargs):
                if str(name) == grub_cfg_path:
                    raise OSError("Tar add error")
                return None

            mock_tar.add.side_effect = add_side_effect

            # Ne doit pas lever, juste logger et continuer.
            ensure_initial_grub_default_backup(GRUB_DEFAULT_PATH)
            assert mock_tar.add.called

    @patch("core.io.core_grub_default_io.tarfile.open")
    @patch("core.io.core_grub_default_io.os.path.isfile", return_value=True)
    @patch("core.io.core_grub_default_io.os.path.exists", return_value=True)
    @patch("core.io.core_grub_default_io.Path")
    def test_create_backup_script_not_file(self, mock_path_cls, mock_exists, mock_isfile, mock_tar_open):
        """Test manual backup skips non-file items in /etc/grub.d."""
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        mock_grub_d = MagicMock()
        mock_grub_d.exists.return_value = True
        mock_script = MagicMock()
        mock_script.is_file.return_value = False # Directory or other
        mock_grub_d.iterdir.return_value = [mock_script]

        def path_side_effect(arg):
            if str(arg) == "/etc/grub.d":
                return mock_grub_d
            return MagicMock()
        mock_path_cls.side_effect = path_side_effect

        def exists_side_effect(path):
            if "backup.manual" in str(path):
                return False
            return True
        mock_exists.side_effect = exists_side_effect

        create_grub_default_backup(GRUB_DEFAULT_PATH)
        # Should not add script
        assert mock_tar.add.call_count == 2 # default_grub + grub.cfg (if exists)
