import subprocess
import pytest

def test_version():
    subprocess.check_output(
        "k53certbot --version",
        shell=True
    )

def test_debug():
    capture = subprocess.check_output(
        "k53certbot --version --debug",
        shell=True
    )
    assert b"debug mode" in capture


def test_bad_command():
    with pytest.raises(subprocess.CalledProcessError):
        subprocess.check_output(
            "k53certbot --bad-command",
            shell=True
        )