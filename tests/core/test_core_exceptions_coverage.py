"""Tests de couverture pour core/core_exceptions.py."""

from core.core_exceptions import GrubCommandError


def test_grub_command_error_full():
    """Test GrubCommandError avec tous les attributs."""
    error = GrubCommandError(
        "Échec de la commande",
        command="update-grub",
        returncode=1,
        stderr="Permission denied"
    )

    assert error.command == "update-grub"
    assert error.returncode == 1
    assert error.stderr == "Permission denied"

    error_str = str(error)
    assert "Échec de la commande" in error_str
    assert "Commande: update-grub" in error_str
    assert "Code retour: 1" in error_str
    assert "Stderr: Permission denied" in error_str

def test_grub_command_error_partial():
    """Test GrubCommandError avec attributs partiels."""
    # Sans commande
    error = GrubCommandError("Message", returncode=2)
    assert "Message" in str(error)
    assert "Code retour: 2" in str(error)
    assert "Commande:" not in str(error)

    # Sans code retour
    error = GrubCommandError("Message", command="ls")
    assert "Message" in str(error)
    assert "Commande: ls" in str(error)
    assert "Code retour:" not in str(error)

    # Sans stderr
    error = GrubCommandError("Message", stderr="Error")
    assert "Message" in str(error)
    assert "Stderr: Error" in str(error)

def test_grub_command_error_long_stderr():
    """Test GrubCommandError avec un stderr très long."""
    long_stderr = "x" * 500
    error = GrubCommandError("Message", stderr=long_stderr)
    assert len(error.stderr) == 500
    assert len(str(error).split("Stderr: ")[1]) <= 200
